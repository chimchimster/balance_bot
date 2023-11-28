import re
import itertools
from typing import Optional, Any, Coroutine, Awaitable

import sqlalchemy.exc

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.methods import EditMessageReplyMarkup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, FSInputFile

from sqlalchemy import select

from database.session import AsyncSessionLocal
from keyboards.inline.app import bought_items_markup
from keyboards.inline.purchases import get_search_filter_keyboard
from utils.jinja_template import render_template
from utils.paginator import PaginatorStorage
from bot import bot as balance_bot


async def validate_user_registration(
        message: Message,
        state: FSMContext,
        state_to_set: State,
        info_msg: str,
        err_msg: str,
        regex_pattern: str,
        key_name: str,
        end: bool = False,
) -> None:

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id:
        await message.chat.delete_message(message_id=last_bot_msg_id)

    msg_txt = message.text

    if not re.match(regex_pattern, msg_txt):

        last_bot_msg = await message.answer(f'<code>{err_msg}</code>')

        await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})

        return

    await state.update_data({key_name: msg_txt})
    await state.set_state(state_to_set)
    await message.chat.delete_message(message_id=message.message_id)

    if not end:
        last_bot_msg = await message.answer(f'<code>{info_msg}</code>')
    else:
        button_yes = KeyboardButton(text='Да')
        button_no = KeyboardButton(text='Нет')

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[button_yes], [button_no]], resize_keyboard=True)

        last_bot_msg = await message.answer(f'<code>{info_msg}</code>', reply_markup=keyboard)

    await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})


async def password_matched(password: str, password_confirmation: str) -> bool:

    if not any([password, password_confirmation]):
        return False

    if password != password_confirmation:
        return False
    return True


async def filter_products(
        filter_name: str,
        table,
        query: CallbackQuery,
        state: FSMContext
) -> Optional[Message]:

    data = await state.get_data()
    last_bot_msg_id = data.get('last_bot_msg_id')

    product_filter = data.get(filter_name)

    if not product_filter:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    select_stmt = select(table.id, table.title)
                    objects = await session.execute(select_stmt)
                    objects = objects.fetchall()

                    await state.update_data(
                        {filter_name: ':'.join([','.join(tuple(map(str, obj))) for obj in objects + [('0', 'Без фильтра')]])})
        except sqlalchemy.exc.SQLAlchemyError:
            bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
            await state.update_data({'last_bot_msg_id': bot_message.message_id})
            return bot_message
    else:
        objects = [tuple(obj.split(',')) for obj in product_filter.split(':')] + [('0', 'Без фильтра')]

    prev_obj = data.get(f'current_{filter_name.split("_")[0]}')

    objects_gen = itertools.cycle(objects)

    current_obj = next(
        itertools.islice(objects_gen, int(prev_obj.split(',')[0]) if prev_obj is not None else 0, None), None
    )

    if current_obj:

        await state.update_data({f'current_{filter_name.split("_")[0]}': ','.join(map(str, current_obj))})

        data = await state.get_data()

        current_brand = data.get('current_brand')
        current_color = data.get('current_color')
        current_size = data.get('current_size')
        current_sex = data.get('current_sex')

        await EditMessageReplyMarkup(
            chat_id=query.message.chat.id, message_id=last_bot_msg_id,
            reply_markup=await get_search_filter_keyboard(
                brand=current_brand.split(',')[-1] if current_brand is not None else None,
                color=current_color.split(',')[-1] if current_color is not None else None,
                size=current_size.split(',')[-1] if current_size is not None else None,
                sex=current_sex.split(',')[-1] if current_sex is not None else None,
            )
        ).as_(balance_bot)


async def paginate(
        query: CallbackQuery,
        state: FSMContext,
        next_obj: Any,
        previous_callback_name: str,
        callback_data: Any,
        template_name: str,
        reply_coroutine,
        paginator_storage: PaginatorStorage,
        is_cart: bool = False,
):
    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')
    last_bot_msg_photo_id = data.get('last_bot_msg_photo_id')

    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

    if last_bot_msg_photo_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_photo_id)

    tg_id = query.message.chat.id

    async with paginator_storage:
        paginator = paginator_storage[tg_id]

    c_data = query.data
    if c_data == previous_callback_name:
        c_data = callback_data(flag=True)
        flag = c_data.flag
    else:
        flag = True if c_data.split(':')[-1] == '1' else False

    paginator.direction = flag
    paginator_value = next_obj(*next(paginator))
    # ТУТ ОШИБКА!! item_description=Decimal('99.98'), item_price='Красивые и нежные, они такие любимые и неизвестные'
    print(paginator_value)
    current_item_serialized = paginator_value._asdict()
    print(current_item_serialized)
    if is_cart is not None:
        await state.update_data({'current_item': current_item_serialized})

    html = await render_template(
        template_name,
        item_title=paginator_value.item_title,
        item_description=paginator_value.item_description,
        item_price=paginator_value.item_price,
        brand_name=paginator_value.brand_name.upper(),
    )

    has_next = paginator.has_next()
    has_prev = paginator.has_prev()

    bot_message_photo = await query.message.answer_photo(
        FSInputFile(paginator_value.image_path),
        caption=paginator_value.item_title,
    )
    bot_message = await query.message.answer(text=html, reply_markup=await reply_coroutine(has_next, has_prev))
    await state.update_data({
        'last_bot_msg_id': bot_message.message_id,
        'last_bot_msg_photo_id': bot_message_photo.message_id
    })

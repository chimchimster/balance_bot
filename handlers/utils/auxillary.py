import functools
import re
import itertools
from typing import Optional, Any, Union, Coroutine, Callable
from bisect import bisect_left

import aiogram.exceptions
import sqlalchemy.exc

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.methods import EditMessageReplyMarkup, SendMessage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, FSInputFile

from sqlalchemy import select

from database.session import AsyncSessionLocal
from keyboards.inline.app import bought_items_markup, main_menu_markup
from keyboards.inline.auth import refuse_operations_keyboard
from keyboards.inline.purchases import get_search_filter_keyboard
from utils.jinja_template import render_template
from utils.paginator import PaginatorStorage
from serializers.serializers import RedisSerializer
from bot import bot as balance_bot


async def validate_user_registration(
        message: Message,
        state: FSMContext,
        state_to_set: State,
        info_msg: str,
        err_msg: str,
        regex_pattern: str,
        key_name: str,
        template_name: str,
        end: bool = False,
) -> None:

    data = await state.get_data()

    username = message.from_user.username.capitalize()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id:
        await message.chat.delete_message(message_id=last_bot_msg_id)

    msg_txt = message.text

    if not re.match(regex_pattern, msg_txt):
        html = await render_template(template_name, msg=err_msg, username=username)
        last_bot_msg = await message.answer(
            html,
            reply_markup=await refuse_operations_keyboard(),
        )

        await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})

        return

    await state.update_data({key_name: msg_txt})
    await state.set_state(state_to_set)
    await message.chat.delete_message(message_id=message.message_id)

    html = await render_template(
        template_name,
        msg=info_msg,
        username=username,
    )
    if not end:
        last_bot_msg = await message.answer(
            text=html,
            reply_markup=await refuse_operations_keyboard(),
        )
    else:
        button_yes = KeyboardButton(text='Да')
        button_no = KeyboardButton(text='Нет')

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [button_yes],
                [button_no],
            ],
            resize_keyboard=True,
        )

        last_bot_msg = await message.answer(
            text=html,
            reply_markup=keyboard,
        )

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

            html = await render_template('errors/common.html')
            bot_message = await query.message.answer(
                text=html,
                reply_markup=await main_menu_markup(),
            )
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

    update_cart = False
    if is_cart is not None:

        cart_has_values = data.get('in_cart')

        if not cart_has_values:
            await state.update_data({'in_cart': []})
        else:
            cart_items_ids = [item.get('id') for item in cart_has_values if item]
            idx_of_obj_in_cart = bisect_left(cart_items_ids, paginator_value.id)
            update_cart = len([value for value in cart_items_ids if value == paginator_value.id]) \
                if (idx_of_obj_in_cart != len(cart_items_ids) and cart_items_ids[idx_of_obj_in_cart] == paginator_value.id) \
                else 0

        current_item = paginator_value._asdict()
        current_item_serialized = await RedisSerializer(current_item).__call__()
        await state.update_data({'current_item': current_item_serialized})

    html = await render_template(
        template_name,
        item_title=paginator_value.title,
        item_description=paginator_value.description,
        item_price=paginator_value.price,
        brand_name=paginator_value.brand_name.upper(),
    )

    has_next = paginator.has_next()
    has_prev = paginator.has_prev()
    await state.update_data({'has_next': has_next, 'has_prev': has_prev})

    current_filter = data.get('current_filters')

    bot_message_photo = await query.message.answer_photo(
        FSInputFile(paginator_value.image_path),
        caption=paginator_value.title,
    )
    bot_message = await query.message.answer(
        text=html,
        reply_markup=await reply_coroutine(has_next, has_prev, update_cart=update_cart, current_filter=current_filter),
    )
    await state.update_data(
        {
            'last_bot_msg_photo_id': bot_message_photo.message_id,
        }
    )

    return bot_message, bot_message_photo


async def delete_prev_messages(
        query_or_message: Union[CallbackQuery, Message],
        previous_msg_id: int,
        previous_msg_photo_id: int,
) -> None:

    if isinstance(query_or_message, Message):
        obj = query_or_message
    elif isinstance(query_or_message, CallbackQuery):
        obj = query_or_message.message
    else:
        raise ValueError

    # Try to delete text message
    if previous_msg_id is not None:
        try:
            await obj.chat.delete_message(message_id=previous_msg_id)
        except aiogram.exceptions.TelegramBadRequest:
            ...

    # Try to delete message with photo
    if previous_msg_photo_id is not None:
        try:
            await obj.chat.delete_message(message_id=previous_msg_photo_id)
        except aiogram.exceptions.TelegramBadRequest:
            ...


async def update_state_after_deleting_prev_message(result_coro: Any, state: FSMContext):

    if isinstance(result_coro, tuple) and len(result_coro) == 2:

        await state.update_data(
            {
                'last_bot_msg_id': result_coro[0].message_id,
                'last_bot_msg_photo_id': result_coro[-1].message_id,
            }
        )
    elif isinstance(result_coro, (CallbackQuery, Message)):

        await state.update_data(
            {
                'last_bot_msg_id': result_coro.message_id,
            }
        )
    else:
        raise ValueError


def delete_prev_messages_and_update_state(coro: Callable):

    @functools.wraps(coro)
    async def wrapper(query_or_message: Union[CallbackQuery, Message], state: FSMContext, *args, **kwargs):

        data = await state.get_data()

        last_bot_msg_id = data.get('last_bot_msg_id')
        last_bot_msg_photo_id = data.get('last_bot_msg_photo_id')

        await delete_prev_messages(query_or_message, last_bot_msg_id, last_bot_msg_photo_id)

        result_coro = await coro(query_or_message, state, *args, **kwargs)

        await update_state_after_deleting_prev_message(result_coro, state)

        return result_coro

    return wrapper


async def group_order(order_items: list[dict]) -> dict:

    grouped_order_items = {}

    for order_item in order_items:
        item = tuple(order_item.items())
        if item not in grouped_order_items:
            grouped_order_items[item] = 1
        else:
            grouped_order_items[item] += 1

    return grouped_order_items

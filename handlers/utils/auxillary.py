import re
import itertools
from typing import Optional

import sqlalchemy.exc

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.methods import EditMessageReplyMarkup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery

from sqlalchemy import select

from database.models import *
from database.session import AsyncSessionLocal
from keyboards.inline.purchases import get_search_filter_keyboard

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

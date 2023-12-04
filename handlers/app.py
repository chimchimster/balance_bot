from typing import Union

import aiogram.exceptions
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from cart.cart import Cart
from keyboards.inline.app import *

from states.states import InitialState
from handlers.utils.auxillary import delete_prev_messages
from balance_bot.utils.jinja_template import render_template

router = Router()


async def send_main_manu(obj: Union[Message, CallbackQuery], state: FSMContext):

    old_data = await state.get_data()

    last_bot_msg_id = old_data.get('last_bot_msg_id')
    last_bot_msg_photo_id = old_data.get('last_bot_msg_photo_id')

    await delete_prev_messages(obj, last_bot_msg_id, last_bot_msg_photo_id)

    await state.set_data({key: value for key, value in old_data.items() if key in ('in_cart', 'current_address', 'current_address_id')})

    html = await render_template('menu/main_menu.html')

    if isinstance(obj, Message):
        qry = obj
    elif isinstance(obj, CallbackQuery):
        qry = obj.message
    else:
        raise ValueError

    bot_message = await qry.answer(text=html, reply_markup=await main_menu_markup())
    await state.update_data({'last_bot_msg_id': bot_message.message_id})

@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):
    await send_main_manu(message, state)


@router.callback_query(
    F.data == 'back_to_main_menu'
)
async def main_menu_callback_handler(query: CallbackQuery, state: FSMContext):
    await send_main_manu(query, state)


@router.message()
async def handle_404(message: Message, state: FSMContext):

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')
    if last_bot_msg_id is not None:
        await message.chat.delete_message(message_id=last_bot_msg_id)
    bot_message = await message.answer('<code>Запрашиваемые вами данные не найдены, пожалуйста, обратитесь в поддержку!</code>')

    await state.update_data({'last_bot_msg_id': bot_message.message_id})

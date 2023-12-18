from typing import Union

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.inline.app import *

from states.states import InitialState
from handlers.utils.auxillary import delete_prev_messages_and_update_state
from balance_bot.utils.jinja_template import render_template

router = Router()


@delete_prev_messages_and_update_state
async def send_main_manu(obj: Union[Message, CallbackQuery], state: FSMContext):

    old_data = await state.get_data()

    await state.set_data({key: value for key, value in old_data.items() if key in (
        'in_cart',
        'current_address',
        'current_address_id',
    )})

    html = await render_template('menu/main_menu.html')

    if isinstance(obj, Message):
        qry = obj
    elif isinstance(obj, CallbackQuery):
        qry = obj.message
    else:
        raise ValueError

    return await qry.answer(text=html, reply_markup=await main_menu_markup())


@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):
    return await send_main_manu(message, state)


@router.callback_query(
    F.data == 'back_to_main_menu'
)
async def main_menu_callback_handler(query: CallbackQuery, state: FSMContext):
    return await send_main_manu(query, state)
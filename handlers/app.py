from typing import Union

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from cart.cart import Cart
from keyboards.inline.app import *

from states.states import InitialState
from balance_bot.utils.jinja_template import render_template

router = Router()


async def send_main_manu(obj: Union[Message, CallbackQuery], state: FSMContext):

    await state.clear()

    html = await render_template('menu/main_menu.html')

    if isinstance(obj, Message):
        await obj.answer(text=html, reply_markup=await main_menu_markup())
    else:
        await obj.message.answer(text=html, reply_markup=await main_menu_markup())


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
async def handle_404(message: Message):
    await message.answer('<code>Запрашиваемые вами данные не найдены, пожалуйста, обратитесь в поддержку!</code>')

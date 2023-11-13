from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states.states import InitialState
from balance_bot.utils.jinja_template import render_template

router = Router()


@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):

    html = await render_template('main_menu.html')

    await message.answer(text=html)

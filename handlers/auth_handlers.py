from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

router = Router()


@router.message(CommandStart)
async def cmd_start_handler(message: Message, state: FSMContext):

    return message.answer('Hello, world!')

import asyncio
from typing import Dict

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from states.states import AuthState
from signals.signals import Signal
from database.models import *
from database.handlers.utils.session import PostgresAsyncSession


router = Router()


@router.message(CommandStart)
async def cmd_start_handler(message: Message, state: FSMContext, **kwargs):

    auth_state = kwargs.pop('auth_state')

    if not auth_state:
        return message.answer('Увы, что-то пошло не так... Разработчики уже работают над вашей проблемой.')

    match auth_state:
        case Signal.AUTHENTICATED:
            # to app handler
            ...
        case Signal.NOT_AUTHENTICATED:
            # to authentication handler
            ...
        case Signal.NOT_REGISTERED:
            # to register handler
            ...


async def register_user_handler(message: Message):
    pass



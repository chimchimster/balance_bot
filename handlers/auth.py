import re
import time
from typing import Optional

import sqlalchemy.exc

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from database.models import *
from database.handlers.utils.session import PostgresAsyncSession
from database.handlers.utils.redis_client import connect_redis_url
from database.models.exceptions.models_exc import *
from keyboards.inline.auth import *
from signals.signals import Signal
from states.states import InitialState, RegState
from handlers.utils.auxillary import validate_user_registration, password_matched
from handlers.app import main_menu_handler


router = Router()


@router.message(CommandStart())
async def cmd_start_handler(message: Message, state: FSMContext, **kwargs):

    auth_state = kwargs.pop('auth_state')

    if not auth_state:
        return message.answer('<code>Увы, что-то пошло не так...</code>')

    match auth_state:
        case Signal.AUTHENTICATED:

            await state.set_state(InitialState.TO_APPLICATION)

            return await main_menu_handler(message, state)

        case Signal.NOT_AUTHENTICATED:

            await state.set_state(InitialState.TO_AUTHENTICATION)

            bot_message = await message.answer(
                f'<code>Привет, {message.from_user.username}!\n\nЧтобы авторизоваться введи пароль:</code>')

            await state.update_data({'last_bot_msg_id': bot_message.message_id})

            return bot_message

        case Signal.NOT_REGISTERED:

            await state.set_state(InitialState.TO_REGISTRATION)

            bot_message = await message.answer(
                f'<code>Привет, {message.from_user.username}\n\nЧтобы начать пользоваться нашим магазином нужно '
                f'зарегистрироваться.\n\nЭто займет совсем немного времни, начнем?</code>',
                reply_markup=await get_registration_keyboard())

            await state.update_data({'last_bot_msg_id': bot_message.message_id})

            return bot_message

        case _:
            # 500 server error
            ...


@router.callback_query(
    InitialState.TO_REGISTRATION,
    F.data == 'to_registration'
)
async def register_user_handler(query: CallbackQuery, state: FSMContext):

    await query.message.chat.delete_message(query.message.message_id)

    await state.set_state(RegState.INPUT_FIRST_NAME)

    bot_message = await query.message.answer('<code>Введите имя:</code>')

    await state.update_data({'last_bot_msg_id': bot_message.message_id})


@router.message(
    RegState.INPUT_FIRST_NAME,
)
async def input_first_name(message: Message, state: FSMContext) -> Optional[Message]:

    return await validate_user_registration(
        message,
        state,
        RegState.INPUT_LAST_NAME,
        'Введите фамилию:',
        'Пожалуйста, введите свое настоящее имя.',
        r'[А-Яа-яA-Za-z\s]{1,50}',
        'first_name',
    )


@router.message(
    RegState.INPUT_LAST_NAME,
)
async def input_last_name(message: Message, state: FSMContext) -> Optional[Message]:

    return await validate_user_registration(
        message,
        state,
        RegState.INPUT_PASSWORD,
        'Придумайте и запишите пароль. Он будет использоваться для входа в магазин.',
        'Пожалуйста, введите свою настоящую фамилию.',
        r'[А-Яа-яA-Za-z\s]{1,50}',
        'last_name'
    )


@router.message(
    RegState.INPUT_PASSWORD,
)
async def input_password(message: Message, state: FSMContext) -> Optional[Message]:

    return await validate_user_registration(
        message,
        state,
        RegState.INPUT_PASSWORD_CONFIRMATION,
        'Повторите пароль',
        'Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские буквы в верхнем и '
        'нижнем регистре, цифры, а также специальные символы.',
        r'[\w!@#$&\(\)\\-]{8,16}',
        'password'
    )


@router.message(
    RegState.INPUT_PASSWORD_CONFIRMATION,
)
async def input_password_confirmation(message: Message, state: FSMContext) -> Optional[Message]:

    return await validate_user_registration(
        message,
        state,
        RegState.CONFIRM_REGISTRATION,
        'Подтвердить введенные данные?',
        'Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские буквы в верхнем и '
        'нижнем регистре, цифры, а также специальные символы.',
        r'[\w!@#$&\(\)\\-]{8,16}',
        'password_confirmation',
        end=True,
    )


@router.message(
    RegState.CONFIRM_REGISTRATION,
    F.text == 'Да',
)
async def confirm_registration(message: Message, state: FSMContext) -> Optional[Message]:

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id:
        await message.chat.delete_message(message_id=last_bot_msg_id)

    tg_id = message.from_user.id
    first_name = data.get('first_name', 'John')
    last_name = data.get('last_name', 'Doe')
    password = data.get('password')
    password_confirmation = data.get('password_confirmation')

    pwd_matched = await password_matched(password, password_confirmation)

    if not pwd_matched:
        bot_message = await message.answer('<code>Упс, пароли не совпадают... Может вы опечатались?</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message

    r_cli = await connect_redis_url()
    now = int(time.time())

    try:
        async with PostgresAsyncSession() as session:
            async with session.begin() as transaction:
                user_id = await Users.create_user(tg_id, first_name, last_name, session)
                credentials = Credentials(user_id=user_id)
                await credentials.set_password(password)
                await credentials.set_auth_hash()
                session.add(credentials)
                await session.commit()
    except sqlalchemy.exc.SQLAlchemyError:
        await transaction.rollback()
        bot_message = await message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})

    else:
        await r_cli.hset(f'auth_hash:{tg_id}', mapping={
            'hash': credentials.auth_hash,
            'last_seen': now,
        })

        bot_message = await message.answer('Успешная регистрация!')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return


@router.message(
    RegState.CONFIRM_REGISTRATION,
    F.text == 'Нет',
)
async def refuse_registration(message: Message, state: FSMContext) -> Message:

    bot_message = await message.answer('<code>Очень жаль... может быть в другой раз?</code>')

    await state.update_data({'last_bot_msg_id': bot_message.message_id})

    return bot_message


@router.message(
    InitialState.TO_AUTHENTICATION
)
async def authenticate_user(message: Message, state: FSMContext) -> Optional[Message]:

    tg_id = message.from_user.id
    pwd = message.text

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id is not None:
        await message.chat.delete_message(message_id=last_bot_msg_id)

    if not re.match(r'[\w!@#$&\(\)\\-]{8,16}', pwd):
        bot_message = await message.answer('<code>У вас ошибка, может вы опечатались?</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        await message.chat.delete_message(message_id=message.message_id)
        return bot_message
    try:
        async with PostgresAsyncSession() as session:
            async with session.begin() as transaction:
                try:
                    user_id = await Users.get_user_id(tg_id, session)
                except UserNotFound:
                    await message.answer('<code>Упс, такого пользователя не существует...</code>')
                    await transaction.rollback()
                else:
                    credentials = await session.execute(select(Credentials).filter_by(user_id=user_id))
                    credentials = credentials.scalar()
                    pwd_matched = await credentials.check_password(pwd)

                    if not pwd_matched:

                        await message.chat.delete_message(message_id=message.message_id)

                        bot_message = await message.answer('<code>Увы, пароли не совпадают. Может вы опечатались?</code>')

                        await state.update_data({'last_bot_msg_id': bot_message.message_id})

                        return bot_message

                    await message.chat.delete_message(message_id=message.message_id)

                    await state.set_state(InitialState.TO_APPLICATION)

                    return await main_menu_handler(message, state)

    except sqlalchemy.exc.SQLAlchemyError:
        await transaction.rollback()
        return await message.answer('<code>Упс, что-то пошло не так...</code>')

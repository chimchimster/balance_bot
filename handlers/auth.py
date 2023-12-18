import re
import time
from typing import Optional

import aiogram.exceptions
import sqlalchemy.exc

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from apps.mail.sender import send_email
from apps.mail.code_gen import generate_code_for_restoring_password
from database.models import *
from database.handlers.utils.session import PostgresAsyncSession
from database.handlers.utils.redis_client import connect_redis_url
from database.models.exceptions.models_exc import *
from keyboards.inline.app import main_menu_markup
from keyboards.inline.auth import get_restore_password_keyboard, refuse_restore_password_keyboard
from states.states import InitialState, RegState, RestoreState
from handlers.utils.auxillary import validate_user_registration, password_matched, delete_prev_messages_and_update_state
from handlers.app import main_menu_handler

router = Router()


@router.message(Command(commands=['run', 'start']))
@delete_prev_messages_and_update_state
async def cmd_start_handler(message: Message, state: FSMContext) -> Message:

    state_level = await state.get_state()

    if state_level == InitialState.TO_AUTHENTICATION:
        return await authenticate_user(message, state)

    return await main_menu_handler(message, state)


@router.callback_query(
    F.data == 'refuse_operations',
)
@delete_prev_messages_and_update_state
async def refuse_restore_operations_handler(query: CallbackQuery, state: FSMContext):

    await state.clear()

    return await query.message.answer(
        f'<code>Привет, {query.from_user.username}!\n\nЧтобы авторизоваться введи пароль:</code>',
        reply_markup=await get_restore_password_keyboard(),
    )


@router.callback_query(
    InitialState.TO_REGISTRATION,
    F.data == 'to_registration'
)
@delete_prev_messages_and_update_state
async def register_user_handler(query: CallbackQuery, state: FSMContext):

    await state.set_state(RegState.INPUT_FIRST_NAME)

    return await query.message.answer('<code>Введите имя:</code>')


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
        RegState.INPUT_EMAIL,
        'Введите актуальную почту (email). Он будет использоваться для восстановления доступа в магазин.',
        'Пожалуйста, введите свою настоящую фамилию.',
        r'[А-Яа-яA-Za-z\s]{1,50}',
        'last_name'
    )


@router.message(
    RegState.INPUT_EMAIL,
)
async def input_email(message: Message, state: FSMContext) -> Optional[Message]:
    return await validate_user_registration(
        message,
        state,
        RegState.INPUT_PASSWORD,
        'Придумайте и запишите пароль. Он будет использоваться для входа в магазин.',
        'Пожалуйста, введите существующую почту.',
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'email'
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
@delete_prev_messages_and_update_state
async def confirm_registration(message: Message, state: FSMContext) -> Message:
    data = await state.get_data()

    tg_id = message.from_user.id
    first_name = data.get('first_name', 'John')
    last_name = data.get('last_name', 'Doe')
    password = data.get('password')
    email = data.get('email')
    password_confirmation = data.get('password_confirmation')

    pwd_matched = await password_matched(password, password_confirmation)

    if not pwd_matched:
        return await message.answer('<code>Упс, пароли не совпадают... Может вы опечатались?</code>')

    r_cli = await connect_redis_url()
    now = int(time.time())

    try:
        await message.chat.delete_message(message_id=message.message_id)
    except aiogram.exceptions.TelegramBadRequest:
        pass

    try:
        async with PostgresAsyncSession() as session:
            async with session.begin() as transaction:
                user_id = await Users.create_user(tg_id, first_name, last_name, email, session)
                credentials = Credentials(user_id=user_id)
                await credentials.set_password(password)
                await credentials.set_auth_hash()
                session.add(credentials)
                await session.commit()
    except sqlalchemy.exc.SQLAlchemyError:
        await transaction.rollback()
        return await message.answer('<code>Упс, что-то пошло не так...</code>')
    else:
        await r_cli.hset(f'auth_hash:{tg_id}', mapping={
            'hash': credentials.auth_hash,
            'last_seen': now,
        })

        return await message.answer('<code>Успешная регистрация!</code>', reply_markup=await main_menu_markup())


@router.message(
    RegState.CONFIRM_REGISTRATION,
    F.text == 'Нет',
)
async def refuse_registration(message: Message, state: FSMContext) -> Message:
    bot_message = await message.answer('<code>Очень жаль... может быть /start в другой раз?</code>')

    await state.update_data({'last_bot_msg_id': bot_message.message_id})

    return bot_message


@router.message(
    InitialState.TO_AUTHENTICATION
)
@delete_prev_messages_and_update_state
async def authenticate_user(message: Message, state: FSMContext) -> Optional[Message]:

    tg_id = message.from_user.id
    pwd = message.text

    try:
        await message.chat.delete_message(message_id=message.message_id)
    except aiogram.exceptions.TelegramBadRequest:
        ...

    if not re.match(r'[\w!@#$&\(\)\\-]{8,16}', pwd):

        return await message.answer(
            '<code>У вас ошибка при вводе парооя, может вы опечатались? Попробуйте еще раз!</code>',
            reply_markup=await get_restore_password_keyboard()
        )

    try:
        async with PostgresAsyncSession() as session:
            async with session.begin() as transaction:
                try:
                    user_id = await Users.get_user_id(tg_id, session)
                except UserNotFound:
                    bot_message = await message.answer('<code>Упс, такого пользователя не существует...</code>')
                    await transaction.rollback()
                    return bot_message
                else:
                    credentials = await session.execute(select(Credentials).filter_by(user_id=user_id))
                    credentials = credentials.scalar()
                    pwd_matched = await credentials.check_password(pwd)

                    if not pwd_matched:

                        return await message.answer(
                            '<code>Увы, пароли не совпадают. Может вы опечатались?</code>',
                            reply_markup=await get_restore_password_keyboard(),
                        )

                    await credentials.set_auth_hash()

                    r_cli = await connect_redis_url()
                    await r_cli.hset(f'auth_hash:{tg_id}', mapping={
                        'hash': credentials.auth_hash,
                        'last_seen': credentials.last_seen,
                    })

                    await state.set_state(InitialState.TO_APPLICATION)

                    return await main_menu_handler(message, state)

    except sqlalchemy.exc.SQLAlchemyError:
        await transaction.rollback()
        return await message.answer('<code>Упс, что-то пошло не так...</code>')


@router.callback_query(
    F.data == 'restore_password'
)
@delete_prev_messages_and_update_state
async def restore_password_handler(query: CallbackQuery, state: FSMContext):

    tg_id = query.message.chat.id

    async with PostgresAsyncSession() as session:
        async with session.begin():

            select_stmt = select(Users.email).filter_by(tg_id=tg_id)

            result_stmt = await session.execute(select_stmt)

            email = result_stmt.scalar()

            if email is None:
                return await query.message.answer(
                    'Мы не смогли найти вашу почту. Пожалуйста, обратитесь в поддержку!',
                    reply_markup=await get_restore_password_keyboard(),
                )

    code = await generate_code_for_restoring_password()
    await state.update_data({'restore_pwd_code': code})
    await send_email(
        [email],
        'Восстановление пароля (Balance bot)',
        'Ты видишь это сообщение, потому что кто-то пытается восстановить доступ к твоему аккаунту!',
        template_name='account/restore_password.html',
        context=code,
    )

    await state.set_state(RestoreState.RESTORE_PASSWORD_INIT)

    return await query.message.answer('Мы отправили секретный код на указанную вами при регистрации почту.\n'
                                      'Введите код из письма:', reply_markup=await refuse_restore_password_keyboard())


@router.message(
    RestoreState.RESTORE_PASSWORD_INIT,
)
@delete_prev_messages_and_update_state
async def validate_restore_code_handler(message: Message, state: FSMContext):

    data = await state.get_data()

    restore_pwd_code = data.get('restore_pwd_code')
    user_wrote = message.text

    try:
        await message.chat.delete_message(message_id=message.message_id)
    except aiogram.exceptions.TelegramBadRequest:
        pass

    if restore_pwd_code != user_wrote:
        return await message.answer(
            'Вы ввели неверный код! Попробуете еще раз?',
            reply_markup=await get_restore_password_keyboard(),
        )

    await state.set_state(RestoreState.NEW_PASSWORD)
    return await message.answer('Введите новый пароль:')


@router.message(
    RestoreState.NEW_PASSWORD,
)
@delete_prev_messages_and_update_state
async def set_new_password_handler(message: Message, state: FSMContext):

    user_wrote = message.text

    if not re.match(r'[\w!@#$&\(\)\\-]{8,16}', user_wrote):
        return await message.answer('Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские '
                                 'буквы в верхнем и нижнем регистре, цифры, а также специальные символы.',
                                    reply_markup=await get_restore_password_keyboard()
                                    )

    await state.update_data({'restore_pwd': user_wrote})
    await state.set_state(RestoreState.NEW_PASSWORD_CONFIRMATION)
    return await message.answer(
        'Повторите введенный вами ранее пароль:',
        reply_markup=await get_restore_password_keyboard(),
    )


@router.message(
    RegState.INPUT_PASSWORD_CONFIRMATION,
)
@delete_prev_messages_and_update_state
async def confirm_new_password_handler(message: Message, state: FSMContext):

    user_wrote = message.text
    tg_id = message.from_user.id

    data = await state.get_data()

    if data and data.get('restore_pwd') == user_wrote:
        try:
            async with PostgresAsyncSession() as session:
                async with session.begin():
                    user_id = await Users.get_user_id(tg_id=tg_id, session=session)

                    credentials = await session.execute(
                        select(Credentials).filter_by(user_id=user_id)
                    )

                    credentials = credentials.scalar()
                    if credentials:
                        await credentials.set_password(password=user_wrote)
                        await credentials.set_auth_hash()
                        await session.commit()

                    await state.set_state(InitialState.TO_AUTHENTICATION)
                    return await message.answer('Пароль успешно обновлен!', reply_markup=await main_menu_markup())
        except sqlalchemy.exc.SQLAlchemyError:
            return await message.answer(
                'Упс, что-то пошло не так...',
                reply_markup=await get_restore_password_keyboard(),
            )

    return await message.answer(
        'Увы, введенные пароли не совпадают. Попробуете еще раз?',
        reply_markup=await get_restore_password_keyboard(),
    )

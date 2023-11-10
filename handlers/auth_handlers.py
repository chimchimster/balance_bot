import re

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from signals.signals import Signal
from states.states import InitialState, RegState
from keyboards.inline.auth_keyboards import *
from handlers.utils.auxillary import validate_user_registration

router = Router()


@router.message(CommandStart())
async def cmd_start_handler(message: Message, state: FSMContext, **kwargs):

    auth_state = kwargs.pop('auth_state')

    if not auth_state:
        return message.answer('Увы, что-то пошло не так...')

    match auth_state:
        case Signal.AUTHENTICATED:
            # to app handler
            ...
        case Signal.NOT_AUTHENTICATED:
            # to authentication handler
            ...
        case Signal.NOT_REGISTERED:

            await state.set_state(InitialState.TO_REGISTRATION)

            return message.answer('Продолжить регистрацию?', reply_markup=get_registration_keyboard())

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

    bot_msg = await query.message.answer('<code>Введите имя:</code>')

    await state.update_data({'last_bot_msg_id': bot_msg.message_id})


@router.message(
    RegState.INPUT_FIRST_NAME,
)
async def input_first_name(message: Message, state: FSMContext) -> None:

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
async def input_last_name(message: Message, state: FSMContext) -> None:

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
async def input_password(message: Message, state: FSMContext) -> None:

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
async def input_password_confirmation(message: Message, state: FSMContext) -> None:

    return await validate_user_registration(
        message,
        state,
        RegState.CONFIRM_REGISTRATION,
        'Подтвердить введенные данные?',
        'Допускается пароль длинною от 8 до 16 символов. Пароль может содержать латинские буквы в верхнем и '
        'нижнем регистре, цифры, а также специальные символы.',
        r'[\w!@#$&\(\)\\-]{8,16}',
        'password_confirmation'
    )


@router.message(
    RegState.CONFIRM_REGISTRATION,
)
async def confirm_registration(message: Message, state: FSMContext) -> None:
    print(message)
    print(await state.get_data())
    await message.answer('Вы успешно зарегистрированы!')

    return

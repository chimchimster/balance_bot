from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from conf import bot_settings


async def get_registration_keyboard() -> InlineKeyboardMarkup:

    register_button = InlineKeyboardButton(
        text='Продолжить регистрацию!',
        callback_data='to_registration'
    )

    exit_button = InlineKeyboardButton(
        text='Может быть в другой раз...',
        callback_data='exit'
    )

    support_button = InlineKeyboardButton(
        text='Обратиться в поддержку',
        url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [register_button],
        [exit_button],
        [support_button],
    ])

    return keyboard


async def get_restore_password_keyboard() -> InlineKeyboardMarkup:

    restore_password_button = InlineKeyboardButton(text='Восстановить пароль?', callback_data='restore_password')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [restore_password_button]
    ])

    return keyboard


async def refuse_restore_password_keyboard() -> InlineKeyboardMarkup:

    refuse_button = InlineKeyboardButton(text='В другой раз...', callback_data='refuse_operations')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [refuse_button],
    ])

    return keyboard


__all__ = ['get_registration_keyboard', 'get_restore_password_keyboard',]

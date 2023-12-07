from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from conf import bot_settings


async def get_registration_keyboard() -> InlineKeyboardMarkup:

    register_button = InlineKeyboardButton(
        text='Да, начинем!',
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


__all__ = ['get_registration_keyboard',]

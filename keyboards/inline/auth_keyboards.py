from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_registration_keyboard() -> InlineKeyboardMarkup:

    register_button = InlineKeyboardButton(
        text='Да, начинем!',
        callback_data='to_registration'
    )

    exit_button = InlineKeyboardButton(
        text='Может быть в другой раз...',
        callback_data='exit'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [register_button],
        [exit_button],
    ])

    return keyboard


async def get_authorization_keyboard():
    pass


__all__ = ['get_registration_keyboard', 'get_authorization_keyboard']

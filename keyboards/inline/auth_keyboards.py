from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_registration_keyboard() -> InlineKeyboardMarkup:

    register_button = InlineKeyboardButton(
        text='Зарегистрироваться',
        callback_data='to_registration'
    )

    exit_button = InlineKeyboardButton(
        text='Выйти',
        callback_data='exit'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [register_button],
        [exit_button],
    ])

    return keyboard


__all__ = ['get_registration_keyboard']

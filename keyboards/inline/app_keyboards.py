from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from callback_data.callback_data import PersonalOrdersCallbackData


async def main_menu_markup() -> InlineKeyboardMarkup:

    personal_button = InlineKeyboardButton(text='В личный кабинет', callback_data='personal_account')
    purchase_button = InlineKeyboardButton(text='К покупкам', callback_data='purchases')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [personal_button],
        [purchase_button],
    ])

    return keyboard


async def personal_account_markup() -> InlineKeyboardMarkup:

    orders_button = InlineKeyboardButton(text='Все заказы', callback_data='orders')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [orders_button],
    ])

    return keyboard

__all__ = ['main_menu_markup',]

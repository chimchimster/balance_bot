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

    orders_button = InlineKeyboardButton(text='К заказам', callback_data='orders')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [orders_button],
    ])

    return keyboard


async def bought_items_markup(has_next: bool, has_prev: bool) -> InlineKeyboardMarkup:

    buttons = []

    if has_prev:
        prev_button = InlineKeyboardButton(text='Назад', callback_data=PersonalOrdersCallbackData(flag=False).pack())
        buttons.append(prev_button)

    if has_next:
        next_button = InlineKeyboardButton(text='Вперед', callback_data=PersonalOrdersCallbackData(flag=True).pack())
        buttons.append(next_button)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    return keyboard

__all__ = ['main_menu_markup', 'bought_items_markup',]

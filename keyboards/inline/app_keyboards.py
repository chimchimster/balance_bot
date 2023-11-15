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

    orders_button = InlineKeyboardButton(text='Мои заказы', callback_data='orders')
    show_addresses = InlineKeyboardButton(text='Мои адреса', callback_data='show_addresses')
    add_address = InlineKeyboardButton(text='Добавить адрес доставки', callback_data='add_address')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [orders_button],
        [show_addresses],
        [add_address],
    ])

    return keyboard


async def bought_items_markup(has_next: bool, has_prev: bool) -> InlineKeyboardMarkup:

    buttons = []

    back_to_main_menu = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    if has_prev:
        prev_button = InlineKeyboardButton(text='Назад', callback_data=PersonalOrdersCallbackData(flag=False).pack())
        buttons.append(prev_button)

    if has_next:
        next_button = InlineKeyboardButton(text='Вперед', callback_data=PersonalOrdersCallbackData(flag=True).pack())
        buttons.append(next_button)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons, [back_to_main_menu]])

    return keyboard

__all__ = ['main_menu_markup', 'bought_items_markup',]

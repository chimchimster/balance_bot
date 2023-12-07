from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from callback_data.callback_data import PersonalOrdersCallbackData
from conf import bot_settings


async def main_menu_markup() -> InlineKeyboardMarkup:

    personal_button = InlineKeyboardButton(text='В личный кабинет', callback_data='personal_account')
    purchase_button = InlineKeyboardButton(text='К покупкам', callback_data='purchases')
    show_cart = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')
    support_button = InlineKeyboardButton(
        text='Обратиться в поддержку',
        url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [personal_button],
        [purchase_button],
        [show_cart],
        [support_button],
    ])

    return keyboard


async def personal_account_markup() -> InlineKeyboardMarkup:

    orders_button = InlineKeyboardButton(text='Мои заказы', callback_data='orders')
    show_addresses = InlineKeyboardButton(text='Мои адреса', callback_data='show_addresses')
    add_address = InlineKeyboardButton(text='Добавить адрес доставки', callback_data='add_address')

    show_cart_button = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')
    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')
    support_button = InlineKeyboardButton(
        text='Обратиться в поддержку',
        url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [orders_button],
        [show_addresses],
        [add_address],
        [show_cart_button],
        [support_button],
        [back_to_main_menu_button],
    ])

    return keyboard


async def bought_items_markup(has_next: bool, has_prev: bool, **kwargs) -> InlineKeyboardMarkup:

    buttons = []

    if has_prev:
        prev_button = InlineKeyboardButton(text='Назад', callback_data=PersonalOrdersCallbackData(flag=False).pack())
        buttons.append(prev_button)

    if has_next:
        next_button = InlineKeyboardButton(text='Вперед', callback_data=PersonalOrdersCallbackData(flag=True).pack())
        buttons.append(next_button)

    show_cart_button = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')
    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    support_button = InlineKeyboardButton(
        text='Обратиться в поддержку',
        url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [show_cart_button],
            [support_button],
            [back_to_main_menu_button],
        ]
    )

    return keyboard


async def back_to_account_markup() -> InlineKeyboardMarkup:

    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')
    back_to_personal_account_button = InlineKeyboardButton(text='Вернуться в личный кабинет', callback_data='personal_account')
    show_cart_button = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')

    support_button = InlineKeyboardButton(
        text='Обратиться в поддержку',
        url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [back_to_personal_account_button],
        [show_cart_button],
        [support_button],
        [back_to_main_menu_button],
    ])

    return keyboard

__all__ = ['main_menu_markup', 'bought_items_markup',]

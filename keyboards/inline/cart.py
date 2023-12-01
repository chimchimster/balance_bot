from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def get_cart_keyboard(*args) -> InlineKeyboardMarkup:

    clean_cart_up_button = InlineKeyboardButton(text='Очистить корзину', callback_data='clean_cart_up')

    builder = InlineKeyboardBuilder()

    addresses_buttons = []
    for address in args:
        adr_button = builder.button(text=address[-1], callback_data='pick_address')
        addresses_buttons.append(adr_button)

    builder.adjust(3, 2)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[clean_cart_up_button]])
    builder.attach(InlineKeyboardBuilder.from_markup(keyboard))

    return builder.as_markup()

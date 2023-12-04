from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def get_cart_keyboard(addresses: dict, cart_has_items: bool = False) -> InlineKeyboardMarkup:

    clean_cart_up_button = InlineKeyboardButton(text='Очистить корзину', callback_data='clean_cart_up')

    pay_orders_button = InlineKeyboardButton(text='Перейти к оплате', callback_data='start_payment')

    builder = InlineKeyboardBuilder()

    for address_id, address in addresses.items():
        builder.button(
            text=address[1] + ', ' + address[2] + ', ' + address[3],
            callback_data=f'pick_address:{address_id}',
        )

    builder.adjust(1, 1)

    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [pay_orders_button] if cart_has_items else [],
            [clean_cart_up_button],
            [back_to_main_menu_button],
        ]
    )
    builder.attach(InlineKeyboardBuilder.from_markup(keyboard))

    return builder.as_markup()

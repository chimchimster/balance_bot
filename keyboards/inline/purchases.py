from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


async def get_search_filter_keyboard(
        brand: str = None,
        size: str = None,
        color: str = None,
        sex: str = None,
) -> InlineKeyboardMarkup:

    brand_button = InlineKeyboardButton(text='Любой бренд' if not brand else brand, callback_data='choose_brand')
    color_button = InlineKeyboardButton(text='Любой цвет' if not color else color, callback_data='choose_color')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [brand_button, color_button],
    ])

    return keyboard

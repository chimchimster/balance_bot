from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


async def get_search_filter_keyboard(
        brand: str = None,
        size: str = None,
        color: str = None,
        sex: str = None,
) -> InlineKeyboardMarkup:

    # Очень жаль, что так вышло :)
    if sex is not None:
        male_or_female = sex.lower().split('.')[-1]
        if male_or_female.startswith('m'):
            sex = 'М'
        elif male_or_female.startswith('f'):
            sex = 'Ж'

    brand_button = InlineKeyboardButton(text='Любой бренд' if not brand else brand, callback_data='choose_brand')
    size_button = InlineKeyboardButton(text='Любой размер' if not size else size, callback_data='choose_size')
    sex_button = InlineKeyboardButton(text='Любой пол' if not sex else sex, callback_data='choose_sex')
    color_button = InlineKeyboardButton(text='Любой цвет' if not color else color, callback_data='choose_color')
    apply_filters_button = InlineKeyboardButton(text='Применить фильтры', callback_data='apply_filters')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [brand_button, size_button],
        [sex_button, color_button],
        [apply_filters_button],
    ])

    return keyboard

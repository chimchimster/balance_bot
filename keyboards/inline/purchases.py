from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from callback_data.callback_data import AvailableItemsCallbackData


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


async def items_markup(has_next: bool, has_prev: bool) -> InlineKeyboardMarkup:

    buttons = []

    back_to_main_menu = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    if has_prev:
        prev_button = InlineKeyboardButton(text='Назад', callback_data=AvailableItemsCallbackData(flag=False).pack())
        buttons.append(prev_button)

    if has_next:
        next_button = InlineKeyboardButton(text='Вперед', callback_data=AvailableItemsCallbackData(flag=True).pack())
        buttons.append(next_button)

    add_to_cart_button = InlineKeyboardButton(text='Добавить в корзину', callback_data='add_to_cart')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons, [back_to_main_menu], [add_to_cart_button]])

    return keyboard

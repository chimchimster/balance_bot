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

    show_cart_button = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')
    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [brand_button, size_button],
        [sex_button, color_button],
        [apply_filters_button],
        [show_cart_button],
        [back_to_main_menu_button],
    ])

    return keyboard


async def items_markup(has_next: bool, has_prev: bool, **kwargs) -> InlineKeyboardMarkup:

    pagination_buttons = []

    back_to_main_menu_button = InlineKeyboardButton(text='Вернуться в главное меню', callback_data='back_to_main_menu')

    if has_prev:
        prev_button = InlineKeyboardButton(text='Назад', callback_data=AvailableItemsCallbackData(flag=False).pack())
        pagination_buttons.append(prev_button)

    if has_next:
        next_button = InlineKeyboardButton(text='Вперед', callback_data=AvailableItemsCallbackData(flag=True).pack())
        pagination_buttons.append(next_button)

    update_cart = kwargs.get('update_cart')

    add_to_cart_button = InlineKeyboardButton(
        text='Добавлено в корзину ⭐' + ' ' + str(update_cart) if update_cart > 0 else 'Добавить в корзину',
        callback_data='add_to_cart',
    )

    delete_from_cart_button = InlineKeyboardButton(text='Убрать из корзины', callback_data='delete_from_cart')

    current_filter = kwargs.get('current_filter')

    filter_title = ''
    if current_filter:

        for key, value in current_filter.items():
            if value != 'Без фильтра':
                if key == 'size':
                    filter_title += 'размер: ' + value.split(',')[-1]
                if key == 'sex':
                    filter_title += 'пол: ' + ('М' if value.split('.')[-1].lower().startswith('m') else 'Ж') + ', '
                if key == 'color':
                    filter_title += 'цвет: ' + value.split(',')[-1] + ', '

    if filter_title == '':
        filter_title = 'без фильтров'
    else:
        filter_title = filter_title.lower()

    current_filter_button = InlineKeyboardButton(text=filter_title, callback_data='purchases')

    show_cart_button = InlineKeyboardButton(text='Моя корзина', callback_data='show_cart')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            pagination_buttons,
            [add_to_cart_button],
            [delete_from_cart_button] if update_cart > 0 else [],
            [current_filter_button],
            [show_cart_button],
            [back_to_main_menu_button],
        ]
    )

    return keyboard

from aiogram.filters.callback_data import CallbackData


class PersonalOrdersCallbackData(CallbackData, prefix='ordered_items'):
    flag: bool


class AvailableItemsCallbackData(CallbackData, prefix='items'):
    flag: bool

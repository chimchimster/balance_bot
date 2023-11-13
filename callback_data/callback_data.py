from aiogram.filters.callback_data import CallbackData


class PersonalOrdersCallbackData(CallbackData, prefix='personal_orders'):
    offset: int

from aiogram.fsm.state import State, StatesGroup


class InitialState(StatesGroup):
    TO_REGISTRATION = State()
    TO_AUTHENTICATION = State()
    TO_APPLICATION = State()


class RegState(StatesGroup):
    INPUT_FIRST_NAME = State()
    INPUT_LAST_NAME = State()
    INPUT_PASSWORD = State()
    INPUT_PASSWORD_CONFIRMATION = State()
    CONFIRM_REGISTRATION = State()


class SetNewAddressState(StatesGroup):
    REGION = State()
    CITY = State()
    STREET = State()
    APARTMENT = State()
    PHONE = State()

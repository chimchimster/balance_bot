from aiogram.fsm.state import State, StatesGroup


class AuthState(StatesGroup):
    AUTHENTICATED = State()
    NOT_AUTHENTICATED = State()
    NOT_REGISTERED = State()


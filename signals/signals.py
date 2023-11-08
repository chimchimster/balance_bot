import enum


class Signal(enum.Enum):

    NOT_REGISTERED = 1
    NOT_AUTHENTICATED = 2
    AUTHENTICATED = 3

    UNKNOWN_ERROR = 900
    DATABASE_ERROR = 901
import enum


class Signal(enum.Enum):

    NOT_REGISTERED = 1
    NOT_AUTHENTICATED = 2
    REGISTERED = 3
    AUTHENTICATED = 4

    UNKNOWN_ERROR = 900
    DATABASE_ERROR = 901

    def name(self):
        return self.value

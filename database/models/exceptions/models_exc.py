class UserNotFound(Exception):
    pass


class IncorrectInput(Exception):
    pass


class AddressNotFound(Exception):
    pass


__all__ = [
    'UserNotFound',
    'IncorrectInput',
    'AddressNotFound',
]
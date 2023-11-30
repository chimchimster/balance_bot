from decimal import Decimal
from typing import Any


class RedisSerializer:
    def __init__(self, struct: dict):
        self._struct = struct

    async def __call__(self, *args, **kwargs):

        for key, value in self._struct.items():
            if not isinstance(value, (int, float, str)):
                self._struct[key] = await self.__serialize(value)

        return self._struct

    @staticmethod
    async def __serialize(value: Any):
        """ Дополняется по мере необходимости. """

        if isinstance(value, Decimal):
            return float(value)
        ...

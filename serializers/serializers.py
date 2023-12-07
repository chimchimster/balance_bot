from decimal import Decimal
from enum import Enum
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

        if isinstance(value, Enum):
            return value.name
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            return str(value)
        if isinstance(value, list):
            serialized_value = []
            for v in value:
                new_val = await RedisSerializer.__serialize(v)
                serialized_value.append(new_val)

            return serialized_value


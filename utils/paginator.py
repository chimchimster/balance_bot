import asyncio
from typing import List


class Paginator:
    def __init__(
            self,
            struct: List[int]
    ) -> None:
        self._struct = struct
        self._current = -1
        self._direction = True

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        self._direction = value

    def __iter__(self):
        return self

    def __next__(self):
        if self._direction:
            self._current += 1
            if self.has_next():
                return self._struct[self._current]
        else:
            if self.has_prev():
                self._current -= 1
                return self._struct[self._current]

        if 0 <= self._current < len(self._struct):
            return self._struct[self._current]
        else:
            raise StopIteration

    def has_next(self) -> bool:

        return self._current < len(self._struct) - 1

    def has_prev(self) -> bool:

        return self._current > 0


class PaginatorStorage:

    def __init__(self):
        self.storage = {}
        self.lock = asyncio.Lock()

    async def __aenter__(self):
        await self.lock.acquire()

    def __setitem__(self, key, value):
        self.storage[key] = value

    def __getitem__(self, item):
        if item is not None:
            return self.storage.get(item)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

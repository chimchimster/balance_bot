from typing import List


class Paginator:
    def __init__(
            self,
            struct: List
    ) -> None:
        self._struct = struct
        self._current = -1
        self._flag = None

    @property
    def flag(self):
        return self._flag

    @flag.setter
    def flag(self, value):
        self._flag = value

    def __iter__(self):
        return self

    def __next__(self):

        if self._flag is None:
            return None

        if self._flag:
            self._current += 1
        else:
            self._current -= 1

        if self.has_next():
            return self._struct[self._current]
        else:
            raise StopIteration

    def has_next(self) -> bool:

        return 0 <= self._current < len(self._struct)

    def has_prev(self) -> bool:

        return self._current > 0

from typing import Optional

from handlers.utils.named_entities import Item


class Cart:

    _instances = {}

    def __new__(cls, *args, **kwargs):
        if args[0] not in cls._instances:
            cls._instances[args[0]] = super().__new__(*args, **kwargs)

        return cls._instances[args[0]]

    def __init__(self, tg_id: int):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._tg_id = tg_id
            self._items = []

    async def add_item(self, item: Item) -> None:
        self._items.append(item)

    async def remove_item(self, item: Item) -> Optional[int]:
        try:
            self._items.remove(item)
        except ValueError:
            return -1

    async def calculate_sum_of_items(self) -> int:
        return sum(item.price for item in self._items)

    async def clean_up(self):
        self._items.clear()

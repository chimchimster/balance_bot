from typing import Optional, Union, Dict

from handlers.utils.named_entities import Item


class Cart:
    def __init__(self, tg_id: int):
        self._tg_id = tg_id
        self._items = []

    async def add_item(self, item: Item) -> None:
        self._items.append(item)

    async def get_item(self, item_id: int):

        for item in self._items:
            if item.get('id') == item_id:
                return item

        return -1

    async def remove_item(self, item: dict) -> Optional[int]:
        try:

            item_id = item.get('id')

            for item in self._items:
                if item.get('id') == item_id:
                    self._items.remove(item)
                    break
        except ValueError:
            return -1

    async def calculate_sum_of_items(self) -> int:
        return round(sum(item.get('price', 0) for item in self._items), 2)

    async def clean_up(self):
        self._items.clear()

    async def fill_up(self, previous_data):
        if previous_data is not None:
            self._items = previous_data

    @property
    async def get_items(self) -> list:
        return self._items


class CartManager:

    _carts = {}

    @classmethod
    async def get_cart(cls, tg_id: int) -> Cart:
        if tg_id not in cls._carts:
            cls._carts[tg_id] = Cart(tg_id)
        return cls._carts[tg_id]

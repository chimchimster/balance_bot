from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

from cart.cart import CartManager
from middlewares.settings import CART_OVERFLOW


class CartIsFullFiledMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
            event: CallbackQuery,
            data: Dict[str, Any]
    ):

        tg_id = event.message.chat.id

        cart = await CartManager.get_cart(tg_id)

        query_text = event.data

        items = await cart.get_items

        if items and len(items) >= CART_OVERFLOW and query_text == 'add_to_cart':
            return await event.answer(
                text='Ваша корзина переполнена. Пожалуйста, удалите элементы корзины либо оплатите, '
                     'чтобы продолжить покупки.'
            )
        else:
            return await handler(event, data)

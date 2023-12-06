from typing import Callable, Awaitable, Dict, Any, Union

from aiogram import BaseMiddleware
from aiogram.types import Message

from middlewares.utils.state import check_auth_state


class AuthUserMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ):

        auth_state = await check_auth_state(event)

        if auth_state:

            data['auth_state'] = auth_state

            return await handler(event, data)







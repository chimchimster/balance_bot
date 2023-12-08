from typing import Callable, Awaitable, Dict, Any, Union

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery

from keyboards.inline.auth import get_registration_keyboard
from middlewares.utils.state import check_auth_state
from signals.signals import Signal
from states.states import InitialState


class AuthUserMiddleware(BaseMiddleware):

    def __init__(self, storage: RedisStorage):
        super().__init__()
        self._storage = storage

    async def __call__(
            self,
            handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any],
    ):

        auth_state = await check_auth_state(event)
        print(auth_state)
        state = FSMContext(
            storage=self._storage,
            key=StorageKey(
                bot_id=event.bot.id,
                chat_id=event.from_user.id if isinstance(event, Message) else event.message.chat.id,
                user_id=event.from_user.id if isinstance(event, Message) else event.from_user.id
            )
        )

        bot_message = None
        match auth_state:
            case Signal.AUTHENTICATED:

                await state.set_state(InitialState.TO_APPLICATION)

            case Signal.NOT_AUTHENTICATED:

                await state.set_state(InitialState.TO_AUTHENTICATION)

                if isinstance(event, Message) and event.text and event.text.startswith('/'):
                    bot_message = await event.answer(
                        f'<code>Привет, {event.from_user.username}!\n\nЧтобы авторизоваться введи пароль:</code>')
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    return await handler(event, data)

            case Signal.NOT_REGISTERED:

                await state.set_state(InitialState.TO_REGISTRATION)

                if isinstance(event, Message) and event.text and event.text.startswith('/'):
                    bot_message = await event.answer(
                        f'<code>Привет, {event.from_user.username}\n\nЧтобы начать пользоваться нашим магазином нужно '
                        f'зарегистрироваться.\n\nЭто займет совсем немного времени, начнем?</code>',
                        reply_markup=await get_registration_keyboard())
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    return await handler(event, data)

            case _:
                # 500 server error
                bot_message = await event.answer('<code>Возникла ошибка 404!</code>')

                return bot_message

        return await handler(event, data)

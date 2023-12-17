from typing import Callable, Awaitable, Dict, Any, Union

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery

from handlers.auth import authenticate_user, restore_password_handler, validate_restore_code_handler, \
    restore_password_confirmation_handler
from keyboards.inline.auth import get_registration_keyboard, get_restore_password_keyboard
from middlewares.utils.state import check_auth_state
from signals.signals import Signal
from states.states import InitialState, RestoreState


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

        if isinstance(event, Message):
            event_type = event
        else:
            event_type = event.message

        match auth_state:
            case Signal.AUTHENTICATED:

                await state.set_state(InitialState.TO_APPLICATION)

            case Signal.NOT_AUTHENTICATED:

                if event_type.reply_markup and event_type.reply_markup.inline_keyboard:
                    inline_button = event_type.reply_markup.inline_keyboard[0][0]

                    if inline_button.callback_data == 'restore_password':

                        return await restore_password_handler(event, state)

                curr_state = await state.get_state()

                if curr_state == RestoreState.RESTORE_PASSWORD_INIT:
                    return await validate_restore_code_handler(event_type, state)
                elif curr_state == RestoreState.NEW_PASSWORD:
                    return await restore_password_handler(event_type, state)
                elif curr_state == RestoreState.NEW_PASSWORD_CONFIRMATION:
                    return await restore_password_confirmation_handler(event_type, state)
                elif curr_state == InitialState.TO_AUTHENTICATION:
                    return await authenticate_user(event_type, state)
                else:
                    await state.set_state(InitialState.TO_AUTHENTICATION)

                    bot_message = await event_type.answer(
                        f'<code>Привет, {event.from_user.username}!\n\nЧтобы авторизоваться введи пароль:</code>',
                        reply_markup=await get_restore_password_keyboard(),
                    )
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message

            case Signal.NOT_REGISTERED:

                await state.set_state(InitialState.TO_REGISTRATION)

                if isinstance(event, Message) and event.text and event.text.startswith('/'):
                    bot_message = await event.answer(
                        f'<code>Привет, {event.from_user.username}\n\nЧтобы начать пользоваться нашим магазином нужно '
                        f'зарегистрироваться.\n\nЭто займет совсем немного времени, начнем?</code>',
                        reply_markup=await get_registration_keyboard(),
                    )
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    return await handler(event, data)

            case _:
                # 500 server error
                bot_message = await event.answer('<code>Возникла ошибка 404!</code>')

                return bot_message

        return await handler(event, data)

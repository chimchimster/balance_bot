from typing import Callable, Awaitable, Dict, Any, Union

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from conf import bot_settings
from handlers.auth import *
from keyboards.inline.auth import get_registration_keyboard, get_restore_password_keyboard
from middlewares.utils.state import check_auth_state
from signals.signals import Signal
from states.states import InitialState, RestoreState
from utils.jinja_template import render_template


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

        state = FSMContext(
            storage=self._storage,
            key=StorageKey(
                bot_id=event.bot.id,
                chat_id=event.from_user.id if isinstance(event, Message) else event.message.chat.id,
                user_id=event.from_user.id if isinstance(event, Message) else event.from_user.id
            )
        )
        print(auth_state, await state.get_state())

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

                    if inline_button.callback_data == 'refuse_operations':

                        return await refuse_restore_operations_handler(event, state)

                curr_state = await state.get_state()

                if curr_state == RestoreState.RESTORE_PASSWORD_INIT:
                    return await validate_restore_code_handler(event_type, state)
                elif curr_state == RestoreState.NEW_PASSWORD:
                    return await set_new_password_handler(event_type, state)
                elif curr_state == RestoreState.NEW_PASSWORD_CONFIRMATION:
                    return await confirm_new_password_handler(event_type, state)
                elif curr_state == InitialState.TO_AUTHENTICATION:
                    return await authenticate_user(event_type, state)
                else:
                    if isinstance(event, Message) and event.text and event.text.startswith('/'):
                        await state.set_state(InitialState.TO_AUTHENTICATION)
                        html = await render_template('auth/welcome_auth.html')
                        bot_message = await event_type.answer(
                            text=html,
                            reply_markup=await get_restore_password_keyboard(),
                        )
                        await state.update_data({'last_bot_msg_id': bot_message.message_id})
                        return bot_message
                    else:
                        return await handler(event, data)

            case Signal.NOT_REGISTERED:

                await state.set_state(InitialState.TO_REGISTRATION)

                if isinstance(event, Message) and event.text and event.text.startswith('/'):
                    html = await render_template(template_name='auth/welcome_reg.html')
                    bot_message = await event.answer(
                        text=html,
                        reply_markup=await get_registration_keyboard(),
                    )
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    return await handler(event, data)
            case _:
                html = await render_template(template_name='errors/common.html')
                bot_message = await event.answer(
                    text=html,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text='Обратиться в поддержку',
                            url=f'https://t.me/{bot_settings.support_username.get_secret_value()}'
                        )]
                    ])
                )

                return bot_message

        return await handler(event, data)

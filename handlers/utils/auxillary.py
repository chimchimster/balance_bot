import re

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from states.states import RegState


async def validate_user_registration(
        message: Message,
        state: FSMContext,
        state_to_set: State,
        info_msg: str,
        err_msg: str,
        regex_pattern: str,
        key_name: str,
) -> None:

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id:
        await message.chat.delete_message(message_id=last_bot_msg_id)

    msg_txt = message.text

    if not re.match(regex_pattern, msg_txt):
        last_bot_msg = await message.answer(f'<code>{err_msg}</code>')

        await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})

        return

    await state.update_data({key_name: msg_txt})
    await state.set_state(state_to_set)
    await message.chat.delete_message(message_id=message.message_id)

    last_bot_msg = await message.answer(f'<code>{info_msg}</code>')

    await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})

    curr_state = await state.get_state()

    if curr_state == RegState.CONFIRM_REGISTRATION:

        button_yes = KeyboardButton(text='<code>Да</code>')
        button_no = KeyboardButton(text='<code>Нет</code>')
        keyboard = ReplyKeyboardMarkup(keyboard=[[button_yes, button_no]])

        await message.answer('Подтвердить введенные данные?', reply_markup=keyboard)
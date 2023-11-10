import re

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


async def validate_user_registration(
        message: Message,
        state: FSMContext,
        state_to_set: State,
        info_msg: str,
        err_msg: str,
        regex_pattern: str,
        key_name: str,
        end: bool = False,
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

    if not end:
        last_bot_msg = await message.answer(f'<code>{info_msg}</code>')
    else:
        button_yes = KeyboardButton(text='Да')
        button_no = KeyboardButton(text='Нет')

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[button_yes], [button_no]], resize_keyboard=True)

        last_bot_msg = await message.answer(f'<code>{info_msg}</code>', reply_markup=keyboard)

    await state.update_data({'last_bot_msg_id': last_bot_msg.message_id})


async def password_matched(password: str, password_confirmation: str) -> bool:

    if not any([password, password_confirmation]):
        return False

    if password != password_confirmation:
        return False
    return True

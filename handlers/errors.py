from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.utils.auxillary import delete_prev_messages_and_update_state
from keyboards.inline.app import main_menu_markup

router = Router()


@router.message()
@delete_prev_messages_and_update_state
async def handle_404(message: Message, state: FSMContext):

    return await message.answer(
        '<code>Запрашиваемые вами данные не найдены, пожалуйста, обратитесь в поддержку!</code>',
        reply_markup=await main_menu_markup()
    )





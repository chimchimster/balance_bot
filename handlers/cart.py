from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(
    F.data == 'show_cart',
)
async def show_cart_handler(query: CallbackQuery, state: FSMContext):

    pass

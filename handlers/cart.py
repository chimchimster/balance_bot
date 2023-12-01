import sqlalchemy.exc
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import select

from cart.cart import CartManager
from database.models.schemas.auth import Addresses, Users
from database.session import AsyncSessionLocal
from utils.jinja_template import render_template
from keyboards.inline.cart import get_cart_keyboard

router = Router()


@router.callback_query(
    F.data == 'show_cart',
)
async def show_cart_handler(query: CallbackQuery, state: FSMContext):

    tg_id = query.message.chat.id
    data = await state.get_data()

    addresses = data.get('shipping_addresses')

    if addresses is None:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():

                    select_stmt = select(
                        Addresses.id,
                        Addresses.street,
                    ).join(Users).filter(Users.tg_id == tg_id)

                    result_stmt = await session.execute(select_stmt)

                    addresses = result_stmt.fetchall()

        except sqlalchemy.exc.SQLAlchemyError:
            bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
            await state.update_data({'last_bot_msg': bot_message.message_id})

    cart_items = data.get('in_cart')

    cart = await CartManager.get_cart(tg_id)
    await cart.fill_up(cart_items)
    items = await cart.get_items
    total_price = await cart.calculate_sum_of_items()

    html = await render_template('cart/cart_detail.html', cart=items, total_price=total_price)

    bot_message = await query.message.answer(text=html, reply_markup=await get_cart_keyboard(*addresses))

    await state.update_data({'last_bot_msg_id': bot_message.message_id})


@router.callback_query(
    F.data == 'clean_cart_up',
)
async def clean_cart_up(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

    await state.update_data({'in_cart': []})

    await show_cart_handler(query, state)


@router.callback_query(
    F.data == 'pick_address',
)
async def pick_address_handler(query: CallbackQuery, state: FSMContext):

    pass
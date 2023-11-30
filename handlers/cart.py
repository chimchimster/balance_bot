from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from cart.cart import CartManager
from utils.jinja_template import render_template

router = Router()


@router.callback_query(
    F.data == 'show_cart',
)
async def show_cart_handler(query: CallbackQuery, state: FSMContext):

    tg_id = query.message.chat.id
    data = await state.get_data()

    cart_items = data.get('in_cart')

    cart = await CartManager.get_cart(tg_id)
    await cart.fill_up(cart_items)
    items = await cart.get_items
    print(items)
    html = await render_template('cart/cart_detail.html', cart=items)
    print(html)
    await query.message.answer(text=html)

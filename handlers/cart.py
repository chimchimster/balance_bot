import aiogram.exceptions
import sqlalchemy.exc
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.methods import EditMessageText
from aiogram.types import CallbackQuery
from sqlalchemy import select

from cart.cart import CartManager
from database.models.schemas.auth import Addresses, Users
from database.session import AsyncSessionLocal
from utils.jinja_template import render_template
from keyboards.inline.cart import get_cart_keyboard
from handlers.utils.auxillary import delete_prev_messages_and_update_state
from bot import bot as balance_bot

router = Router()


@router.callback_query(
    F.data == 'show_cart',
)
@delete_prev_messages_and_update_state
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
                        Addresses.country,
                        Addresses.city,
                        Addresses.street,
                        Addresses.apartment,
                        Addresses.phone,
                    ).join(Users).filter(Users.tg_id == tg_id)

                    result_stmt = await session.execute(select_stmt)

                    addresses = result_stmt.fetchall()
                    addresses = {tpl[0]: tpl[1:] for tpl in addresses}

                    await state.update_data({'shipping_addresses': addresses})

        except sqlalchemy.exc.SQLAlchemyError:
            return await query.message.answer('<code>Упс, что-то пошло не так...</code>')

    cart_items = data.get('in_cart')

    cart = await CartManager.get_cart(tg_id)
    await cart.fill_up(cart_items)
    items = await cart.get_items
    total_price = await cart.calculate_sum_of_items()

    current_address = data.get('current_address')

    if current_address is None:
        current_address = 'не выбран'

    html = await render_template(
        'cart/cart_detail.html',
        cart=items,
        total_price=total_price,
        current_shipping_address=', '.join(current_address) if current_address != 'не выбран' else 'не выбран',
    )

    return await query.message.answer(text=html, reply_markup=await get_cart_keyboard(
            addresses,
            cart_has_items=True if items else False,
        )
    )


@router.callback_query(
    F.data == 'clean_cart_up',
)
@delete_prev_messages_and_update_state
async def clean_cart_up(query: CallbackQuery, state: FSMContext):

    await state.update_data({'in_cart': []})

    return await show_cart_handler(query, state)


@router.callback_query(
    F.data.startswith('pick_address'),
)
async def pick_address_handler(query: CallbackQuery, state: FSMContext):

    picked_address_id = query.data.split(':')[-1]
    tg_id = query.message.chat.id

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    shipping_addresses = data.get('shipping_addresses')

    cart_items = data.get('in_cart')

    if shipping_addresses is not None:
        # Ошибка при обработке shipping address
        current_address = shipping_addresses[picked_address_id]
        await state.update_data({'current_address': current_address, 'current_address_id': picked_address_id})

        cart = await CartManager.get_cart(tg_id)
        await cart.fill_up(cart_items)
        items = await cart.get_items
        total_price = await cart.calculate_sum_of_items()

        html = await render_template(
            'cart/cart_detail.html',
            cart=items,
            total_price=total_price,
            current_shipping_address=', '.join(current_address) if current_address != 'не выбран' else 'не выбран',
        )

        try:
            await EditMessageText(
                text=html,
                message_id=last_bot_msg_id,
                chat_id=query.message.chat.id,
                reply_markup=await get_cart_keyboard(shipping_addresses)
            ).as_(balance_bot)
            await query.answer(f'Выбран адрес доставки: {", ".join(current_address)}')
        except aiogram.exceptions.TelegramBadRequest:
            await query.answer('Указанный адрес уже выбран в качестве адреса доставки!')

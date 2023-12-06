import json
import aiogram
import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, PreCheckoutQuery, ShippingQuery, Message
from sqlalchemy import insert, update

from bot import bot as balance_bot
from balance_bot.cart.cart import CartManager
from database.models.schemas.auth import Users
from database.models.schemas.commerce import Orders, OrderItem
from database.session import AsyncSessionLocal
from keyboards.inline.app import main_menu_markup
from handlers.utils.auxillary import group_order, delete_prev_messages_and_update_state
from handlers.options import shipping_options
from states.states import PaymentsState
from conf import bot_settings

router = Router()


@router.callback_query(
    F.data == 'start_payment'
)
@delete_prev_messages_and_update_state
async def start_payment_handler(query: CallbackQuery, state: FSMContext):

    await state.set_state(PaymentsState.START_PAYMENT)

    tg_id = query.message.chat.id

    data = await state.get_data()

    in_cart = data.get('in_cart')
    cart = await CartManager.get_cart(tg_id)
    await cart.fill_up(in_cart)

    total_cost = await cart.calculate_sum_of_items()

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                user_id = await Users.get_user_id(tg_id, session)

                insert_stmt = insert(Orders).values(user_id=user_id).returning(Orders.id)

                result_stmt = await session.execute(insert_stmt)

                order_id = result_stmt.scalar()

                if order_id is not None:

                    order_items = [
                        {
                            'order_id': order_id,
                            'item_id': item.get('id'),
                            'color': item.get('color') if item.get('color') != 'Без фильтра' else None,
                            'size': item.get('size') if item.get('size') != 'Без фильтра' else None,
                            'sex': item.get('sex') if item.get('sex') != 'Без фильтра' else None,
                        }
                        for item in await cart.get_items if item.get('id') is not None
                    ]

                    grouped_order_items = await group_order(order_items)

                    values_to_insert = [
                        {**dict(order_item), 'qty': qty}
                        for order_item, qty in grouped_order_items.items()
                    ]

                    insert_stmt = insert(OrderItem).values(values_to_insert)

                    await session.execute(insert_stmt)

    except sqlalchemy.exc.SQLAlchemyError:
        return await query.message.answer('<code>Упс, что-то пошло не так...</code>', reply_markup=await main_menu_markup())

    payload = f'{{"user_id": {user_id}, "order_id": {order_id}}}'

    return await balance_bot.send_invoice(
        query.message.chat.id,
        title=f'Оплата заказа №{order_id}',
        description=f'Заказ в магазине Balance. Номер заказа №{order_id}',
        provider_token=bot_settings.payment_provider_token.get_secret_value(),
        currency='rub',
        prices=[aiogram.types.LabeledPrice(label=f'Заказ №{order_id}', amount=int(total_cost * 10))],
        payload=payload,
    )


@router.shipping_query()
async def shipping_handler(shipping_query: ShippingQuery):
    await balance_bot.answer_shipping_query(
        shipping_query.id,
        ok=True,
        shipping_options=shipping_options,
        error_message='Что-то пошло не так?',
    )


@router.pre_checkout_query()
async def checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await balance_bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message="Что-то пошло не так?",
    )


@router.message(F.successful_payment)
async def payment_success_handler(message: Message, state: FSMContext):

    payload_str = message.successful_payment.invoice_payload
    payload_dict = json.loads(payload_str)

    user_id = payload_dict.get('user_id')
    order_id = payload_dict.get('order_id')

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                if user_id and order_id:
                    update_stmt = update(Orders).where(
                        Orders.user_id == user_id, Orders.id == order_id
                    ).values(paid=True)

                    await session.execute(update_stmt)
                else:
                    raise sqlalchemy.exc.SQLAlchemyError

    except sqlalchemy.exc.SQLAlchemyError:
        # Нужно придумать как поступать в данной ситуации.
        # Идея: возможно нужно пользователю выдавать айди заказа с которым он мог бы обратиться в поддержку.
        ...

    await balance_bot.send_message(message.chat.id, f'Спасибо за оплату заказа №{order_id}!')



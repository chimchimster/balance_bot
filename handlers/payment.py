import json
import aiogram
import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, PreCheckoutQuery, ShippingQuery, Message
from sqlalchemy import insert, update, select, desc

from bot import bot as balance_bot
from apps.cart.cart import CartManager
from database.models.schemas.auth import Users, Addresses
from database.models.schemas.commerce import Orders, OrderItem
from database.session import AsyncSessionLocal
from keyboards.inline.app import main_menu_markup, personal_account_markup
from handlers.utils.auxillary import group_order, delete_prev_messages_and_update_state
from handlers.utils.options import shipping_options
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
                            'sex': item.get('sex').split('.')[-1] if item.get('sex') != 'Без фильтра' else None,
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
        prices=[aiogram.types.LabeledPrice(label=f'Заказ №{order_id}', amount=int(total_cost * 100))],
        payload=payload,
        is_flexible=True,
    )


@router.shipping_query()
async def shipping_handler(shipping_query: ShippingQuery, state: FSMContext):

    tg_id = shipping_query.from_user.id
    print(tg_id)
    country = shipping_query.shipping_address.country_code
    city = shipping_query.shipping_address.city
    city_state = shipping_query.shipping_address.state
    street = shipping_query.shipping_address.street_line1
    apartment = shipping_query.shipping_address.street_line2
    post_code = shipping_query.shipping_address.post_code

    data = await state.get_data()

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                user_id_subquery = select(Users.id).filter_by(tg_id=tg_id).scalar_subquery()

                insert_stmt = insert(Addresses).values(
                    user_id=user_id_subquery,
                    country=country,
                    city=city,
                    street=street,
                    apartment=apartment,
                    state=city_state,
                    post_code=post_code,
                ).returning(
                    Addresses.id,
                    Addresses.country,
                    Addresses.city,
                    Addresses.street,
                    Addresses.apartment,
                    Addresses.phone
                )

                address = await session.execute(insert_stmt)
                address = address.fetchone()

                shipping_addresses = {**data.get('shipping_addresses'), address[0]: address[1:]}

                await state.update_data(
                    {
                        'current_address_id': address[0],
                        'current_address': address[1:],
                        'shipping_addresses': shipping_addresses,
                    }
                )

    except sqlalchemy.exc.IntegrityError:

        user_id_subquery = select(Users.id).filter_by(tg_id=tg_id).scalar_subquery()

        select_stmt = select(
            Addresses.id,
            Addresses.country,
            Addresses.city,
            Addresses.street,
            Addresses.apartment,
            Addresses.phone,
        ).filter_by(
            user_id=user_id_subquery
        ).order_by(
            desc(
                Addresses.id
            )
        )

        address = await session.execute(select_stmt)
        address = address.first()

        shipping_addresses = {**data.get('shipping_addresses'), address[0]: address[1:]}

        await state.update_data(
            {
                'current_address_id': address[0],
                'current_address': address[1:],
                'shipping_addresses': shipping_addresses,
            }
        )

    except sqlalchemy.exc.SQLAlchemyError:
        return await balance_bot.send_message(text='<code>Упс, что-то пошло не так...</code>', reply_markup=await main_menu_markup())

    return await balance_bot.answer_shipping_query(
        shipping_query.id,
        ok=True,
        shipping_options=shipping_options,
        error_message='Что-то пошло не так?',
    )


@router.pre_checkout_query()
async def checkout_handler(pre_checkout_query: PreCheckoutQuery):
    return await balance_bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message="Что-то пошло не так?",
    )


@router.message(F.successful_payment)
@delete_prev_messages_and_update_state
async def payment_success_handler(message: Message, state: FSMContext):

    payload_str = message.successful_payment.invoice_payload
    payload_dict = json.loads(payload_str)

    user_id = payload_dict.get('user_id')
    order_id = payload_dict.get('order_id')

    data = await state.get_data()

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                if message.successful_payment:
                    if user_id is not None and order_id is not None:
                        update_stmt = update(Orders).where(
                            Orders.user_id == user_id, Orders.id == order_id
                        ).values(paid=True)

                        await session.execute(update_stmt)
                    else:
                        raise sqlalchemy.exc.SQLAlchemyError

                curr_address_id = data.get('current_address_id')

                if curr_address_id is not None:

                    update_stmt = update(OrderItem).filter(
                        OrderItem.order_id == order_id
                    ).values(address_id=curr_address_id)

                    await session.execute(update_stmt)

                else:

                    select_stmt = select(Addresses.id).filter_by(user_id=user_id).order_by(desc(Addresses.id))

                    last_address_id = await session.execute(select_stmt).first()

                    last_address_id = last_address_id[0] if last_address_id else None

                    if last_address_id is not None:

                        update_stmt = update(OrderItem).filter(
                            OrderItem.order_id == order_id
                        ).values(address_id=last_address_id)

                        await session.execute(update_stmt)
                    else:
                        return await balance_bot.send_message(
                            text='<code>Вы не можете оплачивать покупки пока не добавите адрес доставки. '
                                 'Сделать это можно в личном кабинете.</code>',
                            reply_markup=await personal_account_markup()
                        )

    except sqlalchemy.exc.SQLAlchemyError as e:
        print(e)
        # Нужно придумать как поступать в данной ситуации.
        # Идея: возможно нужно пользователю выдавать айди заказа с которым он мог бы обратиться в поддержку.
        ...

    return await balance_bot.send_message(
        message.chat.id,
        f'Спасибо за оплату заказа №{order_id}!',
        reply_markup=await main_menu_markup(),
    )

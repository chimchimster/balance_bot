import aiogram
import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import insert

from bot import bot as balance_bot
from balance_bot.cart.cart import CartManager
from database.models.schemas.auth import Users
from database.models.schemas.commerce import Orders, OrderItem
from database.session import AsyncSessionLocal
from keyboards.inline.app import main_menu_markup
from states.states import PaymentsState
from conf import bot_settings

router = Router()


@router.callback_query(
    F.data == 'start_payment'
)
async def start_payment_handler(query: CallbackQuery, state: FSMContext):

    await state.set_state(PaymentsState.START_PAYMENT)

    tg_id = query.message.chat.id

    data = await state.get_data()

    in_cart = data.get('in_cart')
    cart = await CartManager.get_cart(tg_id)
    await cart.fill_up(in_cart)

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                user_id = await Users.get_user_id(tg_id, session)

                insert_stmt = insert(Orders).values(user_id=user_id).returning(Orders.id)

                result_stmt = await session.execute(insert_stmt)

                order_id = result_stmt.scalar()

                if order_id is not None:

                    values_to_order_item = [
                        {
                            'order_id': order_id,
                            'item_id': item.get('id'),
                            'color': item.get('color') if item.get('color') != 'Без фильтра' else None,
                            'size': item.get('size') if item.get('size') != 'Без фильтра' else None,
                            'sex': item.get('sex') if item.get('sex') != 'Без фильтра' else None,
                        }
                        for item in await cart.get_items if item.get('id') is not None
                    ]

                    insert_stmt = insert(OrderItem).values(values_to_order_item)

                    await session.execute(insert_stmt)
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(e)
        return await query.message.answer('<code>Упс, что-то пошло не так...</code>', reply_markup=await main_menu_markup())

    await balance_bot.send_invoice(
        query.message.chat.id,
        title='Тестовая оплата',
        description='Подтверждение тестовой оплаты',
        provider_token=bot_settings.payment_provider_token.get_secret_value(),
        currency='rub',
        prices=[aiogram.types.LabeledPrice(label='Some Label', amount=10000)],
        payload='SOME PAYLOAD',
    )


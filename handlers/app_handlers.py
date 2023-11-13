import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from sqlalchemy import select
from sqlalchemy.sql.functions import count, func

from callback_data.callback_data import PersonalOrdersCallbackData
from database.models.exceptions.models_exc import UserNotFound
from keyboards.inline.app_keyboards import *
from database.models import *
from states.states import InitialState, PersonalState
from balance_bot.utils.jinja_template import render_template
from database.session import AsyncSessionLocal

router = Router()


@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):

    await state.clear()

    html = await render_template('main_menu.html')

    await message.answer(text=html, reply_markup=await main_menu_markup())


@router.callback_query(
    F.data == 'personal_account',
)
async def personal_account_handler(query: CallbackQuery, state: FSMContext):

    # first_name, last_name

    tg_id = query.message.from_user.id

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin() as transaction:

                try:
                    data = await session.execute(
                        select(
                            Users.first_name,
                            Users.last_name,
                            count(Orders.id),
                            func.sum(Items.price)
                        )
                        .join(Orders, Orders.user_id == Users.id)
                        .join(OrderItem)
                        .join(Items)
                        .group_by(Users.first_name, Users.last_name)
                        .filter(Users.tg_id == tg_id)
                    )
                    print(data.fetchall())
                except UserNotFound:
                    bot_message = await query.message.answer('<code>Пользователь не найден</code>')
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    pass
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(e)
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message


@router.callback_query(
    F.data == PersonalOrdersCallbackData,
)
async def all_orders_handler(query: CallbackQuery, state: FSMContext):

    # orders_count, addresses, last_order, show_all_orders

    tg_id = query.message.from_user.id

    try:
        async with (AsyncSessionLocal() as session):
            async with session.begin() as transaction:

                select_stmt = select(
                    Users.first_name,
                    Users.last_name,
                    Items.title,
                    Items.description,
                    Items.price,
                    Brands.title,
                    Images.path,
                ).join(Orders, Orders.user_id == Users.id
                       ).join(OrderItem
                              ).join(Items
                                     ).join(Brands
                                            ).join(ItemsImages
                                                   ).join(Images
                                                          ).filter(Users.tg_id == tg_id)

                stmt_result = await session.execute(select_stmt)
                orders = stmt_result.fetchall()
                await session.commit()
    except sqlalchemy.exc.SQLAlchemyError:

        await transaction.rollback()

        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')

        await query.message.chat.delete_message(message_id=bot_message.message_id)

        return bot_message


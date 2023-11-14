from typing import List

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
from keyboards.inline.app_keyboards import personal_account_markup
from states.states import InitialState, PersonalState
from balance_bot.utils.jinja_template import render_template
from database.session import AsyncSessionLocal
from utils.paginator import Paginator

router = Router()


@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):
    await state.clear()

    html = await render_template('menu/main_menu.html')

    await message.answer(text=html, reply_markup=await main_menu_markup())


@router.callback_query(
    F.data == 'personal_account',
)
async def personal_account_handler(query: CallbackQuery, state: FSMContext):
    tg_id = query.message.chat.id

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():

                try:
                    stmt_result = await session.execute(
                        select(
                            Users.id,
                            Users.first_name,
                            Users.last_name,
                            count(Orders.id.distinct()),
                            func.sum(Items.price)
                        )
                        .join(Orders, Orders.user_id == Users.id)
                        .join(OrderItem)
                        .join(Items)
                        .filter(Users.tg_id == tg_id)
                        .group_by(Users.id)
                    )

                    data = stmt_result.fetchone()

                    if data is not None:
                        user_id, first_name, last_name, total_orders_count, total_orders_price = data
                    else:
                        raise UserNotFound

                    await state.update_data({'user_id': user_id, 'first_name': first_name, 'last_name': last_name})
                except UserNotFound:
                    bot_message = await query.message.answer('<code>Пользователь не найден</code>')
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message
                else:
                    html = await render_template(
                        'account/personal_account.html',
                        first_name=first_name,
                        last_name=last_name,
                        orders_count=total_orders_count,
                        orders_sum=total_orders_price,
                    )

                    bot_message = await query.message.answer(text=html, reply_markup=await personal_account_markup())
                    await state.update_data({'last_bot_msg_id': bot_message.message_id})
                    return bot_message

    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message


@router.callback_query(
    F.data == 'orders',
)
async def all_orders_handler(query: CallbackQuery, state: FSMContext):

    # orders_count, addresses, last_order, show_all_orders

    data = await state.get_data()

    user_id = data.get('user_id')

    if user_id is None:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt_result = await session.execute(
                    select(
                        Items.title,
                        Items.description,
                        Items.price,
                        Brands.title,
                        Images.path
                    ).select_from(Orders)
                    .join(OrderItem)
                    .join(Items)
                    .join(Brands)
                    .join(ItemsImages)
                    .join(Images)
                    .filter(Orders.user_id == user_id)
                )

                data = stmt_result.fetchmany(100)

                if data:
                    await paginate_over_bought_items(
                        query.message,
                        PersonalOrdersCallbackData(flag=True),
                        data,
                    )
                else:
                    pass

    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await query.message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message


async def paginate_over_bought_items(
        message: Message,
        callback_data: PersonalOrdersCallbackData,
        struct,
):

    flag = callback_data.flag

    paginator = Paginator(struct, flag)

    html = render_template('account/item_detail.html', )

    await message.answer()
    print(paginator.__next__())



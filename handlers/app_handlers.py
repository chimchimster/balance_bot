import ctypes
import re
from typing import Union

import sqlalchemy.exc

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardMarkup, KeyboardButton

from sqlalchemy import select
from sqlalchemy.sql.functions import count, func

from callback_data.callback_data import PersonalOrdersCallbackData
from database.models.exceptions.models_exc import UserNotFound
from keyboards.inline.app_keyboards import *
from database.models import *
from keyboards.inline.app_keyboards import personal_account_markup
from states.states import InitialState, SetNewAddressState
from balance_bot.utils.jinja_template import render_template
from database.session import AsyncSessionLocal
from utils.paginator import Paginator, PaginatorStorage
from handlers.utils.named_entities import *

router = Router()
paginator_storage = PaginatorStorage()


async def send_main_manu(obj: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()

    html = await render_template('menu/main_menu.html')

    if isinstance(obj, Message):

        await obj.answer(text=html, reply_markup=await main_menu_markup())
    else:

        await obj.message.answer(text=html, reply_markup=await main_menu_markup())


@router.message(
    InitialState.TO_APPLICATION,
)
async def main_menu_handler(message: Message, state: FSMContext):
    await send_main_manu(message, state)


@router.callback_query(
    F.data == 'back_to_main_menu'
)
async def main_menu_callback_handler(query: CallbackQuery, state: FSMContext):
    await send_main_manu(query, state)


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

    tg_id = query.message.chat.id
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

                paginator = Paginator(data)

                async with paginator_storage:
                    paginator_storage[tg_id] = paginator

                if data:
                    await paginate_over_bought_items(query, state)
                else:
                    # empty orders list template rendering
                    pass
    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await query.message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message


@router.callback_query(
    F.data.in_(
        [
            PersonalOrdersCallbackData(flag=True).pack(),
            PersonalOrdersCallbackData(flag=False).pack()
        ]
    )
)
async def paginate_over_bought_items(
        query: CallbackQuery,
        state: FSMContext,
):
    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')
    last_bot_msg_photo_id = data.get('last_bot_msg_photo_id')

    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

    if last_bot_msg_photo_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_photo_id)

    tg_id = query.message.chat.id

    async with paginator_storage:
        paginator = paginator_storage[tg_id]

    c_data = query.data
    if c_data == 'orders':
        c_data = PersonalOrdersCallbackData(flag=True)
        flag = c_data.flag
    else:
        flag = True if c_data.split(':')[-1] == '1' else False

    paginator.direction = flag

    paginator_value = BoughtItem(*next(paginator))

    html = await render_template(
        'account/item_detail.html',
        item_title=paginator_value.item_title,
        item_description=paginator_value.item_description,
        item_price=paginator_value.item_price,
        brand_name=paginator_value.brand_name.upper(),
    )

    has_next = paginator.has_next()
    has_prev = paginator.has_prev()

    bot_message_photo = await query.message.answer_photo(
        FSInputFile(paginator_value.image_path),
        caption=paginator_value.item_title,
    )
    bot_message = await query.message.answer(text=html, reply_markup=await bought_items_markup(has_next, has_prev))
    await state.update_data({
        'last_bot_msg_id': bot_message.message_id,
        'last_bot_msg_photo_id': bot_message_photo.message_id
    })


@router.callback_query(
    F.data == 'show_addresses',
)
async def show_addresses_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    user_id = data.get('user_id')

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt_result = await session.execute(
                    select(
                        Addresses.country,
                        Addresses.city,
                        Addresses.street,
                        Addresses.apartment,
                        Addresses.phone
                    ).filter_by(user_id=user_id)
                )

                data = [AddressItem(*args) for args in stmt_result.fetchall()]
                html = await render_template('account/personal_addresses.html', addresses=data)
                await query.message.answer(text=html)
    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await query.message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message


@router.callback_query(
    F.data == 'add_address',
)
async def add_address_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await query.message.chat.delete_message(message_id=bot_last_msg_id)

    await state.set_state(SetNewAddressState.REGION)

    button_ru = KeyboardButton(text='ru')
    button_kz = KeyboardButton(text='kz')

    keyboard = ReplyKeyboardMarkup(keyboard=[[button_ru, button_kz]])
    keyboard.resize_keyboard = True

    bot_message = await query.message.answer(text='Выберите регион', reply_markup=keyboard)
    await state.update_data({'bot_last_msg_id': bot_message.message_id})


@router.message(
    F.text.lower().in_(['ru', 'kz']),
    SetNewAddressState.REGION,
)
async def add_region_handler(message: Message, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await message.chat.delete_message(message_id=bot_last_msg_id)

    user_choice = message.text.upper()
    await state.update_data({'region': user_choice})
    await state.set_state(SetNewAddressState.CITY)
    bot_message = await message.answer(text='<code>Введите название города:</code>')
    await state.update_data({'bot_last_msg_id': bot_message.message_id})


@router.message(
    SetNewAddressState.CITY,
)
async def add_city_handler(message: Message, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await message.chat.delete_message(message_id=bot_last_msg_id)

    user_wrote = message.text
    if not re.match(r'[А-Яа-я\s]{5,50}', user_wrote):
        bot_message = await message.answer(
            text='<code>Название города не может быть меньше 5-ти символов и превышать 50 символов.</code>'
        )
        await state.update_data({'bot_last_msg_id': bot_message.message_id})
        return

    await state.update_data({'city': user_wrote})
    await state.set_state(SetNewAddressState.STREET)
    bot_message = await message.answer(text='<code>Введите название улицы:</code>')
    await state.update_data({'bot_last_msg_id': bot_message.message_id})


@router.message(
    SetNewAddressState.STREET,
)
async def add_street_handler(message: Message, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await message.chat.delete_message(message_id=bot_last_msg_id)

    user_wrote = message.text
    if not re.match(r'[А-Яа-я\s]{5,255}', user_wrote):
        bot_message = await message.answer(
            text='<code>Название улицы не может быть меньше 5-ти символов и превышать 255 символов.</code>'
        )
        await state.update_data({'bot_last_msg_id': bot_message.message_id})
        return

    await state.update_data({'street': user_wrote})
    await state.set_state(SetNewAddressState.APARTMENT)
    bot_message = await message.answer(text='<code>Введите дом и квартиру в формате дом-квартира.</code>')
    await state.update_data({'bot_last_msg_id': bot_message.message_id})


@router.message(
    SetNewAddressState.APARTMENT,
)
async def add_apartment_handler(message: Message, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await message.chat.delete_message(message_id=bot_last_msg_id)

    user_wrote = message.text
    if not re.match(r'[А-Яа-я\d]{1,10}', user_wrote):
        bot_message = message.answer(
            text='<code>Вы ввели менее одного и более 10 символов.</code>'
        )
        await state.update_data({'bot_last_msg_id': bot_message.message_id})
        return

    await state.update_data({'apartment': user_wrote})
    await state.set_state(SetNewAddressState.PHONE)
    bot_message = await message.answer(text='<code>Введите номер телефона в формате +79999999999:</code>')
    await state.update_data({'bot_last_msg_id': bot_message.message_id})


@router.message(
    SetNewAddressState.PHONE,
)
async def add_phone_handler(message: Message, state: FSMContext):

    data = await state.get_data()
    bot_last_msg_id = data.get('bot_last_msg_id')

    if bot_last_msg_id is not None:
        await message.chat.delete_message(message_id=bot_last_msg_id)

    user_wrote = message.text
    if not re.match(r'^(\+7|8)\d{7,10}$', user_wrote):
        bot_message = message.answer(
            text='<code>Допустимый формат номера телефона +79999999999.</code>'
        )
        await state.update_data({'bot_last_msg_id': bot_message.message_id})
        return

    await state.update_data({'phone_number': user_wrote})

    user_id = data.get('user_id')
    region = data.get('region')
    city = data.get('city')
    street = data.get('street')
    apartment = data.get('apartment')
    phone = data.get('phone')

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await Addresses.set_address(
                    user_id=user_id,
                    country=region,
                    city=city,
                    street=street,
                    apartment=apartment,
                    phone=phone,
                    session=session,
                )
                await session.commit()
    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await message.answer('<code>Упс, что-то пошло не так...</code>')
        await message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message


@router.message()
async def handle_404(message: Message):
    await message.answer('<code>Запрашиваемые вами данные не найдены, пожалуйста, обратитесь в поддержку!</code>')

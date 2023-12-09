import re
from typing import Awaitable

import sqlalchemy.exc
from aiogram.fsm.context import FSMContext

from sqlalchemy import select, or_, and_
from sqlalchemy.sql.functions import count, func, coalesce

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton

from database.models import *
from keyboards.inline.app import personal_account_markup, bought_items_markup, back_to_account_markup, main_menu_markup
from callback_data.callback_data import PersonalOrdersCallbackData
from database.models.exceptions.models_exc import UserNotFound
from states.states import SetNewAddressState
from database.session import AsyncSessionLocal
from handlers.utils.named_entities import Item, AddressItem
from handlers.utils.auxillary import paginate, delete_prev_messages_and_update_state
from utils.jinja_template import render_template
from utils.paginator import Paginator
from mem_storage import paginator_storage

router = Router()


@router.callback_query(
    F.data == 'personal_account',
)
@delete_prev_messages_and_update_state
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
                            coalesce(count(Orders.id.distinct()), 0),
                            coalesce(func.sum(Items.price), 0)
                        )
                        .outerjoin(Orders, and_(Orders.user_id == Users.id, Orders.paid.is_(True)))
                        .outerjoin(OrderItem)
                        .outerjoin(Items)
                        .filter(Users.tg_id == tg_id)
                        .group_by(Users.id, Users.first_name, Users.last_name)
                    )

                    data = stmt_result.fetchone()

                    if data is not None:
                        user_id, first_name, last_name, total_orders_count, total_orders_price = data
                    else:
                        raise UserNotFound
                    await state.update_data({'user_id': user_id, 'first_name': first_name, 'last_name': last_name})
                except UserNotFound:
                    return await query.message.answer('<code>Пользователь не найден</code>')
                else:
                    html = await render_template(
                        'account/personal_account.html',
                        first_name=first_name,
                        last_name=last_name,
                        orders_count=total_orders_count,
                        orders_sum=total_orders_price,
                    )

                    return await query.message.answer(text=html, reply_markup=await personal_account_markup())

    except sqlalchemy.exc.SQLAlchemyError:
        return await query.message.answer(
            '<code>Упс, что-то пошло не так...</code>',
            reply_markup=await main_menu_markup()
        )


@router.callback_query(
    F.data == 'orders',
)
@delete_prev_messages_and_update_state
async def all_orders_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    tg_id = query.message.chat.id
    user_id = data.get('user_id')

    if user_id is None:
        return await query.message.answer('<code>Упс, что-то пошло не так...</code>')
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt_result = await session.execute(
                    select(
                        Items.id,
                        Items.title,
                        Items.description,
                        Items.price,
                        Brands.title,
                        Images.path,
                    ).select_from(Orders)
                    .join(OrderItem)
                    .join(Items)
                    .join(ItemMeta)
                    .join(Brands)
                    .join(ItemsImages)
                    .join(Images)
                    .filter(Orders.user_id == user_id, Orders.paid.is_(True))
                )

                data = stmt_result.fetchmany(100)

                paginator = Paginator(data)

                async with paginator_storage:
                    paginator_storage[tg_id] = paginator

                if data:
                    return await paginate_over_bought_items(query, state)
                else:
                    return await query.message.answer(
                        text='<code>У вас пока что нет покупок в нашем магазине.</code>',
                        reply_markup=await personal_account_markup()
                    )
    except sqlalchemy.exc.SQLAlchemyError:
        return await query.message.answer('<code>Упс, что-то пошло не так...</code>',
                                          reply_markup=await main_menu_markup())


@router.callback_query(
    F.data.in_(
        [
            PersonalOrdersCallbackData(flag=True).pack(),
            PersonalOrdersCallbackData(flag=False).pack()
        ]
    )
)
@delete_prev_messages_and_update_state
async def paginate_over_bought_items(
        query: CallbackQuery,
        state: FSMContext,
) -> Awaitable:
    return await paginate(
        query,
        state,
        Item,
        'orders',
        PersonalOrdersCallbackData,
        'account/item_detail.html',
        bought_items_markup,
        paginator_storage,
    )


@router.callback_query(
    F.data == 'show_addresses',
)
@delete_prev_messages_and_update_state
async def show_addresses_handler(
        query: CallbackQuery,
        state: FSMContext,
) -> Message:
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

                if data:
                    html = await render_template('account/personal_addresses.html', addresses=data)
                    return await query.message.answer(text=html, reply_markup=await back_to_account_markup())
                else:
                    return await query.message.answer(
                        text='<code>У вас пока что нет ни одного добавленного адреса.</code>',
                        reply_markup=await back_to_account_markup()
                    )
    except sqlalchemy.exc.SQLAlchemyError:
        return await query.message.answer('<code>Упс, что-то пошло не так...</code>',
                                          reply_markup=await main_menu_markup())


@router.callback_query(
    F.data == 'add_address',
)
@delete_prev_messages_and_update_state
async def add_address_handler(
        query: CallbackQuery,
        state: FSMContext
) -> Message:
    await state.set_state(SetNewAddressState.REGION)

    button_ru = KeyboardButton(text='ru')
    button_kz = KeyboardButton(text='kz')

    keyboard = ReplyKeyboardMarkup(keyboard=[[button_ru, button_kz]])
    keyboard.resize_keyboard = True

    return await query.message.answer(text='Выберите регион', reply_markup=keyboard)


@router.message(
    F.text.lower().in_(['ru', 'kz']),
    SetNewAddressState.REGION,
)
@delete_prev_messages_and_update_state
async def add_region_handler(message: Message, state: FSMContext):
    await message.chat.delete_message(message_id=message.message_id)

    user_choice = message.text.upper()
    await state.update_data({'region': user_choice})
    await state.set_state(SetNewAddressState.CITY)
    return await message.answer(text='<code>Введите название города:</code>')


@router.message(
    SetNewAddressState.CITY,
)
@delete_prev_messages_and_update_state
async def add_city_handler(message: Message, state: FSMContext) -> Message:
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text
    if not re.match(r'[А-Яа-я\s]{5,50}', user_wrote):
        return await message.answer(
            text='<code>Название города не может быть меньше 5-ти символов и превышать 50 символов.</code>'
        )

    await state.update_data({'city': user_wrote})
    await state.set_state(SetNewAddressState.STREET)
    return await message.answer(text='<code>Введите название улицы:</code>')


@router.message(
    SetNewAddressState.STREET,
)
@delete_prev_messages_and_update_state
async def add_street_handler(message: Message, state: FSMContext) -> Message:
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text
    if not re.match(r'[А-Яа-я\s]{5,255}', user_wrote):
        return await message.answer(
            text='<code>Название улицы не может быть меньше 5-ти символов и превышать 255 символов.</code>'
        )

    await state.update_data({'street': user_wrote})
    await state.set_state(SetNewAddressState.APARTMENT)
    return await message.answer(text='<code>Введите дом и квартиру в формате дом-квартира.</code>')


@router.message(
    SetNewAddressState.APARTMENT,
)
@delete_prev_messages_and_update_state
async def add_apartment_handler(message: Message, state: FSMContext) -> Message:
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text if message.text else None

    if user_wrote is not None:
        if not re.match(r'[А-Яа-я\d]{1,50}', user_wrote):
            return await message.answer(
                text='<code>Вы ввели менее одного и более 50 символов.</code>'
            )

    await state.update_data({'apartment': user_wrote})
    await state.set_state(SetNewAddressState.STATE)
    return await message.answer(text='<code>Введите область.</code>')


@router.message(
    SetNewAddressState.STATE,
)
@delete_prev_messages_and_update_state
async def add_city_state_handler(message: Message, state: FSMContext) -> Message:
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text if message.text else None

    if user_wrote is not None:
        if not re.match(r'[А-Яа-я\d]{1,50}', user_wrote):
            return await message.answer(
                text='<code>Вы ввели менее одного и более 50 символов.</code>'
            )

    await state.update_data({'city_state': user_wrote})
    await state.set_state(SetNewAddressState.POST_CODE)
    return await message.answer(text='<code>Введите почтовый индекс.</code>')


@router.message(
    SetNewAddressState.POST_CODE,
)
@delete_prev_messages_and_update_state
async def add_post_code_handler(message: Message, state: FSMContext) -> Message:
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text if message.text else None

    if user_wrote is not None:
        if not re.match(r'[А-Яа-я\d]{1,50}', user_wrote):
            return await message.answer(
                text='<code>Вы ввели менее одного и более 50 символов.</code>'
            )

    await state.update_data({'post_code': user_wrote})
    await state.set_state(SetNewAddressState.PHONE)
    return await message.answer(text='<code>Введите номер телефона в формате +79999999999.</code>')


@router.message(
    SetNewAddressState.PHONE,
)
@delete_prev_messages_and_update_state
async def add_phone_handler(message: Message, state: FSMContext):
    await message.chat.delete_message(message_id=message.message_id)

    user_wrote = message.text
    if not re.match(r'^(\+7|8)\d{7,10}$', user_wrote):
        return await message.answer(
            text='<code>Допустимый формат номера телефона +79999999999.</code>'
        )

    await state.update_data({'phone': user_wrote})

    data = await state.get_data()

    user_id = data.get('user_id')
    region = data.get('region')
    city = data.get('city')
    street = data.get('street')
    apartment = data.get('apartment')
    city_state = data.get('city_state')
    post_code = data.get('post_code')
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
                    city_state=city_state,
                    post_code=post_code,
                    session=session,
                )
                await session.commit()

                return await message.answer(
                    text='<code>Адрес успешно добавлен!</code>',
                    reply_markup=await personal_account_markup(),
                )

    except sqlalchemy.exc.SQLAlchemyError:
        return await message.answer(
            text='<code>Упс, что-то пошло не так...</code>',
            reply_markup=await main_menu_markup(),
        )

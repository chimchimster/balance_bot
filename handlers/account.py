import re

import aiogram.exceptions
import sqlalchemy.exc
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from sqlalchemy.sql.functions import count, func

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardMarkup, KeyboardButton

from database.models import *
from keyboards.inline.app import personal_account_markup, bought_items_markup, back_to_account_markup
from callback_data.callback_data import PersonalOrdersCallbackData
from database.models.exceptions.models_exc import UserNotFound
from states.states import SetNewAddressState
from database.session import AsyncSessionLocal
from handlers.utils.named_entities import Item, AddressItem
from handlers.utils.auxillary import paginate
from utils.jinja_template import render_template
from utils.paginator import Paginator
from mem_storage import paginator_storage

router = Router()


@router.callback_query(
    F.data == 'personal_account',
)
async def personal_account_handler(query: CallbackQuery, state: FSMContext):
    tg_id = query.message.chat.id

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

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

    data = await state.get_data()

    tg_id = query.message.chat.id
    user_id = data.get('user_id')

    last_bot_msg_id = data.get('last_bot_msg_id')
    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

    if user_id is None:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message
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

    await paginate(
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
async def show_addresses_handler(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    user_id = data.get('user_id')

    last_bot_msg_id = data.get('last_bot_msg_id')
    last_bot_msg_photo_id = data.get('last_bot_msg_photo_id')

    if last_bot_msg_id is not None:
        try:
            await query.message.chat.delete_message(message_id=last_bot_msg_id)
        except aiogram.exceptions.TelegramBadRequest:
            ...

    if last_bot_msg_photo_id is not None:
        try:
            await query.message.chat.delete_message(message_id=last_bot_msg_photo_id)
        except aiogram.exceptions.TelegramBadRequest:
            ...

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
                bot_message = await query.message.answer(text=html, reply_markup=await back_to_account_markup())
                await state.update_data({'last_bot_msg_id': bot_message.message_id})

    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await query.message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message


@router.callback_query(
    F.data == 'add_address',
)
async def add_address_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    last_bot_msg_id = data.get('last_bot_msg_id')

    if last_bot_msg_id is not None:
        await query.message.chat.delete_message(message_id=last_bot_msg_id)

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
        bot_message = await message.answer(
            text='<code>Допустимый формат номера телефона +79999999999.</code>'
        )
        await state.update_data({'bot_last_msg_id': bot_message.message_id})
        return

    await state.update_data({'phone': user_wrote})

    data = await state.get_data()

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

                bot_message = await message.answer('<code>Адрес успешно добавлен!</code>')
                await state.update_data({'bot_last_msg_id': bot_message.message_id})
                return bot_message
    except sqlalchemy.exc.SQLAlchemyError:
        bot_message = await message.answer('<code>Упс, что-то пошло не так...</code>')
        await message.chat.delete_message(message_id=bot_message.message_id)
        return bot_message

import itertools
import pickle
import sqlalchemy.exc

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.methods import EditMessageReplyMarkup

from sqlalchemy import select

from database.session import AsyncSessionLocal
from database.models import *
from keyboards.inline.purchases import get_search_filter_keyboard

from bot import bot as balance_bot

router = Router()


@router.callback_query(
    F.data == 'purchases'
)
async def search_filter_handler(query: CallbackQuery, state: FSMContext):
    bot_message = await query.message.answer(text='<code>Выберте подходящие фильтры:</code>',
                                             reply_markup=await get_search_filter_keyboard())

    await state.update_data({'last_bot_msg_id': bot_message.message_id})

    return bot_message


@router.callback_query(
    F.data == 'choose_brand',
)
async def choose_brand_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    last_bot_msg_id = data.get('last_bot_msg_id')

    brand_filter = data.get('brand_filter')

    if not brand_filter:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    select_stmt = select(Brands.id, Brands.title)
                    brands = await session.execute(select_stmt)
                    brands = brands.fetchall()
                    await state.update_data(
                        {'brand_filter': ':'.join([','.join(tuple(map(str, brand))) for brand in brands])})
        except sqlalchemy.exc.SQLAlchemyError:
            bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
            await state.update_data({'last_bot_msg_id': bot_message.message_id})
    else:
        brands = [tuple(brand.split(',')) for brand in brand_filter.split(':')]

    prev_brand = data.get('current_brand')

    brands_gen = itertools.cycle(brands)
    current_brand = next(
        itertools.islice(brands_gen, int(prev_brand.split(',')[0]) if prev_brand is not None else 0, None), None
    )

    if current_brand:
        await state.update_data({'current_brand': ','.join(map(str, current_brand))})

        await EditMessageReplyMarkup(
            chat_id=query.message.chat.id, message_id=last_bot_msg_id,
            reply_markup=await get_search_filter_keyboard(brand=current_brand[-1])
        ).as_(balance_bot)


@router.callback_query(
    F.data == 'choose_color',
)
async def choose_size_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    last_bot_msg_id = data.get('last_bot_msg_id')

    size_filter = data.get('color_filter')

    if not size_filter:
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():

                    select_stmt = select(Colors.id, Colors.title)
                    colors = await session.execute(select_stmt)
                    colors = colors.fetchall()
                    await state.update_data({'color_filter': ':'.join([','.join(tuple(map(str, brand))) for brand in colors])})
        except sqlalchemy.exc.SQLAlchemyError:
            bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
            await state.update_data({'last_bot_msg_id': bot_message.message_id})
    else:
        colors = [tuple(brand.split(',')) for brand in size_filter.split(':')]

    prev_color = data.get('current_color')

    colors_gen = itertools.cycle(colors)

    current_color = next(
        itertools.islice(colors_gen, int(prev_color.split(',')[0]) if prev_color is not None else 0, None), None
    )

    if current_color:
        await state.update_data({'current_color': ','.join(map(str, current_color))})

        current_brand = data.get('current_brand')
        await EditMessageReplyMarkup(
            chat_id=query.message.chat.id, message_id=last_bot_msg_id,
            reply_markup=await get_search_filter_keyboard(brand=current_brand.split(',')[-1] if current_brand is not None else None, color=current_color[-1])
        ).as_(balance_bot)
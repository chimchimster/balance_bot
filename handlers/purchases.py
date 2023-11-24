from typing import Optional

import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from sqlalchemy import select, join, Text, text, TEXT, any_

from callback_data.callback_data import AvailableItemsCallbackData
from database.models import *
from database.session import AsyncSessionLocal
from handlers.utils.named_entities import Item
from keyboards.inline.purchases import get_search_filter_keyboard, items_markup
from handlers.utils.auxillary import filter_products, paginate
from balance_bot.utils.paginator import Paginator
from mem_storage import paginator_storage

router = Router()


@router.callback_query(
    F.data == 'purchases'
)
async def search_filter_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()

    bot_message = await query.message.answer(text='<code>Выберте подходящие фильтры:</code>',
                                             reply_markup=await get_search_filter_keyboard())

    await state.update_data({'last_bot_msg_id': bot_message.message_id})

    return bot_message


@router.callback_query(
    F.data == 'choose_brand',
)
async def choose_brand_handler(query: CallbackQuery, state: FSMContext):
    await filter_products('brand_filter', Brands, query, state)


@router.callback_query(
    F.data == 'choose_color',
)
async def choose_size_handler(query: CallbackQuery, state: FSMContext):
    await filter_products('color_filter', Colors, query, state)


@router.callback_query(
    F.data == 'choose_sex',
)
async def choose_sex_handler(query: CallbackQuery, state: FSMContext):
    await filter_products('sex_filter', Sex, query, state)


@router.callback_query(
    F.data == 'choose_size',
)
async def choose_size_handler(query: CallbackQuery, state: FSMContext):
    await filter_products('size_filter', Sizes, query, state)


@router.callback_query(
    F.data == 'apply_filters',
)
async def apply_filters_handler(query: CallbackQuery, state: FSMContext) -> Optional[Message]:
    tg_id = query.message.chat.id

    data = await state.get_data()

    color = data.get('current_color', '0,Без фильтра')
    brand = data.get('current_brand', '0,Без фильтра')
    sex = data.get('current_sex', '0,Без фильтра')
    size = data.get('current_size', '0,Без фильтра')

    await state.update_data({'current_filters': {'color': color, 'brand': brand, 'sex': sex, 'size': size}})

    size_title = size.split(',')[-1]
    color_title = color.split(',')[-1]
    sex_title = sex.split(',')[-1].split('.')[-1]
    brand_title = brand.split(',')[-1]

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                select_stmt = select(
                    Items.title,
                    Items.price,
                    Items.description,
                ).select_from(
                    join(Items, ItemsImages, Items.id == ItemsImages.item_id).
                    join(Images, ItemsImages.image_id == Images.id).
                    join(Brands, ItemsImages.item_id == Brands.id).
                    join(ItemMeta, ItemsImages.item_id == ItemMeta.item_id)
                ).where(
                    ItemMeta.size.contains([float(size_title)]) if size_title != 'Без фильтра' else text(''),
                    ItemMeta.color.contains([color_title]) if color_title != 'Без фильтра' else text(''),
                    ItemMeta.sex == sex_title if sex_title != 'Без фильтра' else text(''),
                    Brands.title == brand_title if brand_title != 'Без фильтра' else text('')
                )

                result = await session.execute(select_stmt)

                data = result.fetchall()

                paginator = Paginator(data)

                async with paginator_storage:
                    paginator_storage[tg_id] = paginator

                if data:
                    await paginate_over_items(query, state)
                else:
                    # message that there is no such items and show filters again
                    pass
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(e)
        bot_message = await query.message.answer('<code>Упс, что-то пошло не так...</code>')
        await state.update_data({'last_bot_msg_id': bot_message.message_id})
        return bot_message


@router.callback_query(
    F.data.in_(
        [
            AvailableItemsCallbackData(flag=True).pack(),
            AvailableItemsCallbackData(flag=False).pack()
        ]
    )
)
async def paginate_over_items(query: CallbackQuery, state: FSMContext):

    await paginate(
        query,
        state,
        Item,
        'apply_filters',
        AvailableItemsCallbackData,
        'account/item_detail.html',
        items_markup,
        paginator_storage,
    )


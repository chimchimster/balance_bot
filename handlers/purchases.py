import json
from typing import Optional, Dict

import sqlalchemy.exc
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.methods import EditMessageReplyMarkup
from aiogram.types import CallbackQuery, Message

from sqlalchemy import select, join, text

from callback_data.callback_data import AvailableItemsCallbackData
from cart.cart import CartManager, Cart
from database.models import *
from database.session import AsyncSessionLocal
from handlers.utils.named_entities import Item
from keyboards.inline.purchases import get_search_filter_keyboard, items_markup
from handlers.utils.auxillary import filter_products, paginate
from balance_bot.utils.paginator import Paginator
from mem_storage import paginator_storage
from balance_bot.bot import bot as balance_bot

router = Router()


@router.callback_query(
    F.data == 'purchases'
)
async def search_filter_handler(query: CallbackQuery, state: FSMContext):

    old_data = await state.get_data()

    await state.set_data({key: value for key, value in old_data.items() if key == 'in_cart'})

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
                    Items.id,
                    Items.title,
                    Items.description,
                    Items.price,
                    Brands.title,
                    Images.path,
                ).select_from(
                    join(Items, ItemsImages, Items.id == ItemsImages.item_id).
                    join(Images, ItemsImages.image_id == Images.id).
                    join(Brands, Items.brand_id == Brands.id).
                    join(ItemMeta, Items.id == ItemMeta.item_id)
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
    except sqlalchemy.exc.SQLAlchemyError:
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
async def paginate_over_items(
        query: CallbackQuery,
        state: FSMContext
):

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


@router.callback_query(
    F.data == 'add_to_cart'
)
async def add_to_cart_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    current_item = data.get('current_item')

    tg_id = query.message.chat.id
    cart: Cart = await CartManager.get_cart(tg_id)
    prev_cart_data = data.get('in_cart')
    await cart.fill_up(prev_cart_data)

    if current_item is not None:
        await cart.add_item(current_item)
        await update_cart_and_reply(query, state, cart, current_item)


@router.callback_query(
    F.data == 'delete_from_cart'
)
async def delete_from_cart_handler(query: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    current_item = data.get('current_item')

    tg_id = query.message.chat.id
    cart: Cart = await CartManager.get_cart(tg_id)
    prev_cart_data = data.get('in_cart')
    await cart.fill_up(prev_cart_data)

    if current_item is not None:
        await cart.remove_item(current_item)
        await update_cart_and_reply(query, state, cart, current_item)


async def update_cart_and_reply(query: CallbackQuery, state: FSMContext, cart: Cart, current_item: Dict):

    data = await state.get_data()

    last_bot_msg_id = data.get('last_bot_msg_id')

    has_next, has_prev = bool(data.get('has_next', False)), bool(data.get('has_prev', False))

    cart_items = await cart.get_items

    await state.update_data({'in_cart': cart_items})

    update_cart = len([value.get('id') for value in cart_items if value and value['id'] == current_item.get('id')])

    await EditMessageReplyMarkup(
        message_id=last_bot_msg_id,
        chat_id=query.message.chat.id,
        reply_markup=await items_markup(has_next, has_prev, update_cart=update_cart),
    ).as_(balance_bot)

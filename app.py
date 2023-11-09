import logging
from typing import Dict, Optional

from fastapi import FastAPI, Depends
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage

from conf import bot_settings
from database.handlers.utils.redis_client import connect_redis_url
from handlers.auth_handlers import router as auth_router


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = bot_settings.bot_token.get_secret_value()
WEBHOOK_PATH = f'/bot/{BOT_TOKEN}'
WEBHOOK_URL = f'https://{bot_settings.server_token.get_secret_value()}' + '.onrender.com' + WEBHOOK_PATH

bot = Bot(token=BOT_TOKEN)
app = FastAPI()


async def get_dispatcher(_bot: Bot = Depends(), _storage: RedisStorage = Depends()):
    return Dispatcher(bot=_bot, storage=_storage).include_routers(auth_router)


@app.on_event('startup')
async def on_startup(dispatcher: Dispatcher = Depends()):

    redis_connection = await connect_redis_url()

    storage = RedisStorage(redis_connection)
    dispatcher.storage = storage

    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(url=WEBHOOK_URL)


@app.post(WEBHOOK_PATH)
async def bot_webhook(update: Dict, dispatcher: Dispatcher = Depends(), _bot: Bot = Depends()):
    telegram_update = types.Update(**update)
    await dispatcher.feed_update(_bot, telegram_update)


@app.on_event('shutdown')
async def on_shutdown(_bot: Bot = Depends()):
    await _bot.session.close()

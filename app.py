import asyncio
import sys
import logging

from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from conf import bot_settings
from database.handlers.utils.redis_client import connect_redis_url
from handlers.auth_handlers import router as auth_router


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = bot_settings.bot_token.get_secret_value()
WEBHOOK_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={bot_settings.server_token.get_secret_value()}'


async def on_startup(bot: Bot) -> None:

    await bot.set_webhook(WEBHOOK_URL)


def main() -> None:

    async def get_redis_connection():
        return await connect_redis_url()

    loop = asyncio.new_event_loop()

    r_con = loop.run_until_complete(get_redis_connection())

    dp = Dispatcher(storage=RedisStorage(r_con))

    loop.close()

    dp.include_router(auth_router)

    dp.startup.register(on_startup)

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )

    webhook_requests_handler.register(app, path='')

    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=8000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()

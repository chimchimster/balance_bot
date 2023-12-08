import asyncio
import sys
import logging

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from conf import bot_settings
from database.handlers.setup import setup_database
from database.handlers.utils.redis_client import connect_redis_url
from handlers.auth import router as auth_router
from handlers.app import router as app_router
from handlers.account import router as account_router
from handlers.purchases import router as purchases_router
from handlers.cart import router as cart_router
from handlers.errors import router as error_router
from handlers.payment import router as payment_router
from middlewares.auth import AuthUserMiddleware

from bot import BOT_TOKEN, bot
from middlewares.cart import CartIsFullFiledMiddleware

SERVER_URL = bot_settings.server_token.get_secret_value()
WEBHOOK_URL = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={SERVER_URL}'


async def on_startup(bot: Bot) -> None:
    await setup_database()

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)


def main() -> None:
    loop = asyncio.new_event_loop()
    r_con = loop.run_until_complete(connect_redis_url())
    loop.close()

    redis_storage = RedisStorage(r_con)

    auth_middleware = AuthUserMiddleware(storage=redis_storage)
    cart_filled_middleware = CartIsFullFiledMiddleware()

    dp = Dispatcher(storage=redis_storage)
    dp.message.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(cart_filled_middleware)
    dp.include_routers(
        auth_router,
        app_router,
        account_router,
        purchases_router,
        cart_router,
        payment_router,
        error_router,
    )
    dp.startup.register(on_startup)

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )

    app = web.Application()
    webhook_requests_handler.register(app, path='')

    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=8000)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()

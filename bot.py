from aiogram import Bot
from aiogram.enums import ParseMode

from conf import bot_settings


BOT_TOKEN = bot_settings.bot_token.get_secret_value()

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
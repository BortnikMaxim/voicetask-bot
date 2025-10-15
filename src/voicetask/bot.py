from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
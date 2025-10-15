import asyncio
import os
import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from .bot import bot, dp
from .database.db import init_db
from .services.scheduler import start_scheduler, reschedule_all

from .handlers.commands import router as commands_router
from .handlers.text import router as text_router
from .handlers.voice import router as voice_router

logging.basicConfig(level=logging.INFO)

async def on_startup():
    await init_db()

    # Роутеры
    dp.include_router(commands_router)
    dp.include_router(voice_router)
    dp.include_router(text_router)

    # Команды в меню
    await bot.set_my_commands([
        BotCommand(command="start", description="Приветствие и помощь"),
        BotCommand(command="list", description="Показать активные задачи"),
        BotCommand(command="done", description="Отметить задачу выполненной: /done <id>"),
    ])

    # Планировщик
    start_scheduler()
    await reschedule_all()

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
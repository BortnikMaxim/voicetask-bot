# src/voicetask/main.py
import asyncio
import logging

from aiogram.types import BotCommand

from .bot import bot, dp
from .database.db import init_db
from .services.scheduler import notification_loop  # ⬅ наш фоновый цикл уведомлений

from .handlers.commands import router as commands_router
from .handlers.text import router as text_router
from .handlers.voice import router as voice_router
from .handlers.callbacks import router as callbacks_router  # ⬅ обработчики inline-кнопок

logging.basicConfig(level=logging.INFO)


async def on_startup():
    # В polling-режиме обязательно сбрасываем webhook
    await bot.delete_webhook(drop_pending_updates=True)

    # Инициализируем БД
    await init_db()

    # Подключаем роутеры (порядок важен только если есть конфликтующие фильтры)
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)  # ⬅ для done/snooze
    dp.include_router(voice_router)
    dp.include_router(text_router)

    # Команды в меню бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Приветствие и помощь"),
        BotCommand(command="list", description="Показать активные задачи"),
        BotCommand(command="done", description="Отметить задачу выполненной: /done <id>"),
    ])

    # Фоновая «тикалка» напоминаний (каждые 60 сек)
    asyncio.create_task(notification_loop(60))

    me = await bot.get_me()
    logging.info("Bot started as @%s (id=%s)", me.username, me.id)


async def main():
    await on_startup()
    # Явно перечисляем типы апдейтов, которые нам нужны
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
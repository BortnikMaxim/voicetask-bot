# src/voicetask/handlers/voice.py
import os
import tempfile
from datetime import datetime
from html import escape as html_escape

from aiogram import Router, F
from aiogram.types import Message

from ..services.whisper import transcribe_ogg_file
from ..services.parser import parse_task
from ..database.db import add_task, get_user_timezone
from ..bot import bot

router = Router()

@router.message(F.voice)
async def handle_voice(msg: Message):
    # скачиваем файл
    file = await bot.get_file(msg.voice.file_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    tmp_path = tmp.name
    tmp.close()
    await bot.download(file, destination=tmp_path)

    try:
        text = await transcribe_ogg_file(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass

    # парсинг с учётом TZ пользователя
    user_tz = await get_user_timezone(msg.chat.id)
    parsed = await parse_task(text, user_tz=user_tz)

    title = parsed.get("title", text[:120])
    priority = parsed.get("priority", "normal")
    due_date = parsed.get("due_date")
    due_time = parsed.get("due_time")

    due_at = None
    if due_date:
        if due_time:
            due_at = datetime.fromisoformat(f"{due_date}T{due_time}:00")
        else:
            from ..config import settings
            h, m = map(int, settings.TASK_DEFAULT_TIME.split(":"))
            due_at = datetime.fromisoformat(f"{due_date}T{h:02d}:{m:02d}:00")

    # сохраняем в БД — уведомления пришлёт наш фоновый цикл notification_loop
    task = await add_task(chat_id=msg.chat.id, title=title, priority=priority, due_at=due_at)

    due_text = f" на {due_at.strftime('%Y-%m-%d %H:%M')}" if due_at else ""
    await msg.answer(
        f"📝 Распознал: <i>{html_escape(text)}</i>\n"
        f"✅ Добавил задачу: <b>{html_escape(title)}</b>{due_text}\n"
        f"Приоритет: {priority}",
        parse_mode="HTML",
    )
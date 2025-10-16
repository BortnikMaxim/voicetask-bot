from __future__ import annotations

import os
import tempfile
from html import escape as html_escape
from aiogram import Router, F
from aiogram.types import Message

from ..services.whisper import transcribe_ogg_file
from ..services.parser import parse_task
from ..services.timezone import to_utc_naive, format_for_user  # ⬅️ NEW
from ..database.db import add_task, get_user_timezone
from ..keyboards import main_kb
from ..bot import bot

router = Router()


@router.message(F.voice)
async def handle_voice(msg: Message):
    # Скачиваем voice (OGG/Opus) во временный файл
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

    # Парсинг с учётом TZ пользователя
    user_tz = await get_user_timezone(msg.chat.id)
    parsed = await parse_task(text, user_tz=user_tz)

    title = parsed.get("title", text[:120])
    priority = parsed.get("priority", "normal")
    due_date = parsed.get("due_date")
    due_time = parsed.get("due_time")

    # ⬇️ локальное (польз.) → UTC (naive) перед сохранением
    due_at = to_utc_naive(due_date, due_time, user_tz) if due_date else None

    await add_task(chat_id=msg.chat.id, title=title, priority=priority, due_at=due_at)

    due_text = f" на {format_for_user(due_at, user_tz)}" if due_at else ""
    await msg.answer(
        f"📝 Распознал: <i>{html_escape(text)}</i>\n"
        f"✅ Добавил задачу: <b>{html_escape(title)}</b>{due_text}\n"
        f"Приоритет: {priority}",
        parse_mode="HTML",
        reply_markup=main_kb(),
    )
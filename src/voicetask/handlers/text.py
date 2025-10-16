from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from ..services.parser import parse_task
from ..database.db import add_task, get_user_timezone 
from ..services.scheduler import schedule_task

import html

router = Router()

@router.message(F.text)
async def handle_text(msg: Message):
    text = msg.text.strip()
    user_tz = await get_user_timezone(msg.chat.id)  # ← берём TZ пользователя (или None)
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
            h, m = map(int, settings.TASK_DEFAULT_TIME.split(":"))
            due_at = datetime.fromisoformat(f"{due_date}T{h:02d}:{m:02d}:00")

    task = await add_task(chat_id=msg.chat.id, title=title, priority=priority, due_at=due_at)

    due_text = f" на {due_at.strftime('%Y-%m-%d %H:%M')}" if due_at else ""
    await msg.answer(
        f"📝 Распознал: <i>{html.escape(text)}</i>\n"
        f"✅ Добавил задачу: <b>{html.escape(title)}</b>{due_text}\nПриоритет: {priority}"
    )
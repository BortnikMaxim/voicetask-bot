from ..keyboards import main_kb
from ..database.db import add_task, get_user_timezone, list_active  # ← list_active нужно
from ..config import settings
import html
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message

BUTTON_ADD = "➕ Добавить задачу"
BUTTON_LIST = "📅 Мои задачи"
BUTTON_SETTINGS = "⚙️ Настройки"

router = Router()

@router.message(F.text == BUTTON_LIST)
async def on_list(msg: Message):
    tasks = await list_active(msg.chat.id)
    if not tasks:
        return await msg.answer("Пока нет активных задач ✨")
    lines = []
    for t in tasks:
        when = t.due_at.strftime('%Y-%m-%d %H:%M') if t.due_at else "без срока"
        lines.append(f"<b>#{t.id}</b> — {html.escape(t.title)} · {when} · {t.priority}")
    await msg.answer("\n".join(lines))

@router.message(F.text == BUTTON_SETTINGS)
async def on_settings(msg: Message):
    await msg.answer("Настройки:\n/set_timezone Europe/Moscow — установить часовой пояс")

@router.message(F.text == BUTTON_ADD)
async def on_add_hint(msg: Message):
    await msg.answer("Пришли текст или голосовое: «Напомни завтра в 12 купить кофе»")

IGNORE = {BUTTON_ADD, BUTTON_LIST, BUTTON_SETTINGS}


@router.message(F.text and ~F.text.in_(IGNORE))
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
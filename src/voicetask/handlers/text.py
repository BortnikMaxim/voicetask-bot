from __future__ import annotations

import html
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove

from datetime import datetime
from ..keyboards import main_kb
from ..database.db import add_task, get_user_timezone, list_active
from ..services.parser import parse_task
from ..services.timezone import to_utc_naive, format_for_user  # ⬅️ NEW

BUTTON_ADD = "➕ Добавить задачу"
BUTTON_LIST = "📅 Мои задачи"
BUTTON_SETTINGS = "⚙️ Настройки"

router = Router()


@router.message(F.text == BUTTON_LIST)
async def on_list(msg: Message):
    user_tz = await get_user_timezone(msg.chat.id)
    tasks = await list_active(msg.chat.id)
    if not tasks:
        return await msg.answer("Пока нет активных задач ✨", reply_markup=main_kb())

    lines = []
    for t in tasks:
        when = format_for_user(t.due_at, user_tz) if t.due_at else "без срока"
        lines.append(f"<b>#{t.id}</b> — {html.escape(t.title)} · {when} · {t.priority}")
    await msg.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_kb())


@router.message(F.text == BUTTON_SETTINGS)
async def on_settings(msg: Message):
    await msg.answer(
        "Настройки:\n"
        "/set_timezone Europe/Moscow — установить часовой пояс",
        reply_markup=main_kb()
    )


@router.message(F.text == BUTTON_ADD)
async def on_add_hint(msg: Message):
    await msg.answer(
        "Пришли текст или голосовое: «Напомни завтра в 12 купить кофе»",
        reply_markup=main_kb()
    )


IGNORE = {BUTTON_ADD, BUTTON_LIST, BUTTON_SETTINGS}


@router.message(F.text & ~F.text.in_(IGNORE))
async def handle_text(msg: Message):
    text = msg.text.strip()

    # Парсим и учитываем часовой пояс пользователя
    user_tz = await get_user_timezone(msg.chat.id)
    parsed = await parse_task(text, user_tz=user_tz)

    title = parsed.get("title", text[:120])
    priority = parsed.get("priority", "normal")
    due_date = parsed.get("due_date")
    due_time = parsed.get("due_time")

    # ⬇️ ключевая строка: локальное время пользователя → UTC (naive) для хранения
    due_at = to_utc_naive(due_date, due_time, user_tz) if due_date else None

    await add_task(chat_id=msg.chat.id, title=title, priority=priority, due_at=due_at)

    due_text = f" на {format_for_user(due_at, user_tz)}" if due_at else ""
    await msg.answer(
        f"📝 Распознал: <i>{html.escape(text)}</i>\n"
        f"✅ Добавил задачу: <b>{html.escape(title)}</b>{due_text}\n"
        f"Приоритет: {priority}",
        parse_mode="HTML",
        reply_markup=main_kb(),
    )
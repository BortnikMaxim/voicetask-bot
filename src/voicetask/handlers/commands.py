from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from ..keyboards import main_kb, task_inline_kb
from ..database.db import async_session_maker, Task, mark_done
from ..database.db import upsert_user_timezone, get_user_timezone  # ← NEW
from sqlalchemy import select
import html
from ..config import settings
from ..services.parser import parse_task

router = Router()

@router.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "Привет! Я голосовой таск-бот.\n\n"
        "🎙 Пришли голосовое или текст (например: <i>Напомни записаться на МРТ завтра в 17:00</i>),\n"
        "или используй команды:\n"
        "/list — показать активные задачи\n"
        "/done &lt;id&gt; — отметить задачу выполненной\n"
        "/set_timezone Europe/Moscow — установить часовой пояс",
        reply_markup=main_kb,
    )

@router.message(Command("set_timezone"))
async def cmd_set_timezone(msg: Message):
    parts = msg.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply("Укажи часовой пояс, например:\n<code>/set_timezone Europe/Moscow</code>")
    tz = parts[1].strip()
    # простая валидация формата
    if "/" not in tz:
        return await msg.reply("Неверный формат. Пример: <code>Europe/Moscow</code>")
    await upsert_user_timezone(msg.chat.id, tz)
    await msg.answer(f"✅ Часовой пояс сохранён: <b>{html.escape(tz)}</b>")

@router.message(Command("list"))
async def cmd_list(msg: Message):
    async with async_session_maker() as session:
        q = await session.execute(
            select(Task)
            .where(Task.chat_id == msg.chat.id, Task.is_done == False)
            .order_by(Task.due_at.is_(None), Task.due_at)
        )
        tasks = q.scalars().all()
    if not tasks:
        await msg.answer("Пока нет активных задач ✨")
        return
    lines = []
    for t in tasks:
        when = t.due_at.strftime('%Y-%m-%d %H:%M') if t.due_at else "без срока"
        lines.append(f"<b>#{t.id}</b> — {html.escape(t.title)} · {when} · {t.priority}")
    # прикладываем inline-кнопки для последней задачи как пример
    await msg.answer("\n".join(lines))

# обработчик inline-кликов "done"/"delete"
@router.callback_query(F.data.startswith("done:"))
async def cb_done(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    ok = await mark_done(chat_id=call.message.chat.id, task_id=task_id)
    await call.answer("Готово ✅" if ok else "Не найдено")
    if call.message:
        await call.message.edit_reply_markup(reply_markup=None)

# Хендлер добавления задачи из текстового ввода переносим в text.py (как у тебя),
# но важно — передавать user_tz в parse_task. См. следующий пункт.
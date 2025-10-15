from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

from ..keyboards import main_kb
from ..database.db import async_session_maker, Task, mark_done
from sqlalchemy import select

router = Router()

@router.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "Привет! Я голосовой таск-бот.\n\n"
        "🎙 Пришли голосовое или текст:\n"
        "например: <i>Напомни позвонить Антону завтра в 11:00</i>\n\n"
        "Команды:\n"
        "/list — показать активные задачи\n"
        "/done &lt;id&gt; — отметить задачу выполненной",  # ← было /done <id>
        reply_markup=main_kb,
    )

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
        lines.append(f"<b>#{t.id}</b> — {t.title} · {when} · {t.priority}")
    await msg.answer("\n".join(lines))

@router.message(Command("done"))
async def cmd_done(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.reply("Использование: /done <id>")
        return
    task_id = int(parts[1])
    ok = await mark_done(chat_id=msg.chat.id, task_id=task_id)
    await msg.answer("✅ Готово" if ok else "Не нашёл такую задачу")

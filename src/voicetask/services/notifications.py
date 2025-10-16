from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..bot import bot
from ..database.db import async_session_maker, Task
from sqlalchemy import select, update
from datetime import datetime, timedelta

def _kb_for_task(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{task_id}")],
        [InlineKeyboardButton(text="⏰ Отложить 10 мин", callback_data=f"snooze10:{task_id}")]
    ])

async def notify_task_due(task: Task) -> None:
    due_txt = task.due_at.strftime("%Y-%m-%d %H:%M") if task.due_at else "без даты"
    text = f"🔔 Напоминание:\n<b>{task.title}</b>\n🗓 {due_txt}"
    await bot.send_message(task.chat_id, text, reply_markup=_kb_for_task(task.id), parse_mode="HTML")

async def check_due_and_notify() -> int:
    """Вернёт сколько уведомлений отправлено за проход"""
    now = datetime.utcnow()
    count = 0
    async with async_session_maker() as session:
        q = await session.execute(
            select(Task).where(
                Task.is_done == False,
                Task.due_at != None,
                Task.due_at <= now,
                Task.notified_at.is_(None),
            ).order_by(Task.due_at)
        )
        tasks = q.scalars().all()
        for t in tasks:
            try:
                await notify_task_due(t)
                # помечаем как уведомлён
                await session.execute(
                    update(Task).where(Task.id == t.id).values(notified_at=now)
                )
                count += 1
            except Exception:
                # логируй, но продолжай
                pass
        if tasks:
            await session.commit()
    return count

async def snooze_task(task_id: int, minutes: int = 10) -> bool:
    """Сдвигаем срок и обнуляем notified_at"""
    async with async_session_maker() as session:
        q = await session.execute(select(Task).where(Task.id == task_id))
        t = q.scalar_one_or_none()
        if not t:
            return False
        base = t.due_at or datetime.utcnow()
        new_dt = base + timedelta(minutes=minutes)
        await session.execute(
            update(Task).where(Task.id == task_id).values(due_at=new_dt, notified_at=None)
        )
        await session.commit()
        return True
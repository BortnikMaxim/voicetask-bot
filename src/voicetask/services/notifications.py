from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from sqlalchemy import select, update

from ..bot import bot
from ..database.db import async_session_maker, Task, get_user_timezone
from .timezone import format_for_user  # ⬅️ добавили форматирование времени по TZ пользователя


def _kb_for_task(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура под уведомлением."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{task_id}")],
        [InlineKeyboardButton(text="⏰ Отложить 10 мин", callback_data=f"snooze10:{task_id}")]
    ])


async def notify_task_due(task: Task) -> None:
    """Отправить напоминание пользователю с форматированием времени по его TZ."""
    user_tz = await get_user_timezone(task.chat_id)
    due_txt = format_for_user(task.due_at, user_tz)
    text = f"🔔 Напоминание:\n<b>{task.title}</b>\n🗓 {due_txt}"
    await bot.send_message(
        task.chat_id,
        text,
        reply_markup=_kb_for_task(task.id),
        parse_mode="HTML",
    )


async def check_due_and_notify() -> int:
    """Ищет просроченные задачи, отправляет уведомления и помечает notified_at."""
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
                await session.execute(
                    update(Task).where(Task.id == t.id).values(notified_at=now)
                )
                count += 1
            except Exception as e:
                # просто логируем, чтобы цикл не останавливался
                import logging
                logging.exception(f"Ошибка при уведомлении task_id={t.id}: {e}")

        if count:
            await session.commit()

    return count


async def snooze_task(task_id: int, minutes: int = 10) -> bool:
    """Отложить задачу и сбросить флаг уведомления."""
    async with async_session_maker() as session:
        q = await session.execute(select(Task).where(Task.id == task_id))
        t = q.scalar_one_or_none()
        if not t:
            return False

        base = t.due_at or datetime.utcnow()
        new_dt = base + timedelta(minutes=minutes)
        await session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(due_at=new_dt, notified_at=None)
        )
        await session.commit()

        return True
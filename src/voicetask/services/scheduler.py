# src/voicetask/services/scheduler.py
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from ..config import settings                    # ⬅ добавили импорт настроек
from ..database.db import Task, async_session_maker  # mark_done тут не используется — можно убрать

scheduler = AsyncIOScheduler(timezone=settings.TZ)    # ⬅ было "Europe/Berlin"


async def _notify_and_close(task_id: int, notify_fn: Callable[[int], None]):
    # Отправляем уведомление и отмечаем задачу выполненной/или остаётся активной — на ваше усмотрение
    await notify_fn(task_id)

async def schedule_task(task: Task, notify_fn: Callable[[int], None]):
    if not task.due_at:
        return
    trigger = DateTrigger(run_date=task.due_at)
    scheduler.add_job(_notify_job_wrapper, trigger=trigger, args=[task.id], id=f"task_{task.id}")

async def _notify_job_wrapper(task_id: int):
    from .notifications import notify_task_due
    await notify_task_due(task_id)

async def reschedule_all(notify_fn: Callable[[int], None] | None = None):
    from sqlalchemy import select
    async with async_session_maker() as session:
        now = datetime.now()
        q = await session.execute(select(Task).where(Task.is_done == False, Task.due_at != None, Task.due_at >= now))
        tasks = q.scalars().all()
        for t in tasks:
            await schedule_task(t, notify_fn or (lambda _: None))

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
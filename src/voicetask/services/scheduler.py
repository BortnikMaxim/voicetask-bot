# src/voicetask/services/scheduler.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from ..database.db import Task, async_session_maker
from .notifications import notify_task_due  # отправка сообщения пользователю


async def _fetch_due_tasks(now_utc: datetime) -> list[Task]:
    """Вернёт невыполненные задачи, срок которых наступил, и по ним ещё не слали уведомление."""
    async with async_session_maker() as session:
        q = await session.execute(
            select(Task).where(
                Task.is_done == False,            # активные
                Task.due_at != None,              # есть срок
                Task.due_at <= now_utc,           # пора напоминать
                Task.notified_at.is_(None),       # ещё не уведомляли
            ).order_by(Task.due_at)
        )
        return q.scalars().all()


async def _mark_notified(task_ids: list[int], when: datetime) -> None:
    """Помечает задачи как уведомлённые (чтобы не слать повторно)."""
    if not task_ids:
        return
    async with async_session_maker() as session:
        await session.execute(
            update(Task).where(Task.id.in_(task_ids)).values(notified_at=when)
        )
        await session.commit()


async def check_due_and_notify() -> int:
    """
    Один проход: найти задачи, отправить напоминания, пометить notified_at.
    Возвращает количество отправленных уведомлений.
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # храним UTC в БД как naive
    tasks = await _fetch_due_tasks(now_utc)

    sent = 0
    notified_ids: list[int] = []

    for t in tasks:
        try:
            await notify_task_due(t)  # собственно отправка в Telegram
            notified_ids.append(t.id)
            sent += 1
        except Exception:
            logging.exception("Failed to notify task id=%s", t.id)

    if notified_ids:
        await _mark_notified(notified_ids, now_utc)

    return sent


async def notification_loop(interval_seconds: int = 60) -> None:
    """
    Фоновая «тикалка»: каждые N секунд вызывает check_due_and_notify().
    Запускается из main.py через asyncio.create_task(...).
    """
    logging.info("🔁 Notification loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            count = await check_due_and_notify()
            if count:
                logging.info("📨 Sent %s notifications", count)
        except Exception:
            logging.exception("Notification loop error")
        await asyncio.sleep(interval_seconds)
from datetime import datetime
from sqlalchemy import select

from ..database.db import async_session_maker, Task
from ..bot import bot

async def notify_task_due(task_id: int):
    async with async_session_maker() as session:
        q = await session.execute(select(Task).where(Task.id == task_id))
        task = q.scalar_one_or_none()
        if not task:
            return
        try:
            await bot.send_message(chat_id=task.chat_id, text=f"⏰ Напоминание: {task.title}\nКогда: {task.due_at.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass
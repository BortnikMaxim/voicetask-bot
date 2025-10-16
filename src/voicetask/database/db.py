from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    select,
    Integer,
    String,
    DateTime,
    Boolean,
    BigInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from ..config import settings


# ---------------- Base ----------------
class Base(DeclarativeBase):
    pass


# ---------------- Models ----------------
class User(Base):
    """
    Сохраняем пользовательские настройки (сейчас — только часовой пояс).
    chat_id уникален: один пользователь — одна запись.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), default=None)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(255))
    priority: Mapped[str] = mapped_column(String(16), default="normal")

    # Итоговая дата-время задачи (если дедлайн известен)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    is_done: Mapped[bool] = mapped_column(Boolean, default=False)

    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------- Engine / Session ----------------
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# ---------------- Init ----------------
async def init_db():
    """Создать таблицы при первом запуске (SQLite: просто create_all)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------- Users API ----------------
async def upsert_user_timezone(chat_id: int, tz: str) -> None:
    """Создать/обновить timezone пользователя по chat_id."""
    async with async_session_maker() as session:
        q = await session.execute(select(User).where(User.chat_id == chat_id))
        user = q.scalar_one_or_none()
        if user:
            user.timezone = tz
        else:
            user = User(chat_id=chat_id, timezone=tz)
            session.add(user)
        await session.commit()


async def get_user_timezone(chat_id: int) -> Optional[str]:
    """Вернуть timezone пользователя или None, если не задан."""
    async with async_session_maker() as session:
        q = await session.execute(select(User.timezone).where(User.chat_id == chat_id))
        return q.scalar_one_or_none()


# ---------------- Tasks API ----------------
async def add_task(chat_id: int, title: str, priority: str, due_at: datetime | None) -> Task:
    async with async_session_maker() as session:
        task = Task(chat_id=chat_id, title=title, priority=priority, due_at=due_at)
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def list_active(chat_id: int) -> list[Task]:
    async with async_session_maker() as session:
        q = await session.execute(
            select(Task)
            .where(Task.chat_id == chat_id, Task.is_done == False)
            .order_by(Task.due_at.is_(None), Task.due_at)
        )
        return q.scalars().all()


async def mark_done(chat_id: int, task_id: int) -> bool:
    async with async_session_maker() as session:
        q = await session.execute(select(Task).where(Task.chat_id == chat_id, Task.id == task_id))
        task = q.scalar_one_or_none()
        if not task:
            return False
        task.is_done = True
        await session.commit()
        return True


# (опционально) удаление задачи — если планируешь кнопку "🗑 Удалить"
async def delete_task(chat_id: int, task_id: int) -> bool:
    async with async_session_maker() as session:
        q = await session.execute(select(Task).where(Task.chat_id == chat_id, Task.id == task_id))
        task = q.scalar_one_or_none()
        if not task:
            return False
        await session.delete(task)
        await session.commit()
        return True
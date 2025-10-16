from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..database.db import mark_done
from ..services.notifications import snooze_task

router = Router()


def _safe_int(s: str) -> int | None:
    try:
        return int(s)
    except Exception:
        return None


@router.callback_query(F.data.startswith("done:"))
async def cb_done(call: CallbackQuery):
    """
    Обработчик кнопки «✅ Готово».
    Формат callback_data: done:<task_id>
    """
    task_id = _safe_int(call.data.split(":", 1)[1])
    if task_id is None:
        await call.answer("Некорректный ID задачи", show_alert=True)
        return

    ok = await mark_done(chat_id=call.message.chat.id, task_id=task_id)
    if ok:
        # Меняем текст исходного сообщения-напоминания
        try:
            await call.message.edit_text("✅ Задача отмечена выполненной")
        except Exception:
            # если редактирование нельзя (например, старое сообщение) — просто ответ на клик
            pass
        await call.answer("Готово!")
    else:
        await call.answer("Задача не найдена", show_alert=True)


@router.callback_query(F.data.startswith("snooze10:"))
async def cb_snooze_10(call: CallbackQuery):
    """
    Обработчик кнопки «⏰ Отложить 10 мин».
    Формат callback_data: snooze10:<task_id>
    """
    task_id = _safe_int(call.data.split(":", 1)[1])
    if task_id is None:
        await call.answer("Некорректный ID задачи", show_alert=True)
        return

    ok = await snooze_task(task_id, minutes=10)
    if ok:
        try:
            await call.message.edit_text("⏰ Отложил на 10 минут")
        except Exception:
            pass
        await call.answer("Отложено на 10 мин")
    else:
        await call.answer("Задача не найдена", show_alert=True)


# Универсальный снуз: callback_data вида "snooze:<minutes>:<task_id>"
@router.callback_query(F.data.startswith("snooze:"))
async def cb_snooze_custom(call: CallbackQuery):
    parts = call.data.split(":")
    if len(parts) != 3:
        await call.answer("Некорректные данные", show_alert=True)
        return

    minutes = _safe_int(parts[1])
    task_id = _safe_int(parts[2])
    if minutes is None or task_id is None or minutes <= 0:
        await call.answer("Некорректные параметры", show_alert=True)
        return

    ok = await snooze_task(task_id, minutes=minutes)
    if ok:
        try:
            await call.message.edit_text(f"⏰ Отложил на {minutes} мин")
        except Exception:
            pass
        await call.answer(f"Отложено на {minutes} мин")
    else:
        await call.answer("Задача не найдена", show_alert=True)
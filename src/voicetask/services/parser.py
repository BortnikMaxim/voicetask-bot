import json
import re
from datetime import datetime, time
from typing import Any, Dict, Optional

import dateparser
from openai import OpenAI

from ..config import settings as app_settings

client = OpenAI(api_key=app_settings.OPENAI_API_KEY)

SYSTEM_PROMPT = (
    """
    Ты — ассистент для разбора задач из естественного языка. Твоя цель —
    превратить фразу пользователя на русском языке в структурированную задачу.

    Формат вывода: JSON с полями:
    - title: краткое действие (строка)
    - due_date: дата в формате YYYY-MM-DD (или null)
    - due_time: время в формате HH:MM (или null)
    - priority: one of [low, normal, high]

    Правила:
    - Если дата/время не названы явно, попытайся понять по словам («завтра утром»).
    - Если указано только «завтра/сегодня/послезавтра» — выведи due_date, а due_time = null.
    - Если нет времени, можно оставить null (бот подставит дефолтное время).
    - Не придумывай лишних деталей.
    - Возвращай только JSON (без комментариев и текста).
    """
)

PRIORITY_HINT = {
    "срочно": "high",
    "важно": "high",
    "не срочно": "low",
}

def _fallback_date_parse(text: str, tz: str) -> tuple[Optional[str], Optional[str]]:
    """Парсим дату/время через dateparser как запасной вариант (всегда будущее)."""
    settings_hint = {
        "RELATIVE_BASE": datetime.now(),
        "PREFER_DATES_FROM": "future",   # ключ: всегда будущее
        "TIMEZONE": tz,
        "TO_TIMEZONE": tz,
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    dt = dateparser.parse(text, settings=settings_hint, languages=["ru", "en"])
    if not dt:
        return None, None
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M") if (dt.hour or dt.minute) else None
    return date_str, time_str

async def parse_task(text: str, user_tz: Optional[str] = None) -> Dict[str, Any]:
    """
    Разбирает текст задачи через OpenAI LLM + fallback-парсер.
    Всегда выбирает дату/время в будущем относительно user_tz (или дефолтного TZ).
    """
    tz = (user_tz or app_settings.TZ).strip()
    now = datetime.now()
    current_context = f"Сейчас {now.strftime('%Y-%m-%d %H:%M')}, часовой пояс: {tz}"

    # Быстрая эвристика приоритета
    priority = "normal"
    for k, v in PRIORITY_HINT.items():
        if k in text.lower():
            priority = v
            break

    # Запрос к LLM (без temperature — некоторые модели не принимают)
    try:
        resp = client.chat.completions.create(
            model=app_settings.OPENAI_TASK_PARSER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{current_context}\n\n{text}"},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
    except Exception:
        # Fallback: пытаемся вытащить дату/время локально
        due_date, due_time = _fallback_date_parse(text, tz)
        return {
            "title": text.strip()[:120],
            "due_date": due_date,
            "due_time": due_time,
            "priority": priority,
        }

    # Если LLM не дала дату — fallback
    if not data.get("due_date"):
        dd, dt = _fallback_date_parse(text, tz)
        data["due_date"], data["due_time"] = dd, dt

    # Если дата есть — гарантируем будущее (при необходимости переносим на завтра)
    due_date = data.get("due_date")
    due_time = data.get("due_time")
    if due_date:
        try:
            if due_time:
                candidate = datetime.fromisoformat(f"{due_date}T{due_time}:00")
            else:
                h, m = map(int, app_settings.TASK_DEFAULT_TIME.split(":"))
                candidate = datetime.fromisoformat(f"{due_date}T{h:02d}:{m:02d}:00")

            if candidate <= now:
                from datetime import timedelta
                candidate = candidate + timedelta(days=1)

            data["due_date"] = candidate.strftime("%Y-%m-%d")
            data["due_time"] = candidate.strftime("%H:%M")
        except Exception:
            pass

    data.setdefault("priority", priority)
    if not data.get("title"):
        data["title"] = text.strip()[:120]

    return data
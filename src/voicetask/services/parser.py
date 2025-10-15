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

def _fallback_date_parse(text: str) -> tuple[Optional[str], Optional[str]]:
    """Парсим дату/время через dateparser как запасной вариант."""
    settings_hint = {
    "RELATIVE_BASE": datetime.now(),
    "PREFER_DATES_FROM": "future",
    "TIMEZONE": app_settings.TZ,
    "RETURN_AS_TIMEZONE_AWARE": False,
    "PARSERS": ["relative-time", "absolute-time", "timestamp"]
    }
    dt = dateparser.parse(text, settings=settings_hint, languages=["ru", "en"])
    if not dt:
        return None, None
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M") if (dt.hour or dt.minute) else None
    return date_str, time_str

async def parse_task(text: str) -> Dict[str, Any]:
    # Быстрая эвристика приоритета
    priority = "normal"
    for k, v in PRIORITY_HINT.items():
        if k in text.lower():
            priority = v
            break

    # Запрос к LLM
    resp = client.chat.completions.create(
        model=app_settings.OPENAI_TASK_PARSER_MODEL,
        messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
        ],
        #temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()

    # Защитный парсинг JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: попытаться вытащить дату/время через dateparser
        due_date, due_time = _fallback_date_parse(text)
        return {
            "title": text.strip()[:120],
            "due_date": due_date,
            "due_time": due_time,
            "priority": priority,
        }

    # Подстановка эвристического приоритета, если модель не указала
    data.setdefault("priority", priority)

    # Нормализация due_time: если пусто и в тексте был намек на «утром/вечером» — можно оставить null,
    # бот позже подставит дефолтное время из настроек.
    return data
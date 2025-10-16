from __future__ import annotations
from datetime import datetime
import pytz

from ..config import settings

def to_utc_naive(date_str: str, time_str: str | None, user_tz: str | None) -> datetime:
    """
    Преобразует ЛОКАЛЬНУЮ дату/время пользователя в UTC (naive).
    Если time_str пустое — берём дефолт из настроек (settings.TASK_DEFAULT_TIME).
    """
    if not time_str:
        h, m = map(int, settings.TASK_DEFAULT_TIME.split(":"))
        time_str = f"{h:02d}:{m:02d}"

    dt_local = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    tz_name = user_tz or getattr(settings, "TZ", None) or "UTC"
    tz = pytz.timezone(tz_name)
    dt_local_aware = tz.localize(dt_local)
    dt_utc = dt_local_aware.astimezone(pytz.UTC)
    # храним naive-UTC (как и created_at)
    return dt_utc.replace(tzinfo=None)

def format_for_user(utc_naive_dt: datetime | None, user_tz: str | None) -> str:
    if utc_naive_dt is None:
        return "без даты"

    tz_name = user_tz or getattr(settings, "TZ", None) or "UTC"
    import pytz
    tz = pytz.timezone(tz_name)

    local_dt = pytz.UTC.localize(utc_naive_dt).astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M")
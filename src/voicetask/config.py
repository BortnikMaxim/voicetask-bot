from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # читаем .env, игнорируем лишние переменные и НЕ чувствительны к регистру
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,   # ← ключевое: TZ и tz теперь одинаково читаются
    )

    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str

    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./voicetasks.db")
    OPENAI_TASK_PARSER_MODEL: str = Field(default="gpt-5-mini")
    WHISPER_MODEL: str = Field(default="whisper-1")
    WHISPER_LANGUAGE: str | None = Field(default=None)  # e.g. "ru"

    TASK_DEFAULT_TIME: str = Field(default="09:00")     # HH:MM
    TZ: str = Field(default="Europe/Moscow")            # поддерживаем TZ/tz из .env

settings = Settings()

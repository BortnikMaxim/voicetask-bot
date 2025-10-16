import asyncio
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

from openai import OpenAI

from ..config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def transcribe_ogg_file(src_path: str) -> str:
    # Без конвертации: Telegram voice (OGG/Opus) отправляем напрямую
    with open(src_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=settings.WHISPER_MODEL,          # "whisper-1" или "gpt-4o-mini-transcribe"
            file=f,                                # Передаём бинарный файл как есть
            language=(settings.WHISPER_LANGUAGE or "ru"),
        )
    return (resp.text or "").strip()
import asyncio
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

from openai import OpenAI

from ..config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def ogg_to_wav(src_path: str) -> str:
	dst = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
	dst_path = dst.name
	dst.close()
	# Конвертация через ffmpeg
	cmd = [
	"ffmpeg", "-y", "-i", src_path,
	"-ac", "1", "-ar", "16000",
	dst_path
	]
	proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
	await proc.communicate()
	if proc.returncode != 0:
		raise RuntimeError("FFmpeg conversion failed")
	return dst_path

async def transcribe_ogg_file(src_path: str, language: Optional[str] = None) -> str:
	wav_path = await ogg_to_wav(src_path)
	with open(wav_path, "rb") as f:
		transcript = client.audio.transcriptions.create(
		model=settings.WHISPER_MODEL,
		file=f,
		language=language or settings.WHISPER_LANGUAGE
		)
	try:
		os.remove(wav_path)
	except FileNotFoundError:
		pass
	return transcript.text.strip()
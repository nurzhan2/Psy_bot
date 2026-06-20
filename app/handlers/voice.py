"""
Приём голосовых сообщений от пользователей.

ЮРИДИЧЕСКОЕ ТРЕБОВАНИЕ (от Екатерины, п.2 "Запрет на сбор биометрии"):
Бот должен работать строго с текстом. Голосовое сообщение пользователя
расшифровывается в текст через Whisper, после чего ИСХОДНЫЙ АУДИОФАЙЛ
немедленно удаляется — ни временная, ни постоянная копия голоса клиента
не должна оставаться на сервере. Это отдельно от аудио-практик САМОЙ
Екатерины (личные материалы), которые её собственный голос и хранятся
в базе знаний осознанно, с её согласия.

Поток обработки:
  1. Скачиваем voice-файл во временную папку
  2. Прогоняем через Whisper API -> получаем текст
  3. Немедленно удаляем временный файл (try/finally, чтобы удаление
     произошло даже при ошибке распознавания)
  4. Передаём текст дальше в ту же логику, что и обычное текстовое
     сообщение (онбординг/лимиты/кризис-фильтр/антифлуд/LLM)
"""
import os
import tempfile
import asyncio

from aiogram import Router, F
from aiogram.types import Message
from openai import OpenAI

from config import OPENAI_API_KEY
from app.handlers.dialogue import process_user_text

router = Router()
client = OpenAI(api_key=OPENAI_API_KEY)


def _transcribe_sync(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru",
        )
    return transcript.text


@router.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id

    await message.bot.send_chat_action(message.chat.id, "typing")

    tmp_path = None
    try:
        voice = message.voice
        file = await message.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await message.bot.download_file(file.file_path, destination=tmp_path)

        text = await asyncio.to_thread(_transcribe_sync, tmp_path)

    except Exception:
        await message.answer(
            "Не получилось распознать голосовое сообщение. Попробуй, пожалуйста, "
            "написать текстом 🙏"
        )
        return
    finally:
        # Критично: удаляем файл с голосом пользователя независимо от исхода —
        # это и есть требование "не хранить биометрию клиентов"
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not text or not text.strip():
        await message.answer(
            "Не удалось разобрать, что было сказано в голосовом. Попробуй ещё раз "
            "или напиши текстом."
        )
        return

    await process_user_text(message, text.strip(), source="voice")

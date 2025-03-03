import os
import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ContentType
from pydantic_settings import BaseSettings
import openai
from io import BytesIO
from dotenv import load_dotenv
import tempfile
from gtts import gTTS

load_dotenv()

class Settings(BaseSettings):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

settings = Settings()

logging.basicConfig(level=logging.INFO)
openai.api_key = settings.OPENAI_API_KEY


async def start_handler(message: Message):
    await message.answer("Привет! Отправьте мне голосовое сообщение, и я его обработаю.")

async def voice_message_handler(message: Message):
    if not message.voice:
        await message.answer("Пожалуйста, отправьте голосовое сообщение.")
        return

    voice = message.voice
    file_info = await message.bot.get_file(voice.file_id)
    file = await message.bot.download_file(file_info.file_path)

    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name

        with open(temp_file_path, "rb") as audio_data:
            transcript = openai.Audio.transcribe("whisper-1", audio_data)

        text = transcript['text']

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты дружелюбный помощник."},
                {"role": "user", "content": text}
            ]
        )
        answer = response.choices[0].message['content'].strip()

        tts = gTTS(answer, lang='ru')
        audio_output = BytesIO()
        tts.write_to_fp(audio_output)
        audio_output.seek(0)

        await message.answer_voice(types.BufferedInputFile(audio_output.getvalue(), filename="response.ogg"))

    except Exception as e:
        logging.error(f"Ошибка при обработке голосового сообщения: {e}")
        await message.answer("Произошла ошибка при обработке вашего сообщения. Попробуйте ещё раз.")

    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(start_handler, CommandStart())
    dp.message.register(voice_message_handler, F.content_type == ContentType.VOICE)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


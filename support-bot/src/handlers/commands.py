"""Command handlers for /start and /questions."""

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.enums import ChatType

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    # Only respond in private chats
    if message.chat.type != ChatType.PRIVATE:
        return

    welcome_text = """Привет! Я бот поддержки.

Задайте мне вопрос, и я постараюсь помочь, используя документацию проекта.

Доступные команды:
/start - Это сообщение
/questions - Примеры вопросов

Просто напишите свой вопрос, и я отвечу!"""

    await message.answer(welcome_text)


@router.message(Command("questions"))
async def cmd_questions(message: Message) -> None:
    """Handle /questions command - show example questions."""
    # Only respond in private chats
    if message.chat.type != ChatType.PRIVATE:
        return

    examples_text = """Примеры вопросов, которые вы можете задать:

1. Как настроить авторизацию?
2. Какие есть API эндпоинты?
3. Как запустить проект локально?
4. Как работает система очередей?
5. Какие переменные окружения нужны?

Просто напишите свой вопрос!"""

    await message.answer(examples_text)

"""Command handlers for /start, /help, and /status."""

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.enums import ChatType

from src.clients import ReminderClient, DockerClient
from src.config import get_config

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    # Only respond in private chats
    if message.chat.type != ChatType.PRIVATE:
        return

    welcome_text = """Привет! Я ассистент разработчика.

Что я умею:
- Отвечать на вопросы о проекте (RAG-поиск)
- Управлять задачами ("добавь задачу", "покажи задачи")
- Показывать статус Docker-контейнеров

Команды:
/start - Это сообщение
/help - Подробная справка с примерами
/status - Краткая сводка: задачи + Docker

Просто напишите свой вопрос!"""

    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command - show detailed examples."""
    # Only respond in private chats
    if message.chat.type != ChatType.PRIVATE:
        return

    help_text = """Примеры запросов:

📚 Вопросы о проекте:
• "Как работает авторизация?"
• "Какие есть API эндпоинты?"
• "Как запустить локально?"

📋 Управление задачами:
• "Добавь задачу: фикс авторизации"
• "Покажи все задачи"
• "Отметь задачу abc123 выполненной"
• "Что в приоритете?"

🐳 Статус системы:
• "Работают ли сервисы?"
• "Статус докера\""""

    await message.answer(help_text)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    """Handle /status command - show tasks and Docker summary."""
    # Only respond in private chats
    if message.chat.type != ChatType.PRIVATE:
        return

    config = get_config()

    # Get reminder summary
    tasks_section = ""
    if config.reminder_server_url:
        reminder_client = ReminderClient(config.reminder_server_url)
        summary = await reminder_client.summary()
        if summary:
            tasks_section = f"""📋 Задачи:
• Активных: {summary.active}
• Просроченных: {summary.overdue}
• Выполнено сегодня: {summary.completed_today}"""
        else:
            tasks_section = "📋 Задачи: недоступны"
    else:
        tasks_section = "📋 Задачи: сервер не настроен"

    # Get Docker status
    docker_client = DockerClient()
    containers = await docker_client.get_status()

    if containers:
        container_lines = [f"• {c.name}: {c.state}" for c in containers]
        docker_section = "🐳 Docker:\n" + "\n".join(container_lines)
    else:
        docker_section = "🐳 Docker: нет запущенных контейнеров"

    status_text = f"{tasks_section}\n\n{docker_section}"
    await message.answer(status_text)

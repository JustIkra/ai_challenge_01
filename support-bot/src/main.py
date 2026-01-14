"""Support bot entry point."""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.config import get_config
from src.handlers import commands, messages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialize and run the bot."""
    config = get_config()

    # Initialize bot and dispatcher
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()

    # Register routers
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    logger.info("Starting support bot...")
    logger.info("RAG server: %s", config.rag_server_url)
    logger.info("LLM model: %s", config.openrouter_model)

    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
FastAPI application entry point.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.api.routes import health, chat, message
from app.services.rabbitmq import close_publisher
from app.workers.response_consumer import start_consumer, stop_consumer
from app.db.session import engine, async_session_maker
from app.models import Base, User

# Default user ID used by frontend
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.

    Handles:
    - Starting RabbitMQ response consumer
    - Graceful shutdown of all services
    """
    # Startup
    logger.info("Starting application...")

    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

    # Create default user if not exists
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == DEFAULT_USER_ID)
            )
            if not result.scalar_one_or_none():
                default_user = User(id=DEFAULT_USER_ID, username="default")
                session.add(default_user)
                await session.commit()
                logger.info("Default user created")
            else:
                logger.info("Default user already exists")
    except Exception as e:
        logger.error(f"Failed to create default user: {e}")

    try:
        # Start RabbitMQ consumer in background
        await start_consumer()
        logger.info("RabbitMQ consumer started")
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        # Application can still start, but messaging won't work
        logger.warning("Application starting without RabbitMQ consumer")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    try:
        # Stop consumer
        await stop_consumer()
        logger.info("RabbitMQ consumer stopped")

        # Close publisher
        await close_publisher()
        logger.info("RabbitMQ publisher closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application instance.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(
        health.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        chat.router,
        prefix=settings.API_V1_PREFIX,
    )
    app.include_router(
        message.router,
        prefix=settings.API_V1_PREFIX,
    )

    return app


# Create application instance
app = create_application()

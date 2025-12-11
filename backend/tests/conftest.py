"""
Pytest configuration and shared fixtures.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set required environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
os.environ.setdefault("OPENROUTER_MODEL", "google/gemini-2.5-flash")


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_chat_id():
    """Generate a sample chat ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_request_id():
    """Generate a sample request ID."""
    return uuid.uuid4()

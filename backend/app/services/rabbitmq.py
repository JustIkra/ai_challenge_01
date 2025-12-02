"""
RabbitMQ publisher service for sending requests to Gemini worker.
"""

import asyncio
import json
import logging
from typing import Any

import aio_pika
from aio_pika import Connection, Channel, ExchangeType

from app.config import settings
from app.schemas.rabbitmq import GeminiRequestMessage

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """
    RabbitMQ publisher for sending Gemini requests.

    Handles connection management, retry logic, and message publishing.
    """

    def __init__(self, max_retries: int = 5, retry_delay: float = 1.0):
        """
        Initialize RabbitMQ publisher.

        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.url = settings.RABBITMQ_URL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection: Connection | None = None
        self.channel: Channel | None = None
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to RabbitMQ with exponential backoff retry.

        Raises:
            ConnectionError: If connection fails after max retries
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Connecting to RabbitMQ (attempt {attempt}/{self.max_retries})...")
                self.connection = await aio_pika.connect_robust(
                    self.url,
                    timeout=10.0
                )
                self.channel = await self.connection.channel()

                # Declare exchange for routing
                exchange = await self.channel.declare_exchange(
                    "gemini",
                    ExchangeType.DIRECT,
                    durable=True
                )

                # Declare queues
                await self.channel.declare_queue(
                    "gemini.requests",
                    durable=True
                )
                await self.channel.declare_queue(
                    "gemini.responses",
                    durable=True
                )

                self._connected = True
                logger.info("Successfully connected to RabbitMQ")
                return

            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ (attempt {attempt}/{self.max_retries}): {e}")

                if attempt == self.max_retries:
                    raise ConnectionError(f"Failed to connect to RabbitMQ after {self.max_retries} attempts") from e

                # Exponential backoff
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    async def publish_request(self, request: GeminiRequestMessage) -> None:
        """
        Publish request to gemini.requests queue.

        Args:
            request: Gemini request message

        Raises:
            RuntimeError: If publisher is not connected
            Exception: If publishing fails
        """
        if not self._connected or not self.channel:
            raise RuntimeError("Publisher is not connected. Call connect() first.")

        try:
            # Serialize message to JSON
            message_body = request.model_dump_json(by_alias=True)

            # Create AMQP message
            message = aio_pika.Message(
                body=message_body.encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=str(request.request_id),
                reply_to=request.callback_queue,
            )

            # Publish to queue
            await self.channel.default_exchange.publish(
                message,
                routing_key="gemini.requests",
            )

            logger.info(
                f"Published request to RabbitMQ: request_id={request.request_id}, "
                f"model={request.model}, prompt_length={len(request.prompt)}"
            )

        except Exception as e:
            logger.error(f"Failed to publish request {request.request_id}: {e}")
            raise

    async def close(self) -> None:
        """
        Close RabbitMQ connection gracefully.
        """
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("RabbitMQ connection closed")
            self._connected = False
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if publisher is connected."""
        return self._connected and self.connection is not None and not self.connection.is_closed


# Global publisher instance
_publisher: RabbitMQPublisher | None = None


async def get_publisher() -> RabbitMQPublisher:
    """
    Get or create global publisher instance.

    Returns:
        RabbitMQPublisher: Connected publisher instance
    """
    global _publisher

    if _publisher is None:
        _publisher = RabbitMQPublisher()
        await _publisher.connect()
    elif not _publisher.is_connected:
        await _publisher.connect()

    return _publisher


async def close_publisher() -> None:
    """
    Close global publisher instance.
    """
    global _publisher

    if _publisher is not None:
        await _publisher.close()
        _publisher = None

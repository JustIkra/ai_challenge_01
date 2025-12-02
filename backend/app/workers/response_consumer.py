"""
Background consumer for processing Gemini responses from RabbitMQ.
"""

import asyncio
import json
import logging
from typing import Any

import aio_pika
from aio_pika import Connection, Channel, IncomingMessage
from pydantic import ValidationError

from app.config import settings
from app.db.session import async_session_maker
from app.schemas.rabbitmq import GeminiResponseMessage
from app.services.chat import ChatService

logger = logging.getLogger(__name__)


class ResponseConsumer:
    """
    Background worker for consuming Gemini responses from RabbitMQ.

    Listens to gemini.responses queue and updates message status in database.
    """

    def __init__(self, max_retries: int = 5, retry_delay: float = 1.0):
        """
        Initialize response consumer.

        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.url = settings.RABBITMQ_URL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection: Connection | None = None
        self.channel: Channel | None = None
        self._running = False
        self._consumer_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """
        Establish connection to RabbitMQ with exponential backoff retry.

        Raises:
            ConnectionError: If connection fails after max retries
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Consumer connecting to RabbitMQ (attempt {attempt}/{self.max_retries})...")
                self.connection = await aio_pika.connect_robust(
                    self.url,
                    timeout=10.0
                )
                self.channel = await self.connection.channel()

                # Set QoS - process one message at a time
                await self.channel.set_qos(prefetch_count=1)

                # Declare queue (idempotent)
                await self.channel.declare_queue(
                    "gemini.responses",
                    durable=True
                )

                logger.info("Consumer successfully connected to RabbitMQ")
                return

            except Exception as e:
                logger.error(f"Consumer failed to connect to RabbitMQ (attempt {attempt}/{self.max_retries}): {e}")

                if attempt == self.max_retries:
                    raise ConnectionError(f"Failed to connect to RabbitMQ after {self.max_retries} attempts") from e

                # Exponential backoff
                delay = self.retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    async def start(self) -> None:
        """
        Start consuming messages from gemini.responses queue.

        Runs in background until stop() is called.
        """
        if self._running:
            logger.warning("Consumer is already running")
            return

        await self.connect()

        if not self.channel:
            raise RuntimeError("Consumer channel is not initialized")

        self._running = True
        logger.info("Starting response consumer...")

        try:
            # Get queue
            queue = await self.channel.get_queue("gemini.responses")

            # Start consuming
            async with queue.iterator() as queue_iter:
                logger.info("Consumer is now listening for messages")
                async for message in queue_iter:
                    if not self._running:
                        logger.info("Consumer stopped, breaking message loop")
                        break

                    await self._handle_message(message)

        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
            raise
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise
        finally:
            self._running = False

    async def _handle_message(self, message: IncomingMessage) -> None:
        """
        Handle incoming message from queue.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process(ignore_processed=True):
            try:
                # Parse message body
                body = message.body.decode()
                logger.debug(f"Received message: {body[:200]}...")

                # Validate message schema
                try:
                    response = GeminiResponseMessage.model_validate_json(body)
                except ValidationError as e:
                    logger.error(f"Invalid message schema: {e}")
                    await message.ack()
                    return

                # Process response
                await self.process_response(response)

                # Acknowledge message
                await message.ack()
                logger.info(f"Successfully processed response: request_id={response.request_id}")

            except Exception as e:
                logger.error(f"Error handling message: {e}")
                # Reject and requeue if processing fails
                await message.nack(requeue=False)

    async def process_response(self, response: GeminiResponseMessage) -> None:
        """
        Process Gemini response and update message in database.

        Args:
            response: Validated Gemini response message
        """
        try:
            # Create new database session
            async with async_session_maker() as db:
                # Find message by request_id
                message = await ChatService.get_message_by_request_id(db, response.request_id)

                if not message:
                    logger.error(f"Message not found for request_id={response.request_id}")
                    return

                # Update message based on response status
                if response.status == "success":
                    message.content = response.content or ""
                    message.status = "completed"
                    message.token_usage = response.usage.model_dump() if response.usage else None
                    logger.info(
                        f"Message completed: request_id={response.request_id}, "
                        f"tokens={response.usage.prompt_tokens + response.usage.completion_tokens if response.usage else 0}"
                    )
                elif response.status == "error":
                    message.status = "error"
                    message.content = f"Error: {response.error}"
                    logger.error(f"Message failed: request_id={response.request_id}, error={response.error}")

                # Commit changes
                await db.commit()

        except Exception as e:
            logger.error(f"Error processing response for request_id={response.request_id}: {e}")
            raise

    async def stop(self) -> None:
        """
        Stop consuming messages and close connection gracefully.
        """
        logger.info("Stopping response consumer...")
        self._running = False

        # Cancel consumer task if running
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        # Close connection
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("Consumer RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing consumer connection: {e}")

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running


# Global consumer instance
_consumer: ResponseConsumer | None = None


async def get_consumer() -> ResponseConsumer:
    """
    Get or create global consumer instance.

    Returns:
        ResponseConsumer: Consumer instance
    """
    global _consumer

    if _consumer is None:
        _consumer = ResponseConsumer()

    return _consumer


async def start_consumer() -> None:
    """
    Start global consumer instance in background.
    """
    consumer = await get_consumer()
    if not consumer.is_running:
        consumer._consumer_task = asyncio.create_task(consumer.start())
        logger.info("Consumer background task started")


async def stop_consumer() -> None:
    """
    Stop global consumer instance.
    """
    global _consumer

    if _consumer is not None:
        await _consumer.stop()
        _consumer = None

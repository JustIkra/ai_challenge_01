"""RabbitMQ async consumer for request messages."""
import json
import logging
import time
from datetime import datetime
from typing import Callable, Optional

import aio_pika
from aio_pika import Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractIncomingMessage,
    AbstractQueue,
)

from ..schemas.request import GeminiRequestMessage
from ..schemas.response import GeminiResponseMessage

logger = logging.getLogger(__name__)


class AsyncConsumer:
    """Async consumer for reading requests from RabbitMQ."""

    def __init__(
        self,
        rabbitmq_url: str,
        queue_name: str,
        prefetch_count: int = 10,
    ):
        """Initialize consumer.

        Args:
            rabbitmq_url: RabbitMQ connection URL
            queue_name: Queue name to consume from
            prefetch_count: Number of messages to prefetch
        """
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count

        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                timeout=30,
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.prefetch_count)

            # Declare queue (idempotent)
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True,
            )

            logger.info(
                f"AsyncConsumer connected to RabbitMQ, "
                f"queue '{self.queue_name}', prefetch={self.prefetch_count}"
            )

        except Exception as e:
            logger.error(f"Failed to connect AsyncConsumer to RabbitMQ: {e}")
            raise

    async def start_consuming(
        self,
        message_handler: Callable[[GeminiRequestMessage, AbstractIncomingMessage], None],
    ) -> None:
        """Start consuming messages from queue.

        Args:
            message_handler: Async callback function to handle messages.
                            Should accept (request, raw_message) and be async.
        """
        if not self.queue:
            raise RuntimeError("Consumer not connected. Call connect() first.")

        logger.info(f"Starting to consume messages from '{self.queue_name}'")

        async def on_message(message: AbstractIncomingMessage) -> None:
            """Process incoming message."""
            request_id = None

            try:
                # Parse message body
                body = message.body.decode()
                data = json.loads(body)

                # Validate and parse request
                request = GeminiRequestMessage(**data)
                request_id = request.request_id

                logger.info(
                    f"[{request_id}] Received request "
                    f"(retry_count={request.retry_count}, "
                    f"model={request.model})"
                )

                # Call message handler
                await message_handler(request, message)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message JSON: {e}")
                await message.reject(requeue=False)

            except Exception as e:
                logger.error(
                    f"[{request_id}] Error processing message: {e}",
                    exc_info=True,
                )
                # Reject and don't requeue on unexpected errors
                await message.reject(requeue=False)

        # Start consuming
        await self.queue.consume(on_message)

    async def requeue_with_delay(
        self,
        request: GeminiRequestMessage,
        message: AbstractIncomingMessage,
        delay_seconds: int,
    ) -> None:
        """Requeue message with delay using message TTL.

        Args:
            request: Request message
            message: Original RabbitMQ message
            delay_seconds: Delay in seconds before message becomes available again
        """
        try:
            if not self.channel:
                raise RuntimeError("Channel not initialized")

            # Increment retry count
            request.retry_count += 1
            request.timestamp = datetime.utcnow()

            # Create delayed message
            new_message = Message(
                body=request.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=str(request.request_id),
                expiration=str(delay_seconds * 1000),  # Convert to milliseconds
            )

            # Create delay queue name
            delay_queue_name = f"{self.queue_name}.delay.{delay_seconds}s"

            # Declare delay queue with DLX pointing back to main queue
            delay_queue = await self.channel.declare_queue(
                delay_queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": self.queue_name,
                    "x-message-ttl": delay_seconds * 1000,
                },
            )

            # Publish to delay queue
            await self.channel.default_exchange.publish(
                new_message,
                routing_key=delay_queue_name,
            )

            # Acknowledge original message
            await message.ack()

            logger.info(
                f"[{request.request_id}] Requeued with {delay_seconds}s delay "
                f"(retry_count={request.retry_count})"
            )

        except Exception as e:
            logger.error(
                f"[{request.request_id}] Failed to requeue message: {e}",
                exc_info=True,
            )
            # Reject message on requeue failure
            await message.reject(requeue=False)

    async def close(self) -> None:
        """Close connection to RabbitMQ."""
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()

            logger.info("AsyncConsumer disconnected from RabbitMQ")

        except Exception as e:
            logger.error(f"Error closing AsyncConsumer connection: {e}")

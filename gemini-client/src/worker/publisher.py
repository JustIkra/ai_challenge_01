"""RabbitMQ async publisher for response messages."""
import json
import logging
from typing import Optional

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractConnection

from ..schemas.response import GeminiResponseMessage

logger = logging.getLogger(__name__)


class AsyncPublisher:
    """Async publisher for sending responses to RabbitMQ."""

    def __init__(self, rabbitmq_url: str):
        """Initialize publisher.

        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                timeout=30,
            )
            self.channel = await self.connection.channel()

            logger.info("AsyncPublisher connected to RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to connect AsyncPublisher to RabbitMQ: {e}")
            raise

    async def publish(
        self,
        response: GeminiResponseMessage,
        queue_name: str,
    ) -> None:
        """Publish response message to queue.

        Args:
            response: Response message to publish
            queue_name: Target queue name

        Raises:
            Exception: If publishing fails
        """
        if not self.channel:
            raise RuntimeError("Publisher not connected. Call connect() first.")

        try:
            # Serialize response to JSON
            message_body = response.model_dump_json().encode()

            # Create message
            message = Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                correlation_id=str(response.request_id),
            )

            # Declare queue (idempotent)
            await self.channel.declare_queue(
                queue_name,
                durable=True,
            )

            # Publish to queue
            await self.channel.default_exchange.publish(
                message,
                routing_key=queue_name,
            )

            logger.info(
                f"Published response for request {response.request_id} "
                f"to queue '{queue_name}' (status: {response.status})"
            )

        except Exception as e:
            logger.error(
                f"Failed to publish response for request {response.request_id}: {e}"
            )
            raise

    async def close(self) -> None:
        """Close connection to RabbitMQ."""
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()

            logger.info("AsyncPublisher disconnected from RabbitMQ")

        except Exception as e:
            logger.error(f"Error closing AsyncPublisher connection: {e}")

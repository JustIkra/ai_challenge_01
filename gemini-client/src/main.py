"""Main entry point for Gemini Client Worker."""
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

from aio_pika.abc import AbstractIncomingMessage

from .client.gemini import GeminiAsyncClient
from .client.key_manager import KeyManager
from .config import settings
from .schemas.request import GeminiRequestMessage
from .schemas.response import GeminiResponseMessage
from .utils.logging import setup_logging
from .utils.retry import RateLimitError
from .worker.consumer import AsyncConsumer
from .worker.publisher import AsyncPublisher

logger = logging.getLogger(__name__)


class GeminiWorker:
    """Main worker class for processing Gemini API requests."""

    def __init__(self):
        """Initialize worker components."""
        self.consumer: Optional[AsyncConsumer] = None
        self.publisher: Optional[AsyncPublisher] = None
        self.gemini_client: Optional[GeminiAsyncClient] = None
        self.key_manager: Optional[KeyManager] = None
        self.shutdown_event = asyncio.Event()
        self.retry_delays = settings.get_retry_delays()

    async def setup(self) -> None:
        """Setup worker components."""
        logger.info("Setting up Gemini Worker...")

        # Initialize key manager
        api_keys = settings.get_api_keys()
        self.key_manager = KeyManager(
            api_keys=api_keys,
            max_per_minute=settings.KEYS_MAX_PER_MINUTE,
            cooldown_seconds=settings.KEYS_COOLDOWN_SECONDS,
        )

        # Initialize Gemini client
        self.gemini_client = GeminiAsyncClient(
            proxy_url=settings.HTTP_PROXY,
        )

        # Initialize consumer
        self.consumer = AsyncConsumer(
            rabbitmq_url=settings.RABBITMQ_URL,
            queue_name=settings.REQUEST_QUEUE,
            prefetch_count=settings.WORKER_PREFETCH_COUNT,
        )
        await self.consumer.connect()

        # Initialize publisher
        self.publisher = AsyncPublisher(
            rabbitmq_url=settings.RABBITMQ_URL,
        )
        await self.publisher.connect()

        logger.info("Gemini Worker setup complete")

    async def process_request(
        self,
        request: GeminiRequestMessage,
        message: AbstractIncomingMessage,
    ) -> None:
        """Process a single request message.

        Args:
            request: Request message
            message: Raw RabbitMQ message
        """
        start_time = time.time()
        request_id = str(request.request_id)

        try:
            # Get available API key
            api_key = await self.key_manager.get_available_key()

            if not api_key:
                # No keys available - requeue with escalating delay
                await self._handle_no_keys_available(request, message)
                return

            # Generate content
            try:
                content, usage = await self.gemini_client.generate_content(
                    api_key=api_key,
                    prompt=request.prompt,
                    model=request.model,
                    parameters=request.parameters,
                    request_id=request_id,
                    system_instruction=request.system_instruction,
                )

                # Send success response
                processing_time_ms = (time.time() - start_time) * 1000
                response = GeminiResponseMessage(
                    request_id=request.request_id,
                    status="success",
                    content=content,
                    usage=usage,
                    processing_time_ms=processing_time_ms,
                    model_used=request.model,
                    metadata=request.metadata,
                )

                await self.publisher.publish(response, request.callback_queue)
                await message.ack()

                logger.info(
                    f"[{request_id}] Request processed successfully | "
                    f"model={request.model} | "
                    f"prompt_tokens={usage.prompt_tokens} | "
                    f"completion_tokens={usage.completion_tokens} | "
                    f"total_tokens={usage.total_tokens} | "
                    f"time_ms={processing_time_ms:.2f}"
                )

            except RateLimitError as e:
                # Mark key as rate limited
                await self.key_manager.mark_rate_limited(api_key)

                # Try to get another key
                retry_key = await self.key_manager.get_available_key()

                if retry_key:
                    logger.info(f"[{request_id}] Retrying with different key...")
                    # Retry with different key (recursive call)
                    await self.process_request(request, message)
                else:
                    # No more keys - requeue with delay
                    await self._handle_no_keys_available(request, message)

        except Exception as e:
            # Send error response
            processing_time_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] Unexpected error processing request: {e}",
                exc_info=True,
            )

            response = GeminiResponseMessage(
                request_id=request.request_id,
                status="error",
                error=str(e),
                processing_time_ms=processing_time_ms,
                metadata=request.metadata,
            )

            await self.publisher.publish(response, request.callback_queue)
            await message.ack()

    async def _handle_no_keys_available(
        self,
        request: GeminiRequestMessage,
        message: AbstractIncomingMessage,
    ) -> None:
        """Handle case when no API keys are available.

        Args:
            request: Request message
            message: Raw RabbitMQ message
        """
        request_id = str(request.request_id)

        # Check if max retries exceeded
        if request.retry_count >= settings.QUEUE_MAX_RETRIES:
            logger.error(
                f"[{request_id}] Max retries ({settings.QUEUE_MAX_RETRIES}) exceeded"
            )

            # Send error response
            response = GeminiResponseMessage(
                request_id=request.request_id,
                status="error",
                error=f"Rate limit exceeded after {settings.QUEUE_MAX_RETRIES} retries",
                metadata=request.metadata,
            )

            await self.publisher.publish(response, request.callback_queue)
            await message.ack()
            return

        # Get delay for current retry count
        delay_seconds = self.retry_delays[
            min(request.retry_count, len(self.retry_delays) - 1)
        ]

        logger.warning(
            f"[{request_id}] No keys available. "
            f"Requeuing with {delay_seconds}s delay "
            f"(retry {request.retry_count + 1}/{settings.QUEUE_MAX_RETRIES})"
        )

        # Requeue with delay
        await self.consumer.requeue_with_delay(request, message, delay_seconds)

    async def run(self) -> None:
        """Run the worker."""
        await self.setup()

        logger.info("Starting Gemini Worker...")

        # Start consuming messages
        await self.consumer.start_consuming(self.process_request)

        # Wait for shutdown signal
        await self.shutdown_event.wait()

    async def shutdown(self) -> None:
        """Shutdown worker gracefully."""
        logger.info("Shutting down Gemini Worker...")

        self.shutdown_event.set()

        # Close connections
        if self.consumer:
            await self.consumer.close()
        if self.publisher:
            await self.publisher.close()
        if self.gemini_client:
            await self.gemini_client.close()

        logger.info("Gemini Worker shutdown complete")


async def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)

    logger.info("=" * 60)
    logger.info("Gemini Client Worker")
    logger.info("=" * 60)
    logger.info(f"Request queue: {settings.REQUEST_QUEUE}")
    logger.info(f"Response queue: {settings.RESPONSE_QUEUE}")
    logger.info(f"API keys count: {len(settings.get_api_keys())}")
    logger.info(f"Max requests per key: {settings.KEYS_MAX_PER_MINUTE}/min")
    logger.info(f"Default model: {settings.OPENROUTER_MODEL}")
    logger.info(f"HTTP proxy: {settings.HTTP_PROXY or 'disabled'}")
    logger.info("=" * 60)

    # Create worker
    worker = GeminiWorker()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig: int) -> None:
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        # Run worker
        await worker.run()

    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        await worker.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        sys.exit(0)

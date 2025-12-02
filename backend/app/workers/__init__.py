"""
Background workers for processing RabbitMQ messages.
"""

from app.workers.response_consumer import ResponseConsumer

__all__ = ["ResponseConsumer"]

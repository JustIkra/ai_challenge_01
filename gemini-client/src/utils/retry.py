"""Retry utilities for handling API errors."""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Type

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Exception raised when API rate limit is hit."""

    pass


class LocationError(Exception):
    """Exception raised when API rejects due to unsupported location."""

    pass


class APIError(Exception):
    """General API error."""

    pass


def with_rate_limit_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> Callable:
    """Decorator for retrying functions on rate limit errors with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except (RateLimitError, LocationError) as e:
                    last_exception = e
                    error_type = "Rate limit" if isinstance(e, RateLimitError) else "Location error"

                    if attempt < max_retries:
                        # Calculate exponential backoff delay
                        delay = min(
                            base_delay * (exponential_base**attempt),
                            max_delay,
                        )

                        logger.warning(
                            f"{error_type} in {func.__name__} "
                            f"(attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{error_type} retry exhausted for {func.__name__} "
                            f"after {max_retries} attempts"
                        )
                        raise

                except Exception as e:
                    # Don't retry on other exceptions
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def exponential_backoff_sleep(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> None:
    """Sleep with exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
    """
    delay = min(base_delay * (exponential_base**attempt), max_delay)
    logger.debug(f"Exponential backoff sleep: {delay:.2f}s (attempt {attempt})")
    await asyncio.sleep(delay)

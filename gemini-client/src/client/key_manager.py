"""Key manager for API key rotation and rate limiting."""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class KeyState:
    """State tracking for a single API key."""

    key: str
    usage_count: int = 0
    last_reset: float = field(default_factory=time.time)
    cooldown_until: float = 0.0
    total_requests: int = 0
    rate_limit_count: int = 0

    def is_available(self, max_per_minute: int, current_time: float) -> bool:
        """Check if key is available for use."""
        # Check if in cooldown
        if current_time < self.cooldown_until:
            return False

        # Check if usage count exceeded
        if self.usage_count >= max_per_minute:
            return False

        return True

    def reset_if_needed(self, current_time: float) -> None:
        """Reset usage counter if one minute has passed."""
        time_since_reset = current_time - self.last_reset
        if time_since_reset >= 60.0:
            self.usage_count = 0
            self.last_reset = current_time
            logger.debug(
                f"Reset usage counter for key {self.key[:8]}... "
                f"(total requests: {self.total_requests})"
            )

    def increment_usage(self) -> None:
        """Increment usage counter."""
        self.usage_count += 1
        self.total_requests += 1

    def mark_rate_limited(self, cooldown_seconds: int, current_time: float) -> None:
        """Mark key as rate limited and set cooldown."""
        self.cooldown_until = current_time + cooldown_seconds
        self.rate_limit_count += 1
        logger.warning(
            f"Key {self.key[:8]}... rate limited. "
            f"Cooldown until {self.cooldown_until:.2f} "
            f"(rate limit count: {self.rate_limit_count})"
        )


class KeyManager:
    """Manager for API key rotation with rate limiting."""

    def __init__(
        self,
        api_keys: list[str],
        max_per_minute: int = 10,
        cooldown_seconds: int = 60,
    ):
        """Initialize key manager.

        Args:
            api_keys: List of API keys to rotate
            max_per_minute: Maximum requests per minute per key
            cooldown_seconds: Cooldown period after rate limit hit
        """
        if not api_keys:
            raise ValueError("At least one API key must be provided")

        self.keys = [KeyState(key=key) for key in api_keys]
        self.max_per_minute = max_per_minute
        self.cooldown_seconds = cooldown_seconds
        self.current_index = 0
        self._lock = asyncio.Lock()

        logger.info(
            f"KeyManager initialized with {len(self.keys)} keys, "
            f"max {max_per_minute} req/min, {cooldown_seconds}s cooldown"
        )

    async def get_available_key(self) -> Optional[str]:
        """Get next available API key using round-robin rotation.

        Returns:
            API key if available, None if all keys are unavailable
        """
        async with self._lock:
            current_time = time.time()

            # Reset usage counters if needed
            for key_state in self.keys:
                key_state.reset_if_needed(current_time)

            # Try round-robin starting from current index
            attempts = 0
            while attempts < len(self.keys):
                key_state = self.keys[self.current_index]

                if key_state.is_available(self.max_per_minute, current_time):
                    key_state.increment_usage()
                    result_key = key_state.key
                    result_index = self.current_index

                    # Move to next key for next request
                    self.current_index = (self.current_index + 1) % len(self.keys)

                    logger.debug(
                        f"Selected key index {result_index} "
                        f"(usage: {key_state.usage_count}/{self.max_per_minute})"
                    )
                    return result_key

                # Move to next key
                self.current_index = (self.current_index + 1) % len(self.keys)
                attempts += 1

            # No available keys
            logger.warning("No available API keys at the moment")
            self._log_keys_status(current_time)
            return None

    async def mark_rate_limited(self, key: str) -> None:
        """Mark a key as rate limited.

        Args:
            key: API key that hit rate limit
        """
        async with self._lock:
            current_time = time.time()
            for key_state in self.keys:
                if key_state.key == key:
                    key_state.mark_rate_limited(self.cooldown_seconds, current_time)
                    return

            logger.warning(f"Attempted to mark unknown key as rate limited: {key[:8]}...")

    def _log_keys_status(self, current_time: float) -> None:
        """Log status of all keys for debugging."""
        status_lines = ["API Keys Status:"]
        for i, key_state in enumerate(self.keys):
            cooldown_remaining = max(0, key_state.cooldown_until - current_time)
            status_lines.append(
                f"  Key {i} ({key_state.key[:8]}...): "
                f"usage={key_state.usage_count}/{self.max_per_minute}, "
                f"cooldown={cooldown_remaining:.1f}s, "
                f"total={key_state.total_requests}, "
                f"rate_limits={key_state.rate_limit_count}"
            )
        logger.info("\n".join(status_lines))

    async def get_stats(self) -> dict:
        """Get statistics for all keys.

        Returns:
            Dictionary with key statistics
        """
        async with self._lock:
            current_time = time.time()
            return {
                "total_keys": len(self.keys),
                "available_keys": sum(
                    1
                    for k in self.keys
                    if k.is_available(self.max_per_minute, current_time)
                ),
                "keys": [
                    {
                        "key_prefix": k.key[:8] + "...",
                        "usage_count": k.usage_count,
                        "total_requests": k.total_requests,
                        "rate_limit_count": k.rate_limit_count,
                        "cooldown_remaining": max(0, k.cooldown_until - current_time),
                        "is_available": k.is_available(self.max_per_minute, current_time),
                    }
                    for k in self.keys
                ],
            }

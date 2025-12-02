"""Configuration settings for gemini-client worker."""
import os
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # RabbitMQ configuration
    RABBITMQ_URL: str = Field(
        ...,
        description="RabbitMQ connection URL (amqp://user:pass@host:port/vhost)",
    )
    REQUEST_QUEUE: str = Field(
        default="gemini.requests",
        description="Queue name for incoming requests",
    )
    RESPONSE_QUEUE: str = Field(
        default="gemini.responses",
        description="Queue name for responses",
    )

    # Gemini API configuration
    GEMINI_API_KEYS: str = Field(
        ...,
        description="Comma-separated list of Gemini API keys",
    )
    GEMINI_MODEL_TEXT: str = Field(
        default="gemini-2.5-flash",
        description="Default Gemini model for text generation",
    )
    KEYS_MAX_PER_MINUTE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum requests per minute per API key",
    )
    KEYS_COOLDOWN_SECONDS: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Cooldown period in seconds after rate limit (429)",
    )

    # Queue retry configuration
    QUEUE_RETRY_DELAYS: str = Field(
        default="60,600,3600,86400",
        description="Comma-separated retry delays in seconds (escalating)",
    )
    QUEUE_MAX_RETRIES: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Maximum number of retries before sending error response",
    )

    # HTTP proxy configuration
    HTTP_PROXY: str | None = Field(
        default=None,
        description="HTTP/HTTPS proxy URL (e.g., http://proxy:port or socks5://proxy:port)",
    )

    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Worker configuration
    WORKER_PREFETCH_COUNT: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of messages to prefetch from RabbitMQ",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("GEMINI_API_KEYS")
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        """Validate that at least one API key is provided."""
        keys = [k.strip() for k in v.split(",") if k.strip()]
        if not keys:
            raise ValueError("At least one GEMINI_API_KEY must be provided")
        return v

    @field_validator("QUEUE_RETRY_DELAYS")
    @classmethod
    def validate_retry_delays(cls, v: str) -> str:
        """Validate retry delays format."""
        try:
            delays = [int(d.strip()) for d in v.split(",") if d.strip()]
            if not delays:
                raise ValueError("At least one retry delay must be provided")
            if any(d < 0 for d in delays):
                raise ValueError("Retry delays must be non-negative")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid QUEUE_RETRY_DELAYS format: {e}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    def get_api_keys(self) -> list[str]:
        """Get list of API keys."""
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]

    def get_retry_delays(self) -> list[int]:
        """Get list of retry delays in seconds."""
        return [int(d.strip()) for d in self.QUEUE_RETRY_DELAYS.split(",") if d.strip()]

    def get_proxy_config(self) -> dict[str, Any] | None:
        """Get proxy configuration for HTTP client."""
        if not self.HTTP_PROXY:
            return None

        # Set both http and https to the same proxy
        return {
            "http": self.HTTP_PROXY,
            "https": self.HTTP_PROXY,
        }


# Global settings instance
settings = Settings()

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

    # OpenRouter API configuration
    OPENROUTER_API_KEYS: str = Field(
        ...,
        description="Comma-separated list of OpenRouter API keys",
    )
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter base URL",
    )
    OPENROUTER_MODEL: str = Field(
        default="google/gemini-2.5-flash",
        description="Default OpenRouter model for generation",
    )
    OPENROUTER_SITE_URL: str | None = Field(
        default=None,
        description="Optional site URL for HTTP-Referer header",
    )
    OPENROUTER_SITE_NAME: str | None = Field(
        default=None,
        description="Optional site name for X-Title header",
    )

    # Legacy Gemini API configuration (backward compatibility)
    GEMINI_API_KEYS: str | None = Field(
        default=None,
        description="[DEPRECATED] Use OPENROUTER_API_KEYS instead. Comma-separated list of API keys",
    )
    GEMINI_MODEL_TEXT: str = Field(
        default="gemini-2.5-flash",
        description="[DEPRECATED] Use OPENROUTER_MODEL instead. Default model for text generation",
    )

    # Rate limiting configuration
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

    @field_validator("HTTP_PROXY", mode="before")
    @classmethod
    def validate_http_proxy(cls, v: str | None) -> str | None:
        """Convert empty string to None for HTTP_PROXY."""
        if v is None or v == "":
            return None
        return v

    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_FORMAT: str = Field(
        default="text",
        description="Logging format: 'text' for human-readable, 'json' for structured logging",
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

    @field_validator("OPENROUTER_API_KEYS")
    @classmethod
    def validate_openrouter_api_keys(cls, v: str) -> str:
        """Validate that at least one OpenRouter API key is provided."""
        keys = [k.strip() for k in v.split(",") if k.strip()]
        if not keys:
            raise ValueError("At least one OPENROUTER_API_KEY must be provided")
        return v

    @field_validator("GEMINI_API_KEYS")
    @classmethod
    def validate_gemini_api_keys(cls, v: str | None) -> str | None:
        """Validate legacy GEMINI_API_KEYS field (for backward compatibility)."""
        if v is None or v == "":
            return None
        keys = [k.strip() for k in v.split(",") if k.strip()]
        if not keys:
            return None
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

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = ["text", "json"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"LOG_FORMAT must be one of {valid_formats}")
        return v_lower

    def get_api_keys(self) -> list[str]:
        """Get list of API keys with backward compatibility fallback."""
        # Use OPENROUTER_API_KEYS as primary source
        keys_source = self.OPENROUTER_API_KEYS

        # Fallback to legacy GEMINI_API_KEYS if OPENROUTER_API_KEYS is not set
        if not keys_source and self.GEMINI_API_KEYS:
            keys_source = self.GEMINI_API_KEYS

        if not keys_source:
            return []

        return [k.strip() for k in keys_source.split(",") if k.strip()]

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

    def get_openrouter_headers(self) -> dict[str, str]:
        """Get headers for OpenRouter API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        # Add optional HTTP-Referer header
        if self.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = self.OPENROUTER_SITE_URL

        # Add optional X-Title header
        if self.OPENROUTER_SITE_NAME:
            headers["X-Title"] = self.OPENROUTER_SITE_NAME

        return headers


# Global settings instance
settings = Settings()

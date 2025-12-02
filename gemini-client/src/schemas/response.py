"""Response schemas for Gemini API."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)


class GeminiResponseMessage(BaseModel):
    """Message schema for gemini.responses queue."""

    request_id: UUID
    status: Literal["success", "error"]
    content: str | None = None
    error: str | None = None
    usage: TokenUsage | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float | None = Field(default=None, ge=0)
    model_used: str | None = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example_success": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "success",
                "content": "Python is a high-level programming language...",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 150,
                    "total_tokens": 160,
                },
                "processing_time_ms": 1234.56,
                "model_used": "gemini-pro",
            },
            "example_error": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "error",
                "error": "Rate limit exceeded after all retries",
                "processing_time_ms": 5000.0,
            },
        }

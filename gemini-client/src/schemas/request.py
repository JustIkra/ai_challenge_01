"""Request schemas for Gemini API."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationParameters(BaseModel):
    """Parameters for content generation."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=100)
    max_output_tokens: int = Field(default=8192, ge=1, le=32768)
    candidate_count: int = Field(default=1, ge=1, le=8)
    stop_sequences: list[str] | None = None


class GeminiRequestMessage(BaseModel):
    """Message schema for gemini.requests queue."""

    request_id: UUID
    prompt: str = Field(..., min_length=1)
    model: str = Field(default="gemini-2.5-flash")
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    callback_queue: str = Field(default="gemini.responses")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] | None = None
    system_instruction: str | None = None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "prompt": "Tell me about Python",
                "model": "gemini-2.5-flash",
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                },
                "callback_queue": "gemini.responses",
                "retry_count": 0,
            }
        }

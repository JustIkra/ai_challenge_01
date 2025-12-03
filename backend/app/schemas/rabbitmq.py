"""
RabbitMQ message schemas for Gemini integration.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GenerationParameters(BaseModel):
    """Parameters for text generation."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=8192, ge=1, le=32768)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=100)


class GeminiRequestMessage(BaseModel):
    """Message schema for gemini.requests queue."""

    request_id: uuid.UUID
    prompt: str
    model: str = "gemini-2.5-flash"
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    system_instruction: str | None = None
    callback_queue: str = "gemini.responses"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "prompt": "What is the capital of France?",
                "model": "gemini-2.5-flash",
                "parameters": {
                    "temperature": 0.7,
                    "max_output_tokens": 8192,
                    "top_p": 0.95,
                    "top_k": 40
                },
                "callback_queue": "gemini.responses",
                "timestamp": "2024-01-01T00:00:00Z",
                "retry_count": 0
            }
        }


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)


class GeminiResponseMessage(BaseModel):
    """Message schema for gemini.responses queue."""

    request_id: uuid.UUID
    status: Literal["success", "error"]
    content: str | None = None
    error: str | None = None
    usage: TokenUsage | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "success",
                "content": "The capital of France is Paris.",
                "error": None,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8
                },
                "timestamp": "2024-01-01T00:00:01Z"
            }
        }

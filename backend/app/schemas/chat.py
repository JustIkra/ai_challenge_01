"""
Chat Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.message import MessageResponse


class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    user_id: uuid.UUID = Field(..., description="User ID")
    title: str | None = Field(None, max_length=255, description="Optional chat title")
    system_prompt: str | None = Field(None, description="System instruction for AI")
    temperature: float | None = Field(0.7, description="Temperature for AI responses")
    history_compression_enabled: bool = Field(False, description="Enable history compression")
    history_compression_message_limit: int = Field(10, ge=5, le=50, description="Messages before compression")


class ChatUpdate(BaseModel):
    """Schema for updating a chat."""
    title: str | None = Field(None, max_length=255)
    system_prompt: str | None = Field(None)
    temperature: float | None = Field(None, description="Temperature for AI responses")
    history_compression_enabled: bool | None = Field(None)
    history_compression_message_limit: int | None = Field(None, ge=5, le=50)


class ChatResponse(BaseModel):
    """Schema for chat response."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    system_prompt: str | None
    temperature: float | None
    history_compression_enabled: bool
    history_compression_message_limit: int | None
    compressed_history_summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatWithMessages(ChatResponse):
    """Schema for chat response with messages."""
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

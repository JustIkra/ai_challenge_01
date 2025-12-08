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


class ChatUpdate(BaseModel):
    """Schema for updating a chat."""
    title: str | None = Field(None, max_length=255)
    system_prompt: str | None = Field(None)
    temperature: float | None = Field(None, description="Temperature for AI responses")


class ChatResponse(BaseModel):
    """Schema for chat response."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    system_prompt: str | None
    temperature: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatWithMessages(ChatResponse):
    """Schema for chat response with messages."""
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

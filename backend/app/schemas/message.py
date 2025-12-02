"""
Message Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Message role enum."""
    USER = "user"
    ASSISTANT = "assistant"


class MessageStatus(str, Enum):
    """Message status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    role: MessageRole = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., min_length=1, description="Message content")


class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    status: MessageStatus | None = None
    content: str | None = Field(None, min_length=1)
    token_usage: dict | None = None


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    content: str
    request_id: uuid.UUID | None
    status: str
    token_usage: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageSendRequest(BaseModel):
    """Schema for sending a message."""
    content: str = Field(..., min_length=1, description="Message content")


class MessageSendResponse(BaseModel):
    """Schema for message send response."""
    request_id: uuid.UUID
    status: str  # "pending"
    message: MessageResponse


class MessageStatusResponse(BaseModel):
    """Schema for message status response."""
    request_id: uuid.UUID
    status: str
    message: MessageResponse | None = None
    content: str | None = None
    error: str | None = None

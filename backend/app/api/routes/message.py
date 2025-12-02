"""
Message API routes.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.message import (
    MessageResponse,
    MessageSendRequest,
    MessageSendResponse,
    MessageStatusResponse,
)
from app.services.chat import ChatService
from app.services.rabbitmq import get_publisher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])


@router.post("/chats/{chat_id}/messages", response_model=MessageSendResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: uuid.UUID,
    message_data: MessageSendRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageSendResponse:
    """
    Send a message to a chat.

    This endpoint:
    1. Saves the user message to the database
    2. Creates an assistant message with status "pending"
    3. Generates a request_id for tracking
    4. Returns the request_id for polling

    Note: RabbitMQ integration will be added in TICKET-005.

    Args:
        chat_id: Chat ID
        message_data: Message content
        db: Database session

    Returns:
        MessageSendResponse: Response with request_id and status

    Raises:
        HTTPException: 404 if chat not found
    """
    # Verify chat exists
    chat = await ChatService.get_chat_by_id(db=db, chat_id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with id {chat_id} not found"
        )

    # Create user message
    user_message = await ChatService.create_message(
        db=db,
        chat_id=chat_id,
        role="user",
        content=message_data.content,
        status="completed"
    )

    # Generate request_id for assistant message tracking
    request_id = uuid.uuid4()

    # Create assistant message with pending status
    await ChatService.create_message(
        db=db,
        chat_id=chat_id,
        role="assistant",
        content="",
        request_id=request_id,
        status="pending"
    )

    # Build Gemini request message
    try:
        gemini_request = await ChatService.send_message_to_gemini(
            db=db,
            chat=chat,
            user_message=message_data.content,
            request_id=request_id
        )

        # Publish to RabbitMQ
        publisher = await get_publisher()
        await publisher.publish_request(gemini_request)

        logger.info(f"Published message to RabbitMQ: request_id={request_id}, chat_id={chat_id}")

    except Exception as e:
        logger.error(f"Failed to publish message to RabbitMQ: {e}")
        # Update message status to error
        message = await ChatService.get_message_by_request_id(db, request_id)
        if message:
            message.status = "error"
            message.content = f"Failed to queue request: {str(e)}"
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue message for processing"
        )

    return MessageSendResponse(
        request_id=request_id,
        status="pending",
        message=MessageResponse.model_validate(user_message)
    )


@router.get("/messages/{request_id}/status", response_model=MessageStatusResponse)
async def get_message_status(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> MessageStatusResponse:
    """
    Poll message status by request_id.

    Args:
        request_id: Request ID returned from send_message
        db: Database session

    Returns:
        MessageStatusResponse: Message status and content

    Raises:
        HTTPException: 404 if message not found
    """
    message = await ChatService.get_message_by_request_id(db=db, request_id=request_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with request_id {request_id} not found"
        )

    # Prepare response based on status
    error = None
    content = None

    if message.status == "completed":
        content = message.content
    elif message.status == "error":
        error = message.content or "Unknown error"

    return MessageStatusResponse(
        request_id=request_id,
        status=message.status,
        content=content,
        error=error,
        message=MessageResponse.model_validate(message)
    )

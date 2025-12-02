"""
Chat API routes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.chat import ChatCreate, ChatResponse, ChatUpdate, ChatWithMessages
from app.services.chat import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Create a new chat.

    Args:
        chat_data: Chat creation data
        db: Database session

    Returns:
        ChatResponse: Created chat
    """
    chat = await ChatService.create_chat(
        db=db,
        user_id=chat_data.user_id,
        chat_data=chat_data
    )
    return ChatResponse.model_validate(chat)


@router.get("", response_model=list[ChatResponse])
async def list_chats(
    user_id: uuid.UUID = Query(..., description="User ID to filter chats"),
    db: AsyncSession = Depends(get_db)
) -> list[ChatResponse]:
    """
    List all chats for a user.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        list[ChatResponse]: List of user's chats
    """
    chats = await ChatService.get_user_chats(db=db, user_id=user_id)
    return [ChatResponse.model_validate(chat) for chat in chats]


@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ChatWithMessages:
    """
    Get a chat by ID with all messages.

    Args:
        chat_id: Chat ID
        db: Database session

    Returns:
        ChatWithMessages: Chat with messages

    Raises:
        HTTPException: 404 if chat not found
    """
    chat = await ChatService.get_chat_by_id(db=db, chat_id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with id {chat_id} not found"
        )
    return ChatWithMessages.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: uuid.UUID,
    chat_data: ChatUpdate,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    Update chat settings.

    Args:
        chat_id: Chat ID
        chat_data: Chat update data
        db: Database session

    Returns:
        ChatResponse: Updated chat

    Raises:
        HTTPException: 404 if chat not found
    """
    chat = await ChatService.update_chat(db=db, chat_id=chat_id, chat_data=chat_data)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with id {chat_id} not found"
        )
    return ChatResponse.model_validate(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a chat by ID.

    Args:
        chat_id: Chat ID
        db: Database session

    Raises:
        HTTPException: 404 if chat not found
    """
    deleted = await ChatService.delete_chat(db=db, chat_id=chat_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with id {chat_id} not found"
        )

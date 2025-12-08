"""
Chat service for business logic operations.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.chat import Chat
from app.models.message import Message
from app.schemas.chat import ChatCreate, ChatUpdate
from app.schemas.rabbitmq import GeminiRequestMessage, GenerationParameters


class ChatService:
    """Service for managing chats."""

    @staticmethod
    async def create_chat(
        db: AsyncSession,
        user_id: uuid.UUID,
        chat_data: ChatCreate
    ) -> Chat:
        """
        Create a new chat.

        Args:
            db: Database session
            user_id: User ID
            chat_data: Chat creation data

        Returns:
            Chat: Created chat instance
        """
        chat = Chat(
            user_id=user_id,
            title=chat_data.title,
            system_prompt=chat_data.system_prompt,
            temperature=chat_data.temperature
        )
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

    @staticmethod
    async def get_user_chats(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> list[Chat]:
        """
        Get all chats for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            list[Chat]: List of user's chats
        """
        result = await db.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_chat_by_id(
        db: AsyncSession,
        chat_id: uuid.UUID
    ) -> Chat | None:
        """
        Get chat by ID with messages.

        Args:
            db: Database session
            chat_id: Chat ID

        Returns:
            Chat | None: Chat instance or None if not found
        """
        result = await db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.messages))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_chat(
        db: AsyncSession,
        chat_id: uuid.UUID,
        chat_data: ChatUpdate
    ) -> Chat | None:
        """
        Update chat settings.

        Args:
            db: Database session
            chat_id: Chat ID
            chat_data: Chat update data

        Returns:
            Chat | None: Updated chat instance or None if not found
        """
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()

        if not chat:
            return None

        update_data = chat_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chat, field, value)

        await db.commit()
        await db.refresh(chat)
        return chat

    @staticmethod
    async def delete_chat(
        db: AsyncSession,
        chat_id: uuid.UUID
    ) -> bool:
        """
        Delete a chat by ID.

        Args:
            db: Database session
            chat_id: Chat ID

        Returns:
            bool: True if chat was deleted, False if not found
        """
        result = await db.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()

        if not chat:
            return False

        await db.delete(chat)
        await db.commit()
        return True

    @staticmethod
    async def create_message(
        db: AsyncSession,
        chat_id: uuid.UUID,
        role: str,
        content: str,
        request_id: uuid.UUID | None = None,
        status: str = "pending"
    ) -> Message:
        """
        Create a new message in a chat.

        Args:
            db: Database session
            chat_id: Chat ID
            role: Message role ('user' or 'assistant')
            content: Message content
            request_id: Optional request ID for tracking
            status: Message status (default: 'pending')

        Returns:
            Message: Created message instance
        """
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            request_id=request_id,
            status=status
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_message_by_request_id(
        db: AsyncSession,
        request_id: uuid.UUID
    ) -> Message | None:
        """
        Get message by request ID.

        Args:
            db: Database session
            request_id: Request ID

        Returns:
            Message | None: Message instance or None if not found
        """
        result = await db.execute(
            select(Message).where(Message.request_id == request_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def send_message_to_gemini(
        db: AsyncSession,
        chat: Chat,
        user_message: str,
        request_id: uuid.UUID
    ) -> GeminiRequestMessage:
        """
        Build and return a GeminiRequestMessage for sending to RabbitMQ.

        Args:
            db: Database session
            chat: Chat instance with messages
            user_message: Current user message
            request_id: Request ID for tracking

        Returns:
            GeminiRequestMessage: Message ready to publish to RabbitMQ
        """
        # Build conversation history
        conversation_parts = []

        # Add previous messages from chat history
        if chat.messages:
            for msg in chat.messages:
                if msg.status == "completed" and msg.content:
                    role = "User" if msg.role == "user" else "Assistant"
                    conversation_parts.append(f"{role}: {msg.content}")

        # Add current user message
        conversation_parts.append(f"User: {user_message}")

        # Build the full prompt
        prompt = "\n\n".join(conversation_parts)

        # Add instruction for assistant response
        prompt += "\n\nAssistant:"

        return GeminiRequestMessage(
            request_id=request_id,
            prompt=prompt,
            model=settings.GEMINI_MODEL_TEXT,
            parameters=GenerationParameters(temperature=chat.temperature or 0.7),
            system_instruction=chat.system_prompt
        )

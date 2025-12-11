"""
History compression service for chat conversations.
"""

import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.message import Message
from app.config import settings
from app.schemas.rabbitmq import GeminiRequestMessage, GenerationParameters


COMPRESSION_SYSTEM_PROMPT = """You are a conversation summarizer. Your task is to create a concise summary of the conversation history.

Rules:
1. Preserve key facts, decisions, and important context
2. Keep the summary under 500 words
3. Use bullet points for clarity
4. Include any specific names, numbers, or technical details mentioned
5. Maintain the chronological flow of the conversation
6. Focus on information that would be useful for continuing the conversation

Output format:
- Start with a one-sentence overview
- Follow with bullet points of key points
- End with any pending questions or topics"""


class CompressionService:
    """Service for compressing chat history."""

    @staticmethod
    async def should_compress(db: AsyncSession, chat: Chat) -> bool:
        """
        Check if chat history should be compressed.

        Returns True if compression is enabled and uncompressed message count >= limit.
        """
        if not chat.history_compression_enabled:
            return False

        limit = chat.history_compression_message_limit or 10

        # Count uncompressed completed messages
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat.id)
            .where(Message.status == "completed")
            .where(Message.is_compressed == False)
        )
        uncompressed_messages = result.scalars().all()

        return len(uncompressed_messages) >= limit

    @staticmethod
    async def get_messages_for_compression(
        db: AsyncSession,
        chat_id: uuid.UUID
    ) -> list[Message]:
        """Get uncompressed messages that should be compressed."""
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .where(Message.status == "completed")
            .where(Message.is_compressed == False)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    def build_compression_prompt(messages: list[Message]) -> str:
        """Build a prompt for the AI to summarize the conversation."""
        conversation_parts = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            conversation_parts.append(f"{role}: {msg.content}")

        conversation_text = "\n\n".join(conversation_parts)

        return f"""Please summarize the following conversation:

{conversation_text}

Provide a concise summary following the rules in your instructions."""

    @staticmethod
    async def build_compression_request(
        db: AsyncSession,
        chat: Chat,
        request_id: uuid.UUID
    ) -> GeminiRequestMessage | None:
        """
        Build a GeminiRequestMessage for generating a summary.

        Returns None if compression is not needed.
        """
        messages = await CompressionService.get_messages_for_compression(db, chat.id)

        if not messages:
            return None

        prompt = CompressionService.build_compression_prompt(messages)

        return GeminiRequestMessage(
            request_id=request_id,
            prompt=prompt,
            model=settings.OPENROUTER_MODEL,
            parameters=GenerationParameters(temperature=0.3),  # Lower temp for consistent summaries
            system_instruction=COMPRESSION_SYSTEM_PROMPT
        )

    @staticmethod
    async def apply_compression(
        db: AsyncSession,
        chat_id: uuid.UUID,
        summary: str
    ) -> None:
        """
        Apply compression: save summary and mark messages as compressed.

        Args:
            db: Database session
            chat_id: Chat ID
            summary: Generated summary text
        """
        # Update chat with summary
        await db.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .values(compressed_history_summary=summary)
        )

        # Mark all uncompressed messages as compressed
        await db.execute(
            update(Message)
            .where(Message.chat_id == chat_id)
            .where(Message.is_compressed == False)
            .where(Message.status == "completed")
            .values(is_compressed=True)
        )

        await db.commit()

    @staticmethod
    async def get_uncompressed_message_count(
        db: AsyncSession,
        chat_id: uuid.UUID
    ) -> int:
        """Get count of uncompressed completed messages."""
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .where(Message.status == "completed")
            .where(Message.is_compressed == False)
        )
        return len(result.scalars().all())

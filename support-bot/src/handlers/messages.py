"""Text message handler with RAG + LLM processing."""

import logging
from typing import List

from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType, ChatAction

from src.config import get_config
from src.services.rag_client import RAGClient, RAGResult
from src.services.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = Router()

# Initialize clients lazily
_rag_client: RAGClient = None
_llm_client: LLMClient = None


def get_rag_client() -> RAGClient:
    """Get or create RAG client."""
    global _rag_client
    if _rag_client is None:
        config = get_config()
        _rag_client = RAGClient(config.rag_server_url)
    return _rag_client


def get_llm_client() -> LLMClient:
    """Get or create LLM client."""
    global _llm_client
    if _llm_client is None:
        config = get_config()
        _llm_client = LLMClient(
            api_keys=config.openrouter_api_keys,
            base_url=config.openrouter_base_url,
            model=config.openrouter_model,
        )
    return _llm_client


def build_llm_prompt(question: str, rag_results: List[RAGResult]) -> str:
    """Build user prompt with RAG context.

    Args:
        question: User's question
        rag_results: List of RAG search results

    Returns:
        Formatted prompt for LLM
    """
    context_parts = []

    if rag_results:
        context_parts.append("Контекст из документации:\n")
        for i, result in enumerate(rag_results, 1):
            context_parts.append(f"--- Источник {i}: {result.file_name} ---")
            # Truncate long content
            content = result.content
            if len(content) > 1500:
                content = content[:1500] + "..."
            context_parts.append(content)
            context_parts.append("")

    context_parts.append(f"Вопрос пользователя: {question}")

    return "\n".join(context_parts)


def format_response(llm_response: str, sources: List[str], max_length: int) -> str:
    """Format LLM response with sources.

    Args:
        llm_response: Raw LLM response
        sources: List of source file names
        max_length: Maximum response length

    Returns:
        Formatted response string
    """
    parts = [llm_response]

    # Add sources section if we have any
    if sources:
        unique_sources = list(dict.fromkeys(sources))  # Preserve order, remove duplicates
        sources_text = "\n\nИсточники:\n" + "\n".join(f"- {s}" for s in unique_sources[:5])
        parts.append(sources_text)

    result = "".join(parts)

    # Truncate if too long
    if len(result) > max_length:
        result = result[: max_length - 3] + "..."

    return result


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle incoming text messages."""
    # Only process private messages
    if message.chat.type != ChatType.PRIVATE:
        return

    # Ignore empty messages
    if not message.text or not message.text.strip():
        return

    config = get_config()

    # Truncate long messages
    question = message.text.strip()
    if len(question) > config.max_input_length:
        question = question[: config.max_input_length]

    # Send typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        # Search RAG
        rag_client = get_rag_client()
        rag_response = await rag_client.search(question, limit=config.rag_top_k)

        rag_results = rag_response.results if rag_response else []
        sources = [r.file_name for r in rag_results]

        # Build prompt with context
        system_prompt = config.get_system_prompt()
        user_prompt = build_llm_prompt(question, rag_results)

        # Call LLM
        llm_client = get_llm_client()
        llm_response = await llm_client.chat_completion(system_prompt, user_prompt)

        if llm_response is None:
            await message.answer("Произошла ошибка, попробуйте позже")
            return

        # Format and send response
        formatted = format_response(llm_response, sources, config.max_output_length)
        await message.answer(formatted)

    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)
        await message.answer("Произошла ошибка, попробуйте позже")

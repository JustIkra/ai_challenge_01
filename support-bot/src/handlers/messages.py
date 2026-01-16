"""Text message handler with ReAct agent for tool-based processing."""

import logging
from dataclasses import asdict

from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType, ChatAction

from src.config import get_config
from src.services.rag_client import RAGClient
from src.services.llm_client import LLMClient
from src.clients.reminder import ReminderClient
from src.clients.docker import DockerClient
from src.agent.executor import ReActAgent
from src.agent.tools import ToolName, ToolCall, ToolResult

logger = logging.getLogger(__name__)
router = Router()

# Initialize clients lazily
_rag_client: RAGClient = None
_llm_client: LLMClient = None
_reminder_client: ReminderClient = None
_docker_client: DockerClient = None


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


def get_reminder_client() -> ReminderClient:
    """Get or create Reminder client."""
    global _reminder_client
    if _reminder_client is None:
        config = get_config()
        _reminder_client = ReminderClient(config.reminder_server_url)
    return _reminder_client


def get_docker_client() -> DockerClient:
    """Get or create Docker client."""
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client


async def tool_executor(tool_call: ToolCall) -> ToolResult:
    """Execute a tool call and return the result.

    Args:
        tool_call: The tool call to execute

    Returns:
        ToolResult with success status and result/error
    """
    tool_name = tool_call.name
    args = tool_call.arguments

    try:
        if tool_name == ToolName.RAG_SEARCH:
            rag_client = get_rag_client()
            query = args.get("query", "")
            config = get_config()
            response = await rag_client.search(query, limit=config.rag_top_k)

            if response is None:
                return ToolResult(
                    tool=tool_name.value,
                    success=False,
                    error="RAG search failed",
                )

            # Format results for LLM
            results_data = []
            for r in response.results:
                results_data.append({
                    "file_name": r.file_name,
                    "file_path": r.file_path,
                    "content": r.content[:1500] if len(r.content) > 1500 else r.content,
                    "similarity": r.similarity,
                })

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result={"count": response.count, "results": results_data},
            )

        elif tool_name == ToolName.REMINDER_ADD:
            reminder_client = get_reminder_client()
            text = args.get("text", "")
            due_date = args.get("due_date")
            result = await reminder_client.add(text, due_date)

            if result is None:
                return ToolResult(
                    tool=tool_name.value,
                    success=False,
                    error="Failed to add reminder",
                )

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result=result,
            )

        elif tool_name == ToolName.REMINDER_LIST:
            reminder_client = get_reminder_client()
            show_completed = args.get("show_completed", False)
            reminders = await reminder_client.list(show_completed)

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result={
                    "reminders": [asdict(r) for r in reminders],
                    "count": len(reminders),
                },
            )

        elif tool_name == ToolName.REMINDER_COMPLETE:
            reminder_client = get_reminder_client()
            reminder_id = args.get("id", "")
            success = await reminder_client.complete(reminder_id)

            if not success:
                return ToolResult(
                    tool=tool_name.value,
                    success=False,
                    error=f"Failed to complete reminder {reminder_id}",
                )

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result={"completed_id": reminder_id},
            )

        elif tool_name == ToolName.REMINDER_SUMMARY:
            reminder_client = get_reminder_client()
            summary = await reminder_client.summary()

            if summary is None:
                return ToolResult(
                    tool=tool_name.value,
                    success=False,
                    error="Failed to get reminder summary",
                )

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result=asdict(summary),
            )

        elif tool_name == ToolName.DOCKER_STATUS:
            docker_client = get_docker_client()
            containers = await docker_client.get_status()

            return ToolResult(
                tool=tool_name.value,
                success=True,
                result={
                    "containers": [asdict(c) for c in containers],
                    "count": len(containers),
                },
            )

        else:
            return ToolResult(
                tool=tool_name.value if hasattr(tool_name, "value") else str(tool_name),
                success=False,
                error=f"Unknown tool: {tool_name}",
            )

    except Exception as e:
        logger.error("Tool execution error for %s: %s", tool_name, e, exc_info=True)
        return ToolResult(
            tool=tool_name.value if hasattr(tool_name, "value") else str(tool_name),
            success=False,
            error=str(e),
        )


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    """Handle incoming text messages using ReAct agent."""
    # Only process private messages
    if message.chat.type != ChatType.PRIVATE:
        return

    # Ignore empty messages
    if not message.text or not message.text.strip():
        return

    config = get_config()

    # Truncate long messages
    user_message = message.text.strip()
    if len(user_message) > config.max_input_length:
        user_message = user_message[: config.max_input_length]

    # Send typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        # Create ReAct agent
        llm_client = get_llm_client()
        agent = ReActAgent(
            llm_client=llm_client,
            tool_executor=tool_executor,
            timeout=45.0,
            max_iterations=5,
        )

        # Run agent
        response = await agent.run(user_message)

        # Truncate if too long
        if len(response) > config.max_output_length:
            response = response[: config.max_output_length - 3] + "..."

        await message.answer(response)

    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)
        await message.answer("Произошла ошибка, попробуйте позже")

"""ReAct agent executor with tool calling loop."""

import asyncio
import json
import logging
from typing import Callable, Awaitable

from src.agent.tools import ToolName, ToolCall, ToolResult, get_tools_for_openai
from src.agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class ReActAgent:
    """ReAct agent that executes tools in a loop until a final answer is reached."""

    def __init__(
        self,
        llm_client,  # LLMClient instance
        tool_executor: ToolExecutor,
        timeout: float = 30.0,
        max_iterations: int = 5,
    ):
        """Initialize the ReAct agent.

        Args:
            llm_client: Client for LLM API calls.
            tool_executor: Async function to execute tool calls.
            timeout: Maximum time in seconds for the agent to complete.
            max_iterations: Maximum number of tool-calling iterations.
        """
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.timeout = timeout
        self.max_iterations = max_iterations

    async def run(self, user_message: str) -> str:
        """Execute ReAct loop and return final response.

        Args:
            user_message: The user's input message.

        Returns:
            The agent's final response string.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        tools = get_tools_for_openai()

        try:
            return await asyncio.wait_for(
                self._react_loop(messages, tools), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error("Agent timeout after %s seconds", self.timeout)
            return "Превышено время ожидания. Попробуйте упростить запрос."
        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            return "Произошла ошибка при обработке запроса."

    async def _react_loop(self, messages: list, tools: list) -> str:
        """Main ReAct loop.

        Args:
            messages: Conversation history.
            tools: Tool definitions in OpenAI format.

        Returns:
            The final response from the LLM.
        """
        for iteration in range(self.max_iterations):
            logger.debug("ReAct iteration %d", iteration + 1)

            # Call LLM with tools
            response = await self.llm_client.chat_completion_with_tools(
                messages=messages, tools=tools
            )

            if response is None:
                return "Ошибка при обращении к LLM."

            # Check if LLM wants to call a tool
            tool_calls = response.get("tool_calls", [])

            if not tool_calls:
                # No tool calls - return the final answer
                return response.get("content", "Не удалось получить ответ.")

            # Add assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                logger.info("Executing tool: %s with args: %s", tool_name, tool_args)

                try:
                    tool_enum = ToolName(tool_name)
                    result = await self.tool_executor(
                        ToolCall(name=tool_enum, arguments=tool_args)
                    )
                except ValueError:
                    result = ToolResult(
                        tool=tool_name, success=False, error=f"Unknown tool: {tool_name}"
                    )
                except Exception as e:
                    result = ToolResult(tool=tool_name, success=False, error=str(e))

                # Add tool result to messages
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": json.dumps(
                            result.__dict__, ensure_ascii=False, default=str
                        ),
                    }
                )

        return "Достигнут лимит итераций. Попробуйте упростить запрос."

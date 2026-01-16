"""Tool definitions for the ReAct agent."""

from dataclasses import dataclass
from typing import Optional, List, Any
from enum import Enum


class ToolName(str, Enum):
    """Available tool names."""

    RAG_SEARCH = "rag_search"
    REMINDER_ADD = "reminder_add"
    REMINDER_LIST = "reminder_list"
    REMINDER_COMPLETE = "reminder_complete"
    REMINDER_SUMMARY = "reminder_summary"
    DOCKER_STATUS = "docker_status"


@dataclass
class ToolDefinition:
    """Definition of a tool with its schema."""

    name: ToolName
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolCall:
    """A request to execute a tool."""

    name: ToolName
    arguments: dict


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


TOOL_DEFINITIONS: List[ToolDefinition] = [
    ToolDefinition(
        name=ToolName.RAG_SEARCH,
        description="Поиск информации о проекте в документации и коде",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"}
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name=ToolName.REMINDER_ADD,
        description="Создать новую задачу/напоминание",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Текст задачи"},
                "due_date": {
                    "type": "string",
                    "description": "Дедлайн в формате YYYY-MM-DD (опционально)",
                },
            },
            "required": ["text"],
        },
    ),
    ToolDefinition(
        name=ToolName.REMINDER_LIST,
        description="Показать список задач",
        parameters={
            "type": "object",
            "properties": {
                "show_completed": {
                    "type": "boolean",
                    "description": "Показывать выполненные",
                    "default": False,
                }
            },
        },
    ),
    ToolDefinition(
        name=ToolName.REMINDER_COMPLETE,
        description="Отметить задачу как выполненную",
        parameters={
            "type": "object",
            "properties": {"id": {"type": "string", "description": "ID задачи"}},
            "required": ["id"],
        },
    ),
    ToolDefinition(
        name=ToolName.REMINDER_SUMMARY,
        description="Получить сводку по задачам: активные, просроченные, выполненные сегодня",
        parameters={"type": "object", "properties": {}},
    ),
    ToolDefinition(
        name=ToolName.DOCKER_STATUS,
        description="Показать статус Docker контейнеров",
        parameters={"type": "object", "properties": {}},
    ),
]


def get_tools_for_openai() -> List[dict]:
    """Convert tool definitions to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name.value,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in TOOL_DEFINITIONS
    ]

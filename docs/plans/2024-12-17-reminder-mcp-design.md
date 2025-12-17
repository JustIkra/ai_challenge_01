# Reminder MCP Server Design

## Overview

MCP-сервер для управления задачами/напоминаниями в проекте. Хранит данные в JSON файле в корне проекта.

## Структура

```
day 1/
├── .claude/
│   └── settings.json    # MCP конфиг для проекта
├── mcp/
│   └── reminder/
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           └── index.ts
├── reminders.json       # данные задач (создаётся автоматически)
└── CLAUDE.md            # инструкция про get_summary при старте
```

## Tools

| Tool | Параметры | Описание |
|------|-----------|----------|
| `add_reminder` | `text` (required), `due_date` (optional) | Добавить задачу |
| `list_reminders` | — | Показать все задачи |
| `complete_reminder` | `id` | Отметить выполненной |
| `delete_reminder` | `id` | Удалить задачу |
| `get_summary` | — | Краткая сводка |

## Формат данных (reminders.json)

```json
{
  "reminders": [
    {
      "id": "uuid",
      "text": "Текст задачи",
      "created_at": "2024-12-17T10:00:00Z",
      "due_date": null,
      "completed": false,
      "completed_at": null
    }
  ]
}
```

## Интеграция

- Настройка в `.claude/settings.json` (только для этого проекта)
- Инструкция в `CLAUDE.md` для автоматического вызова `get_summary` при старте

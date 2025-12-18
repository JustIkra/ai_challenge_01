# MCP: Reminder Server

MCP-сервер для управления задачами/напоминаниями проекта. Хранит данные локально в JSON-файле.

## Описание

`reminder-mcp` предоставляет инструменты для создания, просмотра, выполнения и удаления задач. Идеально подходит для интеграции с AI-агентами для отслеживания прогресса работы.

## Установка

```bash
cd mcp/reminder
npm install
```

## Запуск

```bash
npm start
```

Сервер работает через stdio и совместим с MCP-клиентами (Claude Desktop, Claude Code и др.).

## Регистрация в Claude Code

Добавьте в `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reminder": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/mcp/reminder/index.mjs"],
      "cwd": "/ABSOLUTE/PATH/TO/PROJECT/ROOT"
    }
  }
}
```

> **Важно:** `cwd` должен указывать на корень проекта, где будет храниться `reminders.json`.

## Инструменты

### `add_reminder`

Добавить новую задачу.

**Параметры:**
- `text` (string, required) — текст задачи
- `due_date` (string, optional) — дедлайн в формате `YYYY-MM-DD`

**Пример:**
```
Добавь задачу "Написать документацию" с дедлайном 2024-12-20
```

### `list_reminders`

Показать все задачи.

**Параметры:**
- `show_completed` (boolean, optional) — показывать выполненные задачи (по умолчанию `false`)

### `complete_reminder`

Отметить задачу как выполненную.

**Параметры:**
- `id` (string, required) — ID задачи

### `delete_reminder`

Удалить задачу.

**Параметры:**
- `id` (string, required) — ID задачи

### `get_summary`

Получить краткую сводку: активные, просроченные, выполненные сегодня.

**Пример ответа:**
```
Задачи проекта:
- Активных: 3
- Просроченных: 1
- Выполнено сегодня: 2

Просроченные:
  - abc123: Задача X (до 15 дек. 2024)

Активные задачи:
  - def456: Задача Y
  - ghi789: Задача Z (до 25 дек. 2024)
```

## Хранение данных

Данные хранятся в файле `reminders.json` в текущей рабочей директории (cwd). Формат:

```json
{
  "reminders": [
    {
      "id": "abc12345",
      "text": "Задача",
      "created_at": "2024-12-17T10:00:00.000Z",
      "due_date": "2024-12-20",
      "completed": false,
      "completed_at": null
    }
  ]
}
```

## Архитектура

```
┌─────────────────┐     stdio      ┌──────────────────┐
│  MCP Client     │ ◄────────────► │  reminder-mcp    │
│ (Claude Code)   │                │                  │
└─────────────────┘                └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │  reminders.json  │
                                   └──────────────────┘
```

## Зависимости

- `@modelcontextprotocol/sdk` — MCP TypeScript SDK
- `zod` — валидация схем

## Использование с CLAUDE.md

Для автоматического показа задач при старте сессии добавьте в `CLAUDE.md`:

```markdown
## Session Start

При начале новой сессии вызови tool `get_summary` из reminder MCP-сервера, чтобы показать текущие задачи по проекту.
```

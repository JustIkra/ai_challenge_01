# MCP Servers

Коллекция MCP-серверов для расширения возможностей AI-агентов.

## Что такое MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) — открытый протокол для интеграции LLM-приложений с внешними источниками данных и инструментами. MCP позволяет AI-агентам:

- Получать контекст из внешних систем
- Выполнять действия через инструменты (tools)
- Работать с ресурсами (resources) и промптами (prompts)

## Доступные серверы

| Сервер | Описание | Инструменты |
|--------|----------|-------------|
| [reminder](./reminder/) | Управление задачами проекта | `add_reminder`, `list_reminders`, `complete_reminder`, `delete_reminder`, `get_summary` |
| [location-tracker](./location-tracker/) | Геолокация по IP | `get-current-location` |

## Быстрый старт

### 1. Установка зависимостей

```bash
# Reminder server
cd mcp/reminder && npm install

# Location tracker
cd mcp/location-tracker && npm install
```

### 2. Регистрация в Claude Code

Добавьте в `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reminder": {
      "command": "node",
      "args": ["/path/to/mcp/reminder/index.mjs"],
      "cwd": "/path/to/project/root"
    },
    "location-tracker": {
      "command": "node",
      "args": ["/path/to/mcp/location-tracker/index.mjs"]
    }
  }
}
```

### 3. Перезапуск Claude Code

После изменения конфигурации перезапустите Claude Code для применения настроек.

## Архитектура MCP

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                           │
│                    (Claude Code / Desktop)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ stdio
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  reminder-mcp │  │location-tracker│  │   другие...  │
│               │  │               │  │               │
│  • add        │  │  • location   │  │  • ...        │
│  • list       │  │               │  │               │
│  • complete   │  └───────┬───────┘  └───────────────┘
│  • delete     │          │
│  • summary    │          ▼ HTTP
└───────┬───────┘  ┌───────────────┐
        │          │  ip-api.com   │
        ▼          └───────────────┘
┌───────────────┐
│reminders.json │
└───────────────┘
```

## Создание нового MCP-сервера

### Базовая структура

```
mcp/
└── my-server/
    ├── index.mjs      # Основной файл сервера
    ├── package.json   # Зависимости
    └── README.md      # Документация
```

### Минимальный package.json

```json
{
  "name": "my-mcp-server",
  "version": "0.1.0",
  "type": "module",
  "main": "index.mjs",
  "bin": {
    "my-mcp-server": "index.mjs"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.25.0"
  }
}
```

### Минимальный сервер

```javascript
#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-server",
  version: "0.1.0"
});

// Регистрация инструмента
server.registerTool(
  "my-tool",
  {
    description: "Описание инструмента",
    inputSchema: {
      param: z.string().describe("Описание параметра")
    }
  },
  async ({ param }) => {
    return {
      content: [{ type: "text", text: `Результат: ${param}` }]
    };
  }
);

// Запуск сервера
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
```

## Ресурсы

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Servers Examples](https://github.com/modelcontextprotocol/servers)

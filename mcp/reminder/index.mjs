#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// HTTP API base URL - use Docker reminder-server
const REMINDER_API_URL = process.env.REMINDER_API_URL || "http://localhost:8802";

// Helper functions for HTTP requests
async function apiGet(endpoint) {
  const response = await fetch(`${REMINDER_API_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

async function apiPost(endpoint, data) {
  const response = await fetch(`${REMINDER_API_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

// Server setup
const server = new McpServer({
  name: "reminder-mcp",
  version: "0.2.0"
});

// Tool: add_reminder
server.registerTool(
  "add_reminder",
  {
    description: "Добавить новую задачу/напоминание. Возвращает созданную задачу.",
    inputSchema: {
      text: z.string().describe("Текст задачи"),
      due_date: z.string().optional().describe("Дедлайн в формате YYYY-MM-DD (опционально)")
    }
  },
  async ({ text, due_date }) => {
    try {
      const result = await apiPost("/api/add", { text, due_date });
      return {
        content: [
          {
            type: "text",
            text: `Задача добавлена:\n- ID: ${result.id}\n- Текст: ${result.text}${due_date ? `\n- Дедлайн: ${formatDate(due_date)}` : ""}`
          }
        ]
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: `Ошибка: ${error.message}` }]
      };
    }
  }
);

// Tool: list_reminders
server.registerTool(
  "list_reminders",
  {
    description: "Показать все задачи (активные и выполненные).",
    inputSchema: {
      show_completed: z.boolean().optional().describe("Показывать выполненные задачи (по умолчанию false)")
    }
  },
  async ({ show_completed = false }) => {
    try {
      const url = show_completed ? "/api/list?show_completed=true" : "/api/list";
      const data = await apiGet(url);
      const reminders = data.reminders || [];

      if (reminders.length === 0) {
        return {
          content: [{ type: "text", text: "Нет задач." }]
        };
      }

      const lines = reminders.map(r => {
        const status = r.completed ? "[x]" : "[ ]";
        const overdue = r.is_overdue ? " (ПРОСРОЧЕНО)" : "";
        const due = r.due_date ? ` | до ${formatDate(r.due_date)}${overdue}` : "";
        return `${status} ${r.id}: ${r.text}${due}`;
      });

      return {
        content: [{ type: "text", text: lines.join("\n") }]
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: `Ошибка: ${error.message}` }]
      };
    }
  }
);

// Tool: complete_reminder
server.registerTool(
  "complete_reminder",
  {
    description: "Отметить задачу как выполненную по ID.",
    inputSchema: {
      id: z.string().describe("ID задачи")
    }
  },
  async ({ id }) => {
    try {
      const result = await apiPost("/api/complete", { id });
      if (result.already_completed) {
        return {
          content: [{ type: "text", text: `Задача уже была выполнена.` }]
        };
      }
      return {
        content: [{ type: "text", text: `Задача выполнена!` }]
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: `Ошибка: ${error.message}` }]
      };
    }
  }
);

// Tool: delete_reminder
server.registerTool(
  "delete_reminder",
  {
    description: "Удалить задачу по ID.",
    inputSchema: {
      id: z.string().describe("ID задачи")
    }
  },
  async ({ id }) => {
    try {
      await apiPost("/api/delete", { id });
      return {
        content: [{ type: "text", text: `Задача удалена.` }]
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: `Ошибка: ${error.message}` }]
      };
    }
  }
);

// Tool: get_summary
server.registerTool(
  "get_summary",
  {
    description: "Получить краткую сводку по задачам: активные, просроченные, выполненные сегодня."
  },
  async () => {
    try {
      const summary = await apiGet("/api/summary");
      const list = await apiGet("/api/list");
      const reminders = list.reminders || [];

      const lines = [
        `Задачи проекта:`,
        `- Активных: ${summary.active}`,
        `- Просроченных: ${summary.overdue}`,
        `- Выполнено сегодня: ${summary.completed_today}`
      ];

      const overdue = reminders.filter(r => r.is_overdue);
      if (overdue.length > 0) {
        lines.push("");
        lines.push("Просроченные:");
        overdue.forEach(r => {
          lines.push(`  - ${r.id}: ${r.text} (до ${formatDate(r.due_date)})`);
        });
      }

      const active = reminders.filter(r => !r.completed);
      if (active.length > 0 && active.length <= 5) {
        lines.push("");
        lines.push("Активные задачи:");
        active.forEach(r => {
          const due = r.due_date ? ` (до ${formatDate(r.due_date)})` : "";
          lines.push(`  - ${r.id}: ${r.text}${due}`);
        });
      }

      return {
        content: [{ type: "text", text: lines.join("\n") }]
      };
    } catch (error) {
      return {
        content: [{ type: "text", text: `Ошибка подключения к reminder-server: ${error.message}` }]
      };
    }
  }
);

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(error => {
  console.error("Server error:", error);
  process.exit(1);
});

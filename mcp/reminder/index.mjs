#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { randomUUID } from "crypto";

const REMINDERS_FILE = "reminders.json";

// Helper functions
function loadReminders() {
  if (!existsSync(REMINDERS_FILE)) {
    return { reminders: [] };
  }
  try {
    const data = readFileSync(REMINDERS_FILE, "utf-8");
    return JSON.parse(data);
  } catch {
    return { reminders: [] };
  }
}

function saveReminders(data) {
  writeFileSync(REMINDERS_FILE, JSON.stringify(data, null, 2), "utf-8");
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
}

function isOverdue(dueDate) {
  if (!dueDate) return false;
  return new Date(dueDate) < new Date();
}

// Server setup
const server = new McpServer({
  name: "reminder-mcp",
  version: "0.1.0"
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
    const data = loadReminders();

    const reminder = {
      id: randomUUID().slice(0, 8),
      text,
      created_at: new Date().toISOString(),
      due_date: due_date || null,
      completed: false,
      completed_at: null
    };

    data.reminders.push(reminder);
    saveReminders(data);

    return {
      content: [
        {
          type: "text",
          text: `Задача добавлена:\n- ID: ${reminder.id}\n- Текст: ${reminder.text}${due_date ? `\n- Дедлайн: ${formatDate(due_date)}` : ""}`
        }
      ]
    };
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
    const data = loadReminders();

    let reminders = data.reminders;
    if (!show_completed) {
      reminders = reminders.filter(r => !r.completed);
    }

    if (reminders.length === 0) {
      return {
        content: [{ type: "text", text: "Нет задач." }]
      };
    }

    const lines = reminders.map(r => {
      const status = r.completed ? "[x]" : "[ ]";
      const overdue = !r.completed && isOverdue(r.due_date) ? " (ПРОСРОЧЕНО)" : "";
      const due = r.due_date ? ` | до ${formatDate(r.due_date)}${overdue}` : "";
      return `${status} ${r.id}: ${r.text}${due}`;
    });

    return {
      content: [{ type: "text", text: lines.join("\n") }]
    };
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
    const data = loadReminders();
    const reminder = data.reminders.find(r => r.id === id);

    if (!reminder) {
      return {
        content: [{ type: "text", text: `Задача с ID "${id}" не найдена.` }]
      };
    }

    if (reminder.completed) {
      return {
        content: [{ type: "text", text: `Задача "${reminder.text}" уже выполнена.` }]
      };
    }

    reminder.completed = true;
    reminder.completed_at = new Date().toISOString();
    saveReminders(data);

    return {
      content: [{ type: "text", text: `Задача выполнена: ${reminder.text}` }]
    };
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
    const data = loadReminders();
    const index = data.reminders.findIndex(r => r.id === id);

    if (index === -1) {
      return {
        content: [{ type: "text", text: `Задача с ID "${id}" не найдена.` }]
      };
    }

    const removed = data.reminders.splice(index, 1)[0];
    saveReminders(data);

    return {
      content: [{ type: "text", text: `Задача удалена: ${removed.text}` }]
    };
  }
);

// Tool: get_summary
server.registerTool(
  "get_summary",
  {
    description: "Получить краткую сводку по задачам: активные, просроченные, выполненные сегодня."
  },
  async () => {
    const data = loadReminders();
    const reminders = data.reminders;

    if (reminders.length === 0) {
      return {
        content: [{ type: "text", text: "Нет задач в этом проекте." }]
      };
    }

    const active = reminders.filter(r => !r.completed);
    const overdue = active.filter(r => isOverdue(r.due_date));

    const today = new Date().toDateString();
    const completedToday = reminders.filter(r =>
      r.completed && r.completed_at && new Date(r.completed_at).toDateString() === today
    );

    const lines = [
      `Задачи проекта:`,
      `- Активных: ${active.length}`,
      `- Просроченных: ${overdue.length}`,
      `- Выполнено сегодня: ${completedToday.length}`
    ];

    if (overdue.length > 0) {
      lines.push("");
      lines.push("Просроченные:");
      overdue.forEach(r => {
        lines.push(`  - ${r.id}: ${r.text} (до ${formatDate(r.due_date)})`);
      });
    }

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

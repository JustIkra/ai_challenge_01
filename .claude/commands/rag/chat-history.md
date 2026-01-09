---
description: Show RAG chat history
argument-hint: [n] [session]
---

Display the last N messages from a chat session.

## Parameters
- `$1` - Number of messages to show (default: 10)
- `$2` - Session ID (default: 'default')

## Instructions

### Step 1: Get History
Use MCP tool `rag_chat_history` with:
- session_id: `$2` (or 'default')
- limit: `$1` (or 10)

Parse JSON response.

### Step 2: Output Format

```markdown
## История чата

**Сессия:** {session_id}
**Всего сообщений:** {total_in_session}
**Показано:** {messages.length}

---

{for each message:}
### [{role emoji}] {role} ({timestamp})
{content}

{if role == 'assistant' and sources:}
📎 Источники: {sources as comma-separated file paths}

---
{end for}

{if no messages:}
_История пуста. Начните диалог с `/rag:chat <вопрос>`_
```

## Role Emojis
- 👤 user
- 🤖 assistant

## Notes
- Messages are shown in chronological order (oldest first)
- Timestamps help track conversation flow
- Sources show which files were used for each assistant response


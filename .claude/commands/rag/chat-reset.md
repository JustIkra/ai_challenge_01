---
description: Reset RAG chat session memory
argument-hint: [session]
---

Clear all chat history for a session.

## Parameters
- `$1` - Session ID to reset (default: 'default')

## Instructions

### Step 1: Reset Session
Use MCP tool `rag_chat_reset` with:
- session_id: `$1` (or 'default')

### Step 2: Output Result

```markdown
✅ Сессия "{session_id}" очищена.

Удалено сообщений: {deleted_count}

Теперь можете начать новый диалог с `/rag:chat`.
```

## Notes
- This permanently deletes all messages in the session
- Use different session IDs to maintain separate conversations
- Default session is 'default'


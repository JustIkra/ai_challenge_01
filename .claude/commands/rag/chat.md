---
description: RAG chat with memory and sources
argument-hint: <message> [k] [session]
---

Answer the question using RAG context while maintaining session memory.
Each call continues the conversation with full context from previous turns.

## Parameters
- `$1` - Message/question (required)
- `$2` - Number of documents to retrieve (default: 5)
- `$3` - Session ID (default: 'default')

## Instructions

### Step 1: Check Index Status
Use MCP tool `rag_status` to check if index exists.
If total documents = 0:
- Output: "⚠️ Индекс пуст. Запустите `/rag:index` для индексации проекта."
- Stop execution.

### Step 2: Load Chat History
Use MCP tool `rag_chat_history` with:
- session_id: `$3` (or 'default')
- limit: 8

Parse JSON response to get previous messages for context.

### Step 3: Save User Message
Use MCP tool `rag_chat_append` with:
- session_id: `$3` (or 'default')
- role: 'user'
- content: `$1`

### Step 4: RAG Search
Use MCP tool `rag_search` with:
- query: `$1`
- limit: `$2` (or 5)
- format: 'json'

Parse JSON to get results array with file_path and similarity.

### Step 5: Build Context and Generate Answer
Combine:
1. **Chat history** (from Step 2) - previous conversation turns
2. **RAG context** (from Step 4) - relevant documents

Generate a helpful answer that:
- Takes into account the full conversation history
- Uses information from retrieved documents
- Cites specific files when making claims

### Step 6: Save Assistant Response
Use MCP tool `rag_chat_append` with:
- session_id: `$3` (or 'default')
- role: 'assistant'
- content: your answer text
- sources: array of `{file_path, similarity}` for documents actually used

### Step 7: Output Format (REQUIRED)

```markdown
## Источники
{if sources found:}
1. [{similarity as percent}%] {file_path}
2. [{similarity as percent}%] {file_path}
...

{if no sources:}
_Релевантных документов не найдено_

## Ответ
{your answer based on history + context, cite files}

---
_Сессия: {session_id} | История: {message_count} сообщений_
```

## Important Rules
- ALWAYS output the "Источники" section, even if empty
- Show similarity as percentage with 1 decimal (e.g., "87.3%")
- Cite specific files when making claims
- Reference previous conversation turns when relevant
- Keep answers focused and relevant to the question


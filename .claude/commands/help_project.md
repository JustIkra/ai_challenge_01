---
description: Answer questions about this project using RAG semantic search
argument-hint: <question>
---

Answer the question about this project using RAG semantic search with source attribution.

## Parameters
- `$ARGUMENTS` - Question about the project (required)

## Instructions

### Step 1: Check Index Status
Use MCP tool `rag_status` to check if index exists.

If total documents = 0:
- Output: "⚠️ RAG index is empty. Run `/rag:index` first to index project files."
- **STOP** - do not proceed to search.

### Step 2: RAG Search
Use MCP tool `rag_search` with:
- query: `$ARGUMENTS`
- limit: 10
- format: `json`

Parse the JSON response to get array of results.

### Step 3: Filter Results
Apply similarity threshold >= 0.65 (65%).

If no results pass threshold:
- Use top-3 results as fallback
- Note this in the answer

### Step 4: Generate Answer
Based on filtered results:
- Answer the user's question directly
- Cite specific files when making claims
- Be concise and helpful

### Step 5: Output Format

```markdown
## Ответ

{answer based on context, citing specific files}

### Источники:
- [{similarity}%] {file_path} ({language})
- ...
```

### Important Rules
- Show similarity as percentage with 1 decimal (e.g., "87.3%")
- Always cite specific files when making claims
- If question cannot be answered from context, say so clearly
- Keep answer focused and concise

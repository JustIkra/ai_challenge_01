---
description: RAG comparison - answer with/without context
argument-hint: <question> [k]
---

Answer the question about this project in **compare** mode: first WITHOUT RAG context (baseline), then WITH RAG context, then provide comparison analysis.

## Parameters
- `$1` - Question about the project (required)
- `$2` - Number of chunks to retrieve (default: 5)

## Instructions

### Step 1: Check Index Status
First, use MCP tool `rag_status` to check if index exists. If total documents = 0, inform user to run `/rag:index` first and stop.

### Step 2: Baseline Answer (WITHOUT RAG)
Answer the question `$1` based ONLY on your general knowledge and what you can infer from the question. Do NOT use any RAG tools or search the codebase.

Format:
```
## Без RAG (baseline)

[Your answer based only on general knowledge, without accessing project files]
```

### Step 3: RAG Search
Use MCP tool `rag_search` with:
- query: `$1`
- limit: `$2` (or 5 if not specified)

Store the results for the next step.

### Step 4: Answer WITH RAG Context
Now answer the SAME question `$1` using the context from RAG search results.

Format your answer as:
```
## С RAG (топ-{k} чанков)

### Контекст из проекта:
[List the files found with similarity scores]

### Ответ:
[Your answer based on the RAG context. Reference specific files when making claims.]

### Источники:
- file1.py - [what was used from this file]
- file2.md - [what was used from this file]
```

Important rules for RAG answer:
- Answer ONLY based on the provided context
- If context is insufficient, explicitly state what information is missing
- Always attribute claims to specific source files
- Quote relevant code snippets when appropriate

### Step 5: Comparison Analysis
Compare both answers and provide analysis:

```
## Сравнение

### Что изменилось:
[List specific facts/details that appeared in RAG answer but not in baseline]

### Оценка RAG:
- **Улучшил точность**: [Yes/No + explanation of what became more accurate/specific]
- **Не повлиял**: [aspects where RAG didn't change the answer]
- **Ухудшил (шум/нерелевантность)**: [if RAG introduced noise or irrelevant information]

### Вывод:
[1-3 sentences summarizing: Did RAG help for this question? Why or why not?]
```

---
description: Answer question using RAG context with relevance filtering
argument-hint: <question> [k] [threshold]
---

Answer the question about this project using RAG semantic search with relevance filtering.

## Parameters
- `$1` - Question about the project (required)
- `$2` - Number of chunks to show in "unfiltered" block (default: 5)
- `$3` - Similarity threshold 0.0-1.0 (default: 0.70, means 70%)

## Instructions

### Step 1: Check Index Status
Use MCP tool `rag_status` to check if index exists. If total documents = 0, inform user to run `/rag:index` first and stop.

### Step 2: RAG Search (retrieve top-50 candidates)
Use MCP tool `rag_search` with:
- query: `$1`
- limit: 50 (always fetch 50 candidates to ensure we don't miss relevant files)
- format: `json`

Parse the JSON response to get array of results with similarity scores.

### Step 3: Apply Relevance Filter
- Parse `$2` as k (default: 5) - number of results to show in unfiltered block
- Parse `$3` as threshold (default: 0.70)
- Create two result sets:
  1. **Unfiltered**: First k results from all 50 candidates (top-k by similarity)
  2. **Filtered**: All results from 50 candidates where `similarity >= threshold`

### Step 4: Generate Two Answers
Generate answers for BOTH result sets:
1. Answer based on unfiltered results
2. Answer based on filtered results

If filtered set is empty:
- State "No results passed threshold {threshold}"
- Suggest lowering threshold (try 0.60 or 0.50)
- As fallback, use top-1 result from unfiltered set

### Step 5: Output Format
Present results in three blocks:

```markdown
## 1️⃣ RAG без фильтра (топ-{k} чанков)

### Источники ({count} файлов):
{list each source with similarity percentage}
- [{similarity}%] {file_path} ({language})

### Ответ:
{answer based on all top-k results, cite specific files}

---

## 2️⃣ RAG с фильтром релевантности (>= {threshold*100}%)

### Источники ({filtered_count} из 50 кандидатов):
{list filtered sources with similarity percentage}
- [{similarity}%] {file_path} ({language})

{if no results: "⚠️ Ни один результат не прошёл порог {threshold*100}%. Попробуйте threshold=0.60 или 0.50"}

### Ответ:
{answer based on filtered results OR fallback to top-1 if empty}

---

## 3️⃣ Сравнение качества

**Количество источников:**
- Без фильтра: {k} файлов (топ-k из 50 кандидатов)
- С фильтром: {filtered_count} файлов (из 50 кандидатов с similarity >= {threshold})
- Отфильтровано из пула: {50 - filtered_count} файлов

**Оценка качества:**
{2-4 sentences comparing the answers:
- Did filtering improve precision/reduce noise?
- Did filtering remove important context?
- Which answer is more specific/accurate?
- Recommendation: use filter or adjust threshold}
```

### Important Rules
- ALWAYS show all 3 blocks in every response
- Use the SAME question for both answers (no reformulation)
- In comparison, be objective: sometimes unfiltered is better
- Cite specific files when making claims in answers
- Show similarity as percentage with 1 decimal (e.g., "87.3%")

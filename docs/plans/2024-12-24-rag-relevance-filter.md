# RAG Relevance Filter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add relevance filtering to RAG search with comparison mode to improve answer quality by filtering out low-similarity results.

**Architecture:** Two-stage approach: (1) Semantic search returns top-k candidates, (2) Filter by similarity threshold. Compare results with/without filter in single command invocation. Minimal changes to MCP server (add JSON format option), main logic in slash command instructions.

**Tech Stack:** Node.js (MCP server), PostgreSQL (pgvector), slash command (markdown instructions)

---

## Task 1: Add JSON format option to rag_search MCP tool

**Files:**
- Modify: `mcp/rag-server/index.mjs:217-264`

**Step 1: Update rag_search tool schema to accept format parameter**

In `mcp/rag-server/index.mjs`, modify the tool registration (line 217-226):

```javascript
server.registerTool(
  "rag_search",
  {
    description: "Semantic search across indexed project files. Returns most relevant files for the query.",
    inputSchema: {
      query: z.string().describe("Search query"),
      limit: z.number().optional().describe("Maximum number of results (default: 5)"),
      format: z.enum(['text', 'json']).optional().describe("Output format: 'text' (default, human-readable) or 'json' (structured data)")
    }
  },
```

**Step 2: Update rag_search handler to return JSON when requested**

In `mcp/rag-server/index.mjs`, modify the async handler function (line 227-263):

```javascript
  async ({ query, limit = 5, format = 'text' }) => {
    try {
      if (!query || query.trim().length === 0) {
        return formatResult({ success: false, error: "Query cannot be empty" });
      }

      console.error(`[rag_search] Searching for: "${query}" (limit=${limit}, format=${format})`);

      await initDb();

      // Generate query embedding
      const queryEmbedding = await generateQueryEmbedding(query);

      // Search for similar documents
      const results = await searchSimilar(queryEmbedding, limit);

      if (results.length === 0) {
        return formatResult({ success: true, output: "No results found. Try running rag_index first." });
      }

      // Return JSON format if requested
      if (format === 'json') {
        const jsonResults = results.map((r, i) => ({
          rank: i + 1,
          file_path: r.file_path,
          file_type: r.file_type,
          language: r.language || r.file_type,
          similarity: r.similarity,
          lines_count: r.lines_count,
          content: r.content
        }));

        return formatResult({
          success: true,
          output: JSON.stringify({ results: jsonResults, count: results.length }, null, 2)
        });
      }

      // Format results as text (existing behavior)
      const output = results.map((r, i) => {
        const similarity = (r.similarity * 100).toFixed(1);
        const preview = r.content.slice(0, 200).replace(/\n/g, ' ').trim();
        return `${i + 1}. [${similarity}%] ${r.file_path} (${r.language || r.file_type})\n   ${preview}${r.content.length > 200 ? '...' : ''}`;
      }).join('\n\n');

      return formatResult({
        success: true,
        output: `Found ${results.length} results:\n\n${output}`
      });

    } catch (error) {
      console.error(`[rag_search] Error: ${error.message}`);
      return formatResult({ success: false, error: error.message });
    }
  }
);
```

**Step 3: Test JSON format manually**

Run:
```bash
# Start RAG server if not running (it's started via MCP config)
# Test via Claude Code by running:
# /rag:search "database connection" 3 json
```

Expected: JSON response with structured data including similarity scores

**Step 4: Commit**

```bash
git add mcp/rag-server/index.mjs
git commit -m "feat(rag): add JSON format option to rag_search tool"
```

---

## Task 2: Update /rag:ask command with filter and comparison

**Files:**
- Modify: `.claude/commands/rag/ask.md`

**Step 1: Update command description and arguments**

Replace entire file `.claude/commands/rag/ask.md`:

```markdown
---
description: Answer question using RAG context with relevance filtering
argument-hint: <question> [k] [threshold]
---

Answer the question about this project using RAG semantic search with relevance filtering.

## Parameters
- `$1` - Question about the project (required)
- `$2` - Number of chunks to retrieve (default: 5)
- `$3` - Similarity threshold 0.0-1.0 (default: 0.70, means 70%)

## Instructions

### Step 1: Check Index Status
Use MCP tool `rag_status` to check if index exists. If total documents = 0, inform user to run `/rag:index` first and stop.

### Step 2: RAG Search (retrieve top-k candidates)
Use MCP tool `rag_search` with:
- query: `$1`
- limit: `$2` (or 5 if not specified)
- format: `json`

Parse the JSON response to get array of results with similarity scores.

### Step 3: Apply Relevance Filter
- Parse `$3` as threshold (default: 0.70)
- Create two result sets:
  1. **Unfiltered**: All top-k results from Step 2
  2. **Filtered**: Only results where `similarity >= threshold`

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

### Источники ({filtered_count} из {k} файлов):
{list filtered sources with similarity percentage}
- [{similarity}%] {file_path} ({language})

{if no results: "⚠️ Ни один результат не прошёл порог {threshold*100}%. Попробуйте threshold=0.60 или 0.50"}

### Ответ:
{answer based on filtered results OR fallback to top-1 if empty}

---

## 3️⃣ Сравнение качества

**Количество источников:**
- Без фильтра: {k} файлов
- С фильтром: {filtered_count} файлов
- Отфильтровано: {k - filtered_count} файлов

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
```

**Step 2: Test the updated command manually**

Run:
```bash
# Test with default threshold (0.70)
# Via Claude Code: /rag:ask "как работает подключение к БД" 5

# Test with custom threshold
# Via Claude Code: /rag:ask "как работает подключение к БД" 5 0.80
```

Expected:
- Three blocks in output
- Filtered results show only high-similarity items
- Comparison block present

**Step 3: Commit**

```bash
git add .claude/commands/rag/ask.md
git commit -m "feat(rag): add relevance filtering and comparison to /rag:ask"
```

---

## Task 3: Create demo/comparison test scenarios

**Files:**
- Create: `docs/rag-filter-demo.md`

**Step 1: Write demo document with 3 test questions**

Create `docs/rag-filter-demo.md`:

```markdown
# RAG Relevance Filter - Demo Scenarios

This document demonstrates the RAG relevance filtering feature with comparison mode.

## Test Question 1: Specific Technical Query

**Question:** "Как работает подключение к PostgreSQL?"

**Expected behavior:**
- High similarity: backend DB connection code, config files
- Low similarity: unrelated Python/JS files, docs about frontend

**Command:**
```bash
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.70
```

**Expected results:**
- Without filter: 5 files, may include some noise
- With filter (≥70%): 2-3 highly relevant files
- Comparison: Filter should improve precision, answer more focused

---

## Test Question 2: Architectural Question

**Question:** "Какая архитектура используется в проекте?"

**Expected behavior:**
- High similarity: README.md, CLAUDE.md, architecture docs
- Medium similarity: docker-compose.yml, main config files
- Low similarity: specific implementation files

**Command:**
```bash
/rag:ask "Какая архитектура используется в проекте?" 5 0.70
```

**Expected results:**
- Without filter: 5 files with varying relevance
- With filter (≥70%): Documentation files with architecture descriptions
- Comparison: Filter should remove implementation details, keep overview

---

## Test Question 3: Edge Case - No High-Similarity Results

**Question:** "Как реализована блокчейн интеграция?"

**Expected behavior:**
- All results have low similarity (project doesn't use blockchain)
- Filter should catch 0 results

**Command:**
```bash
/rag:ask "Как реализована блокчейн интеграция?" 5 0.70
```

**Expected results:**
- Without filter: 5 files with low similarity (30-50%)
- With filter (≥70%): 0 files, fallback to top-1
- Comparison: Shows filter correctly identifies irrelevant query, suggests lowering threshold

---

## Running the Demo

1. Ensure RAG index is up to date:
   ```bash
   /rag:index
   ```

2. Run each test question above

3. Verify all three questions produce:
   - ✅ 3 blocks in output (unfiltered, filtered, comparison)
   - ✅ Similarity percentages displayed correctly
   - ✅ Filtered count ≤ unfiltered count
   - ✅ Comparison mentions specific differences
   - ✅ Fallback works when filter returns 0 results

## Threshold Sensitivity Test

Run same question with different thresholds:

```bash
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.50
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.70
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.85
```

**Expected:** Higher threshold = fewer filtered results, more precision but potentially less context.
```

**Step 2: Commit**

```bash
git add docs/rag-filter-demo.md
git commit -m "docs(rag): add demo scenarios for relevance filtering"
```

---

## Task 4: Run demo and verify acceptance criteria

**Files:**
- None (verification task)

**Step 1: Index the project**

Run:
```bash
# Via Claude Code:
/rag:index
```

Expected: Index completes successfully

**Step 2: Run Test Question 1**

Run:
```bash
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.70
```

Verify:
- [ ] Three blocks present (unfiltered, filtered, comparison)
- [ ] Similarity shown as percentage (e.g., "87.3%")
- [ ] Filtered count ≤ top-k count
- [ ] Comparison block has 2-4 sentences
- [ ] Both answers cite specific files

**Step 3: Run Test Question 2**

Run:
```bash
/rag:ask "Какая архитектура используется в проекте?" 5 0.70
```

Verify same criteria as Step 2

**Step 4: Run Test Question 3 (edge case)**

Run:
```bash
/rag:ask "Как реализована блокчейн интеграция?" 5 0.70
```

Verify:
- [ ] Filter returns 0 results
- [ ] Message shown: "Ни один результат не прошёл порог"
- [ ] Suggestion to lower threshold present
- [ ] Fallback answer uses top-1 result

**Step 5: Test threshold variations**

Run:
```bash
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.50
/rag:ask "Как работает подключение к PostgreSQL?" 5 0.85
```

Verify:
- [ ] Lower threshold (0.50) → more filtered results
- [ ] Higher threshold (0.85) → fewer filtered results
- [ ] Threshold actually affects context (not just display)

**Step 6: Document results**

Add results to `docs/rag-filter-demo.md` under each test question:

```markdown
## Results (YYYY-MM-DD)

Test 1: ✅ Passed
- Unfiltered: 5 files
- Filtered: 3 files (87.3%, 79.1%, 71.2%)
- Comparison: Filter removed 2 low-relevance files, answer more focused

[repeat for other tests]
```

**Step 7: Commit**

```bash
git add docs/rag-filter-demo.md
git commit -m "docs(rag): add demo test results"
```

---

## Task 5: Update ticket status

**Files:**
- Modify: `.task/TASK-004-rag-relevance-filter-reranker.md`

**Step 1: Mark all acceptance criteria as completed**

In `.task/TASK-004-rag-relevance-filter-reranker.md`, update lines 56-65:

```markdown
## Acceptance Criteria

- [x] Команда принимает параметры: `<question> [k] [threshold]` (или эквивалентно), где `threshold` по умолчанию `0.70`.
- [x] В одном запуске выводятся 3 блока:
  1) `RAG без фильтра (top-k)` — источники + ответ.
  2) `RAG с фильтром (>= threshold)` — источники + ответ; указать сколько результатов осталось.
  3) `Сравнение` — где фильтр улучшил/ухудшил: точность, конкретика, количество "шума".
- [x] Если после фильтрации не осталось результатов:
  - команда явно сообщает "ничего не прошло порог" и предлагает снизить `threshold` (или, как fallback, взять top‑1 без фильтра — если это будет согласовано).
- [x] Порог реально влияет на состав контекста (не только на вывод списка).
- [x] Сравнение воспроизводимо: одинаковый вопрос → одинаковые источники и структура вывода (при фиксированном индексе).
```

**Step 2: Change status to done**

In `.task/TASK-004-rag-relevance-filter-reranker.md`, update line 3:

```markdown
## Статус: `done`
```

**Step 3: Commit**

```bash
git add .task/TASK-004-rag-relevance-filter-reranker.md
git commit -m "chore: mark TASK-004 as done"
```

---

## Summary

**Total tasks:** 5
**Estimated time:** ~30-40 minutes for implementation + testing

**Key changes:**
1. MCP server: Added `format` parameter to `rag_search` tool (JSON output)
2. Slash command: Complete rewrite with filtering logic and comparison mode
3. Documentation: Demo scenarios with 3 test questions

**Testing approach:**
- Manual testing via `/rag:ask` command
- 3 demo scenarios covering: specific query, broad query, no-match query
- Threshold sensitivity testing

**Success criteria:**
- All 5 acceptance criteria from ticket marked as complete
- Demo shows measurable quality improvement with filtering
- Edge cases handled (0 results after filter)

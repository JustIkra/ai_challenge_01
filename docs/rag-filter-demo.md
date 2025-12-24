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

---
description: Answer question using RAG context with relevance filtering
argument-hint: <question> [k] [threshold]
---

Answer the question about this project using RAG semantic search with relevance filtering.

## Parameters
- `$1` - Question about the project (required)
- `$2` - Number of top candidates to retrieve (default: 10)
- `$3` - Similarity threshold 0.0-1.0 (default: 0.70, means 70%)

## Instructions

### Step 1: Check Index Status
Use MCP tool `rag_status` to check if index exists. If total documents = 0, inform user to run `/rag:index` first and stop.

### Step 2: RAG Search
Use MCP tool `rag_search` with:
- query: `$1`
- limit: `$2` (or 10 if not specified)
- format: `json`

Parse the JSON response to get array of results with similarity scores.

### Step 3: Apply Relevance Filter
- Parse `$3` as threshold (default: 0.70)
- Filter results where `similarity >= threshold`
- If no results pass the threshold:
  - State "⚠️ No results passed threshold {threshold*100}%"
  - Suggest lowering threshold (try 0.60 or 0.50)
  - As fallback, use top-1 result from unfiltered candidates

### Step 4: Generate Answer
Generate answer based on filtered results:
- Use all filtered results as context
- Cite specific files when making claims
- Include file paths with line numbers where relevant

### Step 5: Output Format

```markdown
## RAG Search Results (>= {threshold*100}% similarity)

### Sources ({filtered_count} files):
{list filtered sources with similarity percentage}
- [{similarity}%] {file_path} ({language})

{if no results: "⚠️ No results passed threshold {threshold*100}%. Try lowering threshold to 0.60 or 0.50"}

### Answer:
{answer based on filtered results, cite specific files}
```

### Important Rules
- Show similarity as percentage with 1 decimal (e.g., "87.3%")
- Always cite specific files when making claims
- If fallback to top-1 is used, mention it clearly

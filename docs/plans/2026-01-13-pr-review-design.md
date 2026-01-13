# PR Review via GitHub MCP + RAG

**Date:** 2026-01-13
**Task:** TASK-006
**Status:** Design approved

## Overview

Slash-command `/pr:review` for automatic PR review using:
- **GitHub MCP** for PR diff and files
- **RAG** for project documentation context

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    /pr:review main day-19                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Parse git remote → owner/repo                       │
│         git remote get-url origin → github.com:user/repo    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Search PR via GitHub MCP                            │
│         search_pull_requests(head:day-19, base:main)        │
│         → PR #42 found                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Get PR data via GitHub MCP                          │
│         pull_request_read(method: get_files) → file list    │
│         pull_request_read(method: get_diff) → unified diff  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: RAG context                                         │
│         rag_search("review {files} architecture style")     │
│         → CLAUDE.md, README.md, docs/...                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Generate Review                                     │
│         Summary, Major/Minor issues, Questions, Test plan   │
└─────────────────────────────────────────────────────────────┘
```

## Command Interface

**File:** `.claude/commands/pr/review.md`

**Usage:**
```
/pr:review [base_ref] [head_ref]
```

**Parameters:**
- `$1` - base branch (default: main)
- `$2` - head branch (default: current branch)

**Defaults:**
| Parameter | Value |
|-----------|-------|
| k (RAG results) | 10 |
| threshold | 0.70 |
| base_ref | main |
| head_ref | HEAD |

## Algorithm

### Step 1: Detect owner/repo
```bash
git remote get-url origin
# Parse: github.com:owner/repo.git → owner, repo
```

### Step 2: Resolve head branch
If `$2` is empty or "HEAD":
```bash
git branch --show-current → actual branch name
```

### Step 3: Search PR
```
MCP: search_pull_requests(query: "head:{head} base:{base}", owner, repo)
```
If no results → error with `gh pr create` instruction

### Step 4: Get PR data
```
MCP: pull_request_read(method: get_files) → changed files list
MCP: pull_request_read(method: get_diff) → unified diff
```

### Step 5: RAG context
```
MCP: rag_search(query: "review {files} style architecture", limit: 10, format: json)
Filter: similarity >= 0.70
```

### Step 6: Generate review
Output structured markdown review with sections.

## Output Format

```markdown
## PR Review: {base}...{head}

**PR:** #{number} - {title}
**Files changed:** {count}

---

### Summary
{1-3 sentences: what changes, what risk}

---

### Major Issues
{critical: security, data, API breaking changes}

- **{file}:{line}** - {description}

---

### Minor Issues
{style, readability, improvements}

- **{file}** - {description}

---

### Questions
{what to clarify with author}

---

### Suggested Test Plan
- [ ] {test step 1}
- [ ] {test step 2}

---

### Sources
**PR Files:**
- {file1}, {file2}, ...

**RAG Context:**
- [{similarity}%] {doc_path}
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| Cannot parse remote | `Cannot detect GitHub repo. Ensure 'origin' points to GitHub.` |
| PR not found | `No PR found for {base}...{head}. Create: gh pr create --base {base} --head {head}` |
| RAG index empty | `RAG index empty. Run /rag:index first.` (continue without RAG) |
| No RAG results >= threshold | Use top-3 as fallback, note in Sources |
| Diff too large | Show first N files, warn about truncation |
| Branch not found | `Branch '{head}' not found on remote.` |

## Test Case

**Setup:**
```bash
# Ensure day-19 pushed
git push origin day-19

# Create PR if needed
gh pr create --base main --head day-19 --title "Day 19 changes" --draft

# Check RAG index
/rag:status  # if 0 → /rag:index
```

**Run:**
```
/pr:review main day-19
```

**Expected:**
- Review contains ≥5 issues/questions
- ≥3 issues reference files from diff
- Suggested test plan covers components (backend/mcp)
- Sources include PR files + ≥2 RAG sources

## Deliverables

1. `.claude/commands/pr/review.md` - slash command
2. Update `README.md` or `docs/` with usage example
3. This design document

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | GitHub MCP | No custom MCP needed, leverages existing tools |
| Command format | By branches | Matches git workflow `base...head` |
| If PR missing | Error + instruction | User decides whether to create PR |
| Owner/repo detection | From git remote | Transparent, works for most projects |
| RAG query | By changed files | Semantically relevant context |

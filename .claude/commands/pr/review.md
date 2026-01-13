---
description: Review PR using GitHub MCP and RAG documentation context
argument-hint: [base_branch] [head_branch]
---

Review a Pull Request using GitHub MCP for diff/files and RAG for project documentation context.

## Parameters
- `$1` - Base branch (default: main)
- `$2` - Head branch (default: current branch)

## Instructions

### Step 1: Detect Repository Owner and Name
Use Bash to get the remote URL:
```bash
git remote get-url origin
```

Parse the output to extract `owner` and `repo`:
- SSH format: `git@github.com:owner/repo.git` -> owner, repo
- HTTPS format: `https://github.com/owner/repo.git` -> owner, repo

If parsing fails, output error:
> Cannot detect GitHub repo. Ensure 'origin' points to GitHub.

### Step 2: Resolve Branches
- **base**: Use `$1` if provided, otherwise default to `main`
- **head**: Use `$2` if provided, otherwise get current branch:
```bash
git branch --show-current
```

### Step 3: Search for Pull Request
Use MCP tool `search_pull_requests` with:
- query: `head:{head} base:{base}`
- owner: `{owner}`
- repo: `{repo}`

If no PR found, output error:
> No PR found for {base}...{head}. Create one with:
> ```
> gh pr create --base {base} --head {head}
> ```

Extract PR number from results.

### Step 4: Get PR Data
Use MCP tool `pull_request_read` twice:

**4a. Get changed files:**
- owner: `{owner}`
- repo: `{repo}`
- pullNumber: `{pr_number}`
- method: `get_files`

**4b. Get diff:**
- owner: `{owner}`
- repo: `{repo}`
- pullNumber: `{pr_number}`
- method: `get_diff`

Note: If diff is very large (>50 files), warn about truncation and focus on first 20 files.

### Step 5: RAG Context Search
Use MCP tool `rag_search` with:
- query: `review {changed_file_names} architecture style conventions`
- limit: `10`
- format: `json`

Apply relevance filter:
- threshold: `0.70` (70%)
- Filter results where `similarity >= 0.70`

**Fallback behavior:**
- If RAG index is empty: Note "RAG index empty. Run /rag:index for better context." and continue without RAG.
- If no results pass threshold: Use top-3 results as fallback, note in Sources section.

### Step 6: Generate Review
Analyze the diff and files using:
- Changed files and their diffs
- RAG documentation context (CLAUDE.md, README, architecture docs)
- Code patterns and conventions from the project

## Output Format

```markdown
## PR Review: {base}...{head}

**PR:** #{number} - {title}
**Files changed:** {count}

---

### Summary
{1-3 sentences describing what changes and associated risk level}

---

### Major Issues
{Critical issues: security vulnerabilities, data integrity, API breaking changes, logic errors}

- **{file}:{line}** - {description of issue and suggested fix}

{If none: "No major issues found."}

---

### Minor Issues
{Style, readability, performance optimizations, code improvements}

- **{file}** - {description}

{If none: "No minor issues found."}

---

### Questions
{Clarifications needed from the PR author}

- {question about design decision or implementation choice}

{If none: "No questions."}

---

### Suggested Test Plan
- [ ] {specific test step 1}
- [ ] {specific test step 2}
- [ ] {specific test step 3}

---

### Sources

**PR Files:**
- {file1}, {file2}, {file3}, ...

**RAG Context:**
- [{similarity}%] {doc_path}
- [{similarity}%] {doc_path}

{If fallback used: "Note: RAG results below threshold, showing top-3 fallback."}
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| Cannot parse git remote | Output: "Cannot detect GitHub repo. Ensure 'origin' points to GitHub." |
| PR not found | Output: "No PR found for {base}...{head}. Create: `gh pr create --base {base} --head {head}`" |
| Branch not found on remote | Output: "Branch '{head}' not found on remote. Push with: `git push -u origin {head}`" |
| RAG index empty | Continue review without RAG, note in output |
| No RAG results >= threshold | Use top-3 as fallback, note in Sources |
| Diff too large (>50 files) | Show first 20 files, warn about truncation |

## Important Rules
- Always cite specific files and line numbers for issues
- Show similarity as percentage with 1 decimal (e.g., "87.3%")
- Focus on actionable feedback, not style nitpicks unless pattern-breaking
- If data is not visible in diff, explicitly state "not found in diff"
- Consider project conventions from RAG context when reviewing

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start

При начале новой сессии вызови tool `get_summary` из reminder MCP-сервера, чтобы показать текущие задачи по проекту.

## Orchestrator Mode

By default, Claude operates as an **agent orchestrator**:

1. **Read tickets** from `.task/`
2. **Create subtasks** for subagents
3. **Delegate work** via Task tool
4. **Collect results** and update ticket statuses

> **IMPORTANT:** After completing a task, always update ticket status and mark completed Acceptance Criteria (`[x]`).

### Subagent Types

| Type | When to use |
|------|-------------|
| `Explore` | Codebase exploration, file search |
| `Plan` | Implementation planning |
| `general-purpose` | Complex multi-step tasks |
| `code-reviewer` | Code review |

---

## Project Overview

Chat application with Gemini AI integration. Uses message queue architecture with multiple API keys rotation.

## Architecture

```
Nginx :80 → Frontend (Vue :5173) / Backend (FastAPI :8000)
                                        ↓
PostgreSQL ← Backend → Redis
                  ↓
             RabbitMQ
                  ↓
          Gemini Client Worker (multi-key rotation)
                  ↓
             Hysteria2 Proxy → Gemini API
```

**Two repositories:**
- `day1-app` (this repo): Vue frontend, FastAPI backend, Docker Compose
- `gemini-client`: Separate RabbitMQ worker for Gemini API (included as subdirectory)

## Commands

### Docker
```bash
docker-compose up -d                    # Start all services
docker-compose up -d --build            # Rebuild and start
docker-compose logs -f <service>        # View logs (backend, frontend, gemini-client)
docker-compose down                     # Stop services
docker-compose down -v                  # Stop and remove volumes (destroys data)
```

### Backend (Python 3.11+)
```bash
cd backend
pip install -e ".[dev]"                 # Install with dev dependencies
uvicorn app.main:app --reload           # Run dev server
alembic upgrade head                    # Run migrations
alembic revision --autogenerate -m "description"  # Create migration

# Testing
pytest                                  # Run all tests
pytest tests/test_specific.py           # Run single file
pytest tests/test_specific.py::test_name  # Run single test
pytest --cov=app                        # Run with coverage

# Linting
black app tests                         # Format code
ruff check app tests                    # Lint
mypy app                                # Type check
```

### Frontend (Node 20+)
```bash
cd frontend
npm install                             # Install dependencies
npm run dev                             # Run dev server
npm run build                           # Build for production

# Testing
npm run test                            # Run tests (vitest)
npm run test -- tests/specific.test.ts  # Run single file

# Linting
npm run lint                            # ESLint
```

### Gemini Client Worker
```bash
cd gemini-client
pip install -e ".[dev]"                 # Install with dev dependencies
python -m src.main                      # Run worker

# Testing
pytest                                  # Run all tests
pytest --cov=src                        # Run with coverage

# Linting
black src tests
ruff check src tests
mypy src
```

## Key Configuration

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEYS` | Comma-separated Gemini API keys |
| `KEYS_MAX_PER_MINUTE` | Rate limit per key (default: 10) |
| `QUEUE_RETRY_DELAYS` | Retry delays in seconds (default: 60,600,3600,86400) |
| `HTTP_PROXY` | Hysteria2 proxy URL |

## Documentation

| Path | Contents |
|------|----------|
| `.task/` | Current tasks/tickets |
| `.memory-base/technical-docs/` | Technical documentation |
| `.env.example` | Environment variables template |

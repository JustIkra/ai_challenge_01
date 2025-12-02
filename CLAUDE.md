# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Режим работы: Оркестратор агентов

По умолчанию Claude работает как **оркестратор агентов**:

1. **Читает тикеты** из `.memory-base/master/`
2. **Создаёт подзадачи** в `.memory-base/worker/`
3. **Делегирует работу** субагентам через Task tool
4. **Собирает результаты** и обновляет статусы

> **ВАЖНО:** После выполнения задачи **обязательно обновить статус тикета** на `done` и отметить выполненные Acceptance Criteria (`[x]`).

**Полное описание процесса:** [.memory-base/workflow/README.md](.memory-base/workflow/README.md)

### Типы субагентов

| Тип | Когда использовать |
|-----|-------------------|
| `Explore` | Исследование кодовой базы, поиск файлов |
| `Plan` | Планирование реализации |
| `general-purpose` | Сложные многошаговые задачи |
| `code-reviewer` | Ревью кода |

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
- `gemini-client`: Separate RabbitMQ worker for Gemini API

## Commands

### Docker
```bash
docker-compose up -d              # Start all services
docker-compose up -d --build      # Rebuild after changes
docker-compose logs -f            # View logs
docker-compose down               # Stop services
```

### Backend (Python 3.11+)
```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

### Frontend (Node 20+)
```bash
cd frontend
npm install
npm run dev
npm run test
```

## Documentation

| Путь | Содержание |
|------|------------|
| `.memory-base/workflow/` | Процесс работы оркестратора |
| `.memory-base/master/` | Входящие тикеты |
| `.memory-base/worker/` | Тикеты для субагентов |
| `.memory-base/technical-docs/` | Техническая документация |
| `.env.example` | Переменные окружения |

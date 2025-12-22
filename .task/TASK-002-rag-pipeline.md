# TASK-002: RAG Pipeline — Semantic Code Search

## Статус: `done`

## Описание

Семантический поиск по коду и документации проекта через slash-команды Claude Code.

## Контекст

- Scope: только текущий проект (`day 1/`)
- Embeddings: OpenRouter API (`openai/text-embedding-3-small`)
- Storage: PostgreSQL + pgvector (существующая БД)
- Chunking: код — файлы целиком, docs — по параграфам
- Interface: MCP Server + Slash Commands

## Дизайн

См. `docs/plans/2025-12-22-rag-pipeline-design.md`

## Deliverables

1. **MCP Server** (`mcp/rag-server/`):
   - `rag_index` — индексация проекта
   - `rag_search` — semantic search
   - `rag_status` — статистика
   - `rag_clear` — очистка

2. **Slash Commands** (`.claude/commands/rag/`):
   - `/rag:index` — полная индексация
   - `/rag:update` — инкрементальное обновление
   - `/rag:search <query>` — поиск
   - `/rag:status` — статус
   - `/rag:clear` — очистка

3. **Database Migration**:
   - Таблица `rag_documents` с pgvector

## Acceptance Criteria

- [x] pgvector расширение установлено в PostgreSQL (image: pgvector/pgvector:pg16)
- [x] Таблица `rag_documents` создана с HNSW vector индексом
- [x] `/rag:index` индексирует .py, .js, .ts, .vue, .md файлы
- [x] `/rag:search` возвращает top-5 релевантных файлов с similarity score
- [x] `/rag:update` пропускает неизменённые файлы (по hash)
- [x] `/rag:status` показывает количество файлов по типу и языку
- [x] Retry логика для OpenRouter API (429 errors) с exponential backoff
- [x] MCP сервер зарегистрирован в `.mcp.json`

## Структура файлов

```
mcp/rag-server/
├── index.mjs           # MCP server entry (4 tools)
├── lib/
│   ├── loader.mjs      # File loading + hash
│   ├── embeddings.mjs  # OpenRouter API + retry
│   └── db.mjs          # PostgreSQL operations
├── config.mjs          # Configuration
└── package.json

.claude/commands/rag/
├── index.md
├── update.md
├── search.md
├── status.md
└── clear.md

backend/migrations/
└── rag_init.sql        # pgvector + table schema
```

## Инструкция по запуску

```bash
# 1. Пересоздать postgres с pgvector (УДАЛИТ ДАННЫЕ!)
docker-compose down -v
docker-compose up -d postgres

# 2. Установить зависимости MCP сервера
cd mcp/rag-server && npm install

# 3. Добавить OPENROUTER_API_KEY в .env
echo "OPENROUTER_API_KEY=your_key" >> .env

# 4. Перезапустить Claude Code для загрузки MCP сервера

# 5. Использовать slash-команды
/rag:index     # проиндексировать проект
/rag:search "как работает авторизация"
```

## Приоритет: `high`

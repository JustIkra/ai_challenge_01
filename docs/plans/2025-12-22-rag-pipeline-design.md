# RAG Pipeline Design — Semantic Code Search

## Overview

Semantic search по коду и документации проекта через slash-команды Claude Code.

## Решения

| Аспект | Решение |
|--------|---------|
| Scope | Только текущий проект (`day 1/`) |
| Embeddings | OpenRouter API (`openai/text-embedding-3-small`) |
| Storage | PostgreSQL + pgvector |
| Chunking | Код: файлы целиком, Docs: по параграфам |
| Interface | MCP Server + Slash Commands |

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    Slash Commands                        │
│  /rag:index  /rag:update  /rag:search  /rag:status      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                 MCP Server (rag-server)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │  Loader  │→ │ Chunker  │→ │Embeddings│→ │  Index  │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              PostgreSQL + pgvector                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ rag_documents: id, path, content, embedding...  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Схема базы данных

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_documents (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL,              -- 'code' | 'docs'
    content TEXT NOT NULL,
    embedding vector(1536),
    file_hash TEXT NOT NULL,              -- SHA256 для incremental update
    indexed_at TIMESTAMP DEFAULT NOW(),
    language TEXT,
    lines_count INTEGER
);

CREATE INDEX ON rag_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX ON rag_documents (file_path);
```

## Конфигурация

```javascript
const CONFIG = {
  code: {
    patterns: ['**/*.py', '**/*.js', '**/*.ts', '**/*.vue'],
    ignore: ['node_modules/**', '__pycache__/**', 'dist/**', '.git/**']
  },
  docs: {
    patterns: ['**/*.md', '.memory-base/**/*'],
    ignore: ['node_modules/**']
  },
  embeddings: {
    model: 'openai/text-embedding-3-small',
    batchSize: 50,
    maxRetries: 3,
    retryDelay: 1000
  },
  limits: {
    maxFileSize: 100 * 1024,  // 100KB
    maxTokens: 8191
  }
};
```

## Slash Commands

| Команда | Описание |
|---------|----------|
| `/rag:index` | Полная индексация проекта |
| `/rag:update` | Инкрементальное обновление (по hash) |
| `/rag:search <query>` | Поиск top-k релевантных файлов |
| `/rag:status` | Статистика индекса |
| `/rag:clear` | Очистка индекса |

## MCP Tools

| Tool | Параметры | Описание |
|------|-----------|----------|
| `rag_index` | `force?: boolean` | Индексация (force=true для полной) |
| `rag_search` | `query: string, limit?: number` | Semantic search |
| `rag_status` | - | Статистика |
| `rag_clear` | - | Очистка |

## Структура файлов

```
mcp/rag-server/
├── index.mjs           # MCP server entry
├── lib/
│   ├── loader.mjs      # File loading
│   ├── chunker.mjs     # Text splitting
│   ├── embeddings.mjs  # OpenRouter API
│   └── db.mjs          # PostgreSQL operations
├── config.mjs
└── package.json

.claude/commands/rag/
├── index.md
├── update.md
├── search.md
├── status.md
└── clear.md
```

## Зависимости

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "pg": "^8.11.0",
    "pgvector": "^0.2.0",
    "glob": "^10.0.0",
    "crypto": "builtin"
  }
}
```

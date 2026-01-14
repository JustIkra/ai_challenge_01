# TASK-022: Спецификация — Support Assistant Telegram Bot (RAG)

## Резюме

Telegram-бот для ответов на вопросы конечных пользователей с использованием RAG (Retrieval-Augmented Generation). Бот принимает вопросы, ищет релевантный контекст в проиндексированной репозитории через существующий `rag-server`, и генерирует ответ с помощью LLM через OpenRouter API.

---

## Решения по результатам интервью

### Аудитория и доступ
| Параметр | Решение |
|----------|---------|
| Целевая аудитория | Конечные пользователи (self-service) |
| Авторизация | Без авторизации (MVP) — любой может использовать |
| Доступ к тикетам | Нет CRM, только RAG-ответы |
| Chat type | Только личные сообщения (DM) |
| Rate limiting | Без лимита (MVP) |

### RAG и LLM
| Параметр | Решение |
|----------|---------|
| RAG scope | Вся репозитория (code + docs) |
| RAG top-k | 3-5 результатов |
| LLM модель | Конфигурируемо через `.env` (`OPENROUTER_MODEL`) |
| No-match behavior | Ответить без источников (на основе общих знаний LLM) |
| Context memory | Stateless — каждый вопрос обрабатывается отдельно |

### UX/UI
| Параметр | Решение |
|----------|---------|
| Формат ответа | Структурированный (Summary / Шаги / Источники) |
| Показ источников | Только имя файла (без полного пути) |
| Команды бота | `/start`, `/questions` |
| Индикация загрузки | "Печатаю..." (Telegram typing action) |
| Обработка ошибок | Простой отказ ("Произошла ошибка, попробуйте позже") |
| Feedback buttons | Нет (MVP) |

### Технические решения
| Параметр | Решение |
|----------|---------|
| Telegram библиотека | aiogram (async) |
| RAG интеграция | HTTP API (добавить к существующему rag-server) |
| RAG HTTP порт | 8801 |
| Deployment | Отдельный сервис в docker-compose.yml |
| Telegram API mode | Long polling |
| Не-текстовые сообщения | Игнорировать |
| Длинные вопросы (>1000 символов) | Обрезать |
| Длинные ответы (>4096 символов) | Обрезать до 4000 |
| FAQ создание | Использовать существующие доки |
| RAG индексация | Пред-индексация (вручную через `/rag:index`) |
| Системный промпт LLM | Нейтральный ассистент |
| Content policy | Без ограничений (MVP) |
| Логирование | Только ошибки |
| Тестирование | Ручное (MVP) |

---

## Архитектура

```
┌─────────────────┐     HTTP :8801      ┌──────────────┐
│  Telegram Bot   │◄──────────────────►│  rag-server  │
│   (aiogram)     │     /api/search     │  (existing)  │
└────────┬────────┘                     └──────┬───────┘
         │                                     │
         │ HTTP                                │ PG/pgvector
         ▼                                     ▼
┌─────────────────┐                    ┌──────────────┐
│   OpenRouter    │                    │  PostgreSQL  │
│      API        │                    │   (vectors)  │
└─────────────────┘                    └──────────────┘
```

### Компоненты

1. **support-bot/** — новый Python-сервис
   - `main.py` — aiogram bot с long polling
   - `rag_client.py` — HTTP клиент для rag-server
   - `llm_client.py` — OpenRouter API клиент
   - `config.py` — конфигурация из `.env`
   - `prompts/system.txt` — системный промпт для LLM

2. **mcp/rag-server/** — расширение существующего
   - Добавить HTTP API endpoint `/api/search`
   - Порт 8801

---

## API Contracts

### RAG Server HTTP API

**Endpoint:** `POST /api/search`

**Request:**
```json
{
  "query": "почему не работает авторизация",
  "limit": 5,
  "format": "json"
}
```

**Response:**
```json
{
  "results": [
    {
      "rank": 1,
      "file_path": "docs/auth.md",
      "file_type": "docs",
      "language": "markdown",
      "similarity": 0.89,
      "lines_count": 45,
      "content": "..."
    }
  ],
  "count": 5
}
```

**Endpoint:** `GET /api/status`

**Response:**
```json
{
  "total": 150,
  "by_type": { "code": 120, "docs": 30 },
  "by_language": { "python": 50, "javascript": 40, "markdown": 30, "vue": 30 }
}
```

---

## Telegram Bot Flow

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и краткая справка |
| `/questions` | Показать примеры вопросов |

### Обработка сообщений

```
User sends text message
         │
         ▼
┌─────────────────────────────────┐
│ 1. Validate: text only, ≤1000  │
│    chars (truncate if longer)   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 2. Send "typing" action         │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 3. RAG search (top-5)           │
│    POST rag-server:8801/api/search │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 4. Build LLM prompt:            │
│    - System prompt              │
│    - RAG context (snippets)     │
│    - User question              │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 5. Call OpenRouter API          │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 6. Format response:             │
│    - Summary                    │
│    - Steps                      │
│    - Sources (file names only)  │
│    - Truncate to 4000 chars     │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ 7. Send message to user         │
└─────────────────────────────────┘
```

---

## Формат ответа

```
📋 Краткий ответ
[1-2 предложения с сутью ответа]

📝 Рекомендации
1. [Шаг 1]
2. [Шаг 2]
3. [Шаг 3]

📚 Источники
• auth.md
• api-reference.md
```

При отсутствии релевантных источников — секция "Источники" опускается.

---

## Системный промпт LLM

```text
Ты ассистент поддержки. Отвечай на вопросы пользователей по существу, опираясь на предоставленный контекст из документации.

Правила:
1. Давай конкретные, полезные ответы
2. Если контекст не содержит информации — отвечай на основе общих знаний, но укажи что точной информации нет
3. Используй структурированный формат: краткий ответ, затем шаги/рекомендации
4. Пиши на русском языке
5. Не выдумывай несуществующие функции или настройки
6. Если вопрос требует уточнения — задай 1-2 конкретных вопроса
```

---

## Конфигурация (.env)

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=<token>

# OpenRouter
OPENROUTER_API_KEYS=<key1,key2>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3-haiku

# RAG Server
RAG_HTTP_PORT=8801
RAG_TOP_K=5

# Limits
MAX_INPUT_LENGTH=1000
MAX_OUTPUT_LENGTH=4000
```

---

## Структура файлов

```
support-bot/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── main.py           # Bot entry point
│   ├── config.py         # Environment config
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py   # /start, /questions
│   │   └── messages.py   # Text message handler
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag_client.py # HTTP client for rag-server
│   │   └── llm_client.py # OpenRouter client
│   └── prompts/
│       └── system.txt    # LLM system prompt
└── tests/                # (empty for MVP)

mcp/rag-server/
├── index.mjs             # Existing MCP server
├── http-server.mjs       # NEW: HTTP API wrapper
└── ...
```

---

## Docker Compose

```yaml
# Добавить в docker-compose.yml

support-bot:
  build:
    context: ./support-bot
    dockerfile: Dockerfile
  environment:
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - OPENROUTER_API_KEYS=${OPENROUTER_API_KEYS}
    - OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
    - OPENROUTER_MODEL=${OPENROUTER_MODEL:-anthropic/claude-3-haiku}
    - RAG_SERVER_URL=http://rag-server:8801
    - RAG_TOP_K=${RAG_TOP_K:-5}
    - MAX_INPUT_LENGTH=${MAX_INPUT_LENGTH:-1000}
    - MAX_OUTPUT_LENGTH=${MAX_OUTPUT_LENGTH:-4000}
  depends_on:
    - rag-server
  restart: unless-stopped

rag-server:
  build:
    context: ./mcp/rag-server
    dockerfile: Dockerfile
  ports:
    - "8801:8801"
  environment:
    - RAG_DATABASE_URL=${RAG_DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/chatapp}
    - RAG_HTTP_PORT=8801
    - PROJECT_ROOT=/app/project
  volumes:
    - .:/app/project:ro
  depends_on:
    - postgres
  restart: unless-stopped
```

---

## Зависимости (requirements.txt)

```
aiogram>=3.0.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
```

---

## Acceptance Criteria (из тикета)

- [ ] Бот отвечает на общий вопрос без тикета (используя RAG) и возвращает "Источники"
- [ ] ~~Бот отвечает на вопрос с тикетом и явно учитывает поля тикета~~ (убрано — без CRM)
- [ ] Если данных недостаточно — бот отвечает на основе общих знаний (без галлюцинаций о продукте)
- [ ] ~~Есть минимум 5 FAQ статей~~ (используем существующие доки)
- [ ] Индекс RAG не пустой (`/rag:status` показывает документы)
- [ ] Секреты не попадают в git (токены/ключи только в `.env`)

---

## Deliverables

1. ✅ **support-bot/** — Python-сервис с aiogram
2. ✅ **mcp/rag-server/http-server.mjs** — HTTP API wrapper для RAG
3. ✅ **docker-compose.yml** — добавить сервисы support-bot и rag-server
4. ✅ **Документация** — README в support-bot/

---

## Edge Cases

| Сценарий | Поведение |
|----------|-----------|
| Пустое сообщение | Игнорировать |
| Стикер/фото/голосовое | Игнорировать |
| Сообщение >1000 символов | Обрезать до 1000 |
| RAG не нашёл результатов | LLM отвечает без источников |
| OpenRouter недоступен | "Произошла ошибка, попробуйте позже" |
| Ответ >4096 символов | Обрезать до 4000 + "..." |
| Сообщение в группе | Игнорировать |

---

## Risks & Mitigations

| Риск | Митигация |
|------|-----------|
| OpenRouter API costs | Использовать дешёвые модели (claude-3-haiku) |
| LLM hallucinations | Системный промпт + RAG grounding |
| Bot abuse | MVP без защиты; при необходимости добавить whitelist |
| RAG index outdated | Документировать необходимость ручной переиндексации |

---

## Out of Scope (для MVP)

- CRM интеграция (тикеты, пользователи)
- Авторизация пользователей
- Rate limiting
- Session memory (multi-turn conversations)
- Feedback collection
- Image/voice processing
- Группы и каналы
- Автоматическая переиндексация

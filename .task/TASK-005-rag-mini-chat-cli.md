# TASK-005: Мини-чат (CLI) с RAG-памятью и источниками (slash-команда)

## Статус: `done`

## Описание

Реализовать простой чат-бот в CLI через slash-команду, который:
- хранит историю диалога (память сессии),
- на каждом новом вопросе делает retrieval контекста из базы документов через текущий RAG (`rag_search`),
- отвечает с учётом **истории + найденных документов**,
- **обязательно** печатает блок `Источники`, откуда был взят ответ (file_path + similarity).

Результат: “мини-чат” в рамках Claude Code CLI, где каждый вызов `/rag:chat` — это новый ход диалога, но контекст сессии сохраняется между вызовами.

## Контекст

- В проекте есть MCP server `rag-server` с инструментами `rag_status`, `rag_search`.
- Есть набор RAG slash-команд в `.claude/commands/rag/`.

## Пользовательский сценарий (MVP)

1) `/rag:chat "Привет! Что это за проект?"`
2) `/rag:chat "А где у вас реализован RAG поиск?"`
3) `/rag:chat:history`  — показать последние N сообщений
4) `/rag:chat:reset` — сбросить память сессии

## Дизайн: варианты реализации (выбрать один)

### Вариант A (рекомендованный): память через Postgres + MCP tools в `rag-server`

Добавить в `rag-server` минимальные tools для работы с историей диалога, чтобы slash-команда не требовала небезопасного Bash/файловых операций:
- `rag_chat_turn` (или `rag_chat_prepare` + `rag_chat_append`) — читает историю сессии, делает `rag_search`, возвращает структурированный контекст для ответа, сохраняет user/assistant сообщения.

Память хранить в Postgres (в той же БД, где `rag_documents`), например таблица:

- `rag_chat_messages`:
  - `id bigserial primary key`
  - `session_id text not null`
  - `role text not null` (`user` | `assistant`)
  - `content text not null`
  - `sources jsonb null` (для сообщений assistant: массив `{file_path, similarity}`)
  - `created_at timestamptz not null default now()`
  - индекс: `(session_id, created_at)`

Миграция: `backend/migrations/rag_chat_init.sql`.

## Пайплайн на каждый ход

1) Проверка индекса: `rag_status` → если документов 0, подсказать `/rag:index` и остановиться.
2) Загрузка истории: последние `N` сообщений (например, N=8) из сессии.
3) Retrieval: `rag_search(query=<message>, limit=k)` (k по умолчанию 5).
4) Контекст: собрать top‑k (или filtered) в блок `CONTEXT` (ограничить размером, например 6–10KB текста).
5) Ответ: с учётом `HISTORY` + `CONTEXT`, с обязательной атрибуцией источников.
6) Сохранение: дописать в историю `user` и `assistant` (вместе с источниками, которые реально использованы).

## Формат вывода (обязательный)

```
## Источники
1. [92.1%] path/to/file.ext
2. [83.4%] path/to/other.md

## Ответ
...
```

Если источников нет — всё равно печатать блок `Источники` и явно писать, что релевантных документов не найдено.

## Deliverables

1) Новая slash-команда:
- `.claude/commands/rag/chat.md` → `/rag:chat <message> [k] [session]`

2) Команды управления памятью (MVP минимум — reset):
- `.claude/commands/rag/chat-reset.md` → `/rag:chat:reset [session]`
- `.claude/commands/rag/chat-history.md` → `/rag:chat:history [n] [session]`

3) Изменения в `mcp/rag-server/` (вариант A, обязательный):
- tools для работы с Postgres-историей:
  - `rag_chat_history(session_id, limit)` → последние N сообщений (структурировано)
  - `rag_chat_append(session_id, role, content, sources?)` → сохранить сообщение
  - `rag_chat_reset(session_id)` → удалить историю сессии

4) Миграция БД:
- `backend/migrations/rag_chat_init.sql` (таблица `rag_chat_messages` + индексы)

5) Документация:
- короткая секция в `README.md` (или отдельный doc) с примерами команд и сессий.

## Acceptance Criteria

- [x] `/rag:chat "<msg>"` использует историю сессии (второй вопрос учитывает первый).
- [x] На каждом ходе выполняется retrieval через `rag_search`.
- [x] В каждом ответе есть блок `Источники` (даже если пусто).
- [x] Источники содержат `file_path` и similarity (в процентах).
- [x] Есть способ сбросить память (`/rag:chat:reset`).
- [x] Память сохраняется между вызовами команд (персистентно) в Postgres (`rag_chat_messages`).
- [x] При пустом индексе команда подсказывает запустить `/rag:index`.

## Приоритет: `high`

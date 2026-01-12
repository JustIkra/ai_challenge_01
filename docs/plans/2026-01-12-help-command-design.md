# /help Command Design (MVP)

## Overview

Slash-команда `/help` — единая точка входа для Q&A по проекту. Обёртка над существующим RAG с форматированием ответа и атрибуцией источников.

## Решения

| Аспект | Решение |
|--------|---------|
| Вариант | MVP (без repo-context MCP) |
| Расположение | `.claude/commands/help.md` |
| Пустой индекс | Предложить `/rag:index` и остановиться |
| Формат источников | Компактный (file path + similarity) |

## Поведение

```
┌─────────────────────────────────────────┐
│           /help <question>              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│        1. Check rag_status              │
│     (total documents > 0?)              │
└─────────────────┬───────────────────────┘
                  │
          ┌───────┴───────┐
          │               │
          ▼               ▼
     [empty]         [has docs]
          │               │
          ▼               ▼
┌─────────────┐   ┌─────────────────────┐
│ Show error: │   │ 2. rag_search       │
│ Run         │   │    query, limit=10  │
│ /rag:index  │   │    format=json      │
└─────────────┘   └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ 3. Filter by        │
                  │    similarity >= 65%│
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ 4. Generate answer  │
                  │    with citations   │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │ 5. Format output    │
                  │    - Answer         │
                  │    - Sources list   │
                  └─────────────────────┘
```

## Формат вывода

```markdown
## Ответ

{answer based on context, citing specific files}

### Источники:
- [87.3%] README.md (markdown)
- [72.1%] backend/app/main.py (python)
```

## Файл команды

`.claude/commands/help.md`

## Acceptance Criteria

- [x] `/help "как запустить проект?"` → ссылается на `README.md` / `CLAUDE.md`
- [x] `/help "правила работы ассистента"` → ссылается на `CLAUDE.md`
- [x] `/help "API эндпоинты"` → ссылается на backend routes
- [x] `/help "схема данных"` → ссылается на models/migrations
- [x] Источники содержат file_path и similarity %
- [x] Пустой индекс → предлагает `/rag:index`

## Ограничения MVP

- Нет git repo context (ветка, статус изменений)
- Нет line numbers в источниках
- Нет debug режима

## Возможные улучшения (v2)

1. Добавить MCP `repo-context` для git информации
2. Добавить `/help --debug` для отладки
3. Добавить line numbers из RAG метаданных

# Draft: Агент ↔ реальное окружение (Docker) + проверка на реальном девайсе

## Контекст
В репозитории уже есть `docker-compose.yml` со всем стеком (nginx → frontend/backend, postgres, redis, rabbitmq, worker, proxy).
Нужно “привязать” агента к реальному окружению так, чтобы он мог:
- поднимать/пересобирать Docker Compose стек,
- запускать/смотреть длительные процессы (логи) “в фоне”,
- дать воспроизводимую проверку результата на реальном девайсе (телефон/планшет).

Дополнительно: хочется использовать slash-команды Claude Code CLI для типовых операций (логи, rebuild, status, restart), а длительные (tail logs) — запускать “в фоне”.

## Цель
Сделать минимальный, но практичный workflow, который позволяет из Claude Code:
1) поднять окружение через Docker Compose,
2) быстро управлять сервисами и логами через slash-команды,
3) проверить приложение на реальном устройстве в LAN.

MCP “docker-runner” + slash-команды-обертки (более структурно)
- Поднять локальный MCP-сервер (Node/Python) с инструментами: `compose_up`, `compose_ps`, `compose_logs`, `compose_build`, `start_bg_job`, `job_status`, `job_logs`, `job_stop`.
- Slash-команды дергают MCP-инструменты (или просто помогают запрашивать их).
- Плюс: “фоновые” задачи становятся нормальными job’ами с `jobId`.

## Deliverables
- Набор custom slash-команд для управления стеком в `.claude/commands/stack/…`
- Док/README по использованию команд и “фоновых” логов
- Демонстрация проверки на реальном девайсе (телефон) по LAN URL

## Acceptance Criteria
- Из Claude Code в корне проекта:
  - `/stack-up` поднимает окружение (`docker compose up -d`) и возвращает статус.
  - `/stack-ps` показывает состояние контейнеров (все нужные сервисы `Up`/`healthy`).
  - `/stack-rebuild [service]` пересобирает и перезапускает весь стек или конкретный сервис.
  - `/stack-logs <service>` показывает последние логи и/или поток.
  - `/stack-bg-logs <service>` запускает просмотр логов “в фоне” (tmux/nohup) и возвращает как смотреть/остановить.
- С реального девайса в той же сети открывается `http://<LAN_IP>:8089` и отображается фронтенд.
- `http://<LAN_IP>:8089/api/health` возвращает OK (или ожидаемый health payload).

## Спека slash-команд Claude Code (что именно делаем)
### Где лежат команды
- Проектные: `.claude/commands/` (шарятся через репозиторий)
- Персональные: `~/.claude/commands/` (локально на машине)
- Для группировки: использовать подпапки (namespaces), напр. `.claude/commands/stack/*.md`

### Формат команды
Markdown-файл, опционально с YAML frontmatter, например:
```md
---
description: Поднять docker compose стек
argument-hint: [options]
allowed-tools:
  - Bash(docker:*)
---

Запусти стек с опциями: $ARGUMENTS
!`docker compose up -d $ARGUMENTS`
!`docker compose ps`
```

### Поддерживаемые “фичи” (нужны нам)
- Аргументы: `$ARGUMENTS` (все), `$1`, `$2`, … (позиционные)
- File references: `@path/to/file` (подмешивает содержимое файла в контекст команды)
- Bash inline: `!`команда`` (выполняет bash и подставляет вывод)
- Безопасность: ограничивать `allowed-tools`, особенно Bash через фильтры (`Bash(docker:*)`, `Bash(tmux:*)`, …)

## Команды (минимальный набор)
Имена условные — финализировать под реальные нужды.
- `/stack-up [options]` → `docker compose up -d …` + `ps`
- `/stack-down` → `docker compose down` (без `-v` по умолчанию)
- `/stack-ps` → `docker compose ps`
- `/stack-rebuild [service]` → `docker compose up -d --build [service]`
- `/stack-logs <service> [--tail N]` → `docker compose logs …`
- `/stack-bg-logs <service>` → фоновый tail логов (tmux/nohup), вернуть как смотреть/стопать
- `/stack-restart <service>` → `docker compose restart <service>`
- `/stack-exec <service> <cmd…>` → `docker compose exec …` (опционально; аккуратно с безопасностью)

## “Фоновые” логи (рекомендованный механизм)
### Вариант 1: tmux (удобнее всего для “фона”)
Команда запуска:
```bash
tmux new-session -d -s stack-logs-backend "docker compose logs -f backend"
```
Просмотр:
```bash
tmux attach -t stack-logs-backend
```
Останов:
```bash
tmux kill-session -t stack-logs-backend
```

## Риски/нюансы
- “Фон” в slash-командах лучше делать через tmux/nohup или через отдельный MCP runner (jobId), иначе команды будут “висеть” на `logs -f`.
- Командные фильтры для Bash лучше держать узкими (docker/tmux), чтобы не раздать лишние права.
- Не использовать `docker compose down -v` по умолчанию — это разрушает данные (volumes).

1) Под “cloud slash команды” имеется в виду Claude Code CLI (локально)
2) Для “фоновых” логов предпочтительнее `tmux` (можно поставить)


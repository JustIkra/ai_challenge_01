# TASK-001: Slash-команды для управления Docker Compose стеком

## Статус: `done`

## Описание

Создать набор custom slash-команд Claude Code для управления Docker Compose окружением проекта. Команды должны позволять поднимать/останавливать стек, просматривать логи (включая фоновый режим), и проверять приложение на реальном устройстве по LAN.

**Реализация:** MCP-сервер `docker-runner` + slash-команды обёртки (вместо прямых Bash команд).

## Контекст

Проект использует `docker-compose.yml` со стеком: nginx → frontend/backend, postgres, redis, rabbitmq, worker, proxy. Нужна возможность быстро управлять стеком из Claude Code CLI.

## Ссылки на документацию

### Claude Code Custom Slash Commands
- **Официальная документация**: https://context7.com/anthropics/claude-code/llms.txt
- **Формат команд**: Markdown-файлы в `.claude/commands/`
- **Frontmatter поля**:
  - `description` - описание команды
  - `argument-hint` - подсказка по аргументам
  - `allowed-tools` - разрешённые инструменты (напр. `Bash(docker:*)`)
  - `model` - модель для выполнения (опционально)

### Примеры форматов команд

```markdown
---
description: Brief description
argument-hint: [arg1] [arg2]
allowed-tools: Read, Bash(git:*)
---

Command prompt content with:
- Arguments: $1, $2, or $ARGUMENTS
- Files: @path/to/file
- Bash: !`command here`
```

## Deliverables

1. **Slash-команды** в `.claude/commands/stack/`:
   - `/stack-up` - поднять стек
   - `/stack-down` - остановить стек
   - `/stack-ps` - статус контейнеров
   - `/stack-rebuild` - пересобрать сервисы
   - `/stack-logs` - просмотр логов
   - `/stack-bg-logs` - фоновые логи через tmux
   - `/stack-restart` - перезапуск сервиса

2. **README** по использованию команд

## Acceptance Criteria

- [x] `/stack/up` поднимает окружение (`compose_up` MCP tool) и возвращает статус
- [x] `/stack/ps` показывает состояние контейнеров (`compose_ps` MCP tool)
- [x] `/stack/rebuild [service]` пересобирает и перезапускает (`compose_build` MCP tool)
- [x] `/stack/logs <service>` показывает последние логи (`compose_logs` MCP tool)
- [x] `/stack/bg-logs <service>` запускает фоновый просмотр (`job_start` MCP tool, без tmux)
- [x] `/stack/exec <service> <cmd>` выполняет команду в контейнере (`compose_exec` MCP tool)
- [x] `/stack/jobs` управляет фоновыми задачами (`job_list`, `job_logs`, `job_stop` MCP tools)
- [ ] С реального девайса в той же сети открывается `http://<LAN_IP>:8089` — требует теста
- [ ] `http://<LAN_IP>:8089/api/health` возвращает OK — требует теста

## Технические детали

### Архитектура
```
MCP Server (docker-runner)     Slash Commands
├── compose_up                 /stack/up
├── compose_down               /stack/down
├── compose_ps                 /stack/ps
├── compose_build              /stack/rebuild
├── compose_logs               /stack/logs
├── compose_restart            /stack/restart
├── compose_exec               /stack/exec
├── job_start                  /stack/bg-logs
├── job_list                   /stack/jobs
├── job_logs
└── job_stop
```

### Структура файлов
```
mcp/docker-runner/
├── index.mjs           # MCP server entry point
├── lib/
│   ├── compose.mjs     # Docker Compose operations
│   └── jobs.mjs        # Background job manager
└── package.json

.claude/commands/stack/
├── up.md, down.md, ps.md, rebuild.md
├── logs.md, restart.md, exec.md
├── bg-logs.md, jobs.md
```

### Фоновые задачи
Вместо tmux используется in-memory JobManager с child_process.spawn:
- `job_start` — запускает процесс, возвращает jobId
- `job_logs` — читает буферизованный stdout/stderr
- `job_stop` — отправляет SIGTERM

### Безопасность
- MCP tools изолированы от shell injection (execSync с массивом аргументов)
- `compose_down` по умолчанию НЕ удаляет volumes

## Приоритет: `medium`

# MCP: Location Tracker

MCP-сервер для определения местоположения по публичному IP-адресу.

## Описание

`location-tracker-mcp` использует внешний API геолокации (ip-api.com) для определения приблизительного местоположения на основе публичного IP машины, где запущен агент.

## Установка

```bash
cd mcp/location-tracker
npm install
```

## Запуск

```bash
npm start
```

Сервер работает через stdio и совместим с MCP-клиентами (Claude Desktop, Claude Code и др.).

## Регистрация в Claude Code

Добавьте в `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "location-tracker": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/mcp/location-tracker/index.mjs"]
    }
  }
}
```

## Инструменты

### `get-current-location`

Возвращает приблизительное текущее местоположение по публичному IP.

**Параметры:** нет

**Пример ответа:**
```json
{
  "ip": "203.0.113.42",
  "city": "Moscow",
  "region": "Moscow",
  "country": "Russia",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "isp": "ISP Name"
}
```

## Архитектура

```
┌─────────────────┐     stdio      ┌────────────────────┐
│  MCP Client     │ ◄────────────► │ location-tracker   │
│ (Claude Code)   │                │                    │
└─────────────────┘                └─────────┬──────────┘
                                             │
                                             ▼ HTTP
                                   ┌────────────────────┐
                                   │   ip-api.com       │
                                   │ (geolocation API)  │
                                   └────────────────────┘
```

## Зависимости

- `@modelcontextprotocol/sdk` — MCP TypeScript SDK
- `zod` — валидация схем

## Ограничения

- ip-api.com бесплатен для некоммерческого использования
- Точность зависит от IP-провайдера
- Требуется доступ к интернету


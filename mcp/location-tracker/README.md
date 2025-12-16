# MCP: трекер текущего местоположения по IP

Простой MCP‑сервер `location-tracker-mcp`, который вызывает внешнее API геолокации по IP и возвращает примерное местоположение (город, страна, координаты) на основе публичного IP машины, где запущен агент.

## Установка

```bash
cd mcp/location-tracker
npm install
```

## Запуск MCP‑сервера

```bash
cd mcp/location-tracker
npm start
```

Сервер работает через stdio и совместим с MCP‑клиентами (Claude Desktop, Codex CLI и др.), которые умеют подключать MCP‑серверы.

## Регистрация в MCP‑клиенте (пример)

В вашем MCP‑клиенте нужно добавить конфиг сервера. Пример для JSON‑конфига:

```json
{
  "name": "location-tracker-mcp",
  "command": "node",
  "args": [
    "/ABSOLUTE/PATH/TO/mcp/location-tracker/index.mjs"
  ]
}
```

Либо, если вы установили бинарь глобально (`npm install -g`):

```json
{
  "name": "location-tracker-mcp",
  "command": "location-tracker-mcp",
  "args": []
}
```

После перезапуска клиента агент увидит MCP‑сервер с инструментом:

- `get-current-location` — возвращает текстовый JSON с информацией о текущем местоположении по IP.

## Вызов инструмента агентом

В интерфейсе MCP‑клиента (например, Claude Desktop):

- убедитесь, что сервер `location-tracker-mcp` активен;
- попросите агента что-то вроде:

> Вызови MCP‑инструмент `get-current-location` из сервера `location-tracker-mcp` и покажи результат.

Агент выполнит MCP‑вызов и вернёт ответ, содержащий JSON с полями:

- `ip`
- `city`
- `region`
- `country`
- `latitude`
- `longitude`
- `org`


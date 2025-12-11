# Перевод gemini-client на OpenRouter (google/gemini-2.5-flash)

**Status: DONE**

## Цель

Переписать сервис `gemini-client` так, чтобы он вместо прямого обращения к Gemini использовал OpenRouter API с моделью `google/gemini-2.5-flash`, сохранив текущий функционал очереди, worker’ов и контрактов с backend.

## Что нужно изменить

- Конфигурация и окружение:
  - Добавить настройки для OpenRouter (базовый URL, API‑ключ, модель по умолчанию `google/gemini-2.5-flash`) в конфиг `gemini-client` (`gemini-client/src/config.py`, `hysteria/config.yaml` и/или переменные окружения).
  - Описать стратегию хранения и ротации API‑ключа OpenRouter (env, secrets), не хардкодить ключи в репозитории.
- Клиентский код:
  - Заменить/расширить текущий клиент `GeminiClient` в `gemini-client/src/client/gemini.py`, чтобы он вызывал OpenRouter REST API (включая заголовки авторизации и выбор модели `google/gemini-2.5-flash`).
  - Обновить схемы запросов/ответов (`gemini-client/src/schemas/*.py`), чтобы они соответствовали формату OpenRouter, при этом сохранить внешний контракт для backend (формат сообщений, request_id, метаданные).
  - Переписать обработку ошибок и ретраи (`gemini-client/src/utils/retry.py`, логирование) с учётом возможных кодов ошибок и лимитов OpenRouter (rate limit, 4xx/5xx).
- Worker и очередь:
  - Убедиться, что `gemini-client/src/main.py` и worker (`gemini-client/src/worker/consumer.py`) корректно формируют запросы к OpenRouter и обрабатывают ответы/стриминг (если используется streaming).
  - Сохранить существующий интерфейс взаимодействия с backend (формат сообщений в очереди, идентификаторы запросов, структура ответа), чтобы backend не пришлось менять или изменения были минимальными.
- Документация и запуск:
  - Обновить `gemini-client/README.md` и при необходимости `docker-compose.yml` для описания новых переменных окружения и процесса запуска с OpenRouter.

## Критерии приёмки

- [ ] При запуске стека через Docker `gemini-client` использует OpenRouter с моделью `google/gemini-2.5-flash` (подтверждается по логам и/или тестовым запросам).
- [ ] Формат сообщений между backend и `gemini-client` (request/response) остаётся совместимым с текущим кодом backend либо изменения явно описаны и внесены в схемы.
- [ ] Ошибки OpenRouter (включая rate limit) корректно логируются и обрабатываются (ретраи, понятные сообщения в логах).
- [ ] Все существующие тесты для `gemini-client` (`gemini-client/tests`) проходят, при необходимости добавлены новые тесты для OpenRouter‑интеграции.
- [ ] Документация по конфигурации и запуску `gemini-client` обновлена и отражает использование OpenRouter и модели `google/gemini-2.5-flash`.


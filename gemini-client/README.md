# OpenRouter Client Worker

Universal RabbitMQ worker for OpenRouter API with rate limit handling and Gemini model support.

> **Note**: This worker is part of the Day 1 Chat Application stack.
> Configuration is managed via the root `.env` file and the root `docker-compose.yml`.
> See the [main README](../README.md) for full setup instructions.

## Features

- **OpenRouter integration**: Uses OpenRouter API for accessing Gemini models
- **Rate limit handling**: Automatic cooldown and retry with escalating delays
- **Async architecture**: Built with asyncio and aio-pika for high performance
- **Message queue**: RabbitMQ-based request/response pattern
- **HTTP proxy support**: Optional proxy configuration for API requests
- **Graceful shutdown**: Handles SIGTERM/SIGINT signals properly
- **Horizontal scaling**: Run multiple workers concurrently
- **Legacy support**: Fallback to direct Gemini API if OpenRouter key not configured

## Architecture

```
RabbitMQ Queue (gemini.requests)
          ↓
    OpenRouter Worker
          ↓
    OpenRouter API Client
          ↓
   [Optional Proxy]
          ↓
    OpenRouter (google/gemini-2.5-flash)
          ↓
RabbitMQ Queue (gemini.responses)
```

## Installation

### Using Docker (Recommended)

The worker is started as part of the full stack via the root `docker-compose.yml`:

```bash
# From the root directory
docker-compose up -d gemini-client
```

### Manual Installation

```bash
# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"
```

## Configuration

Configuration is done via the root `.env` file. See the [main README](../README.md) for details.

**Key environment variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `RABBITMQ_URL` | RabbitMQ connection string | - |
| `OPENROUTER_API_KEYS` | OpenRouter API key | - |
| `OPENROUTER_MODEL` | Model to use | `google/gemini-2.5-flash` |
| `KEYS_MAX_PER_MINUTE` | Rate limit per key | `10` |
| `QUEUE_RETRY_DELAYS` | Retry delays (seconds) | `60,600,3600,86400` |

### Getting OpenRouter API Key

1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Go to [API Keys](https://openrouter.ai/keys) section
3. Create a new API key
4. Copy the key (starts with `sk-or-v1-`)
5. Add credits to your account for API usage
6. (Optional) Configure site URL and name for dashboard attribution

## Usage

### Running the Worker

```bash
# As part of full stack (recommended)
cd ..  # go to root directory
docker-compose up -d

# Standalone Python (for development)
python -m src.main
```

### Horizontal Scaling

Scale the worker via Docker Compose:

```bash
docker-compose up -d --scale gemini-client=3
```

## Message Schemas

### Request Message (gemini.requests)

```json
{
  "request_id": "uuid",
  "prompt": "Tell me about Python",
  "model": "gemini-pro",
  "parameters": {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 2048
  },
  "callback_queue": "gemini.responses",
  "timestamp": "2025-01-01T00:00:00Z",
  "retry_count": 0
}
```

### Response Message (gemini.responses)

```json
{
  "request_id": "uuid",
  "status": "success",
  "content": "Python is...",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 150,
    "total_tokens": 160
  },
  "processing_time_ms": 1234.56,
  "model_used": "gemini-pro",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

Error response:

```json
{
  "request_id": "uuid",
  "status": "error",
  "error": "Rate limit exceeded after all retries",
  "processing_time_ms": 5000.0,
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## Rate Limiting

### Key Manager

- Round-robin rotation across all API keys
- Tracks usage per key (requests per minute)
- Automatic cooldown on 429 errors
- Returns `None` when all keys are unavailable

### Retry Strategy

When no keys are available:

1. **Retry 0**: Requeue after 1 minute (60s)
2. **Retry 1**: Requeue after 10 minutes (600s)
3. **Retry 2**: Requeue after 1 hour (3600s)
4. **Retry 3**: Requeue after 24 hours (86400s)
5. **Retry 4**: Send error response

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Logging

Structured logging with request tracking:

```
2025-01-01 00:00:00 - src.main - INFO - OpenRouter Worker setup complete
2025-01-01 00:00:01 - src.worker.consumer - INFO - [uuid] Received request (retry_count=0)
2025-01-01 00:00:02 - src.client.openrouter - INFO - [uuid] Content generated (tokens: 160, time: 1234.56ms)
2025-01-01 00:00:03 - src.worker.publisher - INFO - Published response for request uuid
```

## Troubleshooting

### Authentication errors (401)

Check that your `OPENROUTER_API_KEY` is valid and has sufficient credits:

```
- src.client.openrouter - ERROR - Authentication error: Invalid API key
```

Solution: Verify API key at [OpenRouter Keys](https://openrouter.ai/keys) and ensure account has credits

### Rate limit errors (429)

OpenRouter enforces rate limits based on your account tier:

```
- src.client.openrouter - WARNING - Rate limit hit, will retry with backoff
```

Solution: Wait for cooldown or upgrade your OpenRouter account tier

### Messages stuck in queue

Check worker status and RabbitMQ connection. Ensure worker is running and can connect to RabbitMQ.

### Proxy connection issues

Verify `HTTP_PROXY` configuration and proxy server availability.

### Model not available

Ensure `OPENROUTER_MODEL` is set to a valid model ID (e.g., `google/gemini-2.5-flash`). Check [OpenRouter Models](https://openrouter.ai/models) for available models.

## License

MIT

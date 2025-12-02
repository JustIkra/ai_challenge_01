# Day 1 Chat Application

AI-powered chat application with Gemini integration, featuring multi-key rotation, message queue architecture, and proxy support.

## Architecture Overview

```
User (Browser)
    |
    v
Nginx :80 ──┬──> Frontend (Vue.js :5173)
            |
            └──> Backend (FastAPI :8000)
                    |
                    ├──> PostgreSQL (data persistence)
                    ├──> Redis (caching)
                    └──> RabbitMQ (message queue)
                            |
                            v
                    Gemini Client Worker
                            |
                            ├──> Multi-key rotation
                            ├──> Rate limiting
                            └──> Hysteria2 Proxy
                                    |
                                    v
                            Gemini API (Google)
```

### Components

- **Frontend**: Vue.js 3 + TypeScript + Pinia
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Message Queue**: RabbitMQ 3
- **Worker**: Gemini Client (Python)
- **Proxy**: Hysteria2
- **Reverse Proxy**: Nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Valid Gemini API keys (multiple recommended)
- Hysteria2 proxy credentials (optional, for geo-restricted access)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd "day 1"
```

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Edit `.env` and configure:
```bash
# Required: Add your Gemini API keys
GEMINI_API_KEYS=your_key_1,your_key_2,your_key_3

# Required: Set secure passwords
DB_PASSWORD=your_secure_db_password
RABBITMQ_PASSWORD=your_secure_rabbitmq_password

# Optional: Configure Hysteria2 proxy in hysteria/config.yaml
```

4. Start all services:
```bash
docker-compose up -d
```

5. Check services status:
```bash
docker-compose ps
```

6. View logs:
```bash
docker-compose logs -f
```

### Access Points

- **Frontend**: http://localhost
- **API Health Check**: http://localhost/api/health
- **RabbitMQ Management**: http://localhost:15672 (if exposed)

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEYS` | Comma-separated Gemini API keys | `key1,key2,key3` |
| `DB_PASSWORD` | PostgreSQL password | `secure_password_123` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `secure_password_456` |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | `chatapp` |
| `DATABASE_URL` | Full database connection string | `postgresql://...` |

### Message Queue Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://...` |
| `RABBITMQ_USER` | RabbitMQ username | `rabbitmq` |
| `REQUEST_QUEUE` | Request queue name | `gemini.requests` |
| `RESPONSE_QUEUE` | Response queue name | `gemini.responses` |

### Rate Limiting

| Variable | Description | Default |
|----------|-------------|---------|
| `KEYS_MAX_PER_MINUTE` | Max requests per key per minute | `10` |
| `KEYS_COOLDOWN_SECONDS` | Cooldown after rate limit | `60` |

### Retry Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `QUEUE_RETRY_DELAYS` | Escalating retry delays (seconds) | `60,600,3600,86400` |
| `QUEUE_MAX_RETRIES` | Maximum retry attempts | `4` |

### Proxy Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HTTP_PROXY` | Proxy URL for Gemini API calls | `http://hysteria2:8080` |

## Development

### Local Development (Without Docker)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL=postgresql://chatapp:password@localhost:5432/chatapp
export REDIS_URL=redis://localhost:6379
export RABBITMQ_URL=amqp://rabbitmq:password@localhost:5672

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Gemini Client Worker

```bash
cd gemini-client
python -m venv venv
source venv/bin/activate
pip install -e .

# Set environment variables
export RABBITMQ_URL=amqp://rabbitmq:password@localhost:5672
export GEMINI_API_KEYS=your_keys_here

# Run worker
python -m src.main
```

### Testing

#### Backend Tests
```bash
cd backend
pytest
pytest --cov=app tests/
```

#### Frontend Tests
```bash
cd frontend
npm run test
npm run test:unit
```

## Deployment

### Production Checklist

- [ ] Set secure passwords in `.env`
- [ ] Configure valid Gemini API keys (minimum 3 recommended)
- [ ] Update Hysteria2 proxy credentials in `hysteria/config.yaml`
- [ ] Review rate limiting settings
- [ ] Configure backup strategy for PostgreSQL volumes
- [ ] Set up monitoring and alerting
- [ ] Configure SSL/TLS certificates for Nginx
- [ ] Review CORS settings in backend

### Building Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend
docker-compose build gemini-client
```

### Updating Services

```bash
# Rebuild and restart all services
docker-compose up -d --build

# Restart specific service
docker-compose restart backend
```

## Monitoring

### Health Checks

```bash
# API health endpoint
curl http://localhost/api/health

# Check service status
docker-compose ps

# View service logs
docker-compose logs -f backend
docker-compose logs -f gemini-client
docker-compose logs -f rabbitmq
```

### Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U chatapp -d chatapp

# Check connections
docker-compose exec postgres psql -U chatapp -d chatapp -c "SELECT * FROM pg_stat_activity;"
```

### RabbitMQ

```bash
# List queues
docker-compose exec rabbitmq rabbitmqctl list_queues

# Check connections
docker-compose exec rabbitmq rabbitmqctl list_connections
```

### Redis

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Check keys
docker-compose exec redis redis-cli KEYS '*'
```

## Troubleshooting

### Services Won't Start

**Issue**: Docker Compose fails to start services

**Solutions**:
1. Check if ports 80, 5432, 5672, 6379 are already in use:
   ```bash
   lsof -i :80
   lsof -i :5432
   ```
2. Ensure `.env` file exists and has valid values
3. Check Docker daemon is running
4. Review logs: `docker-compose logs`

### Frontend Not Loading

**Issue**: http://localhost shows connection error

**Solutions**:
1. Check Nginx is running: `docker-compose ps nginx`
2. Verify frontend container is running: `docker-compose ps frontend`
3. Check Nginx logs: `docker-compose logs nginx`
4. Verify Nginx configuration: `docker-compose exec nginx cat /etc/nginx/nginx.conf`

### API Returns 502 Bad Gateway

**Issue**: API requests fail with 502 error

**Solutions**:
1. Check backend is running: `docker-compose ps backend`
2. Check backend logs: `docker-compose logs backend`
3. Verify database connection: `docker-compose logs postgres`
4. Test backend directly: `docker-compose exec backend curl http://localhost:8000/api/health`

### Messages Not Being Processed

**Issue**: Chat messages sent but no response from Gemini

**Solutions**:
1. Check gemini-client logs: `docker-compose logs gemini-client`
2. Verify RabbitMQ is running: `docker-compose ps rabbitmq`
3. Check queue status: `docker-compose exec rabbitmq rabbitmqctl list_queues`
4. Verify API keys are valid in `.env`
5. Check proxy is working: `docker-compose logs hysteria2`

### Database Connection Errors

**Issue**: Backend can't connect to PostgreSQL

**Solutions**:
1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check credentials in `.env` match docker-compose.yml
3. Test connection:
   ```bash
   docker-compose exec postgres psql -U chatapp -d chatapp -c "SELECT 1;"
   ```
4. Check logs: `docker-compose logs postgres`

### Rate Limiting Issues

**Issue**: Gemini API rate limits hit frequently

**Solutions**:
1. Add more API keys to `GEMINI_API_KEYS` in `.env`
2. Increase `KEYS_COOLDOWN_SECONDS`
3. Decrease `KEYS_MAX_PER_MINUTE`
4. Monitor worker logs: `docker-compose logs -f gemini-client`

### Hysteria2 Proxy Issues

**Issue**: Worker can't reach Gemini API through proxy

**Solutions**:
1. Check Hysteria2 logs: `docker-compose logs hysteria2`
2. Verify credentials in `hysteria/config.yaml`
3. Test proxy manually:
   ```bash
   docker-compose exec gemini-client curl -x http://hysteria2:8080 https://generativelanguage.googleapis.com
   ```
4. Temporarily disable proxy by commenting out `HTTP_PROXY` in `.env`

## Data Persistence

All data is persisted in Docker volumes:

- `postgres_data`: Database tables and data
- `redis_data`: Redis cache data
- `rabbitmq_data`: RabbitMQ queue state

### Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U chatapp chatapp > backup.sql

# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U chatapp chatapp
```

### Clear Data (Development Only)

```bash
# WARNING: This will delete all data
docker-compose down -v
```

## Project Structure

```
day 1/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Config & security
│   │   ├── db/             # Database models
│   │   └── services/       # Business logic
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   └── Dockerfile
├── frontend/               # Vue.js frontend
│   ├── src/
│   │   ├── components/     # Vue components
│   │   ├── stores/         # Pinia stores
│   │   ├── views/          # Page views
│   │   └── api/            # API client
│   └── Dockerfile
├── gemini-client/          # Gemini API worker
│   ├── src/
│   │   ├── api/            # Gemini API client
│   │   ├── queue/          # RabbitMQ handlers
│   │   └── rate_limiter/   # Multi-key rotation
│   └── Dockerfile
├── nginx/                  # Nginx configuration
│   └── nginx.conf
├── hysteria/               # Hysteria2 proxy config
│   └── config.yaml
├── .memory-base/           # Development docs
├── docker-compose.yml      # Service orchestration
├── .env.example           # Environment template
└── README.md              # This file
```

## API Documentation

### Health Check

```http
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-01T00:00:00Z"
}
```

### Create Chat

```http
POST /api/chats
Content-Type: application/json

{
  "title": "My Chat"
}
```

### Send Message

```http
POST /api/chats/{chat_id}/messages
Content-Type: application/json

{
  "content": "Hello, how are you?",
  "role": "user"
}
```

### Get Chat Messages

```http
GET /api/chats/{chat_id}/messages
```

For complete API documentation, visit http://localhost/api/docs when the services are running.

## Contributing

1. Create feature branch from `main`
2. Make changes with tests
3. Run tests locally
4. Submit pull request with description

## License

[Specify your license]

## Support

For issues and questions:
- Check troubleshooting section above
- Review logs: `docker-compose logs`
- Check `.memory-base/technical-docs/` for detailed documentation

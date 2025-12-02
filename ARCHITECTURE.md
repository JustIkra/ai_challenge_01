# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
│                      http://localhost                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Nginx :80                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  /       → frontend:5173 (Vue.js SPA)                      │ │
│  │  /api/*  → backend:8000  (FastAPI)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────┬────────────────────────┬──────────────────────┘
                 │                        │
        ┌────────▼─────────┐     ┌───────▼────────┐
        │   Frontend       │     │    Backend     │
        │   (Vue.js)       │     │   (FastAPI)    │
        │   - TypeScript   │     │   - SQLAlchemy │
        │   - Pinia        │     │   - Alembic    │
        │   - Tailwind     │     │   - Pydantic   │
        └──────────────────┘     └────────┬───────┘
                                          │
                 ┌────────────────────────┼────────────────────────┐
                 │                        │                        │
        ┌────────▼─────────┐   ┌─────────▼──────┐   ┌───────────▼──────┐
        │   PostgreSQL     │   │     Redis      │   │    RabbitMQ      │
        │   - chatapp DB   │   │   - Cache      │   │  - Request Queue │
        │   - Users        │   │   - Sessions   │   │  - Response Queue│
        │   - Chats        │   │                │   │                  │
        │   - Messages     │   │                │   │                  │
        │   - Templates    │   │                │   │                  │
        └──────────────────┘   └────────────────┘   └──────┬───────────┘
                                                             │
                                                    ┌────────▼──────────┐
                                                    │  Gemini Client    │
                                                    │    (Worker)       │
                                                    │  - Multi-key      │
                                                    │  - Rate limiter   │
                                                    │  - Retry logic    │
                                                    └────────┬──────────┘
                                                             │
                                                    ┌────────▼──────────┐
                                                    │  Hysteria2 Proxy  │
                                                    │   :8080           │
                                                    └────────┬──────────┘
                                                             │
                                                             ▼
                                                    ┌──────────────────┐
                                                    │   Gemini API     │
                                                    │  (Google Cloud)  │
                                                    └──────────────────┘
```

## Component Details

### 1. Frontend Layer

**Technology**: Vue.js 3 + TypeScript + Vite

**Responsibilities**:
- User interface rendering
- State management (Pinia)
- API communication
- Real-time updates

**Port**: 5173 (internal), exposed via Nginx

**Key Features**:
- Chat interface
- Message history
- Prompt template selection
- Real-time response display

### 2. Backend Layer

**Technology**: FastAPI + SQLAlchemy + PostgreSQL

**Responsibilities**:
- REST API endpoints
- Business logic
- Database operations
- Message queue publishing/consuming
- Authentication (future)

**Port**: 8000 (internal), exposed via Nginx at /api

**Key Endpoints**:
- `GET /api/health` - Health check
- `POST /api/chats` - Create chat
- `POST /api/chats/{id}/messages` - Send message
- `GET /api/chats/{id}/messages` - Get messages
- `POST /api/prompts` - Create prompt template

### 3. Database Layer

#### PostgreSQL 16

**Responsibilities**:
- Persistent data storage
- ACID transactions
- Relational integrity

**Tables**:
- `users` - User accounts
- `chats` - Chat sessions
- `messages` - Chat messages (user + assistant)
- `prompt_templates` - Reusable prompts

**Volume**: `postgres_data`

#### Redis 7

**Responsibilities**:
- Session storage (future)
- Caching
- Rate limiting counters

**Volume**: `redis_data`

### 4. Message Queue Layer

**Technology**: RabbitMQ 3

**Responsibilities**:
- Asynchronous message processing
- Request/response queues
- Dead letter queue
- Message retry handling

**Queues**:
- `gemini.requests` - User messages to process
- `gemini.responses` - AI responses from Gemini
- `gemini.requests.dlq` - Failed messages

**Volume**: `rabbitmq_data`

### 5. Worker Layer

**Technology**: Python 3.11 + Gemini SDK

**Responsibilities**:
- Consume messages from queue
- Multi-key rotation
- Rate limiting per key
- API calls to Gemini
- Retry with exponential backoff
- Response publishing

**Key Features**:
- **Multi-key rotation**: Round-robin through multiple API keys
- **Rate limiting**: Track usage per key (10 req/min default)
- **Cooldown**: Automatic key cooldown on rate limit
- **Retry logic**: Escalating delays (1min → 10min → 1hr → 1day)
- **Proxy support**: Routes through Hysteria2

### 6. Proxy Layer

**Technology**: Hysteria2

**Responsibilities**:
- HTTP/HTTPS proxy
- Geographic restriction bypass
- TLS termination

**Port**: 8080 (internal)

**Configuration**: `hysteria/config.yaml`

### 7. Reverse Proxy Layer

**Technology**: Nginx Alpine

**Responsibilities**:
- HTTP routing
- Static file serving (future)
- Load balancing (future)
- SSL/TLS termination (future)

**Port**: 80 (public)

**Routes**:
- `/` → `frontend:5173`
- `/api/*` → `backend:8000`

## Data Flow

### Chat Message Flow

```
1. User types message in UI
   ↓
2. Frontend: POST /api/chats/{id}/messages
   ↓
3. Backend: Save message to PostgreSQL (role: user)
   ↓
4. Backend: Publish to RabbitMQ (gemini.requests)
   ↓
5. Backend: Return 201 Created to frontend
   ↓
6. Worker: Consume message from queue
   ↓
7. Worker: Select available API key (round-robin)
   ↓
8. Worker: Check rate limit for selected key
   ↓
9. Worker: HTTP POST via Hysteria2 proxy
   ↓
10. Gemini API: Process and return response
    ↓
11. Worker: Publish response to RabbitMQ (gemini.responses)
    ↓
12. Backend: Consume response from queue
    ↓
13. Backend: Save message to PostgreSQL (role: assistant)
    ↓
14. Frontend: Poll GET /api/chats/{id}/messages
    ↓
15. Frontend: Display AI response to user
```

### Error Flow

```
API Call Fails
   ↓
Worker: Check retry count < max_retries
   ↓
Worker: Requeue with delay (exponential backoff)
   ↓
Wait: 1min → 10min → 1hr → 1day
   ↓
Retry API call
   ↓
If still fails after max_retries → Dead Letter Queue
```

## Rate Limiting Strategy

### Per-Key Tracking

```python
key_state = {
    "key1": {
        "requests": [],  # Timestamps of requests
        "cooldown_until": None
    },
    "key2": {...},
    "key3": {...}
}
```

### Algorithm

1. Filter keys not in cooldown
2. Remove timestamps older than 60 seconds
3. Find key with least requests
4. If requests < max_per_minute:
   - Use this key
   - Add timestamp
5. Else:
   - Put key in cooldown
   - Try next key

## Scalability Considerations

### Horizontal Scaling

**Can Scale**:
- Frontend (stateless)
- Backend (mostly stateless)
- Gemini Client Workers (fully stateless)
- Redis (cluster mode)
- RabbitMQ (cluster mode)

**Cannot Scale Easily**:
- PostgreSQL (primary-replica setup possible)
- Nginx (can add load balancer)

### Resource Requirements

**Minimum** (Development):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB

**Recommended** (Production):
- CPU: 8 cores
- RAM: 16 GB
- Disk: 100 GB SSD

## Security Layers

### Current

1. **Network Isolation**: Docker internal network
2. **Environment Variables**: Secrets not in code
3. **Database**: Password authentication
4. **RabbitMQ**: Username/password auth

### Future

1. **HTTPS**: SSL/TLS certificates
2. **API Authentication**: JWT tokens
3. **Rate Limiting**: Per-user API limits
4. **Input Validation**: XSS prevention
5. **SQL Injection**: Parameterized queries (already using)
6. **CORS**: Configured origins

## Monitoring Points

### Health Checks

1. **Backend**: `GET /api/health`
2. **PostgreSQL**: Connection test
3. **Redis**: PING command
4. **RabbitMQ**: Queue status
5. **Worker**: Heartbeat messages

### Metrics to Monitor

1. **Request Rate**: Requests per second
2. **Response Time**: API latency
3. **Queue Depth**: Message backlog
4. **Error Rate**: Failed requests
5. **Database Connections**: Connection pool usage
6. **Memory Usage**: Per container
7. **CPU Usage**: Per container
8. **Disk Usage**: Volume sizes

### Log Aggregation

**Current**: Docker logs
```bash
docker-compose logs -f
```

**Future**: ELK Stack or similar
- Elasticsearch: Log storage
- Logstash: Log processing
- Kibana: Log visualization

## Deployment Topology

### Development

```
Single Host (Docker Compose)
  └─ All services in containers
```

### Production (Future)

```
Load Balancer
  ├─ Nginx 1
  └─ Nginx 2
      ├─ Backend 1
      ├─ Backend 2
      └─ Backend 3
          ├─ PostgreSQL Primary
          │   └─ Replicas
          ├─ Redis Cluster
          ├─ RabbitMQ Cluster
          └─ Worker Pool (N instances)
              └─ Hysteria2 Proxy
```

## Technology Stack Summary

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Vue.js | 3.x |
| Frontend Build | Vite | 5.x |
| Frontend Lang | TypeScript | 5.x |
| Frontend State | Pinia | 2.x |
| Backend | FastAPI | 0.109+ |
| Backend ORM | SQLAlchemy | 2.x |
| Backend Migration | Alembic | 1.x |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Queue | RabbitMQ | 3 |
| Worker | Python | 3.11 |
| AI | Gemini API | 1.5 |
| Proxy | Hysteria2 | Latest |
| Reverse Proxy | Nginx | Alpine |
| Container | Docker | 24+ |
| Orchestration | Docker Compose | 2.x |

## Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service orchestration |
| `.env` | Environment variables |
| `nginx/nginx.conf` | Nginx routing |
| `hysteria/config.yaml` | Proxy configuration |
| `backend/alembic.ini` | Database migrations |
| `frontend/vite.config.ts` | Build configuration |
| `gemini-client/pyproject.toml` | Worker dependencies |

## Port Mapping

| Service | Internal Port | External Port | Access |
|---------|---------------|---------------|--------|
| Nginx | 80 | 80 | Public |
| Frontend | 5173 | - | Via Nginx |
| Backend | 8000 | - | Via Nginx |
| PostgreSQL | 5432 | - | Internal |
| Redis | 6379 | - | Internal |
| RabbitMQ | 5672 | - | Internal |
| RabbitMQ Mgmt | 15672 | - | Internal |
| Hysteria2 | 8080 | - | Internal |

## Volume Mapping

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Database files |
| `redis_data` | `/data` | Cache data |
| `rabbitmq_data` | `/var/lib/rabbitmq` | Queue state |
| `./nginx/nginx.conf` | `/etc/nginx/nginx.conf` | Nginx config |
| `./hysteria/config.yaml` | `/etc/hysteria/config.yaml` | Proxy config |

## API Key Rotation Example

```
Request 1: key_1 (0 requests) → Selected
Request 2: key_2 (0 requests) → Selected
Request 3: key_3 (0 requests) → Selected
Request 4: key_1 (1 request)  → Selected
...
Request 30: key_3 (9 requests) → Selected
Request 31: key_1 (10 requests, RATE LIMITED)
           key_2 (10 requests, RATE LIMITED)
           key_3 (10 requests, RATE LIMITED)
           → Wait for cooldown

After 60 seconds: All keys reset
Request 32: key_1 (0 requests) → Selected
```

## Future Enhancements

### Phase 1 (Short-term)
- User authentication & authorization
- WebSocket for real-time updates
- Message editing & deletion
- Chat export functionality

### Phase 2 (Medium-term)
- Multi-model support (OpenAI, Anthropic, etc.)
- File upload & image analysis
- Voice input/output
- Shared chats

### Phase 3 (Long-term)
- Multi-tenant architecture
- Advanced analytics
- Custom model fine-tuning
- Plugin system

# Deployment Guide

## Pre-Deployment Checklist

### 1. Environment Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Set secure `DB_PASSWORD` (minimum 16 characters)
- [ ] Set secure `RABBITMQ_PASSWORD` (minimum 16 characters)
- [ ] Configure at least 3 valid `GEMINI_API_KEYS` (comma-separated)
- [ ] Review rate limiting settings (`KEYS_MAX_PER_MINUTE`, `KEYS_COOLDOWN_SECONDS`)
- [ ] Verify `HTTP_PROXY` setting matches Hysteria2 configuration

### 2. Proxy Configuration

- [ ] Update `hysteria/config.yaml` with valid server credentials
- [ ] Test proxy connectivity manually if possible
- [ ] Ensure proxy server allows Google API access

### 3. Docker Images

- [ ] Verify all Dockerfiles are present:
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
  - `gemini-client/Dockerfile`
- [ ] Ensure build contexts are correct in `docker-compose.yml`

### 4. Network Configuration

- [ ] Ensure port 80 is available for Nginx
- [ ] Verify no conflicts with PostgreSQL port 5432
- [ ] Check RabbitMQ port 5672 is free
- [ ] Confirm Redis port 6379 is available

### 5. Volume Persistence

- [ ] Confirm volumes are defined in `docker-compose.yml`:
  - `postgres_data`
  - `redis_data`
  - `rabbitmq_data`
- [ ] Plan backup strategy for database volume

## Deployment Steps

### Initial Deployment

1. **Clone and Navigate to Project**
```bash
git clone <repository-url>
cd "day 1"
```

2. **Configure Environment**
```bash
cp .env.example .env
nano .env  # or vim, code, etc.
```

3. **Build All Images**
```bash
docker-compose build
```

4. **Start Services**
```bash
docker-compose up -d
```

5. **Verify Services Started**
```bash
docker-compose ps
```

Expected output: All services should show "Up" status

6. **Check Logs for Errors**
```bash
docker-compose logs
```

Look for:
- Database initialization completed
- RabbitMQ ready
- Backend started successfully
- Frontend compiled
- Gemini client connected to RabbitMQ

### Post-Deployment Verification

#### 1. Infrastructure Health

**PostgreSQL**
```bash
docker-compose exec postgres psql -U chatapp -d chatapp -c "SELECT 1;"
```
Expected: `1` returned

**Redis**
```bash
docker-compose exec redis redis-cli PING
```
Expected: `PONG`

**RabbitMQ**
```bash
docker-compose exec rabbitmq rabbitmqctl status
```
Expected: RabbitMQ status displayed without errors

#### 2. Application Health

**Backend API**
```bash
curl http://localhost/api/health
```
Expected:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-01T..."
}
```

**Frontend**
```bash
curl -I http://localhost
```
Expected: `200 OK` status

#### 3. End-to-End Testing

**Test 1: Create Chat**
```bash
curl -X POST http://localhost/api/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'
```
Expected: Chat created with ID returned

**Test 2: Send Message**
```bash
# Replace {chat_id} with actual ID from previous step
curl -X POST http://localhost/api/chats/{chat_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello", "role": "user"}'
```
Expected: Message created

**Test 3: Check Message Queue**
```bash
docker-compose exec rabbitmq rabbitmqctl list_queues
```
Expected: `gemini.requests` queue should have messages or show activity

**Test 4: Verify Gemini Client Processing**
```bash
docker-compose logs -f gemini-client
```
Expected: Log entries showing message processing

#### 4. UI Testing

1. Open http://localhost in browser
2. Create new chat via UI
3. Send a message
4. Verify message appears in chat history
5. Wait for Gemini response (may take 10-60 seconds)
6. Verify response appears in chat

#### 5. Prompt Templates Testing

**Test different templates:**
1. Open chat settings
2. Select "Creative Writing" template
3. Send test message
4. Verify response style matches template
5. Repeat with other templates

## Monitoring

### Continuous Monitoring Commands

**View all logs in real-time**
```bash
docker-compose logs -f
```

**Monitor specific service**
```bash
docker-compose logs -f backend
docker-compose logs -f gemini-client
docker-compose logs -f rabbitmq
```

**Check resource usage**
```bash
docker stats
```

**Monitor queue depth**
```bash
watch -n 5 'docker-compose exec rabbitmq rabbitmqctl list_queues'
```

### Key Metrics to Monitor

1. **RabbitMQ Queue Depth**
   - Request queue should not grow indefinitely
   - Response queue should process quickly

2. **Database Connections**
   - Should remain stable
   - Check for connection leaks

3. **Memory Usage**
   - Backend: Should be under 512MB
   - Frontend: Should be under 256MB
   - Gemini Client: Should be under 512MB

4. **Error Logs**
   - Watch for repeated errors
   - Monitor rate limit errors from Gemini API

## Troubleshooting Deployment

### Issue: Services fail to start

**Diagnosis:**
```bash
docker-compose logs
docker-compose ps
```

**Common causes:**
1. Port conflicts - Check with `lsof -i :80`
2. Invalid `.env` configuration
3. Docker daemon not running
4. Insufficient disk space

**Solution:**
```bash
# Stop all services
docker-compose down

# Remove old containers
docker-compose rm -f

# Rebuild and start
docker-compose up -d --build
```

### Issue: Backend can't connect to database

**Diagnosis:**
```bash
docker-compose logs backend
docker-compose logs postgres
```

**Solution:**
```bash
# Check database is running
docker-compose ps postgres

# Verify credentials in .env
cat .env | grep DB_

# Restart backend
docker-compose restart backend
```

### Issue: Gemini client not processing messages

**Diagnosis:**
```bash
docker-compose logs gemini-client
docker-compose exec rabbitmq rabbitmqctl list_queues
```

**Common causes:**
1. Invalid API keys
2. Rate limiting
3. Proxy not working
4. RabbitMQ connection issues

**Solution:**
```bash
# Verify API keys in .env
cat .env | grep GEMINI_API_KEYS

# Check proxy logs
docker-compose logs hysteria2

# Restart gemini client
docker-compose restart gemini-client
```

### Issue: Frontend not loading

**Diagnosis:**
```bash
docker-compose logs nginx
docker-compose logs frontend
```

**Solution:**
```bash
# Check Nginx configuration
docker-compose exec nginx cat /etc/nginx/nginx.conf

# Restart frontend and nginx
docker-compose restart frontend nginx
```

## Updating Deployment

### Update Application Code

```bash
# Pull latest changes
git pull

# Rebuild affected services
docker-compose build backend frontend

# Restart services
docker-compose up -d backend frontend
```

### Update Environment Variables

```bash
# Edit .env
nano .env

# Restart affected services
docker-compose restart backend gemini-client
```

### Update Dependencies

**Backend:**
```bash
# Update pyproject.toml
cd backend
# Edit dependencies

# Rebuild
docker-compose build backend
docker-compose up -d backend
```

**Frontend:**
```bash
# Update package.json
cd frontend
# Edit dependencies

# Rebuild
docker-compose build frontend
docker-compose up -d frontend
```

## Backup and Restore

### Backup Database

```bash
# Create backup
docker-compose exec postgres pg_dump -U chatapp chatapp > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_*.sql
```

### Restore Database

```bash
# Stop backend to prevent writes
docker-compose stop backend gemini-client

# Restore from backup
gunzip -c backup_20250101_120000.sql.gz | \
  docker-compose exec -T postgres psql -U chatapp chatapp

# Restart services
docker-compose start backend gemini-client
```

### Backup Volumes

```bash
# Create volume backup
docker run --rm \
  -v day1_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_volume_backup.tar.gz -C /data .
```

## Rollback Procedure

### Rollback to Previous Version

```bash
# Stop services
docker-compose down

# Checkout previous version
git checkout <previous-commit-hash>

# Rebuild and start
docker-compose build
docker-compose up -d

# Verify
curl http://localhost/api/health
```

### Rollback Database

```bash
# Stop services
docker-compose stop backend gemini-client

# Restore database backup
gunzip -c backup_previous.sql.gz | \
  docker-compose exec -T postgres psql -U chatapp chatapp

# Restart services
docker-compose start backend gemini-client
```

## Production Hardening

### Security

1. **Change default passwords**
   - Set strong DB_PASSWORD
   - Set strong RABBITMQ_PASSWORD

2. **Network security**
   - Don't expose database ports externally
   - Use firewall rules
   - Consider using Docker networks

3. **API keys**
   - Store in secure secrets management
   - Rotate regularly
   - Use multiple keys for redundancy

4. **SSL/TLS**
   - Configure SSL certificates in Nginx
   - Use Let's Encrypt for free certificates
   - Force HTTPS redirect

### Performance

1. **Database**
   - Configure connection pooling
   - Monitor query performance
   - Set up regular VACUUM operations

2. **Redis**
   - Configure memory limits
   - Set eviction policy
   - Monitor cache hit rates

3. **RabbitMQ**
   - Configure memory limits
   - Set prefetch count
   - Monitor queue depth

4. **Application**
   - Set worker counts appropriately
   - Configure request timeouts
   - Enable response compression

## Maintenance

### Regular Tasks

**Daily:**
- Check service logs for errors
- Monitor queue depths
- Review resource usage

**Weekly:**
- Backup database
- Review disk space usage
- Check for dependency updates

**Monthly:**
- Rotate logs
- Update security patches
- Review and optimize queries

### Cleanup Commands

```bash
# Remove old logs
docker-compose logs --tail=0 > /dev/null

# Remove unused images
docker image prune -a

# Remove unused volumes (CAUTION)
docker volume prune
```

## Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Consult README.md troubleshooting section
4. Check `.memory-base/technical-docs/` for detailed documentation

# AuraFit — Troubleshooting Guide

---

## Service Won't Start

### Port already in use
```bash
# Find and kill the process using the port
lsof -i :8001 | grep LISTEN
kill -9 <PID>

# Or change the port in docker-compose.yml
```

### Container exits immediately
```bash
# Check exit logs
docker compose logs user-service --tail=50

# Common causes:
# 1. Missing .env file
# 2. DATABASE_URL unreachable
# 3. Missing JWT keys
```

### Database connection refused
```bash
# Ensure postgres is healthy
docker compose ps postgres
docker compose logs postgres --tail=20

# Reset postgres
docker compose rm -f postgres
docker compose up -d postgres
sleep 5
make migrate
```

---

## Authentication Issues

### "JWT signature invalid"
- Ensure `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` in `.env` are the matching pair
- Check for extra whitespace or missing `\n` newlines in the key strings
- Regenerate: `ssh-keygen -t rsa -b 4096 -m PEM -f keys/jwt.pem -N ""`

### "Token expired" immediately after login
- Check server clock (`date`) vs expected time
- `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 15 — increase for development

### Google OAuth "redirect_uri_mismatch"
- In Google Cloud Console, add `http://localhost:3000/auth/callback` to allowed redirect URIs
- Ensure `GOOGLE_REDIRECT_URI` in `.env` matches exactly

---

## AI Services

### MediaPipe fails to load
```bash
# Check for missing libGL
docker compose exec facial-analysis python -c "import mediapipe"
# If ImportError: ensure libgl1-mesa-glx is in Dockerfile
```

### CLIP model download stuck
```bash
# Pre-download outside Docker
python -c "from transformers import CLIPModel; CLIPModel.from_pretrained('openai/clip-vit-base-patch32')"

# Or set offline mode after first download
TRANSFORMERS_OFFLINE=1 docker compose up virtual-tryon
```

### Facial analysis returns "no face detected"
- Ensure image is JPEG/PNG (not HEIC)
- Minimum face size: 100×100px
- Good lighting required
- Face must be mostly frontal (< 30° rotation)

### Makeup AR not rendering
- Browser MediaPipe requires HTTPS in production (or `localhost`)
- Chrome requires camera permission: check site settings
- Use "Photo" mode as fallback (server-side rendering)

---

## Database

### pgvector extension missing
```bash
docker compose exec postgres psql -U aurafit -c \
  "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS uuid-ossp;"
```

### Migration conflict / "already applied"
```bash
docker compose exec user-service alembic stamp head    # Mark all as applied
docker compose exec user-service alembic current       # Check current state
```

### Slow queries
```bash
# Enable query logging in .env
DATABASE_ECHO=true

# Enable pg_stat_statements
docker compose exec postgres psql -U aurafit -c \
  "CREATE EXTENSION pg_stat_statements; SELECT * FROM pg_stat_statements LIMIT 10;"
```

---

## Redis

### Connection refused
```bash
docker compose ps redis
docker compose restart redis
redis-cli -h localhost ping    # Should return PONG
```

### Memory full (OOM)
```bash
# Check current memory
redis-cli -h localhost info memory

# Force eviction (configured as allkeys-lru in docker-compose.yml)
# Or increase maxmemory in redis command
```

### Celery tasks not running
```bash
# Check worker is alive
docker compose ps celery-default-worker
docker compose logs celery-default-worker --tail=30

# Check queue depth
redis-cli -h localhost llen celery

# Force restart
docker compose restart celery-default-worker
```

---

## Frontend

### "Cannot GET /dashboard/style-dna"
- Ensure all Next.js pages are present in `apps/web/src/app/dashboard/`
- Run `npm run build` and check for build errors

### API calls return 401 in browser
- Check `NEXT_PUBLIC_API_URL` in `.env.local` matches the running backend
- Clear browser local storage (Zustand auth store)
- Re-login to get fresh tokens

### "Module not found" TypeScript errors
```bash
cd apps/web
npm install           # Ensure all deps installed
npm run typecheck     # See full error list
```

### Hydration mismatch errors
- Components marked `"use client"` that access `window`/`document` — wrap in `useEffect`
- Date formatting — always use consistent locale: `new Date().toLocaleDateString('en-IN')`

---

## Performance

### Slow API response (> 500ms)
```bash
# Check Redis cache hit rate
redis-cli -h localhost info stats | grep keyspace_hits

# Check DB query time
# Enable slow query log in PostgreSQL:
docker compose exec postgres psql -U aurafit -c \
  "ALTER SYSTEM SET log_min_duration_statement = 500;"
docker compose exec postgres psql -U aurafit -c "SELECT pg_reload_conf();"
```

### High Celery queue backlog
```bash
# Scale workers
docker compose scale celery-ai-worker=4

# Purge stuck tasks (warning: loses tasks)
docker compose exec user-service celery -A app.tasks.celery_app purge
```

### Memory leak in AI service
```bash
# Check container memory
docker stats --no-stream

# CLIP/MediaPipe models are large (~500MB each)
# If OOM: increase container memory limit in docker-compose.yml
```

---

## Logs Reference

| Log field | Meaning |
|---|---|
| `"event"` | Structured log event name (e.g. `"auth.login.success"`) |
| `"user_id"` | User UUID |
| `"ms"` | Processing time in milliseconds |
| `"error"` | Exception message |
| `"status"` | HTTP status code |

```bash
# Filter logs by event
docker compose logs user-service 2>&1 | grep '"event":"auth'

# Filter errors only
docker compose logs user-service 2>&1 | grep '"level":"error"'

# Follow real-time
docker compose logs -f user-service | python3 -m json.tool
```

---

## Getting Help

1. Check this guide first
2. Search existing GitHub Issues
3. Run `make health-check` and include output
4. Include relevant logs from `docker compose logs <service> --tail=100`
5. Open a GitHub Issue with reproduction steps

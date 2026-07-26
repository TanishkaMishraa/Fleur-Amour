# AuraFit — Development Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker | 24+ | Service containers |
| Docker Compose | v2 (built into Docker) | Multi-service orchestration |
| Node.js | 20+ | Frontend development |
| Python | 3.11+ | Backend development |
| Make | Any | Developer shortcuts |

---

## First-Time Setup

```bash
# 1. Clone
git clone https://github.com/your-org/aurafit.git
cd aurafit

# 2. Generate RSA keys for JWT
mkdir -p services/user-service/keys
ssh-keygen -t rsa -b 4096 -m PEM \
  -f services/user-service/keys/jwt_private.pem -N ""
openssl rsa \
  -in  services/user-service/keys/jwt_private.pem \
  -pubout \
  -out services/user-service/keys/jwt_public.pem

# 3. Copy env files
cp services/user-service/.env.example services/user-service/.env
cp apps/web/.env.local.example apps/web/.env.local

# 4. Start infrastructure + services
make up   # or: docker compose up -d

# 5. Wait for health (30s for AI models to load)
make health-check   # or: docker compose ps

# 6. Apply migrations
make migrate   # or: docker compose exec user-service alembic upgrade head

# 7. (Optional) Seed test data
docker compose exec user-service python -m app.scripts.seed_data
```

---

## Daily Development

### Start / stop

```bash
make up       # Start all services detached
make down     # Stop and remove containers
make logs     # Tail user-service logs
make logs SERVICE=recommendation-service   # Tail specific service
```

### Frontend development (hot reload)

```bash
cd apps/web
npm install
npm run dev     # http://localhost:3000
```

### Backend shell

```bash
make shell-api        # bash in user-service
make shell-db         # psql in postgres
```

### Useful development commands

```bash
# Rebuild after code change
make build SERVICE=user-service

# Reset DB completely
docker compose down -v && make up && make migrate

# View Celery tasks
open http://localhost:5555   # Flower dashboard

# View DB
open http://localhost:5050   # pgAdmin (admin@aurafit.ai / admin)
```

---

## Code Organisation

### Backend conventions

**File naming:** `snake_case.py`
**Class naming:** `PascalCase`
**API handler naming:** `snake_case` (FastAPI auto-generates OpenAPI names)

**Layer responsibilities:**
```
endpoint.py   → HTTP only: validate request, call service, return response
service.py    → Business logic: orchestration, rules, caching
repository.py → DB only: queries, no business logic
model.py      → ORM: table definition only, no methods
schema.py     → Pydantic: request/response contracts only
```

**Error handling:**
- Raise `NotFoundError`, `PermissionDeniedError`, `ValidationError` from `app.core.errors`
- Endpoints catch and translate to `HTTPException`
- Never let raw `Exception` propagate to client

**Logging:**
```python
from app.core.logging import get_logger
logger = get_logger(__name__)
logger.info("action.verb", key=value)  # Always structured
```

**Caching:**
```python
from app.cache.redis_client import cache_get, cache_set, cache_delete

# Read-through cache pattern
cached = await cache_get(key)
if cached:
    return json.loads(cached)
data = await fetch_from_db()
await cache_set(key, json.dumps(data), ttl=3600)
```

### Frontend conventions

**File naming:** `PascalCase.tsx` for components, `camelCase.ts` for utilities
**Import order:** React → Next → Third-party → Internal (@/...) → Relative

**Component structure:**
```typescript
"use client";  // Only when using hooks/browser APIs

// Imports
import { ... } from "..."

// Types
interface Props { ... }

// Component
export function MyComponent({ prop }: Props) {
  // 1. Hooks
  // 2. Derived state
  // 3. Handlers
  // 4. Render
}
```

**Data fetching:** Always via React Query (`useQuery`, `useMutation`). Never raw `useEffect + fetch`.

**State management:** Zustand stores for auth and UI only. Server state belongs in React Query cache.

---

## Testing

### Run all tests

```bash
make test              # Backend unit + integration tests
make test-frontend     # Frontend component tests
make test-e2e          # E2E tests (requires running stack)
```

### Backend tests (pytest)

```bash
# Unit tests (no DB required)
docker compose exec user-service pytest tests/unit/ -v

# Integration tests (uses test DB)
docker compose exec user-service pytest tests/integration/ -v

# With coverage
docker compose exec user-service pytest --cov=app --cov-report=html
```

### Writing tests

```python
# tests/unit/test_color_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.color_service import ColorService

@pytest.mark.asyncio
async def test_compute_profile_no_scan():
    session = AsyncMock()
    svc = ColorService(session)
    # Mock repository to return None
    with pytest.raises(NotFoundError):
        await svc.compute_and_persist(user_id=uuid4())
```

### Frontend tests

```bash
cd apps/web
npm test              # Jest + Testing Library
npm run test:watch    # Watch mode
npm run test:coverage # Coverage report
```

### E2E tests (Playwright)

```bash
cd apps/web
npx playwright test          # All E2E tests
npx playwright test --ui     # Visual test runner
npx playwright codegen http://localhost:3000  # Record new test
```

---

## Linting & Formatting

```bash
# Python (backend)
ruff check services/user-service/app     # Lint
ruff format services/user-service/app    # Format
mypy services/user-service/app --ignore-missing-imports  # Types

# TypeScript (frontend)
cd apps/web
npm run lint       # ESLint
npm run typecheck  # tsc --noEmit
npm run format     # Prettier
```

CI enforces zero lint errors. Configure your editor:
- **VS Code**: Install `ruff`, `Pylance`, `ESLint`, `Prettier` extensions
- **PyCharm**: Enable ruff as formatter in Settings → Editor → Code Style → Python

---

## Database Migrations

```bash
# Create a new migration
make migrate-create MSG="add product tags column"

# Apply
make migrate

# Rollback one
make migrate-downgrade

# Show history
make migrate-history
```

**Rules:**
- Never edit existing migration files (they're immutable after merge)
- Always test `upgrade` AND `downgrade` paths
- Add `CREATE INDEX CONCURRENTLY` for large-table indexes (use `op.execute()` not `op.create_index()`)

---

## Adding a New Feature

1. **Model** — Add ORM model in `app/models/`; add to `__init__.py`
2. **Migration** — `make migrate-create MSG="description"`
3. **Schema** — Pydantic request/response in `app/schemas/`
4. **Repository** — DB queries in `app/repositories/`
5. **Service** — Business logic in `app/services/`
6. **Endpoint** — HTTP handler in `app/api/v1/endpoints/`
7. **Router** — Register in `app/api/v1/router.py`
8. **Tests** — Unit test service; integration test endpoint
9. **Frontend** — API client → hook → component → page

---

## Environment Variables

See [ENVIRONMENT.md](./ENVIRONMENT.md) for the complete reference.

**Never hardcode secrets.** Use:
- `get_settings()` (cached via `lru_cache`) — access any setting in Python
- `process.env.NEXT_PUBLIC_*` — only for non-secret browser values
- Docker Compose `environment:` key — inject from `.env` file

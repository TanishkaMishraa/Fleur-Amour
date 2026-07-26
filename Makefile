# AuraFit Monorepo — Developer Makefile
# Run targets from the repo root.

.PHONY: help up down build logs shell-api shell-db \
        migrate migrate-create test test-cov lint typecheck \
        celery-worker celery-flower clean

SERVICE ?= user-service
COMPOSE  = docker compose
PY       = docker compose exec $(SERVICE) python
ALEMBIC  = docker compose exec $(SERVICE) alembic

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────────────────────────

up: ## Start full stack (detached)
	$(COMPOSE) up -d

down: ## Stop all containers
	$(COMPOSE) down

build: ## Build all service images
	$(COMPOSE) build

logs: ## Tail logs for SERVICE (default: user-service)
	$(COMPOSE) logs -f $(SERVICE)

shell-api: ## Open bash in user-service container
	$(COMPOSE) exec $(SERVICE) bash

shell-db: ## Open psql in postgres container
	$(COMPOSE) exec postgres psql -U aurafit aurafit

# ── Database migrations ───────────────────────────────────────────────────────

migrate: ## Apply all pending Alembic migrations
	$(ALEMBIC) upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="add column x")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose

migrate-downgrade: ## Downgrade one revision
	$(ALEMBIC) downgrade -1

# ── Testing ───────────────────────────────────────────────────────────────────

test: ## Run all tests (unit + integration)
	$(COMPOSE) exec $(SERVICE) pytest app/tests/ -v

test-unit: ## Run unit tests only
	$(COMPOSE) exec $(SERVICE) pytest app/tests/unit/ -v

test-integration: ## Run integration tests only
	$(COMPOSE) exec $(SERVICE) pytest app/tests/integration/ -v

test-cov: ## Run tests with coverage report
	$(COMPOSE) exec $(SERVICE) pytest app/tests/ \
	  --cov=app --cov-report=term-missing --cov-fail-under=80

# ── Code quality ──────────────────────────────────────────────────────────────

lint: ## Run Ruff linter
	$(COMPOSE) exec $(SERVICE) ruff check app/

lint-fix: ## Auto-fix Ruff lint issues
	$(COMPOSE) exec $(SERVICE) ruff check app/ --fix

typecheck: ## Run mypy static type checks
	$(COMPOSE) exec $(SERVICE) mypy app/

format: ## Format code with Ruff
	$(COMPOSE) exec $(SERVICE) ruff format app/

check: lint typecheck ## Run all quality checks

# ── Celery ────────────────────────────────────────────────────────────────────

celery-worker: ## Start Celery worker locally (outside Docker)
	cd services/user-service && \
	  celery -A app.tasks.celery_app.celery_app worker \
	  --queues=default,notifications,maintenance \
	  --concurrency=4 --loglevel=info

celery-flower: ## Start Flower monitoring dashboard
	$(COMPOSE) up -d celery-flower
	@echo "Flower available at http://localhost:5555"

celery-beat: ## Start Celery Beat scheduler
	cd services/user-service && \
	  celery -A app.tasks.celery_app.celery_app beat --loglevel=info

# ── Utility ───────────────────────────────────────────────────────────────────

clean: ## Remove generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."

gen-keys: ## Generate RSA-4096 key pair for JWT (outputs .pem files in /tmp)
	openssl genrsa -out /tmp/aurafit_jwt_private.pem 4096
	openssl rsa -in /tmp/aurafit_jwt_private.pem -pubout -out /tmp/aurafit_jwt_public.pem
	@echo "Keys written to /tmp/aurafit_jwt_private.pem and /tmp/aurafit_jwt_public.pem"
	@echo "Add contents to .env as JWT_PRIVATE_KEY and JWT_PUBLIC_KEY"

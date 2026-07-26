# AuraFit — Deployment Guide

## Overview

AuraFit runs as 5 Docker containers (+ infrastructure). This guide covers:
1. Docker Compose (local / staging)
2. AWS ECS + RDS + ElastiCache (recommended production)
3. GCP Cloud Run + Cloud SQL (alternative)
4. Environment secrets management

---

## 1. Docker Compose Deployment

### Development

```bash
# Clone repo
git clone https://github.com/your-org/aurafit.git
cd aurafit

# Configure env (see ENVIRONMENT.md)
cp services/user-service/.env.example services/user-service/.env
# Edit .env with your values

# Start everything
docker compose up -d

# Apply migrations
docker compose exec user-service alembic upgrade head

# Seed initial data (optional)
docker compose exec user-service python -m app.scripts.seed_data

# Check health
docker compose ps
```

### Staging (single server)

```bash
# Build production images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start with production overrides
ENVIRONMENT=staging docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d
```

---

## 2. AWS ECS Deployment (Recommended Production)

### Architecture

```
Route 53 → CloudFront → ALB → ECS Tasks
                                 ├── user-service (ECS Fargate)
                                 ├── rec-service  (ECS Fargate)
                                 ├── facial-analysis (ECS EC2 — GPU opt.)
                                 ├── virtual-tryon   (ECS EC2)
                                 └── web (ECS Fargate)

RDS PostgreSQL (Multi-AZ) + ElastiCache Redis (Cluster mode)
S3 + CloudFront CDN
Secrets Manager (all env secrets)
```

### Step-by-step

#### A. Provision infrastructure (Terraform)

```bash
cd infra/terraform/aws
cp terraform.tfvars.example terraform.tfvars
# Edit with your AWS config
terraform init
terraform plan
terraform apply
```

Key resources created:
- VPC with 3 public + 3 private subnets
- RDS PostgreSQL 16 + pgvector (db.r6g.large)
- ElastiCache Redis 7 (cache.r6g.medium)
- S3 buckets (uploads, assets) + CloudFront
- ECR repositories (one per service)
- ECS cluster + task definitions
- ALB + target groups + listener rules
- Secrets Manager entries

#### B. Build and push images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS \
  --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Build + tag + push (run from repo root)
export REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com
export TAG=$(git rev-parse --short HEAD)

for service in user-service recommendation-service; do
  docker build -t $REGISTRY/aurafit-$service:$TAG \
    --target production \
    services/$service/
  docker push $REGISTRY/aurafit-$service:$TAG
done

for ai in facial-analysis virtual-tryon; do
  docker build -t $REGISTRY/aurafit-$ai:$TAG ai/$ai/
  docker push $REGISTRY/aurafit-$ai:$TAG
done

docker build -t $REGISTRY/aurafit-web:$TAG apps/web/
docker push $REGISTRY/aurafit-web:$TAG
```

#### C. Deploy to ECS

```bash
# Update task definitions with new image tags
python infra/scripts/update_ecs_tasks.py --tag $TAG

# Deploy each service
aws ecs update-service \
  --cluster aurafit-prod \
  --service user-service \
  --force-new-deployment

# Monitor deployment
aws ecs wait services-stable \
  --cluster aurafit-prod \
  --services user-service rec-service web
```

#### D. Run migrations

```bash
# Run as one-off ECS task (not a long-running service)
aws ecs run-task \
  --cluster aurafit-prod \
  --task-definition aurafit-migration \
  --overrides '{"containerOverrides":[{"name":"user-service","command":["alembic","upgrade","head"]}]}'
```

### Secrets (AWS Secrets Manager)

All secrets injected at task startup via `secrets:` in task definition:

```json
{
  "secrets": [
    {"name": "SECRET_KEY",            "valueFrom": "arn:aws:secretsmanager:.../aurafit/secret-key"},
    {"name": "DATABASE_URL",          "valueFrom": "arn:aws:secretsmanager:.../aurafit/database-url"},
    {"name": "JWT_PRIVATE_KEY",       "valueFrom": "arn:aws:secretsmanager:.../aurafit/jwt-private"},
    {"name": "JWT_PUBLIC_KEY",        "valueFrom": "arn:aws:secretsmanager:.../aurafit/jwt-public"},
    {"name": "GOOGLE_CLIENT_SECRET",  "valueFrom": "arn:aws:secretsmanager:.../aurafit/google-secret"},
    {"name": "RAZORPAY_KEY_SECRET",   "valueFrom": "arn:aws:secretsmanager:.../aurafit/razorpay-secret"}
  ]
}
```

---

## 3. GCP Cloud Run Deployment (Alternative)

### Services mapping

```
Cloud Run services:
  aurafit-web               → apps/web
  aurafit-user-service      → services/user-service
  aurafit-rec-service       → services/recommendation-service
  aurafit-facial-analysis   → ai/facial-analysis
  aurafit-virtual-tryon     → ai/virtual-tryon

Managed infrastructure:
  Cloud SQL (PostgreSQL 16)
  Memorystore (Redis)
  Cloud Storage (images + PDFs)
  Cloud CDN
  Secret Manager
```

### Deploy

```bash
# Authenticate
gcloud auth login
gcloud config set project aurafit-prod

# Build + push to Artifact Registry
gcloud builds submit \
  --tag europe-west1-docker.pkg.dev/aurafit-prod/aurafit/user-service:$TAG \
  services/user-service/

# Deploy
gcloud run deploy aurafit-user-service \
  --image europe-west1-docker.pkg.dev/aurafit-prod/aurafit/user-service:$TAG \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets="DATABASE_URL=aurafit-db-url:latest,SECRET_KEY=aurafit-secret-key:latest" \
  --min-instances 1 \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2
```

---

## 4. CI/CD (GitHub Actions)

The `.github/workflows/ci-cd.yml` pipeline runs on every push:

1. **Lint** — ruff (Python), ESLint + tsc (TypeScript)
2. **Unit tests** — pytest with coverage
3. **Integration tests** — pytest + real PostgreSQL + Redis services
4. **Build Docker images** — all 5 services
5. **Push to GHCR** — only on `main` branch
6. **Deploy staging** — automatic on `main`
7. **Deploy production** — manual trigger or tag push (`v*.*.*`)

### Required GitHub Secrets

```
AWS_ACCESS_KEY_ID          — AWS IAM user with ECS/ECR permissions
AWS_SECRET_ACCESS_KEY
AWS_REGION                 — e.g. us-east-1
ECR_REGISTRY               — 123456789.dkr.ecr.us-east-1.amazonaws.com
ECS_CLUSTER                — aurafit-prod
ECS_SERVICE_USER           — user-service
ECS_SERVICE_REC            — rec-service
ECS_SERVICE_WEB            — web
SLACK_WEBHOOK_URL          — deployment notifications (optional)
```

---

## 5. Database Migrations

Migrations run via Alembic. All 4 user-service migrations must run in order:

```
001_stage3_auth_schema        → Core: users, sessions, profiles, wardrobe
002_stage5_color_profiles     → Color intelligence: color_profiles
003_stage10_subscriptions     → Subscriptions: subscriptions, subscription_usage
004_stage8_style_dna          → Style DNA: quiz_sessions, quiz_responses, style_dna_reports
```

```bash
# Apply all (development)
docker compose exec user-service alembic upgrade head

# Apply specific
docker compose exec user-service alembic upgrade 003_stage10_subscriptions

# Roll back one
docker compose exec user-service alembic downgrade -1

# Show history
docker compose exec user-service alembic history --verbose
```

---

## 6. Scaling Guide

### Horizontal scaling

All services are stateless except Celery Beat (must be singleton). Scale others freely:

```bash
# ECS
aws ecs update-service --cluster aurafit-prod \
  --service user-service --desired-count 4

# Docker Compose (dev)
docker compose scale user-service=3
```

### Vertical scaling guidelines

| Service | Min RAM | Recommended | GPU? |
|---|---|---|---|
| user-service | 512MB | 2GB | No |
| rec-service | 1GB | 2GB | No (FAISS CPU) |
| facial-analysis | 2GB | 4GB | Optional (MediaPipe) |
| virtual-tryon | 2GB | 4GB | Optional (CLIP) |
| web (Next.js) | 512MB | 1GB | No |

### Database scaling

- Read replicas: add to SQLAlchemy connection pool with `statement_cache_size=0`
- Connection pooling: PgBouncer between services and RDS
- pgvector ANN tuning: `SET hnsw.ef_search = 100` for better recall

### Celery queue routing

```python
# High-priority AI tasks
CELERY_TASK_ROUTES = {
    "app.tasks.ai_tasks.*":  {"queue": "ai.high"},
    "app.tasks.rec_tasks.*": {"queue": "recommendations"},
    "app.tasks.*":           {"queue": "default"},
}
```

---

## 7. Troubleshooting

### Common issues

**`alembic.util.exc.CommandError: Target database is not up to date`**
```bash
docker compose exec user-service alembic stamp head
docker compose exec user-service alembic upgrade head
```

**MediaPipe fails to load in facial-analysis**
```bash
# Ensure libGL is available in container
docker compose exec facial-analysis python -c "import mediapipe; print('OK')"
# If fails: add libGL to Dockerfile: apt-get install -y libgl1
```

**CLIP model download timeout**
```bash
# Pre-download in Dockerfile (already done in virtual-tryon Dockerfile)
# Or set: TRANSFORMERS_CACHE=/app/.cache
```

**Redis connection refused**
```bash
docker compose ps redis
docker compose logs redis
# If not healthy: docker compose restart redis
```

**pgvector extension missing**
```bash
docker compose exec postgres psql -U aurafit -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

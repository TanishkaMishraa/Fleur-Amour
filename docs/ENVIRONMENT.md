# AuraFit — Master Environment Variable Reference
# Copy .env.example to .env in each service directory before running.
# NEVER commit .env files. Use AWS Secrets Manager / GCP Secret Manager in production.

# ════════════════════════════════════════════════════════════════════════════
# USER SERVICE (services/user-service/.env)
# ════════════════════════════════════════════════════════════════════════════

## Core
ENVIRONMENT=local                          # local | staging | production
DEBUG=true
LOG_LEVEL=DEBUG                            # DEBUG | INFO | WARNING | ERROR

## Security — generate with: openssl rand -hex 32
SECRET_KEY=change-me-to-a-random-32-char-string-minimum

## RS256 JWT Keys — generate with:
##   ssh-keygen -t rsa -b 4096 -m PEM -f keys/jwt_private.pem -N ""
##   openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

## Database
DATABASE_URL=postgresql://aurafit:aurafit@localhost:5432/aurafit
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_ECHO=false                        # true in dev for SQL logging

## Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

## Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

## AWS / Storage
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=                         # Empty for local (uses MinIO)
AWS_SECRET_ACCESS_KEY=
S3_UPLOADS_BUCKET=aurafit-uploads-dev
S3_ASSETS_BUCKET=aurafit-assets-dev
CDN_BASE_URL=https://cdn.aurafit.ai
CDN_BASE_URL_DEV=http://localhost:9000     # MinIO in development

## OAuth — Google Cloud Console
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

## Email — SendGrid
SENDGRID_API_KEY=
FROM_EMAIL=hello@aurafit.ai
FROM_NAME=AuraFit

## AI Services — inter-service URLs
FACIAL_ANALYSIS_URL=http://localhost:8010
RECOMMENDATION_SERVICE_URL=http://localhost:8003
VIRTUAL_TRYON_URL=http://localhost:8020

## Subscriptions
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

## Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AI_PER_MINUTE=10
RATE_LIMIT_AUTH_PER_MINUTE=5

## Allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,https://app.aurafit.ai


# ════════════════════════════════════════════════════════════════════════════
# RECOMMENDATION SERVICE (services/recommendation-service/.env)
# ════════════════════════════════════════════════════════════════════════════

DATABASE_URL=postgresql://aurafit:aurafit@localhost:5432/aurafit
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

## Algorithm weights (must sum to 1.0)
CF_WEIGHT=0.40
CB_WEIGHT=0.40
PROFILE_WEIGHT=0.20

## ALS collaborative filtering
ALS_FACTORS=128
ALS_ITERATIONS=20
ALS_REGULARIZATION=0.01

## Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

## Business rules
LUXURY_PRICE_THRESHOLD_INR=10000
MAX_ITEMS_PER_BRAND=3
NEW_PRODUCT_BOOST=1.05

## User service (for profile fetch)
USER_SERVICE_URL=http://localhost:8001


# ════════════════════════════════════════════════════════════════════════════
# FACIAL ANALYSIS SERVICE (ai/facial-analysis/.env)
# ════════════════════════════════════════════════════════════════════════════

ENVIRONMENT=local
DEBUG=true
PORT=8010
S3_UPLOADS_BUCKET=aurafit-uploads-dev
AWS_REGION=us-east-1
CDN_BASE_URL=http://localhost:9000


# ════════════════════════════════════════════════════════════════════════════
# VIRTUAL TRY-ON SERVICE (ai/virtual-tryon/.env)
# ════════════════════════════════════════════════════════════════════════════

ENVIRONMENT=local
DEBUG=true
PORT=8020
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
S3_UPLOADS_BUCKET=aurafit-uploads-dev
AWS_REGION=us-east-1
CDN_BASE_URL=http://localhost:9000
USER_SERVICE_URL=http://localhost:8001

## Celebrity matching models
CELEBRITY_INDEX_PATH=/app/models/celebrity_faiss.index
CELEBRITY_META_PATH=/app/models/celebrity_meta.json

## Makeup AR parameters
LIPSTICK_ALPHA_DEFAULT=0.55
FOUNDATION_ALPHA_DEFAULT=0.30
EYESHADOW_ALPHA_DEFAULT=0.50
HAIR_ALPHA_DEFAULT=0.60


# ════════════════════════════════════════════════════════════════════════════
# NEXT.JS FRONTEND (apps/web/.env.local)
# ════════════════════════════════════════════════════════════════════════════

NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
NEXT_PUBLIC_REC_API_URL=http://localhost:8003/api/v1
NEXT_PUBLIC_VTRYON_API_URL=http://localhost:8020/api/v1
NEXT_PUBLIC_APP_NAME=AuraFit
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_GOOGLE_CLIENT_ID=

## Server-side only (not NEXT_PUBLIC_)
NEXTAUTH_SECRET=change-me-random-string-for-nextauth


# ════════════════════════════════════════════════════════════════════════════
# DOCKER COMPOSE ROOT (.env at repo root)
# ════════════════════════════════════════════════════════════════════════════

POSTGRES_USER=aurafit
POSTGRES_PASSWORD=aurafit          # Change in production!
POSTGRES_DB=aurafit
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=minio123       # Change in production!

## Production image registry
REGISTRY=ghcr.io
IMAGE_PREFIX=your-org/aurafit
IMAGE_TAG=latest

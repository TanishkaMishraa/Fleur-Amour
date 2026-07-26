# AuraFit — AI-Powered Beauty & Styling Platform

> Enterprise-grade beauty intelligence: facial analysis, color science, recommendations, virtual try-on, and personal style AI — comparable to L'Oréal, Sephora, and Nykaa.

[![CI/CD](https://github.com/your-org/aurafit/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/aurafit/actions)
[![License: Commercial](https://img.shields.io/badge/License-Commercial-gold.svg)]()

---

## What is AuraFit?

AuraFit is a full-stack AI beauty platform built in 10 stages. It provides:

| Module | Capability |
|---|---|
| **Facial Analysis** | Skin tone (ITA°/Fitzpatrick), undertone, face shape, acne, dark circles, texture, symmetry, hair |
| **Color Intelligence** | 12-season Munsell/Sci·ART classification, personal palette, makeup/lipstick/hair/outfit/jewellery matching |
| **Recommendation Engine** | Hybrid ALS + SBERT + Profile-rules across 6 domains (makeup, skincare, haircare, fragrance, fashion, accessories) |
| **Smart Alternative Engine** | Ingredient Jaccard, shade ΔE (CIE 1994), fragrance note pyramid, embedding similarity, price comparison |
| **Style DNA** | 35-question quiz → personality dimensions → archetype → 9-section NLP report → ReportLab PDF |
| **Virtual Try-On** | MediaPipe FaceMesh + Canvas2D: lipstick, foundation, eyeshadow (real-time), hair colour (server-side) |
| **Wardrobe AI** | CLIP zero-shot clothing classification, k-means colour, AI outfit generation, capsule wardrobe analysis |
| **Celebrity Matching** | CLIP + FAISS ANN style similarity → celebrity style, makeup, fragrance inspiration |
| **AI Beauty Assistant** | Conversational chat (Claude/GPT backbone) for beauty, styling, and product guidance |
| **Subscription System** | FREE / GLOW ₹499 / RADIANCE ₹999 / LUXE ₹2499 — feature gates, usage tracking, Razorpay/Stripe |
| **Admin Platform** | User management, AI analytics, recommendation monitoring, queue status, daily reports |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      NGINX (Port 80/443)                     │
│          SSL termination · Rate limiting · Routing           │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
      ┌────▼───┐ ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
      │  Web   │ │  User  │ │  Rec   │ │  AI    │
      │ :3000  │ │ :8001  │ │ :8003  │ │Services│
      │Next.js │ │FastAPI │ │FastAPI │ │:8010   │
      │        │ │        │ │        │ │:8020   │
      └────────┘ └───┬────┘ └────────┘ └────────┘
                     │
          ┌──────────┼──────────┐
     ┌────▼───┐ ┌────▼───┐ ┌───▼────┐
     │PostgreSQL│ │ Redis  │ │  S3   │
     │+ pgvector│ │ Cache  │ │Uploads│
     │ :5432  │ │ :6379  │ │  CDN  │
     └────────┘ └────────┘ └────────┘
                     │
          ┌──────────┴──────────┐
     ┌────▼───┐           ┌────▼───┐
     │ Celery │           │ Beat   │
     │Workers │           │Scheduler│
     └────────┘           └────────┘
```

**Services:**
- `apps/web` — Next.js 14 + TypeScript + Tailwind + ShadCN (port 3000)
- `services/user-service` — FastAPI core: auth, profiles, color, style DNA, wardrobe (port 8001)
- `services/recommendation-service` — FastAPI: ALS + SBERT + pgvector recommendations + alternatives (port 8003)
- `ai/facial-analysis` — FastAPI: MediaPipe + OpenCV + DeepFace pipeline (port 8010)
- `ai/virtual-tryon` — FastAPI: makeup AR + wardrobe AI + celebrity matching (port 8020)

**Infrastructure:**
- PostgreSQL 16 + pgvector extension
- Redis 7 (cache + Celery broker)
- MinIO / S3 (image storage)
- Nginx (reverse proxy + SSL)
- Celery (async task queue)

---

## Quick Start (Development)

### Prerequisites
- Docker 24+ and Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)
- 8GB RAM minimum (AI models)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/aurafit.git
cd aurafit

# Copy environment files
cp services/user-service/.env.example services/user-service/.env
cp .env.example .env

# Generate RS256 keys for JWT
ssh-keygen -t rsa -b 4096 -m PEM -f keys/jwt_private.pem -N ""
openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
```

### 2. Start infrastructure

```bash
make up
# or: docker compose up -d
```

### 3. Apply database migrations

```bash
make migrate
# or: docker compose exec user-service alembic upgrade head
```

### 4. Verify services

```bash
curl http://localhost:8001/api/v1/health  # User service
curl http://localhost:8003/api/v1/health  # Rec service
curl http://localhost:8010/health          # Facial analysis
curl http://localhost:8020/api/v1/health  # Virtual try-on
curl http://localhost:3000                 # Frontend
```

### 5. Run tests

```bash
make test                    # All tests
make test SERVICE=user-service  # Specific service
```

---

## Project Structure

```
aurafit/
├── apps/
│   └── web/                         # Next.js 14 frontend
│       ├── src/
│       │   ├── app/                 # App Router pages
│       │   │   ├── auth/            # Login, register, MFA
│       │   │   └── dashboard/       # All feature pages
│       │   ├── components/          # UI components
│       │   ├── lib/                 # API clients, hooks, stores
│       │   └── types/               # TypeScript type definitions
│       └── Dockerfile
│
├── services/
│   ├── user-service/                # Core FastAPI service (port 8001)
│   │   ├── app/
│   │   │   ├── api/v1/endpoints/    # 15 endpoint modules
│   │   │   ├── models/              # 14 SQLAlchemy ORM models
│   │   │   ├── services/            # Business logic layer
│   │   │   ├── repositories/        # Data access layer
│   │   │   └── tasks/               # Celery async tasks
│   │   └── alembic/                 # 4 database migrations
│   │
│   └── recommendation-service/      # Recommendations + alternatives (port 8003)
│       └── app/
│           ├── services/algorithms/ # ALS, SBERT, profile rules
│           └── services/alternatives/ # Ingredient, shade, fragrance engines
│
├── ai/
│   ├── facial-analysis/             # Computer vision pipeline (port 8010)
│   │   └── app/pipeline/analyzers/ # 8 specialised analyzers
│   │
│   └── virtual-tryon/               # AR makeup + wardrobe AI (port 8020)
│       └── app/services/
│           ├── tryon/               # Makeup AR engine (MediaPipe)
│           ├── wardrobe/            # CLIP classification + outfit gen
│           └── celebrity/           # CLIP + FAISS matching
│
├── infra/
│   ├── nginx/                       # nginx.dev.conf + nginx.prod.conf
│   └── docker/postgres/             # init.sql with pgvector extension
│
├── docs/                            # Architecture, API, deployment guides
├── .github/workflows/               # CI/CD pipeline
├── docker-compose.yml               # Development stack
├── docker-compose.prod.yml          # Production overrides
└── Makefile                         # Developer shortcuts
```

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, ShadCN UI, Zustand, React Query, Framer Motion, Axios |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, Celery, structlog |
| **Database** | PostgreSQL 16, pgvector (embeddings), Redis 7 |
| **AI/ML** | MediaPipe FaceMesh, OpenCV, DeepFace, CLIP (ViT-B/32), SBERT (all-MiniLM-L6-v2), FAISS, implicit (ALS), scikit-learn, ReportLab |
| **Auth** | RS256 JWT, refresh token rotation, Redis blocklist, Google OAuth PKCE, TOTP MFA |
| **Storage** | AWS S3 / MinIO (images, PDFs), CDN via CloudFront |
| **DevOps** | Docker, Nginx, GitHub Actions, AWS ECS / GCP Cloud Run |

---

## API Base URLs

| Service | Dev | Prod |
|---|---|---|
| User Service | `http://localhost:8001/api/v1` | `https://api.aurafit.ai/api/v1` |
| Rec Service | `http://localhost:8003/api/v1` | `https://rec.aurafit.ai/api/v1` |
| Facial Analysis | `http://localhost:8010/api/v1` | `https://ai.aurafit.ai/api/v1` |
| Virtual Try-On | `http://localhost:8020/api/v1` | `https://vtryon.aurafit.ai/api/v1` |
| Frontend | `http://localhost:3000` | `https://app.aurafit.ai` |

---

## Subscription Plans

| Feature | Free | Glow ₹499 | Radiance ₹999 | Luxe ₹2499 |
|---|:---:|:---:|:---:|:---:|
| Facial scans/month | 3 | ∞ | ∞ | ∞ |
| Color profile | ✓ | ✓ | ✓ | ✓ |
| Recommendations | ✓ | ✓ | ✓ | ✓ |
| Style DNA Report | ✗ | ✓ | ✓ | ✓ |
| Smart Alternatives | ✗ | ✓ | ✓ | ✓ |
| Virtual Try-On | ✗ | ✗ | ✓ | ✓ |
| Wardrobe AI (items) | 0 | 0 | 50 | ∞ |
| Celebrity Matching | ✗ | ✗ | ✓ | ✓ |
| PDF Export | ✗ | ✗ | ✗ | ✓ |
| AI Chat/day | 5 | 25 | 100 | ∞ |

---

## Contributing

See [DEVELOPMENT.md](./DEVELOPMENT.md) for local setup, coding standards, and PR guidelines.

## License

Proprietary — All rights reserved. AuraFit™ 2025.

# AuraFit — System Architecture

## Design Principles

1. **Microservices by domain** — Each service owns its own DB connection, Celery queue, and API surface. No shared ORM classes across service boundaries.
2. **Repository + Service pattern** — DB access via repository classes; business logic in service classes; HTTP contracts via Pydantic schemas.
3. **Async-first** — FastAPI + asyncpg + SQLAlchemy async everywhere. CPU-bound AI tasks dispatched to Celery workers.
4. **Cache-first reads** — Redis L1 cache with configurable TTLs on all hot paths (user profile: 1h, product list: 30min, recommendations: 1h).
5. **Event-driven async** — Celery handles: embedding refresh, PDF generation, email dispatch, model retraining. Never blocks the API response.

---

## Service Map

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
│                                                                   │
│  Browser / iOS / Android ──► Next.js 14 (SSR + CSR, port 3000)  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼──────────────────────────────────┐
│                         NGINX GATEWAY                             │
│  SSL termination · Rate limiting · Request routing               │
│                                                                   │
│  /api/v1/*          → user-service:8001                          │
│  /rec-api/*         → recommendation-service:8003                │
│  /ai-api/*          → facial-analysis:8010                       │
│  /vtryon-api/*      → virtual-tryon:8020                         │
│  /*                 → web:3000                                   │
└──┬──────────────┬──────────────┬──────────────┬─────────────────┘
   │              │              │              │
┌──▼──────┐  ┌───▼────┐  ┌──────▼──┐  ┌───────▼──┐
│  User   │  │  Rec   │  │ Facial  │  │  VTryon  │
│ Service │  │ Service│  │Analysis │  │ Service  │
│ :8001   │  │ :8003  │  │  :8010  │  │  :8020   │
│         │  │        │  │         │  │          │
│ Auth    │  │ ALS CF │  │MediaPipe│  │Makeup AR │
│ Profile │  │ SBERT  │  │OpenCV   │  │Wardrobe  │
│ Color   │  │ pgvec  │  │DeepFace │  │CLIP+FAISS│
│ StyleDNA│  │ Alt Eng│  │         │  │Celebrity │
│ Wardrobe│  │        │  │         │  │          │
│ Chat    │  │        │  │         │  │          │
│ Subs    │  │        │  │         │  │          │
│ Admin   │  │        │  │         │  │          │
└──┬──────┘  └───┬────┘  └─────────┘  └──────────┘
   │             │
┌──▼─────────────▼──────────────────────────────────────────────┐
│                      DATA LAYER                                │
│                                                                │
│  PostgreSQL 16 + pgvector ──────────── Schema (shared DB)     │
│    users, profiles, wardrobes                                  │
│    facial_scans, color_profiles                                │
│    quiz_sessions, style_dna_reports                            │
│    subscriptions, subscription_usage                           │
│    products, product_embeddings (Vector 384)                   │
│    recommendations, user_product_interactions                  │
│    product_alternatives                                        │
│                                                                │
│  Redis 7 ──────────────────────────────── Cache + Queue       │
│    DB 0: Application cache (user data, recommendations)        │
│    DB 1: Celery broker                                         │
│    DB 2: Celery results                                        │
│    DB 3: Rate limiting counters                                │
│                                                                │
│  S3 / MinIO ───────────────────────────── Object Storage      │
│    aurafit-uploads: selfies, wardrobe images                   │
│    aurafit-assets:  style DNA PDFs, processed results          │
└────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow

```
Client                    User Service                 Redis
  │                           │                          │
  │── POST /auth/login ────►  │                          │
  │                           │── Verify password ──     │
  │                           │── Generate RS256 JWT ──  │
  │                           │── Store refresh token ──►│
  │◄── {access, refresh} ─── │                          │
  │                           │                          │
  │── API request + Bearer ──►│                          │
  │                           │── Verify JWT signature ──│
  │                           │── Check blocklist ──────►│
  │◄── Response ─────────── │                          │
  │                           │                          │
  │── POST /auth/refresh ────►│                          │
  │                           │── Validate refresh ─────►│
  │                           │── Rotate refresh token   │
  │◄── {new_access} ──────── │                          │
```

**Key security properties:**
- RS256 JWT: private key signs tokens; services verify with public key only
- Access tokens: 15 min TTL, stateless verification
- Refresh tokens: 7 day TTL, stored in Redis, single-use (rotation on every refresh)
- Logout: adds access token to Redis blocklist until expiry
- MFA: TOTP via pyotp, QR code served as data URI, backup codes stored hashed

---

## Recommendation Engine Pipeline

```
User Request → POST /recommendations
                    │
            ┌───────▼──────────┐
            │ UserVectorBuilder │  Fetches: profile, color season,
            │                  │  interaction history from DB
            └───────┬──────────┘
                    │ UserPreferenceSignals
         ┌──────────┼──────────────┐
         │          │              │
    ┌────▼───┐ ┌────▼───┐ ┌──────▼──────┐
    │   CF   │ │Content │ │Profile Rules│
    │  ALS   │ │ Based  │ │   Engine   │
    │300 cands│ │200 cands│ │deterministic│
    └────┬───┘ └────┬───┘ └──────┬──────┘
         │          │              │
         └──────────┼──────────────┘
                    │ Merged candidates
            ┌───────▼──────────┐
            │  Hybrid Scoring  │
            │  0.40 × CF       │
            │+ 0.40 × CB       │
            │+ 0.20 × Profile  │
            └───────┬──────────┘
                    │
            ┌───────▼──────────┐
            │  Post-Processing  │
            │  New arrival ×1.05│
            │  Brand diversity  │
            │  Budget filter    │
            └───────┬──────────┘
                    │ Top-20
            ┌───────▼──────────┐
            │  Explanation Gen  │
            │  reason_code →   │
            │  human prose     │
            └───────┬──────────┘
                    │
             RecommendationResponse
```

---

## Smart Alternative Engine

```
Trigger: product.price >= ₹10,000

Source product
    │
    ├─► IngredientEngine   ── INCI parse → Jaccard(actives×3, base×1)
    │   (skincare/haircare)
    │
    ├─► FragranceEngine    ── Note pyramid: top×0.2, mid×0.3, base×0.5
    │   (fragrance)           + olfactive family affinity graph
    │
    ├─► ShadeEngine        ── hex → CIELAB → ΔE (CIE 1994)
    │   (makeup)              ΔE < 2 = near-perfect dupe
    │
    ├─► ContentFilter      ── SBERT cosine similarity (pgvector ANN)
    │   (all domains)
    │
    └─► MatchingEngine     ── Domain-weighted composite:
                              Makeup:     shade×0.4 + embed×0.3 + formula×0.3
                              Skincare:   ingred×0.5 + embed×0.25 + formula×0.25
                              Fragrance:  notes×0.65 + embed×0.2 + character×0.15
                              Fashion:    embed×0.45 + style×0.35 + formula×0.20
```

---

## Database Schema (Key Tables)

```
users ────────────────────────────────────────────────────────────
  id (UUID PK) · email · full_name · role · is_verified
  created_at · updated_at

user_profiles ── 1:1 with users ──────────────────────────────────
  skin_tone · skin_type · undertone · hair_type · body_shape
  style_archetypes [] · fragrance_family [] · skin_concerns []
  budget_range · currency · onboarding_complete

facial_scans ── N:1 with users ──────────────────────────────────
  face_shape · skin_analysis (JSONB) · facial_features (JSONB)
  landmark_data (JSONB) · quality_score · is_active

color_profiles ── N:1 with users ─────────────────────────────────
  season · season_confidence · palette_best (JSONB)
  makeup_recommendations (JSONB) · lipstick_recommendations (JSONB)

quiz_sessions ── N:1 with users ──────────────────────────────────
  quiz_version · status · style_axis · energy_axis · structure_axis
  primary_archetype · secondary_archetype · occasion_mix (JSONB)

style_dna_reports ── N:1 with users ──────────────────────────────
  headline · narrative · skin_profile (JSONB) · color_profile_section (JSONB)
  fashion_profile (JSONB) · fragrance_profile_section (JSONB)
  hairstyle_profile (JSONB) · pdf_url

products ── catalog ──────────────────────────────────────────────
  sku · name · brand_id → brands · category_id → categories
  price · attributes (JSONB) · ingredients · style_tags []
  avg_rating · interaction_count · is_new_arrival · is_trending

product_embeddings ── 1:1 with products ─────────────────────────
  text_embedding (Vector 384)   ← SBERT all-MiniLM-L6-v2
  image_embedding (Vector 512)  ← CLIP ViT-B/32

product_alternatives ── N:N ─────────────────────────────────────
  source_id → products · alt_id → products
  overall_score · ingredient_score · shade_score · fragrance_score
  price_savings · savings_pct · is_best_value · rank

subscriptions ── 1:1 with users ──────────────────────────────────
  plan (free/glow/radiance/luxe) · status · provider
  current_period_end · cancel_at_period_end
```

---

## Celery Task Queues

| Queue | Workers | Tasks |
|---|---|---|
| `default` | 4 | Email, notifications, general async |
| `ai.high` | 2 | Facial scan processing (priority) |
| `ai.low` | 2 | Model retraining, batch embeddings |
| `recommendations` | 2 | User embedding rebuild, rec cache warm |
| `media` | 2 | PDF generation, S3 upload |
| `maintenance` | 1 | Trending recompute, stale report detection |

**Beat schedule:**
```
02:00 UTC — rebuild_cf_model              (nightly ALS retraining)
03:30 UTC — precompute_luxury_alternatives (nightly dupe engine)
06:00 UTC — refresh_product_embeddings    (new/updated products)
*/6h      — recompute_trending            (trending flag update)
Weekly    — pregenerate_stale_reports     (detect outdated Style DNA)
Monthly   — reset_subscription_usage     (monthly usage counters)
```

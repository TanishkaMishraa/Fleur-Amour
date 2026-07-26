"""
AuraFit — Recommendation Service API endpoints.

Routes:
  POST /recommendations          — hybrid recommendations (any domain)
  POST /recommendations/makeup   — makeup-specific
  POST /recommendations/skincare
  POST /recommendations/haircare
  POST /recommendations/fragrance
  POST /recommendations/fashion
  POST /recommendations/accessories
  POST /recommendations/feedback — update click/save/purchase signals
  POST /interactions             — record a user interaction

  GET  /products                 — search/filter catalog
  GET  /products/{id}            — product detail
  GET  /products/{id}/similar    — similar products
  GET  /products/{id}/reviews    — product reviews
  GET  /categories               — category tree
  GET  /brands                   — brand list
  GET  /health                   — liveness probe
  GET  /ready                    — readiness probe
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.recommendation_schemas import (
    FeedbackRequest, InteractionRequest, PaginatedProducts,
    ProductOut, ProductSearchRequest, RecommendationDomain,
    RecommendationRequest, RecommendationResponse, SortOrder,
)
from app.services.catalog_service import CatalogService
from app.services.hybrid_engine import HybridRecommendationEngine

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Recommendation endpoints ──────────────────────────────────────────────────

def _rec_router(domain: RecommendationDomain) -> APIRouter:
    r = APIRouter()

    @r.post(
        f"/recommendations/{domain.value}",
        response_model=RecommendationResponse,
        summary=f"Get {domain.value} recommendations",
        tags=["Recommendations"],
    )
    async def recommend_domain(
        request: RecommendationRequest,
        session: DbSession,
    ) -> RecommendationResponse:
        request.domain = domain
        engine = HybridRecommendationEngine(session)
        return await engine.recommend(request)

    return r


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Get hybrid recommendations (all domains)",
    tags=["Recommendations"],
    description=(
        "Runs the 4-stage hybrid pipeline (CF + Content-Based + Profile rules). "
        "Set `domain` to filter to a specific category. Defaults to `mixed`."
    ),
)
async def recommend(
    request: RecommendationRequest,
    session: DbSession,
) -> RecommendationResponse:
    engine = HybridRecommendationEngine(session)
    return await engine.recommend(request)


@router.post(
    "/recommendations/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Update recommendation outcome signals",
    tags=["Recommendations"],
)
async def recommendation_feedback(
    payload: FeedbackRequest,
    session: DbSession,
) -> None:
    """Record click, save, or purchase against a specific recommendation."""
    from sqlalchemy import select, update
    from app.models.catalog import Recommendation

    result = await session.execute(
        select(Recommendation).where(Recommendation.id == payload.recommendation_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if payload.clicked:   rec.was_clicked   = True
    if payload.saved:     rec.was_saved     = True
    if payload.purchased: rec.was_purchased = True
    session.add(rec)


@router.post(
    "/interactions",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Record a user-product interaction",
    tags=["Interactions"],
)
async def record_interaction(
    payload: InteractionRequest,
    session: DbSession,
) -> dict:
    """
    Records the interaction and schedules async embedding rebuild if
    the user has crossed the MIN_INTERACTION_FOR_CF threshold.
    """
    svc = CatalogService(session)
    await svc.record_interaction(
        user_id=payload.user_id,
        product_id=payload.product_id,
        interaction_type=payload.interaction_type,
        rating=payload.rating,
        session_context=payload.session_context,
    )
    # Trigger async user embedding rebuild via Celery (non-blocking)
    try:
        from app.tasks.rec_tasks import rebuild_user_embedding
        rebuild_user_embedding.apply_async(
            kwargs={"user_id": str(payload.user_id)},
            countdown=30,    # 30s delay to batch multiple rapid interactions
        )
    except Exception:
        pass   # Celery not available in dev mode — non-fatal
    return {"status": "accepted"}


# ── Catalog endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/products",
    response_model=PaginatedProducts,
    summary="Search and filter product catalog",
    tags=["Catalog"],
)
async def search_products(
    session: DbSession,
    q:             str | None = Query(None, description="Full-text search"),
    domain:        RecommendationDomain | None = Query(None),
    category_slug: str | None = Query(None),
    brand_slug:    str | None = Query(None),
    price_min:     float | None = Query(None),
    price_max:     float | None = Query(None),
    skin_tone:     str | None = Query(None),
    undertone:     str | None = Query(None),
    in_stock_only: bool = Query(True),
    sort:          SortOrder = Query(SortOrder.RELEVANCE),
    page:          int = Query(1, ge=1),
    per_page:      int = Query(24, ge=1, le=100),
) -> PaginatedProducts:
    svc = CatalogService(session)
    req = ProductSearchRequest(
        q=q, domain=domain, category_slug=category_slug,
        brand_slug=brand_slug, price_min=price_min, price_max=price_max,
        skin_tone=skin_tone, undertone=undertone, in_stock_only=in_stock_only,
        sort=sort, page=page, per_page=per_page,
    )
    return await svc.search(req)


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
    summary="Get product detail",
    tags=["Catalog"],
)
async def get_product(product_id: UUID, session: DbSession) -> ProductOut:
    svc = CatalogService(session)
    product = await svc.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get(
    "/products/{product_id}/similar",
    summary="Get similar products",
    tags=["Catalog"],
)
async def get_similar_products(
    product_id: UUID,
    session: DbSession,
    limit: int = Query(10, ge=1, le=30),
) -> dict:
    svc = CatalogService(session)
    similar = await svc.get_similar_products(product_id, limit=limit)
    return {"items": [p.model_dump() for p in similar], "total": len(similar)}


@router.get(
    "/products/{product_id}/reviews",
    summary="Get product reviews",
    tags=["Catalog"],
)
async def get_reviews(
    product_id: UUID,
    session: DbSession,
    limit: int = Query(20, ge=1, le=50),
) -> dict:
    from app.schemas.recommendation_schemas import ReviewOut
    svc = CatalogService(session)
    reviews = await svc.get_reviews(product_id, limit=limit)
    return {
        "items":  [ReviewOut.model_validate(r).model_dump() for r in reviews],
        "total":  len(reviews),
    }


@router.get(
    "/categories",
    summary="List product categories",
    tags=["Catalog"],
)
async def list_categories(
    session: DbSession,
    parent_id: UUID | None = Query(None),
) -> dict:
    from app.schemas.recommendation_schemas import CategoryOut
    svc = CatalogService(session)
    cats = await svc.list_categories(parent_id)
    return {"categories": [CategoryOut.model_validate(c).model_dump() for c in cats]}


@router.get(
    "/brands",
    summary="List brands",
    tags=["Catalog"],
)
async def list_brands(
    session: DbSession,
    tier: str | None = Query(None, description="luxury | mid | drugstore"),
) -> dict:
    from app.schemas.recommendation_schemas import BrandOut
    svc = CatalogService(session)
    brands = await svc.list_brands(tier=tier)
    return {"brands": [BrandOut.model_validate(b).model_dump() for b in brands]}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["Health"])
async def health() -> dict:
    from app.services.algorithms.collaborative_filter import get_cf_model
    cf = get_cf_model()
    return {
        "status":         "ok",
        "service":        "AuraFit Recommendation Service",
        "version":        "1.0.0",
        "cf_model_ready": cf.is_ready,
    }


@router.get("/ready", tags=["Health"], include_in_schema=False)
async def ready(session: DbSession) -> dict:
    from sqlalchemy import text
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}


# ── Re-export so main router can import from one location ────────────────────
from app.api.v1.endpoints.alternatives import router as alternatives_router  # noqa: E402

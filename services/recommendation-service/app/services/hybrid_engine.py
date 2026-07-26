"""
AuraFit — Hybrid Recommendation Engine.

Implements the Stage 0 4-stage pipeline:
  Stage 1 — Candidate generation (recall)
    Source A: ALS collaborative filtering (top-300 per user)
    Source B: Content-based ANN via pgvector (top-200)
    Source C: Profile-rule baseline (all in-stock, profile-filtered)
  Stage 2 — Scoring (ranking)
    hybrid_score = (CF_WEIGHT × cf_score)
                 + (CB_WEIGHT × cb_score)
                 + (PROFILE_WEIGHT × profile_score)
  Stage 3 — Post-processing (business rules)
    - Remove already-purchased / excluded items
    - Boost new arrivals (< 14 days): × NEW_PRODUCT_BOOST
    - Brand diversity cap (max MAX_ITEMS_PER_BRAND in top-FINAL_RESULTS)
    - Stock filter (in_stock only)
    - Optional domain filter, budget filter
  Stage 4 — Explanation
    reason_code → human-readable explanation string

Returns: list[RecommendedProduct] (max FINAL_RESULTS items)
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.catalog import Product, ProductEmbedding, RecommendationSession, Recommendation
from app.schemas.recommendation_schemas import (
    BrandOut, CategoryOut, ProductListOut, RecommendationRequest,
    RecommendationResponse, RecommendedProduct, UserPreferenceSignals,
)
from app.services.algorithms.collaborative_filter import get_cf_model
from app.services.algorithms.content_based_filter import get_cb_filter
from app.services.algorithms.profile_rules_engine import ProfileRulesEngine
from app.services.user_vector_builder import UserVectorBuilder

logger = get_logger(__name__)

_ENGINE_VERSION = "1.0.0"

_REASON_COPY = {
    "CF_MATCH":                  "Loved by users with your beauty profile",
    "CB_SIMILAR":                "Similar to products you've engaged with",
    "SKIN_TONE_MATCH":           "Matched to your skin tone",
    "UNDERTONE_MATCH":           "Perfectly suits your undertone",
    "SKIN_COMPATIBLE":           "Compatible with your skin profile",
    "CONCERN_INGREDIENT_MATCH":  "Targets your skin concerns",
    "FRAGRANCE_FAMILY_MATCH":    "Matches your fragrance preferences",
    "FRAGRANCE_EXACT_MATCH":     "Exact match for your favourite fragrance family",
    "STYLE_ARCHETYPE_MATCH":     "Fits your personal style",
    "COLOR_SEASON_MATCH":        "In your personal color palette",
    "BUDGET_MATCH":              "Within your budget",
    "TRENDING":                  "Trending in your category",
    "NEW_ARRIVAL":               "New arrival",
    "PROFILE_MATCH":             "Recommended for your profile",
    "POPULAR":                   "Popular with users like you",
}

_INTERACTION_CONFIDENCE = {
    "purchase": 5.0,
    "save":     3.0,
    "like":     2.0,
    "try_on":   2.0,
    "review":   2.5,
    "view":     0.5,
    "dislike": -1.0,
}


class HybridRecommendationEngine:
    """
    Orchestrates CF + Content-Based + Profile-Rules → ranked list.
    One instance per request (stateless, async).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._s       = get_settings()
        self._cf      = get_cf_model()
        self._cb      = get_cb_filter()
        self._rules   = ProfileRulesEngine()

    async def recommend(
        self,
        request: RecommendationRequest,
    ) -> RecommendationResponse:
        """Full 4-stage hybrid pipeline."""

        # ── Build user preference signals ────────────────────────────────────
        user_id = request.user_id
        builder = UserVectorBuilder(self._session)
        signals = await builder.build(user_id)

        cold_start = signals.interaction_count < self._s.MIN_INTERACTION_FOR_CF
        logger.info(
            "rec.pipeline_start",
            user_id=str(user_id),
            domain=request.domain,
            cold_start=cold_start,
        )

        # ── Stage 1: Candidate generation ────────────────────────────────────
        candidates: dict[str, dict] = {}   # product_id_str → {cf_score, cb_score}

        # Source A: Collaborative Filtering
        if not cold_start and self._cf.is_ready:
            cf_results = self._cf.recommend(str(user_id), n=self._s.CF_CANDIDATES)
            for pid, score in cf_results:
                candidates.setdefault(pid, {})["cf_score"] = score

        # Source B: Content-Based ANN
        user_embedding = await self._cb.get_user_embedding(self._session, user_id)
        if user_embedding:
            cb_results = await self._cb.find_similar_by_embedding(
                self._session,
                query_embedding=user_embedding,
                n=self._s.CB_CANDIDATES,
                exclude_ids=request.exclude_ids or [],
            )
            for pid, score in cb_results:
                candidates.setdefault(pid, {})["cb_score"] = score

        # Source C: Profile-rule baseline (ensures cold-start coverage)
        baseline_ids = await self._get_baseline_candidates(
            domain=request.domain.value,
            limit=self._s.CF_CANDIDATES if cold_start else 100,
        )
        for pid in baseline_ids:
            candidates.setdefault(str(pid), {})

        if not candidates:
            logger.warning("rec.no_candidates", user_id=str(user_id))
            return self._empty_response(request)

        # ── Fetch product details for all candidates ──────────────────────────
        cand_ids = [uuid.UUID(pid) for pid in candidates.keys()]
        products = await self._fetch_products(cand_ids)
        product_map = {str(p.id): p for p in products}

        # ── Stage 2: Scoring ─────────────────────────────────────────────────
        scored: list[dict] = []
        for pid, comp_scores in candidates.items():
            product = product_map.get(pid)
            if not product:
                continue

            # Apply domain filter
            if request.domain.value != "mixed":
                if not self._matches_domain(product, request.domain.value):
                    continue

            # Apply budget filter
            if request.budget_max and product.price > request.budget_max:
                continue
            if request.budget_min and product.price < request.budget_min:
                continue

            # Apply exclude filter
            if request.exclude_ids and uuid.UUID(pid) in request.exclude_ids:
                continue

            cf_score      = comp_scores.get("cf_score", 0.0)
            cb_score      = comp_scores.get("cb_score", 0.0)
            profile_score, reason = self._rules.score(product, signals)

            hybrid_score = (
                self._s.CF_WEIGHT      * cf_score
                + self._s.CB_WEIGHT    * cb_score
                + self._s.PROFILE_WEIGHT * profile_score
            )

            # Determine best reason_code
            if cf_score >= cb_score and cf_score > 0:
                reason = "CF_MATCH"
            elif cb_score > cf_score and cb_score > 0:
                reason = "CB_SIMILAR"

            scored.append({
                "product_id":    pid,
                "product":       product,
                "score":         hybrid_score,
                "cf_score":      cf_score,
                "cb_score":      cb_score,
                "profile_score": profile_score,
                "reason_code":   reason,
            })

        # ── Stage 3: Post-processing ─────────────────────────────────────────
        scored = self._post_process(scored, request)

        # ── Stage 4: Build response ──────────────────────────────────────────
        items = []
        for i, entry in enumerate(scored[: self._s.FINAL_RESULTS]):
            product = entry["product"]
            items.append(
                RecommendedProduct(
                    product=self._to_product_list_out(product),
                    score=round(entry["score"], 5),
                    cf_score=round(entry["cf_score"], 5),
                    cb_score=round(entry["cb_score"], 5),
                    profile_score=round(entry["profile_score"], 5),
                    position=i + 1,
                    reason_code=entry["reason_code"],
                    explanation=_REASON_COPY.get(entry["reason_code"], "Recommended for you"),
                )
            )

        # Persist session + recommendations (async, don't block response)
        session_id = await self._persist_session(user_id, request, items)

        logger.info(
            "rec.pipeline_complete",
            user_id=str(user_id),
            items=len(items),
            cold_start=cold_start,
        )
        return RecommendationResponse(
            session_id=session_id,
            domain=request.domain.value,
            items=items,
            total=len(items),
            model_version=_ENGINE_VERSION,
            cold_start=cold_start,
        )

    # ── Stage 3 helpers ───────────────────────────────────────────────────────

    def _post_process(self, scored: list[dict], request: RecommendationRequest) -> list[dict]:
        """Apply business rules: boosts, diversity, dedup."""
        s = self._s
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=s.NEW_PRODUCT_DAYS)

        for entry in scored:
            product = entry["product"]
            # New arrival boost
            if product.is_new_arrival:
                entry["score"] = min(entry["score"] * s.NEW_PRODUCT_BOOST, 1.0)
                entry["reason_code"] = "NEW_ARRIVAL"
            # Trending boost (smaller)
            if product.is_trending and entry["reason_code"] not in ("NEW_ARRIVAL",):
                entry["score"] = min(entry["score"] * 1.02, 1.0)
                if entry["cf_score"] == 0 and entry["cb_score"] == 0:
                    entry["reason_code"] = "TRENDING"

        # Sort by hybrid score
        scored.sort(key=lambda e: e["score"], reverse=True)

        # Brand diversity cap
        brand_counts: dict = defaultdict(int)
        diversified = []
        overflow    = []
        for entry in scored:
            brand_id = str(entry["product"].brand_id)
            if brand_counts[brand_id] < s.MAX_ITEMS_PER_BRAND:
                diversified.append(entry)
                brand_counts[brand_id] += 1
            else:
                overflow.append(entry)

        # Re-insert overflow at end if we need more items
        combined = diversified + overflow
        return combined

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _get_baseline_candidates(self, domain: str, limit: int = 200) -> list[uuid.UUID]:
        """Popularity-ordered products for the given domain (cold-start fallback)."""
        query = (
            select(Product.id)
            .where(Product.is_active == True)   # noqa: E712
            .where(Product.in_stock == True)    # noqa: E712
            .order_by(Product.interaction_count.desc(), Product.avg_rating.desc())
            .limit(limit)
        )
        if domain != "mixed":
            from app.models.catalog import Category
            query = query.join(Category, Product.category_id == Category.id)
            # Filter by category slug prefix (e.g. "makeup-*")
        result = await self._session.execute(query)
        return [r[0] for r in result.fetchall()]

    async def _fetch_products(self, product_ids: list[uuid.UUID]) -> list[Product]:
        """Batch fetch products with brand + category eagerly loaded."""
        from sqlalchemy.orm import selectinload
        result = await self._session.execute(
            select(Product)
            .where(Product.id.in_(product_ids))
            .where(Product.is_active == True)   # noqa: E712
            .where(Product.in_stock == True)    # noqa: E712
            .options(
                selectinload(Product.brand),
                selectinload(Product.category),
            )
        )
        return list(result.scalars().all())

    async def _persist_session(
        self,
        user_id: uuid.UUID,
        request: RecommendationRequest,
        items: list[RecommendedProduct],
    ) -> uuid.UUID:
        """Persist recommendation session + individual items to DB."""
        from app.models.catalog import RecommendationSession, Recommendation, SessionType

        session_obj = RecommendationSession(
            user_id=user_id,
            session_type=SessionType(request.domain.value) if request.domain.value in SessionType.__members__ else SessionType.MIXED,
            context={
                "occasion":   request.occasion,
                "season":     request.season,
                "budget_max": request.budget_max,
                "budget_min": request.budget_min,
            },
            model_version=_ENGINE_VERSION,
        )
        self._session.add(session_obj)
        await self._session.flush()

        for item in items:
            self._session.add(Recommendation(
                session_id=session_obj.id,
                product_id=item.product.id,
                score=item.score,
                cf_score=item.cf_score,
                cb_score=item.cb_score,
                profile_score=item.profile_score,
                position=item.position,
                reason_code=item.reason_code,
                explanation=item.explanation,
            ))

        return session_obj.id

    # ── Conversion helpers ────────────────────────────────────────────────────

    @staticmethod
    def _matches_domain(product: Product, domain: str) -> bool:
        """Check if a product belongs to the requested domain via category slug."""
        slug = (product.category.slug if product.category else "").lower()
        domain_prefixes = {
            "makeup":      ("makeup", "cosmetic", "foundation", "lipstick", "blush"),
            "skincare":    ("skincare", "serum", "moisturis", "cleanser", "toner", "sunscreen"),
            "haircare":    ("hair",),
            "fragrance":   ("fragrance", "perfume", "eau-de"),
            "fashion":     ("fashion", "clothing", "dress", "top", "trouser"),
            "accessories": ("accessor", "jewel", "bag"),
        }
        return any(slug.startswith(p) for p in domain_prefixes.get(domain, ()))

    @staticmethod
    def _to_product_list_out(product: Product) -> ProductListOut:
        images = product.image_urls or []
        return ProductListOut(
            id=product.id,
            sku=product.sku,
            name=product.name,
            brand_name=product.brand.name if product.brand else "",
            brand_slug=product.brand.slug if product.brand else "",
            category=product.category.name if product.category else "",
            price=float(product.price),
            currency=product.currency,
            image_url=images[0] if images else None,
            avg_rating=product.avg_rating,
            review_count=product.review_count,
            is_new_arrival=product.is_new_arrival,
            is_trending=product.is_trending,
            in_stock=product.in_stock,
        )

    @staticmethod
    def _empty_response(request: RecommendationRequest) -> RecommendationResponse:
        import uuid
        return RecommendationResponse(
            session_id=uuid.uuid4(),
            domain=request.domain.value,
            items=[],
            total=0,
            model_version=_ENGINE_VERSION,
            cold_start=True,
        )

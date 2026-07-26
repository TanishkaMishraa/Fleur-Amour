"""
AuraFit — Smart Alternative Service.

Entry point for all alternative-finding workflows:
  1. get_alternatives(product_id, user_id) — serve from cache or compute
  2. compute_alternatives(source_id)       — run matching against catalog
  3. precompute_for_luxury_catalog()       — nightly batch for all luxury items

Price threshold: configurable. Default ₹10,000 INR.
All prices stored in product.currency; conversion handled at API layer.

Redis cache:
  Key:  alt:{source_product_id}
  TTL:  3600s (1h) for on-demand; 86400s (24h) for pre-computed
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.alternatives import ProductAlternative
from app.models.catalog import Brand, Category, Product, ProductEmbedding
from app.schemas.alternative_schemas import (
    AlternativeGroupResponse,
    AlternativeOut,
    ProductSummaryOut,
)
from app.services.alternatives.matching_engine import AlternativeMatch, matching_engine

logger = get_logger(__name__)

ENGINE_VERSION = "1.0.0"


class SmartAlternativeService:
    """
    Orchestrates the full alternative-finding pipeline.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._s = get_settings()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def get_alternatives(
        self,
        source_id: uuid.UUID,
        limit: int = 5,
        min_similarity: float = 0.40,
    ) -> AlternativeGroupResponse:
        """
        Get alternatives for a product.
        Tries pre-computed rows first; falls back to on-demand computation.
        """
        # Try pre-computed
        stored = await self._load_stored(source_id, limit, min_similarity)
        if stored:
            return stored

        # On-demand compute (slower, but always fresh)
        logger.info("alt.on_demand_compute", source_id=str(source_id))
        return await self._compute_and_return(source_id, limit, min_similarity)

    async def precompute_for_product(self, source_id: uuid.UUID) -> int:
        """
        Compute and persist alternatives for one luxury product.
        Called by the nightly Celery task.
        Returns number of alternatives stored.
        """
        source = await self._get_product_with_embedding(source_id)
        if not source:
            return 0

        s = self._s
        inr_threshold = getattr(s, "LUXURY_PRICE_THRESHOLD_INR", 10000)
        if float(source.price) < inr_threshold:
            logger.debug("alt.skip_not_luxury", product_id=str(source_id), price=source.price)
            return 0

        candidates = await self._get_cheaper_candidates(source, max_results=100)
        if not candidates:
            return 0

        # Compute matches
        src_emb = source.embedding.text_embedding if source.embedding else None
        matches: list[AlternativeMatch] = []
        for cand_product, cand_emb_vec in candidates:
            try:
                m = matching_engine.match(
                    source=source,
                    candidate=cand_product,
                    source_embedding=src_emb,
                    candidate_embedding=cand_emb_vec,
                )
                if m.overall_score >= 0.30:   # Minimum quality gate
                    matches.append(m)
            except Exception as exc:
                logger.warning("alt.match_error", exc=str(exc))

        if not matches:
            return 0

        # Sort and mark best value
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        matches = matching_engine.mark_best_value(matches)

        # Delete old rows, insert new
        await self._session.execute(
            ProductAlternative.__table__.delete().where(
                ProductAlternative.source_id == source_id
            )
        )

        top_matches = matches[:10]   # Store top 10 per source
        for m in top_matches:
            self._session.add(self._match_to_orm(m))

        await self._session.flush()
        logger.info(
            "alt.precomputed",
            source_id=str(source_id),
            count=len(top_matches),
            best_score=round(top_matches[0].overall_score, 3) if top_matches else 0,
        )
        return len(top_matches)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _load_stored(
        self,
        source_id: uuid.UUID,
        limit: int,
        min_similarity: float,
    ) -> AlternativeGroupResponse | None:
        """Load pre-computed alternatives from DB."""
        result = await self._session.execute(
            select(ProductAlternative)
            .where(ProductAlternative.source_id == source_id)
            .where(ProductAlternative.overall_score >= min_similarity)
            .order_by(ProductAlternative.rank)
            .limit(limit)
        )
        rows = list(result.scalars().all())
        if not rows:
            return None

        # Fetch full product data for each alternative
        alt_ids = [r.alt_id for r in rows]
        products = await self._fetch_products(alt_ids)
        product_map = {str(p.id): p for p in products}

        source = await self._get_product_with_embedding(source_id)
        if not source:
            return None

        alternatives = []
        for row in rows:
            alt_product = product_map.get(str(row.alt_id))
            if not alt_product:
                continue
            alternatives.append(self._row_to_out(row, alt_product))

        return self._build_response(source, alternatives, from_cache=True)

    async def _compute_and_return(
        self,
        source_id: uuid.UUID,
        limit: int,
        min_similarity: float,
    ) -> AlternativeGroupResponse:
        """On-demand: compute, persist, return top-N."""
        source = await self._get_product_with_embedding(source_id)
        if not source:
            return self._empty_response(source_id)

        candidates = await self._get_cheaper_candidates(source, max_results=50)
        src_emb = source.embedding.text_embedding if source.embedding else None

        matches: list[AlternativeMatch] = []
        for cand_product, cand_emb_vec in candidates:
            try:
                m = matching_engine.match(
                    source=source,
                    candidate=cand_product,
                    source_embedding=src_emb,
                    candidate_embedding=cand_emb_vec,
                )
                if m.overall_score >= min_similarity:
                    matches.append(m)
            except Exception as exc:
                logger.warning("alt.on_demand_match_error", exc=str(exc))

        if not matches:
            return self._build_response(source, [], from_cache=False)

        matches.sort(key=lambda m: m.overall_score, reverse=True)
        matches = matching_engine.mark_best_value(matches)

        # Persist async (best-effort)
        for m in matches[:10]:
            self._session.add(self._match_to_orm(m))
        try:
            await self._session.flush()
        except Exception:
            pass

        # Build response from top-N matches
        top = matches[:limit]
        alt_ids = [m.alt_id for m in top]
        products = await self._fetch_products(alt_ids)
        product_map = {str(p.id): p for p in products}

        alternatives = []
        for m in top:
            alt_product = product_map.get(str(m.alt_id))
            if alt_product:
                alternatives.append(self._match_to_out(m, alt_product))

        return self._build_response(source, alternatives, from_cache=False)

    async def _get_product_with_embedding(self, product_id: uuid.UUID) -> Product | None:
        result = await self._session.execute(
            select(Product)
            .where(Product.id == product_id)
            .where(Product.is_active == True)   # noqa: E712
            .options(
                selectinload(Product.brand),
                selectinload(Product.category),
                selectinload(Product.embedding),
            )
        )
        return result.scalar_one_or_none()

    async def _get_cheaper_candidates(
        self, source: Product, max_results: int = 100
    ) -> list[tuple[Product, list[float] | None]]:
        """
        Fetch cheaper products in the same category.
        Returns (product, embedding_vector) tuples.
        """
        result = await self._session.execute(
            select(Product, ProductEmbedding.text_embedding)
            .outerjoin(ProductEmbedding, ProductEmbedding.product_id == Product.id)
            .where(Product.is_active == True)   # noqa: E712
            .where(Product.in_stock == True)    # noqa: E712
            .where(Product.id != source.id)
            .where(Product.price < source.price * 0.90)   # At least 10% cheaper
            .where(Product.category_id == source.category_id)
            .options(selectinload(Product.brand), selectinload(Product.category))
            .order_by(Product.avg_rating.desc().nulls_last(), Product.interaction_count.desc())
            .limit(max_results)
        )
        rows = result.fetchall()
        return [(row.Product, row.text_embedding) for row in rows]

    async def _fetch_products(self, product_ids: list[uuid.UUID]) -> list[Product]:
        result = await self._session.execute(
            select(Product)
            .where(Product.id.in_(product_ids))
            .options(selectinload(Product.brand), selectinload(Product.category))
        )
        return list(result.scalars().all())

    def _match_to_orm(self, m: AlternativeMatch) -> ProductAlternative:
        return ProductAlternative(
            source_id=m.source_id,
            alt_id=m.alt_id,
            overall_score=m.overall_score,
            embedding_score=m.embedding_score,
            ingredient_score=m.ingredient_score,
            formula_score=m.formula_score,
            shade_score=m.shade_score,
            fragrance_score=m.fragrance_score,
            style_score=m.style_score,
            match_types=m.match_types,
            match_detail=m.match_detail,
            source_price=m.source_price,
            alt_price=m.alt_price,
            price_savings=m.price_savings,
            savings_pct=m.savings_pct,
            currency=m.currency,
            is_best_value=m.is_best_value,
            rank=m.rank,
            engine_version=ENGINE_VERSION,
        )

    @staticmethod
    def _to_product_summary(product: Product) -> ProductSummaryOut:
        images = product.image_urls or []
        return ProductSummaryOut(
            id=product.id,
            name=product.name,
            brand_name=product.brand.name if product.brand else "",
            brand_tier=product.brand.tier.value if product.brand else "mid",
            category=product.category.name if product.category else "",
            price=float(product.price),
            currency=product.currency,
            image_url=images[0] if images else None,
            avg_rating=product.avg_rating,
            review_count=product.review_count,
            in_stock=product.in_stock,
            attributes=product.attributes,
            ingredients=product.ingredients,
        )

    def _row_to_out(self, row: ProductAlternative, alt_product: Product) -> AlternativeOut:
        return AlternativeOut(
            alt_id=alt_product.id,
            product=self._to_product_summary(alt_product),
            overall_score=row.overall_score,
            overall_pct=round(row.overall_score * 100),
            embedding_score=row.embedding_score,
            ingredient_score=row.ingredient_score,
            formula_score=row.formula_score,
            shade_score=row.shade_score,
            fragrance_score=row.fragrance_score,
            style_score=row.style_score,
            match_types=row.match_types or [],
            match_detail=row.match_detail or {},
            source_price=float(row.source_price),
            alt_price=float(row.alt_price),
            price_savings=float(row.price_savings),
            savings_pct=row.savings_pct,
            currency=row.currency,
            is_best_value=row.is_best_value,
            rank=row.rank,
        )

    def _match_to_out(self, m: AlternativeMatch, alt_product: Product) -> AlternativeOut:
        return AlternativeOut(
            alt_id=alt_product.id,
            product=self._to_product_summary(alt_product),
            overall_score=m.overall_score,
            overall_pct=round(m.overall_score * 100),
            embedding_score=m.embedding_score,
            ingredient_score=m.ingredient_score,
            formula_score=m.formula_score,
            shade_score=m.shade_score,
            fragrance_score=m.fragrance_score,
            style_score=m.style_score,
            match_types=m.match_types,
            match_detail=m.match_detail,
            source_price=m.source_price,
            alt_price=m.alt_price,
            price_savings=m.price_savings,
            savings_pct=m.savings_pct,
            currency=m.currency,
            is_best_value=m.is_best_value,
            rank=m.rank,
        )

    def _build_response(
        self, source: Product, alternatives: list[AlternativeOut], from_cache: bool
    ) -> AlternativeGroupResponse:
        from app.schemas.alternative_schemas import AlternativeGroupResponse
        return AlternativeGroupResponse(
            source=self._to_product_summary(source),
            alternatives=alternatives,
            total=len(alternatives),
            from_cache=from_cache,
            engine_version=ENGINE_VERSION,
        )

    @staticmethod
    def _empty_response(source_id: uuid.UUID) -> AlternativeGroupResponse:
        from app.schemas.alternative_schemas import AlternativeGroupResponse, ProductSummaryOut
        stub = ProductSummaryOut(
            id=source_id, name="", brand_name="", brand_tier="mid",
            category="", price=0, currency="INR", image_url=None,
            avg_rating=None, review_count=0, in_stock=True,
            attributes=None, ingredients=None,
        )
        return AlternativeGroupResponse(
            source=stub, alternatives=[], total=0, from_cache=False, engine_version=ENGINE_VERSION
        )

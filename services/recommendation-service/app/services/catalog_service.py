"""
AuraFit — Product Catalog Service.
Search, filtering, similarity, and product detail retrieval.
Wraps all DB access for the catalog domain.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.catalog import (
    Brand, Category, Product, ProductEmbedding, Review, UserProductInteraction,
)
from app.schemas.recommendation_schemas import (
    PaginatedProducts, ProductListOut, ProductOut, ProductSearchRequest, SortOrder,
)
from app.services.algorithms.collaborative_filter import get_cf_model
from app.services.algorithms.content_based_filter import get_cb_filter

logger = get_logger(__name__)


def _to_list_out(product: Product) -> ProductListOut:
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


def _to_full_out(product: Product) -> ProductOut:
    from app.schemas.recommendation_schemas import BrandOut, CategoryOut
    brand = BrandOut(
        id=product.brand.id, name=product.brand.name,
        slug=product.brand.slug, tier=product.brand.tier.value,
        logo_url=product.brand.logo_url,
    ) if product.brand else None
    category = CategoryOut(
        id=product.category.id, name=product.category.name,
        slug=product.category.slug, icon=product.category.icon,
        parent_id=product.category.parent_id,
    ) if product.category else None
    return ProductOut(
        id=product.id, sku=product.sku, name=product.name,
        brand=brand, category=category,
        description=product.description,
        price=float(product.price), currency=product.currency,
        image_urls=product.image_urls,
        attributes=product.attributes,
        avg_rating=product.avg_rating, review_count=product.review_count,
        is_new_arrival=product.is_new_arrival, is_trending=product.is_trending,
        in_stock=product.in_stock,
        style_tags=product.style_tags, season_tags=product.season_tags,
        concern_tags=product.concern_tags,
    )


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Product search ────────────────────────────────────────────────────────

    async def search(self, req: ProductSearchRequest) -> PaginatedProducts:
        query = (
            select(Product)
            .where(Product.is_active == True)   # noqa: E712
            .options(selectinload(Product.brand), selectinload(Product.category))
        )

        if req.in_stock_only:
            query = query.where(Product.in_stock == True)  # noqa: E712

        if req.q:
            query = query.where(
                or_(
                    Product.name.ilike(f"%{req.q}%"),
                    Product.description.ilike(f"%{req.q}%"),
                )
            )

        if req.category_slug:
            query = query.join(Category, Product.category_id == Category.id).where(
                Category.slug == req.category_slug
            )

        if req.brand_slug:
            query = query.join(Brand, Product.brand_id == Brand.id).where(
                Brand.slug == req.brand_slug
            )

        if req.price_min is not None:
            query = query.where(Product.price >= req.price_min)
        if req.price_max is not None:
            query = query.where(Product.price <= req.price_max)

        if req.skin_tone:
            query = query.where(
                Product.compatible_skin_tones.contains([req.skin_tone])
            )
        if req.undertone:
            query = query.where(
                Product.compatible_undertones.contains([req.undertone])
            )
        if req.concerns:
            for concern in req.concerns:
                query = query.where(Product.concern_tags.contains([concern]))
        if req.style_tags:
            for tag in req.style_tags:
                query = query.where(Product.style_tags.contains([tag]))

        # Sort
        sort_map = {
            SortOrder.PRICE_ASC:   Product.price.asc(),
            SortOrder.PRICE_DESC:  Product.price.desc(),
            SortOrder.RATING:      Product.avg_rating.desc().nulls_last(),
            SortOrder.NEW_ARRIVALS:Product.created_at.desc(),
            SortOrder.TRENDING:    Product.interaction_count.desc(),
            SortOrder.RELEVANCE:   Product.interaction_count.desc(),
        }
        query = query.order_by(sort_map.get(req.sort, Product.interaction_count.desc()))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        # Paginate
        offset = (req.page - 1) * req.per_page
        query  = query.offset(offset).limit(req.per_page)
        rows   = (await self._session.execute(query)).scalars().all()

        return PaginatedProducts(
            items=[_to_list_out(p) for p in rows],
            total=total,
            page=req.page,
            per_page=req.per_page,
            total_pages=max(1, (total + req.per_page - 1) // req.per_page),
        )

    # ── Product detail ────────────────────────────────────────────────────────

    async def get_product(self, product_id: uuid.UUID) -> ProductOut | None:
        result = await self._session.execute(
            select(Product)
            .where(Product.id == product_id)
            .where(Product.is_active == True)  # noqa: E712
            .options(selectinload(Product.brand), selectinload(Product.category))
        )
        product = result.scalar_one_or_none()
        return _to_full_out(product) if product else None

    # ── Similar products ──────────────────────────────────────────────────────

    async def get_similar_products(
        self, product_id: uuid.UUID, limit: int = 10
    ) -> list[ProductListOut]:
        """
        Find similar products via two methods, merged:
          1. Content-based ANN (pgvector cosine on SBERT embeddings)
          2. CF item similarity (item factors dot product)
        """
        cb_results = await self._similar_by_embedding(product_id, n=limit)
        cf_results = self._similar_by_cf(str(product_id), n=limit)

        # Merge: prefer CB score; supplement with CF
        merged: dict[str, float] = {}
        for pid, score in cb_results:
            merged[pid] = score
        for pid, score in cf_results:
            if pid not in merged:
                merged[pid] = score * 0.8   # Slightly down-weight CF

        top_ids = sorted(merged, key=lambda k: merged[k], reverse=True)[:limit]
        if not top_ids:
            return []

        result = await self._session.execute(
            select(Product)
            .where(Product.id.in_([uuid.UUID(pid) for pid in top_ids]))
            .where(Product.is_active == True)   # noqa: E712
            .options(selectinload(Product.brand), selectinload(Product.category))
        )
        products = {str(p.id): p for p in result.scalars().all()}
        return [_to_list_out(products[pid]) for pid in top_ids if pid in products]

    async def _similar_by_embedding(self, product_id: uuid.UUID, n: int) -> list[tuple[str, float]]:
        """Get product's own embedding, then find nearest neighbours."""
        emb_result = await self._session.execute(
            select(ProductEmbedding.text_embedding)
            .where(ProductEmbedding.product_id == product_id)
        )
        row = emb_result.scalar_one_or_none()
        if row is None:
            return []
        cb = get_cb_filter()
        return await cb.find_similar_by_embedding(
            self._session, query_embedding=row, n=n, exclude_ids=[product_id]
        )

    def _similar_by_cf(self, product_id: str, n: int) -> list[tuple[str, float]]:
        return get_cf_model().get_similar_products(product_id, n=n)

    # ── Categories & brands ───────────────────────────────────────────────────

    async def list_categories(self, parent_id: uuid.UUID | None = None) -> list[Category]:
        query = select(Category).where(Category.is_active == True)  # noqa: E712
        if parent_id:
            query = query.where(Category.parent_id == parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))
        query = query.order_by(Category.sort_order)
        return list((await self._session.execute(query)).scalars().all())

    async def list_brands(self, tier: str | None = None) -> list[Brand]:
        query = select(Brand).where(Brand.is_active == True)  # noqa: E712
        if tier:
            query = query.where(Brand.tier == tier)
        return list((await self._session.execute(query)).scalars().all())

    # ── Interaction recording ─────────────────────────────────────────────────

    async def record_interaction(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        interaction_type: str,
        rating: int | None = None,
        session_context: dict | None = None,
    ) -> None:
        """Write interaction + update product counter."""
        _CONFIDENCE = {
            "purchase": 5.0, "save": 3.0, "like": 2.0,
            "try_on": 2.0, "review": 2.5, "view": 0.5, "dislike": -1.0,
        }
        interaction = UserProductInteraction(
            user_id=user_id,
            product_id=product_id,
            interaction_type=interaction_type,
            rating=rating,
            confidence_value=_CONFIDENCE.get(interaction_type, 1.0),
            session_context=session_context,
        )
        self._session.add(interaction)

        # Increment counter (non-blocking; triggers nightly embedding rebuild)
        await self._session.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(interaction_count=Product.interaction_count + 1)
        )
        await self._session.flush()
        logger.info(
            "catalog.interaction_recorded",
            user_id=str(user_id), product_id=str(product_id), type=interaction_type,
        )

    # ── Reviews ───────────────────────────────────────────────────────────────

    async def get_reviews(self, product_id: uuid.UUID, limit: int = 20) -> list[Review]:
        result = await self._session.execute(
            select(Review)
            .where(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

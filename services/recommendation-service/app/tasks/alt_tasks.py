"""
AuraFit — Smart Alternative Engine Celery tasks.

precompute_luxury_alternatives:
  Nightly task (03:30 UTC via Celery Beat).
  Scans all active products above LUXURY_PRICE_THRESHOLD_INR.
  Computes and persists alternatives for each luxury product.
  Also flags is_best_value on the best score/price combo.

recompute_alternatives_for_product:
  On-demand task triggered when:
    - A product's price changes
    - A new product is added to the luxury catalog
    - Embeddings are refreshed for a product
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.alt_tasks.precompute_luxury_alternatives",
    queue="ai.low",
    time_limit=7200,   # 2h max
    soft_time_limit=6000,
)
def precompute_luxury_alternatives() -> dict:
    """
    Nightly: compute alternatives for all luxury products (price ≥ ₹10,000).
    Runs at 03:30 UTC after embedding refresh completes.
    """
    import asyncio
    from app.core.config import get_settings
    from app.db.session import create_async_session

    settings = get_settings()
    threshold = getattr(settings, "LUXURY_PRICE_THRESHOLD_INR", 10000)

    logger.info(f"[alt] precompute_luxury_alternatives start, threshold=₹{threshold}")

    async def _run() -> dict:
        from sqlalchemy import select
        from app.models.catalog import Product
        from app.services.alternatives.alternative_service import SmartAlternativeService

        async with create_async_session() as session:
            # Fetch all luxury product IDs
            result = await session.execute(
                select(Product.id)
                .where(Product.is_active == True)   # noqa: E712
                .where(Product.in_stock == True)    # noqa: E712
                .where(Product.price >= threshold)
                .order_by(Product.interaction_count.desc())  # Most popular first
            )
            luxury_ids = [r[0] for r in result.fetchall()]
            logger.info(f"[alt] found {len(luxury_ids)} luxury products")

        total_computed = 0
        errors = 0
        for product_id in luxury_ids:
            try:
                async with create_async_session() as session:
                    svc = SmartAlternativeService(session)
                    count = await svc.precompute_for_product(product_id)
                    await session.commit()
                    total_computed += count
            except Exception as exc:
                logger.warning(f"[alt] error for {product_id}: {exc}")
                errors += 1

        logger.info(f"[alt] precompute complete: {total_computed} alternatives, {errors} errors")
        return {
            "status": "ok",
            "luxury_products": len(luxury_ids),
            "alternatives_computed": total_computed,
            "errors": errors,
        }

    return asyncio.run(_run())


@shared_task(
    name="app.tasks.alt_tasks.recompute_alternatives_for_product",
    queue="recommendations",
    max_retries=2,
    default_retry_delay=60,
)
def recompute_alternatives_for_product(*, product_id: str) -> dict:
    """
    On-demand: recompute alternatives for one product.
    Triggered when product price changes or new product is added.
    """
    import asyncio
    from app.db.session import create_async_session
    from app.services.alternatives.alternative_service import SmartAlternativeService
    import uuid

    logger.info(f"[alt] recompute product={product_id}")

    async def _run() -> int:
        async with create_async_session() as session:
            svc = SmartAlternativeService(session)
            count = await svc.precompute_for_product(uuid.UUID(product_id))
            await session.commit()
            return count

    count = asyncio.run(_run())
    return {"status": "ok", "product_id": product_id, "alternatives": count}

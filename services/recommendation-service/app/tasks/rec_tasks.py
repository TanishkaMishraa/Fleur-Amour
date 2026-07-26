"""
AuraFit — Recommendation Service Celery tasks.

Task topology (Stage 0 queue routing):
  ai.low:         rebuild_cf_model, refresh_product_embeddings
  recommendations:rebuild_user_embedding, refresh_all_user_embeddings
  maintenance:    recompute_trending, update_product_counters

Beat schedule:
  02:00 UTC daily  → rebuild_cf_model
  06:00 UTC daily  → refresh_product_embeddings (new/updated products)
  Every 6h         → recompute_trending
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.rec_tasks.rebuild_cf_model",
    queue="ai.low",
    time_limit=3600,   # 1h max — training can be slow on large datasets
)
def rebuild_cf_model() -> dict:
    """
    Nightly ALS model rebuild.
    Reads last 90 days of interactions, trains ALS, saves model to disk.
    """
    import asyncio
    import pandas as pd
    from app.db.session import get_sync_session

    logger.info("[rec] rebuild_cf_model start")

    try:
        # Use synchronous session for Celery (not async)
        with get_sync_session() as session:
            result = session.execute("""
                SELECT
                    user_id::text,
                    product_id::text,
                    SUM(confidence_value) AS confidence
                FROM user_product_interactions
                WHERE created_at > NOW() - INTERVAL '90 days'
                  AND confidence_value > 0
                GROUP BY user_id, product_id
                HAVING SUM(confidence_value) >= 0.5
            """)
            rows = result.fetchall()

        interactions = [
            {"user_id": r[0], "product_id": r[1], "confidence": float(r[2])}
            for r in rows
        ]
        logger.info(f"[rec] training on {len(interactions)} user-product pairs")

        from app.services.algorithms.collaborative_filter import get_cf_model
        model = get_cf_model()
        model.train(interactions)

        return {"status": "ok", "trained_on": len(interactions)}

    except Exception as exc:
        logger.exception(f"[rec] rebuild_cf_model failed: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task(
    name="app.tasks.rec_tasks.refresh_product_embeddings",
    queue="ai.low",
    time_limit=7200,   # 2h for large catalog
)
def refresh_product_embeddings(full_refresh: bool = False) -> dict:
    """
    Recompute SBERT text embeddings for new/updated products.
    full_refresh=True: recompute all products (used after model version upgrade).
    Default: only products without embeddings or updated in last 24h.
    """
    logger.info(f"[rec] refresh_product_embeddings full_refresh={full_refresh}")

    try:
        from app.db.session import get_sync_session
        from app.services.algorithms.content_based_filter import get_cb_filter

        cb = get_cb_filter()

        with get_sync_session() as session:
            if full_refresh:
                query = """
                    SELECT p.id, p.name, p.description, p.ingredients,
                           p.attributes, p.concern_tags,
                           b.name as brand_name
                    FROM products p
                    LEFT JOIN brands b ON p.brand_id = b.id
                    WHERE p.is_active = true
                """
            else:
                query = """
                    SELECT p.id, p.name, p.description, p.ingredients,
                           p.attributes, p.concern_tags,
                           b.name as brand_name
                    FROM products p
                    LEFT JOIN brands b ON p.brand_id = b.id
                    LEFT JOIN product_embeddings pe ON pe.product_id = p.id
                    WHERE p.is_active = true
                      AND (pe.id IS NULL OR p.updated_at > NOW() - INTERVAL '24 hours')
                    LIMIT 10000
                """

            products = session.execute(query).fetchall()
            logger.info(f"[rec] embedding {len(products)} products")

            updated = 0
            for row in products:
                # Build text for embedding
                parts = [row.name]
                if row.brand_name:
                    parts.append(row.brand_name)
                if row.description:
                    parts.append(row.description[:512])
                if row.ingredients:
                    parts.append(f"Ingredients: {row.ingredients[:256]}")
                text = ". ".join(p for p in parts if p)

                embedding = cb.embed_text(text)
                if embedding is None:
                    continue

                # Upsert embedding
                session.execute("""
                    INSERT INTO product_embeddings (id, product_id, text_embedding, model_version, created_at, updated_at)
                    VALUES (uuid_generate_v4(), :pid, :emb, '1.0.0', NOW(), NOW())
                    ON CONFLICT (product_id) DO UPDATE
                      SET text_embedding = EXCLUDED.text_embedding,
                          model_version  = EXCLUDED.model_version,
                          updated_at     = NOW()
                """, {"pid": row.id, "emb": embedding})
                updated += 1

            session.commit()

        logger.info(f"[rec] embeddings updated for {updated} products")
        return {"status": "ok", "updated": updated}

    except Exception as exc:
        logger.exception(f"[rec] refresh_product_embeddings failed: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task(
    name="app.tasks.rec_tasks.rebuild_user_embedding",
    queue="recommendations",
    max_retries=2,
    default_retry_delay=30,
)
def rebuild_user_embedding(*, user_id: str) -> dict:
    """
    Rebuild user preference vector after new interactions.
    Called async (30s countdown) after each interaction record.
    """
    logger.info(f"[rec] rebuild_user_embedding user={user_id}")

    try:
        import asyncio
        from app.db.session import create_async_session
        from app.services.algorithms.content_based_filter import get_cb_filter
        import uuid

        async def _run():
            async with create_async_session() as session:
                cb = get_cb_filter()
                embedding = await cb.rebuild_user_embedding(session, uuid.UUID(user_id))
                await session.commit()
                return embedding is not None

        success = asyncio.run(_run())
        return {"status": "ok" if success else "skipped", "user_id": user_id}

    except Exception as exc:
        logger.exception(f"[rec] rebuild_user_embedding failed user={user_id}: {exc}")
        return {"status": "error", "error": str(exc)}


@shared_task(
    name="app.tasks.rec_tasks.recompute_trending",
    queue="maintenance",
)
def recompute_trending() -> dict:
    """
    Recompute is_trending flag for products based on last 7 days interaction count.
    Products in top 5% of interactions = trending.
    Runs every 6h.
    """
    logger.info("[rec] recompute_trending start")
    try:
        from app.db.session import get_sync_session
        with get_sync_session() as session:
            # Compute 95th percentile of interaction counts in last 7 days
            session.execute("""
                WITH recent_counts AS (
                    SELECT product_id, COUNT(*) as cnt
                    FROM user_product_interactions
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    GROUP BY product_id
                ),
                threshold AS (
                    SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY cnt) as p95
                    FROM recent_counts
                )
                UPDATE products
                SET is_trending = (
                    SELECT COALESCE(rc.cnt, 0) >= t.p95
                    FROM threshold t
                    LEFT JOIN recent_counts rc ON rc.product_id = products.id
                )
                WHERE is_active = true
            """)
            session.commit()
        logger.info("[rec] recompute_trending complete")
        return {"status": "ok"}
    except Exception as exc:
        logger.exception(f"[rec] recompute_trending failed: {exc}")
        return {"status": "error", "error": str(exc)}

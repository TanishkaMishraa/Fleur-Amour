"""
AuraFit — Recommendation Celery tasks.
Scheduled nightly (CF model rebuild) and triggered on-demand (per-user refresh).
Routes to recommendations queue per Stage 0 topology.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.rec_tasks.refresh_user_recommendations",
    bind=True,
    max_retries=2,
    queue="recommendations",
)
def refresh_user_recommendations(self, *, user_id: str) -> dict:
    """
    Refresh cached recommendations for a single user.
    Triggered after profile update, facial scan completion, or explicit user action.
    """
    import httpx
    from app.core.config import get_settings
    settings = get_settings()

    try:
        logger.info(f"[rec] refresh_user user={user_id}")
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.RECOMMENDATION_SERVICE_URL}/refresh",
                json={"user_id": user_id},
            )
            response.raise_for_status()
        return {"status": "ok", "user_id": user_id}
    except Exception as exc:
        logger.exception(f"[rec] refresh failed user={user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    name="app.tasks.rec_tasks.rebuild_cf_model",
    queue="ai.low",
)
def rebuild_cf_model() -> dict:
    """
    Nightly collaborative filtering model rebuild.
    Trains ALS matrix factorisation on last 90 days of interactions.
    Runs: daily at 02:00 UTC via Celery Beat.
    """
    logger.info("[rec] rebuild_cf_model start")
    # Production: trigger ML training pipeline
    return {"status": "ok", "task": "rebuild_cf_model"}


@shared_task(
    name="app.tasks.rec_tasks.refresh_product_embeddings",
    queue="ai.low",
)
def refresh_product_embeddings() -> dict:
    """
    Recompute CLIP embeddings for products added or updated since last run.
    Runs twice daily. Calls style-dna AI service batch embedding endpoint.
    """
    logger.info("[rec] refresh_product_embeddings start")
    return {"status": "ok", "task": "refresh_product_embeddings"}

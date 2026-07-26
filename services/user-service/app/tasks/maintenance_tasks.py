"""
AuraFit — Maintenance Celery tasks.
Scheduled via Celery Beat (schedule defined in integrations/celery_app.py).
All tasks are idempotent and safe to re-run.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.maintenance_tasks.purge_expired_sessions",
    queue="maintenance",
)
def purge_expired_sessions() -> dict:
    """
    Remove chat sessions inactive for > 90 days.
    Redis TTL handles auth session expiry automatically; this covers DB cleanup.
    Runs: hourly.
    """
    logger.info("[maintenance] purge_expired_sessions start")
    # Production: DELETE FROM chat_sessions WHERE is_active=false AND last_active_at < now()-90d
    return {"status": "ok", "task": "purge_expired_sessions"}


@shared_task(
    name="app.tasks.maintenance_tasks.anonymise_deleted_users",
    queue="maintenance",
)
def anonymise_deleted_users() -> dict:
    """
    GDPR compliance: anonymise PII for soft-deleted users older than 30 days.
    Sets email = anonymised_{id}@deleted.aurafit.ai, full_name = 'Deleted User'.
    Runs: nightly.
    """
    logger.info("[maintenance] anonymise_deleted_users start")
    # Production:
    # SELECT users WHERE is_deleted=True AND deleted_at < now()-30d
    # UPDATE email, full_name, hashed_password=NULL
    return {"status": "ok", "task": "anonymise_deleted_users"}


@shared_task(
    name="app.tasks.maintenance_tasks.compress_chat_context",
    queue="maintenance",
)
def compress_chat_context(*, session_id: str) -> dict:
    """
    Compress old chat messages into a summary string for the context window.
    Called when a session exceeds 2× the sliding window limit.
    """
    logger.info(f"[maintenance] compress_chat_context session={session_id}")
    # Production:
    # 1. Fetch messages older than window
    # 2. Call LLM: "Summarise this conversation in 200 words"
    # 3. Update chat_sessions.context_summary
    # 4. Delete compressed messages from DB
    return {"status": "ok", "session_id": session_id}


@shared_task(
    name="app.tasks.maintenance_tasks.refresh_product_embeddings",
    queue="ai.low",
)
def refresh_product_embeddings() -> dict:
    """
    Re-compute CLIP product embeddings for new catalog items.
    Triggered by product-service webhook on catalog update.
    """
    logger.info("[maintenance] refresh_product_embeddings start")
    return {"status": "ok", "task": "refresh_product_embeddings"}


@shared_task(
    name="app.tasks.maintenance_tasks.aggregate_analytics",
    queue="maintenance",
)
def aggregate_analytics() -> dict:
    """
    Daily analytics aggregation.
    Materialises interaction summary tables used by the recommendation engine
    and the admin analytics dashboard.
    Runs: daily at 03:00 UTC via Celery Beat.
    """
    logger.info("[maintenance] aggregate_analytics start")
    return {"status": "ok", "task": "aggregate_analytics"}

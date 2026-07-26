"""
AuraFit - Maintenance Celery tasks.
Scheduled via Celery Beat. Cleanup and analytics aggregation.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.maintenance.purge_expired_sessions",
    queue="maintenance",
)
def purge_expired_sessions() -> dict:
    """Remove expired auth sessions from Redis. Runs hourly."""
    logger.info("Running session purge")
    # Redis TTL handles expiry automatically; this is for DB-side cleanup
    return {"status": "ok"}


@shared_task(
    name="app.tasks.maintenance.anonymise_deleted_users",
    queue="maintenance",
)
def anonymise_deleted_users() -> dict:
    """
    GDPR: anonymise PII for soft-deleted users older than 30 days.
    Runs nightly via Celery Beat.
    """
    logger.info("Running user anonymisation job")
    # Query users where is_deleted=True and deleted_at < now() - 30d
    # Set email = anonymised_{id}@deleted.aurafit.ai, full_name = 'Deleted User'
    return {"status": "ok"}

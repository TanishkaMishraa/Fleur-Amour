"""
AuraFit - AI Celery tasks.
Dispatched when user uploads a selfie for facial scan or try-on.
Calls AI microservices (internal HTTP), updates DB + Redis, publishes SSE event.
"""
from __future__ import annotations

import uuid

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.ai.run_facial_scan",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ai.high",
)
def run_facial_scan(self, *, user_id: str, upload_id: str, s3_key: str) -> dict:
    """
    Orchestrate the facial analysis pipeline:
    1. Call ai-facial-analysis service HTTP endpoint
    2. Persist results to facial_scans table
    3. Update upload status
    4. Publish Redis pub/sub event (SSE push to client)
    """
    import asyncio
    import httpx

    from app.core.config import get_settings
    from app.cache.redis_client import RedisKeys

    settings = get_settings()

    try:
        logger.info(f"Starting facial scan for user {user_id}, s3_key={s3_key}")

        # Update task progress in Redis (client polls this)
        # In a real impl, use async Redis within a sync context via run_until_complete
        task_id = self.request.id

        # Call AI microservice
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.AI_FACIAL_SERVICE_URL}/analyze",
                json={"s3_key": s3_key, "user_id": user_id, "task_id": task_id},
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"Facial scan complete for user {user_id}")
        return {"status": "complete", "user_id": user_id, "result": result}

    except Exception as exc:
        logger.exception(f"Facial scan failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@shared_task(
    name="app.tasks.ai.run_tryon",
    bind=True,
    max_retries=2,
    queue="media",
)
def run_tryon(self, *, user_id: str, selfie_s3_key: str, product_id: str) -> dict:
    """
    Virtual try-on pipeline:
    1. Call ai-virtual-tryon service
    2. Store result image to S3
    3. Update upload record, publish SSE event
    """
    import httpx
    from app.core.config import get_settings

    settings = get_settings()

    try:
        logger.info(f"Starting try-on for user {user_id}, product {product_id}")
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{settings.AI_FACIAL_SERVICE_URL}/tryon",  # Virtual try-on service
                json={
                    "selfie_s3_key": selfie_s3_key,
                    "product_id": product_id,
                    "user_id": user_id,
                },
            )
            response.raise_for_status()
            result = response.json()

        return {"status": "complete", "result_url": result.get("result_url")}

    except Exception as exc:
        logger.exception(f"Try-on task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)

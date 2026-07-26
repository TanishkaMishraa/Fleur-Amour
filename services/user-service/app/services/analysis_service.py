"""
AuraFit — Analysis service layer.
Facial scan dispatch, task status polling, scan history retrieval.
Virtual try-on dispatch.
All AI work is async (Celery tasks). This layer manages state and dispatch only.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, cache_get, get_redis
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import FacialScan
from app.repositories.profile_repository import FacialScanRepository
from app.repositories.user_repository import UploadRepository

logger = get_logger(__name__)


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._scan_repo = FacialScanRepository(session)
        self._upload_repo = UploadRepository(session)

    async def initiate_facial_scan(
        self,
        *,
        user_id: uuid.UUID,
        s3_key: str,
        upload_id: str,
    ) -> dict:
        """
        Create a FacialScan record and dispatch the AI task.
        Returns task metadata for client polling.
        """
        from app.tasks.ai_tasks import run_facial_scan

        # Create placeholder scan record (results filled in by Celery worker)
        scan = await self._scan_repo.create(
            user_id=user_id,
            storage_path=s3_key,
            is_active=False,   # Not active until pipeline completes successfully
        )

        task = run_facial_scan.delay(
            user_id=str(user_id),
            scan_id=str(scan.id),
            s3_key=s3_key,
            upload_id=upload_id,
        )

        # Write initial status to Redis for fast polling
        r = get_redis()
        await r.setex(RedisKeys.task_status(task.id), 86400, "PENDING")

        logger.info(
            "aurafit.analysis.scan_dispatched",
            user_id=str(user_id),
            scan_id=str(scan.id),
            task_id=task.id,
        )
        return {"task_id": task.id, "status": "PENDING", "progress": 0}

    async def get_task_status(self, task_id: str) -> dict:
        """
        Poll Redis for task status. Falls back to Celery result backend if not in Redis.
        Progress is stored as JSON: {"step": "...", "progress": 0-100}.
        """
        import json as _json

        r = get_redis()
        status = await r.get(RedisKeys.task_status(task_id))
        progress_raw = await r.get(RedisKeys.task_progress(task_id))
        result_raw = await cache_get(RedisKeys.task_result(task_id))

        progress: int | None = None
        step: str | None = None
        if progress_raw:
            try:
                parsed = _json.loads(progress_raw)
                progress = parsed.get("progress")
                step = parsed.get("step")
            except (ValueError, TypeError):
                # Backward-compat: progress_raw might be a bare integer string
                try:
                    progress = int(progress_raw)
                except (ValueError, TypeError):
                    progress = None

        error: str | None = None
        if isinstance(result_raw, dict) and result_raw.get("success") is False:
            error = result_raw.get("error_message")

        return {
            "task_id": task_id,
            "status": status or "UNKNOWN",
            "progress": progress,
            "step": step,
            "result": result_raw,
            "error": error,
        }

    async def list_scans(self, user_id: uuid.UUID) -> list[FacialScan]:
        return await self._scan_repo.list_by_user(user_id)

    async def get_scan_by_id(self, user_id: uuid.UUID, scan_id: uuid.UUID) -> FacialScan:
        """
        Fetch a single facial scan by ID, scoped to the requesting user.
        Raises NotFoundError if it doesn't exist or belongs to another user.
        """
        scan = await self._scan_repo.get_by_id(scan_id)
        if scan is None or scan.user_id != user_id:
            raise NotFoundError(f"Facial scan {scan_id} not found")
        return scan

    async def get_latest_scan(self, user_id: uuid.UUID) -> FacialScan | None:
        # Try Redis cache first
        cached = await cache_get(RedisKeys.latest_scan(str(user_id)))
        if cached:
            # Return from cache hit (deserialised scan dict — caller must handle)
            pass  # Full ORM object needed; fall through to DB

        return await self._scan_repo.get_latest_active(user_id)

    async def initiate_tryon(
        self,
        *,
        user_id: uuid.UUID,
        selfie_s3_key: str,
        product_id: uuid.UUID,
    ) -> dict:
        """Dispatch virtual try-on Celery task (media queue, GPU worker)."""
        from app.tasks.ai_tasks import run_tryon

        task = run_tryon.delay(
            user_id=str(user_id),
            selfie_s3_key=selfie_s3_key,
            product_id=str(product_id),
        )

        r = get_redis()
        await r.setex(RedisKeys.task_status(task.id), 86400, "PENDING")

        logger.info(
            "aurafit.analysis.tryon_dispatched",
            user_id=str(user_id),
            task_id=task.id,
        )
        return {"task_id": task.id, "status": "PENDING", "progress": 0}

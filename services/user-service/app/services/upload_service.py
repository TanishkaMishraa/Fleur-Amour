"""
AuraFit — S3 presigned upload service.
Generates presigned PUT URLs. Confirms upload and dispatches Celery tasks.
Binary data NEVER passes through this service — only S3 key references.
"""
from __future__ import annotations

import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError, UpstreamError, ValidationError
from app.core.logging import get_logger
from app.models.image import Upload, UploadPurpose, UploadStatus
from app.repositories.user_repository import UploadRepository

logger = get_logger(__name__)

_ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
_EXT_MAP = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class UploadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._upload_repo = UploadRepository(session)
        self._settings = get_settings()

    def _s3_client(self):
        return boto3.client(
            "s3",
            region_name=self._settings.AWS_REGION,
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY or None,
        )

    def _build_s3_key(
        self, user_id: uuid.UUID, purpose: str, file_type: str
    ) -> str:
        ext = _EXT_MAP.get(file_type, "jpg")
        uid = uuid.uuid4()
        return f"raw/{user_id}/{purpose}/{uid}.{ext}"

    async def generate_presigned_url(
        self,
        *,
        user_id: uuid.UUID,
        file_type: str,
        size_bytes: int,
        purpose: str,
    ) -> dict:
        """
        Generate a presigned S3 PUT URL and create an Upload record.
        Returns: upload_url, s3_key, upload_id, expires_in
        """
        if file_type not in _ALLOWED_MIME_TYPES:
            raise ValidationError(f"Unsupported file type: {file_type}")

        s3_key = self._build_s3_key(user_id, purpose, file_type)

        try:
            s3 = self._s3_client()
            presigned_url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._settings.S3_UPLOADS_BUCKET,
                    "Key": s3_key,
                    "ContentType": file_type,
                    "ContentLength": size_bytes,
                },
                ExpiresIn=self._settings.PRESIGNED_URL_EXPIRE_SECONDS,
                HttpMethod="PUT",
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("aurafit.upload.presign_failed", error=str(exc))
            raise UpstreamError("Failed to generate upload URL")

        upload = await self._upload_repo.create(
            user_id=user_id,
            purpose=UploadPurpose(purpose),
            status=UploadStatus.PENDING,
            s3_key=s3_key,
            s3_bucket=self._settings.S3_UPLOADS_BUCKET,
            content_type=file_type,
            size_bytes=size_bytes,
        )

        logger.info(
            "aurafit.upload.presign_created",
            upload_id=str(upload.id),
            purpose=purpose,
            user_id=str(user_id),
        )
        return {
            "upload_url": presigned_url,
            "s3_key": s3_key,
            "upload_id": str(upload.id),
            "expires_in": self._settings.PRESIGNED_URL_EXPIRE_SECONDS,
        }

    async def confirm_upload(
        self,
        *,
        upload_id: str,
        user_id: uuid.UUID,
        s3_key: str,
        purpose: str,
    ) -> dict:
        """
        Mark upload as received and dispatch the appropriate processing task.
        Returns task_id for client polling.
        """
        upload = await self._upload_repo.get_by_id(uuid.UUID(upload_id))
        if not upload or upload.user_id != user_id:
            raise NotFoundError("Upload record not found")
        if upload.s3_key != s3_key:
            raise ValidationError("s3_key does not match upload record")
        if upload.status != UploadStatus.PENDING:
            raise ValidationError(f"Upload already in status: {upload.status}")

        # Update to UPLOADED
        await self._upload_repo.update(upload, status=UploadStatus.PROCESSING)

        # Dispatch correct task based on purpose
        task_id = await self._dispatch_task(upload, purpose)

        await self._upload_repo.update(upload, celery_task_id=task_id)

        logger.info(
            "aurafit.upload.confirmed",
            upload_id=upload_id,
            task_id=task_id,
            purpose=purpose,
        )
        return {
            "upload_id": upload_id,
            "task_id": task_id,
            "status": "PENDING",
        }

    async def _dispatch_task(self, upload: Upload, purpose: str) -> str:
        """Route to the appropriate Celery task by upload purpose."""
        from app.tasks.ai_tasks import run_facial_scan, run_tryon

        if purpose == "facial_scan":
            task = run_facial_scan.delay(
                user_id=str(upload.user_id),
                scan_id=None,
                s3_key=upload.s3_key,
                upload_id=str(upload.id),
            )
        elif purpose == "virtual_tryon":
            task = run_tryon.delay(
                user_id=str(upload.user_id),
                selfie_s3_key=upload.s3_key,
                product_id=None,
            )
        else:
            # avatar and wardrobe_item just resize/optimise
            from app.tasks.ai_tasks import process_image_upload
            task = process_image_upload.delay(
                user_id=str(upload.user_id),
                s3_key=upload.s3_key,
                purpose=purpose,
                upload_id=str(upload.id),
            )

        return task.id

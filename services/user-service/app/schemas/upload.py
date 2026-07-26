"""
AuraFit — Upload presign schemas.
Covers the two-step direct-to-S3 upload flow from Stage 0.
Step 1: request presigned PUT URL.
Step 2: confirm upload and dispatch Celery task.
"""
from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.base import AuraFitSchema

_ALLOWED_PURPOSES = frozenset({"facial_scan", "avatar", "wardrobe_item", "virtual_tryon"})
_ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
_MAX_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB


class PresignRequest(AuraFitSchema):
    file_type: str = Field(
        ..., description=f"MIME type. Allowed: {_ALLOWED_MIME_TYPES}"
    )
    size_bytes: int = Field(..., gt=0, le=_MAX_SIZE_BYTES)
    purpose: str = Field(
        ..., description=f"Upload purpose. One of: {_ALLOWED_PURPOSES}"
    )

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in _ALLOWED_PURPOSES:
            raise ValueError(f"purpose must be one of {_ALLOWED_PURPOSES}")
        return v

    @field_validator("file_type")
    @classmethod
    def validate_mime(cls, v: str) -> str:
        if v not in _ALLOWED_MIME_TYPES:
            raise ValueError(f"file_type must be one of {_ALLOWED_MIME_TYPES}")
        return v


class PresignResponse(AuraFitSchema):
    upload_url: str = Field(..., description="Presigned S3 PUT URL (expires in 5 min)")
    s3_key: str
    upload_id: str = Field(..., description="AuraFit upload record ID for confirmation step")
    expires_in: int = Field(..., description="Seconds until presigned URL expires")


class ConfirmUploadRequest(AuraFitSchema):
    upload_id: str = Field(..., description="upload_id from the presign response")
    s3_key: str = Field(..., description="s3_key from the presign response")
    purpose: str = Field(..., description="Must match the purpose from presign request")


class ConfirmUploadResponse(AuraFitSchema):
    upload_id: str
    task_id: str = Field(..., description="Celery task ID for polling task status")
    status: str = "PENDING"
    message: str = "Upload confirmed. Processing task queued."

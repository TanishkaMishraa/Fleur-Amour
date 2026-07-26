"""
AuraFit — Analysis request/response schemas.
Covers facial scan initiation, task polling, and scan history.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Request schemas ───────────────────────────────────────────────────────────

class ScanInitRequest(AuraFitSchema):
    """Payload sent after client uploads selfie to S3."""
    s3_key: str = Field(..., description="S3 key returned from the presigned upload response")
    upload_id: str = Field(..., description="upload_id from the confirm-upload flow")


class TryonInitRequest(AuraFitSchema):
    """Dispatch a virtual try-on task."""
    selfie_s3_key: str = Field(..., description="S3 key of the selfie image")
    product_id: UUID = Field(..., description="Catalog product to virtually try on")


# ── Response schemas ──────────────────────────────────────────────────────────

class FacialScanOut(UUIDSchema, TimestampSchema):
    user_id: UUID
    storage_path: str
    face_shape: str | None
    skin_analysis: dict | None = Field(
        None,
        description="{'tone': 'medium', 'texture': 'smooth', 'concerns': ['acne']}"
    )
    facial_features: dict | None = Field(
        None,
        description="{'jaw': 'defined', 'cheekbones': 'high', 'eyes': 'almond'}"
    )
    model_version: str | None
    quality_score: float | None
    is_active: bool


class TaskStatusResponse(AuraFitSchema):
    """
    Generic async task status.
    Returned immediately after dispatch and on subsequent polls.
    """
    task_id: str
    status: str = Field(
        ...,
        description="One of: PENDING | STARTED | PROGRESS | SUCCESS | FAILURE",
    )
    progress: int | None = Field(None, ge=0, le=100, description="0–100 percent complete")
    step: str | None = Field(None, description="Human-readable current pipeline step")
    result: dict | None = None
    error: str | None = None

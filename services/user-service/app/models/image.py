"""
AuraFit — Upload ORM model.
Tracks every presigned upload through its full lifecycle.
Backend never stores binary data — only S3 key references.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class UploadPurpose(str, enum.Enum):
    FACIAL_SCAN = "facial_scan"
    AVATAR = "avatar"
    WARDROBE_ITEM = "wardrobe_item"
    VIRTUAL_TRYON = "virtual_tryon"


class UploadStatus(str, enum.Enum):
    PENDING = "pending"         # Presigned URL issued, awaiting client upload
    UPLOADED = "uploaded"       # Client confirmed upload to S3
    PROCESSING = "processing"   # Celery worker task running
    COMPLETE = "complete"       # Pipeline finished, result_url populated
    FAILED = "failed"           # Pipeline error; see error_message


class Upload(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks a user file upload from presigned URL issuance to processing completion.
    Status transitions: PENDING → UPLOADED → PROCESSING → COMPLETE | FAILED
    """
    __tablename__ = "uploads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[UploadPurpose] = mapped_column(
        Enum(UploadPurpose, name="upload_purpose_enum"), nullable=False, index=True
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status_enum"),
        default=UploadStatus.PENDING, nullable=False, index=True
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Result
    result_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="CDN URL of processed output"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="uploads")

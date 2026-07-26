"""
AuraFit — Report and Notification ORM models.
StyleReport: generated "Style DNA Report" deliverable.
Notification + NotificationPreferences: in-app and push channel management.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationType(str, enum.Enum):
    REC_READY = "rec_ready"
    TRYON_READY = "tryon_ready"
    SCAN_COMPLETE = "scan_complete"
    OUTFIT_SUGGESTION = "outfit_suggestion"
    SYSTEM = "system"
    MARKETING = "marketing"


class ReportStatus(str, enum.Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class StyleReport(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Generated Style DNA Report — the core AuraFit deliverable.
    Contains personalised analysis across beauty, style, and fragrance dimensions.
    Generated asynchronously by the Style DNA AI service; stored as structured JSON.
    """
    __tablename__ = "style_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status_enum"),
        default=ReportStatus.GENERATING, nullable=False, index=True
    )

    # Report content sections (structured JSON for flexible rendering)
    skin_section: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Tone, type, concerns, recommended ingredients"
    )
    style_section: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Archetypes, colour palette, body-shape styling tips"
    )
    fragrance_section: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Note families, season/occasion matrix, top picks"
    )
    beauty_section: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Makeup tips, product recommendations by category"
    )

    # Generation metadata
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facial_scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("facial_scans.id", ondelete="SET NULL"), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="CDN URL of generated PDF"
    )

    user: Mapped["User"] = relationship("User", back_populates="style_reports")


class NotificationPreferences(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-user opt-in settings for each notification channel."""
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    email_marketing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_transactional: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_recommendations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_tryon: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """In-app notification record. Also acts as audit log for push/email sends."""
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deep_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications")

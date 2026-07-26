"""
AuraFit — Analysis ORM models.
FacialScan: result of the AI facial analysis pipeline (DeepFace + MediaPipe).
FragranceProfile: note-level fragrance preferences powering the Fragrance AI service.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class FacialScan(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    One AI facial analysis result per uploaded selfie.
    Only is_active=True scan is used for recommendation context.
    landmark_data stores the MediaPipe 468-point mesh for virtual try-on.
    """
    __tablename__ = "facial_scans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="S3 key of the source selfie image"
    )

    # ── AI-derived attributes ──────────────────────────────────────────────
    face_shape: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="oval | round | square | heart | oblong | diamond"
    )
    skin_analysis: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment='{"tone": "medium", "undertone": "warm", "concerns": ["acne"]}'
    )
    facial_features: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment='{"jaw": "defined", "cheekbones": "high", "eyes": "almond"}'
    )
    landmark_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="MediaPipe 468-point face mesh (used by virtual try-on service)"
    )

    # ── Pipeline metadata ──────────────────────────────────────────────────
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="facial_scans")


class FragranceProfile(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Note-level fragrance preferences.
    1:1 with UserProfile. Consumed by the Fragrance AI embedding service.
    """
    __tablename__ = "fragrance_profiles"

    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    preferred_notes: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["rose", "oud", "vanilla"]'
    )
    avoided_notes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    previous_fragrances: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='[{"name": "Chanel No.5", "rating": 5, "brand": "Chanel"}]'
    )
    intensity_preference: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="light | moderate | strong"
    )
    longevity_preference: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="fresh | all_day | long_lasting"
    )
    occasion_preferences: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["daily", "evening", "office"]'
    )

    user_profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="fragrance_profile"
    )

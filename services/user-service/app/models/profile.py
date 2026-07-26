"""
AuraFit — UserProfile ORM model. 1:1 with User.
JSONB columns store flexible multi-value arrays (style archetypes, skin concerns).
Populated progressively via onboarding quiz and facial scan pipeline.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class SkinTone(str, enum.Enum):
    FAIR = "fair"
    LIGHT = "light"
    MEDIUM = "medium"
    OLIVE = "olive"
    TAN = "tan"
    DEEP = "deep"


class SkinType(str, enum.Enum):
    NORMAL = "normal"
    DRY = "dry"
    OILY = "oily"
    COMBINATION = "combination"
    SENSITIVE = "sensitive"


class Undertone(str, enum.Enum):
    COOL = "cool"
    WARM = "warm"
    NEUTRAL = "neutral"


class BodyShape(str, enum.Enum):
    HOURGLASS = "hourglass"
    PEAR = "pear"
    APPLE = "apple"
    RECTANGLE = "rectangle"
    INVERTED_TRIANGLE = "inverted_triangle"


class UserProfile(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Beauty and personal styling profile.
    A profile row is created (empty) on user registration and filled
    progressively through the onboarding quiz and AI scan results.
    """
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Physical attributes (from quiz or AI scan) ─────────────────────────
    skin_tone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    skin_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    undertone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hair_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hair_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    eye_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_shape: Mapped[str | None] = mapped_column(String(30), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_range: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="e.g. '25-34'"
    )

    # ── Style & scent preferences (JSONB arrays) ───────────────────────────
    style_archetypes: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["minimalist","boho","classic"]'
    )
    fragrance_family: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["woody","floral","citrus"]'
    )
    skin_concerns: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["acne","hyperpigmentation","fine_lines"]'
    )
    avoided_ingredients: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='["alcohol","fragrance","parabens"]'
    )

    # ── Budget & locale ────────────────────────────────────────────────────
    budget_range: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="budget | mid | luxury"
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # ── Onboarding state ───────────────────────────────────────────────────
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    quiz_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="profile")
    fragrance_profile: Mapped["FragranceProfile | None"] = relationship(
        "FragranceProfile", back_populates="user_profile", uselist=False,
        cascade="all, delete-orphan",
    )

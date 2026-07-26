"""
AuraFit — Color Intelligence ORM models.
ColorProfile: persists the computed seasonal color season, personal palette,
and all recommendation sets for a user. Derived from facial scan data.
ColorPaletteItem: individual color entries within a profile.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class ColorSeason(str, enum.Enum):
    # Core 4
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    # Extended 12-season system
    LIGHT_SPRING  = "light_spring"
    TRUE_SPRING   = "true_spring"
    BRIGHT_SPRING = "bright_spring"
    LIGHT_SUMMER  = "light_summer"
    TRUE_SUMMER   = "true_summer"
    SOFT_SUMMER   = "soft_summer"
    SOFT_AUTUMN   = "soft_autumn"
    TRUE_AUTUMN   = "true_autumn"
    DEEP_AUTUMN   = "deep_autumn"
    DEEP_WINTER   = "deep_winter"
    TRUE_WINTER   = "true_winter"
    BRIGHT_WINTER = "bright_winter"


class ColorProfile(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Stores the full color intelligence analysis for a user.
    One active profile per user (is_active=True). Previous profiles kept
    for history comparison.

    Derived from facial_scans.skin_analysis (skin_tone + undertone +
    hair_analysis + facial_features).
    """
    __tablename__ = "color_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("facial_scans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Source facial scan this profile was derived from",
    )

    # ── Season classification ──────────────────────────────────────────────
    season: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="ColorSeason enum value (spring|summer|autumn|winter + extended 12)"
    )
    season_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Classification confidence 0.0–1.0"
    )
    season_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # ── Source color attributes (denormalised from scan for fast access) ───
    skin_tone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    undertone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    skin_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    ita_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    fitzpatrick: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hair_color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    eye_color: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Personal palette (JSONB stores list of ColorEntry dicts) ──────────
    palette_best: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='[{"hex": "#...", "name": "...", "category": "neutral"}]'
    )
    palette_avoid: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="Colors that clash with this season"
    )
    palette_neutrals: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    palette_accents: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Recommendations (all stored as structured JSONB) ──────────────────
    makeup_recommendations: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Foundation, blush, eyeshadow, liner, lipstick shades"
    )
    lipstick_recommendations: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='[{"shade": "...", "finish": "...", "hex": "...", "brands": [...]}]'
    )
    hair_color_recommendations: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='[{"name": "...", "hex": "...", "technique": "...", "rationale": "..."}]'
    )
    outfit_recommendations: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Outfit color palettes by occasion (work/evening/casual/sport)"
    )
    jewelry_recommendations: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Metal tones, gemstone colors, and style guidance"
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User")

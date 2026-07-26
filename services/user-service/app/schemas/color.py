"""
AuraFit — Color Intelligence Pydantic schemas.
Request/response contracts for all color analysis endpoints.
"""
from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Shared sub-types ──────────────────────────────────────────────────────────

class ColorEntry(AuraFitSchema):
    """A single color in a palette."""
    hex: str       = Field(..., description="6-digit hex e.g. '#C9A84C'")
    name: str      = Field(..., description="Human-readable color name")
    category: str  = Field(..., description="neutral|accent|base|statement")
    season_fit: str | None = Field(None, description="best|good|avoid")


class LipstickShade(AuraFitSchema):
    shade: str
    hex: str
    finish: str   = Field(..., description="matte|satin|gloss|sheer")
    intensity: str = Field(..., description="light|medium|bold")
    occasion: str  = Field(..., description="everyday|evening|professional|special")
    brands: list[str] = Field(default_factory=list)
    rationale: str


class HairColorOption(AuraFitSchema):
    name: str
    hex: str
    technique: str   = Field(..., description="all-over|highlights|balayage|ombre|gloss")
    commitment: str  = Field(..., description="permanent|semi-permanent|temporary")
    rationale: str
    maintenance: str = Field(..., description="Low|Medium|High")


class OutfitPalette(AuraFitSchema):
    occasion: str
    base_colors: list[ColorEntry]
    accent_colors: list[ColorEntry]
    avoid_colors: list[ColorEntry]
    styling_tip: str


class JewelryRecommendation(AuraFitSchema):
    metal_tones: list[str]      = Field(..., description="gold|rose-gold|silver|bronze|copper")
    gem_colors: list[ColorEntry]
    rationale: str
    style_notes: str


class MakeupColorRecommendation(AuraFitSchema):
    foundation_undertone: str
    foundation_finish: str
    blush_shades: list[ColorEntry]
    eyeshadow_palettes: list[dict]
    eyeliner_colors: list[ColorEntry]
    highlight_shades: list[ColorEntry]
    contour_shades: list[ColorEntry]


# ── Request schemas ───────────────────────────────────────────────────────────

class ColorAnalysisRequest(AuraFitSchema):
    """
    Compute color profile from a scan. If scan_id is omitted,
    uses the user's most recent active facial scan.
    """
    scan_id: UUID | None = Field(
        None,
        description="Facial scan to derive color profile from. Defaults to latest active scan."
    )
    use_extended_seasons: bool = Field(
        True,
        description="Whether to classify into the 12-season system (vs 4-season)"
    )


# ── Response schemas ──────────────────────────────────────────────────────────

class SeasonClassification(AuraFitSchema):
    season: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    key_characteristics: list[str]
    celebrity_examples: list[str]
    season_family: str   = Field(..., description="spring|summer|autumn|winter")
    contrast_level: str  = Field(..., description="low|medium|high")
    chroma_level: str    = Field(..., description="muted|soft|clear|bright")
    value_level: str     = Field(..., description="light|medium|deep")


class PersonalPalette(AuraFitSchema):
    best: list[ColorEntry]
    neutrals: list[ColorEntry]
    accents: list[ColorEntry]
    avoid: list[ColorEntry]
    hero_color: ColorEntry   = Field(..., description="Single best color for this person")


class ColorProfileOut(UUIDSchema, TimestampSchema):
    user_id: UUID
    scan_id: UUID | None
    season: str
    season_confidence: float
    season_description: str | None
    skin_tone: str | None
    undertone: str | None
    skin_hex: str | None
    ita_angle: float | None
    fitzpatrick: int | None
    hair_color_hex: str | None
    palette_best: list | None
    palette_avoid: list | None
    palette_neutrals: list | None
    palette_accents: list | None
    makeup_recommendations: dict | None
    lipstick_recommendations: list | None
    hair_color_recommendations: list | None
    outfit_recommendations: dict | None
    jewelry_recommendations: dict | None
    engine_version: str
    is_active: bool


class FullColorAnalysisResponse(AuraFitSchema):
    """Full response returned immediately on compute (or from cache)."""
    profile_id: UUID
    scan_id: UUID | None
    season: SeasonClassification
    palette: PersonalPalette
    makeup: MakeupColorRecommendation
    lipstick: list[LipstickShade]
    hair_color: list[HairColorOption]
    outfits: list[OutfitPalette]
    jewelry: JewelryRecommendation
    computed_at: str
    engine_version: str

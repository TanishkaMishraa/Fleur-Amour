"""
AuraFit — Wardrobe and outfit request/response schemas.
Wardrobe → WardrobeItem → Outfit → OutfitItem chain.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Wardrobe schemas ──────────────────────────────────────────────────────────

class WardrobeCreateRequest(AuraFitSchema):
    name: str = Field(..., min_length=1, max_length=100)
    is_default: bool = False


class WardrobeOut(UUIDSchema, TimestampSchema):
    user_id: UUID
    name: str
    is_default: bool
    item_count: int = 0


# ── Wardrobe item schemas ─────────────────────────────────────────────────────

class WardrobeItemCreateRequest(AuraFitSchema):
    custom_name: str | None = Field(None, max_length=255)
    product_id: UUID | None = None         # Link to catalog product
    category: str | None = Field(None, max_length=100)
    image_url: str | None = Field(None, max_length=512)
    notes: str | None = Field(None, max_length=1000)
    cost: float | None = Field(None, ge=0)
    brand: str | None = Field(None, max_length=100)
    color_tags: list[str] | None = Field(None, max_length=10)
    occasion_tags: list[str] | None = Field(
        None, max_length=10,
        examples=[["work", "casual", "evening"]],
    )
    season_tags: list[str] | None = Field(
        None, max_length=5,
        examples=[["spring", "summer"]],
    )


class WardrobeItemUpdateRequest(AuraFitSchema):
    """Partial update — all fields optional."""
    custom_name: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=100)
    image_url: str | None = Field(None, max_length=512)
    notes: str | None = Field(None, max_length=1000)
    cost: float | None = Field(None, ge=0)
    brand: str | None = Field(None, max_length=100)
    color_tags: list[str] | None = None
    occasion_tags: list[str] | None = None
    season_tags: list[str] | None = None


class WardrobeItemOut(UUIDSchema, TimestampSchema):
    wardrobe_id: UUID
    product_id: UUID | None
    custom_name: str | None
    category: str | None
    image_url: str | None
    notes: str | None
    cost: float | None
    times_worn: int
    brand: str | None
    color_tags: list | None
    occasion_tags: list | None
    season_tags: list | None
    is_deleted: bool


# ── Outfit schemas ────────────────────────────────────────────────────────────

class OutfitCreateRequest(AuraFitSchema):
    name: str = Field(..., min_length=1, max_length=150)
    occasion: str | None = Field(None, max_length=100)
    season: str | None = Field(None, max_length=50)
    style_tags: list[str] | None = Field(None, max_length=10)


class OutfitGenerateRequest(AuraFitSchema):
    """Payload for AI outfit generation task dispatch."""
    occasion: str | None = Field(None, max_length=100, examples=["work", "date night", "gym"])
    season: str | None = Field(None, max_length=50, examples=["summer", "winter"])
    style_hint: str | None = Field(
        None, max_length=200,
        description="Free-text hint passed to the style-dna AI service",
    )


class OutfitItemOut(AuraFitSchema):
    wardrobe_item_id: UUID
    position: int
    item: WardrobeItemOut | None = None


class OutfitOut(UUIDSchema, TimestampSchema):
    user_id: UUID
    name: str
    occasion: str | None
    season: str | None
    style_tags: list | None
    is_public: bool
    ai_generated: bool
    ai_score: float | None
    items: list[OutfitItemOut] = []

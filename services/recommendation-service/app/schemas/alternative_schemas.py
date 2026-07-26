"""
AuraFit — Smart Alternative Engine Pydantic schemas.
"""
from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, Field


class AuraSchema(BaseModel):
    model_config = {"from_attributes": True}


class ProductSummaryOut(AuraSchema):
    """Lightweight product summary used in alternative cards."""
    id:           UUID
    name:         str
    brand_name:   str
    brand_tier:   str          # luxury | mid | drugstore
    category:     str
    price:        float
    currency:     str
    image_url:    str | None
    avg_rating:   float | None
    review_count: int
    in_stock:     bool
    attributes:   dict | None   # Raw domain attributes for detail display
    ingredients:  str | None    # Raw INCI text


class AlternativeOut(AuraSchema):
    """
    One alternative product with full similarity breakdown.
    This is the primary object rendered in the comparison UI.
    """
    alt_id:        UUID
    product:       ProductSummaryOut

    # ── Similarity scores [0, 1] ──────────────────────────────────────────────
    overall_score:    float = Field(ge=0.0, le=1.0)
    overall_pct:      int   = Field(ge=0, le=100, description="overall_score × 100")
    embedding_score:  float | None = None
    ingredient_score: float | None = None
    formula_score:    float | None = None
    shade_score:      float | None = None
    fragrance_score:  float | None = None
    style_score:      float | None = None

    # ── Match metadata ─────────────────────────────────────────────────────────
    match_types:  list[str]    # Which signals fired (ingredient, shade, fragrance, ...)
    match_detail: dict         # Signal-specific details for tooltips

    # ── Price info ────────────────────────────────────────────────────────────
    source_price:  float
    alt_price:     float
    price_savings: float
    savings_pct:   float       # 0–100
    currency:      str

    # ── Quality ───────────────────────────────────────────────────────────────
    is_best_value: bool
    rank:          int


class AlternativeGroupResponse(AuraSchema):
    """
    Full response for GET /alternatives/{product_id}.
    Contains source product summary + ranked list of alternatives.
    """
    source:         ProductSummaryOut
    alternatives:   list[AlternativeOut]
    total:          int
    from_cache:     bool    # True = served from pre-computed DB rows
    engine_version: str


class AlternativeRequest(AuraSchema):
    """Optional query parameters for alternative requests."""
    limit:          int   = Field(default=5, ge=1, le=10)
    min_similarity: float = Field(default=0.40, ge=0.0, le=1.0)


class ShadeCompareRequest(AuraSchema):
    """Direct shade comparison between two hex codes."""
    hex_a: str
    hex_b: str


class IngredientCompareRequest(AuraSchema):
    """Direct ingredient list comparison."""
    ingredients_a: str
    ingredients_b: str


class FragranceCompareRequest(AuraSchema):
    """Direct fragrance note comparison."""
    attrs_a: dict   # Full product attributes dict for product A
    attrs_b: dict   # Full product attributes dict for product B

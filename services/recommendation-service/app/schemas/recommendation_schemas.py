"""
AuraFit — Recommendation Service Pydantic schemas.
Request/response contracts for all recommendation and catalog endpoints.
"""
from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AuraSchema(BaseModel):
    """Base schema: strict mode, no ORM needed."""
    model_config = {"from_attributes": True, "str_strip_whitespace": True}


# ── Enums ─────────────────────────────────────────────────────────────────────

class RecommendationDomain(StrEnum):
    MAKEUP      = "makeup"
    SKINCARE    = "skincare"
    HAIRCARE    = "haircare"
    FRAGRANCE   = "fragrance"
    FASHION     = "fashion"
    ACCESSORIES = "accessories"
    MIXED       = "mixed"


class SortOrder(StrEnum):
    RELEVANCE     = "relevance"
    PRICE_ASC     = "price_asc"
    PRICE_DESC    = "price_desc"
    RATING        = "rating"
    NEW_ARRIVALS  = "new_arrivals"
    TRENDING      = "trending"


# ── Product schemas ───────────────────────────────────────────────────────────

class BrandOut(AuraSchema):
    id:   UUID
    name: str
    slug: str
    tier: str
    logo_url: str | None


class CategoryOut(AuraSchema):
    id:       UUID
    name:     str
    slug:     str
    icon:     str | None
    parent_id:UUID | None


class ProductOut(AuraSchema):
    id:           UUID
    sku:          str
    name:         str
    brand:        BrandOut
    category:     CategoryOut
    description:  str | None
    price:        float
    currency:     str
    image_urls:   list[str] | None
    attributes:   dict | None
    avg_rating:   float | None
    review_count: int
    is_new_arrival: bool
    is_trending:  bool
    in_stock:     bool
    style_tags:   list[str] | None
    season_tags:  list[str] | None
    concern_tags: list[str] | None


class ProductListOut(AuraSchema):
    """Lighter product summary for list views / recommendation cards."""
    id:          UUID
    sku:         str
    name:        str
    brand_name:  str
    brand_slug:  str
    category:    str
    price:       float
    currency:    str
    image_url:   str | None   # Primary image only
    avg_rating:  float | None
    review_count:int
    is_new_arrival: bool
    is_trending: bool
    in_stock:    bool


class ReviewOut(AuraSchema):
    id:                UUID
    user_id:           UUID
    rating:            int
    title:             str | None
    body:              str | None
    verified_purchase: bool
    skin_type:         str | None
    created_at:        str


# ── Recommendation schemas ────────────────────────────────────────────────────

class RecommendedProduct(AuraSchema):
    """One recommended product with scoring metadata."""
    product:      ProductListOut
    score:        float = Field(ge=0.0, le=1.0)
    cf_score:     float | None = None
    cb_score:     float | None = None
    profile_score:float | None = None
    position:     int
    reason_code:  str
    explanation:  str


class RecommendationRequest(AuraSchema):
    """Request body for POST /recommendations/{domain}."""
    domain:        RecommendationDomain = RecommendationDomain.MIXED
    user_id:       UUID
    # Optional context
    occasion:      str | None = None       # work | evening | casual | sport
    season:        str | None = None       # spring | summer | autumn | winter
    budget_max:    float | None = None
    budget_min:    float | None = None
    brand_ids:     list[UUID] | None = None
    exclude_ids:   list[UUID] | None = None   # Already purchased
    limit:         int = Field(default=20, ge=1, le=50)


class RecommendationResponse(AuraSchema):
    session_id:   UUID
    domain:       str
    items:        list[RecommendedProduct]
    total:        int
    model_version:str
    cold_start:   bool = False     # True if user has < MIN_INTERACTION_FOR_CF interactions


class InteractionRequest(AuraSchema):
    """Record a user↔product interaction."""
    user_id:          UUID
    product_id:       UUID
    interaction_type: str
    rating:           int | None = Field(None, ge=1, le=5)
    session_context:  dict | None = None


class FeedbackRequest(AuraSchema):
    """Update recommendation outcome signals."""
    recommendation_id: UUID
    clicked:   bool = False
    saved:     bool = False
    purchased: bool = False


# ── Catalog request schemas ───────────────────────────────────────────────────

class ProductSearchRequest(AuraSchema):
    q:              str | None = None
    domain:         RecommendationDomain | None = None
    category_slug:  str | None = None
    brand_slug:     str | None = None
    price_min:      float | None = None
    price_max:      float | None = None
    skin_tone:      str | None = None
    undertone:      str | None = None
    concerns:       list[str] | None = None
    style_tags:     list[str] | None = None
    in_stock_only:  bool = True
    sort:           SortOrder = SortOrder.RELEVANCE
    page:           int = Field(default=1, ge=1)
    per_page:       int = Field(default=24, ge=1, le=100)


class PaginatedProducts(AuraSchema):
    items:      list[ProductListOut]
    total:      int
    page:       int
    per_page:   int
    total_pages:int


# ── Similarity schema ─────────────────────────────────────────────────────────

class SimilarProductsRequest(AuraSchema):
    product_id: UUID
    limit:      int = Field(default=10, ge=1, le=30)
    domain:     RecommendationDomain | None = None   # Filter to same domain if set


# ── User preference schemas ───────────────────────────────────────────────────

class UserPreferenceSignals(AuraSchema):
    """
    Summarised preference vector for a user.
    Built from interactions, profile data, and color profile.
    Used internally — not exposed to the client.
    """
    user_id:         UUID
    skin_tone:       str | None
    undertone:       str | None
    skin_concerns:   list[str]
    style_archetypes:list[str]
    color_season:    str | None
    fragrance_family:list[str]
    budget_range:    str | None
    interaction_count:int
    top_categories:  list[str]   # Most interacted categories
    top_brands:      list[str]   # Most interacted brands

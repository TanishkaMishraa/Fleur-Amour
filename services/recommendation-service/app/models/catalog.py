"""
AuraFit — Recommendation Service ORM models.
Product, Brand, Category, ProductEmbedding, Review,
RecommendationSession, Recommendation, UserProductInteraction, SavedProduct.

These models mirror the user-service models but live in the recommendation
service's own DB connection. Cross-service data sharing is via API calls
or shared PostgreSQL schema (same DB, separate services in dev).
"""
from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={getattr(self, 'id', '?')}>"


# ── Mixins ────────────────────────────────────────────────────────────────────

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )


class TimestampMixin:
    from sqlalchemy import func
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Catalog ───────────────────────────────────────────────────────────────────

class BrandTier(str, enum.Enum):
    luxury    = "luxury"
    mid       = "mid"
    drugstore = "drugstore"


class Brand(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "brands"

    name:              Mapped[str]          = mapped_column(String(200), nullable=False)
    slug:              Mapped[str]          = mapped_column(String(200), nullable=False, unique=True, index=True)
    logo_url:          Mapped[str | None]   = mapped_column(String(2048))
    country_of_origin: Mapped[str | None]   = mapped_column(String(100))
    tier:              Mapped[BrandTier]    = mapped_column(Enum(BrandTier, name="brand_tier"), default=BrandTier.mid, nullable=False)
    is_active:         Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship("Product", back_populates="brand")


class Category(Base, UUIDMixin, TimestampMixin):
    """Self-referential tree: Beauty > Skincare > Serums."""
    __tablename__ = "categories"

    name:       Mapped[str]           = mapped_column(String(200), nullable=False)
    slug:       Mapped[str]           = mapped_column(String(200), nullable=False, unique=True, index=True)
    parent_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    icon:       Mapped[str | None]    = mapped_column(String(100))
    sort_order: Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    is_active:  Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)

    parent:   Mapped["Category | None"]  = relationship("Category", remote_side="Category.id")
    products: Mapped[list["Product"]]    = relationship("Product", back_populates="category")


class Product(Base, UUIDMixin, TimestampMixin):
    """
    Core product entity. Supports all 6 domains:
      makeup | skincare | haircare | fragrance | fashion | accessories
    Attributes JSONB stores domain-specific fields flexibly.
    """
    __tablename__ = "products"

    sku:         Mapped[str]          = mapped_column(String(100), nullable=False, unique=True, index=True)
    name:        Mapped[str]          = mapped_column(String(500), nullable=False)
    brand_id:    Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    description: Mapped[str | None]   = mapped_column(Text)
    ingredients: Mapped[str | None]   = mapped_column(Text)         # Raw ingredient list (skincare/haircare)
    price:       Mapped[float]        = mapped_column(Numeric(10, 2), nullable=False)
    currency:    Mapped[str]          = mapped_column(String(3), default="USD", nullable=False)
    image_urls:  Mapped[list | None]  = mapped_column(JSONB)         # ["url1", "url2"]
    is_active:   Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False, index=True)

    # ── Flexible domain-specific attributes ───────────────────────────────
    # Makeup:    {shade, finish, coverage, formula, skin_tone_range, undertone}
    # Skincare:  {skin_type, concerns, key_ingredients, spf, texture}
    # Haircare:  {hair_type, concern, application, hold_level}
    # Fragrance: {family, top_notes, mid_notes, base_notes, longevity, sillage, season}
    # Fashion:   {size_range, color, material, occasion, season, style_tags}
    # Accessories:{material, color, occasion, style_tags, metal_tone}
    attributes: Mapped[dict | None]   = mapped_column(JSONB)

    # Pre-computed compatibility metadata (updated by nightly tasks)
    compatible_skin_tones:  Mapped[list | None] = mapped_column(JSONB)  # ["fair","light","medium"]
    compatible_undertones:  Mapped[list | None] = mapped_column(JSONB)  # ["cool","neutral"]
    compatible_hair_types:  Mapped[list | None] = mapped_column(JSONB)
    style_tags:             Mapped[list | None] = mapped_column(JSONB)   # ["minimalist","boho"]
    season_tags:            Mapped[list | None] = mapped_column(JSONB)   # ["spring","summer"]
    concern_tags:           Mapped[list | None] = mapped_column(JSONB)   # ["acne","dryness"]

    # Catalog metrics
    avg_rating:       Mapped[float | None] = mapped_column(Float)
    review_count:     Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    interaction_count:Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    is_new_arrival:   Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    is_trending:      Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    in_stock:         Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)

    brand:     Mapped["Brand"]               = relationship("Brand", back_populates="products")
    category:  Mapped["Category"]            = relationship("Category", back_populates="products")
    embedding: Mapped["ProductEmbedding | None"] = relationship("ProductEmbedding", back_populates="product", uselist=False)
    reviews:   Mapped[list["Review"]]        = relationship("Review", back_populates="product")


class ProductEmbedding(Base, UUIDMixin, TimestampMixin):
    """
    Dual-vector product embedding:
    - text_embedding:  SBERT(name + description + key_ingredients)  → 384-dim
    - image_embedding: CLIP(primary_image)                          → 512-dim
    Used for ANN (pgvector cosine) content-based retrieval.
    """
    __tablename__ = "product_embeddings"
    __table_args__ = (UniqueConstraint("product_id", name="uq_product_embedding"),)

    product_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    text_embedding:   Mapped[list[float] | None] = mapped_column(Vector(384))   # SBERT all-MiniLM-L6-v2
    image_embedding:  Mapped[list[float] | None] = mapped_column(Vector(512))   # CLIP ViT-B/32
    model_version:    Mapped[str]              = mapped_column(String(50), nullable=False, default="1.0.0")

    product: Mapped["Product"] = relationship("Product", back_populates="embedding")


class Review(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reviews"

    user_id:           Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_id:        Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    rating:            Mapped[int]          = mapped_column(SmallInteger, nullable=False)   # 1-5
    title:             Mapped[str | None]   = mapped_column(String(255))
    body:              Mapped[str | None]   = mapped_column(Text)
    verified_purchase: Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    skin_type:         Mapped[str | None]   = mapped_column(String(30))    # Reviewer's skin type (from quiz)

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")


# ── Recommendation tables ─────────────────────────────────────────────────────

class SessionType(str, enum.Enum):
    MAKEUP     = "makeup"
    SKINCARE   = "skincare"
    HAIRCARE   = "haircare"
    FRAGRANCE  = "fragrance"
    FASHION    = "fashion"
    ACCESSORIES= "accessories"
    MIXED      = "mixed"


class RecommendationSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommendation_sessions"

    user_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    session_type: Mapped[SessionType]  = mapped_column(Enum(SessionType, name="rec_session_type"), nullable=False, index=True)
    context:      Mapped[dict | None]  = mapped_column(JSONB)           # Filters, occasion, season
    model_version:Mapped[str | None]   = mapped_column(String(50))

    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="session", cascade="all, delete-orphan",
        order_by="Recommendation.position",
    )


class Recommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "recommendations"

    session_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recommendation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    score:         Mapped[float]     = mapped_column(Numeric(6, 5), nullable=False)
    cf_score:      Mapped[float | None] = mapped_column(Float)          # Raw CF component
    cb_score:      Mapped[float | None] = mapped_column(Float)          # Raw content-based component
    profile_score: Mapped[float | None] = mapped_column(Float)          # Profile match component
    position:      Mapped[int]       = mapped_column(SmallInteger, nullable=False)
    reason_code:   Mapped[str | None]= mapped_column(String(50))        # CF_MATCH | CB_SIMILAR | PROFILE_RULE | TRENDING
    explanation:   Mapped[str | None]= mapped_column(String(500))
    was_clicked:   Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    was_saved:     Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    was_purchased: Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped["RecommendationSession"] = relationship("RecommendationSession", back_populates="recommendations")


class InteractionType(str, enum.Enum):
    VIEW     = "view"
    LIKE     = "like"
    DISLIKE  = "dislike"
    SAVE     = "save"
    PURCHASE = "purchase"
    TRY_ON   = "try_on"
    REVIEW   = "review"


class UserProductInteraction(Base, UUIDMixin, TimestampMixin):
    """
    All user↔product interaction events.
    Primary implicit feedback signal for ALS collaborative filtering.
    Confidence values: purchase=5, save=3, like=2, try_on=2, view=1
    """
    __tablename__ = "user_product_interactions"

    user_id:          Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(Enum(InteractionType, name="interaction_type_enum_rec"), nullable=False, index=True)
    rating:           Mapped[int | None]      = mapped_column(SmallInteger)           # Explicit 1-5
    confidence_value: Mapped[float | None]    = mapped_column(Float)                  # Precomputed implicit confidence
    session_context:  Mapped[dict | None]     = mapped_column(JSONB)


class UserEmbedding(Base, UUIDMixin, TimestampMixin):
    """
    User preference vector derived from interaction history.
    = weighted mean of liked/saved/purchased product embeddings.
    Rebuilt by Celery task on interaction delta.
    """
    __tablename__ = "user_embeddings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_embedding"),)

    user_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    text_embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
    interaction_count: Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    model_version:  Mapped[str]              = mapped_column(String(50), nullable=False, default="1.0.0")

"""
AuraFit — Smart Alternative Engine ORM model.

ProductAlternative: pre-computed pairings between a source product
(typically luxury/high-price) and a cheaper alternative.

Stored after nightly computation to serve sub-10ms API responses.
Re-computed when:
  1. A new product is added
  2. A product's price changes
  3. Embeddings are refreshed (weekly full refresh)

Match types (stored as a list in match_types):
  - overall:    weighted composite of all signals
  - ingredient: skincare/haircare formula match
  - formula:    finish/texture/coverage/SPF match (makeup + skincare)
  - shade:      colour/hex similarity (makeup)
  - fragrance:  top/mid/base note overlap (fragrance)
  - embedding:  SBERT semantic similarity (all domains)
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean, CheckConstraint, Float, ForeignKey,
    Integer, Numeric, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.catalog import Base, TimestampMixin, UUIDMixin


class AlternativeMatchType(str, enum.Enum):
    OVERALL    = "overall"
    INGREDIENT = "ingredient"
    FORMULA    = "formula"
    SHADE      = "shade"
    FRAGRANCE  = "fragrance"
    EMBEDDING  = "embedding"
    STYLE      = "style"


class ProductAlternative(Base, UUIDMixin, TimestampMixin):
    """
    A pre-computed alternative pair: source → alternative.

    source_id    = the expensive / recommended product
    alt_id       = the affordable alternative

    Scores are all normalised to [0, 1].
    overall_score = weighted mean of available sub-scores.
    """
    __tablename__ = "product_alternatives"
    __table_args__ = (
        UniqueConstraint("source_id", "alt_id", name="uq_product_alternative"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 1", name="ck_alt_score_range"),
        CheckConstraint("price_savings >= 0", name="ck_alt_savings_positive"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Similarity scores [0, 1] ──────────────────────────────────────────────
    overall_score:     Mapped[float]        = mapped_column(Float, nullable=False, index=True)
    embedding_score:   Mapped[float | None] = mapped_column(Float)   # SBERT cosine
    ingredient_score:  Mapped[float | None] = mapped_column(Float)   # Jaccard on parsed INCI
    formula_score:     Mapped[float | None] = mapped_column(Float)   # Attribute overlap
    shade_score:       Mapped[float | None] = mapped_column(Float)   # ΔE colour distance → score
    fragrance_score:   Mapped[float | None] = mapped_column(Float)   # Note overlap
    style_score:       Mapped[float | None] = mapped_column(Float)   # Style tag overlap

    # ── Match metadata ────────────────────────────────────────────────────────
    match_types:  Mapped[list | None] = mapped_column(
        JSONB, comment='["ingredient","formula","shade"] — which signals fired'
    )
    match_detail: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="""
        {
          "matched_ingredients": ["niacinamide", "hyaluronic_acid"],
          "matched_notes":       ["rose", "oud"],
          "shade_delta_e":       8.5,
          "shade_hex_source":    "#C4927A",
          "shade_hex_alt":       "#C28B73",
          "formula_matches":     {"finish": "matte", "spf": "50"},
          "key_ingredient_hits": 4,
          "total_active_ingredients": 7
        }
        """,
    )

    # ── Price info (denormalised for fast API response) ───────────────────────
    source_price:  Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    alt_price:     Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_savings: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    savings_pct:   Mapped[float] = mapped_column(Float, nullable=False)
    currency:      Mapped[str]   = mapped_column(String(3), default="INR", nullable=False)

    # ── Quality signals ────────────────────────────────────────────────────────
    is_best_value:  Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    rank:           Mapped[int]  = mapped_column(Integer, nullable=False, default=1)  # 1 = top alt for this source
    engine_version: Mapped[str]  = mapped_column(String(20), nullable=False, default="1.0.0")

    # ── Relationships ──────────────────────────────────────────────────────────
    source:      Mapped["Product"] = relationship("Product", foreign_keys=[source_id])
    alternative: Mapped["Product"] = relationship("Product", foreign_keys=[alt_id])

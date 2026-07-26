"""
AuraFit — Wardrobe ORM models.
Wardrobe → WardrobeItem → OutfitItem ← Outfit
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Wardrobe(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """Named collection of wardrobe items owned by a user."""
    __tablename__ = "wardrobes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="wardrobes")
    items: Mapped[list["WardrobeItem"]] = relationship(
        "WardrobeItem", back_populates="wardrobe", cascade="all, delete-orphan",
    )


class WardrobeItem(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Single item in a wardrobe.
    product_id is a cross-service reference (no FK — product lives in product-service DB).
    Custom items (no product_id) use custom_name + uploaded image.
    """
    __tablename__ = "wardrobe_items"

    wardrobe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wardrobes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    times_worn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_worn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # JSONB tag lists — flexible, queryable with @> operator
    color_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    occasion_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    season_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    wardrobe: Mapped["Wardrobe"] = relationship("Wardrobe", back_populates="items")
    outfit_items: Mapped[list["OutfitItem"]] = relationship(
        "OutfitItem", back_populates="wardrobe_item",
    )


class Outfit(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Curated combination of wardrobe items.
    Can be user-created or AI-generated (ai_generated=True).
    """
    __tablename__ = "outfits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    occasion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    season: Mapped[str | None] = mapped_column(String(50), nullable=True)
    style_tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["OutfitItem"]] = relationship(
        "OutfitItem", back_populates="outfit", cascade="all, delete-orphan",
        order_by="OutfitItem.position",
    )


class OutfitItem(AuraFitBase):
    """Association: Outfit ↔ WardrobeItem with display ordering."""
    __tablename__ = "outfit_items"
    __table_args__ = (
        UniqueConstraint("outfit_id", "wardrobe_item_id", name="uq_outfit_item"),
    )

    outfit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True
    )
    wardrobe_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wardrobe_items.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    outfit: Mapped["Outfit"] = relationship("Outfit", back_populates="items")
    wardrobe_item: Mapped["WardrobeItem"] = relationship(
        "WardrobeItem", back_populates="outfit_items"
    )

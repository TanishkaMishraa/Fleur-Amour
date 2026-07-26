"""
AuraFit — Product, Brand, Category, ProductEmbedding Models
"""
from __future__ import annotations

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BrandTier(str, enum.Enum):
    luxury = "luxury"
    mid = "mid"
    drugstore = "drugstore"


class Brand(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(2048))
    country_of_origin: Mapped[str | None] = mapped_column(String(100))
    tier: Mapped[BrandTier] = mapped_column(
        Enum(BrandTier, name="brand_tier"),
        default=BrandTier.mid,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship("Product", back_populates="brand")


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Self-referential tree for category hierarchy (e.g. Beauty > Skincare > Serums)."""
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    icon: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    parent: Mapped["Category | None"] = relationship("Category", remote_side="Category.id")
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent")  # type: ignore[misc]
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    image_urls: Mapped[list | None] = mapped_column(JSONB)        # [url1, url2, ...]
    attributes: Mapped[dict | None] = mapped_column(JSONB)        # {shade, finish, SPF, size}
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="products")
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    embedding: Mapped["ProductEmbedding | None"] = relationship(
        "ProductEmbedding", back_populates="product", uselist=False
    )
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku} name={self.name[:40]}>"


class ProductEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    CLIP vector embedding per product for semantic similarity search.
    Uses pgvector for ANN queries.
    """
    __tablename__ = "product_embeddings"
    __table_args__ = (UniqueConstraint("product_id", name="uq_product_embedding"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(512))  # CLIP ViT-B/32
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="embedding")

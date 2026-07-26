"""
AuraFit — Recommendation ORM models.
RecommendationSession groups all items produced in one recommendation call.
Recommendation tracks each product + outcome signals (CTR, saves, purchases).
UserProductInteraction is the primary signal source for the CF model.
SavedProduct is the user's wishlist.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey,
    Numeric, SmallInteger, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class SessionType(str, enum.Enum):
    STYLE = "style"
    BEAUTY = "beauty"
    FRAGRANCE = "fragrance"
    OUTFIT = "outfit"


class InteractionType(str, enum.Enum):
    VIEW = "view"
    LIKE = "like"
    DISLIKE = "dislike"
    SAVE = "save"
    PURCHASE = "purchase"
    TRY_ON = "try_on"
    REVIEW = "review"


class RecommendationSession(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """One recommendation request. Groups all produced candidate items."""
    __tablename__ = "recommendation_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, name="rec_session_type_enum"), nullable=False, index=True
    )
    context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Applied filters, occasion, season context"
    )
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="recommendation_sessions")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation", back_populates="session", cascade="all, delete-orphan",
        order_by="Recommendation.position",
    )


class Recommendation(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual recommended product within a session.
    score = hybrid_score from Stage 0 ranking formula.
    reason_code maps to human-readable explanation copy.
    """
    __tablename__ = "recommendations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendation_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # Cross-service reference — no FK; product lives in product-service DB
    product_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="CF_MATCH | SKIN_COMPATIBLE | STYLE_ARCHETYPE | TRENDING"
    )
    explanation: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Outcome signals — updated async on user interaction
    was_clicked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    was_purchased: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped["RecommendationSession"] = relationship(
        "RecommendationSession", back_populates="recommendations"
    )


class UserProductInteraction(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    All user↔product interaction events.
    Primary signal source for the ALS collaborative filtering model.
    Written on every view, like, save, purchase.
    """
    __tablename__ = "user_product_interactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type_enum"),
        nullable=False, index=True
    )
    rating: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="Explicit 1–5 star rating"
    )
    interaction_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Session context, source page, etc."
    )

    user: Mapped["User"] = relationship("User", back_populates="interactions")


class SavedProduct(AuraFitBase):
    """User's saved / wishlisted products. Composite PK."""
    __tablename__ = "saved_products"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_saved_product"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    saved_at: Mapped[str] = mapped_column(nullable=False)

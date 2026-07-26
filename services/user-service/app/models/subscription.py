"""
AuraFit — Subscription System (Stage 10).
Plans: FREE | GLOW (₹499/mo) | RADIANCE (₹999/mo) | LUXE (₹2499/mo)

FREE:      AI scan (3/month), color profile, basic recs, style quiz
GLOW:      Unlimited scans, full Style DNA, alternatives engine
RADIANCE:  Virtual try-on, wardrobe AI (50 items), celebrity matching
LUXE:      Everything unlimited, priority AI queue, PDF export, API access

Feature gates checked via SubscriptionService.can_use(feature).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPlan(str, enum.Enum):
    FREE      = "free"
    GLOW      = "glow"        # ₹499/mo
    RADIANCE  = "radiance"    # ₹999/mo
    LUXE      = "luxe"        # ₹2499/mo


class SubscriptionStatus(str, enum.Enum):
    ACTIVE    = "active"
    CANCELLED = "cancelled"
    PAST_DUE  = "past_due"
    TRIALING  = "trialing"
    EXPIRED   = "expired"


# ── Feature gates per plan ────────────────────────────────────────────────────

PLAN_FEATURES: dict[SubscriptionPlan, dict[str, int | bool]] = {
    SubscriptionPlan.FREE: {
        "facial_scans_per_month":     3,
        "color_profiles":             True,
        "recommendations":            True,
        "style_quiz":                 True,
        "style_dna_report":           False,
        "alternatives_engine":        False,
        "virtual_tryon":              False,
        "wardrobe_items_limit":       0,
        "celebrity_matching":         False,
        "pdf_export":                 False,
        "priority_ai_queue":          False,
        "ai_chat_messages_per_day":   5,
    },
    SubscriptionPlan.GLOW: {
        "facial_scans_per_month":     999,   # Unlimited
        "color_profiles":             True,
        "recommendations":            True,
        "style_quiz":                 True,
        "style_dna_report":           True,
        "alternatives_engine":        True,
        "virtual_tryon":              False,
        "wardrobe_items_limit":       0,
        "celebrity_matching":         False,
        "pdf_export":                 True,
        "priority_ai_queue":          False,
        "ai_chat_messages_per_day":   20,
    },
    SubscriptionPlan.RADIANCE: {
        "facial_scans_per_month":     999,
        "color_profiles":             True,
        "recommendations":            True,
        "style_quiz":                 True,
        "style_dna_report":           True,
        "alternatives_engine":        True,
        "virtual_tryon":              True,
        "wardrobe_items_limit":       50,
        "celebrity_matching":         True,
        "pdf_export":                 True,
        "priority_ai_queue":          False,
        "ai_chat_messages_per_day":   50,
    },
    SubscriptionPlan.LUXE: {
        "facial_scans_per_month":     999,
        "color_profiles":             True,
        "recommendations":            True,
        "style_quiz":                 True,
        "style_dna_report":           True,
        "alternatives_engine":        True,
        "virtual_tryon":              True,
        "wardrobe_items_limit":       999,   # Unlimited
        "celebrity_matching":         True,
        "pdf_export":                 True,
        "priority_ai_queue":          True,
        "ai_chat_messages_per_day":   999,
    },
}

PLAN_PRICES_INR: dict[SubscriptionPlan, int] = {
    SubscriptionPlan.FREE:     0,
    SubscriptionPlan.GLOW:     499,
    SubscriptionPlan.RADIANCE: 999,
    SubscriptionPlan.LUXE:     2499,
}


class Subscription(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User subscription record. One active subscription per user.
    Payment processing is external (Razorpay/Stripe); this stores
    the state only — not card details.
    """
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    plan:   Mapped[SubscriptionPlan]   = mapped_column(
        Enum(SubscriptionPlan, name="subscription_plan_enum"),
        nullable=False, default=SubscriptionPlan.FREE,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status_enum"),
        nullable=False, default=SubscriptionStatus.ACTIVE, index=True,
    )

    # Billing cycle
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool]             = mapped_column(Boolean, default=False)
    cancelled_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))

    # Payment provider reference (Razorpay / Stripe)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255))
    provider_customer_id:     Mapped[str | None] = mapped_column(String(255))
    provider:                 Mapped[str | None] = mapped_column(String(50))   # razorpay | stripe

    # Usage counters (reset monthly)
    scans_this_month:   Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_reset_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Extended attributes (trial info, coupon, etc.)
    meta: Mapped[dict | None] = mapped_column(JSONB)

    user: Mapped["User"] = relationship("User")

    @property
    def features(self) -> dict:
        return PLAN_FEATURES.get(self.plan, PLAN_FEATURES[SubscriptionPlan.FREE])

    def can_use(self, feature: str) -> bool:
        """Check if current plan grants access to a feature."""
        features = self.features
        val = features.get(feature)
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val > 0
        return False

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

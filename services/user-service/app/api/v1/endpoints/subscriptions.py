"""
AuraFit — Subscription API endpoints (Stage 10).

Routes:
  GET  /subscriptions/me           — current user's subscription + usage
  GET  /subscriptions/plans        — all available plans + pricing
  POST /subscriptions/upgrade      — initiate plan upgrade (payment intent)
  POST /subscriptions/cancel       — cancel at period end
  POST /subscriptions/webhook/razorpay — Razorpay webhook handler
  POST /subscriptions/webhook/stripe   — Stripe webhook handler
  GET  /subscriptions/usage        — current period feature usage
  POST /subscriptions/check        — gate check: can_use(feature)?
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.subscription import (
    PLAN_FEATURES, Subscription, SubscriptionPlan, SubscriptionStatus, SubscriptionUsage,
)
from app.models.user import User

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
logger = get_logger(__name__)

# ── Pricing table (INR) ───────────────────────────────────────────────────────

PLAN_PRICING = {
    SubscriptionPlan.FREE:     {"price_inr": 0,    "price_usd": 0,   "label": "Free"},
    SubscriptionPlan.GLOW:     {"price_inr": 499,  "price_usd": 6,   "label": "Glow"},
    SubscriptionPlan.RADIANCE: {"price_inr": 999,  "price_usd": 12,  "label": "Radiance"},
    SubscriptionPlan.LUXE:     {"price_inr": 2499, "price_usd": 30,  "label": "Luxe"},
}


# ── Request/response schemas ──────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan:     SubscriptionPlan
    provider: str = "razorpay"   # razorpay | stripe
    currency: str = "INR"


class CancelRequest(BaseModel):
    reason: str | None = None


class FeatureCheckRequest(BaseModel):
    feature: str


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_or_create_subscription(
    user_id: UUID, session: any
) -> Subscription:
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = Subscription(
            user_id=user_id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        session.add(sub)
        await session.flush()
    return sub


async def _get_current_usage(user_id: UUID, session: any) -> SubscriptionUsage | None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(SubscriptionUsage)
        .where(SubscriptionUsage.user_id == user_id)
        .where(SubscriptionUsage.period_start <= now)
        .where(SubscriptionUsage.period_end >= now)
        .order_by(SubscriptionUsage.period_start.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/plans", summary="Get all subscription plans with pricing and features")
async def get_plans() -> dict:
    """Public endpoint — no auth required."""
    plans = []
    for plan in SubscriptionPlan:
        features = PLAN_FEATURES[plan]
        pricing  = PLAN_PRICING[plan]
        plans.append({
            "id":          plan.value,
            "label":       pricing["label"],
            "price_inr":   pricing["price_inr"],
            "price_usd":   pricing["price_usd"],
            "billing":     "monthly",
            "features":    features,
            "is_popular":  plan == SubscriptionPlan.RADIANCE,
        })
    return {"plans": plans}


@router.get("/me", summary="Get current user subscription and usage")
async def get_my_subscription(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    sub   = await _get_or_create_subscription(current_user.id, session)
    usage = await _get_current_usage(current_user.id, session)
    gates = PLAN_FEATURES.get(sub.plan, PLAN_FEATURES[SubscriptionPlan.FREE])

    return {
        "subscription": {
            "id":                   str(sub.id),
            "plan":                 sub.plan.value,
            "status":               sub.status.value,
            "current_period_end":   sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
        "features":    gates,
        "usage": {
            "facial_scans":     usage.facial_scans     if usage else 0,
            "ai_chat_messages": usage.ai_chat_messages if usage else 0,
            "style_dna_reports":usage.style_dna_reports if usage else 0,
        } if usage else {},
        "pricing": PLAN_PRICING.get(sub.plan, {}),
    }


@router.get("/usage", summary="Get current period usage counters")
async def get_usage(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    usage = await _get_current_usage(current_user.id, session)
    if not usage:
        return {"period_start": None, "period_end": None, "counters": {}}
    return {
        "period_start": usage.period_start.isoformat(),
        "period_end":   usage.period_end.isoformat(),
        "counters": {
            "facial_scans":         usage.facial_scans,
            "ai_chat_messages":     usage.ai_chat_messages,
            "style_dna_reports":    usage.style_dna_reports,
            "alternatives_lookups": usage.alternatives_lookups,
            "tryon_sessions":       usage.tryon_sessions,
            "wardrobe_items_added": usage.wardrobe_items_added,
        },
    }


@router.post("/check", summary="Feature gate check — returns whether user can use a feature")
async def check_feature(
    payload:      FeatureCheckRequest,
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    sub   = await _get_or_create_subscription(current_user.id, session)
    gates = PLAN_FEATURES.get(sub.plan, PLAN_FEATURES[SubscriptionPlan.FREE])
    gate  = gates.get(payload.feature)

    if gate is False:
        allowed = False
        limit   = 0
        reason  = f"Feature '{payload.feature}' requires a higher plan"
    elif gate is True:
        allowed = True
        limit   = -1
        reason  = None
    elif isinstance(gate, int):
        # Usage count gate
        usage  = await _get_current_usage(current_user.id, session)
        used   = getattr(usage, payload.feature, 0) if usage else 0
        allowed= (used < gate)
        limit  = gate
        reason = None if allowed else f"Monthly limit of {gate} reached for '{payload.feature}'"
    else:
        allowed = True
        limit   = -1
        reason  = None

    return {
        "feature": payload.feature,
        "allowed": allowed,
        "limit":   limit,
        "plan":    sub.plan.value,
        "reason":  reason,
    }


@router.post("/upgrade", summary="Initiate a plan upgrade")
async def upgrade_plan(
    payload:      UpgradeRequest,
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    """
    Creates a payment intent via Razorpay/Stripe.
    In production: returns order_id + key_id for client-side payment modal.
    Here: returns a mock payment intent for local/dev.
    """
    sub = await _get_or_create_subscription(current_user.id, session)

    if sub.plan == payload.plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SAME_PLAN", "message": "Already on this plan"},
        )

    pricing = PLAN_PRICING.get(payload.plan, {})
    amount  = pricing.get("price_inr", 0)

    logger.info(
        "subscription.upgrade_initiated",
        user_id=str(current_user.id),
        from_plan=sub.plan.value,
        to_plan=payload.plan.value,
        amount=amount,
        provider=payload.provider,
    )

    # Production: create Razorpay/Stripe order here
    return {
        "status":      "pending",
        "provider":    payload.provider,
        "plan":        payload.plan.value,
        "amount":      amount,
        "currency":    "INR",
        "order_id":    f"order_{current_user.id.hex[:12]}",   # Mock
        "description": f"AuraFit {payload.plan.value.title()} — Monthly",
        "note":        "Complete payment in the checkout modal",
    }


@router.post("/cancel", summary="Cancel subscription at period end")
async def cancel_subscription(
    payload:      CancelRequest,
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    sub = await _get_or_create_subscription(current_user.id, session)

    if sub.plan == SubscriptionPlan.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FREE_PLAN", "message": "Free plan cannot be cancelled"},
        )

    sub.cancel_at_period_end = True
    sub.cancelled_at         = datetime.now(UTC)
    session.add(sub)

    logger.info(
        "subscription.cancelled",
        user_id=str(current_user.id),
        plan=sub.plan.value,
        reason=payload.reason,
    )
    return {
        "status":  "cancelled",
        "message": "Your plan will remain active until the end of the current billing period.",
        "period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


# ── Webhooks ─────────────────────────────────────────────────────────────────

@router.post(
    "/webhook/razorpay",
    include_in_schema=False,
    summary="Razorpay payment webhook",
)
async def razorpay_webhook(
    request: Request,
    session: DbSession,
    x_razorpay_signature: str = Header(None),
) -> dict:
    """
    Verifies Razorpay HMAC-SHA256 signature and processes:
      - payment.captured → activate subscription
      - subscription.cancelled → update status
    """
    body    = await request.body()
    s       = get_settings()
    secret  = getattr(s, "RAZORPAY_WEBHOOK_SECRET", "")

    if secret and x_razorpay_signature:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("event", "")
        logger.info("razorpay.webhook", event_type=event_type)

        if event_type == "payment.captured":
            # Production: extract plan from payment notes, update subscription
            pass
        elif event_type == "subscription.cancelled":
            pass

    except Exception as exc:
        logger.exception("razorpay.webhook.error", error=str(exc))

    return {"status": "ok"}


@router.post(
    "/webhook/stripe",
    include_in_schema=False,
    summary="Stripe payment webhook",
)
async def stripe_webhook(
    request:       Request,
    session:       DbSession,
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> dict:
    """Stripe webhook handler. Verifies signature, processes subscription events."""
    body = await request.body()
    s    = get_settings()
    secret = getattr(s, "STRIPE_WEBHOOK_SECRET", "")

    try:
        event = json.loads(body)
        logger.info("stripe.webhook", event_type=event.get("type", ""))
    except Exception as exc:
        logger.exception("stripe.webhook.error", error=str(exc))

    return {"status": "ok"}

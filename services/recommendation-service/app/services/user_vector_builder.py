"""
AuraFit — User Preference Vector Builder.

Constructs a UserPreferenceSignals object from:
  1. UserProfile data (skin tone, undertone, style archetypes, concerns, budget)
  2. Active ColorProfile (color season → compatible palettes)
  3. Interaction history (top categories, top brands, interaction count)

This object is the "context" fed into all three recommendation components:
  - CollaborativeFilter: uses user_id
  - ContentBasedFilter: uses user embedding (mean of liked product vectors)
  - ProfileRulesEngine: uses skin_tone, concerns, style_archetypes, color_season
"""
from __future__ import annotations

import uuid
from collections import Counter

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.recommendation_schemas import UserPreferenceSignals

logger = get_logger(__name__)


# Interaction type weights for category/brand preference calculation
_INTERACTION_WEIGHTS = {
    "purchase": 5.0,
    "save":     3.0,
    "like":     2.0,
    "try_on":   2.0,
    "review":   2.5,
    "view":     0.5,
    "dislike": -2.0,
}


class UserVectorBuilder:
    """
    Fetches user data from user-service and interaction history from local DB,
    then computes a preference signal vector.
    """

    def __init__(self, session) -> None:
        self._session  = session
        self._settings = get_settings()

    async def build(self, user_id: uuid.UUID) -> UserPreferenceSignals:
        """Main entry point. Returns a fully-populated UserPreferenceSignals."""
        profile_data  = await self._fetch_user_profile(user_id)
        color_season  = await self._fetch_color_season(user_id)
        interactions  = await self._get_interaction_summary(user_id)

        return UserPreferenceSignals(
            user_id=user_id,
            skin_tone=profile_data.get("skin_tone"),
            undertone=profile_data.get("undertone"),
            skin_concerns=profile_data.get("skin_concerns") or [],
            style_archetypes=profile_data.get("style_archetypes") or [],
            color_season=color_season,
            fragrance_family=profile_data.get("fragrance_family") or [],
            budget_range=profile_data.get("budget_range"),
            interaction_count=interactions["total"],
            top_categories=interactions["top_categories"],
            top_brands=interactions["top_brands"],
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _fetch_user_profile(self, user_id: uuid.UUID) -> dict:
        """Call user-service to get profile data."""
        settings = self._settings
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.USER_SERVICE_URL}/api/v1/users/{user_id}/profile-summary",
                )
                if resp.status_code == 200:
                    return resp.json().get("data") or {}
        except Exception as exc:
            logger.warning("user_vector.profile_fetch_failed", user_id=str(user_id), error=str(exc))
        return {}

    async def _fetch_color_season(self, user_id: uuid.UUID) -> str | None:
        """Get the user's active color season from user-service."""
        settings = self._settings
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.USER_SERVICE_URL}/api/v1/color/profile",
                    headers={"X-Internal-User-ID": str(user_id)},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data")
                    if data:
                        return data.get("season")
        except Exception as exc:
            logger.warning("user_vector.color_fetch_failed", user_id=str(user_id), error=str(exc))
        return None

    async def _get_interaction_summary(self, user_id: uuid.UUID) -> dict:
        """
        Query local interaction table for:
          - total interaction count
          - top 5 interacted categories (weighted by interaction type)
          - top 3 interacted brands
        """
        from sqlalchemy import select, text
        from app.models.catalog import UserProductInteraction, Product

        try:
            result = await self._session.execute(
                select(
                    UserProductInteraction.product_id,
                    UserProductInteraction.interaction_type,
                )
                .where(UserProductInteraction.user_id == user_id)
                .limit(1000)  # Last 1000 interactions max
            )
            rows = result.fetchall()
        except Exception as exc:
            logger.warning("user_vector.interaction_query_failed", user_id=str(user_id), error=str(exc))
            return {"total": 0, "top_categories": [], "top_brands": []}

        if not rows:
            return {"total": 0, "top_categories": [], "top_brands": []}

        # Fetch category + brand for each product (batch)
        product_ids = list({r.product_id for r in rows})
        prod_result = await self._session.execute(
            select(Product.id, Product.category_id, Product.brand_id)
            .where(Product.id.in_(product_ids))
        )
        product_meta = {str(r.id): r for r in prod_result.fetchall()}

        category_scores: Counter = Counter()
        brand_scores:    Counter = Counter()

        for row in rows:
            pid = str(row.product_id)
            weight = _INTERACTION_WEIGHTS.get(row.interaction_type, 1.0)
            if weight <= 0:
                continue
            meta = product_meta.get(pid)
            if meta:
                category_scores[str(meta.category_id)] += weight
                brand_scores[str(meta.brand_id)]       += weight

        return {
            "total":          len(rows),
            "top_categories": [k for k, _ in category_scores.most_common(5)],
            "top_brands":     [k for k, _ in brand_scores.most_common(3)],
        }

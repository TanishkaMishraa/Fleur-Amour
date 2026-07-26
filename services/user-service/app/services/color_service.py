"""
AuraFit — Color Intelligence Service.
Orchestrates:
  1. Load user's active facial scan from DB
  2. Extract color inputs from skin_analysis + hair_analysis JSON
  3. Run ColorIntelligenceEngine.compute() (pure function, ~5ms)
  4. Persist ColorProfile to DB (create or update)
  5. Cache result in Redis (RedisKeys.color_profile)
  6. Return FullColorProfile

Synchronous by design — the engine is fast (~5ms) and has no I/O,
so we don't need a Celery task. The API endpoint can compute inline.
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, cache_delete, cache_get, cache_set
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.color import ColorProfile
from app.repositories.color_repository import ColorRepository
from app.repositories.profile_repository import FacialScanRepository
from app.services.color_engine import ColorIntelligenceEngine, FullColorProfile

logger = get_logger(__name__)

_ENGINE = ColorIntelligenceEngine()       # singleton — no state
_CACHE_TTL = 3600 * 6                     # 6h (re-run after new scan or manual refresh)
_ENGINE_VERSION = "1.0.0"


def _color_cache_key(user_id: str) -> str:
    return f"color_profile:{user_id}"


class ColorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session  = session
        self._repo     = ColorRepository(session)
        self._scan_repo = FacialScanRepository(session)

    # ── Public API ────────────────────────────────────────────────────────────

    async def compute_and_persist(
        self,
        user_id: uuid.UUID,
        scan_id: uuid.UUID | None = None,
        use_extended: bool = True,
    ) -> tuple[ColorProfile, FullColorProfile]:
        """
        Full pipeline: scan → engine → persist → cache.
        Returns (ORM ColorProfile, engine FullColorProfile).
        """
        # 1. Get scan data
        if scan_id:
            scan = await self._scan_repo.get_by_id(scan_id)
            if scan is None or scan.user_id != user_id:
                raise NotFoundError(f"Facial scan {scan_id} not found")
        else:
            scan = await self._scan_repo.get_latest_active(user_id)
            if scan is None:
                raise NotFoundError(
                    "No facial scan found. Please complete a facial scan first to "
                    "generate your personal color profile."
                )

        # 2. Extract inputs from scan JSONB
        inputs = self._extract_inputs(scan)
        logger.info("color.compute.start", user_id=str(user_id), scan_id=str(scan.id))

        # 3. Run engine (pure function)
        full_profile = _ENGINE.compute(inputs)

        # 4. Deactivate previous profiles, persist new
        await self._repo.deactivate_all(user_id)

        orm_profile = await self._repo.create(
            user_id=user_id,
            scan_id=scan.id,
            season=full_profile.season.season,
            season_confidence=full_profile.season.confidence,
            season_description=full_profile.season.description,
            skin_tone=inputs.get("skin_tone"),
            undertone=inputs.get("undertone"),
            skin_hex=inputs.get("skin_hex"),
            ita_angle=inputs.get("ita_angle"),
            fitzpatrick=inputs.get("fitzpatrick"),
            hair_color_hex=inputs.get("hair_color_hex"),
            eye_color=inputs.get("eye_color"),
            palette_best=[{"hex": c.hex, "name": c.name, "category": c.category}
                          for c in full_profile.palette_best],
            palette_avoid=[{"hex": c.hex, "name": c.name, "category": c.category}
                           for c in full_profile.palette_avoid],
            palette_neutrals=[{"hex": c.hex, "name": c.name, "category": c.category}
                              for c in full_profile.palette_neutrals],
            palette_accents=[{"hex": c.hex, "name": c.name, "category": c.category}
                             for c in full_profile.palette_accents],
            makeup_recommendations=full_profile.makeup,
            lipstick_recommendations=full_profile.lipstick,
            hair_color_recommendations=full_profile.hair_color,
            outfit_recommendations=full_profile.outfits,
            jewelry_recommendations=full_profile.jewelry,
            engine_version=_ENGINE_VERSION,
            is_active=True,
        )

        # 5. Cache
        await cache_delete(_color_cache_key(str(user_id)))

        logger.info(
            "color.compute.complete",
            user_id=str(user_id),
            season=full_profile.season.season,
            confidence=full_profile.season.confidence,
        )
        return orm_profile, full_profile

    async def get_active_profile(self, user_id: uuid.UUID) -> ColorProfile | None:
        """Return the user's active color profile (DB only, fast path)."""
        return await self._repo.get_active(user_id)

    async def get_profile_history(self, user_id: uuid.UUID) -> list[ColorProfile]:
        """All color profiles for the user, newest first."""
        return await self._repo.list_by_user(user_id)

    async def delete_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        """Hard delete a specific color profile."""
        profile = await self._repo.get_by_id(profile_id)
        if profile is None or profile.user_id != user_id:
            raise NotFoundError(f"Color profile {profile_id} not found")
        await self._repo.delete(profile)
        await cache_delete(_color_cache_key(str(user_id)))

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_inputs(scan: any) -> dict:
        """
        Pull color-relevant fields from the FacialScan's JSONB columns.
        skin_analysis stores the full Stage 4 pipeline result.
        hair_analysis is nested inside skin_analysis.
        """
        sa: dict = scan.skin_analysis or {}
        ha: dict = sa.get("hair_analysis") or {}
        st: dict = sa.get("skin_tone") or {}

        return {
            "skin_tone":      st.get("tone") or sa.get("skin_tone"),
            "undertone":      st.get("undertone") or sa.get("undertone"),
            "ita_angle":      st.get("ita_angle"),
            "fitzpatrick":    st.get("fitzpatrick"),
            "skin_hex":       st.get("hex_color") or st.get("skin_hex"),
            "hair_color_hex": ha.get("dominant_color"),
            "eye_color":      None,   # Not yet captured in facial pipeline (future)
        }

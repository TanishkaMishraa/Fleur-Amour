"""
AuraFit — Preferences service (Stage 3).
Reads and updates UserPreferences. Invalidates Redis profile cache on change.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, cache_delete
from app.core.logging import get_logger
from app.models.user import UserPreferences
from app.repositories.user_repository import UserPreferencesRepository
from app.schemas.preferences import PreferencesOut, PreferencesUpdateRequest

logger = get_logger(__name__)


class PreferencesService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo    = UserPreferencesRepository(session)

    async def get(self, user_id: uuid.UUID) -> UserPreferences:
        prefs = await self._repo.get_by_user_id(user_id)
        if not prefs:
            # Auto-create if somehow missing (belt-and-suspenders)
            prefs = UserPreferences(user_id=user_id)
            self._session.add(prefs)
            await self._session.flush()
        return prefs

    async def update(
        self, user_id: uuid.UUID, data: PreferencesUpdateRequest
    ) -> UserPreferences:
        prefs   = await self.get(user_id)
        updates = data.model_dump(exclude_none=True)

        if not updates:
            return prefs

        for field, value in updates.items():
            setattr(prefs, field, value)

        self._session.add(prefs)
        await self._session.flush()
        await self._session.refresh(prefs)

        # Invalidate profile cache so next /users/me reflects new prefs
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        logger.info(
            "aurafit.preferences.updated",
            user_id=str(user_id),
            fields=list(updates.keys()),
        )
        return prefs

"""
AuraFit — Profile service layer.
Beauty/style profile management. Fragrance profile management.
Profile cached in Redis (TTL 5 min). Cache invalidated on every update.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, cache_delete
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.analysis import FragranceProfile
from app.models.profile import UserProfile
from app.repositories.profile_repository import (
    FragranceProfileRepository,
    UserProfileRepository,
)
from app.schemas.profile import FragranceProfileRequest, ProfileUpsertRequest

logger = get_logger(__name__)


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._profile_repo = UserProfileRepository(session)
        self._fragrance_repo = FragranceProfileRepository(session)

    async def get_or_create(self, user_id: uuid.UUID) -> UserProfile:
        """Return existing profile or create an empty one."""
        profile = await self._profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self._profile_repo.create(
                user_id=user_id, onboarding_complete=False
            )
            logger.info("aurafit.profile.created", user_id=str(user_id))
        return profile

    async def upsert(
        self, user_id: uuid.UUID, data: ProfileUpsertRequest
    ) -> UserProfile:
        """Create or fully update the user's beauty/style profile."""
        update_kwargs = data.model_dump(exclude_none=True)

        # Convert list fields → raw Python list (JSONB serialisation)
        for jsonb_field in (
            "style_archetypes", "fragrance_family",
            "skin_concerns", "avoided_ingredients"
        ):
            if jsonb_field in update_kwargs:
                update_kwargs[jsonb_field] = list(update_kwargs[jsonb_field])

        profile = await self._profile_repo.upsert(user_id, **update_kwargs)
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        logger.info(
            "aurafit.profile.updated",
            user_id=str(user_id),
            fields=list(update_kwargs.keys()),
        )
        return profile

    async def mark_onboarding_complete(self, user_id: uuid.UUID) -> UserProfile:
        profile = await self.get_or_create(user_id)
        profile = await self._profile_repo.update(
            profile, onboarding_complete=True
        )
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        return profile

    async def get_fragrance_profile(
        self, profile_id: uuid.UUID
    ) -> FragranceProfile | None:
        return await self._fragrance_repo.get_by_profile_id(profile_id)

    async def upsert_fragrance_profile(
        self,
        user_id: uuid.UUID,
        data: FragranceProfileRequest,
    ) -> FragranceProfile:
        profile = await self.get_or_create(user_id)
        kwargs = data.model_dump(exclude_none=True)
        fragrance = await self._fragrance_repo.upsert(profile.id, **kwargs)
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        return fragrance

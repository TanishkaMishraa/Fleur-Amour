"""
AuraFit — Profile, FacialScan, and FragranceProfile repositories.
All DB access for the beauty/style profile domain.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import FacialScan, FragranceProfile
from app.models.profile import UserProfile
from app.repositories.base import BaseRepository


class UserProfileRepository(BaseRepository[UserProfile]):
    model = UserProfile

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserProfile, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, **kwargs) -> UserProfile:
        """Create if not exists, otherwise update with provided kwargs."""
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            return await self.create(user_id=user_id, **kwargs)
        return await self.update(profile, **kwargs)


class FacialScanRepository(BaseRepository[FacialScan]):
    model = FacialScan

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FacialScan, session)

    async def list_by_user(self, user_id: uuid.UUID) -> list[FacialScan]:
        result = await self._session.execute(
            select(FacialScan)
            .where(FacialScan.user_id == user_id)
            .order_by(FacialScan.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_active(self, user_id: uuid.UUID) -> FacialScan | None:
        result = await self._session.execute(
            select(FacialScan)
            .where(FacialScan.user_id == user_id)
            .where(FacialScan.is_active == True)  # noqa: E712
            .order_by(FacialScan.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def deactivate_all(self, user_id: uuid.UUID) -> None:
        """Deactivate previous scans before activating a new one."""
        from sqlalchemy import update
        await self._session.execute(
            update(FacialScan)
            .where(FacialScan.user_id == user_id)
            .values(is_active=False)
        )


class FragranceProfileRepository(BaseRepository[FragranceProfile]):
    model = FragranceProfile

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FragranceProfile, session)

    async def get_by_profile_id(
        self, profile_id: uuid.UUID
    ) -> FragranceProfile | None:
        result = await self._session.execute(
            select(FragranceProfile).where(
                FragranceProfile.user_profile_id == profile_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, profile_id: uuid.UUID, **kwargs) -> FragranceProfile:
        existing = await self.get_by_profile_id(profile_id)
        if existing is None:
            return await self.create(user_profile_id=profile_id, **kwargs)
        return await self.update(existing, **kwargs)

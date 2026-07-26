"""
AuraFit — Color Profile repository.
DB access for ColorProfile. No business logic.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.color import ColorProfile
from app.repositories.base import BaseRepository


class ColorRepository(BaseRepository[ColorProfile]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ColorProfile, session)

    async def get_active(self, user_id: uuid.UUID) -> ColorProfile | None:
        """Return the single active color profile for a user."""
        result = await self.session.execute(
            select(ColorProfile)
            .where(ColorProfile.user_id == user_id)
            .where(ColorProfile.is_active == True)   # noqa: E712
            .order_by(ColorProfile.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[ColorProfile]:
        """All profiles for a user, newest first."""
        result = await self.session.execute(
            select(ColorProfile)
            .where(ColorProfile.user_id == user_id)
            .order_by(ColorProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_all(self, user_id: uuid.UUID) -> None:
        """Set is_active=False on all existing profiles before inserting a new one."""
        await self.session.execute(
            update(ColorProfile)
            .where(ColorProfile.user_id == user_id)
            .values(is_active=False)
        )
        await self.session.flush()

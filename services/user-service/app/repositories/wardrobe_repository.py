"""
AuraFit — Wardrobe, WardrobeItem, and Outfit repositories.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.wardrobe import Outfit, OutfitItem, Wardrobe, WardrobeItem
from app.repositories.base import BaseRepository


class WardrobeRepository(BaseRepository[Wardrobe]):
    model = Wardrobe

    async def list_by_user(self, user_id: uuid.UUID) -> list[Wardrobe]:
        result = await self._session.execute(
            select(Wardrobe)
            .where(Wardrobe.user_id == user_id)
            .order_by(Wardrobe.is_default.desc(), Wardrobe.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_owned(
        self, wardrobe_id: uuid.UUID, user_id: uuid.UUID
    ) -> Wardrobe | None:
        result = await self._session.execute(
            select(Wardrobe)
            .where(Wardrobe.id == wardrobe_id)
            .where(Wardrobe.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_default(self, user_id: uuid.UUID) -> Wardrobe | None:
        result = await self._session.execute(
            select(Wardrobe)
            .where(Wardrobe.user_id == user_id)
            .where(Wardrobe.is_default == True)  # noqa: E712
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def clear_default(self, user_id: uuid.UUID) -> None:
        """Unset is_default on all wardrobes before setting a new default."""
        from sqlalchemy import update
        await self._session.execute(
            update(Wardrobe)
            .where(Wardrobe.user_id == user_id)
            .values(is_default=False)
        )


class WardrobeItemRepository(BaseRepository[WardrobeItem]):
    model = WardrobeItem

    async def list_for_wardrobe(
        self,
        wardrobe_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WardrobeItem], int]:
        rows, total = await self.list(
            offset=offset,
            limit=limit,
            order_by=WardrobeItem.created_at.desc(),
            wardrobe_id=wardrobe_id,
        )
        return list(rows), total

    async def get_owned(
        self, item_id: uuid.UUID, wardrobe_id: uuid.UUID
    ) -> WardrobeItem | None:
        result = await self._session.execute(
            select(WardrobeItem)
            .where(WardrobeItem.id == item_id)
            .where(WardrobeItem.wardrobe_id == wardrobe_id)
            .where(WardrobeItem.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def increment_worn(self, item_id: uuid.UUID) -> None:
        from datetime import UTC, datetime
        from sqlalchemy import update
        await self._session.execute(
            update(WardrobeItem)
            .where(WardrobeItem.id == item_id)
            .values(
                times_worn=WardrobeItem.times_worn + 1,
                last_worn_at=datetime.now(UTC),
            )
        )


class OutfitRepository(BaseRepository[Outfit]):
    model = Outfit

    async def list_by_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Outfit], int]:
        rows, total = await self.list(
            offset=offset, limit=limit,
            order_by=Outfit.created_at.desc(),
            user_id=user_id,
        )
        return list(rows), total

    async def get_with_items(self, outfit_id: uuid.UUID) -> Outfit | None:
        result = await self._session.execute(
            select(Outfit)
            .where(Outfit.id == outfit_id)
            .options(
                selectinload(Outfit.items).selectinload(OutfitItem.wardrobe_item)
            )
        )
        return result.scalar_one_or_none()

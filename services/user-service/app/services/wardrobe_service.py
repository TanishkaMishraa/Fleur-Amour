"""
AuraFit — Wardrobe service layer.
Wardrobe CRUD, item management, outfit management, AI outfit generation dispatch.
All ownership checks enforced here — never trust user-supplied IDs alone.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.models.wardrobe import Outfit, Wardrobe, WardrobeItem
from app.repositories.wardrobe_repository import (
    OutfitRepository,
    WardrobeItemRepository,
    WardrobeRepository,
)
from app.schemas.wardrobe import (
    OutfitCreateRequest,
    OutfitGenerateRequest,
    WardrobeCreateRequest,
    WardrobeItemCreateRequest,
    WardrobeItemUpdateRequest,
)

logger = get_logger(__name__)


class WardrobeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._wardrobe_repo = WardrobeRepository(session)
        self._item_repo = WardrobeItemRepository(session)
        self._outfit_repo = OutfitRepository(session)

    # ── Wardrobes ─────────────────────────────────────────────────────────────

    async def list_wardrobes(self, user_id: uuid.UUID) -> list[Wardrobe]:
        return await self._wardrobe_repo.list_by_user(user_id)

    async def create_wardrobe(
        self, user_id: uuid.UUID, data: WardrobeCreateRequest
    ) -> Wardrobe:
        if data.is_default:
            await self._wardrobe_repo.clear_default(user_id)
        wardrobe = await self._wardrobe_repo.create(
            user_id=user_id,
            name=data.name,
            is_default=data.is_default,
        )
        logger.info("aurafit.wardrobe.created", wardrobe_id=str(wardrobe.id))
        return wardrobe

    async def delete_wardrobe(
        self, wardrobe_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        wardrobe = await self._get_owned_wardrobe(wardrobe_id, user_id)
        await self._wardrobe_repo.delete(wardrobe)

    async def _get_owned_wardrobe(
        self, wardrobe_id: uuid.UUID, user_id: uuid.UUID
    ) -> Wardrobe:
        wardrobe = await self._wardrobe_repo.get_owned(wardrobe_id, user_id)
        if wardrobe is None:
            raise NotFoundError("Wardrobe not found")
        return wardrobe

    # ── Wardrobe items ────────────────────────────────────────────────────────

    async def list_items(
        self,
        wardrobe_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WardrobeItem], int]:
        await self._get_owned_wardrobe(wardrobe_id, user_id)
        return await self._item_repo.list_for_wardrobe(
            wardrobe_id, offset=offset, limit=limit
        )

    async def add_item(
        self,
        wardrobe_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WardrobeItemCreateRequest,
    ) -> WardrobeItem:
        await self._get_owned_wardrobe(wardrobe_id, user_id)
        item = await self._item_repo.create(
            wardrobe_id=wardrobe_id,
            **data.model_dump(exclude_none=True),
        )
        logger.info("aurafit.wardrobe.item_added", item_id=str(item.id))
        return item

    async def update_item(
        self,
        wardrobe_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        data: WardrobeItemUpdateRequest,
    ) -> WardrobeItem:
        await self._get_owned_wardrobe(wardrobe_id, user_id)
        item = await self._item_repo.get_owned(item_id, wardrobe_id)
        if item is None:
            raise NotFoundError("Wardrobe item not found")
        updates = data.model_dump(exclude_none=True)
        return await self._item_repo.update(item, **updates)

    async def remove_item(
        self,
        wardrobe_id: uuid.UUID,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._get_owned_wardrobe(wardrobe_id, user_id)
        item = await self._item_repo.get_owned(item_id, wardrobe_id)
        if item is None:
            raise NotFoundError("Wardrobe item not found")
        await self._item_repo.soft_delete(item)

    # ── Outfits ───────────────────────────────────────────────────────────────

    async def list_outfits(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Outfit], int]:
        return await self._outfit_repo.list_by_user(
            user_id, offset=offset, limit=limit
        )

    async def create_outfit(
        self, user_id: uuid.UUID, data: OutfitCreateRequest
    ) -> Outfit:
        outfit = await self._outfit_repo.create(
            user_id=user_id,
            name=data.name,
            occasion=data.occasion,
            season=data.season,
            style_tags=data.style_tags,
        )
        logger.info("aurafit.outfit.created", outfit_id=str(outfit.id))
        return outfit

    async def generate_outfit(
        self,
        outfit_id: uuid.UUID,
        user_id: uuid.UUID,
        data: OutfitGenerateRequest,
    ) -> dict:
        """
        Dispatch AI outfit generation Celery task.
        Returns task_id for client polling.
        """
        outfit = await self._outfit_repo.get_by_id_or_raise(outfit_id)
        if outfit.user_id != user_id:
            raise PermissionDeniedError("Access denied")

        from app.tasks.ai_tasks import run_outfit_generation
        task = run_outfit_generation.delay(
            user_id=str(user_id),
            outfit_id=str(outfit_id),
            occasion=data.occasion,
            season=data.season,
        )
        logger.info(
            "aurafit.outfit.generation_dispatched",
            outfit_id=str(outfit_id),
            task_id=task.id,
        )
        return {"task_id": task.id, "status": "PENDING"}

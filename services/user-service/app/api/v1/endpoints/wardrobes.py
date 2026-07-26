"""
AuraFit — Wardrobe and outfit endpoints (/api/v1/wardrobes/*).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.dependencies import CurrentUser, WardrobeServiceDep
from app.schemas.base import APIResponse
from app.schemas.wardrobe import (
    OutfitCreateRequest,
    OutfitGenerateRequest,
    OutfitOut,
    WardrobeCreateRequest,
    WardrobeItemCreateRequest,
    WardrobeItemOut,
    WardrobeItemUpdateRequest,
    WardrobeOut,
)

router = APIRouter(prefix="/wardrobes", tags=["Wardrobe"])


@router.get("", response_model=APIResponse[list[WardrobeOut]], summary="List my wardrobes")
async def list_wardrobes(
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[list[WardrobeOut]]:
    wardrobes = await svc.list_wardrobes(current_user.id)
    return APIResponse(data=[WardrobeOut.model_validate(w) for w in wardrobes])


@router.post(
    "",
    response_model=APIResponse[WardrobeOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new wardrobe",
)
async def create_wardrobe(
    payload: WardrobeCreateRequest,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[WardrobeOut]:
    wardrobe = await svc.create_wardrobe(current_user.id, payload)
    return APIResponse(data=WardrobeOut.model_validate(wardrobe))


@router.get(
    "/{wardrobe_id}/items",
    response_model=APIResponse[list[WardrobeItemOut]],
    summary="List items in a wardrobe",
)
async def list_items(
    wardrobe_id: UUID,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> APIResponse[list[WardrobeItemOut]]:
    items = await svc.list_items(wardrobe_id, current_user.id, offset=offset, limit=limit)
    return APIResponse(data=[WardrobeItemOut.model_validate(i) for i in items])


@router.post(
    "/{wardrobe_id}/items",
    response_model=APIResponse[WardrobeItemOut],
    status_code=status.HTTP_201_CREATED,
    summary="Add item to wardrobe",
)
async def add_item(
    wardrobe_id: UUID,
    payload: WardrobeItemCreateRequest,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[WardrobeItemOut]:
    item = await svc.add_item(wardrobe_id, current_user.id, payload)
    return APIResponse(data=WardrobeItemOut.model_validate(item))


@router.patch(
    "/{wardrobe_id}/items/{item_id}",
    response_model=APIResponse[WardrobeItemOut],
    summary="Update wardrobe item",
)
async def update_item(
    wardrobe_id: UUID,
    item_id: UUID,
    payload: WardrobeItemUpdateRequest,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[WardrobeItemOut]:
    item = await svc.update_item(wardrobe_id, item_id, current_user.id, payload)
    return APIResponse(data=WardrobeItemOut.model_validate(item))


@router.delete(
    "/{wardrobe_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove item from wardrobe",
)
async def remove_item(
    wardrobe_id: UUID,
    item_id: UUID,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> None:
    await svc.remove_item(wardrobe_id, item_id, current_user.id)


# ── Outfits ───────────────────────────────────────────────────────────────────

@router.get("/outfits", response_model=APIResponse[list[OutfitOut]], summary="List outfits")
async def list_outfits(
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[list[OutfitOut]]:
    outfits = await svc.list_outfits(current_user.id)
    return APIResponse(data=[OutfitOut.model_validate(o) for o in outfits])


@router.post(
    "/outfits",
    response_model=APIResponse[OutfitOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create outfit",
)
async def create_outfit(
    payload: OutfitCreateRequest,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[OutfitOut]:
    outfit = await svc.create_outfit(current_user.id, payload)
    return APIResponse(data=OutfitOut.model_validate(outfit))


@router.post(
    "/outfits/{outfit_id}/generate",
    response_model=APIResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate outfit with AI (async)",
)
async def generate_outfit(
    outfit_id: UUID,
    payload: OutfitGenerateRequest,
    current_user: CurrentUser,
    svc: WardrobeServiceDep,
) -> APIResponse[dict]:
    task_id = await svc.generate_outfit_async(outfit_id, current_user.id, payload)
    return APIResponse(data={"task_id": task_id}, message="Outfit generation queued")

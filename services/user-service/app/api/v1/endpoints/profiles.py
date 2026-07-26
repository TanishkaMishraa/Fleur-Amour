"""
AuraFit — Beauty/style profile endpoints (/api/v1/profiles/*).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser, ProfileServiceDep
from app.schemas.base import APIResponse
from app.schemas.profile import (
    FragranceProfileOut,
    FragranceProfileRequest,
    ProfileOut,
    ProfileUpsertRequest,
)

router = APIRouter(prefix="/profiles", tags=["Beauty Profile"])


@router.get(
    "/me",
    response_model=APIResponse[ProfileOut | None],
    summary="Get my beauty/style profile",
)
async def get_profile(
    current_user: CurrentUser,
    svc: ProfileServiceDep,
) -> APIResponse[ProfileOut | None]:
    profile = await svc.get_or_create(current_user.id)
    return APIResponse(data=ProfileOut.model_validate(profile))


@router.put(
    "/me",
    response_model=APIResponse[ProfileOut],
    summary="Create or update my beauty/style profile",
)
async def upsert_profile(
    payload: ProfileUpsertRequest,
    current_user: CurrentUser,
    svc: ProfileServiceDep,
) -> APIResponse[ProfileOut]:
    profile = await svc.upsert(current_user.id, payload)
    return APIResponse(data=ProfileOut.model_validate(profile))


@router.post(
    "/me/onboarding-complete",
    response_model=APIResponse[ProfileOut],
    summary="Mark onboarding quiz as complete",
)
async def complete_onboarding(
    current_user: CurrentUser,
    svc: ProfileServiceDep,
) -> APIResponse[ProfileOut]:
    profile = await svc.mark_onboarding_complete(current_user.id)
    return APIResponse(data=ProfileOut.model_validate(profile))


@router.get(
    "/me/fragrance",
    response_model=APIResponse[FragranceProfileOut | None],
    summary="Get fragrance preferences",
)
async def get_fragrance_profile(
    current_user: CurrentUser,
    svc: ProfileServiceDep,
) -> APIResponse[FragranceProfileOut | None]:
    base_profile = await svc.get_or_create(current_user.id)
    fragrance = await svc.get_fragrance_profile(base_profile.id)
    return APIResponse(
        data=FragranceProfileOut.model_validate(fragrance) if fragrance else None
    )


@router.put(
    "/me/fragrance",
    response_model=APIResponse[FragranceProfileOut],
    summary="Update fragrance preferences",
)
async def upsert_fragrance_profile(
    payload: FragranceProfileRequest,
    current_user: CurrentUser,
    svc: ProfileServiceDep,
) -> APIResponse[FragranceProfileOut]:
    fragrance = await svc.upsert_fragrance_profile(current_user.id, payload)
    return APIResponse(data=FragranceProfileOut.model_validate(fragrance))

"""
AuraFit — User preferences endpoints (/api/v1/preferences/*).
GET + PATCH for notification, display, and privacy settings.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.dependencies import CurrentUser, PreferencesServiceDep
from app.schemas.base import APIResponse
from app.schemas.preferences import PreferencesOut, PreferencesUpdateRequest

router = APIRouter(prefix="/preferences", tags=["User Preferences"])


@router.get(
    "",
    response_model=APIResponse[PreferencesOut],
    summary="Get current user preferences",
)
async def get_preferences(
    current_user: CurrentUser,
    svc: PreferencesServiceDep,
) -> APIResponse[PreferencesOut]:
    prefs = await svc.get(current_user.id)
    return APIResponse(data=PreferencesOut.model_validate(prefs))


@router.patch(
    "",
    response_model=APIResponse[PreferencesOut],
    summary="Update user preferences (partial update — PATCH semantics)",
)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: CurrentUser,
    svc: PreferencesServiceDep,
) -> APIResponse[PreferencesOut]:
    prefs = await svc.update(current_user.id, payload)
    return APIResponse(
        data=PreferencesOut.model_validate(prefs),
        message="Preferences updated.",
    )

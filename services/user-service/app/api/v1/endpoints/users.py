"""
AuraFit — User account endpoints (/api/v1/users/*).
Covers: account, preferences, sessions, security info, GDPR export, avatar.
All endpoints require a valid JWT (CurrentUser dependency).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.api.v1.dependencies import (
    AuthServiceDep,
    CurrentUser,
    UserServiceDep,
    get_auth_service,
    get_user_service,
    require_role,
)
from app.models.user import UserRole
from app.schemas.auth import (
    MFADisableRequest,
    MFASetupRequest,
    PasswordChangeRequest,
    SessionRevokeRequest,
)
from app.schemas.base import APIResponse
from app.schemas.auth import MFASetupResponse, SessionOut
from app.schemas.user import (
    DataExportRequest,
    PreferencesOut,
    PreferencesUpdateRequest,
    UserOut,
    UserSecurityOut,
    UserUpdateRequest,
)
from app.core.errors import AuthenticationError, NotFoundError, TokenError

router = APIRouter(prefix="/users", tags=["Users"])


# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNT
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/me",
    response_model=APIResponse[UserOut],
    summary="Get current authenticated user",
)
async def get_me(current_user: CurrentUser) -> APIResponse[UserOut]:
    return APIResponse(data=UserOut.model_validate(current_user))


@router.patch(
    "/me",
    response_model=APIResponse[UserOut],
    summary="Update display name",
)
async def update_me(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> APIResponse[UserOut]:
    user = await svc.update_me(current_user.id, payload)
    return APIResponse(data=UserOut.model_validate(user))


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Deactivate account — soft delete, GDPR erasure queued",
)
async def delete_me(
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> None:
    await svc.deactivate(current_user.id)


# ══════════════════════════════════════════════════════════════════════════════
# AVATAR
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/me/avatar",
    response_model=APIResponse[dict],
    summary="Upload user avatar",
)
async def upload_avatar(
    file: UploadFile,
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> APIResponse[dict]:
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "INVALID_FILE_TYPE", "message": "Only JPEG, PNG, or WebP images are accepted"},
        )
    avatar_url = await svc.upload_avatar(current_user.id, file)
    return APIResponse(data={"avatar_url": avatar_url})


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove user avatar",
)
async def remove_avatar(
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> None:
    await svc.remove_avatar(current_user.id)


# ══════════════════════════════════════════════════════════════════════════════
# PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/me/preferences",
    response_model=APIResponse[PreferencesOut],
    summary="Get user notification, display, and privacy preferences",
)
async def get_preferences(
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> APIResponse[PreferencesOut]:
    prefs = await svc.get_preferences(current_user.id)
    return APIResponse(data=PreferencesOut.model_validate(prefs))


@router.patch(
    "/me/preferences",
    response_model=APIResponse[PreferencesOut],
    summary="Update one or more user preferences",
)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> APIResponse[PreferencesOut]:
    prefs = await svc.update_preferences(current_user.id, payload)
    return APIResponse(data=PreferencesOut.model_validate(prefs))


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY / SESSIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/me/security",
    response_model=APIResponse[UserSecurityOut],
    summary="Get security overview — login history, MFA status, session count",
)
async def get_security(
    current_user: CurrentUser,
    svc: UserServiceDep,
) -> APIResponse[UserSecurityOut]:
    data = await svc.get_security_info(current_user.id)
    return APIResponse(data=data)


@router.get(
    "/me/sessions",
    response_model=APIResponse[list[SessionOut]],
    summary="List all active device sessions",
)
async def list_sessions(
    request: Request,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> APIResponse[list[SessionOut]]:
    sessions = await auth_svc.list_sessions(current_user.id)
    return APIResponse(data=sessions)


@router.delete(
    "/me/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke a specific device session",
)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> None:
    try:
        await auth_svc.revoke_session(current_user.id, session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": exc.code, "message": exc.message})


@router.delete(
    "/me/sessions/others",
    response_model=APIResponse[dict],
    summary="Revoke all sessions except the current one",
)
async def revoke_other_sessions(
    request: Request,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> APIResponse[dict]:
    # Best-effort: get current session ID from request state
    current_session_id_str = getattr(request.state, "session_id", None)
    try:
        current_session_id = uuid.UUID(current_session_id_str) if current_session_id_str else None
    except ValueError:
        current_session_id = None

    if not current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SESSION_NOT_FOUND", "message": "Could not identify current session"},
        )
    count = await auth_svc.revoke_all_other_sessions(current_user.id, current_session_id)
    return APIResponse(data={"revoked": count}, message=f"{count} session(s) revoked")


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Change password (requires current password)",
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> None:
    try:
        await auth_svc.change_password(
            current_user.id, payload.current_password, payload.new_password
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )


# ══════════════════════════════════════════════════════════════════════════════
# MFA
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/me/mfa/setup",
    response_model=APIResponse[MFASetupResponse],
    summary="Initiate MFA setup — returns TOTP secret + QR code + backup codes",
)
async def setup_mfa(
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> APIResponse[MFASetupResponse]:
    resp = await auth_svc.setup_mfa(current_user.id)
    return APIResponse(data=resp)


@router.post(
    "/me/mfa/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Confirm MFA setup with first TOTP code — activates MFA",
)
async def confirm_mfa(
    payload: MFASetupRequest,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> None:
    try:
        await auth_svc.confirm_mfa_setup(current_user.id, payload.code)
    except (TokenError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )


@router.post(
    "/me/mfa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Disable MFA — requires password + TOTP code",
)
async def disable_mfa(
    payload: MFADisableRequest,
    current_user: CurrentUser,
    auth_svc: AuthServiceDep,
) -> None:
    try:
        await auth_svc.disable_mfa(current_user.id, payload.password, payload.code)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )


# ══════════════════════════════════════════════════════════════════════════════
# GDPR
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/me/export",
    response_model=APIResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request GDPR data export — dispatches async Celery job",
)
async def request_data_export(
    payload: DataExportRequest,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    from app.tasks.maintenance_tasks import export_user_data_task
    task = export_user_data_task.delay(
        user_id=str(current_user.id),
        include_interactions=payload.include_interactions,
        include_scan_data=payload.include_scan_data,
        include_chat_history=payload.include_chat_history,
    )
    return APIResponse(
        data={"task_id": task.id},
        message="Your data export has been queued. You will receive an email when it's ready.",
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN (role-gated)
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{user_id}",
    response_model=APIResponse[UserOut],
    summary="[Admin] Get any user by ID",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def admin_get_user(
    user_id: uuid.UUID,
    svc: UserServiceDep,
    _: CurrentUser,
) -> APIResponse[UserOut]:
    user = await svc.get_by_id(user_id)
    return APIResponse(data=UserOut.model_validate(user))

"""
AuraFit — MFA (TOTP) endpoints (/api/v1/mfa/*).
Setup, confirm, disable TOTP 2-factor authentication.
Backup codes generated at setup time.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencies import AuthServiceDep, CurrentUser
from app.core.errors import AuthenticationError, TokenError
from app.schemas.auth import (
    ConfirmMFARequest,
    DisableMFARequest,
    MFASetupResponse,
)
from app.schemas.base import APIResponse

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])


@router.post(
    "/setup",
    response_model=APIResponse[MFASetupResponse],
    summary="Initiate TOTP MFA setup — returns QR code and backup codes",
)
async def setup_mfa(
    current_user: CurrentUser,
    svc: AuthServiceDep,
) -> APIResponse[MFASetupResponse]:
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "MFA_ALREADY_ENABLED", "message": "MFA is already enabled"},
        )
    result = await svc.setup_mfa(current_user.id)
    return APIResponse(
        data=result,
        message="Scan the QR code with your authenticator app, then confirm with a code.",
    )


@router.post(
    "/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Confirm MFA setup with first TOTP code — activates MFA",
)
async def confirm_mfa(
    payload: ConfirmMFARequest,
    current_user: CurrentUser,
    svc: AuthServiceDep,
) -> None:
    try:
        await svc.confirm_mfa_setup(current_user.id, payload.code)
    except (TokenError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )


@router.post(
    "/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Disable MFA — requires current password and a valid TOTP code",
)
async def disable_mfa(
    payload: DisableMFARequest,
    current_user: CurrentUser,
    svc: AuthServiceDep,
) -> None:
    try:
        await svc.disable_mfa(current_user.id, payload.password, payload.code)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        )

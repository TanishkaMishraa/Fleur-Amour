"""
AuraFit — Session management endpoints (/api/v1/sessions/*).
List active sessions, revoke a specific session, revoke all others.
Used by the Security page in the frontend.
"""
from __future__ import annotations

import uuid

import hashlib

from fastapi import APIRouter, Cookie, HTTPException, status

from app.api.v1.dependencies import AuthServiceDep, CurrentUser
from app.core.errors import NotFoundError
from app.schemas.base import APIResponse
from app.schemas.session import RevokeSessionRequest, SessionListOut

router = APIRouter(prefix="/sessions", tags=["Session Management"])

_COOKIE = "refresh_token"


@router.get(
    "",
    response_model=APIResponse[SessionListOut],
    summary="List all active sessions for the current user",
)
async def list_sessions(
    current_user: CurrentUser,
    svc: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
) -> APIResponse[SessionListOut]:
    current_hash: str | None = None
    if refresh_token:
        current_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    sessions = await svc.list_sessions(current_user.id, current_refresh_hash=current_hash)
    return APIResponse(
        data=SessionListOut(sessions=sessions, total=len(sessions))
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke a specific session (sign out that device)",
)
async def revoke_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    svc: AuthServiceDep,
) -> None:
    try:
        await svc.revoke_session(current_user.id, session_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )


@router.delete(
    "",
    response_model=APIResponse[dict],
    summary="Revoke all other sessions — keep the current session active",
)
async def revoke_all_other_sessions(
    current_user: CurrentUser,
    svc: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
) -> APIResponse[dict]:
    # Identify the current session by its refresh token hash
    current_hash = hashlib.sha256(refresh_token.encode()).hexdigest() if refresh_token else None

    from app.repositories.user_repository import UserSessionRepository
    from app.db.session import get_session_factory
    # We go via the service method which accepts current_session_id
    # We need to find the current session ID from its hash first
    from sqlalchemy import select
    from app.models.user import UserSession

    factory = get_session_factory()
    async with factory() as db:
        session_row = None
        if current_hash:
            result = await db.execute(
                select(UserSession)
                .where(UserSession.refresh_token_hash == current_hash)
                .where(UserSession.is_active == True)  # noqa: E712
            )
            session_row = result.scalar_one_or_none()

        if session_row:
            revoked = await svc.revoke_all_other_sessions(current_user.id, session_row.id)
        else:
            revoked = 0

    return APIResponse(
        data={"revoked_count": revoked},
        message=f"Revoked {revoked} other session(s).",
    )

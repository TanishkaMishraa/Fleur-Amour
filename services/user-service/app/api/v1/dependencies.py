"""
AuraFit — FastAPI dependency injection (Stage 3: full auth + RBAC).
get_current_user: validates RS256 JWT, checks blocklist, returns live User object.
require_role:     RBAC factory — raises 403 if role not in allowed set.
Service factories: typed Annotated deps consumed by all endpoints.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, get_redis
from app.core.security import decode_access_token, extract_token_from_header
from app.db.session import get_db_session
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.color_service import ColorService
from app.services.preferences_service import PreferencesService
from app.services.profile_service import ProfileService
from app.services.style_dna.style_dna_service import StyleDNAService
from app.services.upload_service import UploadService
from app.services.user_service import UserService
from app.services.wardrobe_service import WardrobeService

# ── Core DB session dependency ────────────────────────────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── JWT authentication dependency ─────────────────────────────────────────────

async def get_current_user(
    request: Request,
    session: DbSession,
) -> User:
    """
    1. Extract Bearer token from Authorization header.
    2. Verify RS256 signature with public key.
    3. Check JTI against Redis blocklist (logout revocation).
    4. Load live User from DB — ensures account is still active.
    Raises HTTP 401 on any failure.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": "Authentication required"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    authorization = request.headers.get("Authorization", "")
    try:
        token   = extract_token_from_header(authorization)
        payload = decode_access_token(token)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exc

    # Attach decoded payload to request.state for downstream use (logout JTI, etc.)
    request.state.jwt_payload = payload

    # Blocklist check (O(1) Redis GET)
    jti: str = payload.get("jti", "")
    if jti:
        r = get_redis()
        if await r.exists(RedisKeys.token_blocklist(jti)):
            raise credentials_exc

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise credentials_exc

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exc

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_INACTIVE", "message": "Account not found or deactivated"},
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── RBAC guard factory ────────────────────────────────────────────────────────

def require_role(*roles: UserRole):
    """
    Role-based access control. Returns a FastAPI dependency.
    Usage: Depends(require_role(UserRole.ADMIN))
           Depends(require_role(UserRole.ADMIN, UserRole.STYLIST))
    """
    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Requires role: {', '.join(r.value for r in roles)}",
                },
            )
        return current_user
    return _check


# ── Service factories ─────────────────────────────────────────────────────────

def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


def get_user_service(session: DbSession) -> UserService:
    return UserService(session)


def get_profile_service(session: DbSession) -> ProfileService:
    return ProfileService(session)


def get_analysis_service(session: DbSession) -> AnalysisService:
    return AnalysisService(session)


def get_chat_service(session: DbSession) -> ChatService:
    return ChatService(session)


def get_upload_service(session: DbSession) -> UploadService:
    return UploadService(session)


def get_wardrobe_service(session: DbSession) -> WardrobeService:
    return WardrobeService(session)


AuthServiceDep   = Annotated[AuthService,   Depends(get_auth_service)]
UserServiceDep   = Annotated[UserService,   Depends(get_user_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
WardrobeServiceDep = Annotated[WardrobeService, Depends(get_wardrobe_service)]


def get_preferences_service(session: DbSession) -> PreferencesService:
    return PreferencesService(session)


PreferencesServiceDep = Annotated[
    PreferencesService,
    Depends(get_preferences_service),
]


def get_color_service(session: DbSession) -> ColorService:
    return ColorService(session)


ColorServiceDep = Annotated[
    ColorService,
    Depends(get_color_service),
]


def get_style_dna_service(session: DbSession) -> StyleDNAService:
    return StyleDNAService(session)


StyleDNAServiceDep = Annotated[
    StyleDNAService,
    Depends(get_style_dna_service),
]

"""
AuraFit — Auth endpoints (/api/v1/auth/*).
Register, login, OAuth, email verification, password reset, MFA, token refresh.
Thin layer: validate input → delegate to AuthService → shape response.
Refresh token always in HttpOnly Secure cookie. Never in response body.
"""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Request, Response, status, HTTPException

from app.api.v1.dependencies import AuthServiceDep, CurrentUser
from app.core.config import get_settings
from app.core.errors import (
    AccountLockedError, AlreadyExistsError,
    AuthenticationError, PermissionDeniedError, TokenError,
)
from app.schemas.auth import (
    LoginRequest, OAuthCallbackRequest,
    PasswordResetConfirmSchema, PasswordResetRequestSchema,
    RegisterRequest, ResendVerificationRequest,
    TokenResponse,
)
from app.schemas.base import APIResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])
_settings = get_settings()

_COOKIE_NAME = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set HttpOnly Secure SameSite=strict refresh token cookie."""
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not _settings.is_local,
        samesite="strict",
        max_age=_settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(_COOKIE_NAME, path=_COOKIE_PATH)


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION & LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/register",
    response_model=APIResponse[UserOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new AuraFit account",
)
async def register(
    payload: RegisterRequest,
    svc: AuthServiceDep,
) -> APIResponse[UserOut]:
    try:
        user = await svc.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except AlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        )
    return APIResponse(
        data=UserOut.model_validate(user),
        message="Account created. Please check your email to verify your address.",
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Login — returns access token (body) + refresh token (HttpOnly cookie)",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    svc: AuthServiceDep,
) -> APIResponse[TokenResponse]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    try:
        token_pair = await svc.login(
            email=payload.email,
            password=payload.password,
            mfa_code=payload.mfa_code,
            ip_address=ip,
            user_agent=ua,
        )
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={"code": exc.code, "message": exc.message},
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        )

    _set_refresh_cookie(response, token_pair.refresh_token)
    return APIResponse(data=token_pair.access)


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Rotate refresh token — issues new access + refresh tokens",
)
async def refresh(
    response: Response,
    svc: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_NAME),
) -> APIResponse[TokenResponse]:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_MISSING", "message": "Refresh token cookie not present"},
        )
    try:
        token_resp = await svc.refresh(refresh_token)
    except TokenError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        )
    if token_resp.new_refresh_token:
        _set_refresh_cookie(response, token_resp.new_refresh_token)
    return APIResponse(data=token_resp)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Logout — revokes current access + refresh tokens",
)
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    svc: AuthServiceDep,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_NAME),
) -> None:
    payload = getattr(request.state, "jwt_payload", {})
    jti     = payload.get("jti", "")
    await svc.logout(
        jti=jti,
        user_id=str(current_user.id),
        refresh_token=refresh_token or "",
    )
    _clear_refresh_cookie(response)


# ══════════════════════════════════════════════════════════════════════════════
# OAUTH
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/oauth/{provider}",
    response_model=APIResponse[dict],
    summary="Get OAuth authorize URL for a provider (currently: google)",
)
async def oauth_authorize(
    provider: str,
    svc: AuthServiceDep,
) -> APIResponse[dict]:
    if provider not in ("google",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_PROVIDER", "message": f"Provider '{provider}' is not supported"},
        )
    resp = await svc.oauth_authorize_url(provider)
    return APIResponse(data={"authorize_url": resp.authorize_url, "state": resp.state})


@router.post(
    "/oauth/callback",
    response_model=APIResponse[TokenResponse],
    summary="Handle OAuth callback — exchange code for tokens",
)
async def oauth_callback(
    payload: OAuthCallbackRequest,
    request: Request,
    response: Response,
    svc: AuthServiceDep,
) -> APIResponse[TokenResponse]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")

    try:
        token_pair = await svc.oauth_callback(
            provider=payload.provider,
            code=payload.code,
            state=payload.state,
            redirect_uri=payload.redirect_uri,
            ip_address=ip,
            user_agent=ua,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": exc.message},
        )

    _set_refresh_cookie(response, token_pair.refresh_token)
    return APIResponse(data=token_pair.access)


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/verify-email/{token}",
    response_model=APIResponse[UserOut],
    summary="Verify email address with one-time token",
)
async def verify_email(
    token: str,
    svc: AuthServiceDep,
) -> APIResponse[UserOut]:
    try:
        user = await svc.verify_email(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )
    return APIResponse(
        data=UserOut.model_validate(user),
        message="Email address verified successfully.",
    )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Resend email verification — rate limited to 1 per 2 minutes",
)
async def resend_verification(
    payload: ResendVerificationRequest,
    svc: AuthServiceDep,
) -> None:
    try:
        await svc.resend_verification(payload.email)
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMITED", "message": "Please wait before requesting another verification email"},
            headers={"Retry-After": "120"},
        )


# ══════════════════════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Request password reset — always returns 204 (no account enumeration)",
)
async def forgot_password(
    payload: PasswordResetRequestSchema,
    svc: AuthServiceDep,
) -> None:
    await svc.request_password_reset(payload.email)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Confirm password reset with one-time token",
)
async def reset_password(
    payload: PasswordResetConfirmSchema,
    svc: AuthServiceDep,
) -> None:
    try:
        await svc.confirm_password_reset(payload.token, payload.new_password)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        )

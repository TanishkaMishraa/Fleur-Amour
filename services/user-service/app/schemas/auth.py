"""
AuraFit — Auth schemas (Stage 3: complete auth system).
Covers registration, login, OAuth, email verification, MFA, sessions.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import AuraFitSchema


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(AuraFitSchema):
    email:     EmailStr
    password:  str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("one uppercase letter")
        if not any(c.isdigit() for c in v):
            errors.append("one digit")
        if errors:
            raise ValueError(f"Password requires: {', '.join(errors)}")
        return v


class LoginRequest(AuraFitSchema):
    email:    EmailStr
    password: str
    mfa_code: str | None = Field(None, min_length=6, max_length=8, description="TOTP code if MFA enabled")


class OAuthCallbackRequest(AuraFitSchema):
    """Received from frontend after provider redirect."""
    provider:   str   = Field(..., description="google | apple")
    code:       str   = Field(..., description="OAuth authorisation code")
    state:      str | None = None
    redirect_uri: str | None = None


class RefreshRequest(AuraFitSchema):
    """Used when refresh token is sent in body (non-cookie flows)."""
    refresh_token: str


class PasswordChangeRequest(AuraFitSchema):
    current_password: str
    new_password:     str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("New password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one digit")
        return v


class PasswordResetRequestSchema(AuraFitSchema):
    email: EmailStr


class PasswordResetConfirmSchema(AuraFitSchema):
    token:        str
    new_password: str = Field(..., min_length=8, max_length=128)


class EmailVerificationRequest(AuraFitSchema):
    token: str


class ResendVerificationRequest(AuraFitSchema):
    email: EmailStr


class MFASetupRequest(AuraFitSchema):
    """Client submits TOTP code to confirm MFA setup."""
    code: str = Field(..., min_length=6, max_length=6)


class MFADisableRequest(AuraFitSchema):
    password: str
    code:     str = Field(..., min_length=6, max_length=6)


class SessionRevokeRequest(AuraFitSchema):
    session_id: uuid.UUID


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class TokenResponse(AuraFitSchema):
    """Access token returned to client."""
    access_token:      str
    token_type:        str = "bearer"
    expires_in:        int           # seconds
    new_refresh_token: str | None = None   # present on /auth/refresh (rotation)


class TokenPair(AuraFitSchema):
    """Internal: access response + opaque refresh token string."""
    access:        TokenResponse
    refresh_token: str


class OAuthAuthorizeResponse(AuraFitSchema):
    """URL to redirect user to for OAuth provider."""
    provider:      str
    authorize_url: str
    state:         str


class MFASetupResponse(AuraFitSchema):
    """Returned when MFA setup is initiated."""
    secret:       str           # base32 secret for authenticator app
    qr_code_url:  str           # data: URI for QR code image
    backup_codes: list[str]     # one-time use backup codes


class SessionOut(AuraFitSchema):
    """One active session row for the session list page."""
    id:              uuid.UUID
    device_name:     str | None
    device_type:     str | None
    ip_address:      str | None
    location:        str | None
    last_active_at:  datetime | None
    created_at:      datetime
    is_current:      bool = False   # set by service based on current session


# ── Aliases used by mfa endpoints ──────────────────────────────────────────
ConfirmMFARequest = MFASetupRequest
DisableMFARequest = MFADisableRequest

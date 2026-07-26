"""
AuraFit — User + Preferences schemas (Stage 3).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.user import UserRole
from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Requests ──────────────────────────────────────────────────────────────────

class UserUpdateRequest(AuraFitSchema):
    full_name:  str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=512)


class PreferencesUpdateRequest(AuraFitSchema):
    # Notifications
    email_marketing:        bool | None = None
    email_recommendations:  bool | None = None
    email_product_updates:  bool | None = None
    email_security_alerts:  bool | None = None
    push_recommendations:   bool | None = None
    push_tryon_complete:    bool | None = None
    push_scan_complete:     bool | None = None
    in_app_notifications:   bool | None = None
    # Display
    theme:            str | None = Field(None, pattern="^(dark|light|system)$")
    language:         str | None = Field(None, min_length=2, max_length=5)
    currency:         str | None = Field(None, min_length=3, max_length=3)
    measurement_unit: str | None = Field(None, pattern="^(metric|imperial)$")
    # Privacy
    profile_public:         bool | None = None
    allow_data_training:    bool | None = None
    allow_personalisation:  bool | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class UserOut(UUIDSchema, TimestampSchema):
    email:         str
    full_name:     str
    role:          UserRole
    is_active:     bool
    is_verified:   bool
    avatar_url:    str | None
    mfa_enabled:   bool = False
    last_login_at: datetime | None = None


class UserSecurityOut(AuraFitSchema):
    """Security page data — sensitive fields only."""
    email:             str
    is_verified:       bool
    mfa_enabled:       bool
    password_changed_at: datetime | None
    last_login_at:       datetime | None
    last_login_ip:       str | None
    failed_login_attempts: int
    active_sessions_count: int


class PreferencesOut(UUIDSchema, TimestampSchema):
    # Notifications
    email_marketing:        bool
    email_recommendations:  bool
    email_product_updates:  bool
    email_security_alerts:  bool
    push_recommendations:   bool
    push_tryon_complete:    bool
    push_scan_complete:     bool
    in_app_notifications:   bool
    # Display
    theme:            str
    language:         str
    currency:         str
    measurement_unit: str
    # Privacy
    profile_public:         bool
    allow_data_training:    bool
    allow_personalisation:  bool


class DataExportRequest(AuraFitSchema):
    """GDPR data export request."""
    include_interactions: bool = True
    include_scan_data:    bool = True
    include_chat_history: bool = False

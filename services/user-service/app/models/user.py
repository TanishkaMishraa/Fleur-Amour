"""
AuraFit — User ORM model (Stage 3: full auth system).
Extends Stage 1 base with:
  - email_verification_token / email_verified_at
  - mfa_secret / mfa_enabled
  - failed_login_attempts / locked_until
  - UserPreferences (1:1)
  - UserSession table
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuraFitBase, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    USER    = "user"
    STYLIST = "stylist"
    ADMIN   = "admin"


class User(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core identity record. hashed_password is None for pure OAuth accounts.
    email_verified_at is None until user clicks verification link.
    mfa_secret is None until user enables TOTP 2FA.
    """
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    # ── Identity ──────────────────────────────────────────────────────────────
    email:            Mapped[str]      = mapped_column(String(255), nullable=False, index=True)
    hashed_password:  Mapped[str|None] = mapped_column(String(255), nullable=True)
    full_name:        Mapped[str]      = mapped_column(String(255), nullable=False)
    avatar_url:       Mapped[str|None] = mapped_column(String(512), nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active:   Mapped[bool]     = mapped_column(Boolean, default=True,  nullable=False)
    is_verified: Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    role:        Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        default=UserRole.USER, nullable=False, index=True,
    )

    # ── Email verification ────────────────────────────────────────────────────
    email_verification_token:    Mapped[str|None]      = mapped_column(String(128), nullable=True, index=True)
    email_verification_sent_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at:           Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Password reset ────────────────────────────────────────────────────────
    password_reset_token:        Mapped[str|None]      = mapped_column(String(128), nullable=True, index=True)
    password_reset_sent_at:      Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── MFA (TOTP) ────────────────────────────────────────────────────────────
    mfa_enabled: Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret:  Mapped[str|None] = mapped_column(String(64), nullable=True)

    # ── Security / lockout ────────────────────────────────────────────────────
    failed_login_attempts: Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    locked_until:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip:         Mapped[str|None]      = mapped_column(String(45), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    profile:        Mapped["UserProfile"]              = relationship("UserProfile",    back_populates="user", uselist=False, cascade="all, delete-orphan")
    preferences:    Mapped["UserPreferences"]          = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    oauth_accounts: Mapped[list["OAuthAccount"]]       = relationship("OAuthAccount",   back_populates="user", cascade="all, delete-orphan")
    sessions:       Mapped[list["UserSession"]]        = relationship("UserSession",    back_populates="user", cascade="all, delete-orphan")
    facial_scans:   Mapped[list["FacialScan"]]         = relationship("FacialScan",     back_populates="user", cascade="all, delete-orphan")
    wardrobes:      Mapped[list["Wardrobe"]]           = relationship("Wardrobe",       back_populates="user", cascade="all, delete-orphan")
    chat_sessions:  Mapped[list["ChatSession"]]        = relationship("ChatSession",    back_populates="user", cascade="all, delete-orphan")
    notifications:  Mapped[list["Notification"]]       = relationship("Notification",   back_populates="user", cascade="all, delete-orphan")
    style_reports:  Mapped[list["StyleReport"]]        = relationship("StyleReport",    back_populates="user", cascade="all, delete-orphan")
    interactions:   Mapped[list["UserProductInteraction"]] = relationship("UserProductInteraction", back_populates="user", cascade="all, delete-orphan")


class OAuthAccount(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """OAuth provider tokens linked to a user account."""
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),)

    user_id:          Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider:         Mapped[str]       = mapped_column(String(50),   nullable=False)
    provider_user_id: Mapped[str]       = mapped_column(String(255),  nullable=False)
    provider_email:   Mapped[str|None]  = mapped_column(String(255),  nullable=True)
    access_token:     Mapped[str|None]  = mapped_column(String(2048), nullable=True)
    refresh_token:    Mapped[str|None]  = mapped_column(String(2048), nullable=True)
    token_expires_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")


class UserSession(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persistent session record for each active device/browser.
    Allows multi-device session management and selective revocation.
    """
    __tablename__ = "user_sessions"

    user_id:         Mapped[uuid.UUID]  = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str]     = mapped_column(String(64),  nullable=False, unique=True, index=True)
    device_name:     Mapped[str|None]   = mapped_column(String(255), nullable=True)
    device_type:     Mapped[str|None]   = mapped_column(String(50),  nullable=True)   # mobile|desktop|tablet
    ip_address:      Mapped[str|None]   = mapped_column(String(45),  nullable=True)
    user_agent:      Mapped[str|None]   = mapped_column(String(500), nullable=True)
    location:        Mapped[str|None]   = mapped_column(String(100), nullable=True)
    last_active_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:      Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False)
    is_active:       Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class UserPreferences(AuraFitBase, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User-configurable preferences: notifications, privacy, display settings.
    1:1 with User. Auto-created on registration.
    """
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # ── Notifications ─────────────────────────────────────────────────────────
    email_marketing:         Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    email_recommendations:   Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    email_product_updates:   Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    email_security_alerts:   Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    push_recommendations:    Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    push_tryon_complete:     Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    push_scan_complete:      Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)
    in_app_notifications:    Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)

    # ── Display ───────────────────────────────────────────────────────────────
    theme:           Mapped[str]      = mapped_column(String(20),  default="dark",   nullable=False)
    language:        Mapped[str]      = mapped_column(String(10),  default="en",     nullable=False)
    currency:        Mapped[str]      = mapped_column(String(3),   default="USD",    nullable=False)
    measurement_unit:Mapped[str]      = mapped_column(String(10),  default="metric", nullable=False)

    # ── Privacy ───────────────────────────────────────────────────────────────
    profile_public:          Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_data_training:     Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_personalisation:   Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)

    # ── Extended preferences (flexible JSONB) ─────────────────────────────────
    extended: Mapped[dict|None] = mapped_column(JSONB, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="preferences")

"""
AuraFit — RBAC permission matrix (Stage 3).
Defines what each UserRole can do. Consumed by require_role() in dependencies.py
and directly by service-layer guards for fine-grained resource checks.

Design: flat permission strings (resource:action) grouped into role sets.
Services call `can(user.role, "wardrobe:write")` for resource-level checks.
Endpoint-level role requirements use `require_role(UserRole.ADMIN)`.
"""
from __future__ import annotations

from enum import StrEnum
from typing import FrozenSet

from app.models.user import UserRole


# ── Permission strings ────────────────────────────────────────────────────────

class Permission(StrEnum):
    # User management
    USER_READ_SELF        = "user:read:self"
    USER_WRITE_SELF       = "user:write:self"
    USER_DELETE_SELF      = "user:delete:self"
    USER_READ_ANY         = "user:read:any"
    USER_WRITE_ANY        = "user:write:any"
    USER_DELETE_ANY       = "user:delete:any"

    # Profile
    PROFILE_READ_SELF     = "profile:read:self"
    PROFILE_WRITE_SELF    = "profile:write:self"
    PROFILE_READ_ANY      = "profile:read:any"

    # Wardrobe
    WARDROBE_READ         = "wardrobe:read"
    WARDROBE_WRITE        = "wardrobe:write"
    WARDROBE_DELETE       = "wardrobe:delete"

    # Analysis / AI
    ANALYSIS_RUN          = "analysis:run"
    ANALYSIS_READ_SELF    = "analysis:read:self"
    ANALYSIS_READ_ANY     = "analysis:read:any"

    # Recommendations
    REC_VIEW              = "recommendations:view"
    REC_MANAGE            = "recommendations:manage"

    # Chat
    CHAT_USE              = "chat:use"

    # Preferences
    PREFS_READ_SELF       = "preferences:read:self"
    PREFS_WRITE_SELF      = "preferences:write:self"

    # Sessions
    SESSION_READ_SELF     = "session:read:self"
    SESSION_REVOKE_SELF   = "session:revoke:self"
    SESSION_REVOKE_ANY    = "session:revoke:any"

    # Reports
    REPORT_READ_SELF      = "report:read:self"
    REPORT_READ_ANY       = "report:read:any"

    # Admin
    ADMIN_DASHBOARD       = "admin:dashboard"
    ADMIN_USER_MANAGE     = "admin:user:manage"
    ADMIN_SYSTEM          = "admin:system"


# ── Role → permission sets ────────────────────────────────────────────────────

_USER_PERMISSIONS: FrozenSet[Permission] = frozenset({
    Permission.USER_READ_SELF,
    Permission.USER_WRITE_SELF,
    Permission.USER_DELETE_SELF,
    Permission.PROFILE_READ_SELF,
    Permission.PROFILE_WRITE_SELF,
    Permission.WARDROBE_READ,
    Permission.WARDROBE_WRITE,
    Permission.WARDROBE_DELETE,
    Permission.ANALYSIS_RUN,
    Permission.ANALYSIS_READ_SELF,
    Permission.REC_VIEW,
    Permission.CHAT_USE,
    Permission.PREFS_READ_SELF,
    Permission.PREFS_WRITE_SELF,
    Permission.SESSION_READ_SELF,
    Permission.SESSION_REVOKE_SELF,
    Permission.REPORT_READ_SELF,
})

_STYLIST_PERMISSIONS: FrozenSet[Permission] = _USER_PERMISSIONS | frozenset({
    Permission.PROFILE_READ_ANY,
    Permission.ANALYSIS_READ_ANY,
    Permission.REPORT_READ_ANY,
    Permission.REC_MANAGE,
})

_ADMIN_PERMISSIONS: FrozenSet[Permission] = frozenset(Permission)  # all permissions

_ROLE_MATRIX: dict[UserRole, FrozenSet[Permission]] = {
    UserRole.USER:    _USER_PERMISSIONS,
    UserRole.STYLIST: _STYLIST_PERMISSIONS,
    UserRole.ADMIN:   _ADMIN_PERMISSIONS,
}


# ── Public API ────────────────────────────────────────────────────────────────

def can(role: UserRole, permission: Permission) -> bool:
    """Check if a role has a given permission."""
    return permission in _ROLE_MATRIX.get(role, frozenset())


def get_permissions(role: UserRole) -> FrozenSet[Permission]:
    """Return all permissions for a role."""
    return _ROLE_MATRIX.get(role, frozenset())


def assert_permission(role: UserRole, permission: Permission) -> None:
    """
    Raise PermissionDeniedError if role lacks the permission.
    Use in service layer for resource-level guards.
    """
    if not can(role, permission):
        from app.core.errors import PermissionDeniedError
        raise PermissionDeniedError(
            f"Role '{role}' does not have permission '{permission}'"
        )

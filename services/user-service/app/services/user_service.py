"""
AuraFit — User service layer (Stage 3: complete account management).
Handles: display updates, avatar, preferences, security info, soft-delete.
No HTTP context. Fully testable. Repositories handle all DB I/O.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, cache_delete, cache_get, cache_set
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.user import User, UserPreferences
from app.repositories.user_repository import (
    UserPreferencesRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.user import PreferencesUpdateRequest, UserSecurityOut, UserUpdateRequest

logger = get_logger(__name__)
_PROFILE_TTL = 300   # 5 minutes


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session  = session
        self._repo     = UserRepository(session)
        self._pref_repo = UserPreferencesRepository(session)
        self._sess_repo = UserSessionRepository(session)
        self._settings = get_settings()

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_me(self, user_id: uuid.UUID) -> User:
        user = await self._repo.get_with_profile(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def update_me(self, user_id: uuid.UUID, data: UserUpdateRequest) -> User:
        user = await self._repo.get_by_id_or_raise(user_id)
        update_kwargs = data.model_dump(exclude_none=True)
        if update_kwargs:
            user = await self._repo.update(user, **update_kwargs)
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        logger.info("aurafit.user.updated", user_id=str(user_id), fields=list(update_kwargs.keys()))
        return user

    async def deactivate(self, user_id: uuid.UUID) -> None:
        user = await self._repo.get_by_id_or_raise(user_id)
        await self._repo.soft_delete(user)
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        # Queue GDPR erasure job (30-day delay per policy)
        from app.tasks.maintenance_tasks import anonymise_deleted_users
        anonymise_deleted_users.apply_async(countdown=30 * 86400)
        logger.info("aurafit.user.deactivated", user_id=str(user_id))

    # ── Avatar ────────────────────────────────────────────────────────────────

    async def upload_avatar(self, user_id: uuid.UUID, file: UploadFile) -> str:
        """Upload avatar to S3, update user row, return CDN URL."""
        import boto3, io
        from app.core.config import get_settings

        s = get_settings()
        contents = await file.read()

        # Limit to 5 MB
        if len(contents) > 5 * 1024 * 1024:
            from app.core.errors import ValidationError
            raise ValidationError("Avatar file must be under 5 MB")

        key = f"profiles/{user_id}/avatar.{file.content_type.split('/')[-1]}"
        s3  = boto3.client("s3", region_name=s.AWS_REGION)
        s3.put_object(
            Bucket=s.S3_ASSETS_BUCKET,
            Key=key,
            Body=io.BytesIO(contents),
            ContentType=file.content_type or "image/jpeg",
        )

        avatar_url = f"{s.CDN_BASE_URL}/{key}"
        await self._repo.update(await self._repo.get_by_id_or_raise(user_id), avatar_url=avatar_url)
        await cache_delete(RedisKeys.user_profile(str(user_id)))
        return avatar_url

    async def remove_avatar(self, user_id: uuid.UUID) -> None:
        await self._repo.update(await self._repo.get_by_id_or_raise(user_id), avatar_url=None)
        await cache_delete(RedisKeys.user_profile(str(user_id)))

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(self, user_id: uuid.UUID) -> UserPreferences:
        prefs = await self._pref_repo.get_by_user_id(user_id)
        if not prefs:
            # Auto-create if missing (migration safety)
            prefs = await self._pref_repo.create(user_id=user_id)
        return prefs

    async def update_preferences(
        self, user_id: uuid.UUID, data: PreferencesUpdateRequest
    ) -> UserPreferences:
        prefs = await self.get_preferences(user_id)
        updates = data.model_dump(exclude_none=True)
        if updates:
            prefs = await self._pref_repo.update(prefs, **updates)
        logger.info("aurafit.user.preferences_updated", user_id=str(user_id))
        return prefs

    # ── Security info ─────────────────────────────────────────────────────────

    async def get_security_info(self, user_id: uuid.UUID) -> UserSecurityOut:
        user          = await self._repo.get_by_id_or_raise(user_id)
        session_count = await self._sess_repo.count_active(user_id)
        return UserSecurityOut(
            email=user.email,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            password_changed_at=user.password_changed_at,
            last_login_at=user.last_login_at,
            last_login_ip=user.last_login_ip,
            failed_login_attempts=user.failed_login_attempts or 0,
            active_sessions_count=session_count,
        )

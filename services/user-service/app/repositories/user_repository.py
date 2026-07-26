"""
AuraFit — User repository (Stage 3: sessions, preferences, OAuth).
All DB access for users, sessions, preferences, and OAuth accounts.
No business logic — only queries.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import OAuthAccount, User, UserPreferences, UserSession
from app.models.image import Upload, UploadStatus
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    # ── Lookup ────────────────────────────────────────────────────────────────

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.email == email.lower().strip())
            .where(User.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def get_with_profile(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.is_deleted == False)  # noqa: E712
            .options(selectinload(User.profile), selectinload(User.preferences))
        )
        return result.scalar_one_or_none()

    async def get_with_all_relations(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .where(User.is_deleted == False)  # noqa: E712
            .options(
                selectinload(User.profile),
                selectinload(User.preferences),
                selectinload(User.oauth_accounts),
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        count = (await self.session.execute(
            select(func.count()).select_from(User)
            .where(User.email == email.lower().strip())
            .where(User.is_deleted == False)  # noqa: E712
        )).scalar_one()
        return count > 0

    async def get_by_verification_token(self, token: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email_verification_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.password_reset_token == token)
        )
        return result.scalar_one_or_none()

    # ── Updates ───────────────────────────────────────────────────────────────

    async def update_password(self, user_id: uuid.UUID, hashed: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed,
                password_changed_at=datetime.now(UTC),
                failed_login_attempts=0,
                locked_until=None,
                password_reset_token=None,
                password_reset_sent_at=None,
            )
        )

    async def update_last_login(self, user_id: uuid.UUID, ip: str | None = None) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(UTC),
                last_login_ip=ip,
                failed_login_attempts=0,
                locked_until=None,
            )
        )

    async def set_locked_until(self, user_id: uuid.UUID, until: datetime) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(locked_until=until)
        )

    async def mark_email_verified(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_verified=True,
                email_verified_at=datetime.now(UTC),
                email_verification_token=None,
            )
        )

    async def set_verification_token(self, user_id: uuid.UUID, token: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                email_verification_token=token,
                email_verification_sent_at=datetime.now(UTC),
            )
        )

    async def set_reset_token(self, user_id: uuid.UUID, token: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_reset_token=token,
                password_reset_sent_at=datetime.now(UTC),
            )
        )

    async def clear_reset_token(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_reset_token=None, password_reset_sent_at=None)
        )

    async def enable_mfa(self, user_id: uuid.UUID, secret: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(mfa_enabled=True, mfa_secret=secret)
        )

    async def disable_mfa(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(mfa_enabled=False, mfa_secret=None)
        )


class UserSessionRepository(BaseRepository[UserSession]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserSession, session)

    async def get_active_by_token_hash(self, token_hash: str) -> UserSession | None:
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.refresh_token_hash == token_hash)
            .where(UserSession.is_active == True)          # noqa: E712
            .where(UserSession.expires_at > datetime.now(UTC))
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[UserSession]:
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)          # noqa: E712
            .where(UserSession.expires_at > datetime.now(UTC))
            .order_by(UserSession.last_active_at.desc())
        )
        return list(result.scalars().all())

    async def count_active(self, user_id: uuid.UUID) -> int:
        count = (await self.session.execute(
            select(func.count()).select_from(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)          # noqa: E712
            .where(UserSession.expires_at > datetime.now(UTC))
        )).scalar_one()
        return count

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        await self.session.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_active=False)
        )

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        except_session_id: uuid.UUID | None = None,
    ) -> int:
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)           # noqa: E712
        )
        if except_session_id:
            stmt = stmt.where(UserSession.id != except_session_id)
        result = await self.session.execute(stmt.values(is_active=False))
        return result.rowcount


class UserPreferencesRepository(BaseRepository[UserPreferences]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserPreferences, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserPreferences | None:
        result = await self.session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()


class OAuthAccountRepository(BaseRepository[OAuthAccount]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OAuthAccount, session)

    async def get_by_provider(
        self, provider: str, provider_user_id: str
    ) -> OAuthAccount | None:
        result = await self.session.execute(
            select(OAuthAccount)
            .where(OAuthAccount.provider == provider)
            .where(OAuthAccount.provider_user_id == provider_user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthAccount]:
        result = await self.session.execute(
            select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        )
        return list(result.scalars().all())


class UploadRepository(BaseRepository[Upload]):
    """
    Tracks file uploads through their lifecycle:
    PENDING (presigned URL issued) → UPLOADED (client confirmed) →
    PROCESSING (Celery task running) → COMPLETE | FAILED
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Upload, session)

    async def get_by_celery_task_id(self, task_id: str) -> Upload | None:
        result = await self.session.execute(
            select(Upload).where(Upload.celery_task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def mark_processing(self, upload_id: uuid.UUID, celery_task_id: str) -> None:
        await self.session.execute(
            update(Upload)
            .where(Upload.id == upload_id)
            .values(status=UploadStatus.PROCESSING, celery_task_id=celery_task_id)
        )

    async def mark_complete(self, upload_id: uuid.UUID, result_url: str | None = None) -> None:
        await self.session.execute(
            update(Upload)
            .where(Upload.id == upload_id)
            .values(status=UploadStatus.COMPLETE, result_url=result_url)
        )

    async def mark_failed(self, upload_id: uuid.UUID, error_message: str) -> None:
        await self.session.execute(
            update(Upload)
            .where(Upload.id == upload_id)
            .values(status=UploadStatus.FAILED, error_message=error_message[:500])
        )

    async def list_for_user(
        self, user_id: uuid.UUID, *, purpose: str | None = None, limit: int = 20
    ) -> list[Upload]:
        query = select(Upload).where(Upload.user_id == user_id)
        if purpose:
            query = query.where(Upload.purpose == purpose)
        query = query.order_by(Upload.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

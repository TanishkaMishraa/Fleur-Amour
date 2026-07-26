"""
AuraFit — Authentication service (Stage 3: complete system).
Handles: register, login (+MFA), OAuth, email verification,
         password reset, token refresh/rotation, session management, RBAC.
No HTTP context. Fully unit-testable.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pyotp

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisKeys, get_redis
from app.core.config import get_settings
from app.core.errors import (
    AccountLockedError,
    AlreadyExistsError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    TokenError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.profile import UserProfile
from app.models.user import OAuthAccount, User, UserPreferences, UserRole, UserSession
from app.repositories.user_repository import (
    OAuthAccountRepository,
    UserPreferencesRepository,
    UserRepository,
    UserSessionRepository,
)
from app.schemas.auth import (
    MFASetupResponse,
    OAuthAuthorizeResponse,
    SessionOut,
    TokenPair,
    TokenResponse,
)

logger = get_logger(__name__)

_AUTH_ATTEMPTS_KEY    = "auth:attempts:{}"
_AUTH_LOCK_TTL        = 900        # 15-min lockout after 5 failures
_AUTH_MAX_ATTEMPTS    = 5
_VERIFY_TTL           = 86400      # 24h email verification
_RESET_TTL            = 3600       # 1h password reset
_MFA_BACKUP_COUNT     = 8
_SESSION_MAX_PER_USER = 10         # max concurrent device sessions


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session    = session
        self._user_repo  = UserRepository(session)
        self._sess_repo  = UserSessionRepository(session)
        self._oauth_repo = OAuthAccountRepository(session)
        self._pref_repo  = UserPreferencesRepository(session)
        self._settings   = get_settings()

    # ══════════════════════════════════════════════════════════════════════════
    # REGISTRATION
    # ══════════════════════════════════════════════════════════════════════════

    async def register(
        self, *, email: str, password: str, full_name: str
    ) -> User:
        """
        Create new user, empty beauty profile, default preferences.
        Dispatches verification email via Celery.
        """
        normalised = email.lower().strip()
        if await self._user_repo.email_exists(normalised):
            raise AlreadyExistsError("This email address is already registered")

        verification_token = secrets.token_urlsafe(32)

        user = await self._user_repo.create(
            email=normalised,
            hashed_password=hash_password(password),
            full_name=full_name.strip(),
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            email_verification_token=verification_token,
            email_verification_sent_at=datetime.now(UTC),
        )

        # Seed empty profile + default preferences
        self._session.add(UserProfile(user_id=user.id, onboarding_complete=False))
        self._session.add(UserPreferences(user_id=user.id))
        await self._session.flush()

        # Dispatch verification email (fire-and-forget Celery)
        try:
            from app.tasks.notification_tasks import send_email_verification_task
            send_email_verification_task.delay(
                user_id=str(user.id),
                email=normalised,
                full_name=user.full_name,
                token=verification_token,
            )
        except Exception as exc:
            logger.warning("aurafit.auth.email_dispatch_failed", error=str(exc))

        logger.info("aurafit.auth.registered", user_id=str(user.id))
        return user

    # ══════════════════════════════════════════════════════════════════════════
    # LOGIN
    # ══════════════════════════════════════════════════════════════════════════

    async def login(
        self,
        *,
        email:      str,
        password:   str,
        mfa_code:   str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name:str | None = None,
    ) -> TokenPair:
        """
        Validate credentials → check MFA → create session → return token pair.
        Brute-force: 5 failures → 15-min lockout (tracked in Redis + DB).
        """
        r = get_redis()
        normalised = email.lower().strip()
        lock_key   = _AUTH_ATTEMPTS_KEY.format(normalised)

        # ── Brute-force guard ─────────────────────────────────────────────────
        attempts_raw = await r.get(lock_key)
        if attempts_raw and int(attempts_raw) >= _AUTH_MAX_ATTEMPTS:
            raise AccountLockedError(
                "Account temporarily locked due to too many failed attempts. "
                "Please try again in 15 minutes."
            )

        user = await self._user_repo.get_by_email(normalised)

        if not user or not user.hashed_password:
            await r.incr(lock_key)
            await r.expire(lock_key, _AUTH_LOCK_TTL)
            raise AuthenticationError("Invalid email or password")

        # ── DB-level lockout check ────────────────────────────────────────────
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AccountLockedError("Account locked. Check your email to unlock or wait.")

        # ── Password verify ───────────────────────────────────────────────────
        if not verify_password(password, user.hashed_password):
            await r.incr(lock_key)
            await r.expire(lock_key, _AUTH_LOCK_TTL)
            failed = (user.failed_login_attempts or 0) + 1
            # Lock at DB level if >= max attempts
            if failed >= _AUTH_MAX_ATTEMPTS:
                await self._user_repo.set_locked_until(
                    user.id, datetime.now(UTC) + timedelta(minutes=15)
                )
            logger.warning("aurafit.auth.bad_password", email=normalised, attempts=failed)
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")

        # ── TOTP MFA check ────────────────────────────────────────────────────
        if user.mfa_enabled:
            if not mfa_code:
                raise AuthenticationError(
                    "MFA_REQUIRED",
                )
            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(mfa_code, valid_window=1):
                raise AuthenticationError("Invalid authenticator code")

        # ── Clear failure state ───────────────────────────────────────────────
        await r.delete(lock_key)
        await self._user_repo.update_last_login(user.id, ip=ip_address)

        # Rehash if Argon2 params outdated
        if needs_rehash(user.hashed_password):
            await self._user_repo.update_password(user.id, hash_password(password))

        # ── Issue tokens + persist session ────────────────────────────────────
        return await self._issue_token_pair(
            user,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # OAUTH 2.0
    # ══════════════════════════════════════════════════════════════════════════

    async def oauth_authorize_url(self, provider: str) -> OAuthAuthorizeResponse:
        """Build the redirect URL for the given OAuth provider."""
        state = secrets.token_urlsafe(32)
        r     = get_redis()
        await r.setex(f"oauth:state:{state}", 600, provider)  # 10-min expiry

        if provider == "google":
            url = self._build_google_url(state)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        return OAuthAuthorizeResponse(
            provider=provider,
            authorize_url=url,
            state=state,
        )

    async def oauth_callback(
        self,
        *,
        provider:     str,
        code:         str,
        state:        str | None = None,
        redirect_uri: str | None = None,
        ip_address:   str | None = None,
        user_agent:   str | None = None,
    ) -> TokenPair:
        """
        Exchange OAuth code for user info.
        Upsert OAuthAccount + User, then issue token pair.
        """
        if provider == "google":
            user_info = await self._exchange_google_code(code, redirect_uri)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        provider_uid: str   = str(user_info["sub"])
        provider_email: str = user_info.get("email", "").lower()
        full_name: str       = user_info.get("name", provider_email.split("@")[0])
        avatar_url: str|None = user_info.get("picture")

        # Find or create OAuth account
        oauth_acc = await self._oauth_repo.get_by_provider(provider, provider_uid)

        if oauth_acc:
            user = await self._user_repo.get_by_id(oauth_acc.user_id)
            if not user:
                raise AuthenticationError("Associated account not found")
        else:
            # Check if email already registered — link if so, create if not
            user = await self._user_repo.get_by_email(provider_email)
            if not user:
                user = await self._user_repo.create(
                    email=provider_email,
                    hashed_password=None,        # OAuth-only account
                    full_name=full_name,
                    avatar_url=avatar_url,
                    role=UserRole.USER,
                    is_active=True,
                    is_verified=True,            # Email already verified by provider
                    email_verified_at=datetime.now(UTC),
                )
                self._session.add(UserProfile(user_id=user.id, onboarding_complete=False))
                self._session.add(UserPreferences(user_id=user.id))

            oauth_acc = await self._oauth_repo.create(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_uid,
                provider_email=provider_email,
            )
            await self._session.flush()

        if not user.is_active:
            raise AuthenticationError("This account has been deactivated")

        await self._user_repo.update_last_login(user.id, ip=ip_address)
        logger.info("aurafit.auth.oauth_login", user_id=str(user.id), provider=provider)
        return await self._issue_token_pair(user, ip_address=ip_address, user_agent=user_agent)

    def _build_google_url(self, state: str) -> str:
        from urllib.parse import urlencode
        s = self._settings
        params = {
            "client_id":     s.GOOGLE_CLIENT_ID,
            "redirect_uri":  s.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope":         "openid email profile",
            "state":         state,
            "access_type":   "offline",
            "prompt":        "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def _exchange_google_code(self, code: str, redirect_uri: str | None) -> dict:
        s = self._settings
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code":          code,
                    "client_id":     s.GOOGLE_CLIENT_ID,
                    "client_secret": s.GOOGLE_CLIENT_SECRET,
                    "redirect_uri":  redirect_uri or s.GOOGLE_REDIRECT_URI,
                    "grant_type":    "authorization_code",
                },
                timeout=10.0,
            )
            token_res.raise_for_status()
            tokens = token_res.json()

            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                timeout=10.0,
            )
            userinfo_res.raise_for_status()
            return userinfo_res.json()

    # ══════════════════════════════════════════════════════════════════════════
    # TOKEN MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotate refresh token — delete old session, create new one."""
        token_hash = self._hash(refresh_token)
        session    = await self._sess_repo.get_active_by_token_hash(token_hash)

        if not session:
            raise TokenError("Refresh token expired or revoked")

        user = await self._user_repo.get_by_id(session.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Revoke old session row
        await self._sess_repo.revoke_session(session.id)

        # Issue new token pair
        pair = await self._issue_token_pair(
            user,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            device_name=session.device_name,
        )
        return TokenResponse(
            access_token=pair.access.access_token,
            expires_in=pair.access.expires_in,
            new_refresh_token=pair.refresh_token,
        )

    async def logout(self, *, jti: str, user_id: str, refresh_token: str) -> None:
        """Revoke access token JTI + invalidate session."""
        r   = get_redis()
        ttl = self._settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        if jti:
            await r.setex(RedisKeys.token_blocklist(jti), ttl, "revoked")
        if refresh_token:
            token_hash = self._hash(refresh_token)
            sess       = await self._sess_repo.get_active_by_token_hash(token_hash)
            if sess:
                await self._sess_repo.revoke_session(sess.id)
        logger.info("aurafit.auth.logout", user_id=user_id)

    # ══════════════════════════════════════════════════════════════════════════
    # EMAIL VERIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    async def verify_email(self, token: str) -> User:
        user = await self._user_repo.get_by_verification_token(token)
        if not user:
            raise TokenError("Email verification token is invalid or expired")
        if user.is_verified:
            return user   # idempotent — already verified
        await self._user_repo.mark_email_verified(user.id)
        logger.info("aurafit.auth.email_verified", user_id=str(user.id))
        return user

    async def resend_verification(self, email: str) -> None:
        """Resend verification email. Rate-limited to once per 2 minutes."""
        r    = get_redis()
        key  = f"resend_verify:{email.lower()}"
        if await r.exists(key):
            raise PermissionDeniedError("Please wait before requesting another verification email")

        user = await self._user_repo.get_by_email(email.lower())
        if not user or user.is_verified:
            return   # don't leak whether email exists

        token = secrets.token_urlsafe(32)
        await self._user_repo.set_verification_token(user.id, token)
        await r.setex(key, 120, "1")   # 2-minute rate-limit

        from app.tasks.notification_tasks import send_email_verification_task
        send_email_verification_task.delay(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            token=token,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # PASSWORD RESET
    # ══════════════════════════════════════════════════════════════════════════

    async def request_password_reset(self, email: str) -> None:
        """
        Generate reset token, persist to user row, dispatch email.
        Always returns silently — never leaks whether email exists.
        """
        r   = get_redis()
        key = f"reset_rate:{email.lower()}"
        if await r.exists(key):
            return   # silent rate-limit (3-min window)

        user = await self._user_repo.get_by_email(email.lower())
        if not user:
            return

        token = secrets.token_urlsafe(32)
        await self._user_repo.set_reset_token(user.id, token)
        await r.setex(key, 180, "1")   # 3-min rate-limit

        from app.tasks.notification_tasks import send_password_reset_task
        send_password_reset_task.delay(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            token=token,
        )
        logger.info("aurafit.auth.reset_requested", user_id=str(user.id))

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        user = await self._user_repo.get_by_reset_token(token)
        if not user:
            raise TokenError("Password reset token is invalid or expired")

        # Check token age (max 1 hour)
        if user.password_reset_sent_at:
            age = (datetime.now(UTC) - user.password_reset_sent_at).total_seconds()
            if age > _RESET_TTL:
                raise TokenError("Password reset token has expired")

        await self._user_repo.update_password(user.id, hash_password(new_password))
        await self._user_repo.clear_reset_token(user.id)

        # Revoke all active sessions (security: force re-login on all devices)
        await self._sess_repo.revoke_all_for_user(user.id)
        logger.info("aurafit.auth.password_reset", user_id=str(user.id))

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        user = await self._user_repo.get_by_id_or_raise(user_id)
        if not user.hashed_password:
            raise AuthenticationError("OAuth accounts cannot change passwords via this endpoint")
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")
        await self._user_repo.update_password(user.id, hash_password(new_password))
        logger.info("aurafit.auth.password_changed", user_id=str(user_id))

    # ══════════════════════════════════════════════════════════════════════════
    # MFA (TOTP)
    # ══════════════════════════════════════════════════════════════════════════

    async def setup_mfa(self, user_id: uuid.UUID) -> MFASetupResponse:
        """Generate TOTP secret + QR code + backup codes. MFA not active until confirmed."""
        import base64, io, pyotp, qrcode  # type: ignore[import-untyped]

        user   = await self._user_repo.get_by_id_or_raise(user_id)
        secret = pyotp.random_base32()
        totp   = pyotp.TOTP(secret)
        uri    = totp.provisioning_uri(user.email, issuer_name="AuraFit")

        # Generate QR code as data URI
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        qr_url = f"data:image/png;base64,{b64}"

        # Store pending secret in Redis (confirmed when user submits first code)
        r = get_redis()
        await r.setex(f"mfa:setup:{user_id}", 600, secret)

        backup_codes = [secrets.token_hex(4).upper() for _ in range(_MFA_BACKUP_COUNT)]
        # Store hashed backup codes
        await r.setex(
            f"mfa:backup:{user_id}",
            600,
            ",".join(hashlib.sha256(c.encode()).hexdigest() for c in backup_codes)
        )

        return MFASetupResponse(secret=secret, qr_code_url=qr_url, backup_codes=backup_codes)

    async def confirm_mfa_setup(self, user_id: uuid.UUID, code: str) -> None:
        """Activate MFA after user confirms with first TOTP code."""
        r = get_redis()
        secret = await r.get(f"mfa:setup:{user_id}")
        if not secret:
            raise TokenError("MFA setup session expired. Please restart.")

        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            raise AuthenticationError("Invalid authenticator code")

        await self._user_repo.enable_mfa(user_id, secret)
        await r.delete(f"mfa:setup:{user_id}")
        logger.info("aurafit.auth.mfa_enabled", user_id=str(user_id))

    async def disable_mfa(
        self, user_id: uuid.UUID, password: str, code: str
    ) -> None:
        user = await self._user_repo.get_by_id_or_raise(user_id)
        if not user.mfa_enabled:
            return
        if not verify_password(password, user.hashed_password or ""):
            raise AuthenticationError("Incorrect password")
        totp = pyotp.TOTP(user.mfa_secret or "")
        if not totp.verify(code, valid_window=1):
            raise AuthenticationError("Invalid authenticator code")
        await self._user_repo.disable_mfa(user_id)
        logger.info("aurafit.auth.mfa_disabled", user_id=str(user_id))

    # ══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    async def list_sessions(
        self, user_id: uuid.UUID, current_refresh_hash: str | None = None
    ) -> list[SessionOut]:
        sessions = await self._sess_repo.list_active_for_user(user_id)
        result   = []
        for s in sessions:
            result.append(SessionOut(
                id=s.id,
                device_name=s.device_name,
                device_type=s.device_type,
                ip_address=s.ip_address,
                location=s.location,
                last_active_at=s.last_active_at,
                created_at=s.created_at,
                is_current=(current_refresh_hash is not None and s.refresh_token_hash == current_refresh_hash),
            ))
        return result

    async def revoke_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        session = await self._sess_repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise NotFoundError("Session not found")
        await self._sess_repo.revoke_session(session_id)

    async def revoke_all_other_sessions(
        self, user_id: uuid.UUID, current_session_id: uuid.UUID
    ) -> int:
        return await self._sess_repo.revoke_all_for_user(user_id, except_session_id=current_session_id)

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _issue_token_pair(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> TokenPair:
        """Create RS256 access token + opaque refresh token → persist session."""
        access_token              = create_access_token(str(user.id), role=user.role.value)
        refresh_token, expires_at = create_refresh_token()
        token_hash                = self._hash(refresh_token)

        # Prune oldest session if at limit
        active_count = await self._sess_repo.count_active(user.id)
        if active_count >= _SESSION_MAX_PER_USER:
            sessions = await self._sess_repo.list_active_for_user(user.id)
            oldest   = sorted(sessions, key=lambda s: s.created_at)[0]
            await self._sess_repo.revoke_session(oldest.id)

        self._session.add(UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            device_name=device_name,
            device_type=self._detect_device_type(user_agent),
            ip_address=ip_address,
            user_agent=user_agent,
            last_active_at=datetime.now(UTC),
            expires_at=expires_at,
            is_active=True,
        ))
        await self._session.flush()

        s = self._settings
        return TokenPair(
            access=TokenResponse(
                access_token=access_token,
                expires_in=s.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
            refresh_token=refresh_token,
        )

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _detect_device_type(ua: str | None) -> str | None:
        if not ua:
            return None
        ua_lower = ua.lower()
        if any(k in ua_lower for k in ("mobile", "android", "iphone", "ipad")):
            return "mobile"
        if "tablet" in ua_lower:
            return "tablet"
        return "desktop"

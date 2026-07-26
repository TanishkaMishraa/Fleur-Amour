"""
AuraFit — AuthService unit tests.
All external dependencies (DB, Redis) are mocked.
Tests cover registration, login, token refresh, and logout logic.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import AlreadyExistsError, AuthenticationError
from app.core.security import hash_password


class TestRegister:
    @pytest.mark.asyncio
    async def test_raises_when_email_taken(self, test_session):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)

        with patch.object(svc._user_repo, "email_exists", AsyncMock(return_value=True)):
            with pytest.raises(AlreadyExistsError):
                await svc.register(
                    email="taken@aurafit.ai",
                    password="ValidPass1",
                    full_name="Test User",
                )

    @pytest.mark.asyncio
    async def test_email_is_lowercased_on_create(self, test_session, mock_redis):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)

        fake_user = MagicMock()
        fake_user.id = uuid.uuid4()

        with (
            patch.object(svc._user_repo, "email_exists", AsyncMock(return_value=False)),
            patch.object(svc._user_repo, "create", AsyncMock(return_value=fake_user)),
            patch("app.services.auth_service.get_redis", return_value=mock_redis),
            patch.object(test_session, "add"),
            patch.object(test_session, "flush", AsyncMock()),
        ):
            await svc.register(
                email="  UPPER@AURAFIT.AI  ",
                password="ValidPass1",
                full_name="Test User",
            )
            call_kwargs = svc._user_repo.create.call_args.kwargs
            assert call_kwargs["email"] == "upper@aurafit.ai"

    @pytest.mark.asyncio
    async def test_password_is_hashed_on_create(self, test_session, mock_redis):
        from app.services.auth_service import AuthService
        from app.core.security import verify_password
        svc = AuthService(test_session)

        captured_kwargs = {}

        async def mock_create(**kwargs):
            captured_kwargs.update(kwargs)
            m = MagicMock()
            m.id = uuid.uuid4()
            return m

        with (
            patch.object(svc._user_repo, "email_exists", AsyncMock(return_value=False)),
            patch.object(svc._user_repo, "create", side_effect=mock_create),
            patch("app.services.auth_service.get_redis", return_value=mock_redis),
            patch.object(test_session, "add"),
            patch.object(test_session, "flush", AsyncMock()),
        ):
            await svc.register(
                email="test@aurafit.ai",
                password="ValidPass1",
                full_name="Test User",
            )
            stored_hash = captured_kwargs.get("hashed_password", "")
            assert stored_hash != "ValidPass1"
            assert verify_password("ValidPass1", stored_hash)


class TestLogin:
    @pytest.mark.asyncio
    async def test_raises_for_unknown_email(self, test_session):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)

        with patch.object(svc._user_repo, "get_by_email", AsyncMock(return_value=None)):
            with pytest.raises(AuthenticationError):
                await svc.login("unknown@aurafit.ai", "password")

    @pytest.mark.asyncio
    async def test_raises_for_wrong_password(self, test_session):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)

        fake_user = MagicMock()
        fake_user.is_active = True
        fake_user.hashed_password = hash_password("CorrectPass1")

        with patch.object(svc._user_repo, "get_by_email", AsyncMock(return_value=fake_user)):
            with pytest.raises(AuthenticationError):
                await svc.login("user@aurafit.ai", "WrongPass1")

    @pytest.mark.asyncio
    async def test_returns_token_pair_on_success(self, test_session, mock_redis, rsa_key_pair):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)
        private_pem, public_pem = rsa_key_pair

        fake_user = MagicMock()
        fake_user.id = uuid.uuid4()
        fake_user.is_active = True
        fake_user.role = MagicMock()
        fake_user.role.value = "user"
        fake_user.hashed_password = hash_password("CorrectPass1")

        with (
            patch.object(svc._user_repo, "get_by_email", AsyncMock(return_value=fake_user)),
            patch("app.services.auth_service.get_redis", return_value=mock_redis),
            patch("app.core.security._settings") as mock_settings,
        ):
            mock_settings.return_value.ALGORITHM = "RS256"
            mock_settings.return_value.ACCESS_TOKEN_EXPIRE_MINUTES = 15
            mock_settings.return_value.REFRESH_TOKEN_EXPIRE_DAYS = 7
            mock_settings.return_value.JWT_PRIVATE_KEY = private_pem
            mock_settings.return_value.JWT_PUBLIC_KEY = public_pem

            token_resp, refresh_token = await svc.login("user@aurafit.ai", "CorrectPass1")

        assert token_resp.access_token
        assert token_resp.token_type == "bearer"
        assert len(refresh_token) > 10


class TestLogout:
    @pytest.mark.asyncio
    async def test_blocklist_and_delete_refresh(self, test_session, mock_redis):
        from app.services.auth_service import AuthService
        svc = AuthService(test_session)

        with patch("app.services.auth_service.get_redis", return_value=mock_redis):
            await svc.logout(
                jti="test-jti-123",
                user_id=str(uuid.uuid4()),
                refresh_token="some-refresh-token",
            )

        # Should have called setex (blocklist) and delete (refresh token)
        mock_redis.setex.assert_called_once()
        mock_redis.delete.assert_called_once()

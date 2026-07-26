"""
AuraFit — Unit tests for JWT and password utilities.
No external dependencies. Pure logic tests only.
"""
from __future__ import annotations

import time
import uuid

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecret123")
        assert hashed != "MySecret123"
        assert len(hashed) > 20

    def test_correct_password_verifies(self):
        hashed = hash_password("CorrectHorse99")
        assert verify_password("CorrectHorse99", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("CorrectHorse99")
        assert verify_password("WrongPassword1", hashed) is False

    def test_empty_password_fails(self):
        hashed = hash_password("ValidPass1")
        assert verify_password("", hashed) is False

    def test_needs_rehash_returns_bool(self):
        hashed = hash_password("ValidPass1")
        result = needs_rehash(hashed)
        assert isinstance(result, bool)


class TestJWT:
    @pytest.fixture(autouse=True)
    def patch_settings(self, rsa_key_pair, monkeypatch):
        private_pem, public_pem = rsa_key_pair
        import app.core.config as cfg_module

        class _FakeSettings:
            ALGORITHM = "RS256"
            ACCESS_TOKEN_EXPIRE_MINUTES = 15
            REFRESH_TOKEN_EXPIRE_DAYS = 7
            JWT_PRIVATE_KEY = private_pem
            JWT_PUBLIC_KEY = public_pem

        monkeypatch.setattr(cfg_module, "get_settings", lambda: _FakeSettings())
        # Also patch the security module's import
        import app.core.security as sec_module
        monkeypatch.setattr(sec_module, "_settings", lambda: _FakeSettings())

    def test_encode_decode_roundtrip(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, role="user")
        payload = decode_access_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_admin_role_preserved(self):
        token = create_access_token(str(uuid.uuid4()), role="admin")
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_tampered_token_raises(self):
        import jwt
        token = create_access_token(str(uuid.uuid4()), role="user")
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(tampered)

    def test_extra_claims_included(self):
        token = create_access_token(
            str(uuid.uuid4()), role="user", extra_claims={"email": "a@b.com"}
        )
        payload = decode_access_token(token)
        assert payload.get("email") == "a@b.com"

    def test_each_token_has_unique_jti(self):
        uid = str(uuid.uuid4())
        t1 = create_access_token(uid, role="user")
        t2 = create_access_token(uid, role="user")
        p1 = decode_access_token(t1)
        p2 = decode_access_token(t2)
        assert p1["jti"] != p2["jti"]

"""
AuraFit — Security utilities: JWT (RS256) + Argon2id password hashing.
RS256 = asymmetric keys. Private key signs; public key verifies.
Only the auth service needs the private key. All other services verify with public key only.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

# Argon2id — memory-hard, GPU-resistant. Preferred over bcrypt.
_ph = PasswordHasher(
    time_cost=2,        # iterations
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return Argon2id hash of plain-text password."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain text against Argon2id hash. Returns False on mismatch."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, Exception):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if hash params are outdated and the hash should be upgraded on next login."""
    return _ph.check_needs_rehash(hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _settings() -> Any:
    """Indirection allows monkeypatching in unit tests."""
    return get_settings()


def create_access_token(
    subject: str,
    *,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create RS256 access token.
    subject: user UUID as string.
    Expires in ACCESS_TOKEN_EXPIRE_MINUTES (default 15).
    """
    s = _settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),    # unique ID for blocklisting
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, s.JWT_PRIVATE_KEY, algorithm=s.ALGORITHM)


def create_refresh_token() -> tuple[str, datetime]:
    """
    Return (opaque_token, expires_at).
    Stored hashed in Redis. Never contains user data — just a random UUID.
    """
    s = _settings()
    token = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(days=s.REFRESH_TOKEN_EXPIRE_DAYS)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode + validate RS256 JWT with the public key.
    Raises jwt.PyJWTError subclasses on any failure.
    """
    s = _settings()
    return jwt.decode(
        token,
        s.JWT_PUBLIC_KEY,
        algorithms=[s.ALGORITHM],
        options={"require": ["sub", "exp", "jti", "type"]},
    )


def extract_token_from_header(authorization: str) -> str:
    """
    Parse 'Bearer <token>' Authorization header.
    Raises ValueError on bad format.
    """
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Authorization header must be 'Bearer <token>'")
    return parts[1]

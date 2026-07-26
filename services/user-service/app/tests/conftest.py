"""
AuraFit — pytest fixtures.
Async test client, in-memory SQLite DB, mock Redis, mock Celery.
Pattern: override get_db_session and Redis in all integration tests.
"""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import AuraFitBase

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(AuraFitBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock async Redis. Override specific methods per test as needed."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    mock.ping.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.publish.return_value = 0
    mock.aclose.return_value = None
    return mock


@pytest.fixture
def mock_celery_task() -> MagicMock:
    """Mock Celery task.delay() to prevent real task dispatch in tests."""
    task = MagicMock()
    task.id = "test-task-id-0000-0000-000000000001"
    task.delay.return_value = task
    task.apply_async.return_value = task
    return task


@pytest.fixture
async def client(
    test_session: AsyncSession,
    mock_redis: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Fully wired async test client.
    - DB: in-memory SQLite (aiosqlite)
    - Redis: AsyncMock (no network)
    - Celery: always-eager (tasks run synchronously inline)
    """
    from app.db.session import get_db_session
    from app.main import create_app

    # Override DB session dependency
    async def _override_session():
        yield test_session

    # Patch Redis singleton
    monkeypatch.setattr("app.cache.redis_client._redis", mock_redis)

    app = create_app()
    app.dependency_overrides[get_db_session] = _override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as c:
        yield c


@pytest.fixture
def rsa_key_pair() -> tuple[str, str]:
    """
    Ephemeral RSA-2048 key pair for JWT tests.
    Returns (private_pem, public_pem).
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


@pytest.fixture
def valid_register_payload() -> dict:
    return {
        "email": "testuser@aurafit.ai",
        "password": "Secure123",
        "full_name": "Test User",
    }

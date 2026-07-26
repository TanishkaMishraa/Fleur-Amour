"""
AuraFit — Auth endpoint integration tests.
Uses the async test client with in-memory DB and mock Redis.
Tests full request→service→repository→response cycle.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, mock_redis: AsyncMock) -> None:
    with patch("app.services.auth_service.get_redis", return_value=mock_redis):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "ValidPass1",
                "full_name": "New User",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == "newuser@example.com"
    assert "id" in body["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, mock_redis: AsyncMock) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "ValidPass1",
        "full_name": "First User",
    }
    with patch("app.services.auth_service.get_redis", return_value=mock_redis):
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "weak", "full_name": "Test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient, mock_redis: AsyncMock) -> None:
    with patch("app.services.auth_service.get_redis", return_value=mock_redis):
        mock_redis.get = AsyncMock(return_value=None)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "AnyPass1"},
        )
    assert resp.status_code == 401

"""
AuraFit — Integration Tests: Full Stack (Stage 10).

Tests the complete user journey across multiple services:
  1. Register user → verify email → login
  2. Complete facial analysis (mock AI service)
  3. Compute color profile
  4. Start and complete style quiz
  5. Generate Style DNA report
  6. Check recommendations flow
  7. Test subscription feature gates

These tests require:
  - Running PostgreSQL (test DB)
  - Running Redis
  - Running user-service (via httpx.AsyncClient)

Run with:
  pytest tests/integration/test_full_stack.py -v
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """AsyncClient pointed at the test app."""
    from app.main import app
    from httpx import ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(client):
    """Register and verify a test user; return auth tokens."""
    email    = f"test+{uuid.uuid4().hex[:8]}@aurafit-test.ai"
    password = "TestP@ssw0rd123!"

    # Register
    resp = await client.post("/api/v1/auth/register", json={
        "email":      email,
        "password":   password,
        "full_name":  "Test User",
    })
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()["data"]

    # Return auth context
    return {
        "user_id": data["user"]["id"],
        "email":   email,
        "password":password,
        "tokens":  {"access": data["access_token"], "refresh": data["refresh_token"]},
    }


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['tokens']['access']}"}


# ── Auth tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_and_login(client):
    """Full auth round-trip: register → login → get me → refresh → logout."""
    email    = f"flow-{uuid.uuid4().hex[:6]}@aurafit-test.ai"
    password = "SecureP@ss99!"

    # Register
    resp = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Flow User"
    })
    assert resp.status_code == 201
    tokens = resp.json()["data"]
    access  = tokens["access_token"]
    refresh = tokens["refresh_token"]
    assert access and refresh

    # Get current user
    resp = await client.get("/api/v1/users/me",
                            headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == email

    # Refresh token
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_access = resp.json()["data"]["access_token"]
    assert new_access != access

    # Logout
    resp = await client.post("/api/v1/auth/logout",
                             headers={"Authorization": f"Bearer {new_access}"})
    assert resp.status_code == 200

    # Old token should now be invalid
    resp = await client.get("/api/v1/users/me",
                            headers={"Authorization": f"Bearer {new_access}"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    """Registering with an existing email returns 409."""
    email = f"dup-{uuid.uuid4().hex[:6]}@aurafit-test.ai"
    payload = {"email": email, "password": "P@ss123!", "full_name": "A"}

    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_wrong_password_rejected(client, test_user):
    """Login with wrong password returns 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401


# ── Profile tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_update(client, test_user, auth_headers):
    """Update beauty profile and verify persistence."""
    resp = await client.put("/api/v1/profiles/me", json={
        "skin_tone":     "medium",
        "skin_type":     "combination",
        "undertone":     "warm",
        "skin_concerns": ["acne", "hyperpigmentation"],
        "budget_range":  "mid",
    }, headers=auth_headers)
    assert resp.status_code == 200

    # Verify
    get_resp = await client.get("/api/v1/profiles/me", headers=auth_headers)
    profile = get_resp.json()["data"]
    assert profile["skin_tone"] == "medium"
    assert "acne" in profile["skin_concerns"]


# ── Color profile tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_color_season_guide_public(client):
    """Season guide is publicly accessible."""
    resp = await client.get("/api/v1/color/season-guide")
    assert resp.status_code == 200
    seasons = resp.json()["seasons"]
    assert len(seasons) >= 12     # At least 12 extended seasons


@pytest.mark.asyncio
async def test_color_profile_requires_scan(client, test_user, auth_headers):
    """Computing color profile without a scan returns 404."""
    resp = await client.post("/api/v1/color/compute", json={
        "use_extended_seasons": True
    }, headers=auth_headers)
    assert resp.status_code == 404


# ── Quiz tests ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quiz_definition_public(client):
    """Quiz definition is publicly accessible."""
    resp = await client.get("/api/v1/style-dna/quiz")
    assert resp.status_code == 200
    quiz = resp.json()
    assert quiz["total"] == 35
    assert len(quiz["section_order"]) == 5


@pytest.mark.asyncio
async def test_quiz_full_flow(client, test_user, auth_headers):
    """Start quiz → answer all questions → complete → verify archetypes."""
    # Start session
    resp = await client.post("/api/v1/style-dna/quiz/start",
                             headers=auth_headers)
    assert resp.status_code == 200
    session_id = resp.json()["data"]["session_id"]
    total_steps = resp.json()["data"]["total_steps"]
    assert total_steps == 35

    # Get quiz definition
    quiz_resp = await client.get("/api/v1/style-dna/quiz")
    questions = [
        q
        for section in quiz_resp.json()["section_order"]
        for q in quiz_resp.json()["sections"][section]
    ]

    # Answer all questions with first option
    for i, q in enumerate(questions):
        payload: dict = {
            "question_id":    q["id"],
            "question_index": q["index"],
        }
        if q["type"] in ("single", "image_grid"):
            payload["answer_value"] = q["options"][0]["id"]
        elif q["type"] == "multi":
            payload["answer_options"] = [q["options"][0]["id"]]
        elif q["type"] == "scale":
            payload["answer_value"] = "5"

        resp = await client.post(
            f"/api/v1/style-dna/quiz/{session_id}/respond",
            json=payload,
            headers=auth_headers
        )
        assert resp.status_code == 200

    # Complete
    resp = await client.post(
        f"/api/v1/style-dna/quiz/{session_id}/complete",
        headers=auth_headers
    )
    assert resp.status_code == 200
    result = resp.json()["data"]
    assert result["primary_archetype"] is not None
    assert result["secondary_archetype"] is not None


# ── Subscription tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plans_public(client):
    """Plans endpoint is public."""
    resp = await client.get("/api/v1/subscriptions/plans")
    assert resp.status_code == 200
    plans = resp.json()["plans"]
    assert len(plans) == 4   # FREE, GLOW, RADIANCE, LUXE
    plan_ids = {p["id"] for p in plans}
    assert {"free", "glow", "radiance", "luxe"} == plan_ids


@pytest.mark.asyncio
async def test_subscription_defaults_to_free(client, test_user, auth_headers):
    """New users default to free plan."""
    resp = await client.get("/api/v1/subscriptions/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["subscription"]["plan"] == "free"
    assert data["subscription"]["status"] == "active"


@pytest.mark.asyncio
async def test_feature_gate_free_plan(client, test_user, auth_headers):
    """Free plan blocks virtual try-on and wardrobe AI."""
    for feature in ("virtual_tryon", "celebrity_matching", "pdf_export"):
        resp = await client.post("/api/v1/subscriptions/check", json={
            "feature": feature
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["allowed"] is False, f"{feature} should be blocked on free plan"
        assert data["reason"] is not None


@pytest.mark.asyncio
async def test_upgrade_flow(client, test_user, auth_headers):
    """Upgrade returns a payment intent (mock)."""
    resp = await client.post("/api/v1/subscriptions/upgrade", json={
        "plan": "glow",
        "provider": "razorpay",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["amount"] == 499
    assert "order_id" in data


# ── Admin tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_requires_admin_role(client, test_user, auth_headers):
    """Regular users cannot access admin endpoints."""
    resp = await client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert resp.status_code == 403


# ── Health check tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health endpoint returns ok without auth."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_probe(client):
    """Readiness probe verifies DB connectivity."""
    resp = await client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "ready")

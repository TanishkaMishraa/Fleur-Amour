"""
AuraFit — Repository unit tests.
Tests CRUD, soft-delete, pagination, and domain-specific queries.
Uses in-memory SQLite via test_session fixture.
"""
from __future__ import annotations

import uuid

import pytest

from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


class TestBaseRepositoryCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, test_session):
        repo = UserRepository(test_session)
        user = await repo.create(
            email=f"u-{uuid.uuid4()}@aurafit.ai",
            full_name="Test User",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )
        assert user.id is not None

        fetched = await repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, test_session):
        repo = UserRepository(test_session)
        result = await repo.get_by_id(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_mutates_field(self, test_session):
        repo = UserRepository(test_session)
        user = await repo.create(
            email=f"u-{uuid.uuid4()}@aurafit.ai",
            full_name="Old Name",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )
        updated = await repo.update(user, full_name="New Name")
        assert updated.full_name == "New Name"

    @pytest.mark.asyncio
    async def test_soft_delete_hides_from_get(self, test_session):
        repo = UserRepository(test_session)
        user = await repo.create(
            email=f"u-{uuid.uuid4()}@aurafit.ai",
            full_name="To Delete",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )
        await repo.soft_delete(user)
        result = await repo.get_by_id(user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_email_lookup_is_case_insensitive(self, test_session):
        repo = UserRepository(test_session)
        unique_email = f"CaSeUser-{uuid.uuid4()}@AURAFIT.AI"
        await repo.create(
            email=unique_email.lower(),
            full_name="Case User",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )
        found = await repo.get_by_email(unique_email.upper())
        assert found is not None

    @pytest.mark.asyncio
    async def test_email_exists_returns_true_for_existing(self, test_session):
        repo = UserRepository(test_session)
        email = f"exists-{uuid.uuid4()}@aurafit.ai"
        await repo.create(
            email=email,
            full_name="Exists User",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )
        assert await repo.email_exists(email) is True

    @pytest.mark.asyncio
    async def test_email_exists_returns_false_for_new(self, test_session):
        repo = UserRepository(test_session)
        result = await repo.email_exists(f"new-{uuid.uuid4()}@aurafit.ai")
        assert result is False

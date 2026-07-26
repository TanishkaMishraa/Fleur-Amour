"""
AuraFit — Generic async repository.
Implements standard CRUD + soft-delete + pagination.
Service layer calls repositories; never touches ORM directly.
All queries are async (asyncpg). SoftDeleteMixin models are filtered automatically.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AuraFitBase, SoftDeleteMixin

ModelT = TypeVar("ModelT", bound=AuraFitBase)


class BaseRepository(Generic[ModelT]):
    """
    Type-safe async CRUD. Subclasses add domain-specific queries.
    Never instantiate directly — use domain-specific repositories.
    """

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    # ── Read ─────────────────────────────────────────────────────────────────

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        """Return model by PK. Returns None if not found or soft-deleted."""
        obj = await self.session.get(self.model, id)
        if obj is None:
            return None
        if isinstance(obj, SoftDeleteMixin) and obj.is_deleted:
            return None
        return obj

    async def get_by_id_or_raise(self, id: uuid.UUID) -> ModelT:
        """Return model by PK or raise ValueError."""
        obj = await self.get_by_id(id)
        if obj is None:
            raise ValueError(f"{self.model.__name__} {id} not found")
        return obj

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by: Any = None,
        **filters: Any,
    ) -> tuple[Sequence[ModelT], int]:
        """
        Paginated list. Returns (items, total_count).
        Soft-deleted rows excluded automatically.
        Arbitrary equality filters passed as kwargs.
        """
        base_query = select(self.model)

        if issubclass(self.model, SoftDeleteMixin):
            base_query = base_query.where(
                self.model.is_deleted == False  # noqa: E712
            )

        for attr, value in filters.items():
            base_query = base_query.where(getattr(self.model, attr) == value)

        # Count before pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total: int = (await self.session.execute(count_query)).scalar_one()

        if order_by is not None:
            base_query = base_query.order_by(order_by)
        base_query = base_query.offset(offset).limit(limit)

        rows = (await self.session.execute(base_query)).scalars().all()
        return rows, total

    async def count(self, **filters: Any) -> int:
        """Return count of rows matching filters."""
        q = select(func.count()).select_from(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            q = q.where(self.model.is_deleted == False)  # noqa: E712
        for attr, value in filters.items():
            q = q.where(getattr(self.model, attr) == value)
        return (await self.session.execute(q)).scalar_one()

    # ── Write ────────────────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> ModelT:
        """Instantiate, add, flush (to get DB-assigned values), refresh."""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        """Apply kwargs to obj, flush, refresh."""
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Hard delete. Use soft_delete() for most user-facing operations."""
        await self.session.delete(obj)
        await self.session.flush()

    async def soft_delete(self, obj: ModelT) -> ModelT:
        """
        Mark is_deleted=True and record deleted_at.
        Raises TypeError if model does not mix in SoftDeleteMixin.
        """
        if not isinstance(obj, SoftDeleteMixin):
            raise TypeError(
                f"{self.model.__name__} does not support soft delete "
                f"— mix in SoftDeleteMixin."
            )
        obj.is_deleted = True
        obj.deleted_at = datetime.now(UTC)
        self.session.add(obj)
        await self.session.flush()
        return obj

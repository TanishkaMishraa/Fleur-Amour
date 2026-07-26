"""
AuraFit — SQLAlchemy declarative base and shared mixins.
Canonical base class: AuraFitBase (alias Base kept for compat).
All ORM models inherit: AuraFitBase + UUIDPrimaryKeyMixin + TimestampMixin.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AuraFitBase(DeclarativeBase):
    """Project-wide declarative base. All models must inherit from this."""

    def __repr__(self) -> str:
        pk = getattr(self, "id", "?")
        return f"<{self.__class__.__name__} id={pk}>"

    def to_dict(self) -> dict[str, Any]:
        """Utility: column values as plain dict (for logging/debugging only)."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Backwards-compatible alias used by earlier partial files
Base = AuraFitBase


class UUIDPrimaryKeyMixin:
    """UUID v4 primary key. Applied to every AuraFit model."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


# Keep old alias name so legacy generated code still compiles
UUIDMixin = UUIDPrimaryKeyMixin


class TimestampMixin:
    """Automatic created_at / updated_at columns, both timezone-aware."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Non-destructive deletion. Repositories filter is_deleted=False by default.
    Hard purge is reserved for GDPR anonymisation jobs only.
    """
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

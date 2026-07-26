"""
AuraFit - Notification ORM models.
Notification stores in-app notifications.
NotificationPreference stores per-user opt-in settings.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    deep_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class NotificationPreference(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    email_marketing: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_recommendations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_tryon: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

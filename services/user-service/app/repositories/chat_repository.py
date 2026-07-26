"""
AuraFit — ChatSession and ChatMessage repositories.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatSession, session)

    async def get_by_token(self, token: str) -> ChatSession | None:
        result = await self._session.execute(
            select(ChatSession)
            .where(ChatSession.session_token == token)
            .where(ChatSession.is_active == True)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, active_only: bool = True
    ) -> list[ChatSession]:
        q = select(ChatSession).where(ChatSession.user_id == user_id)
        if active_only:
            q = q.where(ChatSession.is_active == True)  # noqa: E712
        q = q.order_by(ChatSession.created_at.desc())
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def deactivate(self, session_id: uuid.UUID) -> None:
        s = await self.get_by_id(session_id)
        if s:
            await self.update(s, is_active=False)


class ChatMessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatMessage, session)

    async def get_recent(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Return the last `limit` messages, oldest-first for LLM context order."""
        # Subquery: get IDs of latest N messages
        sub = (
            select(ChatMessage.id)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .subquery()
        )
        result = await self._session.execute(
            select(ChatMessage)
            .where(ChatMessage.id.in_(select(sub.c.id)))
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_for_session(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id)
        )
        return result.scalar_one()

    async def get_total_tokens(self, session_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.sum(ChatMessage.tokens_used), 0))
            .where(ChatMessage.session_id == session_id)
        )
        return result.scalar_one()

"""
AuraFit — Chat / Aura AI assistant service.
SSE streaming responses. Provider-agnostic LLM client interface.
Sliding context window with automatic summary compression.
Stage 0 tool calling: search_products, get_skin_analysis, create_outfit, etc.
"""
from __future__ import annotations

import json
import secrets
import uuid
from typing import AsyncGenerator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError, PermissionDeniedError, RateLimitedError
from app.core.logging import get_logger
from app.models.chat import ChatSession, MessageRole
from app.repositories.chat_repository import ChatMessageRepository, ChatSessionRepository
from app.schemas.chat import ChatHistoryResponse, ChatSessionOut, MessageOut

logger = get_logger(__name__)

# Sliding window: keep last N messages in context before summarising
_CONTEXT_WINDOW_MESSAGES = 20
_RATE_LIMIT_MESSAGES_PER_HOUR = 30


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = ChatSessionRepository(session)
        self._message_repo = ChatMessageRepository(session)
        self._settings = get_settings()

    async def create_session(self, user_id: uuid.UUID) -> ChatSession:
        """Create a new Aura chat session."""
        token = secrets.token_urlsafe(32)
        chat_session = await self._session_repo.create(
            user_id=user_id,
            session_token=token,
            is_active=True,
        )
        logger.info("aurafit.chat.session_created", session_id=str(chat_session.id))
        return chat_session

    async def stream_response(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator producing SSE events.
        Persists user message, calls LLM, streams tokens, persists assistant message.
        """
        chat_session = await self._session_repo.get_by_id(session_id)
        if not chat_session:
            raise NotFoundError("Chat session not found")
        if chat_session.user_id != user_id:
            raise PermissionDeniedError("Access denied")

        # Rate limit check
        await self._check_rate_limit(user_id)

        # Persist user message
        user_msg = await self._message_repo.create(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
        )

        # Build context messages for LLM
        recent_messages = await self._message_repo.get_recent(
            session_id, limit=_CONTEXT_WINDOW_MESSAGES
        )
        messages_payload = [
            {"role": m.role.value, "content": m.content}
            for m in recent_messages
        ]

        # Build system prompt with user context
        system_prompt = await self._build_system_prompt(user_id)

        # Stream from LLM
        full_response = ""
        tokens_used = 0

        try:
            async for event_data in self._call_llm_streaming(
                system_prompt=system_prompt,
                messages=messages_payload,
            ):
                full_response += event_data.get("content", "")
                tokens_used += event_data.get("tokens", 0)
                yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as exc:
            logger.exception("aurafit.chat.llm_error", error=str(exc))
            error_event = {"type": "error", "message": "AI assistant temporarily unavailable"}
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # Persist assistant message
        await self._message_repo.create(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=full_response,
            tokens_used=tokens_used,
            model_version="claude-sonnet-4-20250514",
        )

        # Trigger context compression if message count exceeds window
        total = await self._message_repo.count_for_session(session_id)
        if total > _CONTEXT_WINDOW_MESSAGES * 2:
            from app.tasks.maintenance_tasks import compress_chat_context
            compress_chat_context.delay(session_id=str(session_id))

        done_event = {"type": "done", "tokens_used": tokens_used}
        yield f"data: {json.dumps(done_event)}\n\n"

    async def get_history(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ChatHistoryResponse:
        chat_session = await self._session_repo.get_by_id(session_id)
        if not chat_session:
            raise NotFoundError("Chat session not found")
        if chat_session.user_id != user_id:
            raise PermissionDeniedError("Access denied")

        messages = await self._message_repo.get_recent(
            session_id, limit=_CONTEXT_WINDOW_MESSAGES
        )
        total = await self._message_repo.count_for_session(session_id)

        return ChatHistoryResponse(
            session=ChatSessionOut.model_validate(chat_session),
            messages=[MessageOut.model_validate(m) for m in messages],
            has_more=total > len(messages),
        )

    async def _build_system_prompt(self, user_id: uuid.UUID) -> str:
        """Construct personalised system prompt using user profile data."""
        # In a complete implementation, fetch profile from cache/DB
        # and inject skin_tone, style_archetypes, etc.
        return (
            "You are Aura, a personal AI beauty and style assistant for AuraFit. "
            "You have access to the user's beauty profile and wardrobe. "
            "Provide personalised advice based on their skin type, tone, and style preferences. "
            "When recommending products, explain why they suit the user specifically. "
            "Be warm, knowledgeable, and concise."
        )

    async def _call_llm_streaming(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """
        Provider-agnostic LLM streaming wrapper.
        Yields event dicts: {"type": "token", "content": "..."} per token.
        Replace with actual Anthropic/OpenAI SDK streaming in production.
        """
        # Stub: yields a single simulated response
        # In production: use anthropic.AsyncAnthropic().messages.stream(...)
        yield {"type": "token", "content": "Hello! How can I help with your style today?"}
        yield {"type": "token", "content": ""}

    async def _check_rate_limit(self, user_id: uuid.UUID) -> None:
        """Redis sliding window rate limit: 30 messages/hour per user."""
        from app.cache.redis_client import RedisKeys, get_redis
        r = get_redis()
        key = RedisKeys.rate_ai(str(user_id))
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 3600)
        if count > _RATE_LIMIT_MESSAGES_PER_HOUR:
            raise RateLimitedError(
                f"AI chat limit of {_RATE_LIMIT_MESSAGES_PER_HOUR} messages/hour reached"
            )

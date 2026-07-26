"""
AuraFit — Chat session schemas.
ChatSession and ChatMessage request/response shapes.
SSE streaming sends individual token events; these schemas cover REST endpoints.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Request schemas ───────────────────────────────────────────────────────────

class MessageRequest(AuraFitSchema):
    content: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message to Aura AI assistant",
    )


# ── Response schemas ──────────────────────────────────────────────────────────

class ChatSessionOut(UUIDSchema, TimestampSchema):
    user_id: UUID
    session_token: str
    context_summary: str | None
    is_active: bool
    total_messages: int = 0
    total_tokens_used: int = 0


class MessageOut(UUIDSchema, TimestampSchema):
    session_id: UUID
    role: str = Field(..., description="user | assistant")
    content: str
    tool_calls: dict | None = None
    tokens_used: int | None
    model_version: str | None


class ChatHistoryResponse(AuraFitSchema):
    """Paginated message history for a session."""
    session: ChatSessionOut
    messages: list[MessageOut]
    has_more: bool = False

"""
AuraFit — Chatbot endpoints (/api/v1/chat/*).
POST /chat/sessions           → create session
POST /chat/sessions/{id}/messages  → send message (SSE streaming response)
GET  /chat/sessions/{id}/messages  → full history
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import ChatServiceDep, CurrentUser
from app.schemas.base import APIResponse
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatSessionOut,
    MessageRequest,
    MessageOut,
)

router = APIRouter(prefix="/chat", tags=["Aura AI Chatbot"])


@router.post(
    "/sessions",
    response_model=APIResponse[ChatSessionOut],
    status_code=status.HTTP_201_CREATED,
    summary="Start a new chat session with Aura",
)
async def create_session(
    current_user: CurrentUser,
    svc: ChatServiceDep,
) -> APIResponse[ChatSessionOut]:
    session = await svc.create_session(current_user.id)
    return APIResponse(data=ChatSessionOut.model_validate(session))


@router.post(
    "/sessions/{session_id}/messages",
    summary="Send message and receive streaming AI response (SSE)",
    description=(
        "Sends a user message to Aura. Response is an SSE stream of JSON events:\n\n"
        "- `{\"type\": \"token\", \"content\": \"...\"}` — partial token\n"
        "- `{\"type\": \"tool_call\", \"name\": \"...\", \"args\": {...}}` — tool invocation\n"
        "- `{\"type\": \"tool_result\", \"content\": [...]}` — tool result injected into context\n"
        "- `{\"type\": \"done\", \"tokens_used\": 123}` — stream complete\n\n"
        "Connect with EventSource or fetch + ReadableStream."
    ),
    response_class=StreamingResponse,
)
async def send_message(
    session_id: UUID,
    payload: MessageRequest,
    current_user: CurrentUser,
    svc: ChatServiceDep,
) -> StreamingResponse:
    """Returns an SSE stream. Content-Type: text/event-stream."""
    stream = svc.stream_response(
        session_id=session_id,
        user_id=current_user.id,
        content=payload.content,
    )
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering for SSE
        },
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=APIResponse[ChatHistoryResponse],
    summary="Retrieve full chat history for a session",
)
async def get_history(
    session_id: UUID,
    current_user: CurrentUser,
    svc: ChatServiceDep,
) -> APIResponse[ChatHistoryResponse]:
    history = await svc.get_history(session_id, current_user.id)
    return APIResponse(data=history)

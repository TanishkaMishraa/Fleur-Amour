"""
AuraFit — HTTP middleware stack (Stage 3).

1. RequestLoggingMiddleware
   Attaches a unique request_id to every request.
   Logs method, path, status, and duration on completion.
   Binds request_id to structlog context so all downstream logs carry it.

2. JWTPayloadMiddleware
   Decodes the JWT (if present) and stashes payload in request.state.
   Lets endpoints access the raw JWT claims (e.g. `jti` for logout)
   without a second decode. Does NOT validate — FastAPI deps handle that.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import structlog

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Assigns X-Request-ID to every request/response.
    Logs access in structured JSON (structlog).
    Binding request_id to contextvars propagates it to all
    downstream log calls in the same async task.
    """

    SKIP_PATHS = frozenset({"/health", "/ready", "/metrics"})

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_ns   = time.perf_counter_ns()

        # Bind to structlog context for this async task
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        response.headers["X-Request-ID"] = request_id

        # Skip noisy probe paths
        if request.url.path not in self.SKIP_PATHS:
            logger.info(
                "http.request",
                status=response.status_code,
                duration_ms=round(elapsed_ms, 2),
                client=getattr(getattr(request, "client", None), "host", "unknown"),
            )

        return response


class JWTPayloadMiddleware(BaseHTTPMiddleware):
    """
    Decodes JWT from Authorization header (if present) and stores
    the raw payload in request.state.jwt_payload.
    Errors are silently ignored — auth validation is handled by deps.

    This allows the logout endpoint to extract `jti` from request.state
    without re-decoding the token.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.jwt_payload = {}

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token,
                    self._settings.JWT_PUBLIC_KEY,
                    algorithms=[self._settings.ALGORITHM],
                    options={"verify_exp": False},   # exp checked by deps
                )
                request.state.jwt_payload = payload
                # Also bind user_id to structlog context
                if uid := payload.get("sub"):
                    structlog.contextvars.bind_contextvars(user_id=uid)
            except Exception:
                pass   # silently ignore — auth deps will reject invalid tokens

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends hardened security headers to every response.
    Works alongside Nginx headers (belt-and-suspenders).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._is_production = get_settings().is_production

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]       = "camera=(), microphone=(), geolocation=()"
        if self._is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response

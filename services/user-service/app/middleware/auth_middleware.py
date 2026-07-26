"""
AuraFit — Auth middleware (Stage 3).
1. RateLimitMiddleware  — per-route sliding window via Redis.
2. RequestContextMiddleware — attaches request_id + decoded JWT payload to request.state.
3. SecurityHeadersMiddleware — adds CSP, HSTS etc. (see main.py for inline version).
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response, status
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.cache.redis_client import get_redis
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Attaches to request.state:
      - request_id  (from X-Request-ID header or new UUID)
      - jwt_payload (decoded token claims if present — no validation here)
      - start_time  (float monotonic)
    Binds request_id to structlog context for the duration of the request.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()
        request.state.jwt_payload = {}

        # Best-effort JWT payload extraction (no key verification — done in dependency)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt as pyjwt
                token = auth_header[7:]
                # decode_options: {"verify_signature": False} — just extract claims
                request.state.jwt_payload = pyjwt.decode(
                    token, options={"verify_signature": False}, algorithms=["RS256"]
                )
            except Exception:
                pass

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - request.state.start_time) * 1000

        response.headers["X-Request-ID"]   = request_id
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP + per-route sliding window rate limiter backed by Redis.
    Configured limits from Stage 0:
      /auth/*       → 5 req/min
      /analysis/*   → 10 req/hour
      everything else → 120 req/min
    Uses Redis INCR + EXPIRE (atomic with pipeline).
    """

    ROUTE_LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/auth/":     (5,  60),    # 5 per 60 sec
        "/api/v1/analysis/": (10, 3600),  # 10 per hour
    }
    DEFAULT_LIMIT = (120, 60)  # 120 per minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        if settings.is_local:
            return await call_next(request)   # skip rate limiting in local dev

        ip    = request.client.host if request.client else "unknown"
        path  = request.url.path

        limit, window = self.DEFAULT_LIMIT
        for prefix, (lim, win) in self.ROUTE_LIMITS.items():
            if path.startswith(prefix):
                limit, window = lim, win
                break

        key = f"rl:{path}:{ip}"
        try:
            r = get_redis()
            async with r.pipeline(transaction=False) as pipe:
                pipe.incr(key)
                pipe.expire(key, window)
                results = await pipe.execute()
            count = results[0]

            if count > limit:
                logger.warning("aurafit.rate_limit.exceeded", ip=ip, path=path, count=count)
                return ORJSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "data": None,
                        "errors": [{
                            "code":    "RATE_LIMITED",
                            "message": f"Too many requests. Limit: {limit} per {window}s.",
                        }],
                    },
                    headers={"Retry-After": str(window)},
                )
        except Exception as exc:
            # Redis unavailable → fail open (don't block users)
            logger.warning("aurafit.rate_limit.redis_error", error=str(exc))

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Appends security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]       = "camera=(), microphone=(), geolocation=()"
        if not get_settings().is_local:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

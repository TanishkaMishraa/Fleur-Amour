"""
AuraFit — Per-route Redis sliding-window rate limiter middleware.
Supplements Nginx global limits with per-user / per-IP application-level limits.
Configured thresholds match Stage 0 architecture spec.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.cache.redis_client import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

# (route_prefix, window_seconds, max_requests, key_by)
_RULES: list[tuple[str, int, int, str]] = [
    ("/api/v1/auth/login",            60,   5,  "ip"),
    ("/api/v1/auth/register",         60,   3,  "ip"),
    ("/api/v1/auth/forgot-password",  60,   2,  "ip"),
    ("/api/v1/auth/resend-verification", 120, 1, "ip"),
    ("/api/v1/auth/oauth",            60,   10, "ip"),
    ("/api/v1/analysis",              3600, 30, "user"),
    ("/api/v1/chat",                  3600, 30, "user"),
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter using Redis INCR + EXPIRE."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        for prefix, window, limit, key_by in _RULES:
            if not path.startswith(prefix):
                continue

            # Determine rate-limit key
            if key_by == "ip":
                identity = request.client.host if request.client else "unknown"
            else:
                # Extract user_id from JWT payload (attached by auth middleware)
                payload = getattr(request.state, "jwt_payload", {})
                identity = payload.get("sub", request.client.host if request.client else "anon")

            bucket   = int(time.time()) // window
            rl_key   = f"rl:{prefix}:{identity}:{bucket}"

            try:
                r       = get_redis()
                count   = await r.incr(rl_key)
                if count == 1:
                    await r.expire(rl_key, window)

                if count > limit:
                    logger.warning(
                        "aurafit.rate_limit.exceeded",
                        path=path, identity=identity, count=count, limit=limit,
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "data":    None,
                            "errors":  [{"code": "RATE_LIMITED", "message": "Too many requests. Please slow down."}],
                        },
                        headers={"Retry-After": str(window)},
                    )
            except Exception as exc:
                # Never hard-fail on Redis errors — allow the request through
                logger.error("aurafit.rate_limit.redis_error", error=str(exc))

            break   # First matching rule wins

        return await call_next(request)

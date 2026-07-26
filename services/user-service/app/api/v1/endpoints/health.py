"""
AuraFit — Health and readiness endpoints.
/health  → liveness  (always 200 if the process is up)
/ready   → readiness (checks DB + Redis; used by Kubernetes readiness probe)
Both are mounted outside /api/v1 prefix at root level in main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.cache.redis_client import get_redis

router = APIRouter(tags=["Health"])

settings = get_settings()


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns 200 if the process is running. No dependency checks.",
)
async def health() -> ORJSONResponse:
    return ORJSONResponse(
        content={
            "status": "ok",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Returns 200 only if the service can reach PostgreSQL and Redis. "
        "Used by Kubernetes to gate traffic during startup and after failures."
    ),
)
async def ready() -> ORJSONResponse:
    checks: dict[str, str] = {}
    overall_ok = True

    # ── PostgreSQL check ──────────────────────────────────────────────────────
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        overall_ok = False

    # ── Redis check ───────────────────────────────────────────────────────────
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        overall_ok = False

    status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return ORJSONResponse(
        status_code=status_code,
        content={"status": "ready" if overall_ok else "degraded", "checks": checks},
    )

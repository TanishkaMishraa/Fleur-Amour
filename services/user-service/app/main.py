"""
AuraFit User Service — FastAPI application factory (Stage 3).
Complete auth + session + RBAC middleware stack.
Docs at /docs in local/staging; disabled in production.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.events import lifespan
from app.api.v1.router import api_router
from app.middleware.auth_middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

settings = get_settings()


def create_app() -> FastAPI:
    """Application factory — returns a fully configured FastAPI instance."""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**AuraFit User Service** — complete authentication, session management, "
            "user profiles, wardrobe, AI skin analysis, and chatbot.\n\n"
            "Part of the AuraFit AI beauty and personal styling platform."
        ),
        docs_url    ="/docs"         if not settings.is_production else None,
        redoc_url   ="/redoc"        if not settings.is_production else None,
        openapi_url ="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
        contact={"name": "AuraFit Engineering", "email": "eng@aurafit.ai"},
        license_info={"name": "Proprietary — All rights reserved"},
        openapi_tags=[
            {"name": "Authentication",          "description": "Register, login, OAuth, token rotation"},
            {"name": "Multi-Factor Authentication", "description": "TOTP 2FA setup and management"},
            {"name": "Session Management",      "description": "View and revoke active device sessions"},
            {"name": "Users",                   "description": "Account management, password change"},
            {"name": "User Preferences",        "description": "Notifications, display, privacy settings"},
            {"name": "Beauty Profile",          "description": "Skin, hair, fragrance, style preferences"},
            {"name": "Wardrobe",                "description": "Collections, items, AI outfit builder"},
            {"name": "Skin & Facial Analysis",  "description": "AI facial scan pipeline"},
            {"name": "File Uploads",            "description": "S3 presigned direct upload flow"},
            {"name": "Aura AI Chatbot",         "description": "Streaming AI personal stylist"},
            {"name": "Health",                  "description": "Kubernetes liveness/readiness probes"},
        ],
    )

    # ── Middleware stack (outermost = last registered) ─────────────────────────
    # Order: GZip → CORS → Security → RateLimit → RequestContext → handler

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # ── Exception handlers ─────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ── Health / readiness (Kubernetes probes) ─────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=True)
    async def health_check() -> dict:
        return {
            "status":  "ok",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def readiness() -> dict:
        from sqlalchemy import text
        from app.db.session import get_session_factory
        from app.cache.redis_client import get_redis
        factory = get_session_factory()
        async with factory() as db:
            await db.execute(text("SELECT 1"))
        await get_redis().ping()
        return {"status": "ready"}

    return app


app = create_app()

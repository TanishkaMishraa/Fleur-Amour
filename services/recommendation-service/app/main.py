"""
AuraFit — Recommendation Service entry point.
FastAPI app factory. Loads CF model at startup. Registers all routers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.api.v1.endpoints.recommendations import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    settings = get_settings()
    structlog.configure(
        processors=[structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Init DB pool
    from app.db.session import init_db
    await init_db()

    # Load ALS model from disk (fast path — model pre-trained nightly)
    from app.services.algorithms.collaborative_filter import load_cf_model_at_startup
    load_cf_model_at_startup()

    structlog.get_logger().info("rec_service.startup_complete")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    from app.db.session import close_db
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AuraFit Recommendation Service — hybrid CF + content-based + profile-rules "
            "recommendation engine across 6 domains: makeup, skincare, haircare, "
            "fragrance, fashion, and accessories."
        ),
        docs_url="/docs"        if not settings.is_production else None,
        redoc_url="/redoc"      if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS if hasattr(settings, "ALLOWED_ORIGINS") else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()

"""
AuraFit — Application lifecycle hooks.
lifespan() context manager handles startup and shutdown.
- Startup: configure logging, init DB pool, init Redis pool
- Shutdown: drain connections gracefully
FastAPI's @asynccontextmanager lifespan replaces deprecated on_event handlers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Executed once at startup (before first request) and once at shutdown.
    The `yield` separates startup from shutdown.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("aurafit.startup.begin", service=app.title, version=app.version)

    from app.db.session import init_db
    from app.cache.redis_client import init_redis

    await init_db()
    logger.info("aurafit.startup.db_ready")

    await init_redis()
    logger.info("aurafit.startup.redis_ready")

    logger.info("aurafit.startup.complete")

    yield  # ← Application serves requests here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("aurafit.shutdown.begin")

    from app.db.session import close_db
    from app.cache.redis_client import close_redis

    await close_db()
    await close_redis()

    logger.info("aurafit.shutdown.complete")

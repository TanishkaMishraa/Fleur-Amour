"""
AuraFit — Recommendation Service async SQLAlchemy session factory.
asyncpg driver. Per-request sessions via FastAPI dependency injection.
Commit on success, rollback on exception — transactions are atomic per request.
"""
from __future__ import annotations

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """
    Initialise the async engine and session factory.
    Called once at application startup in lifespan().
    """
    global _engine, _session_factory

    settings = get_settings()

    _engine = create_async_engine(
        settings.database_url_str,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,                # detect stale TCP connections
        echo=settings.DATABASE_ECHO,
        connect_args={
            "server_settings": {
                "application_name": "aurafit-recommendation-service",
                "jit": "off",              # disable JIT for OLTP workloads
            },
            "command_timeout": 30,
        },
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,            # prevent lazy-load after commit
        autoflush=False,
        autocommit=False,
    )

    # Connectivity check at startup
    from sqlalchemy import text
    async with _engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    logger.info(
        "aurafit.db.ready",
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )


async def close_db() -> None:
    """Drain connection pool. Called at shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("aurafit.db.pool_closed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialised — call init_db() first (lifespan startup)"
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields a per-request AsyncSession.
    Commits on clean exit; rolls back on any exception.
    Usage:
        @router.get("/...")
        async def handler(session: AsyncSession = Depends(get_db_session)):
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

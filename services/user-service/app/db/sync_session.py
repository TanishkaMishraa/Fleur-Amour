"""
AuraFit — Synchronous SQLAlchemy session for Celery workers.
Celery tasks run synchronously, so they cannot use the asyncpg-based
async session from app.db.session. This module provides a sync
(psycopg2) engine + session factory for use inside @shared_task functions.

Usage in a Celery task:
    from app.db.sync_session import get_sync_session
    with get_sync_session() as session:
        scan = session.get(FacialScan, scan_id)
        scan.skin_analysis = {...}
        session.commit()
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
_SessionFactory: sessionmaker | None = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url_sync_str,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=_get_engine(), expire_on_commit=False)
    return _SessionFactory


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager yielding a sync SQLAlchemy session. Commits/rolls back automatically."""
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

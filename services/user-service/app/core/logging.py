"""
AuraFit — Structured logging via structlog.
JSON output in production (for ELK / CloudWatch ingestion).
Coloured console in local dev.
All code uses get_logger(__name__) — never stdlib logging.getLogger().
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import Environment, get_settings


def configure_logging() -> None:
    """Configure structlog processors and stdlib bridge. Call once at startup."""
    settings = get_settings()
    is_prod = settings.ENVIRONMENT == Environment.PRODUCTION

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,   # request_id, user_id from context
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if is_prod
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL)

    # Silence noisy third-party libraries
    for name in ("uvicorn.access", "sqlalchemy.engine", "httpx", "hpack"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger. Use as module-level constant."""
    return structlog.get_logger(name)

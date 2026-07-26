"""
AuraFit — Synchronous Redis client for Celery workers.
Mirrors app.cache.redis_client.RedisKeys conventions but uses the sync
redis-py client (Celery tasks are synchronous functions).

Used for:
  - Writing task status/progress (polled by GET /analysis/scan/{task_id})
  - Publishing pub/sub events for SSE push to connected clients
  - Caching the latest scan result for fast /users/me/scans/latest reads
"""
from __future__ import annotations

import json
from typing import Any

import redis

from app.cache.redis_client import RedisKeys  # re-use key naming conventions
from app.core.config import get_settings

_client: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(
            str(settings.REDIS_URL),
            decode_responses=True,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
        )
    return _client


def set_task_status(task_id: str, status: str, *, ttl: int = 86400) -> None:
    """Set overall task status: PENDING | STARTED | PROGRESS | SUCCESS | FAILURE."""
    get_sync_redis().setex(RedisKeys.task_status(task_id), ttl, status)


def set_task_progress(task_id: str, step: str, progress: int, *, ttl: int = 3600) -> None:
    """Set granular progress for client polling UI (step label + 0-100%)."""
    payload = json.dumps({"step": step, "progress": progress})
    get_sync_redis().setex(RedisKeys.task_progress(task_id), ttl, payload)


def set_task_result(task_id: str, result: dict[str, Any], *, ttl: int = 86400) -> None:
    """Cache the final result payload for fast retrieval without a DB hit."""
    get_sync_redis().setex(RedisKeys.task_result(task_id), ttl, json.dumps(result, default=str))


def publish_event(channel: str, payload: dict[str, Any]) -> None:
    """Publish a pub/sub event — consumed by the SSE gateway to push to connected clients."""
    get_sync_redis().publish(channel, json.dumps(payload, default=str))


def invalidate_cache(key: str) -> None:
    get_sync_redis().delete(key)

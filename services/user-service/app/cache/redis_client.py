"""
AuraFit — Canonical Redis client.
Single connection pool. All keys namespaced via RedisKeys.
Stage 0 namespace conventions strictly enforced here.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None  # type: ignore[type-arg]


async def init_redis() -> None:
    global _redis
    settings = get_settings()
    _redis = aioredis.from_url(
        str(settings.REDIS_URL),
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
        decode_responses=True,
        retry_on_timeout=True,
    )
    await _redis.ping()
    logger.info("aurafit.redis.connected")


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("aurafit.redis.closed")


def get_redis() -> Redis:  # type: ignore[type-arg]
    if _redis is None:
        raise RuntimeError("Redis not initialised. Call init_redis() first.")
    return _redis


# ── Stage 0 key namespace ────────────────────────────────────────────────────

class RedisKeys:
    """Centralised key builders. Never build keys ad-hoc in service code."""

    @staticmethod
    def session(token: str) -> str:
        return f"sessions:{token}"

    @staticmethod
    def user_online(user_id: str) -> str:
        return f"user:online:{user_id}"

    @staticmethod
    def token_blocklist(jti: str) -> str:
        return f"blocklist:tokens:{jti}"

    @staticmethod
    def refresh_token(token_hash: str) -> str:
        return f"refresh:{token_hash}"

    @staticmethod
    def rate_auth(ip: str) -> str:
        return f"rate:auth:{ip}"

    @staticmethod
    def rate_api(user_id: str, endpoint: str) -> str:
        return f"rl:{endpoint}:{user_id}"

    @staticmethod
    def rate_ai(user_id: str) -> str:
        return f"rl:ai:{user_id}"

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"profile:{user_id}"

    @staticmethod
    def latest_scan(user_id: str) -> str:
        return f"scan:latest:{user_id}"

    @staticmethod
    def task_status(task_id: str) -> str:
        return f"task:{task_id}:status"

    @staticmethod
    def task_result(task_id: str) -> str:
        return f"task:{task_id}:result"

    @staticmethod
    def task_progress(task_id: str) -> str:
        return f"task:{task_id}:progress"

    @staticmethod
    def rec_style(user_id: str) -> str:
        return f"rec:{user_id}:style"

    @staticmethod
    def rec_beauty(user_id: str) -> str:
        return f"rec:{user_id}:beauty"

    @staticmethod
    def rec_cf_candidates(user_id: str) -> str:
        return f"rec:{user_id}:cf:candidates"

    @staticmethod
    def product_cache(product_id: str) -> str:
        return f"product:{product_id}"

    @staticmethod
    def catalog_category(slug: str) -> str:
        return f"catalog:category:{slug}"

    @staticmethod
    def pubsub_scan_complete(user_id: str) -> str:
        return f"channel:scan:complete:{user_id}"

    @staticmethod
    def pubsub_tryon_complete(user_id: str) -> str:
        return f"channel:tryon:complete:{user_id}"

    @staticmethod
    def pubsub_rec_refresh(user_id: str) -> str:
        return f"channel:rec:refresh:{user_id}"


# ── Cache helpers ────────────────────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl: int) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    r = get_redis()
    keys = [k async for k in r.scan_iter(match=pattern, count=100)]
    if keys:
        return await r.delete(*keys)
    return 0


async def is_rate_limited(key: str, limit: int, window_seconds: int) -> bool:
    """Sliding window rate limiter. Returns True if limit exceeded."""
    r = get_redis()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window_seconds)
    return count > limit

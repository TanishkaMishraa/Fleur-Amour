"""
AuraFit — core/redis.py compatibility shim.
Some generated code imports from app.core.redis; re-export everything
from the canonical app.cache.redis_client so both import paths work.
"""
from app.cache.redis_client import (  # noqa: F401
    CacheService as _CacheService,
    RedisKeys,
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
    close_redis,
    get_redis,
    get_redis as get_redis_client,   # alias used by some integrations
    init_redis,
    is_rate_limited,
)

# Provide the CacheService class some older generated files import
try:
    from app.cache.redis_client import CacheService  # noqa: F401
except ImportError:
    pass


class CacheService:
    """
    Object-oriented cache helper. Wraps the module-level helpers.
    Inject via Redis client parameter for testability.
    """
    def __init__(self, redis=None) -> None:
        self._redis = redis

    async def get(self, key: str):
        return await cache_get(key)

    async def set(self, key: str, value, ttl: int | None = None) -> None:
        if ttl:
            await cache_set(key, value, ttl)
        else:
            import json
            r = get_redis()
            await r.set(key, json.dumps(value, default=str))

    async def delete(self, *keys: str) -> None:
        for key in keys:
            await cache_delete(key)

    async def exists(self, key: str) -> bool:
        r = get_redis()
        return bool(await r.exists(key))

    async def increment(self, key: str, ttl: int | None = None) -> int:
        r = get_redis()
        count = await r.incr(key)
        if count == 1 and ttl:
            await r.expire(key, ttl)
        return count

    async def publish(self, channel: str, message) -> None:
        import json
        r = get_redis()
        await r.publish(channel, json.dumps(message, default=str))

    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        return await is_rate_limited(key, limit, window_seconds)

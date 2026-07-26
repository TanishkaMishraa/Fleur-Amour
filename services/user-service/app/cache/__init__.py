"""AuraFit — Cache package. Canonical Redis client lives here."""
from app.cache.redis_client import (
    RedisKeys,
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
    close_redis,
    get_redis,
    init_redis,
)

__all__ = [
    "RedisKeys",
    "get_redis",
    "init_redis",
    "close_redis",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cache_delete_pattern",
]

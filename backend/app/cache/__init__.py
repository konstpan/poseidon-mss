"""Cache module for Poseidon MSS.

Provides Redis-based caching for vessel positions and other frequently accessed data.
"""

from app.cache.redis_client import (
    RedisClient,
    get_redis_client,
    init_redis_client,
    close_redis_client,
)

__all__ = [
    "RedisClient",
    "get_redis_client",
    "init_redis_client",
    "close_redis_client",
]

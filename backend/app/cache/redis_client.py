"""Redis caching layer for Poseidon MSS.

Provides:
- Connection pooling for Redis
- Vessel position caching with TTL
- Helper methods for common cache operations
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache key prefixes
VESSEL_POSITION_PREFIX = "vessel:position:"
VESSEL_STATIC_PREFIX = "vessel:static:"
ZONE_PREFIX = "zone:"
ALERT_PREFIX = "alert:"

# Default TTLs (in seconds)
VESSEL_POSITION_TTL = 300  # 5 minutes
VESSEL_STATIC_TTL = 3600  # 1 hour
ZONE_TTL = 1800  # 30 minutes


class RedisClient:
    """Redis client with connection pooling for caching operations."""

    def __init__(self, redis_url: str):
        """Initialize Redis client.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to Redis with connection pooling."""
        if self._is_connected:
            return

        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()
            self._is_connected = True
            logger.info("Redis client connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        self._is_connected = False
        logger.info("Redis client disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def health_check(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if healthy, False otherwise
        """
        if not self._client:
            return False

        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    # ==================== Vessel Position Caching ====================

    async def set_vessel_position(
        self,
        mmsi: int,
        latitude: float,
        longitude: float,
        speed: Optional[float] = None,
        course: Optional[float] = None,
        heading: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        ttl: int = VESSEL_POSITION_TTL,
    ) -> bool:
        """Cache vessel position data.

        Args:
            mmsi: Vessel MMSI
            latitude: Latitude
            longitude: Longitude
            speed: Speed over ground (knots)
            course: Course over ground (degrees)
            heading: True heading (degrees)
            timestamp: Position timestamp
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._client:
            return False

        key = f"{VESSEL_POSITION_PREFIX}{mmsi}"
        data = {
            "mmsi": mmsi,
            "latitude": latitude,
            "longitude": longitude,
            "speed": speed,
            "course": course,
            "heading": heading,
            "timestamp": timestamp.isoformat() if timestamp else datetime.utcnow().isoformat(),
            "cached_at": datetime.utcnow().isoformat(),
        }

        try:
            await self._client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to cache vessel position {mmsi}: {e}")
            return False

    async def get_vessel_position(self, mmsi: int) -> Optional[dict[str, Any]]:
        """Get cached vessel position.

        Args:
            mmsi: Vessel MMSI

        Returns:
            Position data dict or None if not cached
        """
        if not self._client:
            return None

        key = f"{VESSEL_POSITION_PREFIX}{mmsi}"

        try:
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached vessel position {mmsi}: {e}")
            return None

    async def get_all_vessel_positions(self) -> list[dict[str, Any]]:
        """Get all cached vessel positions.

        Returns:
            List of position data dicts
        """
        if not self._client:
            return []

        try:
            keys = []
            async for key in self._client.scan_iter(f"{VESSEL_POSITION_PREFIX}*"):
                keys.append(key)

            if not keys:
                return []

            values = await self._client.mget(keys)
            positions = []
            for value in values:
                if value:
                    positions.append(json.loads(value))

            return positions

        except Exception as e:
            logger.error(f"Failed to get all cached vessel positions: {e}")
            return []

    async def delete_vessel_position(self, mmsi: int) -> bool:
        """Delete cached vessel position.

        Args:
            mmsi: Vessel MMSI

        Returns:
            True if deleted
        """
        if not self._client:
            return False

        key = f"{VESSEL_POSITION_PREFIX}{mmsi}"

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cached vessel position {mmsi}: {e}")
            return False

    # ==================== Vessel Static Data Caching ====================

    async def set_vessel_static(
        self,
        mmsi: int,
        data: dict[str, Any],
        ttl: int = VESSEL_STATIC_TTL,
    ) -> bool:
        """Cache vessel static data.

        Args:
            mmsi: Vessel MMSI
            data: Static data dictionary
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._client:
            return False

        key = f"{VESSEL_STATIC_PREFIX}{mmsi}"
        data["cached_at"] = datetime.utcnow().isoformat()

        try:
            await self._client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to cache vessel static data {mmsi}: {e}")
            return False

    async def get_vessel_static(self, mmsi: int) -> Optional[dict[str, Any]]:
        """Get cached vessel static data.

        Args:
            mmsi: Vessel MMSI

        Returns:
            Static data dict or None if not cached
        """
        if not self._client:
            return None

        key = f"{VESSEL_STATIC_PREFIX}{mmsi}"

        try:
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached vessel static data {mmsi}: {e}")
            return None

    # ==================== Batch Operations ====================

    async def set_vessel_positions_batch(
        self,
        positions: list[dict[str, Any]],
        ttl: int = VESSEL_POSITION_TTL,
    ) -> int:
        """Cache multiple vessel positions in a batch.

        Args:
            positions: List of position dicts with mmsi, latitude, longitude, etc.
            ttl: Time-to-live in seconds

        Returns:
            Number of positions cached
        """
        if not self._client or not positions:
            return 0

        try:
            pipe = self._client.pipeline()

            for pos in positions:
                mmsi = pos.get("mmsi")
                if not mmsi:
                    continue

                key = f"{VESSEL_POSITION_PREFIX}{mmsi}"
                pos["cached_at"] = datetime.utcnow().isoformat()
                pipe.setex(key, ttl, json.dumps(pos))

            await pipe.execute()
            return len(positions)

        except Exception as e:
            logger.error(f"Failed to batch cache vessel positions: {e}")
            return 0

    # ==================== Generic Cache Operations ====================

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a cache value.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Optional TTL in seconds

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            data = json.dumps(value) if not isinstance(value, str) else value

            if ttl:
                await self._client.setex(key, ttl, data)
            else:
                await self._client.set(key, data)

            return True
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._client:
            return None

        try:
            data = await self._client.get(key)
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data
            return None
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a cache key.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self._client:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """Get Redis statistics.

        Returns:
            Dictionary with Redis stats
        """
        if not self._client:
            return {"status": "disconnected"}

        try:
            info = await self._client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def init_redis_client() -> RedisClient:
    """Initialize the global Redis client.

    Returns:
        Initialized RedisClient instance
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient(settings.redis_url)
        await _redis_client.connect()

    return _redis_client


async def close_redis_client() -> None:
    """Close the global Redis client."""
    global _redis_client

    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


def get_redis_client() -> Optional[RedisClient]:
    """Get the global Redis client instance.

    Returns:
        RedisClient instance or None if not initialized
    """
    return _redis_client

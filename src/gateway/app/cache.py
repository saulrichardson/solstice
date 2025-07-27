import hashlib
import json
import logging
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

# Local
from .config import settings

logger = logging.getLogger("gateway.cache")


class Cache:
    """Simple cache for LLM responses."""

    def __init__(self):
        self.enabled = bool(settings.redis_url)
        self.ttl = settings.cache_ttl
        self._client = None

    async def connect(self):
        """Initialize Redis connection."""
        if not self.enabled:
            return

        try:
            self._client = await redis.from_url(
                settings.redis_url, decode_responses=True
            )
            await self._client.ping()
            logger.info("Cache connected successfully")
        except (RedisError, Exception) as e:
            logger.warning(f"Cache connection failed: {e}. Running without cache.")
            self.enabled = False

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    def _generate_key(self, cache_data: dict) -> str:
        """Generate cache key from request parameters."""
        # Create a stable hash from the request
        key_str = json.dumps(cache_data, sort_keys=True)
        return f"llm:cache:{hashlib.sha256(key_str.encode()).hexdigest()}"

    async def get_response(self, cache_data: dict) -> Optional[dict]:
        """Get cached response."""
        if not self.enabled or not self._client:
            return None

        key = self._generate_key(cache_data)

        try:
            data = await self._client.get(key)
            if data:
                logger.info(f"Cache hit for key: {key[:16]}...")
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def set_response(self, cache_data: dict, response: dict):
        """Cache a response."""
        if not self.enabled or not self._client:
            return

        key = self._generate_key(cache_data)

        try:
            await self._client.setex(key, self.ttl, json.dumps(response))
            logger.info(f"Cached response for key: {key[:16]}...")
        except (RedisError, Exception) as e:
            logger.warning(f"Cache set error: {e}")


# Global cache instance
cache = Cache()

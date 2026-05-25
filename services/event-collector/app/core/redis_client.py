"""Redis client for caching and rate limiting"""

import json
from typing import Any, Set
import importlib
import structlog

# Dynamically import redis.asyncio to avoid static import resolution issues in editors/linters.
# At runtime this will try to load `redis.asyncio` (redis-py >= 4) and fall back to `aioredis` (older package) if needed.
_aioredis_mod = None
try:
    _redis_mod = importlib.import_module("redis")
    _aioredis_mod = getattr(_redis_mod, "asyncio", None)
except Exception:
    # Fallback to older aioredis package if available, otherwise leave as None
    try:
        _aioredis_mod = importlib.import_module("aioredis")
    except Exception:
        _aioredis_mod = None

aioredis = _aioredis_mod  # type: ignore

from app.core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client wrapper"""
    
    def __init__(self):
        self.redis: Any = None
        self.is_connected = False
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
            # Test connection
            await self.redis.ping()
            self.is_connected = True
            logger.info("redis_connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.is_connected = False
            logger.info("redis_disconnected")
    
    async def get(self, key: str) -> str | None:
        """Get value by key"""
        if not self.redis:
            return None
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """
        Set key-value pair
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
        """
        if not self.redis:
            return False
        return await self.redis.set(key, value, ex=ex)
    
    async def incr(self, key: str) -> int:
        """Increment key value"""
        if not self.redis:
            return 0
        return await self.redis.incr(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        if not self.redis:
            return False
        return await self.redis.expire(key, seconds)
    
    async def delete(self, key: str) -> int:
        """Delete key"""
        if not self.redis:
            return 0
        return await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0
    
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration"""
        if not self.redis:
            return False
        return await self.redis.setex(key, seconds, value)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self.redis:
            return -1
        return await self.redis.ttl(key)
    
    async def lpush(self, key: str, *values: str) -> int:
        """Push values to list (left)"""
        if not self.redis:
            return 0
        return await self.redis.lpush(key, *values)
    
    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        """Get range from list"""
        if not self.redis:
            return []
        return await self.redis.lrange(key, start, end)
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list to specified range"""
        if not self.redis:
            return False
        return await self.redis.ltrim(key, start, end)
    
    async def sadd(self, key: str, *values: str) -> int:
        """Add members to set"""
        if not self.redis:
            return 0
        return await self.redis.sadd(key, *values)
    
    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set"""
        if not self.redis:
            return set()
        return await self.redis.smembers(key)
    
    async def cache_json(self, key: str, data: Any, ex: int = 3600) -> bool:
        """Cache JSON data"""
        try:
            json_str = json.dumps(data)
            return await self.set(key, json_str, ex=ex)
        except Exception as e:
            logger.error("cache_json_failed", key=key, error=str(e))
            return False
    
    async def get_json(self, key: str) -> Any | None:
        """Get cached JSON data"""
        try:
            json_str = await self.get(key)
            if json_str:
                return json.loads(json_str)
            return None
        except Exception as e:
            logger.error("get_json_failed", key=key, error=str(e))
            return None
    
    async def incrby(self, key: str, amount: int) -> int:
        """Increment key value by amount"""
        if not self.redis:
            return 0
        return await self.redis.incrby(key, amount)

    async def rate_limit_check(self, identifier: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Check rate limit for identifier.

        Uses an atomic Lua script so the INCR and EXPIRE are a single operation —
        avoids the race where two concurrent first-requests both see count==1 and
        only one of them sets the expiry, leaving the key immortal.

        Args:
            identifier: Unique identifier (e.g., IP, user_id)
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        if not self.redis:
            return True, limit

        key = f"rate_limit:{identifier}"

        # Atomic: increment and set TTL only on the very first call within the window
        _LUA_INCR_EXPIRE = """
            local count = redis.call('INCR', KEYS[1])
            if count == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
            end
            return count
        """

        try:
            count = await self.redis.eval(_LUA_INCR_EXPIRE, 1, key, window)
            is_allowed = count <= limit
            remaining = max(0, limit - count)
            return is_allowed, remaining

        except Exception as e:
            logger.error("rate_limit_check_failed", error=str(e))
            # Fail open - allow request on error
            return True, limit


# Global Redis client instance
redis_client = RedisClient()

"""
Distributed Cache Manager for Production
Supports Redis for distributed caching with in-memory fallback
"""
import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv('config/.env')
logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not available, using in-memory cache only")


class CacheManager:
    """Production-level cache manager with Redis support and in-memory fallback."""

    def __init__(self):
        self.redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.default_ttl = 300  # 5 minutes

        # Try to connect to Redis if enabled
        if self.redis_enabled and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD') or None,
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory cache.")
                self.redis_client = None
        else:
            logger.info("📦 Using in-memory cache (Redis disabled or unavailable)")

    def _get_key(self, namespace: str, key: str) -> str:
        """Generate cache key with namespace."""
        return f"{namespace}:{key}"

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._get_key(namespace, key)

        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(cache_key)
                if value:
                    logger.info(f"💾 Redis cache HIT: {cache_key[:50]}...")
                    return json.loads(value)
            except Exception as e:
                logger.error(f"❌ Redis GET error: {e}")

        # Fallback to in-memory cache
        if cache_key in self.memory_cache:
            cached_data, expiry = self.memory_cache[cache_key]
            if datetime.now() < expiry:
                logger.info(f"💾 Memory cache HIT: {cache_key[:50]}...")
                return cached_data
            else:
                # Expired
                del self.memory_cache[cache_key]
                logger.info(f"⏰ Memory cache EXPIRED: {cache_key[:50]}...")

        logger.info(f"❌ Cache MISS: {cache_key[:50]}...")
        return None

    def set(self, namespace: str, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        cache_key = self._get_key(namespace, key)
        ttl = ttl or self.default_ttl

        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(value)
                )
                logger.info(f"✅ Redis cache SET: {cache_key[:50]}... (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.error(f"❌ Redis SET error: {e}")

        # Fallback to in-memory cache
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.memory_cache[cache_key] = (value, expiry)

        # Limit in-memory cache size (LRU)
        if len(self.memory_cache) > 1000:
            oldest_key = min(self.memory_cache.keys(),
                           key=lambda k: self.memory_cache[k][1])
            del self.memory_cache[oldest_key]
            logger.info(f"🧹 Memory cache cleaned (removed oldest entry)")

        logger.info(f"✅ Memory cache SET: {cache_key[:50]}... (TTL: {ttl}s)")
        return True

    def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache."""
        cache_key = self._get_key(namespace, key)

        # Delete from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception as e:
                logger.error(f"❌ Redis DELETE error: {e}")

        # Delete from in-memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

        logger.info(f"🗑️ Cache deleted: {cache_key[:50]}...")
        return True

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        count = 0

        # Clear from Redis
        if self.redis_client:
            try:
                pattern = f"{namespace}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
                logger.info(f"🧹 Redis cleared {count} keys from {namespace}")
            except Exception as e:
                logger.error(f"❌ Redis CLEAR error: {e}")

        # Clear from in-memory cache
        prefix = f"{namespace}:"
        keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self.memory_cache[key]
            count += 1

        logger.info(f"🧹 Cleared {count} keys from namespace: {namespace}")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_enabled": self.redis_client is not None,
            "memory_cache_size": len(self.memory_cache),
            "default_ttl": self.default_ttl
        }

        if self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats["redis_stats"] = {
                    "total_connections": info.get('total_connections_received', 0),
                    "total_commands": info.get('total_commands_processed', 0),
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0)
                }
            except Exception as e:
                logger.error(f"❌ Redis stats error: {e}")

        return stats

    def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        health = {
            "status": "healthy",
            "redis_available": False,
            "memory_cache_available": True
        }

        if self.redis_client:
            try:
                self.redis_client.ping()
                health["redis_available"] = True
            except Exception as e:
                health["status"] = "degraded"
                health["redis_error"] = str(e)
                logger.warning(f"⚠️ Redis health check failed: {e}")

        return health


# Global cache instance (shared across requests in same container)
_cache_instance = None

def get_cache() -> CacheManager:
    """Get singleton cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance

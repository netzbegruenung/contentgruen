"""
Simple in-memory cache for frequently accessed data.
"""

import time
import logging
from typing import Any, Optional, Dict
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with expiration."""

    value: Any
    expires_at: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expires_at

    def increment_hits(self):
        """Increment the hit counter for this entry."""
        self.hit_count += 1


class CacheManager:
    """
    Thread-safe in-memory cache with TTL support.
    """

    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize cache manager.

        Args:
            default_ttl_seconds: Default time-to-live for cache entries (5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl_seconds
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                logger.debug(f"Cache entry expired for key: {key}")
                return None

            entry.increment_hits()
            self._stats["hits"] += 1
            logger.debug(f"Cache hit for key: {key} (hits: {entry.hit_count})")
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl

        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if the key was deleted, False if it didn't exist
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache entry for key: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats["evictions"] += count
            logger.info(f"Cleared {count} cache entries")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats["evictions"] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests * 100 if total_requests > 0 else 0
            )

            return {
                "entries": len(self._cache),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.

        Args:
            pattern: Pattern to match (simple string prefix matching)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            matching_keys = [
                key for key in self._cache.keys() if key.startswith(pattern)
            ]

            for key in matching_keys:
                del self._cache[key]
                self._stats["evictions"] += 1

            if matching_keys:
                logger.debug(
                    f"Invalidated {len(matching_keys)} cache entries matching pattern: {pattern}"
                )

            return len(matching_keys)


# Global cache instance for trending content
_trending_cache = CacheManager(default_ttl_seconds=300)  # 5 minute TTL


def get_trending_cache() -> CacheManager:
    """Get the global trending content cache instance."""
    return _trending_cache

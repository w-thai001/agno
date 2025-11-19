"""
Cache manager for API responses.

Implements LRU (Least Recently Used) caching with TTL (Time To Live)
to reduce redundant API calls and improve performance.
"""

import hashlib
import json
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

from agno.utils.log import logger

from .models import CacheConfig, HTTPMethod


class CacheEntry:
    """Represents a single cache entry with TTL."""

    def __init__(self, value: Any, ttl: int):
        """
        Initialize cache entry.

        Args:
            value: The cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> Any:
        """Access the cached value and update metrics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value

    def get_age(self) -> float:
        """Get the age of the cache entry in seconds."""
        return time.time() - self.created_at


class CacheManager:
    """
    LRU cache manager with TTL support for API responses.

    Features:
    - LRU eviction policy when cache is full
    - TTL-based expiration
    - Thread-safe operations
    - Cache hit/miss metrics
    - Selective caching based on HTTP method
    """

    def __init__(self, config: CacheConfig):
        """
        Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        logger.debug(
            f"CacheManager initialized: enabled={config.enabled}, "
            f"ttl={config.ttl}s, max_size={config.max_size}"
        )

    def _generate_cache_key(
        self,
        endpoint_name: str,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        body: Optional[Any] = None,
    ) -> str:
        """
        Generate a unique cache key for the request.

        Args:
            endpoint_name: Endpoint name
            method: HTTP method
            url: Request URL
            headers: Request headers (optional)
            params: Query parameters (optional)
            body: Request body (optional)

        Returns:
            SHA256 hash as cache key
        """
        # Create a deterministic representation
        key_parts = {
            "endpoint": endpoint_name,
            "method": method,
            "url": url,
            "params": params or {},
            "body": body,
        }

        # Include specific headers that affect response (exclude auth, user-agent, etc.)
        if headers:
            cache_affecting_headers = {
                k: v
                for k, v in headers.items()
                if k.lower() in ["accept", "accept-language", "accept-encoding", "content-type"]
            }
            if cache_affecting_headers:
                key_parts["headers"] = cache_affecting_headers

        # Generate hash
        key_string = json.dumps(key_parts, sort_keys=True, default=str)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self,
        endpoint_name: str,
        method: HTTPMethod,
        url: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        body: Optional[Any] = None,
    ) -> Optional[Any]:
        """
        Get a cached response if available and not expired.

        Args:
            endpoint_name: Endpoint name
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: Query parameters
            body: Request body

        Returns:
            Cached response or None if not found/expired
        """
        if not self.config.enabled:
            return None

        # Check if this method should be cached
        if method not in self.config.cache_methods:
            logger.debug(f"CacheManager: Method {method} not cacheable")
            return None

        cache_key = self._generate_cache_key(endpoint_name, method.value, url, headers, params, body)

        with self.lock:
            if cache_key in self.cache:
                entry = self.cache[cache_key]

                if entry.is_expired():
                    logger.debug(f"CacheManager: Cache entry expired for {endpoint_name}")
                    del self.cache[cache_key]
                    self.misses += 1
                    return None

                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                self.hits += 1

                logger.debug(
                    f"CacheManager: Cache HIT for {endpoint_name}, "
                    f"age={entry.get_age():.1f}s, access_count={entry.access_count + 1}"
                )
                return entry.access()

            self.misses += 1
            logger.debug(f"CacheManager: Cache MISS for {endpoint_name}")
            return None

    def put(
        self,
        endpoint_name: str,
        method: HTTPMethod,
        url: str,
        response: Any,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        body: Optional[Any] = None,
        ttl: Optional[int] = None,
    ):
        """
        Cache a response.

        Args:
            endpoint_name: Endpoint name
            method: HTTP method
            url: Request URL
            response: Response to cache
            headers: Request headers
            params: Query parameters
            body: Request body
            ttl: Custom TTL (uses config default if not provided)
        """
        if not self.config.enabled:
            return

        # Check if this method should be cached
        if method not in self.config.cache_methods:
            return

        cache_key = self._generate_cache_key(endpoint_name, method.value, url, headers, params, body)
        cache_ttl = ttl if ttl is not None else self.config.ttl

        with self.lock:
            # Check if we need to evict entries
            if len(self.cache) >= self.config.max_size and cache_key not in self.cache:
                # Remove oldest entry (first item)
                evicted_key = next(iter(self.cache))
                del self.cache[evicted_key]
                self.evictions += 1
                logger.debug(f"CacheManager: Evicted oldest entry, total evictions={self.evictions}")

            self.cache[cache_key] = CacheEntry(response, cache_ttl)
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)

            logger.debug(
                f"CacheManager: Cached response for {endpoint_name}, "
                f"ttl={cache_ttl}s, cache_size={len(self.cache)}"
            )

    def invalidate(
        self,
        endpoint_name: Optional[str] = None,
        method: Optional[HTTPMethod] = None,
        url: Optional[str] = None,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        body: Optional[Any] = None,
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            endpoint_name: Endpoint name (invalidate all if None)
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: Query parameters
            body: Request body

        Returns:
            Number of entries invalidated
        """
        with self.lock:
            if all(
                x is None for x in [endpoint_name, method, url, headers, params, body]
            ):
                # Clear entire cache
                count = len(self.cache)
                self.cache.clear()
                logger.info(f"CacheManager: Cleared entire cache, {count} entries removed")
                return count

            # Invalidate specific entry
            if endpoint_name and method and url:
                cache_key = self._generate_cache_key(
                    endpoint_name, method.value, url, headers, params, body
                )
                if cache_key in self.cache:
                    del self.cache[cache_key]
                    logger.info(f"CacheManager: Invalidated cache for {endpoint_name}")
                    return 1

            return 0

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"CacheManager: Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

    def get_metrics(self) -> dict:
        """Get cache metrics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "enabled": self.config.enabled,
                "size": len(self.cache),
                "max_size": self.config.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": hit_rate,
                "evictions": self.evictions,
                "utilization_percent": (len(self.cache) / self.config.max_size * 100)
                if self.config.max_size > 0
                else 0,
            }

    def reset_metrics(self):
        """Reset hit/miss/eviction counters."""
        with self.lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            logger.info("CacheManager: Metrics reset")

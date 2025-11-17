"""
Intelligent caching system with TTL, LRU eviction, and cache invalidation.

Features:
- LRU (Least Recently Used) eviction when max_size reached
- TTL (Time To Live) expiration with automatic cleanup
- Pattern-based invalidation (e.g., "user:*")
- Namespace support for multi-tenant caching
- Thread-safe operations
- Memory-efficient storage with size limits
- Cache statistics tracking (hit rate, miss rate, evictions)
"""

import json
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Pattern, Tuple


class CacheManagerFSA:
    """Intelligent cache manager with LRU eviction, TTL, and pattern-based invalidation."""

    def __init__(
        self,
        max_size: int = 1000,
        max_bytes: Optional[int] = None,
        default_ttl: Optional[float] = None,
        namespace: str = "default",
    ):
        """
        Initialize the cache manager.

        Args:
            max_size: Maximum number of cache entries (default: 1000)
            max_bytes: Maximum cache size in bytes (default: None, unlimited)
            default_ttl: Default TTL in seconds for cache entries (default: None, no expiration)
            namespace: Namespace for cache isolation (default: "default")
        """
        self.max_size = max_size
        self.max_bytes = max_bytes
        self.default_ttl = default_ttl
        self.namespace = namespace

        # Cache storage: {key: (value, expiry_timestamp, access_count, size_bytes)}
        self._cache: OrderedDict[str, Tuple[Any, Optional[float], int, int]] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_size_bytes = 0

        # Thread safety
        self._lock = threading.RLock()

        # Background cleanup thread
        self._cleanup_interval = 60  # seconds
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()

    def _start_cleanup_thread(self):
        """Start background thread for TTL cleanup."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
            self._cleanup_thread.start()

    def _cleanup_expired(self):
        """Background task to remove expired cache entries."""
        while not self._stop_cleanup.is_set():
            self._stop_cleanup.wait(self._cleanup_interval)
            if not self._stop_cleanup.is_set():
                self._remove_expired_entries()

    def _remove_expired_entries(self):
        """Remove all expired cache entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, (_, expiry, _, _) in self._cache.items():
                if expiry is not None and current_time > expiry:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_entry(key)

    def _remove_entry(self, key: str):
        """Remove a cache entry and update size tracking."""
        if key in self._cache:
            _, _, _, size_bytes = self._cache[key]
            del self._cache[key]
            self._total_size_bytes -= size_bytes

    def _get_entry_size(self, value: Any) -> int:
        """Estimate size of cache entry in bytes."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value) if isinstance(value, bytes) else len(value.encode("utf-8"))
            elif isinstance(value, (int, float, bool)):
                return 8
            else:
                # Serialize to JSON for size estimation
                return len(json.dumps(value, default=str).encode("utf-8"))
        except Exception:
            return 100  # Default estimate for unknown types

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            # OrderedDict maintains insertion order; move_to_end() manages LRU
            key, (_, _, _, size_bytes) = self._cache.popitem(last=False)
            self._total_size_bytes -= size_bytes
            self._evictions += 1

    def _ensure_capacity(self, new_entry_size: int):
        """Ensure cache has capacity for new entry."""
        # Remove expired entries first
        self._remove_expired_entries()

        # Evict LRU entries if needed
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        # Evict based on memory limit
        if self.max_bytes is not None:
            while (
                self._cache
                and self._total_size_bytes + new_entry_size > self.max_bytes
            ):
                self._evict_lru()

    def cache_get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve cached value.

        Args:
            key: Cache key
            default: Default value if key not found or expired

        Returns:
            Cached value or default
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            value, expiry, access_count, size_bytes = self._cache[key]

            # Check if expired
            if expiry is not None and time.time() > expiry:
                self._remove_entry(key)
                self._misses += 1
                return default

            # Update access tracking (LRU)
            self._cache.move_to_end(key)
            self._cache[key] = (value, expiry, access_count + 1, size_bytes)
            self._hits += 1

            return value

    def cache_set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Store value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: use default_ttl)
        """
        with self._lock:
            # Calculate expiry timestamp
            if ttl is not None:
                expiry = time.time() + ttl
            elif self.default_ttl is not None:
                expiry = time.time() + self.default_ttl
            else:
                expiry = None

            # Calculate entry size
            entry_size = self._get_entry_size(value)

            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)

            # Ensure capacity
            self._ensure_capacity(entry_size)

            # Add new entry
            self._cache[key] = (value, expiry, 0, entry_size)
            self._total_size_bytes += entry_size

            # Start cleanup thread if TTL is used
            if expiry is not None and self._cleanup_thread is None:
                self._start_cleanup_thread()

    def cache_delete(self, key: str) -> bool:
        """
        Remove specific cache entry.

        Args:
            key: Cache key to remove

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def cache_clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear all cache or pattern-matched entries.

        Args:
            pattern: Optional glob-style pattern (e.g., "user:*", "*:session")

        Returns:
            Number of entries cleared
        """
        with self._lock:
            if pattern is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._total_size_bytes = 0
                return count

            # Pattern-based clearing
            regex_pattern = self._glob_to_regex(pattern)
            keys_to_delete = [key for key in self._cache.keys() if regex_pattern.match(key)]

            for key in keys_to_delete:
                self._remove_entry(key)

            return len(keys_to_delete)

    def cache_exists(self, key: str) -> bool:
        """
        Check if key exists and is valid (not expired).

        Args:
            key: Cache key to check

        Returns:
            True if key exists and is valid, False otherwise
        """
        with self._lock:
            if key not in self._cache:
                return False

            _, expiry, _, _ = self._cache[key]

            # Check if expired
            if expiry is not None and time.time() > expiry:
                self._remove_entry(key)
                return False

            return True

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit_rate, miss_rate, evictions, size, total_size_bytes
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            miss_rate = self._misses / total_requests if total_requests > 0 else 0.0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "miss_rate": miss_rate,
                "evictions": self._evictions,
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_size_bytes": self._total_size_bytes,
                "max_bytes": self.max_bytes,
                "namespace": self.namespace,
            }

    def warm_cache(self, data: Dict[str, Any], ttl: Optional[float] = None) -> int:
        """
        Warm cache with multiple entries.

        Args:
            data: Dictionary of key-value pairs to cache
            ttl: Optional TTL for all entries

        Returns:
            Number of entries cached
        """
        count = 0
        for key, value in data.items():
            self.cache_set(key, value, ttl=ttl)
            count += 1
        return count

    def reset_stats(self):
        """Reset cache statistics."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def shutdown(self):
        """Stop background cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread is not None:
            self._cleanup_thread.join(timeout=2)

    @staticmethod
    def _glob_to_regex(pattern: str) -> Pattern:
        """Convert glob pattern to regex pattern."""
        # Escape special regex characters except * and ?
        pattern = re.escape(pattern)
        # Replace escaped glob wildcards with regex equivalents
        pattern = pattern.replace(r"\*", ".*").replace(r"\?", ".")
        return re.compile(f"^{pattern}$")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.shutdown()
        except Exception:
            pass

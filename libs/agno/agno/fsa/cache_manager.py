"""
Cache Manager FSA (Functional Specification Agent)

A high-velocity, credit-conscious cache management component for the Core Infrastructure track.
Implements LRU eviction, TTL expiration, and size management with automatic cleanup.

Author: Agno Core Team
Track: Core Infrastructure
"""

from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from threading import Lock, Thread
import time
import logging
from enum import Enum


logger = logging.getLogger(__name__)


class EvictionReason(Enum):
    """Reasons for cache entry eviction"""
    TTL_EXPIRED = "ttl_expired"
    SIZE_LIMIT = "size_limit"
    MANUAL_DELETE = "manual_delete"
    CACHE_CLEAR = "cache_clear"


@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    ttl_seconds: Optional[int] = None
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL"""
        if self.ttl_seconds is None:
            return False
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary"""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "age_seconds": self.age_seconds,
            "is_expired": self.is_expired,
        }


@dataclass
class EvictionRecord:
    """Record of a cache eviction event"""
    key: str
    reason: EvictionReason
    timestamp: datetime
    entry_age_seconds: float
    access_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert eviction record to dictionary"""
        return {
            "key": self.key,
            "reason": self.reason.value,
            "timestamp": self.timestamp.isoformat(),
            "entry_age_seconds": self.entry_age_seconds,
            "access_count": self.access_count,
        }


@dataclass
class CacheStats:
    """Cache statistics and metrics"""
    total_entries: int = 0
    max_cache_size: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_evictions: int = 0
    total_sets: int = 0
    total_deletes: int = 0
    cache_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate

    @property
    def utilization_rate(self) -> float:
        """Calculate cache utilization rate"""
        if self.max_cache_size == 0:
            return 0.0
        return self.total_entries / self.max_cache_size

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "total_entries": self.total_entries,
            "max_cache_size": self.max_cache_size,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "total_evictions": self.total_evictions,
            "total_sets": self.total_sets,
            "total_deletes": self.total_deletes,
            "cache_size_bytes": self.cache_size_bytes,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "utilization_rate": self.utilization_rate,
        }


@dataclass
class EvictionReport:
    """Report of cache eviction activity"""
    total_evictions: int = 0
    evictions_by_reason: Dict[str, int] = field(default_factory=dict)
    recent_evictions: List[EvictionRecord] = field(default_factory=list)
    max_recent_evictions: int = 100

    def record_eviction(self, record: EvictionRecord):
        """Record an eviction event"""
        self.total_evictions += 1
        reason_key = record.reason.value
        self.evictions_by_reason[reason_key] = self.evictions_by_reason.get(reason_key, 0) + 1

        # Keep only recent evictions
        self.recent_evictions.append(record)
        if len(self.recent_evictions) > self.max_recent_evictions:
            self.recent_evictions.pop(0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "total_evictions": self.total_evictions,
            "evictions_by_reason": self.evictions_by_reason,
            "recent_evictions": [r.to_dict() for r in self.recent_evictions[-10:]],  # Last 10
        }


class CacheManagerFSA:
    """
    Cache Manager FSA - Functional Specification Agent

    High-velocity in-memory cache with LRU eviction, TTL expiration, and size management.
    Designed for credit-conscious operations with minimal overhead.

    Features:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) expiration
    - Maximum size management
    - Thread-safe operations
    - Automatic cleanup
    - Comprehensive statistics and eviction reporting

    Inputs:
    - cache_key: Unique identifier for cached data
    - cache_value: Data to cache
    - ttl_seconds: Time-to-live in seconds (optional)
    - max_cache_size: Maximum number of entries

    Outputs:
    - cached_data: Retrieved cached data
    - cache_stats: Performance metrics and statistics
    - eviction_report: Detailed eviction activity report
    """

    def __init__(
        self,
        max_cache_size: int = 1000,
        default_ttl_seconds: Optional[int] = None,
        cleanup_interval_seconds: int = 60,
        enable_auto_cleanup: bool = True,
    ):
        """
        Initialize Cache Manager FSA

        Args:
            max_cache_size: Maximum number of cache entries (default: 1000)
            default_ttl_seconds: Default TTL for entries without explicit TTL (default: None)
            cleanup_interval_seconds: Interval for automatic cleanup thread (default: 60)
            enable_auto_cleanup: Enable automatic background cleanup (default: True)
        """
        self.max_cache_size = max_cache_size
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.enable_auto_cleanup = enable_auto_cleanup

        # Core cache storage (OrderedDict for LRU)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

        # Statistics and reporting
        self.stats = CacheStats(max_cache_size=max_cache_size)
        self.eviction_report = EvictionReport()

        # Cleanup thread
        self._cleanup_thread: Optional[Thread] = None
        self._cleanup_running = False

        if self.enable_auto_cleanup:
            self._start_cleanup_thread()

        logger.info(
            f"CacheManagerFSA initialized: max_size={max_cache_size}, "
            f"default_ttl={default_ttl_seconds}, cleanup_interval={cleanup_interval_seconds}"
        )

    def set(
        self,
        cache_key: str,
        cache_value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set a value in the cache

        Args:
            cache_key: Unique key for the cache entry
            cache_value: Value to cache
            ttl_seconds: Time-to-live in seconds (uses default if not specified)

        Returns:
            bool: True if successfully set
        """
        with self._lock:
            # Use default TTL if not specified
            if ttl_seconds is None:
                ttl_seconds = self.default_ttl_seconds

            # Check if we need to evict for size limit
            if cache_key not in self._cache and len(self._cache) >= self.max_cache_size:
                self._evict_lru()

            # Create or update entry
            now = datetime.now()
            entry = CacheEntry(
                key=cache_key,
                value=cache_value,
                created_at=now,
                accessed_at=now,
                ttl_seconds=ttl_seconds,
            )

            # Move to end (most recently used)
            if cache_key in self._cache:
                del self._cache[cache_key]

            self._cache[cache_key] = entry
            self.stats.total_entries = len(self._cache)
            self.stats.total_sets += 1

            logger.debug(f"Cache set: key={cache_key}, ttl={ttl_seconds}")
            return True

    def get(self, cache_key: str) -> Tuple[Optional[Any], bool]:
        """
        Get a value from the cache

        Args:
            cache_key: Key to retrieve

        Returns:
            Tuple[Optional[Any], bool]: (value, hit) where hit indicates cache hit/miss
        """
        with self._lock:
            entry = self._cache.get(cache_key)

            # Cache miss
            if entry is None:
                self.stats.total_misses += 1
                logger.debug(f"Cache miss: key={cache_key}")
                return None, False

            # Check if expired
            if entry.is_expired:
                self._evict_entry(
                    cache_key,
                    EvictionReason.TTL_EXPIRED,
                    remove_from_cache=True,
                )
                self.stats.total_misses += 1
                logger.debug(f"Cache miss (expired): key={cache_key}")
                return None, False

            # Cache hit - update access metadata and move to end (LRU)
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self._cache.move_to_end(cache_key)

            self.stats.total_hits += 1
            logger.debug(f"Cache hit: key={cache_key}")
            return entry.value, True

    def delete(self, cache_key: str) -> bool:
        """
        Delete a specific cache entry

        Args:
            cache_key: Key to delete

        Returns:
            bool: True if entry existed and was deleted
        """
        with self._lock:
            if cache_key in self._cache:
                self._evict_entry(
                    cache_key,
                    EvictionReason.MANUAL_DELETE,
                    remove_from_cache=True,
                )
                self.stats.total_deletes += 1
                logger.debug(f"Cache delete: key={cache_key}")
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cache entries

        Returns:
            int: Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)

            # Record evictions
            for key in list(self._cache.keys()):
                self._evict_entry(
                    key,
                    EvictionReason.CACHE_CLEAR,
                    remove_from_cache=False,
                )

            self._cache.clear()
            self.stats.total_entries = 0
            logger.info(f"Cache cleared: {count} entries removed")
            return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict[str, Any]: Cache statistics
        """
        with self._lock:
            self.stats.total_entries = len(self._cache)
            return self.stats.to_dict()

    def get_eviction_report(self) -> Dict[str, Any]:
        """
        Get eviction report

        Returns:
            Dict[str, Any]: Eviction report
        """
        with self._lock:
            return self.eviction_report.to_dict()

    def get_entry_info(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a cache entry

        Args:
            cache_key: Key to inspect

        Returns:
            Optional[Dict[str, Any]]: Entry information or None if not found
        """
        with self._lock:
            entry = self._cache.get(cache_key)
            if entry is None:
                return None
            return entry.to_dict()

    def cleanup_expired(self) -> int:
        """
        Manually trigger cleanup of expired entries

        Returns:
            int: Number of entries cleaned up
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in expired_keys:
                self._evict_entry(
                    key,
                    EvictionReason.TTL_EXPIRED,
                    remove_from_cache=True,
                )

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

    def _evict_lru(self) -> None:
        """Evict the least recently used entry (internal)"""
        if not self._cache:
            return

        # First item in OrderedDict is least recently used
        lru_key = next(iter(self._cache))
        self._evict_entry(lru_key, EvictionReason.SIZE_LIMIT, remove_from_cache=True)
        logger.debug(f"LRU eviction: key={lru_key}")

    def _evict_entry(
        self,
        cache_key: str,
        reason: EvictionReason,
        remove_from_cache: bool = True,
    ) -> None:
        """
        Evict a specific entry and record the eviction (internal)

        Args:
            cache_key: Key to evict
            reason: Reason for eviction
            remove_from_cache: Whether to remove from cache dict
        """
        entry = self._cache.get(cache_key)
        if entry is None:
            return

        # Record eviction
        record = EvictionRecord(
            key=cache_key,
            reason=reason,
            timestamp=datetime.now(),
            entry_age_seconds=entry.age_seconds,
            access_count=entry.access_count,
        )
        self.eviction_report.record_eviction(record)
        self.stats.total_evictions += 1

        # Remove from cache
        if remove_from_cache:
            del self._cache[cache_key]
            self.stats.total_entries = len(self._cache)

    def _cleanup_worker(self) -> None:
        """Background worker for automatic cleanup"""
        logger.info("Cleanup worker started")

        while self._cleanup_running:
            time.sleep(self.cleanup_interval_seconds)

            if not self._cleanup_running:
                break

            try:
                expired_count = self.cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"Auto cleanup: removed {expired_count} expired entries")
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")

        logger.info("Cleanup worker stopped")

    def _start_cleanup_thread(self) -> None:
        """Start the automatic cleanup thread"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return

        self._cleanup_running = True
        self._cleanup_thread = Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Automatic cleanup thread started")

    def _stop_cleanup_thread(self) -> None:
        """Stop the automatic cleanup thread"""
        if self._cleanup_thread is None:
            return

        self._cleanup_running = False
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Automatic cleanup thread stopped")

    def shutdown(self) -> None:
        """Shutdown the cache manager and cleanup resources"""
        logger.info("Shutting down CacheManagerFSA")
        self._stop_cleanup_thread()
        with self._lock:
            self._cache.clear()
            self.stats.total_entries = 0

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()

    def __len__(self) -> int:
        """Get number of entries in cache"""
        with self._lock:
            return len(self._cache)

    def __contains__(self, cache_key: str) -> bool:
        """Check if key exists in cache (without affecting LRU)"""
        with self._lock:
            entry = self._cache.get(cache_key)
            if entry is None:
                return False
            return not entry.is_expired

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"CacheManagerFSA(entries={len(self._cache)}, "
            f"max_size={self.max_cache_size}, "
            f"hit_rate={self.stats.hit_rate:.2%})"
        )


# Example usage and demonstration
def example_basic_operations():
    """Example: Basic get/set/delete operations"""
    print("\n=== Example 1: Basic Operations ===")

    cache = CacheManagerFSA(max_cache_size=5, enable_auto_cleanup=False)

    # Set values
    cache.set("user:1001", {"name": "Alice", "role": "admin"}, ttl_seconds=300)
    cache.set("user:1002", {"name": "Bob", "role": "user"}, ttl_seconds=300)
    cache.set("config:api_key", "sk-abc123xyz", ttl_seconds=3600)

    # Get values
    value, hit = cache.get("user:1001")
    print(f"Get user:1001: {value}, hit={hit}")

    # Delete
    deleted = cache.delete("user:1002")
    print(f"Deleted user:1002: {deleted}")

    # Stats
    stats = cache.get_stats()
    print(f"Stats: {stats}")

    cache.shutdown()


def example_lru_eviction():
    """Example: LRU eviction with size limit"""
    print("\n=== Example 2: LRU Eviction ===")

    cache = CacheManagerFSA(max_cache_size=3, enable_auto_cleanup=False)

    # Fill cache to capacity
    for i in range(5):
        cache.set(f"key:{i}", f"value:{i}")
        print(f"Set key:{i}, cache size: {len(cache)}")

    # Check eviction report
    report = cache.get_eviction_report()
    print(f"Evictions: {report}")

    cache.shutdown()


def example_ttl_expiration():
    """Example: TTL expiration and automatic cleanup"""
    print("\n=== Example 3: TTL Expiration ===")

    cache = CacheManagerFSA(
        max_cache_size=100,
        default_ttl_seconds=2,
        cleanup_interval_seconds=1,
        enable_auto_cleanup=True,
    )

    # Set entries with short TTL
    cache.set("temp:session", "session_data", ttl_seconds=1)
    cache.set("temp:token", "token_data", ttl_seconds=3)

    # Immediate get
    value, hit = cache.get("temp:session")
    print(f"Immediate get: {value}, hit={hit}")

    # Wait for expiration
    print("Waiting 2 seconds for expiration...")
    time.sleep(2)

    # Try to get expired entry
    value, hit = cache.get("temp:session")
    print(f"After expiration: {value}, hit={hit}")

    # Manual cleanup
    expired_count = cache.cleanup_expired()
    print(f"Manually cleaned up {expired_count} entries")

    cache.shutdown()


def example_comprehensive_stats():
    """Example: Comprehensive statistics and reporting"""
    print("\n=== Example 4: Statistics and Reporting ===")

    cache = CacheManagerFSA(max_cache_size=10, enable_auto_cleanup=False)

    # Perform various operations
    cache.set("key:1", "value:1")
    cache.set("key:2", "value:2")
    cache.set("key:3", "value:3", ttl_seconds=1)

    cache.get("key:1")
    cache.get("key:1")  # Hit
    cache.get("key:999")  # Miss

    time.sleep(1.5)
    cache.get("key:3")  # Expired miss

    cache.delete("key:2")

    # Get detailed stats
    stats = cache.get_stats()
    print(f"Cache Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Get eviction report
    report = cache.get_eviction_report()
    print(f"\nEviction Report:")
    for key, value in report.items():
        print(f"  {key}: {value}")

    # Get entry info
    entry_info = cache.get_entry_info("key:1")
    print(f"\nEntry Info for key:1:")
    for key, value in entry_info.items():
        print(f"  {key}: {value}")

    cache.shutdown()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 70)
    print("Cache Manager FSA - Functional Specification Agent")
    print("Core Infrastructure Track - High Velocity Implementation")
    print("=" * 70)

    # Run examples
    example_basic_operations()
    example_lru_eviction()
    example_ttl_expiration()
    example_comprehensive_stats()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)

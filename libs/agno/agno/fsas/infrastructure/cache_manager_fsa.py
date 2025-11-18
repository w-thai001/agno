"""
Comprehensive Cache Manager FSA with multi-level caching, advanced eviction policies,
and invalidation strategies.

This module provides a production-ready caching solution with:
- Multi-level cache support (L1 memory, L2 disk, L3 distributed)
- Multiple eviction policies: LRU, LFU, FIFO, TTL-based, adaptive
- Cache warming and preloading capabilities
- Cache statistics and performance monitoring
- Thread-safe operations with concurrent access handling
- Serialization/deserialization for complex objects
- Cache invalidation patterns (tag-based, pattern-based, dependency-based)
- Write-through and write-back strategies
- Cache compression for large objects
- Bloom filter for negative cache optimization
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import pickle
import re
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from agno.utils.log import logger


class CacheOperation(Enum):
    """Supported cache operations."""

    GET = "get"
    SET = "set"
    DELETE = "delete"
    INVALIDATE_TAG = "invalidate_tag"
    INVALIDATE_PATTERN = "invalidate_pattern"
    WARM = "warm"
    CLEAR = "clear"
    OPTIMIZE = "optimize"


class WriteStrategy(Enum):
    """Cache write strategies."""

    WRITE_THROUGH = "write_through"  # Write to all levels immediately
    WRITE_BACK = "write_back"  # Write to L1 first, propagate later


@dataclass
class CacheEntry:
    """Wrapper for cached items with metadata."""

    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # Time to live in seconds
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)
    size: int = 0  # Size in bytes
    compressed: bool = False
    level: int = 1  # Cache level (1, 2, or 3)

    def __post_init__(self):
        """Calculate size after initialization."""
        if self.size == 0:
            self.size = self._calculate_size()

    def _calculate_size(self) -> int:
        """Calculate the size of the cached value."""
        try:
            return len(pickle.dumps(self.value))
        except Exception:
            return len(str(self.value).encode())

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def access(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "access_count": self.access_count,
            "last_access": self.last_access,
            "tags": list(self.tags),
            "size": self.size,
            "compressed": self.compressed,
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        data["tags"] = set(data.get("tags", []))
        return cls(**data)


@dataclass
class CacheStatistics:
    """Metrics collection for cache performance."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    invalidations: int = 0
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    promotions: int = 0
    compressions: int = 0
    decompressions: int = 0
    errors: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    total_size: int = 0  # Total size in bytes
    start_time: float = field(default_factory=time.time)

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate()

    def avg_access_time(self) -> float:
        """Calculate average access time."""
        # This would need timing data, simplified for now
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "promotions": self.promotions,
            "compressions": self.compressions,
            "decompressions": self.decompressions,
            "hit_rate": self.hit_rate(),
            "miss_rate": self.miss_rate(),
            "total_size": self.total_size,
            "uptime": time.time() - self.start_time,
            "errors": dict(self.errors),
        }


class EvictionPolicy(ABC):
    """Abstract base class for eviction policies."""

    @abstractmethod
    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select a cache entry to evict."""
        pass

    @abstractmethod
    def on_access(self, entry: CacheEntry) -> None:
        """Called when an entry is accessed."""
        pass

    @abstractmethod
    def on_insert(self, entry: CacheEntry) -> None:
        """Called when an entry is inserted."""
        pass


class LRUPolicy(EvictionPolicy):
    """Least Recently Used eviction policy."""

    def __init__(self):
        self.access_order: OrderedDict[str, float] = OrderedDict()

    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select least recently used entry."""
        if not self.access_order:
            return None
        # Return the first (oldest) key
        return next(iter(self.access_order))

    def on_access(self, entry: CacheEntry) -> None:
        """Update access order."""
        # Move to end (most recent)
        self.access_order.pop(entry.key, None)
        self.access_order[entry.key] = entry.last_access

    def on_insert(self, entry: CacheEntry) -> None:
        """Add to access order."""
        self.access_order[entry.key] = entry.timestamp


class LFUPolicy(EvictionPolicy):
    """Least Frequently Used eviction policy."""

    def __init__(self):
        self.frequency: Dict[str, int] = {}

    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select least frequently used entry."""
        if not self.frequency:
            return None
        return min(self.frequency, key=self.frequency.get)

    def on_access(self, entry: CacheEntry) -> None:
        """Update frequency count."""
        self.frequency[entry.key] = entry.access_count

    def on_insert(self, entry: CacheEntry) -> None:
        """Initialize frequency count."""
        self.frequency[entry.key] = 0


class FIFOPolicy(EvictionPolicy):
    """First In First Out eviction policy."""

    def __init__(self):
        self.insertion_order: OrderedDict[str, float] = OrderedDict()

    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select oldest entry."""
        if not self.insertion_order:
            return None
        return next(iter(self.insertion_order))

    def on_access(self, entry: CacheEntry) -> None:
        """No-op for FIFO."""
        pass

    def on_insert(self, entry: CacheEntry) -> None:
        """Track insertion order."""
        self.insertion_order[entry.key] = entry.timestamp


class TTLPolicy(EvictionPolicy):
    """Time To Live based eviction policy."""

    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Select expired entry or oldest entry."""
        # First, look for expired entries
        for key, entry in entries.items():
            if entry.is_expired():
                return key
        # If no expired entries, select oldest
        if not entries:
            return None
        return min(entries.keys(), key=lambda k: entries[k].timestamp)

    def on_access(self, entry: CacheEntry) -> None:
        """No-op for TTL."""
        pass

    def on_insert(self, entry: CacheEntry) -> None:
        """No-op for TTL."""
        pass


class AdaptivePolicy(EvictionPolicy):
    """Adaptive eviction policy that combines LRU and LFU."""

    def __init__(self):
        self.lru = LRUPolicy()
        self.lfu = LFUPolicy()
        self.use_lru_ratio = 0.5  # Starts at 50/50, adapts based on hit rate

    def select_victim(self, entries: Dict[str, CacheEntry]) -> Optional[str]:
        """Adaptively select victim based on recent performance."""
        import random

        if random.random() < self.use_lru_ratio:
            return self.lru.select_victim(entries)
        else:
            return self.lfu.select_victim(entries)

    def on_access(self, entry: CacheEntry) -> None:
        """Update both policies."""
        self.lru.on_access(entry)
        self.lfu.on_access(entry)

    def on_insert(self, entry: CacheEntry) -> None:
        """Update both policies."""
        self.lru.on_insert(entry)
        self.lfu.on_insert(entry)

    def adapt(self, hit_rate: float) -> None:
        """Adapt the policy mix based on hit rate."""
        # If hit rate is low, favor LFU more
        if hit_rate < 0.5:
            self.use_lru_ratio = max(0.2, self.use_lru_ratio - 0.1)
        else:
            self.use_lru_ratio = min(0.8, self.use_lru_ratio + 0.1)


class BloomFilter:
    """Simple bloom filter for negative cache optimization."""

    def __init__(self, size: int = 10000, num_hashes: int = 3):
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array = [False] * size

    def _hash(self, key: str, seed: int) -> int:
        """Generate hash for the key."""
        h = hashlib.md5(f"{key}{seed}".encode()).hexdigest()
        return int(h, 16) % self.size

    def add(self, key: str) -> None:
        """Add key to bloom filter."""
        for i in range(self.num_hashes):
            idx = self._hash(key, i)
            self.bit_array[idx] = True

    def might_contain(self, key: str) -> bool:
        """Check if key might be in the set."""
        for i in range(self.num_hashes):
            idx = self._hash(key, i)
            if not self.bit_array[idx]:
                return False
        return True

    def clear(self) -> None:
        """Clear the bloom filter."""
        self.bit_array = [False] * self.size


class CacheLevel(ABC):
    """Abstract base class for cache levels."""

    def __init__(
        self,
        max_size: int,
        eviction_policy: Optional[EvictionPolicy] = None,
        compression_threshold: int = 1024,
    ):
        self.max_size = max_size
        self.eviction_policy = eviction_policy or LRUPolicy()
        self.compression_threshold = compression_threshold
        self.entries: Dict[str, CacheEntry] = {}
        self.current_size = 0
        self.lock = threading.RLock()

    @abstractmethod
    def _store(self, entry: CacheEntry) -> None:
        """Store entry in the cache level."""
        pass

    @abstractmethod
    def _retrieve(self, key: str) -> Optional[CacheEntry]:
        """Retrieve entry from the cache level."""
        pass

    @abstractmethod
    def _remove(self, key: str) -> None:
        """Remove entry from the cache level."""
        pass

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self.lock:
            entry = self._retrieve(key)
            if entry and not entry.is_expired():
                entry.access()
                self.eviction_policy.on_access(entry)
                return entry
            elif entry and entry.is_expired():
                # Remove expired entry
                self._remove(key)
            return None

    def set(self, entry: CacheEntry) -> None:
        """Set entry in cache."""
        with self.lock:
            # Check if we need to evict
            while self.current_size + entry.size > self.max_size and self.entries:
                self._evict_one()

            # Compress if needed
            if entry.size > self.compression_threshold:
                entry = self._compress_entry(entry)

            self._store(entry)
            self.eviction_policy.on_insert(entry)

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self.lock:
            if key in self.entries:
                self._remove(key)
                return True
            return False

    def _evict_one(self) -> None:
        """Evict one entry based on eviction policy."""
        victim_key = self.eviction_policy.select_victim(self.entries)
        if victim_key:
            self._remove(victim_key)

    def _compress_entry(self, entry: CacheEntry) -> CacheEntry:
        """Compress entry value."""
        try:
            compressed_value = gzip.compress(pickle.dumps(entry.value))
            entry.value = compressed_value
            entry.compressed = True
            entry.size = len(compressed_value)
        except Exception as e:
            logger.warning(f"Failed to compress entry {entry.key}: {e}")
        return entry

    def _decompress_entry(self, entry: CacheEntry) -> CacheEntry:
        """Decompress entry value."""
        if entry.compressed:
            try:
                entry.value = pickle.loads(gzip.decompress(entry.value))
                entry.compressed = False
            except Exception as e:
                logger.error(f"Failed to decompress entry {entry.key}: {e}")
        return entry

    def clear(self) -> None:
        """Clear all entries."""
        with self.lock:
            for key in list(self.entries.keys()):
                self._remove(key)


class L1MemoryCache(CacheLevel):
    """L1 in-memory cache level."""

    def _store(self, entry: CacheEntry) -> None:
        """Store in memory."""
        if entry.key in self.entries:
            self.current_size -= self.entries[entry.key].size
        self.entries[entry.key] = entry
        self.current_size += entry.size

    def _retrieve(self, key: str) -> Optional[CacheEntry]:
        """Retrieve from memory."""
        entry = self.entries.get(key)
        if entry:
            entry = self._decompress_entry(entry)
        return entry

    def _remove(self, key: str) -> None:
        """Remove from memory."""
        if key in self.entries:
            self.current_size -= self.entries[key].size
            del self.entries[key]


class L2DiskCache(CacheLevel):
    """L2 disk-based cache level."""

    def __init__(
        self,
        max_size: int,
        eviction_policy: Optional[EvictionPolicy] = None,
        compression_threshold: int = 1024,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(max_size, eviction_policy, compression_threshold)
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "agno_l2_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_file_path(self, key: str) -> str:
        """Get file path for cache key."""
        # Hash the key to create a valid filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")

    def _store(self, entry: CacheEntry) -> None:
        """Store on disk."""
        try:
            file_path = self._get_file_path(entry.key)
            with open(file_path, "wb") as f:
                pickle.dump(entry, f)

            if entry.key in self.entries:
                self.current_size -= self.entries[entry.key].size
            self.entries[entry.key] = entry
            self.current_size += entry.size
        except Exception as e:
            logger.error(f"Failed to store entry {entry.key} to disk: {e}")
            raise

    def _retrieve(self, key: str) -> Optional[CacheEntry]:
        """Retrieve from disk."""
        try:
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    entry = pickle.load(f)
                entry = self._decompress_entry(entry)
                return entry
        except Exception as e:
            logger.error(f"Failed to retrieve entry {key} from disk: {e}")
        return None

    def _remove(self, key: str) -> None:
        """Remove from disk."""
        try:
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
            if key in self.entries:
                self.current_size -= self.entries[key].size
                del self.entries[key]
        except Exception as e:
            logger.error(f"Failed to remove entry {key} from disk: {e}")

    def clear(self) -> None:
        """Clear all disk cache."""
        super().clear()
        # Also clean up the directory
        try:
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to clear disk cache: {e}")


class L3DistributedCache(CacheLevel):
    """L3 distributed cache level (mock implementation for demonstration)."""

    def __init__(
        self,
        max_size: int,
        eviction_policy: Optional[EvictionPolicy] = None,
        compression_threshold: int = 1024,
        nodes: Optional[List[str]] = None,
    ):
        super().__init__(max_size, eviction_policy, compression_threshold)
        self.nodes = nodes or ["localhost:6379"]
        # In a real implementation, this would connect to Redis, Memcached, etc.
        # For now, we'll use in-memory as a mock
        self._mock_storage: Dict[str, CacheEntry] = {}

    def _store(self, entry: CacheEntry) -> None:
        """Store in distributed cache."""
        try:
            # Mock distributed storage
            if entry.key in self._mock_storage:
                self.current_size -= self._mock_storage[entry.key].size
            self._mock_storage[entry.key] = entry
            self.entries[entry.key] = entry
            self.current_size += entry.size
        except Exception as e:
            logger.error(f"Failed to store entry {entry.key} in distributed cache: {e}")
            raise

    def _retrieve(self, key: str) -> Optional[CacheEntry]:
        """Retrieve from distributed cache."""
        try:
            entry = self._mock_storage.get(key)
            if entry:
                entry = self._decompress_entry(entry)
            return entry
        except Exception as e:
            logger.error(f"Failed to retrieve entry {key} from distributed cache: {e}")
        return None

    def _remove(self, key: str) -> None:
        """Remove from distributed cache."""
        try:
            if key in self._mock_storage:
                self.current_size -= self._mock_storage[key].size
                del self._mock_storage[key]
            if key in self.entries:
                del self.entries[key]
        except Exception as e:
            logger.error(f"Failed to remove entry {key} from distributed cache: {e}")


class CacheInvalidator:
    """Handles cache invalidation strategies."""

    def __init__(self):
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> set of keys
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # key -> dependent keys
        self.lock = threading.RLock()

    def index_entry(self, entry: CacheEntry) -> None:
        """Index an entry by its tags."""
        with self.lock:
            for tag in entry.tags:
                self.tag_index[tag].add(entry.key)

    def remove_entry(self, key: str, tags: Set[str]) -> None:
        """Remove an entry from the index."""
        with self.lock:
            for tag in tags:
                self.tag_index[tag].discard(key)

    def invalidate_by_tag(self, tag: str) -> Set[str]:
        """Get all keys with the given tag."""
        with self.lock:
            return self.tag_index.get(tag, set()).copy()

    def invalidate_by_pattern(self, pattern: str) -> Set[str]:
        """Get all keys matching the pattern."""
        with self.lock:
            regex = re.compile(pattern)
            matching_keys = set()
            # Check all indexed keys
            for tag_keys in self.tag_index.values():
                for key in tag_keys:
                    if regex.search(key):
                        matching_keys.add(key)
            return matching_keys

    def add_dependency(self, key: str, depends_on: str) -> None:
        """Add a dependency relationship."""
        with self.lock:
            self.dependency_graph[depends_on].add(key)

    def invalidate_dependents(self, key: str) -> Set[str]:
        """Get all keys that depend on the given key."""
        with self.lock:
            return self.dependency_graph.get(key, set()).copy()

    def clear(self) -> None:
        """Clear all indexes."""
        with self.lock:
            self.tag_index.clear()
            self.dependency_graph.clear()


class CacheManagerFSA:
    """
    Comprehensive Cache Manager with Finite State Automaton architecture.

    Provides multi-level caching with advanced eviction policies, invalidation strategies,
    and comprehensive monitoring.
    """

    def __init__(
        self,
        l1_size: int = 1024 * 1024 * 100,  # 100 MB
        l2_size: int = 1024 * 1024 * 1024,  # 1 GB
        l3_size: int = 1024 * 1024 * 1024 * 10,  # 10 GB
        eviction_policy: str = "lru",
        write_strategy: WriteStrategy = WriteStrategy.WRITE_THROUGH,
        enable_l2: bool = True,
        enable_l3: bool = False,
        compression_threshold: int = 1024,
        enable_bloom_filter: bool = True,
        l2_cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Cache Manager.

        Args:
            l1_size: Maximum size for L1 cache in bytes
            l2_size: Maximum size for L2 cache in bytes
            l3_size: Maximum size for L3 cache in bytes
            eviction_policy: Eviction policy to use (lru, lfu, fifo, ttl, adaptive)
            write_strategy: Write strategy (write_through or write_back)
            enable_l2: Enable L2 disk cache
            enable_l3: Enable L3 distributed cache
            compression_threshold: Minimum size in bytes to trigger compression
            enable_bloom_filter: Enable bloom filter for negative cache
            l2_cache_dir: Directory for L2 cache files
        """
        # Initialize eviction policies
        self.eviction_policy_type = eviction_policy
        self.write_strategy = write_strategy

        # Create cache levels
        self.l1 = L1MemoryCache(
            max_size=l1_size,
            eviction_policy=self._create_eviction_policy(eviction_policy),
            compression_threshold=compression_threshold,
        )

        self.l2: Optional[L2DiskCache] = None
        if enable_l2:
            self.l2 = L2DiskCache(
                max_size=l2_size,
                eviction_policy=self._create_eviction_policy(eviction_policy),
                compression_threshold=compression_threshold,
                cache_dir=l2_cache_dir,
            )

        self.l3: Optional[L3DistributedCache] = None
        if enable_l3:
            self.l3 = L3DistributedCache(
                max_size=l3_size,
                eviction_policy=self._create_eviction_policy(eviction_policy),
                compression_threshold=compression_threshold,
            )

        # Initialize components
        self.statistics = CacheStatistics()
        self.invalidator = CacheInvalidator()
        self.bloom_filter = BloomFilter() if enable_bloom_filter else None
        self.lock = threading.RLock()

        logger.info(
            f"CacheManagerFSA initialized with L1={l1_size}, L2={l2_size if enable_l2 else 'disabled'}, "
            f"L3={l3_size if enable_l3 else 'disabled'}, policy={eviction_policy}"
        )

    def _create_eviction_policy(self, policy_name: str) -> EvictionPolicy:
        """Create an eviction policy instance."""
        policies = {
            "lru": LRUPolicy,
            "lfu": LFUPolicy,
            "fifo": FIFOPolicy,
            "ttl": TTLPolicy,
            "adaptive": AdaptivePolicy,
        }
        policy_class = policies.get(policy_name.lower(), LRUPolicy)
        return policy_class()

    def execute(
        self,
        operation: CacheOperation,
        key: Optional[str] = None,
        value: Any = None,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
        level: int = 1,
        default: Any = None,
        promote: bool = True,
        pattern: Optional[str] = None,
        tag: Optional[str] = None,
        loader: Optional[Callable] = None,
    ) -> Any:
        """
        Execute a cache operation.

        Args:
            operation: The operation to execute
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for the cache entry
            level: Cache level to operate on
            default: Default value for GET operations
            promote: Whether to promote entries to upper levels
            pattern: Pattern for pattern-based invalidation
            tag: Tag for tag-based invalidation
            loader: Loader function for cache warming

        Returns:
            Result of the operation
        """
        try:
            if operation == CacheOperation.GET:
                return self.get(key, default=default, promote=promote)
            elif operation == CacheOperation.SET:
                return self.set(key, value, ttl=ttl, tags=tags, level=level)
            elif operation == CacheOperation.DELETE:
                return self.delete(key, cascade=True)
            elif operation == CacheOperation.INVALIDATE_TAG:
                return self.invalidate_by_tag(tag)
            elif operation == CacheOperation.INVALIDATE_PATTERN:
                return self.invalidate_by_pattern(pattern)
            elif operation == CacheOperation.WARM:
                return self.warm_cache(loader)
            elif operation == CacheOperation.CLEAR:
                return self.clear()
            elif operation == CacheOperation.OPTIMIZE:
                return self.optimize_eviction()
            else:
                raise ValueError(f"Unknown operation: {operation}")
        except Exception as e:
            self.error_handling(operation, e)
            raise

    def get(self, key: str, default: Any = None, promote: bool = True) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if not found
            promote: Promote to upper cache levels

        Returns:
            Cached value or default
        """
        with self.lock:
            # Check bloom filter first (negative cache)
            if self.bloom_filter and not self.bloom_filter.might_contain(key):
                self.statistics.misses += 1
                logger.debug(f"Cache miss (bloom filter): {key}")
                return default

            # Try L1 first
            entry = self.l1.get(key)
            if entry:
                self.statistics.hits += 1
                self.statistics.l1_hits += 1
                logger.debug(f"Cache hit (L1): {key}")
                return entry.value

            # Try L2
            if self.l2:
                entry = self.l2.get(key)
                if entry:
                    self.statistics.hits += 1
                    self.statistics.l2_hits += 1
                    logger.debug(f"Cache hit (L2): {key}")
                    if promote:
                        self.promote_to_upper_level(key, entry, from_level=2)
                    return entry.value

            # Try L3
            if self.l3:
                entry = self.l3.get(key)
                if entry:
                    self.statistics.hits += 1
                    self.statistics.l3_hits += 1
                    logger.debug(f"Cache hit (L3): {key}")
                    if promote:
                        self.promote_to_upper_level(key, entry, from_level=3)
                    return entry.value

            # Cache miss
            self.statistics.misses += 1
            logger.debug(f"Cache miss: {key}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        tags: Optional[Set[str]] = None,
        level: int = 1,
    ) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for the entry
            level: Target cache level
        """
        with self.lock:
            try:
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl=ttl,
                    tags=tags or set(),
                    level=level,
                )

                # Add to bloom filter
                if self.bloom_filter:
                    self.bloom_filter.add(key)

                # Index by tags
                self.invalidator.index_entry(entry)

                # Store based on write strategy
                if self.write_strategy == WriteStrategy.WRITE_THROUGH:
                    # Write to all levels
                    self.l1.set(entry)
                    if self.l2 and level >= 2:
                        self.l2.set(entry)
                    if self.l3 and level >= 3:
                        self.l3.set(entry)
                else:
                    # Write to L1 first, propagate later
                    self.l1.set(entry)

                self.statistics.sets += 1
                self.statistics.total_size += entry.size
                logger.debug(f"Cache set: {key} (size={entry.size}, ttl={ttl})")

            except Exception as e:
                logger.error(f"Failed to set cache entry {key}: {e}")
                self.statistics.errors["set"] += 1
                raise

    def delete(self, key: str, cascade: bool = True) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key
            cascade: Delete from all levels

        Returns:
            True if deleted, False otherwise
        """
        with self.lock:
            deleted = False

            # Get entry to remove from index
            entry = self.l1.get(key)
            if entry:
                self.invalidator.remove_entry(key, entry.tags)

            # Delete from all levels
            if self.l1.delete(key):
                deleted = True
            if cascade and self.l2 and self.l2.delete(key):
                deleted = True
            if cascade and self.l3 and self.l3.delete(key):
                deleted = True

            if deleted:
                self.statistics.deletes += 1
                logger.debug(f"Cache delete: {key}")

            return deleted

    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with the given tag.

        Args:
            tag: Tag to invalidate

        Returns:
            Number of entries invalidated
        """
        with self.lock:
            keys = self.invalidator.invalidate_by_tag(tag)
            count = 0
            for key in keys:
                if self.delete(key, cascade=True):
                    count += 1
            self.statistics.invalidations += count
            logger.info(f"Invalidated {count} entries by tag: {tag}")
            return count

    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching the pattern.

        Args:
            pattern: Regex pattern to match keys

        Returns:
            Number of entries invalidated
        """
        with self.lock:
            keys = self.invalidator.invalidate_by_pattern(pattern)
            count = 0
            for key in keys:
                if self.delete(key, cascade=True):
                    count += 1
            self.statistics.invalidations += count
            logger.info(f"Invalidated {count} entries by pattern: {pattern}")
            return count

    def warm_cache(self, keys_or_loader: Union[List[str], Callable]) -> int:
        """
        Warm the cache with preloaded data.

        Args:
            keys_or_loader: List of keys or a loader function

        Returns:
            Number of entries warmed
        """
        count = 0
        try:
            if callable(keys_or_loader):
                # Loader function should return dict of key -> value
                data = keys_or_loader()
                for key, value in data.items():
                    self.set(key, value)
                    count += 1
            else:
                # List of keys - no-op without values
                logger.warning("Cache warming with keys only requires a loader function")

            logger.info(f"Warmed cache with {count} entries")
            return count
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            self.statistics.errors["warm"] += 1
            return count

    def promote_to_upper_level(self, key: str, entry: CacheEntry, from_level: int) -> None:
        """
        Promote a cache entry to upper levels.

        Args:
            key: Cache key
            entry: Cache entry to promote
            from_level: Source cache level
        """
        try:
            if from_level >= 2:
                self.l1.set(entry)
                self.statistics.promotions += 1
                logger.debug(f"Promoted {key} from L{from_level} to L1")
        except Exception as e:
            logger.error(f"Failed to promote entry {key}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of statistics
        """
        with self.lock:
            stats = self.statistics.to_dict()
            stats["l1_size"] = self.l1.current_size
            stats["l1_entries"] = len(self.l1.entries)
            if self.l2:
                stats["l2_size"] = self.l2.current_size
                stats["l2_entries"] = len(self.l2.entries)
            if self.l3:
                stats["l3_size"] = self.l3.current_size
                stats["l3_entries"] = len(self.l3.entries)
            return stats

    def validate(self) -> bool:
        """
        Validate cache consistency.

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for expired entries
            expired_keys = []
            for key, entry in self.l1.entries.items():
                if entry.is_expired():
                    expired_keys.append(key)

            # Clean up expired entries
            for key in expired_keys:
                self.delete(key, cascade=True)

            logger.info(f"Cache validation: removed {len(expired_keys)} expired entries")
            return True
        except Exception as e:
            logger.error(f"Cache validation failed: {e}")
            return False

    def error_handling(self, operation: CacheOperation, error: Exception) -> None:
        """
        Handle cache errors.

        Args:
            operation: The operation that failed
            error: The error that occurred
        """
        error_type = type(error).__name__
        self.statistics.errors[f"{operation.value}_{error_type}"] += 1
        logger.error(f"Cache error during {operation.value}: {error_type} - {error}")

    def optimize_eviction(self) -> None:
        """Optimize eviction policies based on current performance."""
        if self.eviction_policy_type == "adaptive":
            hit_rate = self.statistics.hit_rate()
            if isinstance(self.l1.eviction_policy, AdaptivePolicy):
                self.l1.eviction_policy.adapt(hit_rate)
            if self.l2 and isinstance(self.l2.eviction_policy, AdaptivePolicy):
                self.l2.eviction_policy.adapt(hit_rate)
            if self.l3 and isinstance(self.l3.eviction_policy, AdaptivePolicy):
                self.l3.eviction_policy.adapt(hit_rate)
            logger.info(f"Optimized eviction policies (hit_rate={hit_rate:.2f})")

    def clear(self) -> None:
        """Clear all cache levels."""
        with self.lock:
            self.l1.clear()
            if self.l2:
                self.l2.clear()
            if self.l3:
                self.l3.clear()
            if self.bloom_filter:
                self.bloom_filter.clear()
            self.invalidator.clear()
            logger.info("Cleared all cache levels")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.validate()
        return False

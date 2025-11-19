"""Cache Manager FSA with TTL and eviction policies."""
from collections import OrderedDict
from enum import Enum
from time import time
from typing import Any, Optional


class CacheState(Enum):
    """FSA States for cache management."""
    EMPTY, ACTIVE, FULL, EVICTING = "empty", "active", "full", "evicting"


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU, LFU, FIFO = "lru", "lfu", "fifo"


class CacheManager:
    """Finite State Automaton for cache management with TTL and eviction."""

    def __init__(self, max_size: int = 100, ttl: Optional[float] = None, policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size = max_size
        self.ttl = ttl
        self.policy = policy
        self.cache: OrderedDict = OrderedDict()
        self.access_count: dict = {}
        self.timestamps: dict = {}
        self.state = CacheState.EMPTY

    def _update_state(self) -> None:
        """Transition between states based on cache size."""
        size = len(self.cache)
        self.state = CacheState.EMPTY if size == 0 else (CacheState.FULL if size >= self.max_size else CacheState.ACTIVE)

    def _is_expired(self, key: str) -> bool:
        """Check if a cache entry has expired."""
        return self.ttl is not None and time() - self.timestamps.get(key, 0) > self.ttl

    def _evict(self) -> None:
        """Evict entry based on policy."""
        self.state = CacheState.EVICTING
        if self.policy in (EvictionPolicy.LRU, EvictionPolicy.FIFO):
            self.cache.popitem(last=False)
        elif self.policy == EvictionPolicy.LFU:
            key = min(self.access_count, key=self.access_count.get)
            del self.cache[key], self.access_count[key], self.timestamps[key]
        self._update_state()

    def set(self, key: str, value: Any) -> None:
        """Set cache entry."""
        if self.state == CacheState.FULL and key not in self.cache:
            self._evict()
        self.cache[key] = value
        self.cache.move_to_end(key)
        self.access_count[key] = self.access_count.get(key, 0) + 1
        self.timestamps[key] = time()
        self._update_state()

    def get(self, key: str) -> Optional[Any]:
        """Get cache entry."""
        if key not in self.cache or self._is_expired(key):
            return None
        self.cache.move_to_end(key)
        self.access_count[key] = self.access_count.get(key, 0) + 1
        return self.cache[key]

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        if key in self.cache:
            del self.cache[key], self.access_count[key], self.timestamps[key]
            self._update_state()
            return True
        return False

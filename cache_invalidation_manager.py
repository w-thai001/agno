"""Cache Invalidation Manager FSA - Multi-strategy cache invalidation with dependency tracking."""

from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any, Callable, Dict, List, Optional, Pattern, Set
import re


class CacheState(Enum):
    """FSA States for cache entries."""
    VALID = "valid"
    STALE = "stale"
    INVALIDATED = "invalidated"
    PURGED = "purged"


class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    MANUAL = "manual"


@dataclass
class CacheEntry:
    """Cache entry with FSA state tracking."""
    key: str
    value: Any
    state: CacheState = CacheState.VALID
    created_at: float = field(default_factory=time)
    accessed_at: float = field(default_factory=time)
    access_count: int = 0
    ttl: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)

    def transition(self, new_state: CacheState) -> None:
        """FSA state transition."""
        self.state = new_state

    def is_expired(self) -> bool:
        """Check TTL expiration."""
        return self.ttl is not None and (time() - self.created_at) > self.ttl

    def access(self) -> None:
        """Update access metrics."""
        self.accessed_at = time()
        self.access_count += 1


class CacheInvalidationManager:
    """FSA-based cache invalidation manager with multi-strategy support."""

    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # key -> dependents
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)

    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            dependencies: Optional[List[str]] = None) -> None:
        """Set cache entry with optional TTL and dependencies."""
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict(InvalidationStrategy.LRU)

        entry = CacheEntry(key, value, ttl=ttl or self.default_ttl)
        if dependencies:
            entry.dependencies = set(dependencies)
            for dep in dependencies:
                self.dependencies[dep].add(key)

        self.cache[key] = entry
        self.cache.move_to_end(key)
        self._emit_event("set", key, value)

    def get(self, key: str, strategy: InvalidationStrategy = InvalidationStrategy.TTL) -> Optional[Any]:
        """Get cache entry with strategy-based validation."""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # FSA state validation
        if entry.state in (CacheState.INVALIDATED, CacheState.PURGED):
            return None

        # TTL validation
        if entry.is_expired():
            self._transition_and_invalidate(entry, CacheState.STALE)
            return None

        # Update access patterns
        entry.access()
        self.cache.move_to_end(key)

        return entry.value if entry.state == CacheState.VALID else None

    def invalidate(self, key: str, cascade: bool = True) -> None:
        """Manually invalidate cache entry with optional dependency cascade."""
        if key not in self.cache:
            return

        entry = self.cache[key]
        self._transition_and_invalidate(entry, CacheState.INVALIDATED)

        # Cascade to dependents
        if cascade and key in self.dependencies:
            for dependent in list(self.dependencies[key]):
                self.invalidate(dependent, cascade=True)
            del self.dependencies[key]

    def invalidate_pattern(self, pattern: str) -> int:
        """Pattern-based bulk invalidation."""
        regex = re.compile(pattern)
        count = 0
        for key in list(self.cache.keys()):
            if regex.search(key):
                self.invalidate(key, cascade=False)
                count += 1
        return count

    def purge_invalidated(self) -> int:
        """Purge all invalidated/stale entries."""
        count = 0
        for key in list(self.cache.keys()):
            entry = self.cache[key]
            if entry.state in (CacheState.INVALIDATED, CacheState.STALE):
                entry.transition(CacheState.PURGED)
                del self.cache[key]
                count += 1
                self._emit_event("purge", key, None)
        return count

    def on(self, event: str, handler: Callable) -> None:
        """Register event handler for invalidation events."""
        self.event_handlers[event].append(handler)

    def _evict(self, strategy: InvalidationStrategy) -> None:
        """Evict entry based on strategy."""
        if not self.cache:
            return

        if strategy == InvalidationStrategy.LRU:
            key, entry = self.cache.popitem(last=False)
        elif strategy == InvalidationStrategy.LFU:
            key = min(self.cache.keys(), key=lambda k: self.cache[k].access_count)
            entry = self.cache.pop(key)
        else:
            return

        entry.transition(CacheState.PURGED)
        self._emit_event("evict", key, strategy.value)

    def _transition_and_invalidate(self, entry: CacheEntry, new_state: CacheState) -> None:
        """FSA state transition with event emission."""
        old_state = entry.state
        entry.transition(new_state)
        self._emit_event("invalidate", entry.key, {"from": old_state.value, "to": new_state.value})

    def _emit_event(self, event: str, key: str, data: Any) -> None:
        """Emit invalidation event to registered handlers."""
        for handler in self.event_handlers.get(event, []):
            handler(key, data)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        state_counts = defaultdict(int)
        for entry in self.cache.values():
            state_counts[entry.state.value] += 1

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "states": dict(state_counts),
            "dependencies": len(self.dependencies)
        }

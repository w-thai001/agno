"""
Fallback Strategies for Circuit Breaker FSA

This module provides multiple fallback strategies for handling requests
when the circuit breaker is OPEN or when primary requests fail.
"""

import asyncio
import pickle
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Optional, Tuple
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Base Classes
# ============================================================================


class FallbackStrategy(ABC):
    """
    Abstract base class for fallback strategies.

    Fallback strategies provide alternative responses when the primary
    service is unavailable or the circuit breaker is OPEN.
    """

    def __init__(self, name: str = "fallback_strategy"):
        """
        Initialize fallback strategy.

        Args:
            name: Name identifier for this strategy
        """
        self.name = name
        self._fallback_count = 0
        self._fallback_success_count = 0
        self._fallback_failure_count = 0

    @abstractmethod
    def execute(
        self,
        original_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute fallback logic.

        Args:
            original_func: The original function that failed
            *args: Positional arguments for original_func
            **kwargs: Keyword arguments for original_func

        Returns:
            Fallback result
        """
        pass

    async def execute_async(
        self,
        original_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute fallback logic asynchronously.

        Args:
            original_func: The original async function that failed
            *args: Positional arguments for original_func
            **kwargs: Keyword arguments for original_func

        Returns:
            Fallback result
        """
        # Default implementation wraps synchronous execute
        return self.execute(original_func, *args, **kwargs)

    def get_stats(self) -> Dict[str, int]:
        """Get fallback statistics."""
        return {
            "fallback_count": self._fallback_count,
            "fallback_success_count": self._fallback_success_count,
            "fallback_failure_count": self._fallback_failure_count,
        }

    def reset_stats(self) -> None:
        """Reset fallback statistics."""
        self._fallback_count = 0
        self._fallback_success_count = 0
        self._fallback_failure_count = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# ============================================================================
# Cache Fallback
# ============================================================================


@dataclass
class CacheEntry:
    """Entry in the fallback cache."""
    value: Any
    timestamp: datetime
    hit_count: int = 0
    is_stale: bool = False


class CacheFallback(FallbackStrategy):
    """
    Fallback that returns cached responses.

    Caches successful responses and returns them when primary service fails.
    Supports TTL (time-to-live) and cache size limits.

    Example:
        >>> cache = CacheFallback(
        ...     ttl_seconds=300.0,  # 5 minutes
        ...     max_cache_size=1000
        ... )
        >>> # Cache will store recent successful responses
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_cache_size: int = 1000,
        allow_stale: bool = True,
        stale_ttl_seconds: float = 3600.0,
        cache_key_func: Optional[Callable[..., str]] = None,
        name: str = "cache_fallback"
    ):
        """
        Initialize cache fallback.

        Args:
            ttl_seconds: Time-to-live for cache entries
            max_cache_size: Maximum number of cache entries
            allow_stale: Allow returning stale cache entries
            stale_ttl_seconds: TTL for stale entries
            cache_key_func: Function to generate cache keys from args/kwargs
            name: Strategy name
        """
        super().__init__(name)
        self.ttl = ttl_seconds
        self.max_cache_size = max_cache_size
        self.allow_stale = allow_stale
        self.stale_ttl = stale_ttl_seconds
        self.cache_key_func = cache_key_func or self._default_cache_key

        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.Lock()
        self._cache_hits = 0
        self._cache_misses = 0

        logger.debug(
            f"Initialized {self.name} with ttl={ttl_seconds}s, "
            f"max_size={max_cache_size}, allow_stale={allow_stale}"
        )

    def _default_cache_key(self, func: Callable, *args, **kwargs) -> str:
        """Generate cache key from function and arguments."""
        key_parts = [func.__name__]

        # Add args
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Use hash for complex objects
                try:
                    key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
                except Exception:
                    key_parts.append(type(arg).__name__)

        # Add kwargs
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
            else:
                try:
                    key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")
                except Exception:
                    key_parts.append(f"{k}={type(v).__name__}")

        return ":".join(key_parts)

    def store(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._cache_lock:
            # Enforce cache size limit
            if len(self._cache) >= self.max_cache_size:
                self._evict_oldest()

            self._cache[key] = CacheEntry(
                value=value,
                timestamp=datetime.now(),
                hit_count=0,
                is_stale=False
            )

            logger.debug(f"{self.name}: Cached value for key '{key}'")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._cache_lock:
            if key not in self._cache:
                self._cache_misses += 1
                return None

            entry = self._cache[key]
            age = (datetime.now() - entry.timestamp).total_seconds()

            # Check if fresh
            if age <= self.ttl:
                entry.hit_count += 1
                self._cache_hits += 1
                logger.debug(f"{self.name}: Cache hit for key '{key}' (age={age:.1f}s)")
                return entry.value

            # Check if stale but acceptable
            if self.allow_stale and age <= self.stale_ttl:
                entry.hit_count += 1
                entry.is_stale = True
                self._cache_hits += 1
                logger.debug(f"{self.name}: Stale cache hit for key '{key}' (age={age:.1f}s)")
                return entry.value

            # Expired
            del self._cache[key]
            self._cache_misses += 1
            logger.debug(f"{self.name}: Cache expired for key '{key}' (age={age:.1f}s)")
            return None

    def _evict_oldest(self) -> None:
        """Evict oldest cache entry (LRU)."""
        if not self._cache:
            return

        # Find entry with oldest timestamp
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]
        logger.debug(f"{self.name}: Evicted cache entry '{oldest_key}'")

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with cache fallback."""
        self._fallback_count += 1

        # Generate cache key
        cache_key = self.cache_key_func(original_func, *args, **kwargs)

        # Try to get from cache
        cached_value = self.get(cache_key)

        if cached_value is not None:
            self._fallback_success_count += 1
            logger.info(f"{self.name}: Returning cached value for '{cache_key}'")
            return cached_value

        # No cache hit
        self._fallback_failure_count += 1
        logger.warning(f"{self.name}: No cached value for '{cache_key}'")
        raise ValueError(f"No cached value available for fallback")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

            return {
                "cache_size": len(self._cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
            }

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        with self._cache_lock:
            self._cache.clear()
            logger.info(f"{self.name}: Cache cleared")

    def __repr__(self) -> str:
        return (
            f"CacheFallback(ttl={self.ttl}s, size={len(self._cache)}/{self.max_cache_size}, "
            f"hit_rate={self.get_cache_stats()['hit_rate']:.1%})"
        )


# ============================================================================
# Default Value Fallback
# ============================================================================


class DefaultValueFallback(FallbackStrategy):
    """
    Fallback that returns a default value.

    Returns a predefined default value when primary service fails.
    Simple but effective for non-critical operations.

    Example:
        >>> fallback = DefaultValueFallback(default_value=[])
        >>> # Returns empty list when service fails
    """

    def __init__(
        self,
        default_value: Any = None,
        default_factory: Optional[Callable[[], Any]] = None,
        name: str = "default_value_fallback"
    ):
        """
        Initialize default value fallback.

        Args:
            default_value: Static default value to return
            default_factory: Factory function to generate default value
            name: Strategy name
        """
        super().__init__(name)
        self.default_value = default_value
        self.default_factory = default_factory

        if default_factory:
            logger.debug(f"Initialized {self.name} with default_factory")
        else:
            logger.debug(f"Initialized {self.name} with default_value={default_value}")

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with default value fallback."""
        self._fallback_count += 1
        self._fallback_success_count += 1

        if self.default_factory:
            result = self.default_factory()
            logger.info(f"{self.name}: Returning factory-generated default value")
        else:
            result = self.default_value
            logger.info(f"{self.name}: Returning default value")

        return result

    def __repr__(self) -> str:
        if self.default_factory:
            return f"DefaultValueFallback(factory={self.default_factory.__name__})"
        return f"DefaultValueFallback(value={self.default_value})"


# ============================================================================
# Alternative Service Fallback
# ============================================================================


class AlternativeServiceFallback(FallbackStrategy):
    """
    Fallback that routes to an alternative service.

    Routes requests to a backup service when primary fails.
    Useful for multi-region deployments or service redundancy.

    Example:
        >>> def backup_service(*args, **kwargs):
        ...     return requests.get("https://backup-api.example.com/data")
        >>>
        >>> fallback = AlternativeServiceFallback(
        ...     alternative_func=backup_service,
        ...     timeout_seconds=5.0
        ... )
    """

    def __init__(
        self,
        alternative_func: Callable[..., Any],
        timeout_seconds: Optional[float] = None,
        retry_on_failure: bool = False,
        max_retries: int = 1,
        name: str = "alternative_service_fallback"
    ):
        """
        Initialize alternative service fallback.

        Args:
            alternative_func: Function to call alternative service
            timeout_seconds: Timeout for alternative service call
            retry_on_failure: Retry alternative service on failure
            max_retries: Maximum number of retries
            name: Strategy name
        """
        super().__init__(name)
        self.alternative_func = alternative_func
        self.timeout = timeout_seconds
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries

        logger.debug(
            f"Initialized {self.name} with timeout={timeout_seconds}s, "
            f"max_retries={max_retries}"
        )

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with alternative service fallback."""
        self._fallback_count += 1

        attempts = 0
        last_error = None

        while attempts <= self.max_retries:
            try:
                logger.info(f"{self.name}: Calling alternative service (attempt {attempts + 1})")

                # Call alternative service
                if self.timeout:
                    # Simple timeout implementation
                    result = self._call_with_timeout(self.alternative_func, *args, **kwargs)
                else:
                    result = self.alternative_func(*args, **kwargs)

                self._fallback_success_count += 1
                logger.info(f"{self.name}: Alternative service succeeded")
                return result

            except Exception as e:
                last_error = e
                attempts += 1
                logger.warning(f"{self.name}: Alternative service failed (attempt {attempts}): {e}")

                if attempts <= self.max_retries and self.retry_on_failure:
                    time.sleep(0.1 * attempts)  # Brief backoff
                    continue
                break

        # All attempts failed
        self._fallback_failure_count += 1
        logger.error(f"{self.name}: Alternative service failed after {attempts} attempts")
        raise Exception(f"Alternative service failed: {last_error}")

    async def execute_async(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async with alternative service fallback."""
        self._fallback_count += 1

        attempts = 0
        last_error = None

        while attempts <= self.max_retries:
            try:
                logger.info(f"{self.name}: Calling alternative service async (attempt {attempts + 1})")

                # Call alternative service
                if self.timeout:
                    result = await asyncio.wait_for(
                        self.alternative_func(*args, **kwargs),
                        timeout=self.timeout
                    )
                else:
                    result = await self.alternative_func(*args, **kwargs)

                self._fallback_success_count += 1
                logger.info(f"{self.name}: Alternative service succeeded")
                return result

            except Exception as e:
                last_error = e
                attempts += 1
                logger.warning(f"{self.name}: Alternative service failed (attempt {attempts}): {e}")

                if attempts <= self.max_retries and self.retry_on_failure:
                    await asyncio.sleep(0.1 * attempts)
                    continue
                break

        self._fallback_failure_count += 1
        raise Exception(f"Alternative service failed: {last_error}")

    def _call_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with timeout (synchronous)."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.timeout)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"Alternative service timed out after {self.timeout}s")

    def __repr__(self) -> str:
        return (
            f"AlternativeServiceFallback(func={self.alternative_func.__name__}, "
            f"timeout={self.timeout}s)"
        )


# ============================================================================
# Degraded Mode Fallback
# ============================================================================


class DegradedModeFallback(FallbackStrategy):
    """
    Fallback that provides reduced functionality.

    Returns a degraded response with limited data or features.
    Useful for graceful degradation of service capabilities.

    Example:
        >>> def degraded_handler(func, *args, **kwargs):
        ...     # Return partial data
        ...     return {"status": "degraded", "data": None, "message": "Limited service"}
        >>>
        >>> fallback = DegradedModeFallback(
        ...     degraded_func=degraded_handler,
        ...     include_error_info=True
        ... )
    """

    def __init__(
        self,
        degraded_func: Callable[..., Any],
        include_error_info: bool = False,
        degradation_marker: str = "DEGRADED",
        name: str = "degraded_mode_fallback"
    ):
        """
        Initialize degraded mode fallback.

        Args:
            degraded_func: Function that provides degraded response
            include_error_info: Include error information in response
            degradation_marker: Marker to indicate degraded mode
            name: Strategy name
        """
        super().__init__(name)
        self.degraded_func = degraded_func
        self.include_error_info = include_error_info
        self.degradation_marker = degradation_marker

        logger.debug(f"Initialized {self.name} with degraded function")

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with degraded mode fallback."""
        self._fallback_count += 1

        try:
            result = self.degraded_func(original_func, *args, **kwargs)

            # Add degradation marker if result is dict
            if isinstance(result, dict) and self.degradation_marker:
                result[self.degradation_marker] = True

            self._fallback_success_count += 1
            logger.info(f"{self.name}: Returning degraded response")
            return result

        except Exception as e:
            self._fallback_failure_count += 1
            logger.error(f"{self.name}: Degraded function failed: {e}")
            raise

    def __repr__(self) -> str:
        return f"DegradedModeFallback(func={self.degraded_func.__name__})"


# ============================================================================
# Queued Request Fallback
# ============================================================================


class QueuedRequestFallback(FallbackStrategy):
    """
    Fallback that queues requests for later processing.

    Queues failed requests and retries them when service recovers.
    Useful for eventually-consistent operations.

    Example:
        >>> fallback = QueuedRequestFallback(
        ...     max_queue_size=1000,
        ...     ttl_seconds=3600.0,  # 1 hour
        ...     on_recovery=process_queue
        ... )
    """

    def __init__(
        self,
        max_queue_size: int = 1000,
        ttl_seconds: float = 3600.0,
        on_recovery: Optional[Callable[[Deque], None]] = None,
        persist_to_disk: bool = False,
        persistence_path: Optional[Path] = None,
        name: str = "queued_request_fallback"
    ):
        """
        Initialize queued request fallback.

        Args:
            max_queue_size: Maximum number of queued requests
            ttl_seconds: Time-to-live for queued requests
            on_recovery: Callback to process queue on recovery
            persist_to_disk: Persist queue to disk
            persistence_path: Path for persistence file
            name: Strategy name
        """
        super().__init__(name)
        self.max_queue_size = max_queue_size
        self.ttl = ttl_seconds
        self.on_recovery = on_recovery
        self.persist_to_disk = persist_to_disk
        self.persistence_path = persistence_path or Path("/tmp/circuit_breaker_queue.pkl")

        self._queue: Deque[Tuple[datetime, Callable, tuple, dict]] = deque(maxlen=max_queue_size)
        self._queue_lock = threading.Lock()

        # Load persisted queue if available
        if self.persist_to_disk:
            self._load_queue()

        logger.debug(
            f"Initialized {self.name} with max_size={max_queue_size}, "
            f"ttl={ttl_seconds}s, persist={persist_to_disk}"
        )

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with queued request fallback."""
        self._fallback_count += 1

        with self._queue_lock:
            # Clean expired requests
            self._clean_expired()

            # Check queue size
            if len(self._queue) >= self.max_queue_size:
                self._fallback_failure_count += 1
                logger.warning(f"{self.name}: Queue full ({len(self._queue)}), dropping request")
                raise ValueError("Request queue full")

            # Queue the request
            self._queue.append((datetime.now(), original_func, args, kwargs))
            self._fallback_success_count += 1

            logger.info(f"{self.name}: Queued request (queue_size={len(self._queue)})")

            # Persist if enabled
            if self.persist_to_disk:
                self._persist_queue()

            # Return acknowledgment
            return {
                "status": "queued",
                "queue_position": len(self._queue),
                "message": "Request queued for later processing"
            }

    def _clean_expired(self) -> None:
        """Remove expired requests from queue."""
        cutoff_time = datetime.now() - timedelta(seconds=self.ttl)

        original_size = len(self._queue)
        self._queue = deque(
            (ts, func, args, kwargs)
            for ts, func, args, kwargs in self._queue
            if ts >= cutoff_time
        )

        removed = original_size - len(self._queue)
        if removed > 0:
            logger.debug(f"{self.name}: Removed {removed} expired requests from queue")

    def process_queue(self) -> Dict[str, Any]:
        """
        Process all queued requests.

        Returns:
            Statistics about processing
        """
        with self._queue_lock:
            total = len(self._queue)
            successes = 0
            failures = 0

            logger.info(f"{self.name}: Processing {total} queued requests")

            while self._queue:
                timestamp, func, args, kwargs = self._queue.popleft()

                try:
                    func(*args, **kwargs)
                    successes += 1
                except Exception as e:
                    failures += 1
                    logger.warning(f"{self.name}: Failed to process queued request: {e}")

            stats = {
                "total_processed": total,
                "successes": successes,
                "failures": failures,
                "success_rate": successes / total if total > 0 else 0.0
            }

            logger.info(
                f"{self.name}: Processed queue - {successes}/{total} succeeded "
                f"({stats['success_rate']:.1%})"
            )

            # Clear persistence
            if self.persist_to_disk:
                self._persist_queue()

            return stats

    def _persist_queue(self) -> None:
        """Persist queue to disk."""
        try:
            with open(self.persistence_path, 'wb') as f:
                pickle.dump(list(self._queue), f)
            logger.debug(f"{self.name}: Persisted queue to {self.persistence_path}")
        except Exception as e:
            logger.error(f"{self.name}: Failed to persist queue: {e}")

    def _load_queue(self) -> None:
        """Load queue from disk."""
        try:
            if self.persistence_path.exists():
                with open(self.persistence_path, 'rb') as f:
                    queued_items = pickle.load(f)
                    self._queue = deque(queued_items, maxlen=self.max_queue_size)
                logger.info(f"{self.name}: Loaded {len(self._queue)} items from {self.persistence_path}")
        except Exception as e:
            logger.error(f"{self.name}: Failed to load queue: {e}")

    def get_queue_size(self) -> int:
        """Get current queue size."""
        with self._queue_lock:
            return len(self._queue)

    def clear_queue(self) -> None:
        """Clear all queued requests."""
        with self._queue_lock:
            self._queue.clear()
            if self.persist_to_disk:
                self._persist_queue()
            logger.info(f"{self.name}: Queue cleared")

    def __repr__(self) -> str:
        return f"QueuedRequestFallback(queue_size={len(self._queue)}/{self.max_queue_size})"


# ============================================================================
# Custom Fallback
# ============================================================================


class CustomFallback(FallbackStrategy):
    """
    Custom fallback using user-defined function.

    Provides complete flexibility for fallback logic.

    Example:
        >>> def my_fallback(func, *args, **kwargs):
        ...     # Custom fallback logic
        ...     return {"error": "Service unavailable", "retry_after": 60}
        >>>
        >>> fallback = CustomFallback(fallback_func=my_fallback)
    """

    def __init__(
        self,
        fallback_func: Callable[..., Any],
        name: str = "custom_fallback"
    ):
        """
        Initialize custom fallback.

        Args:
            fallback_func: Custom fallback function
            name: Strategy name
        """
        super().__init__(name)
        self.fallback_func = fallback_func

        logger.debug(f"Initialized {self.name} with custom function")

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with custom fallback."""
        self._fallback_count += 1

        try:
            result = self.fallback_func(original_func, *args, **kwargs)
            self._fallback_success_count += 1
            logger.info(f"{self.name}: Custom fallback succeeded")
            return result
        except Exception as e:
            self._fallback_failure_count += 1
            logger.error(f"{self.name}: Custom fallback failed: {e}")
            raise

    async def execute_async(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async with custom fallback."""
        self._fallback_count += 1

        try:
            if asyncio.iscoroutinefunction(self.fallback_func):
                result = await self.fallback_func(original_func, *args, **kwargs)
            else:
                result = self.fallback_func(original_func, *args, **kwargs)

            self._fallback_success_count += 1
            logger.info(f"{self.name}: Custom fallback succeeded (async)")
            return result
        except Exception as e:
            self._fallback_failure_count += 1
            logger.error(f"{self.name}: Custom fallback failed (async): {e}")
            raise

    def __repr__(self) -> str:
        return f"CustomFallback(func={self.fallback_func.__name__})"


# ============================================================================
# Composite Fallback
# ============================================================================


class CompositeFallback(FallbackStrategy):
    """
    Composite fallback that tries multiple strategies in sequence.

    Attempts fallback strategies in order until one succeeds.

    Example:
        >>> fallback = CompositeFallback(
        ...     strategies=[
        ...         CacheFallback(),
        ...         AlternativeServiceFallback(backup_func),
        ...         DefaultValueFallback(default_value=None)
        ...     ]
        ... )
    """

    def __init__(
        self,
        strategies: list[FallbackStrategy],
        name: str = "composite_fallback"
    ):
        """
        Initialize composite fallback.

        Args:
            strategies: List of fallback strategies to try
            name: Strategy name
        """
        super().__init__(name)
        if not strategies:
            raise ValueError("At least one strategy must be provided")

        self.strategies = strategies

        logger.debug(f"Initialized {self.name} with {len(strategies)} strategies")

    def execute(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute with composite fallback."""
        self._fallback_count += 1

        last_error = None
        for i, strategy in enumerate(self.strategies):
            try:
                logger.debug(f"{self.name}: Trying strategy {i + 1}/{len(self.strategies)}: {strategy.name}")
                result = strategy.execute(original_func, *args, **kwargs)
                self._fallback_success_count += 1
                logger.info(f"{self.name}: Strategy {strategy.name} succeeded")
                return result
            except Exception as e:
                last_error = e
                logger.debug(f"{self.name}: Strategy {strategy.name} failed: {e}")
                continue

        # All strategies failed
        self._fallback_failure_count += 1
        logger.error(f"{self.name}: All {len(self.strategies)} strategies failed")
        raise Exception(f"All fallback strategies failed. Last error: {last_error}")

    async def execute_async(self, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async with composite fallback."""
        self._fallback_count += 1

        last_error = None
        for i, strategy in enumerate(self.strategies):
            try:
                logger.debug(f"{self.name}: Trying strategy {i + 1}/{len(self.strategies)}: {strategy.name}")
                result = await strategy.execute_async(original_func, *args, **kwargs)
                self._fallback_success_count += 1
                logger.info(f"{self.name}: Strategy {strategy.name} succeeded (async)")
                return result
            except Exception as e:
                last_error = e
                logger.debug(f"{self.name}: Strategy {strategy.name} failed (async): {e}")
                continue

        self._fallback_failure_count += 1
        raise Exception(f"All fallback strategies failed. Last error: {last_error}")

    def __repr__(self) -> str:
        strategy_names = [s.name for s in self.strategies]
        return f"CompositeFallback(strategies={strategy_names})"

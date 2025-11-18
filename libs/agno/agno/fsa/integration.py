"""
Integration Patterns for Circuit Breaker FSA

This module provides integration with other resilience patterns
such as retry logic, timeouts, bulkheads, rate limiting, and caching.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Base Integration
# ============================================================================


class Integration(ABC):
    """
    Abstract base class for integrations.

    Integrations wrap circuit breaker functionality with additional
    resilience patterns.
    """

    def __init__(self, name: str = "integration"):
        """
        Initialize integration.

        Args:
            name: Name identifier for this integration
        """
        self.name = name

    @abstractmethod
    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Wrap circuit breaker execution with additional logic.

        Args:
            circuit_breaker: Circuit breaker instance
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of execution
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# ============================================================================
# Retry Integration
# ============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay_seconds: float = 0.1
    max_delay_seconds: float = 10.0
    multiplier: float = 2.0
    jitter: bool = True


class RetryIntegration(Integration):
    """
    Integration with retry logic.

    Combines circuit breaker with exponential backoff retry.
    Retries failed requests before giving up.

    Example:
        >>> retry = RetryIntegration(
        ...     max_retries=3,
        ...     exponential_backoff=True
        ... )
        >>> cb = CircuitBreakerFSA()
        >>> result = retry.wrap_execute(cb, api_call)
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 10.0,
        exponential_backoff: bool = True,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retry_on_circuit_open: bool = False,
        name: str = "retry_integration"
    ):
        """
        Initialize retry integration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay before first retry
            max_delay: Maximum delay between retries
            exponential_backoff: Use exponential backoff
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Add random jitter to delays
            retry_on_circuit_open: Retry even when circuit is open
            name: Integration name
        """
        super().__init__(name)
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retry_on_circuit_open = retry_on_circuit_open

        logger.debug(
            f"Initialized {self.name} with max_retries={max_retries}, "
            f"exponential_backoff={exponential_backoff}"
        )

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with retry logic."""
        from agno.fsa.circuit_breaker import CircuitOpenError

        last_error = None
        attempt = 0

        while attempt <= self.max_retries:
            try:
                return circuit_breaker.execute(func, *args, **kwargs)

            except CircuitOpenError as e:
                # Don't retry on circuit open unless configured to do so
                if not self.retry_on_circuit_open:
                    raise
                last_error = e

            except Exception as e:
                last_error = e
                logger.debug(f"{self.name}: Attempt {attempt + 1} failed: {e}")

            attempt += 1

            # Don't sleep after last attempt
            if attempt <= self.max_retries:
                delay = self._calculate_delay(attempt)
                logger.debug(f"{self.name}: Retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(delay)

        # All retries exhausted
        logger.warning(f"{self.name}: All {self.max_retries} retries exhausted")
        raise last_error

    async def wrap_execute_async(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute async with retry logic."""
        from agno.fsa.circuit_breaker import CircuitOpenError

        last_error = None
        attempt = 0

        while attempt <= self.max_retries:
            try:
                return await circuit_breaker.execute_async(func, *args, **kwargs)

            except CircuitOpenError as e:
                if not self.retry_on_circuit_open:
                    raise
                last_error = e

            except Exception as e:
                last_error = e
                logger.debug(f"{self.name}: Attempt {attempt + 1} failed: {e}")

            attempt += 1

            if attempt <= self.max_retries:
                delay = self._calculate_delay(attempt)
                logger.debug(f"{self.name}: Retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(delay)

        logger.warning(f"{self.name}: All {self.max_retries} retries exhausted")
        raise last_error

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.exponential_backoff:
            delay = min(
                self.initial_delay * (self.backoff_multiplier ** (attempt - 1)),
                self.max_delay
            )
        else:
            delay = self.initial_delay

        # Add jitter
        if self.jitter:
            import random
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount

        return delay


# ============================================================================
# Timeout Integration
# ============================================================================


class TimeoutIntegration(Integration):
    """
    Integration with timeout enforcement.

    Enforces maximum execution time for requests.
    Cancels requests that exceed timeout.

    Example:
        >>> timeout = TimeoutIntegration(timeout_seconds=5.0)
        >>> cb = CircuitBreakerFSA()
        >>> result = timeout.wrap_execute(cb, slow_api_call)
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        raise_on_timeout: bool = True,
        name: str = "timeout_integration"
    ):
        """
        Initialize timeout integration.

        Args:
            timeout_seconds: Timeout in seconds
            raise_on_timeout: Raise exception on timeout
            name: Integration name
        """
        super().__init__(name)
        self.timeout = timeout_seconds
        self.raise_on_timeout = raise_on_timeout

        logger.debug(f"Initialized {self.name} with timeout={timeout_seconds}s")

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with timeout."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(circuit_breaker.execute, func, *args, **kwargs)

            try:
                result = future.result(timeout=self.timeout)
                return result

            except concurrent.futures.TimeoutError:
                logger.warning(f"{self.name}: Execution timed out after {self.timeout}s")
                if self.raise_on_timeout:
                    raise TimeoutError(f"Execution exceeded timeout of {self.timeout}s")
                return None

    async def wrap_execute_async(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute async with timeout."""
        try:
            result = await asyncio.wait_for(
                circuit_breaker.execute_async(func, *args, **kwargs),
                timeout=self.timeout
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(f"{self.name}: Execution timed out after {self.timeout}s")
            if self.raise_on_timeout:
                raise TimeoutError(f"Execution exceeded timeout of {self.timeout}s")
            return None


# ============================================================================
# Bulkhead Integration
# ============================================================================


class BulkheadIntegration(Integration):
    """
    Integration with bulkhead pattern.

    Isolates resources and limits concurrent requests.
    Prevents resource exhaustion from cascading failures.

    Example:
        >>> bulkhead = BulkheadIntegration(
        ...     max_concurrent=10,
        ...     max_queue_size=100
        ... )
        >>> cb = CircuitBreakerFSA()
        >>> result = bulkhead.wrap_execute(cb, api_call)
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue_size: int = 100,
        queue_timeout_seconds: float = 30.0,
        name: str = "bulkhead_integration"
    ):
        """
        Initialize bulkhead integration.

        Args:
            max_concurrent: Maximum concurrent executions
            max_queue_size: Maximum queue size for waiting requests
            queue_timeout_seconds: Timeout for queued requests
            name: Integration name
        """
        super().__init__(name)
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.queue_timeout = queue_timeout_seconds

        self._semaphore = threading.Semaphore(max_concurrent)
        self._queue: Deque[Any] = deque(maxlen=max_queue_size)
        self._queue_lock = threading.Lock()
        self._active_count = 0

        logger.debug(
            f"Initialized {self.name} with max_concurrent={max_concurrent}, "
            f"max_queue={max_queue_size}"
        )

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with bulkhead isolation."""
        # Try to acquire semaphore
        acquired = self._semaphore.acquire(timeout=self.queue_timeout)

        if not acquired:
            logger.warning(f"{self.name}: Bulkhead full, request rejected")
            raise RuntimeError("Bulkhead capacity exceeded")

        try:
            with self._queue_lock:
                self._active_count += 1

            logger.debug(f"{self.name}: Executing (active={self._active_count}/{self.max_concurrent})")
            return circuit_breaker.execute(func, *args, **kwargs)

        finally:
            with self._queue_lock:
                self._active_count -= 1
            self._semaphore.release()

    async def wrap_execute_async(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute async with bulkhead isolation."""
        # Use asyncio Semaphore for async
        if not hasattr(self, '_async_semaphore'):
            self._async_semaphore = asyncio.Semaphore(self.max_concurrent)

        async with self._async_semaphore:
            with self._queue_lock:
                self._active_count += 1

            try:
                logger.debug(f"{self.name}: Executing async (active={self._active_count}/{self.max_concurrent})")
                return await circuit_breaker.execute_async(func, *args, **kwargs)
            finally:
                with self._queue_lock:
                    self._active_count -= 1

    def get_active_count(self) -> int:
        """Get number of active executions."""
        with self._queue_lock:
            return self._active_count


# ============================================================================
# Rate Limiter Integration
# ============================================================================


class RateLimiterIntegration(Integration):
    """
    Integration with rate limiting.

    Limits request rate to prevent overwhelming services.
    Uses token bucket algorithm.

    Example:
        >>> limiter = RateLimiterIntegration(
        ...     requests_per_second=10.0,
        ...     burst_size=20
        ... )
        >>> cb = CircuitBreakerFSA()
        >>> result = limiter.wrap_execute(cb, api_call)
    """

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: Optional[int] = None,
        name: str = "rate_limiter_integration"
    ):
        """
        Initialize rate limiter integration.

        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size (defaults to requests_per_second)
            name: Integration name
        """
        super().__init__(name)
        self.rate = requests_per_second
        self.burst_size = burst_size or int(requests_per_second)

        # Token bucket implementation
        self._tokens = float(self.burst_size)
        self._last_update = time.time()
        self._lock = threading.Lock()

        logger.debug(
            f"Initialized {self.name} with rate={requests_per_second}rps, "
            f"burst={self.burst_size}"
        )

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with rate limiting."""
        # Wait for token
        self._acquire_token()

        return circuit_breaker.execute(func, *args, **kwargs)

    async def wrap_execute_async(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute async with rate limiting."""
        # Wait for token asynchronously
        await self._acquire_token_async()

        return await circuit_breaker.execute_async(func, *args, **kwargs)

    def _acquire_token(self) -> None:
        """Acquire a token from the bucket (blocking)."""
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_update
                self._last_update = now

                # Add tokens based on elapsed time
                self._tokens = min(
                    self.burst_size,
                    self._tokens + elapsed * self.rate
                )

                # Check if token available
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

            # Wait a bit before trying again
            time.sleep(0.01)

    async def _acquire_token_async(self) -> None:
        """Acquire a token from the bucket (async)."""
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_update
                self._last_update = now

                self._tokens = min(
                    self.burst_size,
                    self._tokens + elapsed * self.rate
                )

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

            await asyncio.sleep(0.01)

    def get_available_tokens(self) -> float:
        """Get number of available tokens."""
        with self._lock:
            now = time.time()
            elapsed = now - self._last_update

            tokens = min(
                self.burst_size,
                self._tokens + elapsed * self.rate
            )

            return tokens


# ============================================================================
# Cache Integration
# ============================================================================


class CacheIntegration(Integration):
    """
    Integration with caching layer.

    Caches successful responses and serves from cache when available.
    Reduces load on backend services.

    Example:
        >>> cache = CacheIntegration(ttl_seconds=300.0)
        >>> cb = CircuitBreakerFSA()
        >>> result = cache.wrap_execute(cb, api_call)
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_cache_size: int = 1000,
        cache_key_func: Optional[Callable[..., str]] = None,
        name: str = "cache_integration"
    ):
        """
        Initialize cache integration.

        Args:
            ttl_seconds: Time-to-live for cache entries
            max_cache_size: Maximum number of cache entries
            cache_key_func: Function to generate cache keys
            name: Integration name
        """
        super().__init__(name)
        self.ttl = ttl_seconds
        self.max_cache_size = max_cache_size
        self.cache_key_func = cache_key_func or self._default_cache_key

        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self._cache_lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        logger.debug(f"Initialized {self.name} with ttl={ttl_seconds}s, max_size={max_cache_size}")

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with caching."""
        # Generate cache key
        cache_key = self.cache_key_func(func, *args, **kwargs)

        # Try to get from cache
        cached_value = self._get_from_cache(cache_key)
        if cached_value is not None:
            self._hits += 1
            logger.debug(f"{self.name}: Cache hit for key '{cache_key}'")
            return cached_value

        self._misses += 1

        # Execute and cache result
        result = circuit_breaker.execute(func, *args, **kwargs)
        self._put_in_cache(cache_key, result)

        return result

    def _default_cache_key(self, func: Callable, *args, **kwargs) -> str:
        """Generate default cache key."""
        import hashlib

        key_parts = [func.__name__]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._cache_lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            # Check if expired
            age = (datetime.now() - timestamp).total_seconds()
            if age > self.ttl:
                del self._cache[key]
                return None

            return value

    def _put_in_cache(self, key: str, value: Any) -> None:
        """Put value in cache."""
        with self._cache_lock:
            # Enforce size limit (simple LRU-like eviction)
            if len(self._cache) >= self.max_cache_size:
                # Remove oldest entry
                if self._cache:
                    oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]

            self._cache[key] = (value, datetime.now())

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_size": self.max_cache_size
        }

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        with self._cache_lock:
            self._cache.clear()


# ============================================================================
# Service Mesh Integration
# ============================================================================


class ServiceMeshIntegration(Integration):
    """
    Integration with service mesh (Istio, Linkerd, etc.).

    Provides interoperability with service mesh features.
    Adds metadata and headers for mesh routing.

    Example:
        >>> mesh = ServiceMeshIntegration(
        ...     service_name="user-service",
        ...     version="v1.2.0"
        ... )
        >>> cb = CircuitBreakerFSA()
        >>> result = mesh.wrap_execute(cb, api_call)
    """

    def __init__(
        self,
        service_name: str,
        version: str = "v1",
        namespace: str = "default",
        mesh_headers: Optional[Dict[str, str]] = None,
        name: str = "service_mesh_integration"
    ):
        """
        Initialize service mesh integration.

        Args:
            service_name: Name of the service
            version: Service version
            namespace: Kubernetes namespace
            mesh_headers: Additional mesh headers
            name: Integration name
        """
        super().__init__(name)
        self.service_name = service_name
        self.version = version
        self.namespace = namespace
        self.mesh_headers = mesh_headers or {}

        logger.debug(
            f"Initialized {self.name} for service={service_name}, "
            f"version={version}, namespace={namespace}"
        )

    def wrap_execute(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute with service mesh metadata."""
        # Add mesh metadata to kwargs
        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        # Add standard service mesh headers
        kwargs['headers'].update({
            'x-service-name': self.service_name,
            'x-service-version': self.version,
            'x-namespace': self.namespace,
            'x-circuit-breaker-state': str(circuit_breaker.get_state()),
        })

        # Add custom mesh headers
        kwargs['headers'].update(self.mesh_headers)

        return circuit_breaker.execute(func, *args, **kwargs)

    def get_mesh_metadata(self) -> Dict[str, str]:
        """Get service mesh metadata."""
        return {
            'service_name': self.service_name,
            'version': self.version,
            'namespace': self.namespace,
            **self.mesh_headers
        }

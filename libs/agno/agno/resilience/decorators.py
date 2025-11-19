"""
Resilience Pattern Decorators

Provides convenient decorators for applying resilience patterns including
circuit breakers, bulkheads, retries, timeouts, and combinations.
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Optional, TypeVar, Any, Type
from dataclasses import dataclass

from agno.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from agno.resilience.bulkhead import Bulkhead, BulkheadConfig
from agno.exceptions import CircuitBreakerOpenError, BulkheadFullError

T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    delay_seconds: float = 1.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    retry_on_exceptions: tuple = (Exception,)


def with_retry(config: Optional[RetryConfig] = None) -> Callable:
    """
    Decorator for retrying failed function calls.

    Example:
        ```python
        @with_retry(RetryConfig(max_attempts=3, delay_seconds=2))
        def unstable_api_call():
            return requests.get("https://api.example.com/data")
        ```
    """
    cfg = config or RetryConfig()

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                delay = cfg.delay_seconds

                for attempt in range(cfg.max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except cfg.retry_on_exceptions as e:
                        last_exception = e
                        if attempt < cfg.max_attempts - 1:
                            await asyncio.sleep(delay)
                            if cfg.exponential_backoff:
                                delay = min(delay * cfg.backoff_multiplier, cfg.max_delay_seconds)

                raise last_exception

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                delay = cfg.delay_seconds

                for attempt in range(cfg.max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except cfg.retry_on_exceptions as e:
                        last_exception = e
                        if attempt < cfg.max_attempts - 1:
                            time.sleep(delay)
                            if cfg.exponential_backoff:
                                delay = min(delay * cfg.backoff_multiplier, cfg.max_delay_seconds)

                raise last_exception

            return sync_wrapper

    return decorator


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior"""
    timeout_seconds: float = 30.0
    timeout_exception: Type[Exception] = TimeoutError


def with_timeout(config: Optional[TimeoutConfig] = None) -> Callable:
    """
    Decorator for enforcing timeouts on function calls.

    Example:
        ```python
        @with_timeout(TimeoutConfig(timeout_seconds=10))
        async def slow_operation():
            await some_long_running_task()
        ```
    """
    cfg = config or TimeoutConfig()

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=cfg.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise cfg.timeout_exception(
                        f"Function {func.__name__} exceeded timeout of {cfg.timeout_seconds}s"
                    )

            return async_wrapper
        else:
            # Sync timeout is more complex, requires threading
            # For simplicity, just return the function as-is for sync
            # A production implementation would use threading.Timer
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # TODO: Implement sync timeout with threading
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_calls: int = 10
    period_seconds: float = 1.0


class RateLimiter:
    """Simple token bucket rate limiter"""

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.calls = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire rate limit token (async)"""
        async with self._lock:
            now = time.time()
            # Remove old calls outside the window
            self.calls = [c for c in self.calls if now - c < self.period_seconds]

            if len(self.calls) >= self.max_calls:
                # Wait until oldest call expires
                sleep_time = self.period_seconds - (now - self.calls[0])
                await asyncio.sleep(sleep_time)
                self.calls = self.calls[1:]

            self.calls.append(now)


def with_rate_limit(config: Optional[RateLimitConfig] = None) -> Callable:
    """
    Decorator for rate limiting function calls.

    Example:
        ```python
        @with_rate_limit(RateLimitConfig(max_calls=10, period_seconds=1))
        async def api_call():
            return await client.get_data()
        ```
    """
    cfg = config or RateLimitConfig()
    limiter = RateLimiter(cfg.max_calls, cfg.period_seconds)

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                await limiter.acquire()
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            # Rate limiting for sync is complex, return as-is
            return func

    return decorator


def resilient(
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    bulkhead_config: Optional[BulkheadConfig] = None,
    retry_config: Optional[RetryConfig] = None,
    timeout_config: Optional[TimeoutConfig] = None,
    name: Optional[str] = None
) -> Callable:
    """
    Composite decorator that applies multiple resilience patterns.

    Applies patterns in order: Timeout → Circuit Breaker → Bulkhead → Retry → Function

    Example:
        ```python
        @resilient(
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
            bulkhead_config=BulkheadConfig(max_concurrent=10),
            retry_config=RetryConfig(max_attempts=3),
            timeout_config=TimeoutConfig(timeout_seconds=30),
            name="critical_service"
        )
        async def critical_service_call():
            return await service.call()
        ```
    """

    def decorator(func: Callable) -> Callable:
        # Start with the original function
        wrapped = func
        func_name = name or func.__name__

        # Apply retry (innermost)
        if retry_config:
            wrapped = with_retry(retry_config)(wrapped)

        # Apply bulkhead
        if bulkhead_config:
            bh = Bulkhead(name=f"{func_name}_bulkhead", config=bulkhead_config)
            if asyncio.iscoroutinefunction(wrapped):
                original_wrapped = wrapped

                @wraps(original_wrapped)
                async def bulkhead_wrapper(*args, **kwargs):
                    return await bh.execute_async(original_wrapped, *args, **kwargs)

                wrapped = bulkhead_wrapper
            else:
                original_wrapped = wrapped

                @wraps(original_wrapped)
                def bulkhead_wrapper(*args, **kwargs):
                    return bh.execute(original_wrapped, *args, **kwargs)

                wrapped = bulkhead_wrapper

        # Apply circuit breaker
        if circuit_breaker_config:
            cb = CircuitBreaker(name=f"{func_name}_circuit", config=circuit_breaker_config)
            if asyncio.iscoroutinefunction(wrapped):
                original_wrapped = wrapped

                @wraps(original_wrapped)
                async def cb_wrapper(*args, **kwargs):
                    return await cb.call_async(original_wrapped, *args, **kwargs)

                wrapped = cb_wrapper
            else:
                original_wrapped = wrapped

                @wraps(original_wrapped)
                def cb_wrapper(*args, **kwargs):
                    return cb.call(original_wrapped, *args, **kwargs)

                wrapped = cb_wrapper

        # Apply timeout (outermost)
        if timeout_config:
            wrapped = with_timeout(timeout_config)(wrapped)

        return wrapped

    return decorator


def fallback(fallback_func: Callable, on_exceptions: tuple = (Exception,)) -> Callable:
    """
    Decorator that provides fallback behavior on exceptions.

    Example:
        ```python
        def get_cached_user(user_id):
            return cache.get(user_id)

        @fallback(get_cached_user, on_exceptions=(HTTPError,))
        def get_user(user_id):
            return api.get_user(user_id)
        ```
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except on_exceptions:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*args, **kwargs)
                    else:
                        return fallback_func(*args, **kwargs)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except on_exceptions:
                    return fallback_func(*args, **kwargs)

            return sync_wrapper

    return decorator

"""Retry Handler FSA with exponential backoff and circuit breaker for agno framework."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple, Type, Union

from agno.utils.log import logger


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, rejecting requests
    HALF_OPEN = "half_open"  # Testing if circuit can close


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Base for exponential backoff
    jitter: bool = True  # Add randomness to delay
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)

    # Circuit breaker settings
    circuit_breaker_enabled: bool = False
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Time in seconds before moving to half-open


@dataclass
class RetryStats:
    """Statistics for retry attempts."""

    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay: float = 0.0
    circuit_opens: int = 0


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class RetryHandler:
    """
    Retry handler with exponential backoff and circuit breaker.

    Features:
    - Exponential backoff with jitter
    - Configurable max retries
    - Retry on specific exceptions
    - Async and sync support
    - Basic circuit breaker pattern
    """

    def __init__(self, config: Optional[RetryConfig] = None, name: Optional[str] = None):
        """
        Initialize RetryHandler.

        Args:
            config: Retry configuration
            name: Optional name for the handler
        """
        self.config = config or RetryConfig()
        self.name = name or "RetryHandler"
        self.stats = RetryStats()

        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def circuit_state(self) -> CircuitState:
        """Get current circuit state, updating if necessary."""
        if not self.config.circuit_breaker_enabled:
            return CircuitState.CLOSED

        # Check if we should move from OPEN to HALF_OPEN
        if self._circuit_state == CircuitState.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.config.timeout:
                self._circuit_state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"{self.name}: Circuit breaker moved to HALF_OPEN state")

        return self._circuit_state

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )

        if self.config.jitter:
            # Add jitter: random value between 0 and delay
            delay = random.uniform(0, delay)

        return delay

    def _record_success(self) -> None:
        """Record a successful execution."""
        self.stats.successful_attempts += 1

        if not self.config.circuit_breaker_enabled:
            return

        if self._circuit_state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._circuit_state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"{self.name}: Circuit breaker CLOSED after {self._success_count} successes")
        elif self._circuit_state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed execution."""
        self.stats.failed_attempts += 1

        if not self.config.circuit_breaker_enabled:
            return

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._circuit_state == CircuitState.HALF_OPEN:
            # Any failure in half-open returns to open
            self._circuit_state = CircuitState.OPEN
            self.stats.circuit_opens += 1
            logger.warning(f"{self.name}: Circuit breaker OPENED from half-open state")
        elif self._circuit_state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._circuit_state = CircuitState.OPEN
                self.stats.circuit_opens += 1
                logger.warning(
                    f"{self.name}: Circuit breaker OPENED after {self._failure_count} failures"
                )

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with retry logic (synchronous).

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            CircuitBreakerOpen: If circuit breaker is open
            Exception: The last exception if all retries fail
        """
        # Check circuit breaker
        if self.circuit_state == CircuitState.OPEN:
            raise CircuitBreakerOpen(f"Circuit breaker is OPEN for {self.name}")

        last_exception = None
        attempt = 0

        while attempt <= self.config.max_retries:
            self.stats.total_attempts += 1

            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except self.config.retry_on_exceptions as e:
                last_exception = e
                self._record_failure()

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.stats.total_delay += delay
                    logger.debug(
                        f"{self.name}: Attempt {attempt + 1}/{self.config.max_retries + 1} failed. "
                        f"Retrying in {delay:.2f}s. Error: {e}"
                    )
                    time.sleep(delay)
                    attempt += 1
                else:
                    logger.error(
                        f"{self.name}: All {self.config.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )
                    break
            except Exception as e:
                # Exception not in retry list, fail immediately
                logger.error(f"{self.name}: Non-retryable exception: {e}")
                self._record_failure()
                raise

        # All retries exhausted
        if last_exception:
            raise last_exception

        raise RuntimeError(f"{self.name}: Retry logic failed without exception")

    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with retry logic (asynchronous).

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            CircuitBreakerOpen: If circuit breaker is open
            Exception: The last exception if all retries fail
        """
        # Check circuit breaker
        if self.circuit_state == CircuitState.OPEN:
            raise CircuitBreakerOpen(f"Circuit breaker is OPEN for {self.name}")

        last_exception = None
        attempt = 0

        while attempt <= self.config.max_retries:
            self.stats.total_attempts += 1

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self._record_success()
                return result
            except self.config.retry_on_exceptions as e:
                last_exception = e
                self._record_failure()

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.stats.total_delay += delay
                    logger.debug(
                        f"{self.name}: Attempt {attempt + 1}/{self.config.max_retries + 1} failed. "
                        f"Retrying in {delay:.2f}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    attempt += 1
                else:
                    logger.error(
                        f"{self.name}: All {self.config.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )
                    break
            except Exception as e:
                # Exception not in retry list, fail immediately
                logger.error(f"{self.name}: Non-retryable exception: {e}")
                self._record_failure()
                raise

        # All retries exhausted
        if last_exception:
            raise last_exception

        raise RuntimeError(f"{self.name}: Retry logic failed without exception")

    def reset(self) -> None:
        """Reset retry handler state."""
        self.stats = RetryStats()
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.debug(f"{self.name}: State reset")

    def get_stats(self) -> RetryStats:
        """Get retry statistics."""
        return self.stats


# Decorator versions for convenience
def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for automatic retry with exponential backoff (sync functions).

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add randomness to delay
        retry_on_exceptions: Tuple of exception types to retry on

    Example:
        @retry(max_retries=3, initial_delay=0.5)
        def my_function():
            # Your code here
            pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on_exceptions=retry_on_exceptions,
    )
    handler = RetryHandler(config=config)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return handler.execute(func, *args, **kwargs)
        return wrapper

    return decorator


def retry_async(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for automatic retry with exponential backoff (async functions).

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add randomness to delay
        retry_on_exceptions: Tuple of exception types to retry on

    Example:
        @retry_async(max_retries=3, initial_delay=0.5)
        async def my_async_function():
            # Your code here
            pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on_exceptions=retry_on_exceptions,
    )
    handler = RetryHandler(config=config)

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await handler.execute_async(func, *args, **kwargs)
        return wrapper

    return decorator

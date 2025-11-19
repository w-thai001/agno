"""
Retry Logic with Exponential Backoff

Provides retry mechanisms for database operations with configurable backoff strategies.
"""

import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from agno.database_adapter.exceptions import RetryExhausted
from agno.utils.log import logger


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            exponential_base: Base for exponential backoff (default: 2.0)
            jitter: Whether to add random jitter to delays (default: True)
            retryable_exceptions: Tuple of exception types to retry on
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(self.initial_delay * (self.exponential_base**attempt), self.max_delay)

        if self.jitter:
            import random

            # Add jitter: random value between 0 and 25% of delay
            jitter_amount = delay * 0.25 * random.random()
            delay += jitter_amount

        return delay


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    Decorator to add retry logic to a function.

    Args:
        config: RetryConfig instance (uses default if None)
        on_retry: Optional callback called on each retry with (exception, attempt_number)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(RetryConfig(max_retries=5))
        def connect_to_db():
            # Connection logic
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt >= config.max_retries:
                        logger.error(
                            f"Retry exhausted after {config.max_retries} attempts for {func.__name__}: {str(e)}"
                        )
                        raise RetryExhausted(
                            f"Failed after {config.max_retries} retries: {str(e)}"
                        ) from e

                    delay = config.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RetryExhausted(f"Retry logic failed unexpectedly for {func.__name__}")

        return wrapper

    return decorator


class RetryContext:
    """Context manager for manual retry control."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry context.

        Args:
            config: RetryConfig instance (uses default if None)
        """
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception: Optional[Exception] = None

    def __enter__(self) -> "RetryContext":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            return True  # Success, no retry needed

        if not isinstance(exc_val, self.config.retryable_exceptions):
            return False  # Not a retryable exception, propagate

        self.last_exception = exc_val

        if self.attempt >= self.config.max_retries:
            logger.error(f"Retry exhausted after {self.config.max_retries} attempts")
            return False  # Propagate exception

        delay = self.config.calculate_delay(self.attempt)
        logger.warning(f"Attempt {self.attempt + 1} failed. Retrying in {delay:.2f}s...")

        time.sleep(delay)
        self.attempt += 1
        return True  # Suppress exception, will retry

    def should_retry(self) -> bool:
        """Check if another retry attempt should be made."""
        return self.attempt < self.config.max_retries

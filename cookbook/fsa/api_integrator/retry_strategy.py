"""
Retry strategy with exponential backoff.

Implements intelligent retry logic for failed API requests with
exponential backoff and jitter to avoid thundering herd problem.
"""

import random
import time
from typing import Any, Callable, Optional, Type

from agno.utils.log import logger

from .models import RetryConfig


class RetryStrategy:
    """
    Retry strategy with exponential backoff.

    Features:
    - Exponential backoff with configurable base
    - Jitter to avoid thundering herd
    - Configurable max retries and max delay
    - Selective retry based on status codes
    - Retry on specific exceptions
    """

    def __init__(self, config: RetryConfig):
        """
        Initialize retry strategy.

        Args:
            config: Retry configuration
        """
        self.config = config
        logger.debug(
            f"RetryStrategy initialized: max_retries={config.max_retries}, "
            f"initial_delay={config.initial_delay}s, max_delay={config.max_delay}s"
        )

    def execute(
        self,
        func: Callable,
        *args,
        endpoint_name: Optional[str] = None,
        retry_on_exceptions: Optional[list[Type[Exception]]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            endpoint_name: Name of the endpoint (for logging)
            retry_on_exceptions: Exception types to retry on
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries failed
        """
        endpoint_name = endpoint_name or "unknown"
        retry_on_exceptions = retry_on_exceptions or [Exception]
        last_exception = None
        retry_count = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"RetryStrategy for {endpoint_name}: Attempt {attempt + 1}/"
                        f"{self.config.max_retries + 1}"
                    )

                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"RetryStrategy for {endpoint_name}: Succeeded after {attempt} retries"
                    )

                return result

            except Exception as e:
                last_exception = e
                retry_count = attempt

                # Check if we should retry this exception
                should_retry = any(isinstance(e, exc_type) for exc_type in retry_on_exceptions)

                if not should_retry:
                    logger.debug(
                        f"RetryStrategy for {endpoint_name}: Exception {type(e).__name__} "
                        f"not in retry list, not retrying"
                    )
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    logger.error(
                        f"RetryStrategy for {endpoint_name}: All {self.config.max_retries} "
                        f"retries exhausted"
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"RetryStrategy for {endpoint_name}: Attempt {attempt + 1} failed "
                    f"with {type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception

    def execute_with_status_check(
        self,
        func: Callable,
        *args,
        endpoint_name: Optional[str] = None,
        get_status_code: Optional[Callable[[Any], int]] = None,
        retry_on_exceptions: Optional[list[Type[Exception]]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic based on HTTP status codes.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            endpoint_name: Name of the endpoint (for logging)
            get_status_code: Function to extract status code from result
            retry_on_exceptions: Exception types to retry on
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            Exception: If all retries failed
        """
        endpoint_name = endpoint_name or "unknown"
        retry_on_exceptions = retry_on_exceptions or []
        last_exception = None
        retry_count = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(
                        f"RetryStrategy for {endpoint_name}: Attempt {attempt + 1}/"
                        f"{self.config.max_retries + 1}"
                    )

                result = func(*args, **kwargs)

                # Check status code if extractor provided
                if get_status_code:
                    status_code = get_status_code(result)

                    if status_code in self.config.retry_on_status_codes:
                        if attempt >= self.config.max_retries:
                            logger.error(
                                f"RetryStrategy for {endpoint_name}: "
                                f"Status {status_code}, all retries exhausted"
                            )
                            return result

                        delay = self._calculate_delay(attempt)
                        logger.warning(
                            f"RetryStrategy for {endpoint_name}: "
                            f"Status {status_code} (retryable). Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        continue

                # Success
                if attempt > 0:
                    logger.info(
                        f"RetryStrategy for {endpoint_name}: Succeeded after {attempt} retries"
                    )

                return result

            except Exception as e:
                last_exception = e
                retry_count = attempt

                # Check if we should retry this exception
                should_retry = any(isinstance(e, exc_type) for exc_type in retry_on_exceptions)

                if not should_retry:
                    logger.debug(
                        f"RetryStrategy for {endpoint_name}: Exception {type(e).__name__} "
                        f"not in retry list, not retrying"
                    )
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    logger.error(
                        f"RetryStrategy for {endpoint_name}: All {self.config.max_retries} "
                        f"retries exhausted"
                    )
                    raise

                # Calculate delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"RetryStrategy for {endpoint_name}: Attempt {attempt + 1} failed "
                    f"with {type(e).__name__}: {str(e)}. Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        exponential_delay = self.config.initial_delay * (self.config.exponential_base**attempt)

        # Cap at max_delay
        delay = min(exponential_delay, self.config.max_delay)

        # Add jitter (±25% randomization)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        final_delay = delay + jitter

        # Ensure non-negative
        return max(0, final_delay)

    def should_retry_status_code(self, status_code: int) -> bool:
        """
        Check if a status code should trigger a retry.

        Args:
            status_code: HTTP status code

        Returns:
            True if should retry, False otherwise
        """
        return status_code in self.config.retry_on_status_codes

    def get_retry_delay(self, attempt: int) -> float:
        """
        Get the retry delay for a specific attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        return self._calculate_delay(attempt)


class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, message: str, attempts: int, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception

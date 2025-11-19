"""
Circuit breaker implementation for API Integrator FSA.

Implements the circuit breaker pattern to prevent cascading failures
when an API becomes unresponsive or starts failing.
"""

import time
from threading import Lock
from typing import Optional

from agno.utils.log import logger

from .models import CircuitBreakerConfig, CircuitBreakerState


class CircuitBreaker:
    """
    Circuit breaker for API calls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(self, endpoint_name: str, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.

        Args:
            endpoint_name: Name of the endpoint this circuit breaker protects
            config: Circuit breaker configuration
        """
        self.endpoint_name = endpoint_name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = Lock()

        logger.debug(f"CircuitBreaker initialized for {endpoint_name}: {config}")

    def call(self, func, *args, **kwargs):
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if not self.config.enabled:
            return func(*args, **kwargs)

        with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker for {self.endpoint_name}: OPEN -> HALF_OPEN")
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN for {self.endpoint_name}. "
                        f"Service is unavailable. Will retry after timeout."
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.config.timeout

    def _on_success(self):
        """Handle successful request."""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"Circuit breaker for {self.endpoint_name}: Success in HALF_OPEN "
                    f"({self.success_count}/{self.config.success_threshold})"
                )
                if self.success_count >= self.config.success_threshold:
                    logger.info(f"Circuit breaker for {self.endpoint_name}: HALF_OPEN -> CLOSED")
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    def _on_failure(self, exception: Exception):
        """Handle failed request."""
        with self.lock:
            # Check if this exception type should be monitored
            exception_name = type(exception).__name__
            if exception_name not in self.config.monitored_exceptions:
                logger.debug(
                    f"Circuit breaker for {self.endpoint_name}: "
                    f"Exception {exception_name} not monitored, ignoring"
                )
                return

            self.failure_count += 1
            self.last_failure_time = time.time()

            logger.warning(
                f"Circuit breaker for {self.endpoint_name}: Failure recorded "
                f"({self.failure_count}/{self.config.failure_threshold})"
            )

            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.warning(f"Circuit breaker for {self.endpoint_name}: HALF_OPEN -> OPEN")
                self.state = CircuitBreakerState.OPEN
                self.failure_count = 0
                self.success_count = 0
            elif (
                self.state == CircuitBreakerState.CLOSED
                and self.failure_count >= self.config.failure_threshold
            ):
                logger.error(
                    f"Circuit breaker for {self.endpoint_name}: CLOSED -> OPEN "
                    f"(threshold {self.config.failure_threshold} reached)"
                )
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self.lock:
            return self.state

    def reset(self):
        """Manually reset the circuit breaker to CLOSED state."""
        with self.lock:
            logger.info(f"Circuit breaker for {self.endpoint_name}: Manual reset to CLOSED")
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None

    def get_metrics(self) -> dict:
        """Get circuit breaker metrics."""
        with self.lock:
            return {
                "endpoint_name": self.endpoint_name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "time_since_last_failure": (
                    time.time() - self.last_failure_time if self.last_failure_time else None
                ),
            }

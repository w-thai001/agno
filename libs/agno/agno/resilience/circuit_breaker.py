"""
Circuit Breaker Finite State Automaton (FSA)

This module implements a comprehensive circuit breaker pattern with:
- State machine: CLOSED → OPEN → HALF_OPEN
- Failure detection and automatic recovery
- Bulkhead isolation
- Fallback execution
- Real-time metrics and monitoring
- Async/sync support

Example:
    ```python
    from agno.resilience import CircuitBreaker, CircuitBreakerConfig
    from agno.resilience.policies import create_balanced_policy

    # Create circuit breaker
    cb = CircuitBreaker(
        name="api_service",
        config=CircuitBreakerConfig(
            failure_policy=create_balanced_policy(),
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=3
        )
    )

    # Use with sync function
    try:
        result = cb.call(lambda: api_client.get_user(user_id))
    except CircuitBreakerOpenError:
        result = get_cached_user(user_id)  # Fallback

    # Use with async function
    result = await cb.call_async(async_api_call)
    ```
"""

import asyncio
import time
import threading
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, TypeVar, Generic, List, Dict
from functools import wraps

from agno.resilience.states import CircuitState, CircuitStateData, StateTransition
from agno.resilience.policies import (
    FailurePolicy,
    TimeoutPolicy,
    HealthCheckConfig,
    create_balanced_policy
)
from agno.resilience.metrics import CircuitBreakerMetrics, register_circuit
from agno.exceptions import CircuitBreakerOpenError, BulkheadFullError

T = TypeVar('T')


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for circuit breaker behavior.

    This provides fine-grained control over circuit breaker operation,
    including failure detection, recovery, bulkhead isolation, and fallback.
    """
    # Failure detection
    failure_policy: Optional[FailurePolicy] = None
    failure_threshold: int = 5  # Consecutive failures to open
    success_threshold: int = 2  # Consecutive successes to close from half-open

    # Timeout and recovery
    timeout_policy: Optional[TimeoutPolicy] = None
    recovery_timeout: float = 60.0  # Seconds before attempting half-open
    half_open_max_calls: int = 3  # Max requests in half-open state

    # Health checks
    health_check_config: Optional[HealthCheckConfig] = None

    # Bulkhead isolation
    max_concurrent_calls: Optional[int] = None  # None = unlimited

    # Fallback
    fallback_function: Optional[Callable] = None
    fallback_async_function: Optional[Callable] = None

    # Custom failure predicate
    is_failure: Optional[Callable[[Any, Optional[Exception]], bool]] = None

    # Metrics and monitoring
    enable_metrics: bool = True
    metrics_window_size: int = 100  # Number of recent calls to track

    # State transition hooks
    on_state_change: Optional[Callable[[StateTransition], None]] = None
    on_open: Optional[Callable[[CircuitStateData], None]] = None
    on_close: Optional[Callable[[CircuitStateData], None]] = None
    on_half_open: Optional[Callable[[CircuitStateData], None]] = None

    # Logging
    verbose: bool = False

    def __post_init__(self):
        # Set default policies if not provided
        if self.failure_policy is None:
            self.failure_policy = create_balanced_policy()

        if self.timeout_policy is None:
            self.timeout_policy = TimeoutPolicy(
                open_timeout_seconds=self.recovery_timeout
            )

        if self.health_check_config is None:
            self.health_check_config = HealthCheckConfig(enabled=False)

        # Default failure predicate: exception or None result
        if self.is_failure is None:
            self.is_failure = lambda result, error: error is not None


class CircuitBreaker:
    """
    Circuit Breaker Finite State Automaton.

    Implements the circuit breaker pattern with comprehensive monitoring,
    adaptive recovery, and bulkhead isolation.

    Thread-safe for concurrent access.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit breaker
            config: Configuration (uses defaults if not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State management
        self._state = CircuitStateData(current_state=CircuitState.CLOSED)
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

        # Metrics
        self._metrics = register_circuit(name) if self.config.enable_metrics else None

        # Bulkhead semaphore
        self._semaphore: Optional[threading.Semaphore] = None
        self._async_semaphore: Optional[asyncio.Semaphore] = None
        if self.config.max_concurrent_calls:
            self._semaphore = threading.Semaphore(self.config.max_concurrent_calls)
            self._async_semaphore = asyncio.Semaphore(self.config.max_concurrent_calls)

        self._log(f"Circuit breaker '{name}' initialized in CLOSED state")

    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection (sync).

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            BulkheadFullError: If bulkhead is full
            Exception: Any exception from func
        """
        # Check bulkhead
        if not self._try_acquire_bulkhead():
            raise BulkheadFullError(self.name, self.config.max_concurrent_calls)

        try:
            # Check circuit state
            self._before_call()

            # Execute function with timing
            start_time = time.time()
            error = None
            result = None

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error = e
                raise
            finally:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                self._after_call(result, error, latency)

            return result

        except CircuitBreakerOpenError:
            # Circuit is open, try fallback
            if self.config.fallback_function:
                self._log(f"Circuit open, executing fallback")
                return self.config.fallback_function(*args, **kwargs)
            raise

        finally:
            self._release_bulkhead()

    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> T:
        """
        Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            BulkheadFullError: If bulkhead is full
            Exception: Any exception from func
        """
        # Check bulkhead
        if not await self._try_acquire_bulkhead_async():
            raise BulkheadFullError(self.name, self.config.max_concurrent_calls)

        try:
            # Check circuit state
            await self._before_call_async()

            # Execute function with timing
            start_time = time.time()
            error = None
            result = None

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                error = e
                raise
            finally:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                await self._after_call_async(result, error, latency)

            return result

        except CircuitBreakerOpenError:
            # Circuit is open, try fallback
            if self.config.fallback_async_function:
                self._log(f"Circuit open, executing async fallback")
                return await self.config.fallback_async_function(*args, **kwargs)
            raise

        finally:
            await self._release_bulkhead_async()

    @contextmanager
    def context(self):
        """
        Context manager for circuit breaker protection (sync).

        Example:
            ```python
            with cb.context():
                # Protected code
                result = api_call()
            ```
        """
        if not self._try_acquire_bulkhead():
            raise BulkheadFullError(self.name, self.config.max_concurrent_calls)

        try:
            self._before_call()
            start_time = time.time()
            error = None

            try:
                yield
            except Exception as e:
                error = e
                raise
            finally:
                latency = (time.time() - start_time) * 1000
                self._after_call(None, error, latency)

        finally:
            self._release_bulkhead()

    @asynccontextmanager
    async def context_async(self):
        """
        Async context manager for circuit breaker protection.

        Example:
            ```python
            async with cb.context_async():
                # Protected code
                result = await api_call()
            ```
        """
        if not await self._try_acquire_bulkhead_async():
            raise BulkheadFullError(self.name, self.config.max_concurrent_calls)

        try:
            await self._before_call_async()
            start_time = time.time()
            error = None

            try:
                yield
            except Exception as e:
                error = e
                raise
            finally:
                latency = (time.time() - start_time) * 1000
                await self._after_call_async(None, error, latency)

        finally:
            await self._release_bulkhead_async()

    def _before_call(self) -> None:
        """Check circuit state before executing call (sync)"""
        with self._lock:
            # Attempt recovery if timeout expired
            if self._state.current_state == CircuitState.OPEN:
                if self.config.timeout_policy.should_attempt_reset(self._state):
                    self._transition_to_half_open()

            # Reject if circuit is open
            if self._state.current_state == CircuitState.OPEN:
                self._state.record_rejection()
                retry_after = (self._state.state_entered_at + self.config.timeout_policy.get_open_timeout()).isoformat()
                raise CircuitBreakerOpenError(
                    message=f"Circuit breaker '{self.name}' is OPEN. Failure rate: {self._state.get_failure_rate():.2%}. Retry after: {retry_after}",
                    circuit_name=self.name,
                    failure_rate=self._state.get_failure_rate(),
                    retry_after=retry_after
                )

            # In half-open state, limit concurrent requests
            if self._state.current_state == CircuitState.HALF_OPEN:
                if self._state.half_open_attempts >= self.config.half_open_max_calls:
                    retry_after = (self._state.state_entered_at + self.config.timeout_policy.get_open_timeout()).isoformat()
                    raise CircuitBreakerOpenError(
                        message=f"Circuit breaker '{self.name}' is in HALF_OPEN state and at capacity.",
                        circuit_name=self.name,
                        failure_rate=self._state.get_failure_rate(),
                        retry_after=retry_after
                    )
                self._state.half_open_attempts += 1

            self._state.total_requests += 1
            self._state.concurrent_requests += 1
            self._state.max_concurrent_requests_seen = max(
                self._state.max_concurrent_requests_seen,
                self._state.concurrent_requests
            )

    async def _before_call_async(self) -> None:
        """Check circuit state before executing call (async)"""
        async with self._async_lock:
            # Attempt recovery if timeout expired
            if self._state.current_state == CircuitState.OPEN:
                if self.config.timeout_policy.should_attempt_reset(self._state):
                    self._transition_to_half_open()

            # Reject if circuit is open
            if self._state.current_state == CircuitState.OPEN:
                self._state.record_rejection()
                retry_after = (self._state.state_entered_at + self.config.timeout_policy.get_open_timeout()).isoformat()
                raise CircuitBreakerOpenError(
                    message=f"Circuit breaker '{self.name}' is OPEN. Failure rate: {self._state.get_failure_rate():.2%}. Retry after: {retry_after}",
                    circuit_name=self.name,
                    failure_rate=self._state.get_failure_rate(),
                    retry_after=retry_after
                )

            # In half-open state, limit concurrent requests
            if self._state.current_state == CircuitState.HALF_OPEN:
                if self._state.half_open_attempts >= self.config.half_open_max_calls:
                    retry_after = (self._state.state_entered_at + self.config.timeout_policy.get_open_timeout()).isoformat()
                    raise CircuitBreakerOpenError(
                        message=f"Circuit breaker '{self.name}' is in HALF_OPEN state and at capacity.",
                        circuit_name=self.name,
                        failure_rate=self._state.get_failure_rate(),
                        retry_after=retry_after
                    )
                self._state.half_open_attempts += 1

            self._state.total_requests += 1
            self._state.concurrent_requests += 1
            self._state.max_concurrent_requests_seen = max(
                self._state.max_concurrent_requests_seen,
                self._state.concurrent_requests
            )

    def _after_call(self, result: Any, error: Optional[Exception], latency: float) -> None:
        """Process call result and update state (sync)"""
        with self._lock:
            self._state.concurrent_requests -= 1

            # Determine if call was a failure
            is_failure = self.config.is_failure(result, error)

            if is_failure:
                self._state.record_failure(error)
                if self._state.current_state == CircuitState.HALF_OPEN:
                    self._state.half_open_failures += 1
            else:
                self._state.record_success(latency)
                if self._state.current_state == CircuitState.HALF_OPEN:
                    self._state.half_open_successes += 1

            # Check state transitions
            self._check_state_transitions()

            # Update metrics
            if self._metrics:
                self._metrics.update_from_state(self._state)

    async def _after_call_async(self, result: Any, error: Optional[Exception], latency: float) -> None:
        """Process call result and update state (async)"""
        async with self._async_lock:
            self._state.concurrent_requests -= 1

            # Determine if call was a failure
            is_failure = self.config.is_failure(result, error)

            if is_failure:
                self._state.record_failure(error)
                if self._state.current_state == CircuitState.HALF_OPEN:
                    self._state.half_open_failures += 1
            else:
                self._state.record_success(latency)
                if self._state.current_state == CircuitState.HALF_OPEN:
                    self._state.half_open_successes += 1

            # Check state transitions
            self._check_state_transitions()

            # Update metrics
            if self._metrics:
                self._metrics.update_from_state(self._state)

    def _check_state_transitions(self) -> None:
        """Check and execute state transitions based on current state"""
        current = self._state.current_state

        if current == CircuitState.CLOSED:
            # CLOSED → OPEN
            if self.config.failure_policy.should_open(self._state):
                self._transition_to_open()

        elif current == CircuitState.HALF_OPEN:
            # HALF_OPEN → OPEN (failures detected)
            if self._state.half_open_failures > 0:
                self._transition_to_open()
                self.config.timeout_policy.increase_timeout()  # Increase backoff

            # HALF_OPEN → CLOSED (recovery successful)
            elif self.config.failure_policy.should_close(self._state):
                self._transition_to_closed()
                self.config.timeout_policy.reset_timeout()  # Reset backoff

    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        transition = self._state.transition_to(
            CircuitState.OPEN,
            f"Failure threshold exceeded. Failure rate: {self._state.get_failure_rate():.2%}"
        )
        self._log(f"Circuit OPENED: {transition.reason}")
        self._notify_state_change(transition)

        if self.config.on_open:
            self.config.on_open(self._state)

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        transition = self._state.transition_to(
            CircuitState.HALF_OPEN,
            f"Recovery timeout expired. Attempting recovery..."
        )
        self._log(f"Circuit HALF_OPEN: {transition.reason}")
        self._notify_state_change(transition)

        if self.config.on_half_open:
            self.config.on_half_open(self._state)

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        transition = self._state.transition_to(
            CircuitState.CLOSED,
            f"Recovery successful. Success rate: {self._state.get_success_rate():.2%}"
        )
        self._log(f"Circuit CLOSED: {transition.reason}")
        self._notify_state_change(transition)

        if self.config.on_close:
            self.config.on_close(self._state)

    def _notify_state_change(self, transition: StateTransition) -> None:
        """Notify listeners of state change"""
        if self.config.on_state_change:
            self.config.on_state_change(transition)

    def _try_acquire_bulkhead(self) -> bool:
        """Try to acquire bulkhead semaphore (sync)"""
        if self._semaphore is None:
            return True
        return self._semaphore.acquire(blocking=False)

    async def _try_acquire_bulkhead_async(self) -> bool:
        """Try to acquire bulkhead semaphore (async)"""
        if self._async_semaphore is None:
            return True
        try:
            self._async_semaphore.acquire_nowait()
            return True
        except:
            return False

    def _release_bulkhead(self) -> None:
        """Release bulkhead semaphore (sync)"""
        if self._semaphore:
            self._semaphore.release()

    async def _release_bulkhead_async(self) -> None:
        """Release bulkhead semaphore (async)"""
        if self._async_semaphore:
            self._async_semaphore.release()

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled"""
        if self.config.verbose:
            print(f"[CircuitBreaker:{self.name}] {message}")

    # Public API for state inspection and control

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state.current_state

    def get_metrics(self) -> Optional[CircuitBreakerMetrics]:
        """Get circuit breaker metrics"""
        if self._metrics:
            self._metrics.update_from_state(self._state)
        return self._metrics

    def get_state_data(self) -> Dict[str, Any]:
        """Get detailed state information"""
        return self._state.to_dict()

    def force_open(self) -> None:
        """Manually force circuit to OPEN state"""
        with self._lock:
            if self._state.current_state != CircuitState.OPEN:
                self._transition_to_open()

    def force_close(self) -> None:
        """Manually force circuit to CLOSED state (use with caution)"""
        with self._lock:
            if self._state.current_state != CircuitState.CLOSED:
                self._state.reset()
                self._transition_to_closed()

    def reset(self) -> None:
        """Reset circuit breaker to initial state"""
        with self._lock:
            self._state = CircuitStateData(current_state=CircuitState.CLOSED)
            self.config.timeout_policy.reset_timeout()
            self._log("Circuit breaker reset to CLOSED state")


# Decorator for easy circuit breaker application
def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> Callable:
    """
    Decorator to wrap functions with circuit breaker protection.

    Example:
        ```python
        @circuit_breaker(name="my_api", config=CircuitBreakerConfig(failure_threshold=3))
        def call_api():
            return requests.get("https://api.example.com/data")
        ```
    """
    cb = CircuitBreaker(name=name, config=config)

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await cb.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return cb.call(func, *args, **kwargs)
            return sync_wrapper

    return decorator

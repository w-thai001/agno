"""
Circuit Breaker FSA - Core Implementation

This module implements the core Circuit Breaker Finite State Automaton with
three states (CLOSED, OPEN, HALF_OPEN) and comprehensive failure handling.
"""

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple, Union
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class CircuitOpenError(Exception):
    """Raised when a request is attempted while the circuit is open."""

    def __init__(self, message: str = "Circuit breaker is OPEN", last_failure_time: Optional[datetime] = None):
        self.last_failure_time = last_failure_time
        super().__init__(message)


class FallbackFailedError(Exception):
    """Raised when the fallback mechanism fails."""

    def __init__(self, message: str = "Fallback execution failed", original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message)


class ConfigurationError(Exception):
    """Raised when the circuit breaker configuration is invalid."""
    pass


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, message: str, from_state: Optional['CircuitState'] = None, to_state: Optional['CircuitState'] = None):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(message)


# ============================================================================
# Enums
# ============================================================================


class CircuitState(Enum):
    """
    Circuit Breaker States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast
    - HALF_OPEN: Testing recovery, limited probe requests allowed
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __str__(self) -> str:
        return self.value.upper()


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class CircuitBreakerConfig:
    """Configuration for Circuit Breaker FSA."""

    # Failure thresholds
    failure_threshold: int = 5  # Number of failures before opening
    failure_rate_threshold: float = 0.5  # Percentage threshold (0.0-1.0)
    consecutive_failure_threshold: int = 3  # Consecutive failures

    # Timing
    timeout: float = 60.0  # Timeout before transitioning to HALF_OPEN (seconds)
    half_open_timeout: float = 30.0  # Timeout in HALF_OPEN state

    # Half-open probing
    half_open_max_calls: int = 3  # Number of probe calls in HALF_OPEN
    half_open_success_threshold: int = 2  # Successes needed to close

    # Windows
    rolling_window_size: int = 100  # Size of rolling window for metrics
    time_window_seconds: float = 60.0  # Time window for rate calculations

    # Latency thresholds
    slow_call_duration_threshold: float = 5.0  # Slow call threshold (seconds)
    slow_call_rate_threshold: float = 0.5  # Percentage of slow calls to trigger

    # Recovery
    enable_exponential_backoff: bool = True
    max_backoff_time: float = 300.0  # Maximum backoff time (seconds)
    backoff_multiplier: float = 2.0

    # Monitoring
    enable_metrics: bool = True
    enable_health_checks: bool = True
    health_check_interval: float = 10.0  # Health check interval (seconds)

    # Advanced
    enable_bulkhead: bool = False
    max_concurrent_calls: int = 10
    queue_size: int = 100

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.failure_threshold < 1:
            raise ConfigurationError("failure_threshold must be >= 1")
        if not 0.0 <= self.failure_rate_threshold <= 1.0:
            raise ConfigurationError("failure_rate_threshold must be between 0.0 and 1.0")
        if self.timeout < 0:
            raise ConfigurationError("timeout must be >= 0")
        if self.half_open_max_calls < 1:
            raise ConfigurationError("half_open_max_calls must be >= 1")
        if self.rolling_window_size < 1:
            raise ConfigurationError("rolling_window_size must be >= 1")


@dataclass
class CircuitMetrics:
    """Metrics collected by the Circuit Breaker."""

    state: CircuitState
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0

    # Timing
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0

    # State transitions
    state_transitions: int = 0
    last_state_change: Optional[datetime] = None
    time_in_state_seconds: float = 0.0

    # Failure rates
    failure_rate: float = 0.0
    success_rate: float = 0.0
    slow_call_rate: float = 0.0

    # Half-open specific
    half_open_calls: int = 0
    half_open_successes: int = 0
    half_open_failures: int = 0

    # Recovery
    recovery_attempts: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0

    # Timestamps
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_rejection_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "state": self.state.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "average_latency_ms": self.average_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "state_transitions": self.state_transitions,
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
            "time_in_state_seconds": self.time_in_state_seconds,
            "failure_rate": self.failure_rate,
            "success_rate": self.success_rate,
            "slow_call_rate": self.slow_call_rate,
            "half_open_calls": self.half_open_calls,
            "half_open_successes": self.half_open_successes,
            "half_open_failures": self.half_open_failures,
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_rejection_time": self.last_rejection_time.isoformat() if self.last_rejection_time else None,
        }


@dataclass
class HealthStatus:
    """Health status of the circuit breaker."""

    is_healthy: bool
    state: CircuitState
    uptime_seconds: float
    error_message: Optional[str] = None
    last_check_time: Optional[datetime] = None
    consecutive_failures: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "state": self.state.value,
            "uptime_seconds": self.uptime_seconds,
            "error_message": self.error_message,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class RequestRecord:
    """Record of a single request."""

    timestamp: datetime
    duration_ms: float
    success: bool
    error: Optional[Exception] = None

    def is_slow(self, threshold_ms: float) -> bool:
        """Check if request was slow."""
        return self.duration_ms > threshold_ms


# ============================================================================
# Circuit Breaker FSA
# ============================================================================


class CircuitBreakerFSA:
    """
    Comprehensive Circuit Breaker Finite State Automaton.

    This implementation provides:
    - Three-state FSA: CLOSED, OPEN, HALF_OPEN
    - Multiple failure detection strategies
    - Automatic recovery with configurable strategies
    - Fallback mechanisms
    - Comprehensive metrics and monitoring
    - Thread-safe operations
    - Bulkhead isolation
    - Health check probing

    Example:
        >>> config = CircuitBreakerConfig(failure_threshold=5, timeout=60.0)
        >>> cb = CircuitBreakerFSA(config=config, name="api_service")
        >>>
        >>> def api_call():
        ...     return requests.get("https://api.example.com/data")
        >>>
        >>> try:
        ...     result = cb.execute(api_call)
        ... except CircuitOpenError:
        ...     result = get_cached_data()  # Fallback
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        name: str = "circuit_breaker",
        failure_detector: Optional['FailureDetector'] = None,
        recovery_strategy: Optional['RecoveryStrategy'] = None,
        fallback_strategy: Optional['FallbackStrategy'] = None,
    ):
        """
        Initialize Circuit Breaker FSA.

        Args:
            config: Configuration for the circuit breaker
            name: Name identifier for this circuit breaker
            failure_detector: Custom failure detection strategy
            recovery_strategy: Custom recovery strategy
            fallback_strategy: Custom fallback strategy
        """
        self.config = config or CircuitBreakerConfig()
        self.config.validate()
        self.name = name

        # State management
        self._state = CircuitState.CLOSED
        self._state_lock = threading.RLock()
        self._state_change_time = datetime.now()

        # Metrics
        self._metrics = CircuitMetrics(state=self._state)
        self._request_history: Deque[RequestRecord] = deque(maxlen=self.config.rolling_window_size)

        # Failure tracking
        self._consecutive_failures = 0
        self._failure_count_in_window = 0
        self._last_failure_time: Optional[datetime] = None

        # Half-open tracking
        self._half_open_calls = 0
        self._half_open_successes = 0

        # Recovery tracking
        self._backoff_count = 0
        self._next_attempt_time: Optional[datetime] = None

        # Event listeners
        self._state_change_listeners: List[Callable[[CircuitState, CircuitState], None]] = []
        self._failure_listeners: List[Callable[[Exception], None]] = []
        self._success_listeners: List[Callable[[], None]] = []

        # Strategies (to be injected)
        self._failure_detector = failure_detector
        self._recovery_strategy = recovery_strategy
        self._fallback_strategy = fallback_strategy

        # Bulkhead
        self._concurrent_calls = 0
        self._concurrent_calls_lock = threading.Lock()
        self._queue: Deque[Any] = deque(maxlen=self.config.queue_size)

        # Health check
        self._start_time = datetime.now()
        self._health_check_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Start health check if enabled
        if self.config.enable_health_checks:
            self._start_health_check_thread()

        logger.info(f"Circuit Breaker '{self.name}' initialized in {self._state} state")

    # ========================================================================
    # Core State Management
    # ========================================================================

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._state_lock:
            return self._state

    def _transition_to(self, new_state: CircuitState, reason: str = "") -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state
            reason: Reason for transition

        Raises:
            StateTransitionError: If transition is invalid
        """
        with self._state_lock:
            old_state = self._state

            # Validate transition
            if not self._is_valid_transition(old_state, new_state):
                raise StateTransitionError(
                    f"Invalid transition from {old_state} to {new_state}",
                    from_state=old_state,
                    to_state=new_state
                )

            # Update state
            self._state = new_state
            self._state_change_time = datetime.now()
            self._metrics.state = new_state
            self._metrics.state_transitions += 1
            self._metrics.last_state_change = self._state_change_time

            # Reset state-specific counters
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
                self._half_open_successes = 0
            elif new_state == CircuitState.CLOSED:
                self._consecutive_failures = 0
                self._failure_count_in_window = 0
                self._backoff_count = 0
                self._next_attempt_time = None

            logger.info(f"Circuit Breaker '{self.name}': {old_state} -> {new_state}" + (f" ({reason})" if reason else ""))

            # Notify listeners
            self._notify_state_change_listeners(old_state, new_state)

    def _is_valid_transition(self, from_state: CircuitState, to_state: CircuitState) -> bool:
        """
        Check if state transition is valid.

        Valid transitions:
        - CLOSED -> OPEN
        - OPEN -> HALF_OPEN
        - HALF_OPEN -> CLOSED
        - HALF_OPEN -> OPEN
        - Any state -> same state (no-op)
        """
        if from_state == to_state:
            return True

        valid_transitions = {
            CircuitState.CLOSED: {CircuitState.OPEN},
            CircuitState.OPEN: {CircuitState.HALF_OPEN},
            CircuitState.HALF_OPEN: {CircuitState.CLOSED, CircuitState.OPEN},
        }

        return to_state in valid_transitions.get(from_state, set())

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset (OPEN -> HALF_OPEN)."""
        if self._state != CircuitState.OPEN:
            return False

        if self._next_attempt_time is not None:
            return datetime.now() >= self._next_attempt_time

        time_in_open = (datetime.now() - self._state_change_time).total_seconds()
        return time_in_open >= self.config.timeout

    def _calculate_next_attempt_time(self) -> datetime:
        """Calculate next attempt time with exponential backoff."""
        if not self.config.enable_exponential_backoff:
            return datetime.now() + timedelta(seconds=self.config.timeout)

        backoff_time = min(
            self.config.timeout * (self.config.backoff_multiplier ** self._backoff_count),
            self.config.max_backoff_time
        )
        return datetime.now() + timedelta(seconds=backoff_time)

    # ========================================================================
    # Request Execution
    # ========================================================================

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            CircuitOpenError: If circuit is OPEN
            FallbackFailedError: If execution and fallback both fail
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            try:
                self._transition_to(CircuitState.HALF_OPEN, "timeout expired")
            except StateTransitionError as e:
                logger.warning(f"Failed to transition to HALF_OPEN: {e}")

        # Check current state
        current_state = self.get_state()

        if current_state == CircuitState.OPEN:
            self._metrics.rejected_requests += 1
            self._metrics.last_rejection_time = datetime.now()

            # Try fallback if available
            if self._fallback_strategy:
                try:
                    return self._fallback_strategy.execute(func, *args, **kwargs)
                except Exception as e:
                    raise FallbackFailedError("Circuit is OPEN and fallback failed", original_error=e)

            raise CircuitOpenError("Circuit breaker is OPEN", last_failure_time=self._last_failure_time)

        if current_state == CircuitState.HALF_OPEN:
            # Check if we've exceeded half-open call limit
            with self._state_lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self._metrics.rejected_requests += 1
                    self._metrics.last_rejection_time = datetime.now()

                    if self._fallback_strategy:
                        try:
                            return self._fallback_strategy.execute(func, *args, **kwargs)
                        except Exception as e:
                            raise FallbackFailedError("Circuit is HALF_OPEN (probe limit) and fallback failed", original_error=e)

                    raise CircuitOpenError("Circuit breaker is HALF_OPEN (probe limit reached)")

                self._half_open_calls += 1
                self._metrics.half_open_calls += 1

        # Bulkhead check
        if self.config.enable_bulkhead:
            with self._concurrent_calls_lock:
                if self._concurrent_calls >= self.config.max_concurrent_calls:
                    self._metrics.rejected_requests += 1
                    raise CircuitOpenError("Bulkhead limit reached")
                self._concurrent_calls += 1

        # Execute request
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Record success
            self._record_success(duration_ms)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Record failure
            self._record_failure(e, duration_ms)

            # Try fallback if available
            if self._fallback_strategy:
                try:
                    return self._fallback_strategy.execute(func, *args, **kwargs)
                except Exception as fallback_error:
                    raise FallbackFailedError(
                        f"Execution failed and fallback failed: {fallback_error}",
                        original_error=e
                    )

            raise

        finally:
            # Release bulkhead
            if self.config.enable_bulkhead:
                with self._concurrent_calls_lock:
                    self._concurrent_calls -= 1

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            CircuitOpenError: If circuit is OPEN
            FallbackFailedError: If execution and fallback both fail
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            try:
                self._transition_to(CircuitState.HALF_OPEN, "timeout expired")
            except StateTransitionError as e:
                logger.warning(f"Failed to transition to HALF_OPEN: {e}")

        # Check current state
        current_state = self.get_state()

        if current_state == CircuitState.OPEN:
            self._metrics.rejected_requests += 1
            self._metrics.last_rejection_time = datetime.now()

            if self._fallback_strategy:
                try:
                    return await self._fallback_strategy.execute_async(func, *args, **kwargs)
                except Exception as e:
                    raise FallbackFailedError("Circuit is OPEN and fallback failed", original_error=e)

            raise CircuitOpenError("Circuit breaker is OPEN", last_failure_time=self._last_failure_time)

        if current_state == CircuitState.HALF_OPEN:
            with self._state_lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self._metrics.rejected_requests += 1
                    self._metrics.last_rejection_time = datetime.now()

                    if self._fallback_strategy:
                        try:
                            return await self._fallback_strategy.execute_async(func, *args, **kwargs)
                        except Exception as e:
                            raise FallbackFailedError("Circuit is HALF_OPEN and fallback failed", original_error=e)

                    raise CircuitOpenError("Circuit breaker is HALF_OPEN (probe limit reached)")

                self._half_open_calls += 1
                self._metrics.half_open_calls += 1

        # Bulkhead check
        if self.config.enable_bulkhead:
            with self._concurrent_calls_lock:
                if self._concurrent_calls >= self.config.max_concurrent_calls:
                    self._metrics.rejected_requests += 1
                    raise CircuitOpenError("Bulkhead limit reached")
                self._concurrent_calls += 1

        # Execute request
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            self._record_success(duration_ms)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._record_failure(e, duration_ms)

            if self._fallback_strategy:
                try:
                    return await self._fallback_strategy.execute_async(func, *args, **kwargs)
                except Exception as fallback_error:
                    raise FallbackFailedError(
                        f"Execution failed and fallback failed: {fallback_error}",
                        original_error=e
                    )

            raise

        finally:
            if self.config.enable_bulkhead:
                with self._concurrent_calls_lock:
                    self._concurrent_calls -= 1

    # ========================================================================
    # Recording Results
    # ========================================================================

    def _record_success(self, duration_ms: float) -> None:
        """Record a successful request."""
        with self._state_lock:
            # Update metrics
            self._metrics.total_requests += 1
            self._metrics.successful_requests += 1
            self._metrics.last_success_time = datetime.now()

            # Add to history
            record = RequestRecord(
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                success=True
            )
            self._request_history.append(record)

            # Update latency metrics
            self._update_latency_metrics(duration_ms)

            # Reset consecutive failures
            self._consecutive_failures = 0

            # Handle state-specific logic
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                self._metrics.half_open_successes += 1

                # Check if we should close the circuit
                if self._half_open_successes >= self.config.half_open_success_threshold:
                    self._transition_to(CircuitState.CLOSED, "recovery successful")
                    self._metrics.successful_recoveries += 1

            # Notify listeners
            self._notify_success_listeners()

    def _record_failure(self, error: Exception, duration_ms: float) -> None:
        """Record a failed request."""
        with self._state_lock:
            # Update metrics
            self._metrics.total_requests += 1
            self._metrics.failed_requests += 1
            self._metrics.last_failure_time = datetime.now()
            self._last_failure_time = self._metrics.last_failure_time

            # Add to history
            record = RequestRecord(
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                success=False,
                error=error
            )
            self._request_history.append(record)

            # Update latency metrics
            self._update_latency_metrics(duration_ms)

            # Update failure counts
            self._consecutive_failures += 1
            self._failure_count_in_window += 1

            # Calculate failure rate
            self._update_failure_rate()

            # Check if we should open the circuit
            if self._state == CircuitState.CLOSED:
                if self._should_open_circuit():
                    self._transition_to(CircuitState.OPEN, "failure threshold exceeded")
                    self._backoff_count = 0
                    self._next_attempt_time = self._calculate_next_attempt_time()

            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN reopens the circuit
                self._metrics.half_open_failures += 1
                self._transition_to(CircuitState.OPEN, "half-open probe failed")
                self._backoff_count += 1
                self._next_attempt_time = self._calculate_next_attempt_time()
                self._metrics.failed_recoveries += 1

            # Notify listeners
            self._notify_failure_listeners(error)

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open based on failure detection."""
        # Use custom failure detector if provided
        if self._failure_detector:
            return self._failure_detector.should_open(self._request_history, self.config)

        # Default failure detection: check multiple conditions

        # 1. Consecutive failures
        if self._consecutive_failures >= self.config.consecutive_failure_threshold:
            logger.info(f"Circuit '{self.name}': Consecutive failure threshold reached ({self._consecutive_failures})")
            return True

        # 2. Failure count in window
        if self._failure_count_in_window >= self.config.failure_threshold:
            logger.info(f"Circuit '{self.name}': Failure count threshold reached ({self._failure_count_in_window})")
            return True

        # 3. Failure rate
        if self._metrics.failure_rate >= self.config.failure_rate_threshold:
            logger.info(f"Circuit '{self.name}': Failure rate threshold reached ({self._metrics.failure_rate:.2%})")
            return True

        return False

    def _update_failure_rate(self) -> None:
        """Update failure rate metrics."""
        if not self._request_history:
            return

        # Calculate failure rate in rolling window
        total = len(self._request_history)
        failures = sum(1 for r in self._request_history if not r.success)

        self._metrics.failure_rate = failures / total if total > 0 else 0.0
        self._metrics.success_rate = 1.0 - self._metrics.failure_rate

        # Calculate slow call rate
        slow_threshold_ms = self.config.slow_call_duration_threshold * 1000
        slow_calls = sum(1 for r in self._request_history if r.is_slow(slow_threshold_ms))
        self._metrics.slow_call_rate = slow_calls / total if total > 0 else 0.0

    def _update_latency_metrics(self, duration_ms: float) -> None:
        """Update latency metrics."""
        if self._metrics.total_requests == 1:
            self._metrics.average_latency_ms = duration_ms
            self._metrics.max_latency_ms = duration_ms
            self._metrics.min_latency_ms = duration_ms
        else:
            # Update running average
            n = self._metrics.total_requests
            self._metrics.average_latency_ms = (
                (self._metrics.average_latency_ms * (n - 1) + duration_ms) / n
            )
            self._metrics.max_latency_ms = max(self._metrics.max_latency_ms, duration_ms)
            self._metrics.min_latency_ms = min(self._metrics.min_latency_ms, duration_ms)

    # ========================================================================
    # Manual Control
    # ========================================================================

    def force_open(self) -> None:
        """Force the circuit to OPEN state."""
        with self._state_lock:
            if self._state != CircuitState.OPEN:
                self._transition_to(CircuitState.OPEN, "manually forced")

    def force_close(self) -> None:
        """Force the circuit to CLOSED state."""
        with self._state_lock:
            if self._state != CircuitState.CLOSED:
                self._transition_to(CircuitState.CLOSED, "manually forced")

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        with self._state_lock:
            self._state = CircuitState.CLOSED
            self._state_change_time = datetime.now()
            self._consecutive_failures = 0
            self._failure_count_in_window = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._backoff_count = 0
            self._next_attempt_time = None
            self._request_history.clear()

            # Reset metrics
            self._metrics = CircuitMetrics(state=self._state)

            logger.info(f"Circuit Breaker '{self.name}' reset to CLOSED state")

    # ========================================================================
    # Metrics and Monitoring
    # ========================================================================

    def get_metrics(self) -> CircuitMetrics:
        """Get current metrics."""
        with self._state_lock:
            # Update time in state
            self._metrics.time_in_state_seconds = (
                datetime.now() - self._state_change_time
            ).total_seconds()
            return self._metrics

    def health_check(self) -> HealthStatus:
        """Perform health check and return status."""
        with self._state_lock:
            uptime = (datetime.now() - self._start_time).total_seconds()
            is_healthy = self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

            error_message = None
            if self._state == CircuitState.OPEN:
                error_message = f"Circuit is OPEN. Last failure: {self._last_failure_time}"

            return HealthStatus(
                is_healthy=is_healthy,
                state=self._state,
                uptime_seconds=uptime,
                error_message=error_message,
                last_check_time=datetime.now(),
                consecutive_failures=self._consecutive_failures
            )

    def _start_health_check_thread(self) -> None:
        """Start background health check thread."""
        def health_check_loop():
            while not self._shutdown_event.is_set():
                try:
                    status = self.health_check()
                    if not status.is_healthy:
                        logger.warning(f"Circuit '{self.name}' health check: {status.error_message}")
                except Exception as e:
                    logger.error(f"Health check error for circuit '{self.name}': {e}")

                self._shutdown_event.wait(self.config.health_check_interval)

        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True,
            name=f"CircuitBreaker-{self.name}-HealthCheck"
        )
        self._health_check_thread.start()

    # ========================================================================
    # Event Listeners
    # ========================================================================

    def add_state_change_listener(self, listener: Callable[[CircuitState, CircuitState], None]) -> None:
        """Add a listener for state changes."""
        self._state_change_listeners.append(listener)

    def add_failure_listener(self, listener: Callable[[Exception], None]) -> None:
        """Add a listener for failures."""
        self._failure_listeners.append(listener)

    def add_success_listener(self, listener: Callable[[], None]) -> None:
        """Add a listener for successes."""
        self._success_listeners.append(listener)

    def _notify_state_change_listeners(self, old_state: CircuitState, new_state: CircuitState) -> None:
        """Notify all state change listeners."""
        for listener in self._state_change_listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change listener: {e}")

    def _notify_failure_listeners(self, error: Exception) -> None:
        """Notify all failure listeners."""
        for listener in self._failure_listeners:
            try:
                listener(error)
            except Exception as e:
                logger.error(f"Error in failure listener: {e}")

    def _notify_success_listeners(self) -> None:
        """Notify all success listeners."""
        for listener in self._success_listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"Error in success listener: {e}")

    # ========================================================================
    # Configuration and Strategies
    # ========================================================================

    def configure(self, config: CircuitBreakerConfig) -> None:
        """Update configuration."""
        config.validate()
        with self._state_lock:
            self.config = config
            logger.info(f"Circuit Breaker '{self.name}' configuration updated")

    def set_failure_detector(self, detector: 'FailureDetector') -> None:
        """Set custom failure detector."""
        self._failure_detector = detector

    def set_recovery_strategy(self, strategy: 'RecoveryStrategy') -> None:
        """Set custom recovery strategy."""
        self._recovery_strategy = strategy

    def set_fallback(self, strategy: 'FallbackStrategy') -> None:
        """Set fallback strategy."""
        self._fallback_strategy = strategy

    # ========================================================================
    # Cleanup
    # ========================================================================

    def shutdown(self) -> None:
        """Shutdown the circuit breaker and cleanup resources."""
        logger.info(f"Shutting down Circuit Breaker '{self.name}'")
        self._shutdown_event.set()

        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"CircuitBreakerFSA(name='{self.name}', state={self._state}, "
            f"failures={self._metrics.failed_requests}, "
            f"successes={self._metrics.successful_requests})"
        )


# ============================================================================
# Decorator
# ============================================================================


def circuit_breaker(
    config: Optional[CircuitBreakerConfig] = None,
    name: Optional[str] = None,
    failure_detector: Optional['FailureDetector'] = None,
    recovery_strategy: Optional['RecoveryStrategy'] = None,
    fallback_strategy: Optional['FallbackStrategy'] = None,
):
    """
    Decorator to wrap a function with a circuit breaker.

    Example:
        >>> @circuit_breaker(
        ...     config=CircuitBreakerConfig(failure_threshold=5),
        ...     name="api_call"
        ... )
        ... def call_api():
        ...     return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        cb = CircuitBreakerFSA(
            config=config,
            name=func_name,
            failure_detector=failure_detector,
            recovery_strategy=recovery_strategy,
            fallback_strategy=fallback_strategy,
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.execute(func, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cb.execute_async(func, *args, **kwargs)

        # Return appropriate wrapper based on whether func is async
        if asyncio.iscoroutinefunction(func):
            async_wrapper._circuit_breaker = cb
            return async_wrapper
        else:
            wrapper._circuit_breaker = cb
            return wrapper

    return decorator

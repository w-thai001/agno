"""
Circuit Breaker Failure Detection Policies

This module defines policies for determining when a circuit should open, close,
or transition to half-open state. Policies can be combined for sophisticated
failure detection strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any, List
from datetime import datetime, timedelta

from agno.resilience.states import CircuitStateData


class FailurePolicy(ABC):
    """Base class for failure detection policies"""

    @abstractmethod
    def should_open(self, state: CircuitStateData) -> bool:
        """Determine if the circuit should open based on current state"""
        pass

    @abstractmethod
    def should_close(self, state: CircuitStateData) -> bool:
        """Determine if the circuit should close from half-open state"""
        pass


@dataclass
class ConsecutiveFailurePolicy(FailurePolicy):
    """
    Opens circuit after N consecutive failures.

    This is the simplest policy - useful for protecting against
    cascading failures and giving downstream services time to recover.
    """
    threshold: int = 5

    def should_open(self, state: CircuitStateData) -> bool:
        return state.consecutive_failures >= self.threshold

    def should_close(self, state: CircuitStateData) -> bool:
        # In half-open state, require successful probes
        return state.half_open_successes > 0 and state.half_open_failures == 0


@dataclass
class FailureRatePolicy(FailurePolicy):
    """
    Opens circuit when failure rate exceeds threshold over a time window.

    More sophisticated than consecutive failures - accounts for intermittent
    successes but still detects degraded service quality.
    """
    threshold: float = 0.5  # 50% failure rate
    window_seconds: int = 60  # 60 second window
    minimum_requests: int = 10  # Require minimum sample size

    def should_open(self, state: CircuitStateData) -> bool:
        # Need minimum requests before making a decision
        recent_calls = [
            call for call in state.recent_calls
            if (datetime.utcnow() - call['timestamp']).total_seconds() <= self.window_seconds
        ]

        if len(recent_calls) < self.minimum_requests:
            return False

        failure_rate = state.get_failure_rate(self.window_seconds)
        return failure_rate >= self.threshold

    def should_close(self, state: CircuitStateData) -> bool:
        # Require low failure rate in half-open state
        if state.half_open_attempts < 3:
            return False

        failure_rate = state.half_open_failures / state.half_open_attempts if state.half_open_attempts > 0 else 0
        return failure_rate < (self.threshold * 0.5)  # 50% better than threshold


@dataclass
class LatencyPolicy(FailurePolicy):
    """
    Opens circuit when latency exceeds threshold.

    Protects against slow but not failing services that could cause
    timeout cascades.
    """
    p95_threshold_ms: float = 1000.0  # 1 second
    p99_threshold_ms: float = 2000.0  # 2 seconds
    consecutive_violations: int = 3

    def __init__(self, p95_threshold_ms: float = 1000.0, p99_threshold_ms: float = 2000.0, consecutive_violations: int = 3):
        self.p95_threshold_ms = p95_threshold_ms
        self.p99_threshold_ms = p99_threshold_ms
        self.consecutive_violations = consecutive_violations
        self._violation_count = 0

    def should_open(self, state: CircuitStateData) -> bool:
        if not state.recent_latencies:
            return False

        # Check if latency exceeds thresholds
        if state.p95_latency > self.p95_threshold_ms or state.p99_latency > self.p99_threshold_ms:
            self._violation_count += 1
        else:
            self._violation_count = 0

        return self._violation_count >= self.consecutive_violations

    def should_close(self, state: CircuitStateData) -> bool:
        if state.half_open_attempts < 3:
            return False

        # Latency should be back to normal
        return state.p95_latency < self.p95_threshold_ms and state.p99_latency < self.p99_threshold_ms


@dataclass
class CompositePolicy(FailurePolicy):
    """
    Combines multiple policies with AND/OR logic.

    Allows building sophisticated failure detection strategies.
    """
    policies: List[FailurePolicy]
    require_all: bool = False  # True = AND, False = OR

    def should_open(self, state: CircuitStateData) -> bool:
        if self.require_all:
            return all(policy.should_open(state) for policy in self.policies)
        else:
            return any(policy.should_open(state) for policy in self.policies)

    def should_close(self, state: CircuitStateData) -> bool:
        if self.require_all:
            return all(policy.should_close(state) for policy in self.policies)
        else:
            return any(policy.should_close(state) for policy in self.policies)


@dataclass
class CustomPredicatePolicy(FailurePolicy):
    """
    Uses custom predicates to determine circuit state.

    Allows users to define their own failure conditions beyond
    standard HTTP status codes.
    """
    should_open_predicate: Callable[[CircuitStateData], bool]
    should_close_predicate: Callable[[CircuitStateData], bool]

    def should_open(self, state: CircuitStateData) -> bool:
        return self.should_open_predicate(state)

    def should_close(self, state: CircuitStateData) -> bool:
        return self.should_close_predicate(state)


@dataclass
class TimeoutPolicy:
    """
    Defines timeout behavior for the circuit breaker.

    Controls how long the circuit stays open before attempting recovery.
    """
    # Base timeout before attempting half-open
    open_timeout_seconds: float = 60.0

    # Adaptive timeout multiplier (increases on repeated failures)
    adaptive_multiplier: float = 1.5
    max_timeout_seconds: float = 300.0  # 5 minutes max

    # Half-open timeout
    half_open_timeout_seconds: float = 30.0

    # Track timeout multiplier
    _current_multiplier: float = 1.0

    def get_open_timeout(self) -> timedelta:
        """Get current timeout before transitioning to half-open"""
        timeout = min(
            self.open_timeout_seconds * self._current_multiplier,
            self.max_timeout_seconds
        )
        return timedelta(seconds=timeout)

    def increase_timeout(self) -> None:
        """Increase timeout after failed recovery attempt"""
        self._current_multiplier *= self.adaptive_multiplier

    def reset_timeout(self) -> None:
        """Reset timeout after successful recovery"""
        self._current_multiplier = 1.0

    def should_attempt_reset(self, state: CircuitStateData) -> bool:
        """Check if enough time has passed to attempt reset"""
        if state.current_state.value != 'open':
            return False

        time_in_open = datetime.utcnow() - state.state_entered_at
        return time_in_open >= self.get_open_timeout()


@dataclass
class HealthCheckConfig:
    """
    Configuration for active health check probes.

    Health checks actively probe the service during half-open state
    to determine if it has recovered.
    """
    # Enable active health checks
    enabled: bool = False

    # Number of probe requests in half-open state
    probe_requests: int = 3

    # Success rate required to close circuit
    required_success_rate: float = 1.0  # 100% by default

    # Custom health check function
    health_check_function: Optional[Callable[[], bool]] = None

    # Timeout for health check probe
    probe_timeout_seconds: float = 5.0

    def should_close_circuit(self, successes: int, failures: int) -> bool:
        """Determine if circuit should close based on probe results"""
        total = successes + failures
        if total < self.probe_requests:
            return False

        success_rate = successes / total
        return success_rate >= self.required_success_rate


# Predefined policy templates for common use cases
def create_aggressive_policy() -> FailurePolicy:
    """Fast circuit opening for critical services"""
    return ConsecutiveFailurePolicy(threshold=3)


def create_balanced_policy() -> FailurePolicy:
    """Balanced approach suitable for most services"""
    return CompositePolicy(
        policies=[
            ConsecutiveFailurePolicy(threshold=5),
            FailureRatePolicy(threshold=0.5, window_seconds=60, minimum_requests=10)
        ],
        require_all=False  # OR logic
    )


def create_conservative_policy() -> FailurePolicy:
    """More tolerant policy for unstable services"""
    return FailureRatePolicy(
        threshold=0.7,  # 70% failure rate
        window_seconds=120,
        minimum_requests=20
    )


def create_latency_aware_policy(p95_threshold_ms: float = 1000.0) -> FailurePolicy:
    """Policy that considers both failures and latency"""
    return CompositePolicy(
        policies=[
            FailureRatePolicy(threshold=0.5, window_seconds=60, minimum_requests=10),
            LatencyPolicy(p95_threshold_ms=p95_threshold_ms, consecutive_violations=3)
        ],
        require_all=False  # OR logic - either condition triggers opening
    )

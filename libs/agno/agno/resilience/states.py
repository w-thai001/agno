"""
Circuit Breaker State Definitions

This module defines the states for the Circuit Breaker Finite State Automaton (FSA).
The circuit breaker implements the following state machine:

    CLOSED → OPEN → HALF_OPEN → CLOSED
         ↑__________________________|

States:
- CLOSED: Normal operation, requests are allowed
- OPEN: Circuit is tripped, requests are rejected immediately
- HALF_OPEN: Testing recovery, limited requests are allowed
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import deque


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class StateTransition:
    """Records a state transition event"""
    from_state: CircuitState
    to_state: CircuitState
    timestamp: datetime
    reason: str
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class CircuitStateData:
    """
    Tracks the current state and metrics of a circuit breaker.

    This data structure maintains all the information needed to determine
    state transitions and track circuit breaker health.
    """
    # Current state
    current_state: CircuitState = CircuitState.CLOSED

    # Failure tracking
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # Rate tracking (for sliding window)
    recent_calls: deque = field(default_factory=lambda: deque(maxlen=100))

    # Timing
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_entered_at: datetime = field(default_factory=datetime.utcnow)
    last_state_change: datetime = field(default_factory=datetime.utcnow)

    # Half-open state tracking
    half_open_attempts: int = 0
    half_open_successes: int = 0
    half_open_failures: int = 0

    # Latency tracking
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0

    # State transition history
    transition_history: List[StateTransition] = field(default_factory=list)

    # Bulkhead tracking
    concurrent_requests: int = 0
    max_concurrent_requests_seen: int = 0
    total_requests: int = 0
    rejected_requests: int = 0

    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def record_success(self, latency: Optional[float] = None) -> None:
        """Record a successful call"""
        self.success_count += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = datetime.utcnow()
        self.recent_calls.append({
            'success': True,
            'timestamp': datetime.utcnow(),
            'latency': latency
        })
        if latency is not None:
            self.recent_latencies.append(latency)
            self._update_latency_percentiles()

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed call"""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = datetime.utcnow()
        self.recent_calls.append({
            'success': False,
            'timestamp': datetime.utcnow(),
            'error': str(error) if error else None
        })

    def record_rejection(self) -> None:
        """Record a rejected request (circuit open)"""
        self.rejected_requests += 1

    def get_failure_rate(self, window_seconds: Optional[int] = None) -> float:
        """
        Calculate failure rate over the recent window.

        Args:
            window_seconds: Time window to consider (None = all recent calls)

        Returns:
            Failure rate as a float between 0.0 and 1.0
        """
        if not self.recent_calls:
            return 0.0

        now = datetime.utcnow()
        relevant_calls = self.recent_calls

        if window_seconds is not None:
            relevant_calls = [
                call for call in self.recent_calls
                if (now - call['timestamp']).total_seconds() <= window_seconds
            ]

        if not relevant_calls:
            return 0.0

        failures = sum(1 for call in relevant_calls if not call['success'])
        return failures / len(relevant_calls)

    def get_success_rate(self, window_seconds: Optional[int] = None) -> float:
        """Calculate success rate over the recent window"""
        return 1.0 - self.get_failure_rate(window_seconds)

    def _update_latency_percentiles(self) -> None:
        """Update latency percentile metrics"""
        if not self.recent_latencies:
            return

        sorted_latencies = sorted(self.recent_latencies)
        n = len(sorted_latencies)

        self.p50_latency = sorted_latencies[int(n * 0.50)]
        self.p95_latency = sorted_latencies[int(n * 0.95)]
        self.p99_latency = sorted_latencies[int(n * 0.99)]

    def transition_to(self, new_state: CircuitState, reason: str) -> StateTransition:
        """
        Transition to a new state and record the event.

        Args:
            new_state: The state to transition to
            reason: Reason for the transition

        Returns:
            StateTransition event
        """
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            metrics={
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'failure_rate': self.get_failure_rate(),
                'consecutive_failures': self.consecutive_failures
            }
        )

        self.current_state = new_state
        self.state_entered_at = datetime.utcnow()
        self.last_state_change = datetime.utcnow()
        self.transition_history.append(transition)

        # Reset state-specific counters
        if new_state == CircuitState.HALF_OPEN:
            self.half_open_attempts = 0
            self.half_open_successes = 0
            self.half_open_failures = 0

        return transition

    def reset(self) -> None:
        """Reset all counters (useful for manual circuit reset)"""
        self.failure_count = 0
        self.success_count = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.half_open_attempts = 0
        self.half_open_successes = 0
        self.half_open_failures = 0
        self.rejected_requests = 0
        self.recent_calls.clear()
        self.recent_latencies.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Export state data as dictionary"""
        return {
            'current_state': self.current_state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'failure_rate': self.get_failure_rate(),
            'success_rate': self.get_success_rate(),
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'state_entered_at': self.state_entered_at.isoformat(),
            'p50_latency': self.p50_latency,
            'p95_latency': self.p95_latency,
            'p99_latency': self.p99_latency,
            'concurrent_requests': self.concurrent_requests,
            'max_concurrent_requests_seen': self.max_concurrent_requests_seen,
            'total_requests': self.total_requests,
            'rejected_requests': self.rejected_requests,
            'custom_metrics': self.custom_metrics
        }

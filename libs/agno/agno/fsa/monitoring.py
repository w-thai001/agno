"""
Monitoring and Metrics for Circuit Breaker FSA

This module provides comprehensive monitoring, metrics collection,
and alerting capabilities for circuit breakers.
"""

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# State Transition Tracker
# ============================================================================


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: 'CircuitState'
    to_state: 'CircuitState'
    timestamp: datetime
    reason: str
    metadata: Dict[str, Any]


class StateTransitionTracker:
    """
    Tracks circuit breaker state transitions.

    Records all state changes with timestamps and reasons,
    providing historical analysis capabilities.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize state transition tracker.

        Args:
            max_history: Maximum number of transitions to keep
        """
        self.max_history = max_history
        self._transitions: Deque[StateTransition] = deque(maxlen=max_history)
        self._transition_counts: Dict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

        logger.debug(f"Initialized StateTransitionTracker with max_history={max_history}")

    def record_transition(
        self,
        from_state: 'CircuitState',
        to_state: 'CircuitState',
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a state transition.

        Args:
            from_state: Previous state
            to_state: New state
            reason: Reason for transition
            metadata: Additional metadata
        """
        with self._lock:
            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.now(),
                reason=reason,
                metadata=metadata or {}
            )

            self._transitions.append(transition)
            self._transition_counts[(from_state, to_state)] += 1

            logger.info(f"State transition: {from_state} -> {to_state} ({reason})")

    def get_transitions(
        self,
        limit: Optional[int] = None,
        from_state: Optional['CircuitState'] = None,
        to_state: Optional['CircuitState'] = None
    ) -> List[StateTransition]:
        """
        Get transition history.

        Args:
            limit: Maximum number of transitions to return
            from_state: Filter by source state
            to_state: Filter by target state

        Returns:
            List of state transitions
        """
        with self._lock:
            transitions = list(self._transitions)

            # Apply filters
            if from_state:
                transitions = [t for t in transitions if t.from_state == from_state]
            if to_state:
                transitions = [t for t in transitions if t.to_state == to_state]

            # Apply limit
            if limit:
                transitions = transitions[-limit:]

            return transitions

    def get_transition_counts(self) -> Dict[tuple, int]:
        """Get counts of each transition type."""
        with self._lock:
            return dict(self._transition_counts)

    def get_time_in_state(self, state: 'CircuitState') -> float:
        """
        Calculate total time spent in a specific state.

        Args:
            state: State to calculate time for

        Returns:
            Total seconds in state
        """
        with self._lock:
            total_time = 0.0
            current_state_start = None

            for transition in self._transitions:
                if transition.from_state == state and current_state_start:
                    duration = (transition.timestamp - current_state_start).total_seconds()
                    total_time += duration
                    current_state_start = None

                if transition.to_state == state:
                    current_state_start = transition.timestamp

            # Add time in current state
            if current_state_start:
                duration = (datetime.now() - current_state_start).total_seconds()
                total_time += duration

            return total_time

    def get_flapping_rate(self, time_window_seconds: float = 300.0) -> float:
        """
        Calculate flapping rate (rapid state changes).

        Args:
            time_window_seconds: Time window to analyze

        Returns:
            Number of transitions per minute
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
            recent_transitions = [
                t for t in self._transitions
                if t.timestamp >= cutoff_time
            ]

            if not recent_transitions:
                return 0.0

            return len(recent_transitions) / (time_window_seconds / 60.0)

    def clear(self) -> None:
        """Clear transition history."""
        with self._lock:
            self._transitions.clear()
            self._transition_counts.clear()


# ============================================================================
# Failure Rate Calculator
# ============================================================================


class FailureRateCalculator:
    """
    Calculates failure rates over various time windows.

    Provides real-time and historical failure rate analysis.
    """

    def __init__(self):
        """Initialize failure rate calculator."""
        self._request_history: Deque[tuple] = deque(maxlen=10000)
        self._lock = threading.Lock()

    def record_request(self, success: bool, duration_ms: float) -> None:
        """
        Record a request result.

        Args:
            success: Whether request succeeded
            duration_ms: Request duration in milliseconds
        """
        with self._lock:
            self._request_history.append((datetime.now(), success, duration_ms))

    def get_failure_rate(self, time_window_seconds: Optional[float] = None) -> float:
        """
        Calculate failure rate.

        Args:
            time_window_seconds: Time window to analyze (None for all history)

        Returns:
            Failure rate (0.0-1.0)
        """
        with self._lock:
            if not self._request_history:
                return 0.0

            # Filter by time window
            if time_window_seconds:
                cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
                requests = [
                    (ts, success, dur) for ts, success, dur in self._request_history
                    if ts >= cutoff_time
                ]
            else:
                requests = list(self._request_history)

            if not requests:
                return 0.0

            failures = sum(1 for _, success, _ in requests if not success)
            return failures / len(requests)

    def get_success_rate(self, time_window_seconds: Optional[float] = None) -> float:
        """
        Calculate success rate.

        Args:
            time_window_seconds: Time window to analyze

        Returns:
            Success rate (0.0-1.0)
        """
        return 1.0 - self.get_failure_rate(time_window_seconds)

    def get_request_rate(self, time_window_seconds: float = 60.0) -> float:
        """
        Calculate request rate (requests per second).

        Args:
            time_window_seconds: Time window to analyze

        Returns:
            Requests per second
        """
        with self._lock:
            cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
            recent_requests = [
                (ts, success, dur) for ts, success, dur in self._request_history
                if ts >= cutoff_time
            ]

            return len(recent_requests) / time_window_seconds

    def clear(self) -> None:
        """Clear request history."""
        with self._lock:
            self._request_history.clear()


# ============================================================================
# Latency Monitor
# ============================================================================


@dataclass
class LatencyStats:
    """Latency statistics."""
    mean_ms: float
    median_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


class LatencyMonitor:
    """
    Monitors request latency and calculates percentiles.

    Tracks response times and provides detailed latency analysis.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize latency monitor.

        Args:
            window_size: Number of samples to keep
        """
        self.window_size = window_size
        self._latencies: Deque[float] = deque(maxlen=window_size)
        self._lock = threading.Lock()

    def record_latency(self, duration_ms: float) -> None:
        """
        Record a request latency.

        Args:
            duration_ms: Request duration in milliseconds
        """
        with self._lock:
            self._latencies.append(duration_ms)

    def get_latency_stats(self) -> Optional[LatencyStats]:
        """
        Get latency statistics.

        Returns:
            Latency statistics or None if no data
        """
        with self._lock:
            if not self._latencies:
                return None

            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)

            return LatencyStats(
                mean_ms=sum(sorted_latencies) / n,
                median_ms=self._percentile(sorted_latencies, 0.5),
                p50_ms=self._percentile(sorted_latencies, 0.5),
                p95_ms=self._percentile(sorted_latencies, 0.95),
                p99_ms=self._percentile(sorted_latencies, 0.99),
                min_ms=sorted_latencies[0],
                max_ms=sorted_latencies[-1]
            )

    @staticmethod
    def _percentile(sorted_data: List[float], percentile: float) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0

        k = (len(sorted_data) - 1) * percentile
        f = int(k)
        c = f + 1

        if c >= len(sorted_data):
            return sorted_data[-1]

        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def get_slow_call_rate(self, threshold_ms: float) -> float:
        """
        Calculate rate of slow calls.

        Args:
            threshold_ms: Threshold for slow calls

        Returns:
            Slow call rate (0.0-1.0)
        """
        with self._lock:
            if not self._latencies:
                return 0.0

            slow_calls = sum(1 for lat in self._latencies if lat > threshold_ms)
            return slow_calls / len(self._latencies)

    def clear(self) -> None:
        """Clear latency history."""
        with self._lock:
            self._latencies.clear()


# ============================================================================
# Success Rate Tracker
# ============================================================================


class SuccessRateTracker:
    """
    Tracks success rates over time.

    Provides time-series analysis of success rates.
    """

    def __init__(self, bucket_size_seconds: float = 60.0, max_buckets: int = 60):
        """
        Initialize success rate tracker.

        Args:
            bucket_size_seconds: Size of each time bucket
            max_buckets: Maximum number of buckets to keep
        """
        self.bucket_size = bucket_size_seconds
        self.max_buckets = max_buckets

        self._buckets: Dict[int, Dict[str, int]] = {}
        self._lock = threading.Lock()

    def record_result(self, success: bool) -> None:
        """
        Record a request result.

        Args:
            success: Whether request succeeded
        """
        with self._lock:
            bucket_key = self._get_bucket_key()

            if bucket_key not in self._buckets:
                self._buckets[bucket_key] = {"total": 0, "successes": 0}
                self._cleanup_old_buckets()

            self._buckets[bucket_key]["total"] += 1
            if success:
                self._buckets[bucket_key]["successes"] += 1

    def get_success_rate(self, time_window_seconds: Optional[float] = None) -> float:
        """
        Get success rate over time window.

        Args:
            time_window_seconds: Time window to analyze

        Returns:
            Success rate (0.0-1.0)
        """
        with self._lock:
            if not self._buckets:
                return 0.0

            # Calculate number of buckets to include
            if time_window_seconds:
                num_buckets = int(time_window_seconds / self.bucket_size)
            else:
                num_buckets = len(self._buckets)

            # Get recent buckets
            current_bucket = self._get_bucket_key()
            bucket_keys = [
                current_bucket - i
                for i in range(num_buckets)
                if current_bucket - i in self._buckets
            ]

            if not bucket_keys:
                return 0.0

            total = sum(self._buckets[k]["total"] for k in bucket_keys)
            successes = sum(self._buckets[k]["successes"] for k in bucket_keys)

            return successes / total if total > 0 else 0.0

    def _get_bucket_key(self) -> int:
        """Get current bucket key."""
        return int(time.time() / self.bucket_size)

    def _cleanup_old_buckets(self) -> None:
        """Remove old buckets beyond max_buckets."""
        if len(self._buckets) > self.max_buckets:
            current_bucket = self._get_bucket_key()
            cutoff_bucket = current_bucket - self.max_buckets

            keys_to_remove = [k for k in self._buckets.keys() if k < cutoff_bucket]
            for key in keys_to_remove:
                del self._buckets[key]

    def clear(self) -> None:
        """Clear all buckets."""
        with self._lock:
            self._buckets.clear()


# ============================================================================
# Circuit Health Reporter
# ============================================================================


class CircuitHealthReporter:
    """
    Reports overall health status of circuit breaker.

    Aggregates metrics and provides health assessment.
    """

    def __init__(self):
        """Initialize health reporter."""
        self.failure_rate_calc = FailureRateCalculator()
        self.latency_monitor = LatencyMonitor()
        self.success_rate_tracker = SuccessRateTracker()

    def record_request(self, success: bool, duration_ms: float) -> None:
        """
        Record a request result.

        Args:
            success: Whether request succeeded
            duration_ms: Request duration in milliseconds
        """
        self.failure_rate_calc.record_request(success, duration_ms)
        self.latency_monitor.record_latency(duration_ms)
        self.success_rate_tracker.record_result(success)

    def get_health_score(self) -> float:
        """
        Calculate health score (0.0-1.0).

        Returns:
            Health score where 1.0 is perfect health
        """
        # Weight factors
        success_weight = 0.5
        latency_weight = 0.3
        stability_weight = 0.2

        # Success rate component (0-1)
        success_rate = self.success_rate_tracker.get_success_rate(300.0)  # 5 minutes
        success_score = success_rate

        # Latency component (0-1)
        latency_stats = self.latency_monitor.get_latency_stats()
        if latency_stats:
            # Normalize latency (assuming 1000ms is poor)
            normalized_latency = min(latency_stats.p95_ms / 1000.0, 1.0)
            latency_score = 1.0 - normalized_latency
        else:
            latency_score = 1.0

        # Stability component (consistent performance)
        # High variance in latency or success rate reduces stability
        stability_score = 0.8  # Simplified for now

        # Calculate weighted score
        health_score = (
            success_score * success_weight +
            latency_score * latency_weight +
            stability_score * stability_weight
        )

        return health_score

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.

        Returns:
            Health status dictionary
        """
        health_score = self.get_health_score()

        # Determine status
        if health_score >= 0.9:
            status = "healthy"
        elif health_score >= 0.7:
            status = "degraded"
        elif health_score >= 0.5:
            status = "unhealthy"
        else:
            status = "critical"

        return {
            "status": status,
            "health_score": health_score,
            "success_rate": self.success_rate_tracker.get_success_rate(300.0),
            "failure_rate": self.failure_rate_calc.get_failure_rate(300.0),
            "latency_stats": asdict(self.latency_monitor.get_latency_stats()) if self.latency_monitor.get_latency_stats() else None,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Metrics Exporter
# ============================================================================


class MetricsExporter:
    """
    Exports metrics in various formats (Prometheus, JSON, etc.).

    Provides integration with monitoring systems.
    """

    def __init__(self, circuit_breaker: 'CircuitBreakerFSA'):
        """
        Initialize metrics exporter.

        Args:
            circuit_breaker: Circuit breaker to export metrics for
        """
        self.circuit_breaker = circuit_breaker

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        metrics = self.circuit_breaker.get_metrics()
        name = self.circuit_breaker.name

        lines = [
            f"# HELP circuit_breaker_state Current state of circuit breaker (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
            f"# TYPE circuit_breaker_state gauge",
            f'circuit_breaker_state{{name="{name}"}} {self._state_to_number(metrics.state)}',
            "",
            f"# HELP circuit_breaker_requests_total Total number of requests",
            f"# TYPE circuit_breaker_requests_total counter",
            f'circuit_breaker_requests_total{{name="{name}"}} {metrics.total_requests}',
            "",
            f"# HELP circuit_breaker_successes_total Total number of successful requests",
            f"# TYPE circuit_breaker_successes_total counter",
            f'circuit_breaker_successes_total{{name="{name}"}} {metrics.successful_requests}',
            "",
            f"# HELP circuit_breaker_failures_total Total number of failed requests",
            f"# TYPE circuit_breaker_failures_total counter",
            f'circuit_breaker_failures_total{{name="{name}"}} {metrics.failed_requests}',
            "",
            f"# HELP circuit_breaker_rejected_total Total number of rejected requests",
            f"# TYPE circuit_breaker_rejected_total counter",
            f'circuit_breaker_rejected_total{{name="{name}"}} {metrics.rejected_requests}',
            "",
            f"# HELP circuit_breaker_failure_rate Current failure rate",
            f"# TYPE circuit_breaker_failure_rate gauge",
            f'circuit_breaker_failure_rate{{name="{name}"}} {metrics.failure_rate}',
            "",
            f"# HELP circuit_breaker_latency_ms Average latency in milliseconds",
            f"# TYPE circuit_breaker_latency_ms gauge",
            f'circuit_breaker_latency_ms{{name="{name}"}} {metrics.average_latency_ms}',
            "",
            f"# HELP circuit_breaker_state_transitions_total Total number of state transitions",
            f"# TYPE circuit_breaker_state_transitions_total counter",
            f'circuit_breaker_state_transitions_total{{name="{name}"}} {metrics.state_transitions}',
        ]

        return "\n".join(lines)

    def export_json(self) -> str:
        """
        Export metrics as JSON.

        Returns:
            JSON-formatted metrics
        """
        metrics = self.circuit_breaker.get_metrics()
        return json.dumps(metrics.to_dict(), indent=2)

    @staticmethod
    def _state_to_number(state: 'CircuitState') -> int:
        """Convert state to number for Prometheus."""
        from agno.fsa.circuit_breaker import CircuitState
        return {
            CircuitState.CLOSED: 0,
            CircuitState.OPEN: 1,
            CircuitState.HALF_OPEN: 2,
        }.get(state, -1)


# ============================================================================
# Alert Manager
# ============================================================================


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert notification."""
    level: AlertLevel
    message: str
    timestamp: datetime
    circuit_name: str
    metadata: Dict[str, Any]


class AlertManager:
    """
    Manages alerts and notifications for circuit breaker events.

    Sends alerts when thresholds are breached or state changes occur.
    """

    def __init__(
        self,
        circuit_breaker: 'CircuitBreakerFSA',
        alert_handlers: Optional[List[Callable[[Alert], None]]] = None
    ):
        """
        Initialize alert manager.

        Args:
            circuit_breaker: Circuit breaker to monitor
            alert_handlers: List of functions to call with alerts
        """
        self.circuit_breaker = circuit_breaker
        self.alert_handlers = alert_handlers or []

        self._alerts: Deque[Alert] = deque(maxlen=1000)
        self._alert_counts: Dict[AlertLevel, int] = defaultdict(int)
        self._lock = threading.Lock()

        # Register as state change listener
        self.circuit_breaker.add_state_change_listener(self._on_state_change)

        logger.debug(f"Initialized AlertManager for circuit '{circuit_breaker.name}'")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add an alert handler.

        Args:
            handler: Function to call with alerts
        """
        self.alert_handlers.append(handler)

    def _on_state_change(self, from_state: 'CircuitState', to_state: 'CircuitState') -> None:
        """Handle state change events."""
        from agno.fsa.circuit_breaker import CircuitState

        # Determine alert level based on transition
        if to_state == CircuitState.OPEN:
            level = AlertLevel.ERROR
            message = f"Circuit breaker opened: {from_state} -> {to_state}"
        elif to_state == CircuitState.HALF_OPEN:
            level = AlertLevel.WARNING
            message = f"Circuit breaker entering recovery: {from_state} -> {to_state}"
        elif to_state == CircuitState.CLOSED and from_state == CircuitState.HALF_OPEN:
            level = AlertLevel.INFO
            message = f"Circuit breaker recovered: {from_state} -> {to_state}"
        else:
            level = AlertLevel.INFO
            message = f"Circuit breaker state change: {from_state} -> {to_state}"

        self.send_alert(
            level=level,
            message=message,
            metadata={
                "from_state": str(from_state),
                "to_state": str(to_state)
            }
        )

    def send_alert(
        self,
        level: AlertLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send an alert.

        Args:
            level: Alert severity level
            message: Alert message
            metadata: Additional metadata
        """
        with self._lock:
            alert = Alert(
                level=level,
                message=message,
                timestamp=datetime.now(),
                circuit_name=self.circuit_breaker.name,
                metadata=metadata or {}
            )

            self._alerts.append(alert)
            self._alert_counts[level] += 1

            logger.log(
                self._log_level_for_alert(level),
                f"[{level.value.upper()}] {self.circuit_breaker.name}: {message}"
            )

            # Call handlers
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")

    @staticmethod
    def _log_level_for_alert(level: AlertLevel) -> int:
        """Get logging level for alert level."""
        return {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }.get(level, logging.INFO)

    def get_recent_alerts(self, limit: int = 100) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        with self._lock:
            return list(self._alerts)[-limit:]

    def get_alert_counts(self) -> Dict[AlertLevel, int]:
        """Get counts of alerts by level."""
        with self._lock:
            return dict(self._alert_counts)

    def clear_alerts(self) -> None:
        """Clear alert history."""
        with self._lock:
            self._alerts.clear()
            self._alert_counts.clear()

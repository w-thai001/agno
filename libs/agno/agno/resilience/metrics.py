"""
Circuit Breaker Metrics and Monitoring

This module provides comprehensive metrics collection and export capabilities
for circuit breakers, enabling integration with monitoring systems like
Prometheus, Datadog, and custom dashboards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Protocol
from collections import defaultdict
import json

from agno.resilience.states import CircuitState, CircuitStateData, StateTransition


@dataclass
class CircuitBreakerMetrics:
    """
    Comprehensive metrics for a single circuit breaker instance.

    Tracks all relevant metrics for monitoring, alerting, and debugging.
    """
    # Identity
    circuit_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Current state metrics
    current_state: CircuitState = CircuitState.CLOSED
    state_duration_seconds: float = 0.0

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0

    # Rate metrics
    current_failure_rate: float = 0.0
    current_success_rate: float = 0.0

    # Latency metrics (milliseconds)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # State transition metrics
    total_state_transitions: int = 0
    times_opened: int = 0
    times_half_opened: int = 0
    times_closed: int = 0

    # Time in states (cumulative)
    total_time_closed_seconds: float = 0.0
    total_time_open_seconds: float = 0.0
    total_time_half_open_seconds: float = 0.0

    # Bulkhead metrics
    concurrent_requests: int = 0
    max_concurrent_requests: int = 0
    bulkhead_rejections: int = 0

    # Error tracking
    error_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    # Time-series data (last hour)
    request_history: List[Dict[str, Any]] = field(default_factory=list)

    def update_from_state(self, state: CircuitStateData) -> None:
        """Update metrics from circuit state data"""
        self.current_state = state.current_state
        self.state_duration_seconds = (datetime.utcnow() - state.state_entered_at).total_seconds()

        self.total_requests = state.total_requests
        self.successful_requests = state.success_count
        self.failed_requests = state.failure_count
        self.rejected_requests = state.rejected_requests

        self.current_failure_rate = state.get_failure_rate()
        self.current_success_rate = state.get_success_rate()

        self.p50_latency_ms = state.p50_latency
        self.p95_latency_ms = state.p95_latency
        self.p99_latency_ms = state.p99_latency

        if state.recent_latencies:
            self.avg_latency_ms = sum(state.recent_latencies) / len(state.recent_latencies)
            self.max_latency_ms = max(state.recent_latencies)

        self.concurrent_requests = state.concurrent_requests
        self.max_concurrent_requests = state.max_concurrent_requests_seen

        self.total_state_transitions = len(state.transition_history)

        # Count state transitions
        for transition in state.transition_history:
            if transition.to_state == CircuitState.OPEN:
                self.times_opened += 1
            elif transition.to_state == CircuitState.HALF_OPEN:
                self.times_half_opened += 1
            elif transition.to_state == CircuitState.CLOSED:
                self.times_closed += 1

    def to_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metric string
        """
        lines = []
        prefix = f"circuit_breaker_{self.circuit_name}"

        # State gauge (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
        state_value = {CircuitState.CLOSED: 0, CircuitState.OPEN: 1, CircuitState.HALF_OPEN: 2}
        lines.append(f"{prefix}_state {state_value[self.current_state]}")

        # Counters
        lines.append(f"{prefix}_requests_total {self.total_requests}")
        lines.append(f"{prefix}_requests_successful_total {self.successful_requests}")
        lines.append(f"{prefix}_requests_failed_total {self.failed_requests}")
        lines.append(f"{prefix}_requests_rejected_total {self.rejected_requests}")

        # Rates
        lines.append(f"{prefix}_failure_rate {self.current_failure_rate:.4f}")
        lines.append(f"{prefix}_success_rate {self.current_success_rate:.4f}")

        # Latency
        lines.append(f"{prefix}_latency_p50_milliseconds {self.p50_latency_ms:.2f}")
        lines.append(f"{prefix}_latency_p95_milliseconds {self.p95_latency_ms:.2f}")
        lines.append(f"{prefix}_latency_p99_milliseconds {self.p99_latency_ms:.2f}")

        # State transitions
        lines.append(f"{prefix}_state_transitions_total {self.total_state_transitions}")
        lines.append(f"{prefix}_times_opened_total {self.times_opened}")

        # Bulkhead
        lines.append(f"{prefix}_concurrent_requests {self.concurrent_requests}")
        lines.append(f"{prefix}_bulkhead_rejections_total {self.bulkhead_rejections}")

        return "\n".join(lines)

    def to_datadog_format(self) -> List[Dict[str, Any]]:
        """
        Export metrics in Datadog format.

        Returns:
            List of metric dictionaries for Datadog API
        """
        timestamp = int(datetime.utcnow().timestamp())
        tags = [f"circuit:{self.circuit_name}"]

        metrics = [
            {
                "metric": "circuit_breaker.state",
                "points": [[timestamp, {CircuitState.CLOSED: 0, CircuitState.OPEN: 1, CircuitState.HALF_OPEN: 2}[self.current_state]]],
                "type": "gauge",
                "tags": tags
            },
            {
                "metric": "circuit_breaker.requests.total",
                "points": [[timestamp, self.total_requests]],
                "type": "count",
                "tags": tags
            },
            {
                "metric": "circuit_breaker.requests.failed",
                "points": [[timestamp, self.failed_requests]],
                "type": "count",
                "tags": tags
            },
            {
                "metric": "circuit_breaker.failure_rate",
                "points": [[timestamp, self.current_failure_rate]],
                "type": "gauge",
                "tags": tags
            },
            {
                "metric": "circuit_breaker.latency.p95",
                "points": [[timestamp, self.p95_latency_ms]],
                "type": "gauge",
                "tags": tags
            }
        ]

        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary for JSON serialization"""
        return {
            "circuit_name": self.circuit_name,
            "timestamp": datetime.utcnow().isoformat(),
            "state": {
                "current": self.current_state.value,
                "duration_seconds": self.state_duration_seconds
            },
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "rejected": self.rejected_requests
            },
            "rates": {
                "failure_rate": self.current_failure_rate,
                "success_rate": self.current_success_rate
            },
            "latency_ms": {
                "p50": self.p50_latency_ms,
                "p95": self.p95_latency_ms,
                "p99": self.p99_latency_ms,
                "avg": self.avg_latency_ms,
                "max": self.max_latency_ms
            },
            "transitions": {
                "total": self.total_state_transitions,
                "times_opened": self.times_opened,
                "times_half_opened": self.times_half_opened,
                "times_closed": self.times_closed
            },
            "bulkhead": {
                "concurrent": self.concurrent_requests,
                "max_concurrent": self.max_concurrent_requests,
                "rejections": self.bulkhead_rejections
            }
        }

    def to_json(self) -> str:
        """Export metrics as JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class MetricsExporter(Protocol):
    """Protocol for metrics exporters"""

    def export(self, metrics: CircuitBreakerMetrics) -> None:
        """Export metrics to external system"""
        ...


@dataclass
class MetricsCollector:
    """
    Aggregates metrics from multiple circuit breakers.

    Useful for system-wide monitoring and dashboards.
    """
    circuits: Dict[str, CircuitBreakerMetrics] = field(default_factory=dict)

    def register_circuit(self, name: str) -> CircuitBreakerMetrics:
        """Register a new circuit breaker for monitoring"""
        metrics = CircuitBreakerMetrics(circuit_name=name)
        self.circuits[name] = metrics
        return metrics

    def get_circuit_metrics(self, name: str) -> Optional[CircuitBreakerMetrics]:
        """Get metrics for a specific circuit"""
        return self.circuits.get(name)

    def get_all_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """Get metrics for all circuits"""
        return self.circuits

    def get_summary(self) -> Dict[str, Any]:
        """Get aggregate summary across all circuits"""
        total_circuits = len(self.circuits)
        open_circuits = sum(1 for m in self.circuits.values() if m.current_state == CircuitState.OPEN)
        half_open_circuits = sum(1 for m in self.circuits.values() if m.current_state == CircuitState.HALF_OPEN)
        closed_circuits = sum(1 for m in self.circuits.values() if m.current_state == CircuitState.CLOSED)

        total_requests = sum(m.total_requests for m in self.circuits.values())
        total_failures = sum(m.failed_requests for m in self.circuits.values())
        total_rejections = sum(m.rejected_requests for m in self.circuits.values())

        overall_failure_rate = total_failures / total_requests if total_requests > 0 else 0.0

        return {
            "total_circuits": total_circuits,
            "state_distribution": {
                "open": open_circuits,
                "half_open": half_open_circuits,
                "closed": closed_circuits
            },
            "aggregate_metrics": {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "total_rejections": total_rejections,
                "overall_failure_rate": overall_failure_rate
            },
            "unhealthy_circuits": [
                name for name, metrics in self.circuits.items()
                if metrics.current_state != CircuitState.CLOSED
            ]
        }

    def to_json(self) -> str:
        """Export all circuit metrics as JSON"""
        return json.dumps({
            "summary": self.get_summary(),
            "circuits": {name: metrics.to_dict() for name, metrics in self.circuits.items()}
        }, indent=2)


# Global metrics collector instance
_global_collector = MetricsCollector()


def get_global_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return _global_collector


def register_circuit(name: str) -> CircuitBreakerMetrics:
    """Register a circuit with the global collector"""
    return _global_collector.register_circuit(name)

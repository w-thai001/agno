"""Metrics Collector Finite State Automaton for tracking application metrics."""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for metrics collection."""
    IDLE = "idle"
    RECORDING = "recording"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class Metric:
    """Represents a metric."""
    name: str
    metric_type: MetricType
    value: Any = 0
    values: List[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class MetricsCollectorFSA:
    """Finite State Automaton for collecting and aggregating metrics."""

    def __init__(self):
        self.state = State.IDLE
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        logger.info("Metrics collector initialized")

    def start_recording(self):
        """Start metrics recording session."""
        with self._lock:
            if self.state == State.RECORDING:
                logger.warning("Already recording metrics")
                return

            self._transition(self.state, State.RECORDING)
            logger.info("Started metrics recording")

    def stop_recording(self):
        """Stop metrics recording session."""
        with self._lock:
            if self.state != State.RECORDING:
                logger.warning("Not currently recording")
                return

            self._transition(State.RECORDING, State.IDLE)
            logger.info("Stopped metrics recording")

    def increment(self, name: str, value: float = 1.0):
        """Increment a counter metric."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.COUNTER)
            metric.value += value
            metric.timestamp = time.time()
            logger.debug(f"Counter {name}: +{value} = {metric.value}")

    def set_gauge(self, name: str, value: float):
        """Set a gauge metric to a specific value."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.GAUGE)
            metric.value = value
            metric.timestamp = time.time()
            logger.debug(f"Gauge {name}: {value}")

    def record_histogram(self, name: str, value: float):
        """Record a value in a histogram metric."""
        with self._lock:
            metric = self._get_or_create_metric(name, MetricType.HISTOGRAM)
            metric.values.append(value)
            metric.timestamp = time.time()
            logger.debug(f"Histogram {name}: recorded {value}")

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def aggregate(self, name: str) -> Optional[Dict[str, Any]]:
        """Aggregate metric data."""
        with self._lock:
            metric = self._metrics.get(name)
            if not metric:
                return None

            self._transition(self.state, State.AGGREGATING)

            result = {
                "name": name,
                "type": metric.metric_type.value,
                "timestamp": metric.timestamp
            }

            if metric.metric_type == MetricType.COUNTER:
                result["value"] = metric.value
                result["count"] = metric.value

            elif metric.metric_type == MetricType.GAUGE:
                result["value"] = metric.value
                result["current"] = metric.value

            elif metric.metric_type == MetricType.HISTOGRAM:
                if metric.values:
                    sorted_values = sorted(metric.values)
                    result["count"] = len(metric.values)
                    result["sum"] = sum(metric.values)
                    result["avg"] = sum(metric.values) / len(metric.values)
                    result["min"] = min(metric.values)
                    result["max"] = max(metric.values)
                    result["p50"] = self._percentile(sorted_values, 50)
                    result["p95"] = self._percentile(sorted_values, 95)
                    result["p99"] = self._percentile(sorted_values, 99)
                else:
                    result["count"] = 0

            self._transition(State.AGGREGATING, State.COMPLETED)
            self._transition(State.COMPLETED, self.state)

            return result

    def aggregate_all(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate all metrics."""
        results = {}
        for name in list(self._metrics.keys()):
            results[name] = self.aggregate(name)
        return results

    def reset_metric(self, name: str):
        """Reset a specific metric."""
        with self._lock:
            metric = self._metrics.get(name)
            if not metric:
                return

            if metric.metric_type == MetricType.COUNTER:
                metric.value = 0
            elif metric.metric_type == MetricType.GAUGE:
                metric.value = 0
            elif metric.metric_type == MetricType.HISTOGRAM:
                metric.values.clear()

            logger.debug(f"Reset metric {name}")

    def reset_all(self):
        """Reset all metrics."""
        with self._lock:
            for name in list(self._metrics.keys()):
                self.reset_metric(name)
            logger.info("Reset all metrics")

    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._transition(self.state, State.IDLE)
            logger.info("Cleared all metrics")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self._lock:
            counters = sum(1 for m in self._metrics.values() if m.metric_type == MetricType.COUNTER)
            gauges = sum(1 for m in self._metrics.values() if m.metric_type == MetricType.GAUGE)
            histograms = sum(1 for m in self._metrics.values() if m.metric_type == MetricType.HISTOGRAM)

            return {
                "state": self.state.value,
                "total_metrics": len(self._metrics),
                "counters": counters,
                "gauges": gauges,
                "histograms": histograms
            }

    def _get_or_create_metric(self, name: str, metric_type: MetricType) -> Metric:
        """Get existing metric or create new one."""
        if name in self._metrics:
            metric = self._metrics[name]
            if metric.metric_type != metric_type:
                raise ValueError(
                    f"Metric {name} exists as {metric.metric_type.value}, "
                    f"cannot use as {metric_type.value}"
                )
            return metric

        metric = Metric(name=name, metric_type=metric_type)
        self._metrics[name] = metric
        logger.debug(f"Created {metric_type.value} metric: {name}")
        return metric

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower = int(index)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = index - lower

        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

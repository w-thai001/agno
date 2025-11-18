"""
Failure Detection Strategies for Circuit Breaker FSA

This module provides multiple failure detection strategies for determining
when a circuit breaker should transition from CLOSED to OPEN state.
"""

import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, List, Optional
import logging
import statistics

logger = logging.getLogger(__name__)


# ============================================================================
# Base Classes
# ============================================================================


class FailureDetector(ABC):
    """
    Abstract base class for failure detection strategies.

    Failure detectors analyze request history and determine whether
    the circuit breaker should open based on specific criteria.
    """

    def __init__(self, name: str = "detector"):
        """
        Initialize failure detector.

        Args:
            name: Name identifier for this detector
        """
        self.name = name

    @abstractmethod
    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """
        Determine if circuit should open based on request history.

        Args:
            request_history: Deque of recent request records
            config: Circuit breaker configuration

        Returns:
            True if circuit should open, False otherwise
        """
        pass

    def reset(self) -> None:
        """Reset detector state."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


# ============================================================================
# Count-Based Detection
# ============================================================================


class CountBasedDetector(FailureDetector):
    """
    Detects failures based on absolute count within a rolling window.

    Opens circuit if the number of failures exceeds a threshold
    within the specified window size.

    Example:
        >>> detector = CountBasedDetector(
        ...     failure_threshold=10,
        ...     window_size=100
        ... )
        >>> should_open = detector.should_open(request_history, config)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        window_size: int = 100,
        name: str = "count_based_detector"
    ):
        """
        Initialize count-based detector.

        Args:
            failure_threshold: Number of failures to trigger opening
            window_size: Size of rolling window to consider
            name: Detector name
        """
        super().__init__(name)
        self.failure_threshold = failure_threshold
        self.window_size = window_size
        logger.debug(f"Initialized {self.name} with threshold={failure_threshold}, window={window_size}")

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if failure count exceeds threshold."""
        if not request_history:
            return False

        # Count failures in window
        failure_count = sum(1 for record in request_history if not record.success)

        should_open = failure_count >= self.failure_threshold

        if should_open:
            logger.info(
                f"{self.name}: Failure count {failure_count} exceeds threshold {self.failure_threshold}"
            )

        return should_open

    def __repr__(self) -> str:
        return (
            f"CountBasedDetector(threshold={self.failure_threshold}, "
            f"window={self.window_size})"
        )


# ============================================================================
# Percentage-Based Detection
# ============================================================================


class PercentageBasedDetector(FailureDetector):
    """
    Detects failures based on failure rate percentage.

    Opens circuit if the failure rate exceeds a percentage threshold
    within the rolling window. Requires a minimum number of requests
    to avoid premature triggering.

    Example:
        >>> detector = PercentageBasedDetector(
        ...     failure_rate_threshold=0.5,  # 50%
        ...     minimum_requests=10
        ... )
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.5,
        minimum_requests: int = 10,
        window_size: int = 100,
        name: str = "percentage_based_detector"
    ):
        """
        Initialize percentage-based detector.

        Args:
            failure_rate_threshold: Failure rate threshold (0.0-1.0)
            minimum_requests: Minimum requests before checking threshold
            window_size: Size of rolling window
            name: Detector name
        """
        super().__init__(name)
        if not 0.0 <= failure_rate_threshold <= 1.0:
            raise ValueError("failure_rate_threshold must be between 0.0 and 1.0")

        self.failure_rate_threshold = failure_rate_threshold
        self.minimum_requests = minimum_requests
        self.window_size = window_size

        logger.debug(
            f"Initialized {self.name} with rate={failure_rate_threshold:.1%}, "
            f"min_requests={minimum_requests}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if failure rate exceeds threshold."""
        if not request_history:
            return False

        total_requests = len(request_history)

        # Wait for minimum number of requests
        if total_requests < self.minimum_requests:
            return False

        # Calculate failure rate
        failure_count = sum(1 for record in request_history if not record.success)
        failure_rate = failure_count / total_requests

        should_open = failure_rate >= self.failure_rate_threshold

        if should_open:
            logger.info(
                f"{self.name}: Failure rate {failure_rate:.1%} exceeds threshold "
                f"{self.failure_rate_threshold:.1%} ({failure_count}/{total_requests})"
            )

        return should_open

    def __repr__(self) -> str:
        return (
            f"PercentageBasedDetector(threshold={self.failure_rate_threshold:.1%}, "
            f"min_requests={self.minimum_requests})"
        )


# ============================================================================
# Consecutive Failure Detection
# ============================================================================


class ConsecutiveFailureDetector(FailureDetector):
    """
    Detects consecutive failures without intervening successes.

    Opens circuit if N consecutive failures occur. This is useful
    for detecting complete service outages.

    Example:
        >>> detector = ConsecutiveFailureDetector(
        ...     consecutive_threshold=5
        ... )
    """

    def __init__(
        self,
        consecutive_threshold: int = 3,
        name: str = "consecutive_failure_detector"
    ):
        """
        Initialize consecutive failure detector.

        Args:
            consecutive_threshold: Number of consecutive failures to trigger
            name: Detector name
        """
        super().__init__(name)
        self.consecutive_threshold = consecutive_threshold
        self._consecutive_count = 0

        logger.debug(f"Initialized {self.name} with threshold={consecutive_threshold}")

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if consecutive failures exceed threshold."""
        if not request_history:
            return False

        # Count consecutive failures from the end
        consecutive_failures = 0
        for record in reversed(request_history):
            if not record.success:
                consecutive_failures += 1
            else:
                break

        self._consecutive_count = consecutive_failures
        should_open = consecutive_failures >= self.consecutive_threshold

        if should_open:
            logger.info(
                f"{self.name}: Consecutive failures {consecutive_failures} exceeds "
                f"threshold {self.consecutive_threshold}"
            )

        return should_open

    def reset(self) -> None:
        """Reset consecutive count."""
        self._consecutive_count = 0

    def __repr__(self) -> str:
        return f"ConsecutiveFailureDetector(threshold={self.consecutive_threshold})"


# ============================================================================
# Sliding Window Detection
# ============================================================================


class SlidingWindowDetector(FailureDetector):
    """
    Detects failures within a time-based sliding window.

    Opens circuit if failure rate exceeds threshold within a
    specific time window (e.g., 50% failures in last 60 seconds).

    Example:
        >>> detector = SlidingWindowDetector(
        ...     time_window_seconds=60.0,
        ...     failure_rate_threshold=0.5,
        ...     minimum_requests=10
        ... )
    """

    def __init__(
        self,
        time_window_seconds: float = 60.0,
        failure_rate_threshold: float = 0.5,
        minimum_requests: int = 10,
        name: str = "sliding_window_detector"
    ):
        """
        Initialize sliding window detector.

        Args:
            time_window_seconds: Time window in seconds
            failure_rate_threshold: Failure rate threshold (0.0-1.0)
            minimum_requests: Minimum requests in window
            name: Detector name
        """
        super().__init__(name)
        if not 0.0 <= failure_rate_threshold <= 1.0:
            raise ValueError("failure_rate_threshold must be between 0.0 and 1.0")

        self.time_window_seconds = time_window_seconds
        self.failure_rate_threshold = failure_rate_threshold
        self.minimum_requests = minimum_requests

        logger.debug(
            f"Initialized {self.name} with window={time_window_seconds}s, "
            f"rate={failure_rate_threshold:.1%}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if failure rate exceeds threshold in time window."""
        if not request_history:
            return False

        # Filter requests within time window
        cutoff_time = datetime.now() - timedelta(seconds=self.time_window_seconds)
        recent_requests = [
            record for record in request_history
            if record.timestamp >= cutoff_time
        ]

        if len(recent_requests) < self.minimum_requests:
            return False

        # Calculate failure rate
        failure_count = sum(1 for record in recent_requests if not record.success)
        failure_rate = failure_count / len(recent_requests)

        should_open = failure_rate >= self.failure_rate_threshold

        if should_open:
            logger.info(
                f"{self.name}: Failure rate {failure_rate:.1%} in last "
                f"{self.time_window_seconds}s exceeds threshold "
                f"{self.failure_rate_threshold:.1%} ({failure_count}/{len(recent_requests)})"
            )

        return should_open

    def __repr__(self) -> str:
        return (
            f"SlidingWindowDetector(window={self.time_window_seconds}s, "
            f"threshold={self.failure_rate_threshold:.1%})"
        )


# ============================================================================
# Latency-Based Detection
# ============================================================================


class LatencyBasedDetector(FailureDetector):
    """
    Detects slow responses that exceed latency thresholds.

    Opens circuit if too many requests are slow (exceed latency threshold).
    This is useful for detecting degraded service performance.

    Example:
        >>> detector = LatencyBasedDetector(
        ...     slow_call_duration_threshold=5000.0,  # 5 seconds in ms
        ...     slow_call_rate_threshold=0.5,  # 50%
        ...     minimum_requests=10
        ... )
    """

    def __init__(
        self,
        slow_call_duration_threshold: float = 5000.0,  # milliseconds
        slow_call_rate_threshold: float = 0.5,
        minimum_requests: int = 10,
        name: str = "latency_based_detector"
    ):
        """
        Initialize latency-based detector.

        Args:
            slow_call_duration_threshold: Threshold for slow calls (milliseconds)
            slow_call_rate_threshold: Rate of slow calls to trigger (0.0-1.0)
            minimum_requests: Minimum requests before checking
            name: Detector name
        """
        super().__init__(name)
        if not 0.0 <= slow_call_rate_threshold <= 1.0:
            raise ValueError("slow_call_rate_threshold must be between 0.0 and 1.0")

        self.slow_call_duration_threshold = slow_call_duration_threshold
        self.slow_call_rate_threshold = slow_call_rate_threshold
        self.minimum_requests = minimum_requests

        logger.debug(
            f"Initialized {self.name} with latency={slow_call_duration_threshold}ms, "
            f"rate={slow_call_rate_threshold:.1%}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if slow call rate exceeds threshold."""
        if not request_history:
            return False

        if len(request_history) < self.minimum_requests:
            return False

        # Count slow calls
        slow_call_count = sum(
            1 for record in request_history
            if record.is_slow(self.slow_call_duration_threshold)
        )

        slow_call_rate = slow_call_count / len(request_history)
        should_open = slow_call_rate >= self.slow_call_rate_threshold

        if should_open:
            logger.info(
                f"{self.name}: Slow call rate {slow_call_rate:.1%} exceeds threshold "
                f"{self.slow_call_rate_threshold:.1%} ({slow_call_count}/{len(request_history)} "
                f"calls >{self.slow_call_duration_threshold}ms)"
            )

        return should_open

    def __repr__(self) -> str:
        return (
            f"LatencyBasedDetector(threshold={self.slow_call_duration_threshold}ms, "
            f"rate={self.slow_call_rate_threshold:.1%})"
        )


# ============================================================================
# Anomaly Detection
# ============================================================================


@dataclass
class AnomalyThresholds:
    """Thresholds for anomaly detection."""
    zscore_threshold: float = 3.0  # Standard deviations from mean
    minimum_samples: int = 20  # Minimum samples for statistical significance
    lookback_window: int = 100  # Number of samples to use for baseline


class AnomalyDetector(FailureDetector):
    """
    ML-based anomaly detection using statistical methods.

    Detects anomalies in failure patterns using Z-score analysis.
    Opens circuit when current failure rate significantly deviates
    from historical baseline.

    This is useful for detecting unexpected spikes in failures that
    may not trigger absolute thresholds but represent abnormal behavior.

    Example:
        >>> detector = AnomalyDetector(
        ...     zscore_threshold=3.0,
        ...     minimum_samples=20
        ... )
    """

    def __init__(
        self,
        zscore_threshold: float = 3.0,
        minimum_samples: int = 20,
        lookback_window: int = 100,
        time_window_seconds: float = 10.0,
        name: str = "anomaly_detector"
    ):
        """
        Initialize anomaly detector.

        Args:
            zscore_threshold: Z-score threshold for anomaly detection
            minimum_samples: Minimum samples needed for detection
            lookback_window: Number of historical samples to use
            time_window_seconds: Time window for calculating current rate
            name: Detector name
        """
        super().__init__(name)
        self.zscore_threshold = zscore_threshold
        self.minimum_samples = minimum_samples
        self.lookback_window = lookback_window
        self.time_window_seconds = time_window_seconds

        # Historical failure rates
        self._failure_rate_history: Deque[float] = deque(maxlen=lookback_window)
        self._last_check_time = datetime.now()

        logger.debug(
            f"Initialized {self.name} with zscore={zscore_threshold}, "
            f"min_samples={minimum_samples}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if current failure pattern is anomalous."""
        if not request_history or len(request_history) < self.minimum_samples:
            return False

        # Calculate current failure rate in recent window
        cutoff_time = datetime.now() - timedelta(seconds=self.time_window_seconds)
        recent_requests = [
            record for record in request_history
            if record.timestamp >= cutoff_time
        ]

        if not recent_requests:
            return False

        current_failure_rate = sum(1 for r in recent_requests if not r.success) / len(recent_requests)

        # Update historical baseline periodically
        time_since_update = (datetime.now() - self._last_check_time).total_seconds()
        if time_since_update >= self.time_window_seconds:
            self._failure_rate_history.append(current_failure_rate)
            self._last_check_time = datetime.now()

        # Need sufficient history for anomaly detection
        if len(self._failure_rate_history) < self.minimum_samples:
            return False

        # Calculate statistical measures
        try:
            mean_rate = statistics.mean(self._failure_rate_history)
            stdev_rate = statistics.stdev(self._failure_rate_history)

            # Avoid division by zero
            if stdev_rate == 0:
                return current_failure_rate > mean_rate

            # Calculate Z-score
            zscore = abs((current_failure_rate - mean_rate) / stdev_rate)

            should_open = zscore >= self.zscore_threshold

            if should_open:
                logger.info(
                    f"{self.name}: Anomaly detected - current failure rate {current_failure_rate:.1%} "
                    f"deviates {zscore:.2f} standard deviations from baseline "
                    f"(mean={mean_rate:.1%}, stdev={stdev_rate:.3f})"
                )

            return should_open

        except statistics.StatisticsError as e:
            logger.warning(f"{self.name}: Statistical calculation error: {e}")
            return False

    def reset(self) -> None:
        """Reset anomaly detector state."""
        self._failure_rate_history.clear()
        self._last_check_time = datetime.now()

    def __repr__(self) -> str:
        return (
            f"AnomalyDetector(zscore={self.zscore_threshold}, "
            f"min_samples={self.minimum_samples})"
        )


# ============================================================================
# Custom Predicate Detection
# ============================================================================


class CustomDetector(FailureDetector):
    """
    Custom failure detection using user-defined predicate functions.

    Allows complete flexibility in defining failure detection logic.
    The predicate function receives request history and config and
    returns whether the circuit should open.

    Example:
        >>> def my_predicate(history, config):
        ...     # Custom logic
        ...     recent_failures = sum(1 for r in list(history)[-10:] if not r.success)
        ...     return recent_failures > 7
        >>>
        >>> detector = CustomDetector(predicate=my_predicate)
    """

    def __init__(
        self,
        predicate: Callable[[Deque['RequestRecord'], 'CircuitBreakerConfig'], bool],
        name: str = "custom_detector"
    ):
        """
        Initialize custom detector.

        Args:
            predicate: Function that determines if circuit should open
            name: Detector name
        """
        super().__init__(name)
        self.predicate = predicate

        logger.debug(f"Initialized {self.name} with custom predicate")

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check using custom predicate."""
        try:
            return self.predicate(request_history, config)
        except Exception as e:
            logger.error(f"{self.name}: Predicate error: {e}")
            return False

    def __repr__(self) -> str:
        return f"CustomDetector(predicate={self.predicate.__name__})"


# ============================================================================
# Composite Detection
# ============================================================================


class CompositeDetector(FailureDetector):
    """
    Combines multiple failure detectors with AND/OR logic.

    Allows combining multiple detection strategies. Can be configured
    to open circuit if ANY detector triggers (OR) or if ALL detectors
    trigger (AND).

    Example:
        >>> detector = CompositeDetector(
        ...     detectors=[
        ...         CountBasedDetector(failure_threshold=10),
        ...         PercentageBasedDetector(failure_rate_threshold=0.5),
        ...     ],
        ...     require_all=False  # OR logic
        ... )
    """

    def __init__(
        self,
        detectors: List[FailureDetector],
        require_all: bool = False,
        name: str = "composite_detector"
    ):
        """
        Initialize composite detector.

        Args:
            detectors: List of failure detectors to combine
            require_all: If True, all detectors must agree (AND logic).
                        If False, any detector can trigger (OR logic).
            name: Detector name
        """
        super().__init__(name)
        if not detectors:
            raise ValueError("At least one detector must be provided")

        self.detectors = detectors
        self.require_all = require_all

        logic_type = "AND" if require_all else "OR"
        logger.debug(f"Initialized {self.name} with {len(detectors)} detectors ({logic_type} logic)")

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check using combined detector logic."""
        results = []
        for detector in self.detectors:
            try:
                result = detector.should_open(request_history, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in detector {detector.name}: {e}")
                results.append(False)

        if self.require_all:
            # AND logic: all must agree
            should_open = all(results)
            if should_open:
                logger.info(f"{self.name}: All {len(self.detectors)} detectors triggered (AND)")
        else:
            # OR logic: any can trigger
            should_open = any(results)
            if should_open:
                triggered = sum(results)
                logger.info(f"{self.name}: {triggered}/{len(self.detectors)} detectors triggered (OR)")

        return should_open

    def reset(self) -> None:
        """Reset all detectors."""
        for detector in self.detectors:
            detector.reset()

    def __repr__(self) -> str:
        logic = "AND" if self.require_all else "OR"
        return f"CompositeDetector({len(self.detectors)} detectors, {logic})"


# ============================================================================
# Error Type Detection
# ============================================================================


class ErrorTypeDetector(FailureDetector):
    """
    Detects failures based on specific error types.

    Opens circuit when specific exception types occur at a certain rate.
    This is useful for treating different errors differently (e.g.,
    authentication errors vs. timeout errors).

    Example:
        >>> detector = ErrorTypeDetector(
        ...     error_types=[TimeoutError, ConnectionError],
        ...     failure_threshold=5,
        ...     window_size=50
        ... )
    """

    def __init__(
        self,
        error_types: List[type],
        failure_threshold: int = 5,
        window_size: int = 50,
        name: str = "error_type_detector"
    ):
        """
        Initialize error type detector.

        Args:
            error_types: List of exception types to track
            failure_threshold: Number of matching errors to trigger
            window_size: Size of rolling window
            name: Detector name
        """
        super().__init__(name)
        self.error_types = tuple(error_types)
        self.failure_threshold = failure_threshold
        self.window_size = window_size

        logger.debug(
            f"Initialized {self.name} tracking {len(error_types)} error types "
            f"with threshold={failure_threshold}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check if specific error types exceed threshold."""
        if not request_history:
            return False

        # Count matching error types
        matching_errors = sum(
            1 for record in request_history
            if not record.success and record.error and isinstance(record.error, self.error_types)
        )

        should_open = matching_errors >= self.failure_threshold

        if should_open:
            logger.info(
                f"{self.name}: Matching error count {matching_errors} exceeds "
                f"threshold {self.failure_threshold}"
            )

        return should_open

    def __repr__(self) -> str:
        error_names = [e.__name__ for e in self.error_types]
        return f"ErrorTypeDetector(types={error_names}, threshold={self.failure_threshold})"


# ============================================================================
# Adaptive Detection
# ============================================================================


class AdaptiveDetector(FailureDetector):
    """
    Adaptive failure detection that learns from patterns.

    Adjusts thresholds dynamically based on observed patterns.
    During stable periods, becomes more sensitive. During unstable
    periods, becomes more tolerant to avoid flapping.

    Example:
        >>> detector = AdaptiveDetector(
        ...     initial_failure_rate_threshold=0.5,
        ...     adaptation_rate=0.1
        ... )
    """

    def __init__(
        self,
        initial_failure_rate_threshold: float = 0.5,
        minimum_threshold: float = 0.2,
        maximum_threshold: float = 0.8,
        adaptation_rate: float = 0.1,
        stability_window: int = 50,
        minimum_requests: int = 10,
        name: str = "adaptive_detector"
    ):
        """
        Initialize adaptive detector.

        Args:
            initial_failure_rate_threshold: Starting threshold
            minimum_threshold: Minimum allowed threshold
            maximum_threshold: Maximum allowed threshold
            adaptation_rate: Rate of threshold adjustment (0.0-1.0)
            stability_window: Window for measuring stability
            minimum_requests: Minimum requests before adapting
            name: Detector name
        """
        super().__init__(name)
        self.current_threshold = initial_failure_rate_threshold
        self.minimum_threshold = minimum_threshold
        self.maximum_threshold = maximum_threshold
        self.adaptation_rate = adaptation_rate
        self.stability_window = stability_window
        self.minimum_requests = minimum_requests

        self._recent_failure_rates: Deque[float] = deque(maxlen=stability_window)

        logger.debug(
            f"Initialized {self.name} with initial_threshold={initial_failure_rate_threshold:.1%}, "
            f"adaptation_rate={adaptation_rate}"
        )

    def should_open(self, request_history: Deque['RequestRecord'], config: 'CircuitBreakerConfig') -> bool:
        """Check with adaptive threshold."""
        if not request_history or len(request_history) < self.minimum_requests:
            return False

        # Calculate current failure rate
        failure_count = sum(1 for record in request_history if not record.success)
        current_rate = failure_count / len(request_history)

        # Update history
        self._recent_failure_rates.append(current_rate)

        # Adapt threshold based on stability
        if len(self._recent_failure_rates) >= self.minimum_requests:
            self._adapt_threshold()

        should_open = current_rate >= self.current_threshold

        if should_open:
            logger.info(
                f"{self.name}: Failure rate {current_rate:.1%} exceeds adaptive threshold "
                f"{self.current_threshold:.1%}"
            )

        return should_open

    def _adapt_threshold(self) -> None:
        """Adapt threshold based on recent patterns."""
        if len(self._recent_failure_rates) < 2:
            return

        # Measure stability using standard deviation
        try:
            stdev = statistics.stdev(self._recent_failure_rates)
            mean_rate = statistics.mean(self._recent_failure_rates)

            # High stability (low stdev): become more sensitive (lower threshold)
            # Low stability (high stdev): become more tolerant (higher threshold)

            # Normalize stdev to 0-1 range (assuming max stdev is ~0.5)
            normalized_volatility = min(stdev / 0.5, 1.0)

            # Calculate target threshold
            # High volatility -> higher threshold
            # Low volatility -> lower threshold
            target_threshold = (
                self.minimum_threshold +
                (self.maximum_threshold - self.minimum_threshold) * normalized_volatility
            )

            # Gradually move toward target
            old_threshold = self.current_threshold
            self.current_threshold = (
                self.current_threshold * (1 - self.adaptation_rate) +
                target_threshold * self.adaptation_rate
            )

            # Clamp to bounds
            self.current_threshold = max(
                self.minimum_threshold,
                min(self.maximum_threshold, self.current_threshold)
            )

            if abs(self.current_threshold - old_threshold) > 0.05:
                logger.debug(
                    f"{self.name}: Adapted threshold {old_threshold:.1%} -> "
                    f"{self.current_threshold:.1%} (volatility={normalized_volatility:.2f})"
                )

        except statistics.StatisticsError:
            pass

    def reset(self) -> None:
        """Reset adaptive detector state."""
        self._recent_failure_rates.clear()

    def __repr__(self) -> str:
        return f"AdaptiveDetector(current_threshold={self.current_threshold:.1%})"

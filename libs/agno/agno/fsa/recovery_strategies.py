"""
Recovery Strategies for Circuit Breaker FSA

This module provides multiple recovery strategies for transitioning
from OPEN to HALF_OPEN and eventually back to CLOSED state.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import logging
import random

logger = logging.getLogger(__name__)


# ============================================================================
# Base Classes
# ============================================================================


class RecoveryStrategy(ABC):
    """
    Abstract base class for recovery strategies.

    Recovery strategies determine when and how a circuit breaker
    should attempt to recover from OPEN state.
    """

    def __init__(self, name: str = "recovery_strategy"):
        """
        Initialize recovery strategy.

        Args:
            name: Name identifier for this strategy
        """
        self.name = name
        self._recovery_attempts = 0
        self._last_recovery_attempt: Optional[datetime] = None

    @abstractmethod
    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: 'CircuitBreakerConfig'
    ) -> datetime:
        """
        Calculate when the next recovery attempt should occur.

        Args:
            current_attempt: Number of recovery attempts so far
            last_failure_time: Time of last failure
            config: Circuit breaker configuration

        Returns:
            Datetime when next attempt should occur
        """
        pass

    def should_attempt_recovery(self, last_failure_time: datetime) -> bool:
        """
        Check if recovery should be attempted now.

        Args:
            last_failure_time: Time of last failure

        Returns:
            True if recovery should be attempted
        """
        if self._last_recovery_attempt is None:
            return True

        next_attempt = self.calculate_next_attempt_time(
            self._recovery_attempts,
            last_failure_time,
            None
        )

        return datetime.now() >= next_attempt

    def on_recovery_success(self) -> None:
        """Called when recovery succeeds."""
        self._recovery_attempts = 0
        self._last_recovery_attempt = None
        logger.info(f"{self.name}: Recovery successful, reset attempts")

    def on_recovery_failure(self) -> None:
        """Called when recovery fails."""
        self._recovery_attempts += 1
        self._last_recovery_attempt = datetime.now()
        logger.info(f"{self.name}: Recovery failed, attempts={self._recovery_attempts}")

    def reset(self) -> None:
        """Reset recovery state."""
        self._recovery_attempts = 0
        self._last_recovery_attempt = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', attempts={self._recovery_attempts})"


# ============================================================================
# Exponential Backoff Recovery
# ============================================================================


class ExponentialBackoffRecovery(RecoveryStrategy):
    """
    Recovery with exponential backoff between attempts.

    Wait time doubles after each failed recovery attempt:
    1s -> 2s -> 4s -> 8s -> 16s -> ...

    This prevents overwhelming a failing service with recovery attempts.

    Example:
        >>> strategy = ExponentialBackoffRecovery(
        ...     initial_delay_seconds=1.0,
        ...     max_delay_seconds=300.0,
        ...     multiplier=2.0
        ... )
    """

    def __init__(
        self,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 300.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        name: str = "exponential_backoff_recovery"
    ):
        """
        Initialize exponential backoff recovery.

        Args:
            initial_delay_seconds: Initial delay before first recovery
            max_delay_seconds: Maximum delay between attempts
            multiplier: Multiplier for each attempt
            jitter: Add random jitter to prevent thundering herd
            name: Strategy name
        """
        super().__init__(name)
        self.initial_delay = initial_delay_seconds
        self.max_delay = max_delay_seconds
        self.multiplier = multiplier
        self.jitter = jitter

        logger.debug(
            f"Initialized {self.name} with initial_delay={initial_delay_seconds}s, "
            f"max_delay={max_delay_seconds}s, multiplier={multiplier}"
        )

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt time with exponential backoff."""
        # Calculate exponential delay
        delay = min(
            self.initial_delay * (self.multiplier ** current_attempt),
            self.max_delay
        )

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * 0.1 * random.random()  # 0-10% jitter
            delay = delay + jitter_amount

        next_attempt = last_failure_time + timedelta(seconds=delay)

        logger.debug(
            f"{self.name}: Next attempt in {delay:.2f}s (attempt {current_attempt + 1})"
        )

        return next_attempt

    def __repr__(self) -> str:
        return (
            f"ExponentialBackoffRecovery(initial={self.initial_delay}s, "
            f"max={self.max_delay}s, multiplier={self.multiplier})"
        )


# ============================================================================
# Fixed Delay Recovery
# ============================================================================


class FixedDelayRecovery(RecoveryStrategy):
    """
    Recovery with fixed delay between attempts.

    Waits a constant amount of time between recovery attempts.
    Simple but predictable strategy.

    Example:
        >>> strategy = FixedDelayRecovery(delay_seconds=60.0)
    """

    def __init__(
        self,
        delay_seconds: float = 60.0,
        jitter: bool = False,
        name: str = "fixed_delay_recovery"
    ):
        """
        Initialize fixed delay recovery.

        Args:
            delay_seconds: Fixed delay between attempts
            jitter: Add random jitter
            name: Strategy name
        """
        super().__init__(name)
        self.delay = delay_seconds
        self.jitter = jitter

        logger.debug(f"Initialized {self.name} with delay={delay_seconds}s")

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt time with fixed delay."""
        delay = self.delay

        # Add jitter if enabled
        if self.jitter:
            jitter_amount = delay * 0.1 * random.random()
            delay = delay + jitter_amount

        return last_failure_time + timedelta(seconds=delay)

    def __repr__(self) -> str:
        return f"FixedDelayRecovery(delay={self.delay}s)"


# ============================================================================
# Adaptive Recovery
# ============================================================================


@dataclass
class RecoveryPattern:
    """Pattern learned from recovery attempts."""
    time_of_day_success_rate: Dict[int, float]  # Hour -> success rate
    day_of_week_success_rate: Dict[int, float]  # Day -> success rate
    avg_recovery_time_seconds: float
    last_successful_recovery: Optional[datetime] = None


class AdaptiveRecovery(RecoveryStrategy):
    """
    Adaptive recovery that learns from past patterns.

    Learns optimal recovery timing based on historical success patterns.
    Adapts delays based on time of day, day of week, and past success rates.

    Example:
        >>> strategy = AdaptiveRecovery(
        ...     learning_rate=0.1,
        ...     min_delay_seconds=10.0,
        ...     max_delay_seconds=600.0
        ... )
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        min_delay_seconds: float = 10.0,
        max_delay_seconds: float = 600.0,
        name: str = "adaptive_recovery"
    ):
        """
        Initialize adaptive recovery.

        Args:
            learning_rate: Rate of adaptation (0.0-1.0)
            min_delay_seconds: Minimum delay
            max_delay_seconds: Maximum delay
            name: Strategy name
        """
        super().__init__(name)
        self.learning_rate = learning_rate
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds

        # Learning data
        self._current_delay = min_delay_seconds
        self._success_history: List[bool] = []
        self._time_of_day_success: Dict[int, List[bool]] = {h: [] for h in range(24)}
        self._recovery_times: List[float] = []

        logger.debug(
            f"Initialized {self.name} with learning_rate={learning_rate}, "
            f"delay_range=[{min_delay_seconds}, {max_delay_seconds}]s"
        )

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt time adaptively."""
        # Get current context
        current_hour = datetime.now().hour

        # Calculate base delay
        if self._success_history:
            # Adapt based on recent success rate
            recent_successes = sum(self._success_history[-10:])
            recent_attempts = len(self._success_history[-10:])
            success_rate = recent_successes / recent_attempts if recent_attempts > 0 else 0.5

            # Higher success rate -> shorter delay
            # Lower success rate -> longer delay
            delay_factor = 1.0 - (success_rate * 0.5)  # 0.5-1.0 range
            self._current_delay = self.min_delay + (self.max_delay - self.min_delay) * delay_factor
        else:
            self._current_delay = self.min_delay

        # Adjust for time of day
        if current_hour in self._time_of_day_success and self._time_of_day_success[current_hour]:
            hour_successes = sum(self._time_of_day_success[current_hour])
            hour_attempts = len(self._time_of_day_success[current_hour])
            hour_success_rate = hour_successes / hour_attempts

            # Adjust delay based on historical success at this hour
            time_factor = 1.0 - (hour_success_rate * 0.3)  # 0.7-1.0 range
            self._current_delay *= time_factor

        # Clamp to bounds
        self._current_delay = max(self.min_delay, min(self.max_delay, self._current_delay))

        next_attempt = last_failure_time + timedelta(seconds=self._current_delay)

        logger.debug(
            f"{self.name}: Adaptive delay {self._current_delay:.2f}s "
            f"(hour={current_hour}, attempt={current_attempt + 1})"
        )

        return next_attempt

    def on_recovery_success(self) -> None:
        """Learn from successful recovery."""
        super().on_recovery_success()

        # Record success
        self._success_history.append(True)
        current_hour = datetime.now().hour
        self._time_of_day_success[current_hour].append(True)

        # Decrease delay on success (learn that shorter delays work)
        self._current_delay = max(
            self.min_delay,
            self._current_delay * (1.0 - self.learning_rate)
        )

        logger.debug(f"{self.name}: Learned from success, adjusted delay to {self._current_delay:.2f}s")

    def on_recovery_failure(self) -> None:
        """Learn from failed recovery."""
        super().on_recovery_failure()

        # Record failure
        self._success_history.append(False)
        current_hour = datetime.now().hour
        self._time_of_day_success[current_hour].append(False)

        # Increase delay on failure (learn that longer delays needed)
        self._current_delay = min(
            self.max_delay,
            self._current_delay * (1.0 + self.learning_rate)
        )

        logger.debug(f"{self.name}: Learned from failure, adjusted delay to {self._current_delay:.2f}s")

    def reset(self) -> None:
        """Reset adaptive state."""
        super().reset()
        self._current_delay = self.min_delay
        # Keep learned patterns

    def __repr__(self) -> str:
        success_rate = (
            sum(self._success_history) / len(self._success_history)
            if self._success_history else 0.0
        )
        return (
            f"AdaptiveRecovery(current_delay={self._current_delay:.2f}s, "
            f"success_rate={success_rate:.1%})"
        )


# ============================================================================
# Health Check Recovery
# ============================================================================


class HealthCheckRecovery(RecoveryStrategy):
    """
    Recovery based on health check probes.

    Actively probes the service with health checks before attempting
    recovery. Only transitions to HALF_OPEN when health checks pass.

    Example:
        >>> def health_check():
        ...     response = requests.get("https://api.example.com/health")
        ...     return response.status_code == 200
        >>>
        >>> strategy = HealthCheckRecovery(
        ...     health_check=health_check,
        ...     check_interval_seconds=10.0
        ... )
    """

    def __init__(
        self,
        health_check: Callable[[], bool],
        check_interval_seconds: float = 10.0,
        consecutive_successes_required: int = 2,
        timeout_seconds: float = 5.0,
        name: str = "health_check_recovery"
    ):
        """
        Initialize health check recovery.

        Args:
            health_check: Function that returns True if service is healthy
            check_interval_seconds: Interval between health checks
            consecutive_successes_required: Number of successful checks needed
            timeout_seconds: Timeout for health check calls
            name: Strategy name
        """
        super().__init__(name)
        self.health_check = health_check
        self.check_interval = check_interval_seconds
        self.consecutive_successes_required = consecutive_successes_required
        self.timeout = timeout_seconds

        self._consecutive_successes = 0
        self._last_check_time: Optional[datetime] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._is_healthy = False
        self._shutdown_event = threading.Event()

        logger.debug(
            f"Initialized {self.name} with check_interval={check_interval_seconds}s, "
            f"required_successes={consecutive_successes_required}"
        )

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt based on health checks."""
        # If health checks are passing, attempt immediately
        if self._is_healthy:
            return datetime.now()

        # Otherwise, wait for next check interval
        if self._last_check_time:
            return self._last_check_time + timedelta(seconds=self.check_interval)

        return last_failure_time + timedelta(seconds=self.check_interval)

    def should_attempt_recovery(self, last_failure_time: datetime) -> bool:
        """Only attempt recovery if health checks are passing."""
        # Start health check thread if not running
        if not self._health_check_thread or not self._health_check_thread.is_alive():
            self._start_health_check_thread()

        return self._is_healthy

    def _start_health_check_thread(self) -> None:
        """Start background health check thread."""
        def health_check_loop():
            while not self._shutdown_event.is_set():
                try:
                    # Perform health check with timeout
                    start_time = time.time()
                    is_healthy = self._run_health_check_with_timeout()
                    duration = time.time() - start_time

                    self._last_check_time = datetime.now()

                    if is_healthy:
                        self._consecutive_successes += 1
                        logger.debug(
                            f"{self.name}: Health check passed "
                            f"({self._consecutive_successes}/{self.consecutive_successes_required}) "
                            f"in {duration:.3f}s"
                        )

                        # Mark healthy if enough consecutive successes
                        if self._consecutive_successes >= self.consecutive_successes_required:
                            if not self._is_healthy:
                                logger.info(f"{self.name}: Service is now healthy")
                            self._is_healthy = True
                    else:
                        logger.debug(f"{self.name}: Health check failed")
                        self._consecutive_successes = 0
                        self._is_healthy = False

                except Exception as e:
                    logger.warning(f"{self.name}: Health check error: {e}")
                    self._consecutive_successes = 0
                    self._is_healthy = False

                # Wait for next check
                self._shutdown_event.wait(self.check_interval)

        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True,
            name=f"HealthCheckRecovery-{self.name}"
        )
        self._health_check_thread.start()

    def _run_health_check_with_timeout(self) -> bool:
        """Run health check with timeout."""
        result = [False]
        exception = [None]

        def check():
            try:
                result[0] = self.health_check()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            logger.warning(f"{self.name}: Health check timed out after {self.timeout}s")
            return False

        if exception[0]:
            raise exception[0]

        return result[0]

    def on_recovery_success(self) -> None:
        """Called when recovery succeeds."""
        super().on_recovery_success()
        self._consecutive_successes = 0

    def on_recovery_failure(self) -> None:
        """Called when recovery fails."""
        super().on_recovery_failure()
        self._consecutive_successes = 0
        self._is_healthy = False

    def shutdown(self) -> None:
        """Shutdown health check thread."""
        self._shutdown_event.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)

    def __repr__(self) -> str:
        return (
            f"HealthCheckRecovery(healthy={self._is_healthy}, "
            f"successes={self._consecutive_successes}/{self.consecutive_successes_required})"
        )


# ============================================================================
# Manual Recovery
# ============================================================================


class ManualRecovery(RecoveryStrategy):
    """
    Manual recovery requiring operator intervention.

    Circuit remains OPEN until manually reset by operator.
    Useful for critical failures requiring human investigation.

    Example:
        >>> strategy = ManualRecovery()
        >>> # Circuit stays OPEN until:
        >>> strategy.allow_recovery()
    """

    def __init__(self, name: str = "manual_recovery"):
        """
        Initialize manual recovery.

        Args:
            name: Strategy name
        """
        super().__init__(name)
        self._recovery_allowed = False

        logger.debug(f"Initialized {self.name} - requires manual intervention")

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Never automatically attempts recovery."""
        # Return far future to prevent automatic recovery
        return datetime.max

    def should_attempt_recovery(self, last_failure_time: datetime) -> bool:
        """Only attempt recovery if manually allowed."""
        return self._recovery_allowed

    def allow_recovery(self) -> None:
        """Manually allow recovery attempt."""
        self._recovery_allowed = True
        logger.info(f"{self.name}: Recovery manually allowed")

    def deny_recovery(self) -> None:
        """Deny recovery attempts."""
        self._recovery_allowed = False
        logger.info(f"{self.name}: Recovery manually denied")

    def on_recovery_success(self) -> None:
        """Called when recovery succeeds."""
        super().on_recovery_success()
        self._recovery_allowed = False

    def on_recovery_failure(self) -> None:
        """Called when recovery fails."""
        super().on_recovery_failure()
        self._recovery_allowed = False

    def reset(self) -> None:
        """Reset manual recovery state."""
        super().reset()
        self._recovery_allowed = False

    def __repr__(self) -> str:
        return f"ManualRecovery(allowed={self._recovery_allowed})"


# ============================================================================
# Gradual Recovery
# ============================================================================


class GradualRecovery(RecoveryStrategy):
    """
    Gradual recovery with incremental traffic increase.

    Slowly increases traffic percentage during recovery to avoid
    overwhelming a recovering service. Implements a "ramp-up" pattern.

    Example:
        >>> strategy = GradualRecovery(
        ...     initial_traffic_percentage=0.1,  # Start with 10%
        ...     increment_percentage=0.1,  # Increase by 10%
        ...     increment_interval_seconds=30.0  # Every 30 seconds
        ... )
    """

    def __init__(
        self,
        initial_traffic_percentage: float = 0.1,
        increment_percentage: float = 0.1,
        increment_interval_seconds: float = 30.0,
        success_threshold_percentage: float = 0.8,
        name: str = "gradual_recovery"
    ):
        """
        Initialize gradual recovery.

        Args:
            initial_traffic_percentage: Starting traffic percentage (0.0-1.0)
            increment_percentage: Traffic increase per interval (0.0-1.0)
            increment_interval_seconds: Seconds between increments
            success_threshold_percentage: Success rate to allow increment
            name: Strategy name
        """
        super().__init__(name)
        self.initial_percentage = initial_traffic_percentage
        self.increment_percentage = increment_percentage
        self.increment_interval = increment_interval_seconds
        self.success_threshold = success_threshold_percentage

        self._current_percentage = initial_traffic_percentage
        self._last_increment_time: Optional[datetime] = None
        self._successful_requests = 0
        self._total_requests = 0

        logger.debug(
            f"Initialized {self.name} with initial={initial_traffic_percentage:.0%}, "
            f"increment={increment_percentage:.0%}, interval={increment_interval_seconds}s"
        )

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt time."""
        # First attempt happens after initial delay
        if self._last_increment_time is None:
            return last_failure_time + timedelta(seconds=self.increment_interval)

        return self._last_increment_time + timedelta(seconds=self.increment_interval)

    def should_allow_request(self) -> bool:
        """
        Determine if a request should be allowed based on current traffic percentage.

        Returns:
            True if request should be allowed
        """
        # Use random sampling to achieve desired percentage
        return random.random() < self._current_percentage

    def record_request_result(self, success: bool) -> None:
        """
        Record result of a request during recovery.

        Args:
            success: Whether request succeeded
        """
        self._total_requests += 1
        if success:
            self._successful_requests += 1

        # Check if we should increment traffic
        if self._should_increment_traffic():
            self._increment_traffic()

    def _should_increment_traffic(self) -> bool:
        """Check if traffic should be incremented."""
        if self._current_percentage >= 1.0:
            return False

        # Need minimum requests before incrementing
        if self._total_requests < 10:
            return False

        # Check success rate
        success_rate = self._successful_requests / self._total_requests
        if success_rate < self.success_threshold:
            return False

        # Check if enough time has passed
        if self._last_increment_time is None:
            return True

        time_since_increment = (datetime.now() - self._last_increment_time).total_seconds()
        return time_since_increment >= self.increment_interval

    def _increment_traffic(self) -> None:
        """Increment traffic percentage."""
        old_percentage = self._current_percentage
        self._current_percentage = min(1.0, self._current_percentage + self.increment_percentage)
        self._last_increment_time = datetime.now()

        # Reset counters
        self._successful_requests = 0
        self._total_requests = 0

        logger.info(
            f"{self.name}: Incremented traffic {old_percentage:.0%} -> "
            f"{self._current_percentage:.0%}"
        )

    def on_recovery_success(self) -> None:
        """Called when recovery succeeds (100% traffic)."""
        super().on_recovery_success()
        self._current_percentage = 1.0
        logger.info(f"{self.name}: Full recovery achieved (100% traffic)")

    def on_recovery_failure(self) -> None:
        """Called when recovery fails."""
        super().on_recovery_failure()
        # Reset to initial percentage
        self._current_percentage = self.initial_percentage
        self._last_increment_time = None
        self._successful_requests = 0
        self._total_requests = 0
        logger.info(f"{self.name}: Recovery failed, reset to {self._current_percentage:.0%} traffic")

    def reset(self) -> None:
        """Reset gradual recovery state."""
        super().reset()
        self._current_percentage = self.initial_percentage
        self._last_increment_time = None
        self._successful_requests = 0
        self._total_requests = 0

    def get_current_traffic_percentage(self) -> float:
        """Get current traffic percentage."""
        return self._current_percentage

    def __repr__(self) -> str:
        return f"GradualRecovery(current_traffic={self._current_percentage:.0%})"


# ============================================================================
# Scheduled Recovery
# ============================================================================


class ScheduledRecovery(RecoveryStrategy):
    """
    Recovery at scheduled times (e.g., during maintenance windows).

    Only attempts recovery during specified time windows.
    Useful for services with known maintenance schedules.

    Example:
        >>> strategy = ScheduledRecovery(
        ...     allowed_hours=[2, 3, 4],  # 2 AM - 4 AM
        ...     allowed_days_of_week=[5, 6]  # Saturday, Sunday
        ... )
    """

    def __init__(
        self,
        allowed_hours: Optional[List[int]] = None,
        allowed_days_of_week: Optional[List[int]] = None,
        timezone_offset_hours: int = 0,
        name: str = "scheduled_recovery"
    ):
        """
        Initialize scheduled recovery.

        Args:
            allowed_hours: List of hours (0-23) when recovery is allowed
            allowed_days_of_week: List of days (0=Monday, 6=Sunday) when recovery is allowed
            timezone_offset_hours: Timezone offset from UTC
            name: Strategy name
        """
        super().__init__(name)
        self.allowed_hours = allowed_hours or list(range(24))  # All hours by default
        self.allowed_days = allowed_days_of_week or list(range(7))  # All days by default
        self.timezone_offset = timezone_offset_hours

        logger.debug(
            f"Initialized {self.name} with hours={allowed_hours}, days={allowed_days_of_week}"
        )

    def calculate_next_attempt_time(
        self,
        current_attempt: int,
        last_failure_time: datetime,
        config: Optional['CircuitBreakerConfig'] = None
    ) -> datetime:
        """Calculate next attempt time within allowed schedule."""
        now = datetime.now()
        current_hour = (now.hour + self.timezone_offset) % 24
        current_day = now.weekday()

        # If currently in allowed window, return now
        if self._is_in_allowed_window(current_hour, current_day):
            return now

        # Find next allowed window
        next_attempt = now
        while not self._is_in_allowed_window(
            (next_attempt.hour + self.timezone_offset) % 24,
            next_attempt.weekday()
        ):
            next_attempt += timedelta(hours=1)

            # Safety limit
            if (next_attempt - now).total_seconds() > 7 * 24 * 3600:  # 1 week
                logger.warning(f"{self.name}: No allowed window found in next week")
                break

        return next_attempt

    def _is_in_allowed_window(self, hour: int, day_of_week: int) -> bool:
        """Check if time is in allowed recovery window."""
        return hour in self.allowed_hours and day_of_week in self.allowed_days

    def should_attempt_recovery(self, last_failure_time: datetime) -> bool:
        """Only attempt recovery during allowed windows."""
        now = datetime.now()
        current_hour = (now.hour + self.timezone_offset) % 24
        current_day = now.weekday()

        is_allowed = self._is_in_allowed_window(current_hour, current_day)

        if not is_allowed:
            logger.debug(
                f"{self.name}: Outside allowed recovery window "
                f"(hour={current_hour}, day={current_day})"
            )

        return is_allowed

    def __repr__(self) -> str:
        return f"ScheduledRecovery(hours={self.allowed_hours}, days={self.allowed_days})"

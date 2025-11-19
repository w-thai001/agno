"""Health Check Finite State Automaton for service health monitoring."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for health checking."""
    IDLE = "idle"
    CHECKING = "checking"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Represents a health check."""
    name: str
    check_fn: Callable[[], bool]
    critical: bool = True
    timeout: float = 5.0
    threshold: Optional[float] = None


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    success: bool
    value: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class HealthCheckFSA:
    """Finite State Automaton for health checking."""

    def __init__(self):
        self.state = State.IDLE
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, CheckResult] = {}
        self._last_check_time: float = 0.0
        logger.info("Health check system initialized")

    def register(
        self,
        name: str,
        check_fn: Callable[[], bool],
        critical: bool = True,
        timeout: float = 5.0,
        threshold: Optional[float] = None
    ):
        """Register a health check."""
        check = HealthCheck(
            name=name,
            check_fn=check_fn,
            critical=critical,
            timeout=timeout,
            threshold=threshold
        )
        self._checks[name] = check
        logger.debug(f"Registered {'critical' if critical else 'non-critical'} check: {name}")

    def check_health(self) -> HealthStatus:
        """Execute all health checks and determine overall status."""
        self._transition(self.state, State.CHECKING)
        self._last_check_time = time.time()

        logger.info(f"Running {len(self._checks)} health checks")

        critical_failures = 0
        non_critical_failures = 0

        for name, health_check in self._checks.items():
            result = self._execute_check(health_check)
            self._results[name] = result

            if not result.success:
                if health_check.critical:
                    critical_failures += 1
                    logger.warning(f"Critical check failed: {name}")
                else:
                    non_critical_failures += 1
                    logger.warning(f"Non-critical check failed: {name}")

        # Determine overall health
        overall_status = self._determine_status(critical_failures, non_critical_failures)
        self._transition_to_health_state(overall_status)

        return overall_status

    def get_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            "status": self._get_health_status().value,
            "state": self.state.value,
            "timestamp": self._last_check_time,
            "checks": {
                name: {
                    "status": result.status.value,
                    "success": result.success,
                    "duration": result.duration,
                    "error": result.error
                }
                for name, result in self._results.items()
            },
            "summary": {
                "total": len(self._checks),
                "passed": sum(1 for r in self._results.values() if r.success),
                "failed": sum(1 for r in self._results.values() if not r.success)
            }
        }

    def get_check_result(self, name: str) -> Optional[CheckResult]:
        """Get result of a specific check."""
        return self._results.get(name)

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.state == State.HEALTHY

    def is_degraded(self) -> bool:
        """Check if system is degraded."""
        return self.state == State.DEGRADED

    def is_unhealthy(self) -> bool:
        """Check if system is unhealthy."""
        return self.state == State.UNHEALTHY

    def clear_checks(self):
        """Clear all registered checks."""
        self._checks.clear()
        self._results.clear()
        self._transition(self.state, State.IDLE)
        logger.info("Cleared all health checks")

    def _execute_check(self, health_check: HealthCheck) -> CheckResult:
        """Execute a single health check."""
        start_time = time.time()

        try:
            result = health_check.check_fn()
            duration = time.time() - start_time

            # Evaluate result
            if isinstance(result, bool):
                success = result
                value = result
            elif isinstance(result, (int, float)):
                value = result
                if health_check.threshold is not None:
                    success = result <= health_check.threshold
                else:
                    success = result > 0
            else:
                success = bool(result)
                value = result

            status = HealthStatus.HEALTHY if success else (
                HealthStatus.UNHEALTHY if health_check.critical else HealthStatus.DEGRADED
            )

            return CheckResult(
                name=health_check.name,
                status=status,
                success=success,
                value=value,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Health check {health_check.name} failed: {e}")

            status = HealthStatus.UNHEALTHY if health_check.critical else HealthStatus.DEGRADED

            return CheckResult(
                name=health_check.name,
                status=status,
                success=False,
                error=str(e),
                duration=duration
            )

    def _determine_status(self, critical_failures: int, non_critical_failures: int) -> HealthStatus:
        """Determine overall health status."""
        if critical_failures > 0:
            return HealthStatus.UNHEALTHY
        elif non_critical_failures > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _transition_to_health_state(self, status: HealthStatus):
        """Transition to health state based on status."""
        if status == HealthStatus.HEALTHY:
            self._transition(State.CHECKING, State.HEALTHY)
        elif status == HealthStatus.DEGRADED:
            self._transition(State.CHECKING, State.DEGRADED)
        else:
            self._transition(State.CHECKING, State.UNHEALTHY)

    def _get_health_status(self) -> HealthStatus:
        """Get current health status from state."""
        if self.state == State.HEALTHY:
            return HealthStatus.HEALTHY
        elif self.state == State.DEGRADED:
            return HealthStatus.DEGRADED
        elif self.state == State.UNHEALTHY:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.HEALTHY

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

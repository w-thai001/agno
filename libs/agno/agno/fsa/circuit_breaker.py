"""
FSA Circuit Breaker

Resilience pattern for FSA execution:
- Automatic failure detection
- Circuit states (Closed, Open, Half-Open)
- Failure threshold monitoring
- Automatic recovery attempts
- Fallback execution
- Health-based circuit control

Prevents cascading failures and enables graceful degradation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
import time

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class CircuitState(str, Enum):
    """Circuit Breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerState(str, Enum):
    """States for Circuit Breaker FSA"""
    INITIAL = "initial"
    MONITORING = "monitoring"
    EVALUATING = "evaluating"
    EXECUTING = "executing"
    RECOVERING = "recovering"
    SUCCESS = "success"
    FAILED = "failed"


class CircuitMetrics(BaseModel):
    """Circuit breaker metrics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    consecutive_failures: int
    last_failure_time: Optional[str]
    circuit_state: CircuitState
    failure_rate: float
    avg_response_time: float


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""
    failure_threshold: int  # Number of failures to open circuit
    success_threshold: int  # Number of successes to close circuit
    timeout_seconds: float  # Time to wait before half-open
    failure_rate_threshold: float  # Max failure rate (0.0-1.0)
    slow_call_threshold_ms: float  # Threshold for slow calls


class CircuitBreakerEvent(BaseModel):
    """Circuit breaker state change event"""
    timestamp: str
    from_state: CircuitState
    to_state: CircuitState
    reason: str
    metrics: CircuitMetrics


@dataclass
class FSACircuitBreaker(FSA):
    """
    FSA Circuit Breaker

    Implements circuit breaker pattern for FSA execution:
    - Monitors FSA execution failures
    - Opens circuit after threshold failures
    - Attempts recovery after timeout
    - Provides fallback execution
    - Prevents cascading failures

    Example:
        ```python
        # Create circuit breaker
        circuit_breaker = FSACircuitBreaker(
            name="CircuitBreaker",
            failure_threshold=5,
            timeout_seconds=60.0
        )

        # Wrap FSA execution
        result = circuit_breaker.execute_protected(
            my_fsa,
            context={"task": "test"},
            fallback=lambda ctx: {"result": "fallback"}
        )

        # Check circuit state
        if circuit_breaker.circuit_state == CircuitState.OPEN:
            print("Circuit is open - FSA is failing")
        ```
    """

    # Configuration
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    failure_rate_threshold: float = 0.5
    slow_call_threshold_ms: float = 5000.0

    # Circuit state
    circuit_state: CircuitState = CircuitState.CLOSED
    state_change_time: Optional[datetime] = None

    # Metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    response_times: List[float] = field(default_factory=list)

    # History
    state_changes: List[CircuitBreakerEvent] = field(default_factory=list)

    # Fallback
    fallback_function: Optional[Callable] = None

    def __post_init__(self):
        """Initialize circuit breaker"""
        self.initial_state = CircuitBreakerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {CircuitBreakerState.SUCCESS, CircuitBreakerState.FAILED}
        self.state_history = [self.current_state]

        self.state_change_time = datetime.now()

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSACircuitBreaker {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup circuit breaker workflow"""
        # INITIAL -> MONITORING
        self.add_transition(
            CircuitBreakerState.INITIAL,
            CircuitBreakerState.MONITORING,
            action=self._start_monitoring,
            description="Start monitoring"
        )

        # MONITORING -> EVALUATING
        self.add_transition(
            CircuitBreakerState.MONITORING,
            CircuitBreakerState.EVALUATING,
            condition=lambda ctx: ctx.get("request_received", False),
            action=self._evaluate_circuit,
            description="Evaluate circuit state"
        )

        # EVALUATING -> EXECUTING (circuit closed or half-open)
        self.add_transition(
            CircuitBreakerState.EVALUATING,
            CircuitBreakerState.EXECUTING,
            condition=lambda ctx: ctx.get("circuit_allows_request", False),
            action=self._execute_request,
            description="Execute request"
        )

        # EVALUATING -> FAILED (circuit open)
        self.add_transition(
            CircuitBreakerState.EVALUATING,
            CircuitBreakerState.FAILED,
            condition=lambda ctx: ctx.get("circuit_open", False),
            action=self._handle_circuit_open,
            description="Circuit open - reject request"
        )

        # EXECUTING -> SUCCESS
        self.add_transition(
            CircuitBreakerState.EXECUTING,
            CircuitBreakerState.SUCCESS,
            condition=lambda ctx: ctx.get("execution_success", False),
            action=self._record_success,
            description="Record successful execution"
        )

        # EXECUTING -> RECOVERING
        self.add_transition(
            CircuitBreakerState.EXECUTING,
            CircuitBreakerState.RECOVERING,
            condition=lambda ctx: ctx.get("execution_failed", False),
            action=self._record_failure,
            description="Record failure and attempt recovery"
        )

        # RECOVERING -> SUCCESS (fallback succeeded)
        self.add_transition(
            CircuitBreakerState.RECOVERING,
            CircuitBreakerState.SUCCESS,
            condition=lambda ctx: ctx.get("fallback_success", False),
            description="Fallback successful"
        )

        # RECOVERING -> FAILED (no fallback or fallback failed)
        self.add_transition(
            CircuitBreakerState.RECOVERING,
            CircuitBreakerState.FAILED,
            condition=lambda ctx: ctx.get("fallback_failed", False),
            description="Recovery failed"
        )

        # Error handling
        for state in CircuitBreakerState:
            if state not in [CircuitBreakerState.SUCCESS, CircuitBreakerState.FAILED]:
                self.add_transition(
                    state,
                    CircuitBreakerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _start_monitoring(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start circuit monitoring"""
        if self.debug_mode:
            logger.debug("Circuit breaker monitoring started")

        context["monitoring_active"] = True
        return context

    def _evaluate_circuit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate circuit state and decide if request is allowed"""
        current_state = self.circuit_state

        # Check if we should transition from OPEN to HALF_OPEN
        if current_state == CircuitState.OPEN:
            time_since_open = (datetime.now() - self.state_change_time).total_seconds()

            if time_since_open >= self.timeout_seconds:
                # Transition to HALF_OPEN to try recovery
                self._transition_circuit(CircuitState.HALF_OPEN, "Timeout expired, attempting recovery")
                context["circuit_allows_request"] = True
                context["circuit_open"] = False
            else:
                # Circuit still open, reject request
                context["circuit_allows_request"] = False
                context["circuit_open"] = True
        elif current_state in [CircuitState.CLOSED, CircuitState.HALF_OPEN]:
            # Allow request
            context["circuit_allows_request"] = True
            context["circuit_open"] = False

        context["circuit_state"] = self.circuit_state.value

        return context

    def _execute_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the protected FSA"""
        fsa = context.get("fsa")
        fsa_context = context.get("fsa_context", {})

        if not fsa:
            context["critical_error"] = True
            raise ValueError("No FSA provided for circuit breaker")

        # Execute FSA and measure time
        start_time = time.time()

        try:
            result = fsa.run(initial_context=fsa_context)
            elapsed_ms = (time.time() - start_time) * 1000

            self.response_times.append(elapsed_ms)
            self.total_requests += 1

            # Check if execution was successful and reasonably fast
            if result.success and elapsed_ms < self.slow_call_threshold_ms:
                context["execution_success"] = True
                context["execution_failed"] = False
                context["result"] = result
            else:
                # Consider slow calls as failures
                context["execution_success"] = False
                context["execution_failed"] = True
                context["failure_reason"] = "slow_call" if elapsed_ms >= self.slow_call_threshold_ms else "execution_failed"

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.response_times.append(elapsed_ms)
            self.total_requests += 1

            context["execution_success"] = False
            context["execution_failed"] = True
            context["error"] = str(e)
            context["failure_reason"] = "exception"

            if self.debug_mode:
                logger.error(f"FSA execution failed: {e}")

        return context

    def _record_success(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record successful execution"""
        self.successful_requests += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0

        if self.debug_mode:
            logger.debug(f"Success recorded. Consecutive successes: {self.consecutive_successes}")

        # If we're in HALF_OPEN and hit success threshold, close circuit
        if self.circuit_state == CircuitState.HALF_OPEN:
            if self.consecutive_successes >= self.success_threshold:
                self._transition_circuit(CircuitState.CLOSED, "Success threshold reached")

        context["success_recorded"] = True
        return context

    def _record_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record failed execution"""
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = datetime.now()

        failure_reason = context.get("failure_reason", "unknown")

        if self.debug_mode:
            logger.warning(f"Failure recorded ({failure_reason}). Consecutive failures: {self.consecutive_failures}")

        # Check if we should open the circuit
        failure_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0

        should_open = (
            self.consecutive_failures >= self.failure_threshold or
            failure_rate >= self.failure_rate_threshold
        )

        if should_open and self.circuit_state != CircuitState.OPEN:
            self._transition_circuit(
                CircuitState.OPEN,
                f"Failure threshold reached ({self.consecutive_failures} consecutive failures, {failure_rate:.1%} rate)"
            )

        # If we're in HALF_OPEN and get a failure, immediately open circuit
        if self.circuit_state == CircuitState.HALF_OPEN:
            self._transition_circuit(CircuitState.OPEN, "Failure during half-open state")

        # Try fallback if available
        if self.fallback_function or context.get("fallback"):
            fallback_fn = context.get("fallback") or self.fallback_function
            try:
                fallback_result = fallback_fn(context.get("fsa_context", {}))
                context["fallback_success"] = True
                context["fallback_failed"] = False
                context["result"] = fallback_result
                if self.debug_mode:
                    logger.info("Fallback executed successfully")
            except Exception as e:
                context["fallback_success"] = False
                context["fallback_failed"] = True
                context["fallback_error"] = str(e)
                if self.debug_mode:
                    logger.error(f"Fallback failed: {e}")
        else:
            context["fallback_success"] = False
            context["fallback_failed"] = True

        return context

    def _handle_circuit_open(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request when circuit is open"""
        if self.debug_mode:
            logger.warning("Request rejected - circuit is open")

        # Try fallback if available
        if self.fallback_function or context.get("fallback"):
            fallback_fn = context.get("fallback") or self.fallback_function
            try:
                fallback_result = fallback_fn(context.get("fsa_context", {}))
                context["result"] = fallback_result
                context["fallback_used"] = True
            except Exception as e:
                context["error"] = f"Circuit open and fallback failed: {e}"
        else:
            context["error"] = "Circuit breaker is open - request rejected"

        return context

    def _transition_circuit(self, new_state: CircuitState, reason: str) -> None:
        """Transition circuit to new state"""
        old_state = self.circuit_state
        self.circuit_state = new_state
        self.state_change_time = datetime.now()

        # Record state change event
        event = CircuitBreakerEvent(
            timestamp=self.state_change_time.isoformat(),
            from_state=old_state,
            to_state=new_state,
            reason=reason,
            metrics=self.get_metrics()
        )
        self.state_changes.append(event)

        if self.debug_mode:
            logger.info(f"Circuit state changed: {old_state.value} -> {new_state.value} ({reason})")

    def execute_protected(
        self,
        fsa: FSA,
        context: Optional[Dict[str, Any]] = None,
        fallback: Optional[Callable] = None
    ) -> Any:
        """
        Execute FSA with circuit breaker protection

        Args:
            fsa: FSA to execute
            context: Context for FSA execution
            fallback: Optional fallback function

        Returns:
            Execution result or fallback result
        """
        # Reset for new request
        self.reset()

        execution_context = {
            "request_received": True,
            "fsa": fsa,
            "fsa_context": context or {},
            "fallback": fallback
        }

        result = self.run(execution_context)

        return result.context.get("result")

    def get_metrics(self) -> CircuitMetrics:
        """Get current circuit breaker metrics"""
        failure_rate = (
            self.failed_requests / self.total_requests
            if self.total_requests > 0 else 0.0
        )

        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0.0
        )

        return CircuitMetrics(
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            consecutive_failures=self.consecutive_failures,
            last_failure_time=self.last_failure_time.isoformat() if self.last_failure_time else None,
            circuit_state=self.circuit_state,
            failure_rate=failure_rate,
            avg_response_time=avg_response_time
        )

    def reset_metrics(self) -> None:
        """Reset circuit breaker metrics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_failure_time = None
        self.response_times.clear()

        if self.debug_mode:
            logger.debug("Circuit breaker metrics reset")

    def get_state_history(self) -> List[CircuitBreakerEvent]:
        """Get circuit state change history"""
        return self.state_changes

    def is_call_permitted(self) -> bool:
        """Check if a call is currently permitted"""
        if self.circuit_state == CircuitState.CLOSED:
            return True
        elif self.circuit_state == CircuitState.HALF_OPEN:
            return True
        elif self.circuit_state == CircuitState.OPEN:
            # Check if timeout expired
            time_since_open = (datetime.now() - self.state_change_time).total_seconds()
            return time_since_open >= self.timeout_seconds
        return False

    def force_open(self, reason: str = "Manually opened") -> None:
        """Manually force circuit to open"""
        if self.circuit_state != CircuitState.OPEN:
            self._transition_circuit(CircuitState.OPEN, reason)

    def force_close(self, reason: str = "Manually closed") -> None:
        """Manually force circuit to close"""
        if self.circuit_state != CircuitState.CLOSED:
            self._transition_circuit(CircuitState.CLOSED, reason)
            self.consecutive_failures = 0
            self.consecutive_successes = 0

    def force_half_open(self, reason: str = "Manually set to half-open") -> None:
        """Manually force circuit to half-open"""
        if self.circuit_state != CircuitState.HALF_OPEN:
            self._transition_circuit(CircuitState.HALF_OPEN, reason)

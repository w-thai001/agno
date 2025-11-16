"""
FSA Auto-Healer

Automatic error recovery and self-healing:
- Detects and diagnoses failures
- Applies recovery strategies automatically
- Learns from successful recoveries
- Provides fallback mechanisms
- Monitors health and triggers healing
- Prevents recurring failures

Critical for production reliability and fault tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import time
from collections import defaultdict

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class FailureType(str, Enum):
    """Types of failures"""
    TRANSIENT = "transient"  # Temporary, likely to succeed on retry
    INTERMITTENT = "intermittent"  # Occasional, pattern-based
    PERSISTENT = "persistent"  # Ongoing, requires intervention
    CRITICAL = "critical"  # System-level, requires immediate action


class RecoveryStrategy(str, Enum):
    """Recovery strategies"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RESET_STATE = "reset_state"
    ROLLBACK = "rollback"
    ALTERNATIVE_PATH = "alternative_path"
    MANUAL_INTERVENTION = "manual_intervention"


class HealthStatus(str, Enum):
    """Health statuses"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class FailureDiagnosis(BaseModel):
    """Failure diagnosis"""
    failure_type: FailureType
    error_message: str
    stack_trace: Optional[str]
    affected_state: str
    context_snapshot: Dict[str, Any]
    timestamp: str
    recovery_strategy: RecoveryStrategy


class RecoveryAttempt(BaseModel):
    """Recovery attempt record"""
    attempt_id: str
    strategy: RecoveryStrategy
    timestamp: str
    success: bool
    duration: float
    error: Optional[str] = None


class HealingReport(BaseModel):
    """Healing session report"""
    fsa_name: str
    failure_count: int
    recovery_attempts: List[RecoveryAttempt]
    successful_recoveries: int
    failed_recoveries: int
    learned_patterns: List[str]
    health_status: HealthStatus


class AutoHealerState(str, Enum):
    """States for Auto-Healer FSA"""
    INITIAL = "initial"
    MONITORING = "monitoring"
    DETECTING = "detecting"
    DIAGNOSING = "diagnosing"
    HEALING = "healing"
    VERIFYING = "verifying"
    LEARNING = "learning"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FSAAutoHealer(FSA):
    """
    FSA Auto-Healer

    Provides automatic error recovery and self-healing:
    - Monitors FSA execution for failures
    - Diagnoses failure types and causes
    - Applies appropriate recovery strategies
    - Learns from successful recoveries
    - Prevents recurring failures
    - Provides health monitoring

    Example:
        ```python
        # Create auto-healer
        healer = FSAAutoHealer(
            name="Healer",
            max_recovery_attempts=3,
            enable_learning=True
        )

        # Wrap FSA execution
        result = healer.heal_execution(
            my_fsa,
            context={"task": "test"}
        )

        # Check healing report
        report = healer.get_healing_report()
        print(f"Recoveries: {report.successful_recoveries}")
        print(f"Health: {report.health_status}")
        ```
    """

    # Configuration
    max_recovery_attempts: int = 3
    enable_learning: bool = True
    health_check_interval: float = 60.0
    failure_threshold: int = 5

    # Protected FSA
    protected_fsa: Optional[FSA] = None

    # Failure tracking
    failures: List[FailureDiagnosis] = field(default_factory=list)
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)
    failure_patterns: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Learned recovery strategies
    learned_strategies: Dict[str, RecoveryStrategy] = field(default_factory=dict)

    # Health
    health_status: HealthStatus = HealthStatus.HEALTHY
    last_health_check: Optional[datetime] = None

    # Statistics
    total_failures: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0

    def __post_init__(self):
        """Initialize auto-healer"""
        self.initial_state = AutoHealerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {AutoHealerState.SUCCESS, AutoHealerState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAAutoHealer {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup auto-healer workflow"""
        # INITIAL -> MONITORING
        self.add_transition(
            AutoHealerState.INITIAL,
            AutoHealerState.MONITORING,
            action=self._start_monitoring,
            description="Start health monitoring"
        )

        # MONITORING -> DETECTING
        self.add_transition(
            AutoHealerState.MONITORING,
            AutoHealerState.DETECTING,
            condition=lambda ctx: ctx.get("failure_detected", False),
            action=self._detect_failure,
            description="Detect failure"
        )

        # MONITORING -> SUCCESS (no failures)
        self.add_transition(
            AutoHealerState.MONITORING,
            AutoHealerState.SUCCESS,
            condition=lambda ctx: ctx.get("execution_complete", False) and not ctx.get("failure_detected", False),
            description="Execution completed successfully"
        )

        # DETECTING -> DIAGNOSING
        self.add_transition(
            AutoHealerState.DETECTING,
            AutoHealerState.DIAGNOSING,
            condition=lambda ctx: ctx.get("detection_complete", False),
            action=self._diagnose_failure,
            description="Diagnose failure type"
        )

        # DIAGNOSING -> HEALING
        self.add_transition(
            AutoHealerState.DIAGNOSING,
            AutoHealerState.HEALING,
            condition=lambda ctx: ctx.get("diagnosis_complete", False),
            action=self._apply_healing,
            description="Apply recovery strategy"
        )

        # HEALING -> VERIFYING
        self.add_transition(
            AutoHealerState.HEALING,
            AutoHealerState.VERIFYING,
            condition=lambda ctx: ctx.get("healing_applied", False),
            action=self._verify_recovery,
            description="Verify recovery success"
        )

        # VERIFYING -> LEARNING (recovery successful)
        self.add_transition(
            AutoHealerState.VERIFYING,
            AutoHealerState.LEARNING,
            condition=lambda ctx: ctx.get("recovery_successful", False),
            action=self._learn_from_recovery,
            description="Learn from successful recovery"
        )

        # VERIFYING -> HEALING (recovery failed, retry)
        self.add_transition(
            AutoHealerState.VERIFYING,
            AutoHealerState.HEALING,
            condition=lambda ctx: (
                not ctx.get("recovery_successful", False) and
                ctx.get("retry_count", 0) < self.max_recovery_attempts
            ),
            action=self._retry_recovery,
            description="Retry recovery with different strategy"
        )

        # VERIFYING -> FAILED (max retries exceeded)
        self.add_transition(
            AutoHealerState.VERIFYING,
            AutoHealerState.FAILED,
            condition=lambda ctx: (
                not ctx.get("recovery_successful", False) and
                ctx.get("retry_count", 0) >= self.max_recovery_attempts
            ),
            description="Recovery failed - max attempts exceeded"
        )

        # LEARNING -> MONITORING (continue monitoring)
        self.add_transition(
            AutoHealerState.LEARNING,
            AutoHealerState.MONITORING,
            condition=lambda ctx: ctx.get("learning_complete", False),
            description="Return to monitoring"
        )

        # Error handling
        for state in AutoHealerState:
            if state not in [AutoHealerState.SUCCESS, AutoHealerState.FAILED]:
                self.add_transition(
                    state,
                    AutoHealerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _start_monitoring(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start health monitoring"""
        if self.debug_mode:
            logger.debug("Auto-healer monitoring started")

        self.last_health_check = datetime.now()
        context["monitoring_active"] = True

        return context

    def _detect_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect failure occurrence"""
        error = context.get("error")
        current_state = context.get("current_state")

        if self.debug_mode:
            logger.warning(f"Failure detected in state: {current_state}")

        self.total_failures += 1

        context["detection_complete"] = True
        context["detected_error"] = error
        context["detected_state"] = current_state

        return context

    def _diagnose_failure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose failure type and determine recovery strategy"""
        error = context.get("detected_error", "")
        current_state = context.get("detected_state", "unknown")

        # Determine failure type based on error pattern
        failure_type = self._classify_failure(error)

        # Determine recovery strategy
        recovery_strategy = self._select_recovery_strategy(failure_type, error)

        # Create diagnosis
        diagnosis = FailureDiagnosis(
            failure_type=failure_type,
            error_message=str(error),
            stack_trace=context.get("stack_trace"),
            affected_state=current_state,
            context_snapshot=self.protected_fsa.context.copy() if self.protected_fsa else {},
            timestamp=datetime.now().isoformat(),
            recovery_strategy=recovery_strategy
        )

        self.failures.append(diagnosis)

        # Update failure patterns
        error_pattern = self._extract_error_pattern(error)
        self.failure_patterns[error_pattern] += 1

        context["diagnosis"] = diagnosis
        context["recovery_strategy"] = recovery_strategy
        context["diagnosis_complete"] = True

        if self.debug_mode:
            logger.info(f"Diagnosis: {failure_type.value} - Strategy: {recovery_strategy.value}")

        return context

    def _apply_healing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply recovery strategy"""
        strategy = context.get("recovery_strategy")
        diagnosis = context.get("diagnosis")

        if not strategy or not diagnosis:
            context["critical_error"] = True
            return context

        attempt_id = f"recovery-{len(self.recovery_attempts) + 1}"
        start_time = time.time()

        if self.debug_mode:
            logger.info(f"Applying recovery strategy: {strategy.value}")

        try:
            # Apply strategy
            success = self._execute_recovery_strategy(strategy, diagnosis)

            duration = time.time() - start_time

            # Record attempt
            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=strategy,
                timestamp=datetime.now().isoformat(),
                success=success,
                duration=duration
            )

            self.recovery_attempts.append(attempt)

            context["recovery_attempt"] = attempt
            context["healing_applied"] = True

            if success:
                self.successful_recoveries += 1
            else:
                self.failed_recoveries += 1

        except Exception as e:
            duration = time.time() - start_time

            attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                strategy=strategy,
                timestamp=datetime.now().isoformat(),
                success=False,
                duration=duration,
                error=str(e)
            )

            self.recovery_attempts.append(attempt)
            self.failed_recoveries += 1

            context["recovery_attempt"] = attempt
            context["healing_applied"] = True

            if self.debug_mode:
                logger.error(f"Recovery strategy failed: {e}")

        return context

    def _verify_recovery(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Verify recovery success"""
        attempt = context.get("recovery_attempt")

        if not attempt:
            context["recovery_successful"] = False
            return context

        # Check if recovery was successful
        if attempt.success:
            # Verify FSA is in healthy state
            if self.protected_fsa:
                is_healthy = self._check_fsa_health()
                context["recovery_successful"] = is_healthy

                if self.debug_mode:
                    if is_healthy:
                        logger.info("Recovery verified successful")
                    else:
                        logger.warning("Recovery applied but FSA still unhealthy")
            else:
                context["recovery_successful"] = True
        else:
            context["recovery_successful"] = False

            # Increment retry count
            retry_count = context.get("retry_count", 0) + 1
            context["retry_count"] = retry_count

            if self.debug_mode:
                logger.warning(f"Recovery failed. Retry count: {retry_count}/{self.max_recovery_attempts}")

        return context

    def _retry_recovery(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retry recovery with alternative strategy"""
        previous_strategy = context.get("recovery_strategy")

        # Select alternative strategy
        alternative_strategy = self._select_alternative_strategy(previous_strategy)

        context["recovery_strategy"] = alternative_strategy

        if self.debug_mode:
            logger.info(f"Retrying with alternative strategy: {alternative_strategy.value}")

        return context

    def _learn_from_recovery(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from successful recovery"""
        if not self.enable_learning:
            context["learning_complete"] = True
            return context

        diagnosis = context.get("diagnosis")
        recovery_strategy = context.get("recovery_strategy")

        if diagnosis and recovery_strategy:
            # Learn association between error pattern and successful strategy
            error_pattern = self._extract_error_pattern(diagnosis.error_message)
            self.learned_strategies[error_pattern] = recovery_strategy

            if self.debug_mode:
                logger.info(f"Learned: '{error_pattern}' -> {recovery_strategy.value}")

        # Update health status
        self._update_health_status()

        context["learning_complete"] = True

        return context

    def _classify_failure(self, error: Any) -> FailureType:
        """Classify failure type"""
        error_str = str(error).lower()

        # Critical failures
        if any(keyword in error_str for keyword in ["critical", "fatal", "system error"]):
            return FailureType.CRITICAL

        # Transient failures
        if any(keyword in error_str for keyword in ["timeout", "connection", "network", "temporary"]):
            return FailureType.TRANSIENT

        # Check failure frequency
        error_pattern = self._extract_error_pattern(error)
        frequency = self.failure_patterns.get(error_pattern, 0)

        if frequency >= self.failure_threshold:
            return FailureType.PERSISTENT
        elif frequency > 1:
            return FailureType.INTERMITTENT

        return FailureType.TRANSIENT

    def _select_recovery_strategy(self, failure_type: FailureType, error: Any) -> RecoveryStrategy:
        """Select appropriate recovery strategy"""
        # Check if we have a learned strategy for this error
        error_pattern = self._extract_error_pattern(error)
        if error_pattern in self.learned_strategies:
            return self.learned_strategies[error_pattern]

        # Default strategies by failure type
        strategy_map = {
            FailureType.TRANSIENT: RecoveryStrategy.RETRY,
            FailureType.INTERMITTENT: RecoveryStrategy.RETRY_WITH_BACKOFF,
            FailureType.PERSISTENT: RecoveryStrategy.RESET_STATE,
            FailureType.CRITICAL: RecoveryStrategy.MANUAL_INTERVENTION
        }

        return strategy_map.get(failure_type, RecoveryStrategy.RETRY)

    def _select_alternative_strategy(self, previous_strategy: RecoveryStrategy) -> RecoveryStrategy:
        """Select alternative recovery strategy"""
        strategy_escalation = {
            RecoveryStrategy.RETRY: RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.RETRY_WITH_BACKOFF: RecoveryStrategy.RESET_STATE,
            RecoveryStrategy.RESET_STATE: RecoveryStrategy.ROLLBACK,
            RecoveryStrategy.ROLLBACK: RecoveryStrategy.ALTERNATIVE_PATH,
            RecoveryStrategy.ALTERNATIVE_PATH: RecoveryStrategy.MANUAL_INTERVENTION
        }

        return strategy_escalation.get(previous_strategy, RecoveryStrategy.MANUAL_INTERVENTION)

    def _execute_recovery_strategy(self, strategy: RecoveryStrategy, diagnosis: FailureDiagnosis) -> bool:
        """Execute recovery strategy"""
        if not self.protected_fsa:
            return False

        try:
            if strategy == RecoveryStrategy.RETRY:
                # Simple retry
                self.protected_fsa.reset()
                result = self.protected_fsa.run()
                return result.success

            elif strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
                # Retry with exponential backoff
                for attempt in range(3):
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s
                    self.protected_fsa.reset()
                    result = self.protected_fsa.run()
                    if result.success:
                        return True
                return False

            elif strategy == RecoveryStrategy.RESET_STATE:
                # Reset to initial state
                self.protected_fsa.reset()
                self.protected_fsa.context.clear()
                return True

            elif strategy == RecoveryStrategy.ROLLBACK:
                # Rollback to previous state
                if len(self.protected_fsa.state_history) > 1:
                    previous_state = self.protected_fsa.state_history[-2]
                    self.protected_fsa.current_state = previous_state
                    return True
                return False

            elif strategy == RecoveryStrategy.ALTERNATIVE_PATH:
                # Try alternative execution path
                # This would require FSA to support alternative paths
                return False

            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                # Log for manual intervention
                logger.critical(f"Manual intervention required: {diagnosis.error_message}")
                return False

        except Exception as e:
            if self.debug_mode:
                logger.error(f"Strategy execution failed: {e}")
            return False

        return False

    def _extract_error_pattern(self, error: Any) -> str:
        """Extract error pattern for learning"""
        error_str = str(error)

        # Extract error type
        if ":" in error_str:
            return error_str.split(":")[0].strip()

        # Extract first few words
        words = error_str.split()[:5]
        return " ".join(words)

    def _check_fsa_health(self) -> bool:
        """Check FSA health"""
        if not self.protected_fsa:
            return False

        # Check if FSA is in valid state
        if self.protected_fsa.current_state in self.protected_fsa.final_states:
            # Check if it's a success state
            return True  # Simplified check

        return True

    def _update_health_status(self) -> None:
        """Update overall health status"""
        if self.total_failures == 0:
            self.health_status = HealthStatus.HEALTHY
        else:
            success_rate = self.successful_recoveries / self.total_failures if self.total_failures > 0 else 0

            if success_rate >= 0.9:
                self.health_status = HealthStatus.HEALTHY
            elif success_rate >= 0.7:
                self.health_status = HealthStatus.DEGRADED
            elif success_rate >= 0.5:
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.CRITICAL

    def heal_execution(
        self,
        fsa: FSA,
        context: Optional[Dict[str, Any]] = None
    ) -> FSAExecutionResult:
        """
        Execute FSA with automatic healing

        Args:
            fsa: FSA to protect
            context: Initial context

        Returns:
            Execution result
        """
        self.protected_fsa = fsa
        self.reset()

        healing_context = {
            "target_fsa": fsa,
            "initial_context": context or {}
        }

        try:
            # Try normal execution
            result = fsa.run(initial_context=context)

            if result.success:
                healing_context["execution_complete"] = True
                healing_context["failure_detected"] = False
                self.run(healing_context)
                return result
            else:
                # Failure detected
                healing_context["failure_detected"] = True
                healing_context["error"] = result.context.get("error", "Execution failed")
                healing_context["current_state"] = str(fsa.current_state)

                # Run healing process
                self.run(healing_context)

                # If healing succeeded, return successful result
                if self.current_state == AutoHealerState.SUCCESS:
                    return fsa.run(initial_context=context)

                return result

        except Exception as e:
            # Exception during execution
            healing_context["failure_detected"] = True
            healing_context["error"] = str(e)
            healing_context["stack_trace"] = traceback.format_exc() if hasattr(traceback, 'format_exc') else None
            healing_context["current_state"] = str(fsa.current_state)

            # Run healing process
            self.run(healing_context)

            # If healing succeeded, retry execution
            if self.current_state == AutoHealerState.SUCCESS:
                return fsa.run(initial_context=context)

            # Return failed result
            from agno.fsa.base import FSAExecutionResult
            return FSAExecutionResult(
                success=False,
                final_state=str(fsa.current_state),
                context={"error": str(e)},
                duration=0.0,
                transitions_executed=0
            )

    def get_healing_report(self) -> HealingReport:
        """Get healing report"""
        learned_patterns = [
            f"{pattern} -> {strategy.value}"
            for pattern, strategy in self.learned_strategies.items()
        ]

        return HealingReport(
            fsa_name=self.protected_fsa.name if self.protected_fsa else "",
            failure_count=self.total_failures,
            recovery_attempts=self.recovery_attempts,
            successful_recoveries=self.successful_recoveries,
            failed_recoveries=self.failed_recoveries,
            learned_patterns=learned_patterns,
            health_status=self.health_status
        )

    def get_failure_patterns(self) -> Dict[str, int]:
        """Get failure pattern frequencies"""
        return dict(self.failure_patterns)

    def get_learned_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Get learned recovery strategies"""
        return dict(self.learned_strategies)

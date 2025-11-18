"""
Error Recovery Finite State Automaton (FSA) for Agno AI Agent Operations.

This module provides robust error detection, recovery, and resilience mechanisms for AI agent
operations. It automatically detects failures, executes recovery strategies, and maintains
operational continuity with minimal disruption.

Key Features:
- Multi-strategy error recovery (retry, fallback, rollback, circuit-breaker)
- Exponential backoff retry logic
- Circuit breaker pattern for cascading failure prevention
- State checkpoint and rollback capabilities
- Health monitoring and analytics
- Comprehensive error classification
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import traceback
from uuid import uuid4

from agno.exceptions import AgnoError, ModelProviderError, ModelRateLimitError


# Configure logging
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Classification of error types for recovery strategy selection."""

    TRANSIENT = "transient"  # Temporary errors (network blips, timeouts)
    RATE_LIMIT = "rate_limit"  # API rate limiting errors
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # Out of memory, disk space, etc.
    AUTHENTICATION = "authentication"  # Auth/permission errors
    VALIDATION = "validation"  # Input validation errors
    MODEL_ERROR = "model_error"  # LLM provider errors
    NETWORK = "network"  # Network connectivity issues
    TIMEOUT = "timeout"  # Operation timeout
    STATE_CORRUPTION = "state_corruption"  # Internal state issues
    UNRECOVERABLE = "unrecoverable"  # Fatal errors requiring manual intervention
    UNKNOWN = "unknown"  # Unclassified errors


class RecoveryStrategyType(Enum):
    """Types of recovery strategies available."""

    RETRY = "retry"  # Simple retry with backoff
    FALLBACK = "fallback"  # Use alternative approach
    ROLLBACK = "rollback"  # Restore previous state
    CIRCUIT_BREAK = "circuit_break"  # Stop to prevent cascading failures
    DEGRADE = "degrade"  # Continue with reduced functionality
    ESCALATE = "escalate"  # Escalate to higher-level handler
    SKIP = "skip"  # Skip the operation and continue


class FSAState(Enum):
    """States in the Error Recovery FSA."""

    IDLE = "idle"
    DETECTING = "detecting"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    RECOVERING = "recovering"
    VALIDATING = "validating"
    MONITORING = "monitoring"
    FAILED = "failed"
    RECOVERED = "recovered"


@dataclass
class OperationContext:
    """Context information for an operation that may need recovery."""

    operation_id: str
    operation_name: str
    start_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    fallback_operations: List[Callable] = field(default_factory=list)
    checkpoints: List[StateCheckpoint] = field(default_factory=list)

    def add_checkpoint(self, checkpoint: StateCheckpoint) -> None:
        """Add a state checkpoint for potential rollback."""
        self.checkpoints.append(checkpoint)

    def get_latest_checkpoint(self) -> Optional[StateCheckpoint]:
        """Get the most recent checkpoint."""
        return self.checkpoints[-1] if self.checkpoints else None


@dataclass
class ErrorState:
    """Represents the current error state."""

    error: Exception
    category: ErrorCategory
    timestamp: datetime
    context: OperationContext
    stack_trace: str
    recovery_attempted: bool = False
    recovery_count: int = 0


@dataclass
class RecoveryStrategy:
    """Defines a recovery strategy for an error."""

    strategy_type: RecoveryStrategyType
    max_attempts: int = 3
    backoff_base: float = 2.0
    backoff_multiplier: float = 1.0
    timeout: float = 60.0
    fallback_strategy: Optional[RecoveryStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return self.backoff_multiplier * (self.backoff_base ** attempt)


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool
    strategy_used: RecoveryStrategyType
    attempts_made: int
    duration_seconds: float
    error_category: ErrorCategory
    message: str
    recovered_state: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of error state validation."""

    is_valid: bool
    is_recoverable: bool
    recommended_strategy: Optional[RecoveryStrategyType] = None
    reason: str = ""
    confidence: float = 1.0


@dataclass
class StateCheckpoint:
    """Snapshot of operation state for rollback."""

    checkpoint_id: str
    timestamp: datetime
    state_data: Dict[str, Any]
    operation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackResult:
    """Result of a state rollback operation."""

    success: bool
    checkpoint_id: str
    rollback_time: datetime
    state_restored: Dict[str, Any]
    message: str


@dataclass
class HealthStatus:
    """Health status of an operation or system component."""

    operation_id: str
    is_healthy: bool
    error_rate: float
    success_rate: float
    avg_recovery_time: float
    last_error: Optional[datetime] = None
    circuit_open: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAnalytics:
    """Analytics data for failures within a time window."""

    time_window: str
    total_errors: int
    errors_by_category: Dict[ErrorCategory, int]
    recovery_success_rate: float
    most_common_errors: List[Tuple[str, int]]
    avg_recovery_time: float
    circuit_breaker_activations: int
    unrecoverable_errors: int


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes needed to close circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.success_count = 0
        self.state = "closed"  # closed, open, half_open
        self.last_failure_time: Optional[datetime] = None

    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.success_count = 0
                logger.info("Circuit breaker closed after successful recoveries")

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.success_count = 0

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        """Check if operation can be attempted."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.timeout:
                    self.state = "half_open"
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False

        return self.state == "half_open"

    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "open"


class ErrorRecoveryFSA:
    """
    Finite State Automaton for Error Recovery in AI Agent Operations.

    This FSA provides comprehensive error detection, classification, and recovery
    capabilities with multiple recovery strategies, circuit breaking, and health monitoring.
    """

    def __init__(
        self,
        max_retry_attempts: int = 3,
        base_backoff: float = 2.0,
        circuit_breaker_threshold: int = 5,
        enable_analytics: bool = True,
    ):
        """
        Initialize the Error Recovery FSA.

        Args:
            max_retry_attempts: Maximum number of retry attempts for transient errors
            base_backoff: Base value for exponential backoff calculation
            circuit_breaker_threshold: Number of failures before circuit opens
            enable_analytics: Whether to collect analytics data
        """
        self.max_retry_attempts = max_retry_attempts
        self.base_backoff = base_backoff
        self.enable_analytics = enable_analytics

        # FSA state management
        self.current_state = FSAState.IDLE
        self.state_history: deque = deque(maxlen=100)

        # Circuit breakers per operation
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.circuit_breaker_threshold = circuit_breaker_threshold

        # Error tracking and analytics
        self.error_history: deque = deque(maxlen=1000)
        self.recovery_stats: Dict[str, Any] = defaultdict(lambda: {"success": 0, "failure": 0, "total_time": 0.0})
        self.operation_health: Dict[str, HealthStatus] = {}

        # State checkpoints
        self.checkpoints: Dict[str, StateCheckpoint] = {}

        # Recovery strategy mappings
        self._initialize_recovery_strategies()

        logger.info(f"ErrorRecoveryFSA initialized with max_retries={max_retry_attempts}")

    def _initialize_recovery_strategies(self) -> None:
        """Initialize default recovery strategy mappings for each error category."""
        self.strategy_map: Dict[ErrorCategory, RecoveryStrategy] = {
            ErrorCategory.TRANSIENT: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.RETRY,
                max_attempts=self.max_retry_attempts,
                backoff_base=self.base_backoff,
                backoff_multiplier=1.0,
            ),
            ErrorCategory.RATE_LIMIT: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.RETRY,
                max_attempts=5,
                backoff_base=2.0,
                backoff_multiplier=2.0,  # Longer backoff for rate limits
            ),
            ErrorCategory.NETWORK: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.RETRY,
                max_attempts=self.max_retry_attempts,
                backoff_base=self.base_backoff,
                backoff_multiplier=1.5,
            ),
            ErrorCategory.TIMEOUT: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.RETRY,
                max_attempts=2,
                backoff_base=1.5,
                backoff_multiplier=1.0,
            ),
            ErrorCategory.MODEL_ERROR: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.FALLBACK,
                max_attempts=1,
            ),
            ErrorCategory.STATE_CORRUPTION: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.ROLLBACK,
                max_attempts=1,
            ),
            ErrorCategory.RESOURCE_EXHAUSTION: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.DEGRADE,
                max_attempts=1,
            ),
            ErrorCategory.VALIDATION: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.ESCALATE,
                max_attempts=1,
            ),
            ErrorCategory.AUTHENTICATION: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.ESCALATE,
                max_attempts=1,
            ),
            ErrorCategory.UNRECOVERABLE: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.ESCALATE,
                max_attempts=0,
            ),
            ErrorCategory.UNKNOWN: RecoveryStrategy(
                strategy_type=RecoveryStrategyType.RETRY,
                max_attempts=1,
                backoff_base=1.0,
            ),
        }

    def _transition_state(self, new_state: FSAState) -> None:
        """Transition to a new FSA state."""
        old_state = self.current_state
        self.current_state = new_state
        self.state_history.append((datetime.now(), old_state, new_state))
        logger.debug(f"FSA state transition: {old_state.value} -> {new_state.value}")

    def detect_error_type(self, error: Exception) -> ErrorCategory:
        """
        Classify an error into a category for recovery strategy selection.

        Args:
            error: The exception to classify

        Returns:
            ErrorCategory indicating the type of error
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check for rate limit errors
        if isinstance(error, ModelRateLimitError) or "rate limit" in error_str or "429" in error_str:
            return ErrorCategory.RATE_LIMIT

        # Check for model provider errors
        if isinstance(error, ModelProviderError):
            return ErrorCategory.MODEL_ERROR

        # Check for network errors
        if any(keyword in error_str for keyword in ["connection", "network", "dns", "socket"]):
            return ErrorCategory.NETWORK

        # Check for timeout errors
        if any(keyword in error_str for keyword in ["timeout", "timed out", "deadline"]):
            return ErrorCategory.TIMEOUT

        # Check for authentication errors
        if any(keyword in error_str for keyword in ["auth", "unauthorized", "forbidden", "401", "403"]):
            return ErrorCategory.AUTHENTICATION

        # Check for validation errors
        if any(keyword in error_str for keyword in ["validation", "invalid", "bad request", "400"]):
            return ErrorCategory.VALIDATION

        # Check for resource exhaustion
        if any(keyword in error_str for keyword in ["memory", "disk space", "quota", "resource"]):
            return ErrorCategory.RESOURCE_EXHAUSTION

        # Check for state corruption
        if any(keyword in error_str for keyword in ["state", "corrupt", "inconsistent"]):
            return ErrorCategory.STATE_CORRUPTION

        # Check for explicitly unrecoverable errors
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            return ErrorCategory.UNRECOVERABLE

        # Default to transient for common temporary issues
        if any(keyword in error_str for keyword in ["temporary", "unavailable", "retry"]):
            return ErrorCategory.TRANSIENT

        logger.debug(f"Error classified as UNKNOWN: {error_type} - {error_str[:100]}")
        return ErrorCategory.UNKNOWN

    def validate(self, error_state: ErrorState) -> ValidationResult:
        """
        Validate whether an error state is recoverable and determine the best strategy.

        Args:
            error_state: The error state to validate

        Returns:
            ValidationResult with recoverability assessment and recommended strategy
        """
        # Check if we've exceeded retry limits
        if error_state.context.retry_count >= error_state.context.max_retries:
            return ValidationResult(
                is_valid=True,
                is_recoverable=False,
                reason=f"Max retries ({error_state.context.max_retries}) exceeded",
                confidence=1.0,
            )

        # Check circuit breaker status
        operation_id = error_state.context.operation_id
        circuit_breaker = self._get_circuit_breaker(operation_id)
        if circuit_breaker.is_open():
            return ValidationResult(
                is_valid=True,
                is_recoverable=False,
                recommended_strategy=RecoveryStrategyType.CIRCUIT_BREAK,
                reason="Circuit breaker is open",
                confidence=1.0,
            )

        # Unrecoverable errors
        if error_state.category == ErrorCategory.UNRECOVERABLE:
            return ValidationResult(
                is_valid=True,
                is_recoverable=False,
                recommended_strategy=RecoveryStrategyType.ESCALATE,
                reason="Error is categorized as unrecoverable",
                confidence=1.0,
            )

        # Determine recommended strategy
        strategy = self.select_recovery_strategy(error_state.category)

        return ValidationResult(
            is_valid=True,
            is_recoverable=True,
            recommended_strategy=strategy.strategy_type,
            reason="Error is recoverable with appropriate strategy",
            confidence=0.8 if error_state.category != ErrorCategory.UNKNOWN else 0.5,
        )

    def select_recovery_strategy(self, error_type: ErrorCategory) -> RecoveryStrategy:
        """
        Select the optimal recovery strategy for a given error type.

        Args:
            error_type: The category of error

        Returns:
            RecoveryStrategy to use for recovery
        """
        return self.strategy_map.get(error_type, self.strategy_map[ErrorCategory.UNKNOWN])

    def apply_recovery(
        self,
        strategy: RecoveryStrategy,
        context: OperationContext,
        operation: Optional[Callable] = None,
    ) -> bool:
        """
        Apply a recovery strategy to attempt recovery.

        Args:
            strategy: The recovery strategy to apply
            context: Operation context
            operation: Optional operation to retry (for RETRY strategy)

        Returns:
            True if recovery succeeded, False otherwise
        """
        logger.info(f"Applying recovery strategy: {strategy.strategy_type.value} for {context.operation_name}")

        try:
            if strategy.strategy_type == RecoveryStrategyType.RETRY:
                return self._apply_retry_strategy(strategy, context, operation)
            elif strategy.strategy_type == RecoveryStrategyType.FALLBACK:
                return self._apply_fallback_strategy(strategy, context)
            elif strategy.strategy_type == RecoveryStrategyType.ROLLBACK:
                return self._apply_rollback_strategy(strategy, context)
            elif strategy.strategy_type == RecoveryStrategyType.DEGRADE:
                return self._apply_degrade_strategy(strategy, context)
            elif strategy.strategy_type == RecoveryStrategyType.CIRCUIT_BREAK:
                return self._apply_circuit_break_strategy(strategy, context)
            else:
                logger.warning(f"Unsupported recovery strategy: {strategy.strategy_type.value}")
                return False

        except Exception as e:
            logger.error(f"Error during recovery application: {e}")
            return False

    def _apply_retry_strategy(
        self,
        strategy: RecoveryStrategy,
        context: OperationContext,
        operation: Optional[Callable],
    ) -> bool:
        """Apply retry strategy with exponential backoff."""
        if not operation:
            logger.warning("No operation provided for retry strategy")
            return False

        for attempt in range(strategy.max_attempts):
            if attempt > 0:
                backoff_time = strategy.calculate_backoff(attempt - 1)
                logger.info(f"Retry attempt {attempt + 1}/{strategy.max_attempts} after {backoff_time:.2f}s backoff")
                time.sleep(backoff_time)

            try:
                operation()
                logger.info(f"Retry successful on attempt {attempt + 1}")
                return True
            except Exception as e:
                logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                if attempt == strategy.max_attempts - 1:
                    return False

        return False

    def _apply_fallback_strategy(self, strategy: RecoveryStrategy, context: OperationContext) -> bool:
        """Apply fallback strategy using alternative operations."""
        if not context.fallback_operations:
            logger.warning("No fallback operations available")
            return False

        for i, fallback_op in enumerate(context.fallback_operations):
            try:
                logger.info(f"Attempting fallback operation {i + 1}/{len(context.fallback_operations)}")
                fallback_op()
                logger.info(f"Fallback operation {i + 1} succeeded")
                return True
            except Exception as e:
                logger.warning(f"Fallback operation {i + 1} failed: {e}")

        return False

    def _apply_rollback_strategy(self, strategy: RecoveryStrategy, context: OperationContext) -> bool:
        """Apply rollback strategy to restore previous state."""
        checkpoint = context.get_latest_checkpoint()
        if not checkpoint:
            logger.warning("No checkpoint available for rollback")
            return False

        try:
            rollback_result = self.rollback_state(checkpoint)
            return rollback_result.success
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def _apply_degrade_strategy(self, strategy: RecoveryStrategy, context: OperationContext) -> bool:
        """Apply degradation strategy to continue with reduced functionality."""
        logger.info("Applying graceful degradation")
        context.metadata["degraded"] = True
        context.metadata["degradation_reason"] = "Resource exhaustion"
        return True

    def _apply_circuit_break_strategy(self, strategy: RecoveryStrategy, context: OperationContext) -> bool:
        """Apply circuit breaker strategy."""
        logger.warning(f"Circuit breaker activated for operation {context.operation_id}")
        return False

    def rollback_state(self, checkpoint: StateCheckpoint) -> RollbackResult:
        """
        Rollback to a previous state checkpoint.

        Args:
            checkpoint: The checkpoint to restore

        Returns:
            RollbackResult indicating success and details
        """
        logger.info(f"Rolling back to checkpoint {checkpoint.checkpoint_id}")

        try:
            # In a real implementation, this would restore actual state
            # For this implementation, we simulate the rollback
            restored_state = checkpoint.state_data.copy()

            return RollbackResult(
                success=True,
                checkpoint_id=checkpoint.checkpoint_id,
                rollback_time=datetime.now(),
                state_restored=restored_state,
                message=f"Successfully rolled back to checkpoint {checkpoint.checkpoint_id}",
            )
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return RollbackResult(
                success=False,
                checkpoint_id=checkpoint.checkpoint_id,
                rollback_time=datetime.now(),
                state_restored={},
                message=f"Rollback failed: {str(e)}",
            )

    def execute(self, error: Exception, context: OperationContext) -> RecoveryResult:
        """
        Main recovery pipeline - execute complete error recovery process.

        Args:
            error: The exception that occurred
            context: Context of the operation that failed

        Returns:
            RecoveryResult with recovery outcome and details
        """
        start_time = time.time()

        try:
            # Transition to detecting state
            self._transition_state(FSAState.DETECTING)

            # Detect error type
            error_category = self.detect_error_type(error)
            logger.info(f"Error detected: {error_category.value} - {str(error)[:100]}")

            # Create error state
            error_state = ErrorState(
                error=error,
                category=error_category,
                timestamp=datetime.now(),
                context=context,
                stack_trace=traceback.format_exc(),
            )

            # Record error in history
            if self.enable_analytics:
                self.error_history.append(error_state)

            # Transition to analyzing state
            self._transition_state(FSAState.ANALYZING)

            # Validate recoverability
            validation = self.validate(error_state)
            if not validation.is_recoverable:
                self._transition_state(FSAState.FAILED)
                circuit_breaker = self._get_circuit_breaker(context.operation_id)
                circuit_breaker.record_failure()

                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategyType.ESCALATE,
                    attempts_made=0,
                    duration_seconds=time.time() - start_time,
                    error_category=error_category,
                    message=f"Error not recoverable: {validation.reason}",
                )

            # Transition to planning state
            self._transition_state(FSAState.PLANNING)

            # Select recovery strategy
            strategy = self.select_recovery_strategy(error_category)
            logger.info(f"Selected recovery strategy: {strategy.strategy_type.value}")

            # Transition to recovering state
            self._transition_state(FSAState.RECOVERING)

            # Check circuit breaker
            circuit_breaker = self._get_circuit_breaker(context.operation_id)
            if not circuit_breaker.can_attempt():
                self._transition_state(FSAState.FAILED)
                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategyType.CIRCUIT_BREAK,
                    attempts_made=0,
                    duration_seconds=time.time() - start_time,
                    error_category=error_category,
                    message="Circuit breaker is open",
                )

            # Apply recovery strategy
            recovery_success = self.apply_recovery(strategy, context)

            # Transition to validating state
            self._transition_state(FSAState.VALIDATING)

            duration = time.time() - start_time

            if recovery_success:
                self._transition_state(FSAState.RECOVERED)
                circuit_breaker.record_success()
                self._update_health_status(context.operation_id, True, duration)

                if self.enable_analytics:
                    self.recovery_stats[strategy.strategy_type.value]["success"] += 1
                    self.recovery_stats[strategy.strategy_type.value]["total_time"] += duration

                return RecoveryResult(
                    success=True,
                    strategy_used=strategy.strategy_type,
                    attempts_made=context.retry_count + 1,
                    duration_seconds=duration,
                    error_category=error_category,
                    message=f"Recovery successful using {strategy.strategy_type.value} strategy",
                )
            else:
                self._transition_state(FSAState.FAILED)
                circuit_breaker.record_failure()
                self._update_health_status(context.operation_id, False, duration)

                if self.enable_analytics:
                    self.recovery_stats[strategy.strategy_type.value]["failure"] += 1

                return RecoveryResult(
                    success=False,
                    strategy_used=strategy.strategy_type,
                    attempts_made=context.retry_count + 1,
                    duration_seconds=duration,
                    error_category=error_category,
                    message=f"Recovery failed after {context.retry_count + 1} attempts",
                )

        except Exception as recovery_error:
            # Meta error handling - error in the error handler itself
            logger.error(f"Error during recovery process: {recovery_error}")
            self._transition_state(FSAState.FAILED)

            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategyType.ESCALATE,
                attempts_made=0,
                duration_seconds=time.time() - start_time,
                error_category=ErrorCategory.UNRECOVERABLE,
                message=f"Recovery process failed: {str(recovery_error)}",
                metadata={"original_error": str(error), "recovery_error": str(recovery_error)},
            )

    def _get_circuit_breaker(self, operation_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for an operation."""
        if operation_id not in self.circuit_breakers:
            self.circuit_breakers[operation_id] = CircuitBreaker(
                failure_threshold=self.circuit_breaker_threshold,
                success_threshold=2,
                timeout=60.0,
            )
        return self.circuit_breakers[operation_id]

    def _update_health_status(self, operation_id: str, success: bool, duration: float) -> None:
        """Update health status for an operation."""
        if operation_id not in self.operation_health:
            self.operation_health[operation_id] = HealthStatus(
                operation_id=operation_id,
                is_healthy=True,
                error_rate=0.0,
                success_rate=1.0,
                avg_recovery_time=0.0,
            )

        health = self.operation_health[operation_id]
        circuit_breaker = self._get_circuit_breaker(operation_id)

        # Update health metrics
        if not success:
            health.last_error = datetime.now()
            health.error_rate = min(1.0, health.error_rate + 0.1)
            health.success_rate = max(0.0, health.success_rate - 0.1)
        else:
            health.error_rate = max(0.0, health.error_rate - 0.05)
            health.success_rate = min(1.0, health.success_rate + 0.05)

        # Update average recovery time
        if health.avg_recovery_time == 0.0:
            health.avg_recovery_time = duration
        else:
            health.avg_recovery_time = (health.avg_recovery_time * 0.8) + (duration * 0.2)

        health.is_healthy = health.success_rate > 0.7 and not circuit_breaker.is_open()
        health.circuit_open = circuit_breaker.is_open()

    def monitor_health(self, operation_id: str) -> HealthStatus:
        """
        Monitor and return health status for an operation.

        Args:
            operation_id: ID of the operation to monitor

        Returns:
            HealthStatus with current health metrics
        """
        if operation_id not in self.operation_health:
            # Return default healthy status for new operations
            return HealthStatus(
                operation_id=operation_id,
                is_healthy=True,
                error_rate=0.0,
                success_rate=1.0,
                avg_recovery_time=0.0,
            )

        return self.operation_health[operation_id]

    def analyze_failures(self, time_window: str = "1h") -> FailureAnalytics:
        """
        Analyze failures within a time window and generate insights.

        Args:
            time_window: Time window for analysis (e.g., "1h", "24h", "7d")

        Returns:
            FailureAnalytics with failure insights and statistics
        """
        # Parse time window
        window_seconds = self._parse_time_window(time_window)
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)

        # Filter errors within time window
        recent_errors = [err for err in self.error_history if err.timestamp >= cutoff_time]

        if not recent_errors:
            return FailureAnalytics(
                time_window=time_window,
                total_errors=0,
                errors_by_category={},
                recovery_success_rate=1.0,
                most_common_errors=[],
                avg_recovery_time=0.0,
                circuit_breaker_activations=0,
                unrecoverable_errors=0,
            )

        # Calculate statistics
        errors_by_category: Dict[ErrorCategory, int] = defaultdict(int)
        error_messages: Dict[str, int] = defaultdict(int)
        unrecoverable_count = 0
        circuit_breaker_count = sum(1 for cb in self.circuit_breakers.values() if cb.is_open())

        for error_state in recent_errors:
            errors_by_category[error_state.category] += 1
            error_messages[str(error_state.error)[:100]] += 1
            if error_state.category == ErrorCategory.UNRECOVERABLE:
                unrecoverable_count += 1

        # Calculate recovery success rate
        total_successes = sum(stats["success"] for stats in self.recovery_stats.values())
        total_failures = sum(stats["failure"] for stats in self.recovery_stats.values())
        total_attempts = total_successes + total_failures
        recovery_success_rate = total_successes / total_attempts if total_attempts > 0 else 1.0

        # Calculate average recovery time
        total_time = sum(stats["total_time"] for stats in self.recovery_stats.values())
        avg_recovery_time = total_time / total_successes if total_successes > 0 else 0.0

        # Get most common errors
        most_common = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]

        return FailureAnalytics(
            time_window=time_window,
            total_errors=len(recent_errors),
            errors_by_category=dict(errors_by_category),
            recovery_success_rate=recovery_success_rate,
            most_common_errors=most_common,
            avg_recovery_time=avg_recovery_time,
            circuit_breaker_activations=circuit_breaker_count,
            unrecoverable_errors=unrecoverable_count,
        )

    def _parse_time_window(self, time_window: str) -> float:
        """Parse time window string to seconds."""
        time_window = time_window.strip().lower()
        if time_window.endswith("s"):
            return float(time_window[:-1])
        elif time_window.endswith("m"):
            return float(time_window[:-1]) * 60
        elif time_window.endswith("h"):
            return float(time_window[:-1]) * 3600
        elif time_window.endswith("d"):
            return float(time_window[:-1]) * 86400
        else:
            # Default to treating as hours
            return float(time_window) * 3600

    def create_checkpoint(self, operation_id: str, state_data: Dict[str, Any]) -> StateCheckpoint:
        """
        Create a state checkpoint for potential rollback.

        Args:
            operation_id: ID of the operation
            state_data: State data to checkpoint

        Returns:
            StateCheckpoint object
        """
        checkpoint = StateCheckpoint(
            checkpoint_id=str(uuid4()),
            timestamp=datetime.now(),
            state_data=state_data.copy(),
            operation_id=operation_id,
        )

        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        logger.debug(f"Created checkpoint {checkpoint.checkpoint_id} for operation {operation_id}")

        return checkpoint

    def get_state_history(self) -> List[Tuple[datetime, FSAState, FSAState]]:
        """Get FSA state transition history."""
        return list(self.state_history)

    def reset(self) -> None:
        """Reset the FSA to initial state."""
        self.current_state = FSAState.IDLE
        self.circuit_breakers.clear()
        self.error_history.clear()
        self.recovery_stats.clear()
        self.operation_health.clear()
        self.checkpoints.clear()
        logger.info("ErrorRecoveryFSA reset to initial state")

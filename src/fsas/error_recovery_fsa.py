"""
Error Recovery Finite State Automaton (FSA)

A production-ready FSA for handling failure modes and implementing error recovery strategies.
Supports error classification, retry strategies with exponential backoff, and graceful degradation.
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime


# Configure logging
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for recovery strategy selection."""
    API = "api"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryState(Enum):
    """FSA states for error recovery process."""
    IDLE = "idle"
    ERROR_DETECTED = "error_detected"
    ERROR_CLASSIFIED = "error_classified"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    DEGRADED_MODE = "degraded_mode"


@dataclass
class ErrorContext:
    """Context information for an error occurrence."""
    error: Exception
    error_type: ErrorType = ErrorType.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovery_actions: List[str] = field(default_factory=list)


@dataclass
class RecoveryStrategy:
    """Configuration for error recovery strategy."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    enable_degraded_mode: bool = True
    fallback_action: Optional[Callable] = None


class ErrorRecoveryFSA:
    """
    Finite State Automaton for error detection, classification, and recovery.

    This FSA manages the complete error recovery lifecycle:
    1. Error detection
    2. Error classification
    3. Recovery strategy selection
    4. Recovery execution with retries
    5. Incident logging

    Example:
        >>> fsa = ErrorRecoveryFSA()
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     result = fsa.handle_error(e, context={"operation": "api_call"})
        ...     if result.recovered:
        ...         print("Operation recovered successfully")
    """

    def __init__(
        self,
        strategy: Optional[RecoveryStrategy] = None,
        log_handler: Optional[Callable] = None
    ):
        """
        Initialize the Error Recovery FSA.

        Args:
            strategy: Recovery strategy configuration
            log_handler: Custom logging handler for incidents
        """
        self.state = RecoveryState.IDLE
        self.strategy = strategy or RecoveryStrategy()
        self.log_handler = log_handler or self._default_log_handler
        self.error_history: List[ErrorContext] = []
        self.state_transitions: List[tuple] = []

    def detect_error(self, error: Exception, metadata: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """
        Detect and create context for an error.

        Args:
            error: The exception that occurred
            metadata: Additional context about the error

        Returns:
            ErrorContext object with error information
        """
        self._transition_state(RecoveryState.ERROR_DETECTED)

        context = ErrorContext(
            error=error,
            timestamp=datetime.now(),
            metadata=metadata or {},
            max_retries=self.strategy.max_retries
        )

        self.error_history.append(context)
        logger.debug(f"Error detected: {type(error).__name__} - {str(error)}")

        return context

    def classify_failure(self, context: ErrorContext) -> ErrorType:
        """
        Classify the error type based on error characteristics.

        Args:
            context: Error context to classify

        Returns:
            ErrorType enum value
        """
        self._transition_state(RecoveryState.ERROR_CLASSIFIED)

        error = context.error
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # API-related errors
        if any(keyword in error_str or keyword in error_type_name
               for keyword in ['api', 'http', 'request', 'response', 'status', 'connection']):
            context.error_type = ErrorType.API

        # Timeout errors
        elif any(keyword in error_str or keyword in error_type_name
                 for keyword in ['timeout', 'deadline', 'expired']):
            context.error_type = ErrorType.TIMEOUT

        # Validation errors
        elif any(keyword in error_str or keyword in error_type_name
                 for keyword in ['validation', 'invalid', 'schema', 'format']):
            context.error_type = ErrorType.VALIDATION

        # Resource errors
        elif any(keyword in error_str or keyword in error_type_name
                 for keyword in ['memory', 'disk', 'quota', 'limit', 'resource']):
            context.error_type = ErrorType.RESOURCE

        else:
            context.error_type = ErrorType.UNKNOWN

        logger.info(f"Error classified as: {context.error_type.value}")
        return context.error_type

    def execute_recovery(
        self,
        context: ErrorContext,
        recovery_action: Callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute recovery strategy with exponential backoff retries.

        Args:
            context: Error context
            recovery_action: Callable to retry
            *args: Positional arguments for recovery_action
            **kwargs: Keyword arguments for recovery_action

        Returns:
            Dict with recovery result including 'success', 'result', and 'attempts'
        """
        self._transition_state(RecoveryState.RECOVERY_IN_PROGRESS)

        for attempt in range(context.max_retries + 1):
            context.retry_count = attempt

            try:
                # Execute recovery action
                result = recovery_action(*args, **kwargs)

                # Success!
                self._transition_state(RecoveryState.RECOVERY_SUCCESS)
                context.recovery_actions.append(f"Success on attempt {attempt + 1}")

                logger.info(f"Recovery successful after {attempt + 1} attempt(s)")
                return {
                    'success': True,
                    'result': result,
                    'attempts': attempt + 1,
                    'recovered': True
                }

            except Exception as e:
                context.recovery_actions.append(f"Attempt {attempt + 1} failed: {str(e)}")
                logger.warning(f"Recovery attempt {attempt + 1} failed: {str(e)}")

                # Check if we should retry
                if attempt < context.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.debug(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    self._transition_state(RecoveryState.RECOVERY_FAILED)

                    # Try degraded mode if enabled
                    if self.strategy.enable_degraded_mode and self.strategy.fallback_action:
                        return self._execute_degraded_mode(context, *args, **kwargs)

                    logger.error(f"Recovery failed after {context.max_retries + 1} attempts")
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': attempt + 1,
                        'recovered': False
                    }

        return {'success': False, 'recovered': False}

    def _execute_degraded_mode(
        self,
        context: ErrorContext,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute fallback action in degraded mode.

        Args:
            context: Error context
            *args: Positional arguments for fallback action
            **kwargs: Keyword arguments for fallback action

        Returns:
            Dict with degraded mode execution result
        """
        self._transition_state(RecoveryState.DEGRADED_MODE)
        logger.warning("Entering degraded mode with fallback action")

        try:
            result = self.strategy.fallback_action(*args, **kwargs)
            context.recovery_actions.append("Fallback action executed successfully")

            return {
                'success': True,
                'result': result,
                'degraded_mode': True,
                'recovered': True
            }
        except Exception as e:
            logger.error(f"Degraded mode fallback also failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'degraded_mode': True,
                'recovered': False
            }

    def log_incident(self, context: ErrorContext, additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error incident with full context.

        Args:
            context: Error context to log
            additional_info: Additional information to include in log
        """
        incident = {
            'timestamp': context.timestamp.isoformat(),
            'error_type': context.error_type.value,
            'error': str(context.error),
            'error_class': type(context.error).__name__,
            'retry_count': context.retry_count,
            'recovery_actions': context.recovery_actions,
            'metadata': context.metadata,
            'state': self.state.value,
            'additional_info': additional_info or {}
        }

        self.log_handler(incident)

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.strategy.base_delay * (self.strategy.exponential_base ** attempt)
        return min(delay, self.strategy.max_delay)

    def _transition_state(self, new_state: RecoveryState) -> None:
        """
        Transition FSA to a new state.

        Args:
            new_state: Target state
        """
        old_state = self.state
        self.state = new_state
        self.state_transitions.append((old_state, new_state, datetime.now()))
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    def _default_log_handler(self, incident: Dict[str, Any]) -> None:
        """
        Default incident logging handler.

        Args:
            incident: Incident information dictionary
        """
        logger.error(f"Incident logged: {incident}")

    def handle_error(
        self,
        error: Exception,
        recovery_action: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete error handling workflow: detect, classify, recover, and log.

        This is the main entry point for handling errors through the FSA.

        Args:
            error: The exception to handle
            recovery_action: Callable to execute for recovery
            context: Additional context metadata
            *args: Arguments for recovery action
            **kwargs: Keyword arguments for recovery action

        Returns:
            Dict with complete recovery result
        """
        # Detect error
        error_context = self.detect_error(error, metadata=context)

        # Classify error
        error_type = self.classify_failure(error_context)

        # Execute recovery if action provided
        result = {'recovered': False, 'error_type': error_type.value}

        if recovery_action:
            result = self.execute_recovery(error_context, recovery_action, *args, **kwargs)
            result['error_type'] = error_type.value

        # Log incident
        self.log_incident(error_context, additional_info=result)

        # Reset to idle
        self._transition_state(RecoveryState.IDLE)

        return result

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about handled errors.

        Returns:
            Dictionary with error statistics
        """
        if not self.error_history:
            return {'total_errors': 0, 'by_type': {}, 'average_retries': 0}

        error_type_counts = {}
        total_retries = 0

        for ctx in self.error_history:
            error_type_counts[ctx.error_type.value] = error_type_counts.get(ctx.error_type.value, 0) + 1
            total_retries += ctx.retry_count

        return {
            'total_errors': len(self.error_history),
            'by_type': error_type_counts,
            'average_retries': total_retries / len(self.error_history) if self.error_history else 0,
            'state_transitions': len(self.state_transitions)
        }

    def reset(self) -> None:
        """Reset the FSA to initial state."""
        self.state = RecoveryState.IDLE
        self.error_history.clear()
        self.state_transitions.clear()
        logger.info("FSA reset to initial state")

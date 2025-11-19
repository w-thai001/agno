"""Error Handler Finite State Automaton with retry logic and recovery strategies."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categorization for handling strategies."""
    TRANSIENT = "transient"  # Network glitches, temporary unavailability
    PERMANENT = "permanent"  # Invalid input, auth failure
    TIMEOUT = "timeout"  # Request timeout
    RATE_LIMIT = "rate_limit"  # API rate limiting


class State(Enum):
    """FSA states for error handling."""
    IDLE = "idle"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    FAILED = "failed"
    RESOLVED = "resolved"


@dataclass
class ErrorContext:
    """Context for error handling."""
    error: Exception
    category: ErrorCategory
    attempt: int = 0
    max_retries: int = 3
    base_delay: float = 1.0
    metadata: dict = field(default_factory=dict)


class ErrorHandlerFSA:
    """Finite State Automaton for error handling with retry and recovery."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.state = State.IDLE
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.context: Optional[ErrorContext] = None

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and attributes."""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        if "timeout" in error_msg or error_type in ("TimeoutError", "asyncio.TimeoutError"):
            return ErrorCategory.TIMEOUT
        elif "rate limit" in error_msg or error_type == "RateLimitError":
            return ErrorCategory.RATE_LIMIT
        elif error_type in ("ConnectionError", "NetworkError", "TemporaryFailure"):
            return ErrorCategory.TRANSIENT
        elif error_type in ("ValueError", "AuthenticationError", "PermissionError"):
            return ErrorCategory.PERMANENT
        else:
            # Default to transient for unknown errors
            return ErrorCategory.TRANSIENT

    def handle_error(self, error: Exception, operation: Callable, **kwargs) -> Any:
        """Main entry point for error handling."""
        category = self.categorize_error(error)
        self.context = ErrorContext(
            error=error,
            category=category,
            max_retries=kwargs.get("max_retries", self.max_retries),
            base_delay=kwargs.get("base_delay", self.base_delay),
            metadata=kwargs.get("metadata", {})
        )

        logger.error(f"Error occurred: {error} (Category: {category.value})")
        self._transition(State.IDLE, State.RETRYING)

        return self._execute_fsm(operation)

    def _execute_fsm(self, operation: Callable) -> Any:
        """Execute the FSA logic."""
        while self.state not in (State.RESOLVED, State.FAILED):
            if self.state == State.RETRYING:
                result = self._handle_retry(operation)
                if result is not None:
                    return result
            elif self.state == State.RECOVERING:
                result = self._handle_recovery(operation)
                if result is not None:
                    return result

        if self.state == State.FAILED:
            logger.error(f"Operation failed after all recovery attempts: {self.context.error}")
            raise self.context.error

    def _handle_retry(self, operation: Callable) -> Optional[Any]:
        """Handle retry logic with exponential backoff."""
        if self.context.attempt >= self.context.max_retries:
            logger.warning(f"Max retries ({self.context.max_retries}) exceeded")
            self._transition(State.RETRYING, State.RECOVERING)
            return None

        self.context.attempt += 1
        delay = self._calculate_delay()

        logger.info(f"Retry attempt {self.context.attempt}/{self.context.max_retries} after {delay}s")
        time.sleep(delay)

        try:
            result = operation()
            logger.info("Operation succeeded after retry")
            self._transition(State.RETRYING, State.RESOLVED)
            return result
        except Exception as e:
            logger.warning(f"Retry {self.context.attempt} failed: {e}")
            self.context.error = e
            # Stay in RETRYING state for next attempt
            return None

    def _handle_recovery(self, operation: Callable) -> Optional[Any]:
        """Apply recovery strategies based on error category."""
        strategy = self._get_recovery_strategy()
        logger.info(f"Applying recovery strategy for {self.context.category.value}")

        try:
            strategy()
            # Retry operation after recovery
            result = operation()
            logger.info("Operation succeeded after recovery")
            self._transition(State.RECOVERING, State.RESOLVED)
            return result
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.context.error = e
            self._transition(State.RECOVERING, State.FAILED)
            return None

    def _get_recovery_strategy(self) -> Callable:
        """Get recovery strategy based on error category."""
        strategies = {
            ErrorCategory.TRANSIENT: self._recover_transient,
            ErrorCategory.TIMEOUT: self._recover_timeout,
            ErrorCategory.RATE_LIMIT: self._recover_rate_limit,
            ErrorCategory.PERMANENT: self._recover_permanent,
        }
        return strategies.get(self.context.category, self._recover_default)

    def _recover_transient(self):
        """Recovery for transient errors - wait longer."""
        delay = self.base_delay * 5
        logger.info(f"Transient error recovery: waiting {delay}s")
        time.sleep(delay)

    def _recover_timeout(self):
        """Recovery for timeout errors - exponential backoff."""
        delay = self.base_delay * (2 ** self.context.attempt)
        logger.info(f"Timeout recovery: waiting {delay}s")
        time.sleep(delay)

    def _recover_rate_limit(self):
        """Recovery for rate limit errors - longer wait."""
        delay = 60  # Wait 1 minute for rate limit
        logger.info(f"Rate limit recovery: waiting {delay}s")
        time.sleep(delay)

    def _recover_permanent(self):
        """Recovery for permanent errors - log and fail."""
        logger.error("Permanent error detected - no recovery possible")
        raise self.context.error

    def _recover_default(self):
        """Default recovery strategy."""
        logger.warning("Using default recovery strategy")
        time.sleep(self.base_delay * 2)

    def _calculate_delay(self) -> float:
        """Calculate delay with exponential backoff."""
        return self.base_delay * (2 ** (self.context.attempt - 1))

    def _transition(self, from_state: State, to_state: State):
        """Transition between states with logging."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

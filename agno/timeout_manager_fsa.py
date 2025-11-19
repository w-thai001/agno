"""Timeout Manager Finite State Automaton for operation timeout management."""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for timeout management."""
    IDLE = "idle"
    RUNNING = "running"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class TimeoutContext:
    """Context for timeout operations."""
    operation_id: str
    timeout_duration: float
    start_time: float = 0.0
    elapsed_time: float = 0.0
    result: Any = None
    error: Optional[Exception] = None
    cancellation_token: bool = False


class TimeoutManagerFSA:
    """Finite State Automaton for managing operation timeouts."""

    def __init__(self, default_timeout: float = 30.0):
        self.state = State.IDLE
        self.default_timeout = default_timeout
        self.context: Optional[TimeoutContext] = None
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def execute_with_timeout(
        self,
        operation: Callable,
        operation_id: str,
        timeout: Optional[float] = None,
        on_timeout: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None
    ) -> Any:
        """Execute operation with timeout management."""
        timeout_duration = timeout or self.default_timeout

        with self._lock:
            if self.state != State.IDLE:
                raise RuntimeError(f"Manager busy in state: {self.state.value}")

            self.context = TimeoutContext(
                operation_id=operation_id,
                timeout_duration=timeout_duration
            )
            self._transition(State.IDLE, State.RUNNING)

        logger.info(f"Starting operation {operation_id} with {timeout_duration}s timeout")
        self.context.start_time = time.time()

        # Start timeout timer
        self._start_timeout_timer(on_timeout)

        try:
            result = self._execute_operation(operation)
            return result
        finally:
            self._cleanup()

    def cancel(self, reason: str = "User requested"):
        """Cancel the running operation."""
        with self._lock:
            if self.state != State.RUNNING:
                logger.warning(f"Cannot cancel: not running (state: {self.state.value})")
                return False

            logger.info(f"Cancelling operation {self.context.operation_id}: {reason}")
            self.context.cancellation_token = True
            self._transition(State.RUNNING, State.CANCELLED)
            self._cancel_timer()
            return True

    def get_elapsed_time(self) -> float:
        """Get elapsed time for current operation."""
        if self.context and self.context.start_time > 0:
            return time.time() - self.context.start_time
        return 0.0

    def get_remaining_time(self) -> float:
        """Get remaining time before timeout."""
        if self.context:
            elapsed = self.get_elapsed_time()
            return max(0, self.context.timeout_duration - elapsed)
        return 0.0

    def is_timed_out(self) -> bool:
        """Check if operation has timed out."""
        return self.state == State.TIMEOUT

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        if self.context:
            return self.context.cancellation_token
        return False

    def _execute_operation(self, operation: Callable) -> Any:
        """Execute operation with cancellation checks."""
        result = None

        try:
            # For demonstration, wrap operation execution
            result = operation()

            with self._lock:
                if self.state == State.RUNNING:
                    self.context.result = result
                    self.context.elapsed_time = self.get_elapsed_time()
                    self._transition(State.RUNNING, State.COMPLETED)
                    self._cancel_timer()
                    logger.info(
                        f"Operation {self.context.operation_id} completed in "
                        f"{self.context.elapsed_time:.2f}s"
                    )
                elif self.state == State.TIMEOUT:
                    raise TimeoutError(
                        f"Operation {self.context.operation_id} timed out after "
                        f"{self.context.timeout_duration}s"
                    )
                elif self.state == State.CANCELLED:
                    raise InterruptedError(
                        f"Operation {self.context.operation_id} was cancelled"
                    )

            return result

        except Exception as e:
            with self._lock:
                self.context.error = e
                self.context.elapsed_time = self.get_elapsed_time()
                if self.state == State.RUNNING:
                    self._cancel_timer()
            raise

    def _start_timeout_timer(self, on_timeout: Optional[Callable]):
        """Start the timeout detection timer."""
        def timeout_handler():
            with self._lock:
                if self.state == State.RUNNING:
                    elapsed = self.get_elapsed_time()
                    logger.warning(
                        f"Operation {self.context.operation_id} timed out after {elapsed:.2f}s"
                    )
                    self.context.elapsed_time = elapsed
                    self._transition(State.RUNNING, State.TIMEOUT)

                    if on_timeout:
                        try:
                            on_timeout(self.context)
                        except Exception as e:
                            logger.error(f"Error in timeout callback: {e}")

        self._timer = threading.Timer(self.context.timeout_duration, timeout_handler)
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self):
        """Cancel the timeout timer."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _cleanup(self):
        """Cleanup resources after operation completion."""
        self._cancel_timer()
        with self._lock:
            if self.state in (State.COMPLETED, State.TIMEOUT, State.CANCELLED):
                self._transition(self.state, State.IDLE)

    def _transition(self, from_state: State, to_state: State):
        """Transition between states with logging."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

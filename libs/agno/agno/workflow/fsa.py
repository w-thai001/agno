"""
Workflow Engine FSA (Finite State Automaton) - FSA-3.1 Specification

A simple, fast, and functional workflow engine based on finite state automaton principles.
Provides core execution logic with step runner, state tracker, and error handler.

Key Components:
- State: Represents a node in the workflow FSA
- Transition: Defines edges between states with conditions
- StepRunner: Executes state actions and handles transitions
- StateTracker: Manages current state and history
- ErrorHandler: Handles failures and recovery strategies
- FSAEngine: Main orchestrator for workflow execution

FSA-3.1 Spec Compliance:
- Deterministic state transitions
- Explicit error states and recovery paths
- State persistence and resumability
- Action isolation and composability
- Event-driven execution model
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union, Iterator
from enum import Enum
import logging
import traceback
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger(__name__)


class StateType(Enum):
    """FSA-3.1: State classification types"""
    START = "start"
    INTERMEDIATE = "intermediate"
    END = "end"
    ERROR = "error"
    RECOVERY = "recovery"


class TransitionCondition(Enum):
    """FSA-3.1: Standard transition conditions"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CONDITION_MET = "condition_met"
    ALWAYS = "always"
    CUSTOM = "custom"


class ExecutionStatus(Enum):
    """FSA-3.1: Execution status tracking"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    RECOVERED = "recovered"


@dataclass
class StateContext:
    """
    FSA-3.1: Context passed between states during execution.
    Contains all data, metadata, and state needed for workflow execution.
    """
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    history: List[str] = field(default_factory=list)

    def add_error(self, error: Exception, state: str) -> None:
        """Record an error in the context"""
        self.errors.append({
            "state": state,
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        })

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """Get the most recent error"""
        return self.errors[-1] if self.errors else None

    def clear_errors(self) -> None:
        """Clear all errors"""
        self.errors.clear()


@dataclass
class State:
    """
    FSA-3.1: Represents a state node in the workflow FSA.

    Each state has:
    - Unique name identifier
    - Type (start, intermediate, end, error, recovery)
    - Action to execute when entering this state
    - Optional timeout in seconds
    - Metadata for custom state configuration
    """
    name: str
    state_type: StateType
    action: Optional[Callable[[StateContext], Any]] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def execute(self, context: StateContext) -> Any:
        """Execute the state's action with the given context"""
        if self.action is None:
            logger.debug(f"State '{self.name}' has no action, skipping")
            return None

        try:
            logger.info(f"Executing state: {self.name}")
            result = self.action(context)
            return result
        except Exception as e:
            logger.error(f"Error executing state '{self.name}': {e}")
            context.add_error(e, self.name)
            raise


@dataclass
class Transition:
    """
    FSA-3.1: Defines a transition edge between states.

    Transitions specify:
    - Source state name
    - Target state name
    - Condition for the transition to fire
    - Optional guard function for custom logic
    - Priority (higher priority evaluated first)
    """
    from_state: str
    to_state: str
    condition: TransitionCondition
    guard: Optional[Callable[[StateContext, Any], bool]] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_transition(self, context: StateContext, result: Any) -> bool:
        """
        Evaluate if this transition should fire.

        Args:
            context: Current state context
            result: Result from the current state's action

        Returns:
            True if transition should occur, False otherwise
        """
        # Check guard function if provided
        if self.guard is not None:
            try:
                return self.guard(context, result)
            except Exception as e:
                logger.error(f"Guard function error in transition {self.from_state}->{self.to_state}: {e}")
                return False

        # Standard condition evaluation
        if self.condition == TransitionCondition.ALWAYS:
            return True
        elif self.condition == TransitionCondition.SUCCESS:
            return result is not None and not isinstance(result, Exception)
        elif self.condition == TransitionCondition.FAILURE:
            return isinstance(result, Exception) or len(context.errors) > 0
        elif self.condition == TransitionCondition.CONDITION_MET:
            return bool(result)

        return False


@dataclass
class ExecutionStep:
    """FSA-3.1: Records a single execution step in the workflow"""
    state_name: str
    timestamp: str
    duration_ms: float
    result: Any
    status: ExecutionStatus
    error: Optional[str] = None


class StateTracker:
    """
    FSA-3.1: Tracks current state, history, and execution progress.

    Responsibilities:
    - Maintain current state
    - Record state transition history
    - Track execution metrics
    - Provide state snapshot for persistence
    """

    def __init__(self, initial_state: str):
        self.current_state: str = initial_state
        self.execution_history: List[ExecutionStep] = []
        self.state_visit_count: Dict[str, int] = {}
        self.total_transitions: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def transition_to(self, new_state: str) -> None:
        """Transition to a new state"""
        logger.debug(f"Transitioning: {self.current_state} -> {new_state}")
        self.current_state = new_state
        self.total_transitions += 1
        self.state_visit_count[new_state] = self.state_visit_count.get(new_state, 0) + 1

    def record_step(self, step: ExecutionStep) -> None:
        """Record an execution step"""
        self.execution_history.append(step)

    def start_execution(self) -> None:
        """Mark execution start"""
        self.start_time = datetime.now()

    def end_execution(self) -> None:
        """Mark execution end"""
        self.end_time = datetime.now()

    def get_duration_ms(self) -> float:
        """Get total execution duration in milliseconds"""
        if self.start_time is None:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000

    def get_snapshot(self) -> Dict[str, Any]:
        """Get current state snapshot for persistence"""
        return {
            "current_state": self.current_state,
            "total_transitions": self.total_transitions,
            "state_visit_count": self.state_visit_count,
            "execution_history_count": len(self.execution_history),
            "duration_ms": self.get_duration_ms(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    def has_visited(self, state_name: str) -> bool:
        """Check if a state has been visited"""
        return state_name in self.state_visit_count

    def get_visit_count(self, state_name: str) -> int:
        """Get number of times a state has been visited"""
        return self.state_visit_count.get(state_name, 0)


class ErrorHandler:
    """
    FSA-3.1: Handles errors and recovery strategies.

    Strategies:
    - Retry: Retry the failed state N times
    - Skip: Skip the failed state and continue
    - Recover: Transition to a recovery state
    - Fail: Stop execution and raise error
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_states: Optional[List[str]] = None,
        recovery_state: Optional[str] = None,
    ):
        self.max_retries = max_retries
        self.retry_states = set(retry_states or [])
        self.recovery_state = recovery_state
        self.retry_counts: Dict[str, int] = {}

    def handle_error(
        self,
        state: State,
        error: Exception,
        context: StateContext,
    ) -> Optional[str]:
        """
        Handle an error that occurred during state execution.

        Args:
            state: The state where the error occurred
            error: The exception that was raised
            context: Current execution context

        Returns:
            Next state name if recovery is possible, None if execution should stop
        """
        logger.error(f"Error in state '{state.name}': {error}")

        # Check if state supports retry
        if state.name in self.retry_states:
            retry_count = self.retry_counts.get(state.name, 0)
            if retry_count < self.max_retries:
                self.retry_counts[state.name] = retry_count + 1
                logger.info(f"Retrying state '{state.name}' (attempt {retry_count + 1}/{self.max_retries})")
                return state.name  # Retry same state

        # Check if recovery state is configured
        if self.recovery_state:
            logger.info(f"Transitioning to recovery state: {self.recovery_state}")
            return self.recovery_state

        # No recovery possible
        logger.error(f"No recovery strategy for state '{state.name}', stopping execution")
        return None

    def reset_retry_count(self, state_name: str) -> None:
        """Reset retry count for a state (called on success)"""
        if state_name in self.retry_counts:
            del self.retry_counts[state_name]


class StepRunner:
    """
    FSA-3.1: Executes individual state steps and manages transitions.

    Responsibilities:
    - Execute state actions
    - Evaluate transition conditions
    - Handle errors during execution
    - Record execution metrics
    """

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler

    def run_step(
        self,
        state: State,
        context: StateContext,
        tracker: StateTracker,
    ) -> tuple[Any, ExecutionStatus]:
        """
        Execute a single state step.

        Args:
            state: State to execute
            context: Execution context
            tracker: State tracker

        Returns:
            Tuple of (result, status)
        """
        start_time = datetime.now()
        result = None
        status = ExecutionStatus.RUNNING
        error_msg = None

        try:
            # Execute the state action
            result = state.execute(context)
            status = ExecutionStatus.COMPLETED

            # Reset retry count on success
            self.error_handler.reset_retry_count(state.name)

        except Exception as e:
            error_msg = str(e)
            status = ExecutionStatus.FAILED
            result = e

        finally:
            # Record the execution step
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            step = ExecutionStep(
                state_name=state.name,
                timestamp=start_time.isoformat(),
                duration_ms=duration_ms,
                result=result if not isinstance(result, Exception) else None,
                status=status,
                error=error_msg,
            )
            tracker.record_step(step)

        return result, status

    def find_next_state(
        self,
        current_state: str,
        transitions: List[Transition],
        context: StateContext,
        result: Any,
    ) -> Optional[str]:
        """
        Find the next state based on transitions and current result.

        Args:
            current_state: Current state name
            transitions: List of all transitions
            context: Execution context
            result: Result from current state execution

        Returns:
            Next state name or None if no valid transition
        """
        # Filter transitions from current state and sort by priority
        valid_transitions = [
            t for t in transitions
            if t.from_state == current_state
        ]
        valid_transitions.sort(key=lambda t: t.priority, reverse=True)

        # Find first transition that can fire
        for transition in valid_transitions:
            if transition.can_transition(context, result):
                logger.debug(
                    f"Transition matched: {transition.from_state} -> {transition.to_state} "
                    f"(condition: {transition.condition.value})"
                )
                return transition.to_state

        # No valid transition found
        logger.warning(f"No valid transition from state '{current_state}'")
        return None


@dataclass
class FSAEngine:
    """
    FSA-3.1: Main workflow engine for FSA execution.

    Orchestrates the entire workflow execution by coordinating:
    - State definitions and transitions
    - Step-by-step execution
    - State tracking and history
    - Error handling and recovery
    - Context management
    """

    states: Dict[str, State] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    initial_state: Optional[str] = None
    error_handler: ErrorHandler = field(default_factory=ErrorHandler)
    max_steps: int = 1000

    def __post_init__(self):
        """Initialize engine components"""
        self.step_runner = StepRunner(self.error_handler)
        self._validate_fsa()

    def _validate_fsa(self) -> None:
        """Validate FSA structure"""
        if not self.states:
            logger.warning("FSA has no states defined")
            return

        # Check for start state
        start_states = [s for s in self.states.values() if s.state_type == StateType.START]
        if not start_states:
            logger.warning("No START state defined in FSA")
        elif len(start_states) > 1:
            logger.warning(f"Multiple START states defined: {[s.name for s in start_states]}")

        # Set initial state if not explicitly set
        if self.initial_state is None and start_states:
            self.initial_state = start_states[0].name
            logger.info(f"Auto-detected initial state: {self.initial_state}")

        # Validate transitions reference valid states
        for transition in self.transitions:
            if transition.from_state not in self.states:
                logger.warning(f"Transition references unknown from_state: {transition.from_state}")
            if transition.to_state not in self.states:
                logger.warning(f"Transition references unknown to_state: {transition.to_state}")

    def add_state(self, state: State) -> None:
        """Add a state to the FSA"""
        self.states[state.name] = state
        logger.debug(f"Added state: {state.name} (type: {state.state_type.value})")

    def add_transition(self, transition: Transition) -> None:
        """Add a transition to the FSA"""
        self.transitions.append(transition)
        logger.debug(
            f"Added transition: {transition.from_state} -> {transition.to_state} "
            f"(condition: {transition.condition.value})"
        )

    def run(
        self,
        initial_context: Optional[StateContext] = None,
        starting_state: Optional[str] = None,
    ) -> StateContext:
        """
        Execute the workflow FSA.

        Args:
            initial_context: Optional initial context (created if not provided)
            starting_state: Optional override for starting state

        Returns:
            Final state context after execution
        """
        # Initialize context and tracker
        context = initial_context or StateContext()
        start_state = starting_state or self.initial_state

        if start_state is None:
            raise ValueError("No initial state defined for FSA")

        if start_state not in self.states:
            raise ValueError(f"Initial state '{start_state}' not found in FSA")

        tracker = StateTracker(start_state)
        tracker.start_execution()

        logger.info(f"Starting FSA execution from state: {start_state}")

        # Main execution loop
        steps = 0
        while steps < self.max_steps:
            steps += 1

            # Get current state
            current_state = self.states.get(tracker.current_state)
            if current_state is None:
                logger.error(f"State '{tracker.current_state}' not found")
                break

            # Add to context history
            context.history.append(current_state.name)

            # Execute the state
            result, status = self.step_runner.run_step(current_state, context, tracker)

            # Handle errors
            if status == ExecutionStatus.FAILED:
                recovery_state = self.error_handler.handle_error(
                    current_state,
                    result if isinstance(result, Exception) else Exception("Unknown error"),
                    context,
                )

                if recovery_state is None:
                    logger.error("Execution failed with no recovery")
                    break

                # Transition to recovery state
                tracker.transition_to(recovery_state)
                continue

            # Check if we've reached an end state
            if current_state.state_type in (StateType.END, StateType.ERROR):
                logger.info(f"Reached {current_state.state_type.value} state: {current_state.name}")
                break

            # Find next state
            next_state = self.step_runner.find_next_state(
                current_state.name,
                self.transitions,
                context,
                result,
            )

            if next_state is None:
                logger.warning(f"No valid transition from state '{current_state.name}', stopping")
                break

            # Transition to next state
            tracker.transition_to(next_state)

        # Finalize execution
        tracker.end_execution()

        # Add execution metadata to context
        context.metadata.update({
            "execution": tracker.get_snapshot(),
            "completed_steps": steps,
            "max_steps_reached": steps >= self.max_steps,
        })

        logger.info(
            f"FSA execution completed: {steps} steps, "
            f"{tracker.total_transitions} transitions, "
            f"{tracker.get_duration_ms():.2f}ms"
        )

        return context

    def run_async(
        self,
        initial_context: Optional[StateContext] = None,
        starting_state: Optional[str] = None,
    ) -> Iterator[tuple[str, StateContext]]:
        """
        Execute the workflow FSA with step-by-step yielding.

        Yields:
            Tuple of (state_name, context) after each step
        """
        # Initialize context and tracker
        context = initial_context or StateContext()
        start_state = starting_state or self.initial_state

        if start_state is None:
            raise ValueError("No initial state defined for FSA")

        if start_state not in self.states:
            raise ValueError(f"Initial state '{start_state}' not found in FSA")

        tracker = StateTracker(start_state)
        tracker.start_execution()

        logger.info(f"Starting async FSA execution from state: {start_state}")

        # Main execution loop
        steps = 0
        while steps < self.max_steps:
            steps += 1

            # Get current state
            current_state = self.states.get(tracker.current_state)
            if current_state is None:
                logger.error(f"State '{tracker.current_state}' not found")
                break

            # Add to context history
            context.history.append(current_state.name)

            # Yield before execution
            yield (current_state.name, deepcopy(context))

            # Execute the state
            result, status = self.step_runner.run_step(current_state, context, tracker)

            # Handle errors
            if status == ExecutionStatus.FAILED:
                recovery_state = self.error_handler.handle_error(
                    current_state,
                    result if isinstance(result, Exception) else Exception("Unknown error"),
                    context,
                )

                if recovery_state is None:
                    logger.error("Execution failed with no recovery")
                    break

                tracker.transition_to(recovery_state)
                continue

            # Check if we've reached an end state
            if current_state.state_type in (StateType.END, StateType.ERROR):
                logger.info(f"Reached {current_state.state_type.value} state: {current_state.name}")
                break

            # Find next state
            next_state = self.step_runner.find_next_state(
                current_state.name,
                self.transitions,
                context,
                result,
            )

            if next_state is None:
                logger.warning(f"No valid transition from state '{current_state.name}', stopping")
                break

            # Transition to next state
            tracker.transition_to(next_state)

        # Finalize execution
        tracker.end_execution()

        # Add execution metadata to context
        context.metadata.update({
            "execution": tracker.get_snapshot(),
            "completed_steps": steps,
            "max_steps_reached": steps >= self.max_steps,
        })

        # Final yield with complete context
        yield (tracker.current_state, context)

        logger.info(
            f"Async FSA execution completed: {steps} steps, "
            f"{tracker.total_transitions} transitions, "
            f"{tracker.get_duration_ms():.2f}ms"
        )

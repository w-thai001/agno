"""
State Machine FSA Implementation

Provides flexible state machine implementation for FSA lifecycle management,
state transitions, event handling, and workflow orchestration. Enables complex
multi-state FSA behavior with validation, guards, actions, and transition
history tracking.
"""

from __future__ import annotations

import json
import pickle
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field


# ============================================================================
# Enums and Constants
# ============================================================================


class StateStatus(str, Enum):
    """Status of a state in the state machine."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENTERED = "entered"
    EXITED = "exited"


class TransitionStatus(str, Enum):
    """Status of a transition attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class PersistenceFormat(str, Enum):
    """Format for state persistence."""
    JSON = "json"
    PICKLE = "pickle"


# ============================================================================
# Core Data Models
# ============================================================================


class State(BaseModel):
    """
    Represents a state in the finite state machine.

    A state can have entry and exit actions that execute when transitioning
    into or out of the state.

    Attributes:
        name: Unique identifier for the state
        description: Human-readable description of the state
        entry_action: Optional callable executed when entering the state
        exit_action: Optional callable executed when exiting the state
        metadata: Additional state-specific data
        is_initial: Whether this is an initial state
        is_final: Whether this is a final/terminal state
    """
    name: str
    description: Optional[str] = None
    entry_action: Optional[str] = None  # Stored as string reference
    exit_action: Optional[str] = None  # Stored as string reference
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_initial: bool = False
    is_final: bool = False

    class Config:
        arbitrary_types_allowed = True

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, State):
            return self.name == other.name
        return False


class Event(BaseModel):
    """
    Represents an event that triggers a state transition.

    Attributes:
        name: Unique identifier for the event
        description: Human-readable description of the event
        payload: Data associated with the event
        timestamp: When the event was created
        priority: Event priority for ordering (higher = more important)
    """
    name: str
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = 0

    def __hash__(self) -> int:
        return hash(self.name)


class Transition(BaseModel):
    """
    Represents a transition between states.

    Attributes:
        from_state: Source state
        to_state: Destination state
        event: Event that triggers this transition
        guard: Optional callable that must return True for transition to proceed
        action: Optional callable executed during transition
        priority: Transition priority when multiple transitions match
        metadata: Additional transition-specific data
    """
    from_state: State
    to_state: State
    event: Event
    guard: Optional[str] = None  # Stored as string reference
    action: Optional[str] = None  # Stored as string reference
    priority: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class Context(BaseModel):
    """
    Execution context for the state machine.

    Maintains the current state and any shared data needed across
    transitions and actions.

    Attributes:
        data: Shared data dictionary
        variables: State machine variables
        stack: Call stack for nested state machines
        trace: Execution trace for debugging
    """
    data: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    stack: List[str] = Field(default_factory=list)
    trace: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True

    def set(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.data.get(key, default)

    def add_trace(self, message: str) -> None:
        """Add a trace message."""
        self.trace.append(f"[{datetime.now().isoformat()}] {message}")


class Action(BaseModel):
    """
    Represents an action to be executed.

    Attributes:
        name: Action identifier
        callable_ref: Reference to the callable function
        description: Human-readable description
    """
    name: str
    callable_ref: str
    description: Optional[str] = None


# ============================================================================
# Result Models
# ============================================================================


class ActionResult(BaseModel):
    """
    Result of executing an action.

    Attributes:
        success: Whether the action succeeded
        result: Return value from the action
        error: Error message if action failed
        execution_time: Time taken to execute (seconds)
    """
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    class Config:
        arbitrary_types_allowed = True


class TransitionResult(BaseModel):
    """
    Result of a state transition.

    Attributes:
        status: Status of the transition
        from_state: Source state
        to_state: Destination state (may be same as from_state if transition failed)
        event: Event that triggered the transition
        guard_passed: Whether guard condition passed
        action_result: Result of transition action if any
        error: Error message if transition failed
        timestamp: When the transition occurred
    """
    status: TransitionStatus
    from_state: State
    to_state: State
    event: Event
    guard_passed: bool = True
    action_result: Optional[ActionResult] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class HistoryEntry(BaseModel):
    """
    Record of a state transition for audit trail.

    Attributes:
        id: Unique identifier for this history entry
        from_state: Source state name
        to_state: Destination state name
        event: Event name that triggered transition
        timestamp: When the transition occurred
        context_snapshot: Snapshot of context at transition time
        success: Whether transition succeeded
        metadata: Additional metadata
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_state: str
    to_state: str
    event: str
    timestamp: datetime
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsistencyReport(BaseModel):
    """
    Report on state consistency validation.

    Attributes:
        is_consistent: Whether state is consistent
        errors: List of consistency errors found
        warnings: List of consistency warnings
        state: State that was validated
        context: Context that was validated
    """
    is_consistent: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    state: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PersistenceResult(BaseModel):
    """
    Result of persisting state.

    Attributes:
        success: Whether persistence succeeded
        persistence_id: Unique identifier for the persisted state
        format: Format used for persistence
        location: Where the state was persisted
        error: Error message if persistence failed
    """
    success: bool
    persistence_id: Optional[str] = None
    format: PersistenceFormat = PersistenceFormat.JSON
    location: Optional[str] = None
    error: Optional[str] = None


class StateRestoreResult(BaseModel):
    """
    Result of restoring state.

    Attributes:
        success: Whether restore succeeded
        state: Restored state
        context: Restored context
        timestamp: When state was originally persisted
        error: Error message if restore failed
    """
    success: bool
    state: Optional[State] = None
    context: Optional[Context] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class TransitionAnalysis(BaseModel):
    """
    Analysis of transition patterns.

    Attributes:
        total_transitions: Total number of transitions
        successful_transitions: Number of successful transitions
        failed_transitions: Number of failed transitions
        state_frequencies: How often each state was visited
        event_frequencies: How often each event was triggered
        common_paths: Most common transition paths
        average_transition_time: Average time between transitions
        anomalies: Detected anomalies in transition patterns
    """
    total_transitions: int = 0
    successful_transitions: int = 0
    failed_transitions: int = 0
    state_frequencies: Dict[str, int] = Field(default_factory=dict)
    event_frequencies: Dict[str, int] = Field(default_factory=dict)
    common_paths: List[Tuple[str, str, int]] = Field(default_factory=list)
    average_transition_time: float = 0.0
    anomalies: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """
    Result of validating state machine configuration.

    Attributes:
        is_valid: Whether configuration is valid
        errors: List of validation errors
        warnings: List of validation warnings
        unreachable_states: States that cannot be reached
        dead_end_states: States with no outgoing transitions
        initial_states: List of initial states
        final_states: List of final states
    """
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    unreachable_states: List[str] = Field(default_factory=list)
    dead_end_states: List[str] = Field(default_factory=list)
    initial_states: List[str] = Field(default_factory=list)
    final_states: List[str] = Field(default_factory=list)


class StateMachineConfig(BaseModel):
    """
    Configuration for a state machine.

    Attributes:
        name: Name of the state machine
        states: List of all states
        transitions: List of all transitions
        initial_state: The starting state
        actions: Registry of available actions
        guards: Registry of available guard functions
    """
    name: str
    states: List[State] = Field(default_factory=list)
    transitions: List[Transition] = Field(default_factory=list)
    initial_state: Optional[State] = None
    actions: Dict[str, str] = Field(default_factory=dict)
    guards: Dict[str, str] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class WorkflowDefinition(BaseModel):
    """
    Definition for a multi-step workflow.

    Attributes:
        name: Workflow name
        description: Workflow description
        steps: List of workflow steps (events to trigger in order)
        initial_state: Starting state for the workflow
        expected_final_state: Expected final state
        timeout: Maximum execution time in seconds
        on_error: Error handling strategy
    """
    name: str
    description: Optional[str] = None
    steps: List[Event] = Field(default_factory=list)
    initial_state: Optional[State] = None
    expected_final_state: Optional[State] = None
    timeout: float = 300.0
    on_error: str = "stop"  # stop, continue, retry

    class Config:
        arbitrary_types_allowed = True


class WorkflowResult(BaseModel):
    """
    Result of executing a workflow.

    Attributes:
        success: Whether workflow completed successfully
        final_state: State at workflow completion
        steps_completed: Number of steps completed
        total_steps: Total number of steps
        execution_time: Total execution time
        transition_history: History of all transitions
        errors: List of errors encountered
    """
    success: bool
    final_state: Optional[State] = None
    steps_completed: int = 0
    total_steps: int = 0
    execution_time: float = 0.0
    transition_history: List[HistoryEntry] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class StateMachineResult(BaseModel):
    """
    Result of executing a state machine.

    Attributes:
        success: Whether execution completed successfully
        final_state: Final state reached
        events_processed: Number of events processed
        context: Final execution context
        history: Transition history
        errors: List of errors encountered
    """
    success: bool
    final_state: Optional[State] = None
    events_processed: int = 0
    context: Optional[Context] = None
    history: List[HistoryEntry] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Main State Machine FSA Class
# ============================================================================


@dataclass
class StateMachineFSA:
    """
    Flexible state machine implementation for FSA lifecycle management.

    Provides comprehensive state management with support for:
    - State definitions with entry/exit actions
    - Event-driven transitions with guard conditions
    - Action execution with context passing
    - Transition history tracking for audit trails
    - State validation and consistency checking
    - State persistence and recovery
    - Workflow orchestration for complex flows
    - Transition pattern analysis

    Attributes:
        name: Name of the state machine
        config: State machine configuration
        current_state: Currently active state
        context: Execution context
        history: Transition history
        actions: Registry of action functions
        guards: Registry of guard functions
        persistence_path: Path for state persistence
    """

    name: str = "StateMachine"
    config: Optional[StateMachineConfig] = None
    current_state: Optional[State] = None
    context: Context = field(default_factory=Context)
    history: List[HistoryEntry] = field(default_factory=list)
    actions: Dict[str, Callable] = field(default_factory=dict)
    guards: Dict[str, Callable] = field(default_factory=dict)
    persistence_path: Optional[Path] = None

    # Internal state tracking
    _states: Dict[str, State] = field(default_factory=dict)
    _transitions: Dict[str, List[Transition]] = field(default_factory=lambda: defaultdict(list))
    _initial_state: Optional[State] = None

    def __post_init__(self):
        """Initialize the state machine."""
        if self.config:
            self._load_config(self.config)

        if self.persistence_path is None:
            self.persistence_path = Path("/tmp/state_machine_persistence")
            self.persistence_path.mkdir(exist_ok=True)

    def _load_config(self, config: StateMachineConfig) -> None:
        """Load configuration into the state machine."""
        self.name = config.name

        # Load states
        for state in config.states:
            self._states[state.name] = state
            if state.is_initial:
                self._initial_state = state

        # Load transitions
        for transition in config.transitions:
            key = f"{transition.from_state.name}:{transition.event.name}"
            self._transitions[key].append(transition)

        # Set initial state
        if config.initial_state:
            self._initial_state = config.initial_state
            self.current_state = config.initial_state

    def define_state(
        self,
        name: str,
        entry_action: Optional[Callable] = None,
        exit_action: Optional[Callable] = None,
        description: Optional[str] = None,
        is_initial: bool = False,
        is_final: bool = False,
        **metadata
    ) -> State:
        """
        Create and register a state definition.

        Args:
            name: Unique state identifier
            entry_action: Function to call when entering state
            exit_action: Function to call when exiting state
            description: Human-readable state description
            is_initial: Whether this is an initial state
            is_final: Whether this is a final state
            **metadata: Additional state metadata

        Returns:
            State: The created state
        """
        # Register actions if provided
        entry_ref = None
        if entry_action:
            entry_ref = f"entry_{name}"
            self.actions[entry_ref] = entry_action

        exit_ref = None
        if exit_action:
            exit_ref = f"exit_{name}"
            self.actions[exit_ref] = exit_action

        state = State(
            name=name,
            description=description,
            entry_action=entry_ref,
            exit_action=exit_ref,
            metadata=metadata,
            is_initial=is_initial,
            is_final=is_final
        )

        self._states[name] = state

        if is_initial and self._initial_state is None:
            self._initial_state = state

        return state

    def define_transition(
        self,
        from_state: State,
        to_state: State,
        event: Event,
        guard: Optional[Callable] = None,
        action: Optional[Callable] = None,
        priority: int = 0,
        **metadata
    ) -> Transition:
        """
        Define a state transition.

        Args:
            from_state: Source state
            to_state: Destination state
            event: Event that triggers transition
            guard: Optional guard condition
            action: Optional action to execute during transition
            priority: Transition priority
            **metadata: Additional transition metadata

        Returns:
            Transition: The created transition
        """
        # Register guard and action if provided
        guard_ref = None
        if guard:
            guard_ref = f"guard_{from_state.name}_{to_state.name}_{event.name}"
            self.guards[guard_ref] = guard

        action_ref = None
        if action:
            action_ref = f"action_{from_state.name}_{to_state.name}_{event.name}"
            self.actions[action_ref] = action

        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            guard=guard_ref,
            action=action_ref,
            priority=priority,
            metadata=metadata
        )

        key = f"{from_state.name}:{event.name}"
        self._transitions[key].append(transition)
        # Sort by priority (higher priority first)
        self._transitions[key].sort(key=lambda t: t.priority, reverse=True)

        return transition

    def execute_guard(self, transition: Transition, context: Context) -> bool:
        """
        Evaluate a guard condition.

        Args:
            transition: Transition with guard to evaluate
            context: Current execution context

        Returns:
            bool: True if guard passes (or no guard), False otherwise
        """
        if not transition.guard:
            return True

        guard_func = self.guards.get(transition.guard)
        if not guard_func:
            context.add_trace(f"Guard function '{transition.guard}' not found, allowing transition")
            return True

        try:
            result = guard_func(context)
            context.add_trace(f"Guard '{transition.guard}' evaluated to {result}")
            return bool(result)
        except Exception as e:
            context.add_trace(f"Guard '{transition.guard}' raised exception: {e}")
            return False

    def execute_action(self, action: str, context: Context) -> ActionResult:
        """
        Execute an action.

        Args:
            action: Action reference to execute
            context: Execution context

        Returns:
            ActionResult: Result of action execution
        """
        start_time = datetime.now()

        action_func = self.actions.get(action)
        if not action_func:
            return ActionResult(
                success=False,
                error=f"Action '{action}' not found",
                execution_time=0.0
            )

        try:
            result = action_func(context)
            execution_time = (datetime.now() - start_time).total_seconds()
            context.add_trace(f"Action '{action}' executed successfully")
            return ActionResult(
                success=True,
                result=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            context.add_trace(f"Action '{action}' failed: {e}")
            return ActionResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    def handle_event(self, current_state: State, event: Event) -> TransitionResult:
        """
        Process an event and execute the appropriate transition.

        Args:
            current_state: Current state
            event: Event to handle

        Returns:
            TransitionResult: Result of the transition attempt
        """
        key = f"{current_state.name}:{event.name}"
        transitions = self._transitions.get(key, [])

        if not transitions:
            self.context.add_trace(f"No transition defined for event '{event.name}' in state '{current_state.name}'")
            return TransitionResult(
                status=TransitionStatus.BLOCKED,
                from_state=current_state,
                to_state=current_state,
                event=event,
                error=f"No transition defined for event '{event.name}'"
            )

        # Try transitions in priority order
        for transition in transitions:
            # Execute exit action of current state
            if current_state.exit_action:
                exit_result = self.execute_action(current_state.exit_action, self.context)
                if not exit_result.success:
                    self.context.add_trace(f"Exit action failed for state '{current_state.name}'")

            # Evaluate guard
            guard_passed = self.execute_guard(transition, self.context)
            if not guard_passed:
                self.context.add_trace(f"Guard failed for transition to '{transition.to_state.name}'")
                continue

            # Execute transition action
            action_result = None
            if transition.action:
                action_result = self.execute_action(transition.action, self.context)
                if not action_result.success:
                    self.context.add_trace(f"Transition action failed")
                    return TransitionResult(
                        status=TransitionStatus.FAILED,
                        from_state=current_state,
                        to_state=current_state,
                        event=event,
                        guard_passed=True,
                        action_result=action_result,
                        error=action_result.error
                    )

            # Execute entry action of new state
            if transition.to_state.entry_action:
                entry_result = self.execute_action(transition.to_state.entry_action, self.context)
                if not entry_result.success:
                    self.context.add_trace(f"Entry action failed for state '{transition.to_state.name}'")

            # Transition successful
            self.current_state = transition.to_state
            self.context.add_trace(
                f"Transitioned from '{current_state.name}' to '{transition.to_state.name}' on event '{event.name}'"
            )

            return TransitionResult(
                status=TransitionStatus.SUCCESS,
                from_state=current_state,
                to_state=transition.to_state,
                event=event,
                guard_passed=True,
                action_result=action_result
            )

        # No transition with passing guard found
        return TransitionResult(
            status=TransitionStatus.BLOCKED,
            from_state=current_state,
            to_state=current_state,
            event=event,
            guard_passed=False,
            error="All guards failed"
        )

    def track_transition(
        self,
        from_state: State,
        to_state: State,
        event: Event,
        timestamp: datetime,
        success: bool = True
    ) -> HistoryEntry:
        """
        Record a transition in the history.

        Args:
            from_state: Source state
            to_state: Destination state
            event: Event that triggered transition
            timestamp: When transition occurred
            success: Whether transition succeeded

        Returns:
            HistoryEntry: The created history entry
        """
        entry = HistoryEntry(
            from_state=from_state.name,
            to_state=to_state.name,
            event=event.name,
            timestamp=timestamp,
            context_snapshot=self.context.model_dump(),
            success=success
        )

        self.history.append(entry)
        return entry

    def validate_state_consistency(
        self,
        current_state: State,
        context: Context
    ) -> ConsistencyReport:
        """
        Check state validity and consistency.

        Args:
            current_state: State to validate
            context: Context to validate

        Returns:
            ConsistencyReport: Validation report
        """
        errors = []
        warnings = []

        # Check if state exists in registered states
        if current_state.name not in self._states:
            errors.append(f"State '{current_state.name}' not registered in state machine")

        # Check for required context variables (if defined in metadata)
        required_vars = current_state.metadata.get("required_context", [])
        for var in required_vars:
            if var not in context.data:
                errors.append(f"Required context variable '{var}' missing for state '{current_state.name}'")

        # Check for state invariants (if defined)
        invariants = current_state.metadata.get("invariants", [])
        for invariant_name in invariants:
            if invariant_name in self.guards:
                if not self.execute_guard(
                    Transition(
                        from_state=current_state,
                        to_state=current_state,
                        event=Event(name="invariant_check"),
                        guard=invariant_name
                    ),
                    context
                ):
                    errors.append(f"Invariant '{invariant_name}' violated in state '{current_state.name}'")

        # Check if we're in a final state with available transitions
        if current_state.is_final:
            has_transitions = any(
                key.startswith(f"{current_state.name}:")
                for key in self._transitions.keys()
            )
            if has_transitions:
                warnings.append(f"Final state '{current_state.name}' has outgoing transitions")

        return ConsistencyReport(
            is_consistent=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            state=current_state.name,
            context=context.model_dump()
        )

    def persist_state(
        self,
        state: State,
        context: Context,
        format: PersistenceFormat = PersistenceFormat.JSON
    ) -> PersistenceResult:
        """
        Save state for recovery.

        Args:
            state: State to persist
            context: Context to persist
            format: Persistence format (JSON or PICKLE)

        Returns:
            PersistenceResult: Result of persistence operation
        """
        persistence_id = str(uuid4())

        try:
            data = {
                "state": state.model_dump(),
                "context": context.model_dump(),
                "timestamp": datetime.now().isoformat(),
                "history": [h.model_dump() for h in self.history]
            }

            if format == PersistenceFormat.JSON:
                file_path = self.persistence_path / f"{persistence_id}.json"
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            else:  # PICKLE
                file_path = self.persistence_path / f"{persistence_id}.pkl"
                with open(file_path, "wb") as f:
                    pickle.dump(data, f)

            return PersistenceResult(
                success=True,
                persistence_id=persistence_id,
                format=format,
                location=str(file_path)
            )
        except Exception as e:
            return PersistenceResult(
                success=False,
                error=str(e)
            )

    def restore_state(self, persistence_id: str) -> StateRestoreResult:
        """
        Recover saved state.

        Args:
            persistence_id: ID of the persisted state

        Returns:
            StateRestoreResult: Result of restore operation
        """
        try:
            # Try JSON first
            json_path = self.persistence_path / f"{persistence_id}.json"
            pkl_path = self.persistence_path / f"{persistence_id}.pkl"

            data = None
            if json_path.exists():
                with open(json_path, "r") as f:
                    data = json.load(f)
            elif pkl_path.exists():
                with open(pkl_path, "rb") as f:
                    data = pickle.load(f)
            else:
                return StateRestoreResult(
                    success=False,
                    error=f"No persisted state found for ID '{persistence_id}'"
                )

            state = State(**data["state"])
            context = Context(**data["context"])
            timestamp = datetime.fromisoformat(data["timestamp"])

            # Restore history
            self.history = [HistoryEntry(**h) for h in data.get("history", [])]

            # Update current state and context
            self.current_state = state
            self.context = context

            return StateRestoreResult(
                success=True,
                state=state,
                context=context,
                timestamp=timestamp
            )
        except Exception as e:
            return StateRestoreResult(
                success=False,
                error=str(e)
            )

    def analyze_transitions(self, history: List[HistoryEntry]) -> TransitionAnalysis:
        """
        Analyze transition patterns.

        Args:
            history: List of historical transitions to analyze

        Returns:
            TransitionAnalysis: Analysis results
        """
        if not history:
            return TransitionAnalysis()

        analysis = TransitionAnalysis()
        analysis.total_transitions = len(history)

        state_freq: Dict[str, int] = defaultdict(int)
        event_freq: Dict[str, int] = defaultdict(int)
        path_freq: Dict[Tuple[str, str], int] = defaultdict(int)
        transition_times: List[float] = []

        successful = 0
        failed = 0

        for i, entry in enumerate(history):
            # Count success/failure
            if entry.success:
                successful += 1
            else:
                failed += 1

            # Track state frequencies
            state_freq[entry.from_state] += 1
            state_freq[entry.to_state] += 1

            # Track event frequencies
            event_freq[entry.event] += 1

            # Track path frequencies
            path_freq[(entry.from_state, entry.to_state)] += 1

            # Calculate transition times
            if i > 0:
                time_diff = (entry.timestamp - history[i-1].timestamp).total_seconds()
                transition_times.append(time_diff)

        analysis.successful_transitions = successful
        analysis.failed_transitions = failed
        analysis.state_frequencies = dict(state_freq)
        analysis.event_frequencies = dict(event_freq)

        # Find common paths
        sorted_paths = sorted(path_freq.items(), key=lambda x: x[1], reverse=True)
        analysis.common_paths = [(p[0], p[1], count) for p, count in sorted_paths[:10]]

        # Calculate average transition time
        if transition_times:
            analysis.average_transition_time = sum(transition_times) / len(transition_times)

        # Detect anomalies
        if failed > successful:
            analysis.anomalies.append("More failed transitions than successful ones")

        # Check for loops
        for (from_state, to_state), count in path_freq.items():
            if from_state == to_state and count > 1:
                analysis.anomalies.append(f"Self-loop detected in state '{from_state}' ({count} times)")

        return analysis

    def validate(self, machine_config: StateMachineConfig) -> ValidationResult:
        """
        Validate state machine configuration.

        Args:
            machine_config: Configuration to validate

        Returns:
            ValidationResult: Validation results
        """
        errors = []
        warnings = []
        unreachable_states = []
        dead_end_states = []
        initial_states = []
        final_states = []

        # Check for initial state
        if not machine_config.initial_state:
            has_initial = any(s.is_initial for s in machine_config.states)
            if not has_initial:
                errors.append("No initial state defined")
        else:
            initial_states.append(machine_config.initial_state.name)

        # Collect all state names
        state_names = {s.name for s in machine_config.states}

        # Build reachability graph
        reachable: Set[str] = set()
        has_outgoing: Set[str] = set()

        if machine_config.initial_state:
            reachable.add(machine_config.initial_state.name)

        # Track states with outgoing transitions
        for transition in machine_config.transitions:
            has_outgoing.add(transition.from_state.name)
            # Check if states exist
            if transition.from_state.name not in state_names:
                errors.append(f"Transition references unknown state '{transition.from_state.name}'")
            if transition.to_state.name not in state_names:
                errors.append(f"Transition references unknown state '{transition.to_state.name}'")

        # Find reachable states using BFS
        if machine_config.initial_state:
            queue = [machine_config.initial_state.name]
            while queue:
                current = queue.pop(0)
                for transition in machine_config.transitions:
                    if transition.from_state.name == current:
                        if transition.to_state.name not in reachable:
                            reachable.add(transition.to_state.name)
                            queue.append(transition.to_state.name)

        # Find unreachable states
        for state in machine_config.states:
            if state.name not in reachable and not state.is_initial:
                unreachable_states.append(state.name)

            # Track initial and final states
            if state.is_initial:
                initial_states.append(state.name)
            if state.is_final:
                final_states.append(state.name)

        # Find dead-end states (no outgoing transitions)
        for state in machine_config.states:
            if state.name not in has_outgoing and not state.is_final:
                dead_end_states.append(state.name)
                warnings.append(f"State '{state.name}' has no outgoing transitions and is not marked as final")

        # Check for duplicate state names
        state_name_counts = defaultdict(int)
        for state in machine_config.states:
            state_name_counts[state.name] += 1

        for name, count in state_name_counts.items():
            if count > 1:
                errors.append(f"Duplicate state name '{name}' found {count} times")

        # Check for multiple initial states
        if len(initial_states) > 1:
            warnings.append(f"Multiple initial states defined: {initial_states}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            unreachable_states=unreachable_states,
            dead_end_states=dead_end_states,
            initial_states=initial_states,
            final_states=final_states
        )

    def orchestrate_workflow(self, workflow_def: WorkflowDefinition) -> WorkflowResult:
        """
        Execute multi-state workflow.

        Args:
            workflow_def: Workflow definition

        Returns:
            WorkflowResult: Result of workflow execution
        """
        start_time = datetime.now()

        # Set initial state
        if workflow_def.initial_state:
            self.current_state = workflow_def.initial_state
        elif self._initial_state:
            self.current_state = self._initial_state
        else:
            return WorkflowResult(
                success=False,
                errors=["No initial state defined for workflow"]
            )

        result = WorkflowResult(
            total_steps=len(workflow_def.steps),
            final_state=self.current_state
        )

        # Execute workflow steps
        for i, event in enumerate(workflow_def.steps):
            try:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > workflow_def.timeout:
                    result.errors.append(f"Workflow timeout after {elapsed:.2f} seconds")
                    break

                # Handle event
                transition_result = self.handle_event(self.current_state, event)

                # Track transition
                history_entry = self.track_transition(
                    from_state=transition_result.from_state,
                    to_state=transition_result.to_state,
                    event=event,
                    timestamp=transition_result.timestamp,
                    success=transition_result.status == TransitionStatus.SUCCESS
                )
                result.transition_history.append(history_entry)

                # Handle transition failure
                if transition_result.status != TransitionStatus.SUCCESS:
                    error_msg = f"Step {i+1} failed: {transition_result.error}"
                    result.errors.append(error_msg)

                    if workflow_def.on_error == "stop":
                        break
                    elif workflow_def.on_error == "continue":
                        continue
                    # For retry, we would need additional logic
                else:
                    result.steps_completed += 1

            except Exception as e:
                error_msg = f"Step {i+1} raised exception: {str(e)}"
                result.errors.append(error_msg)

                if workflow_def.on_error == "stop":
                    break

        # Calculate execution time
        result.execution_time = (datetime.now() - start_time).total_seconds()
        result.final_state = self.current_state

        # Check if we reached expected final state
        if workflow_def.expected_final_state:
            if self.current_state.name != workflow_def.expected_final_state.name:
                result.errors.append(
                    f"Did not reach expected final state '{workflow_def.expected_final_state.name}', "
                    f"ended in '{self.current_state.name}'"
                )

        result.success = len(result.errors) == 0 and result.steps_completed == result.total_steps

        return result

    def execute(self, initial_state: State, events: List[Event]) -> StateMachineResult:
        """
        Main state machine execution.

        Args:
            initial_state: Starting state
            events: List of events to process

        Returns:
            StateMachineResult: Execution result
        """
        self.current_state = initial_state
        self.context = Context()
        self.history = []

        result = StateMachineResult(
            context=self.context,
            final_state=initial_state
        )

        for event in events:
            try:
                # Handle event
                transition_result = self.handle_event(self.current_state, event)

                # Track transition
                self.track_transition(
                    from_state=transition_result.from_state,
                    to_state=transition_result.to_state,
                    event=event,
                    timestamp=transition_result.timestamp,
                    success=transition_result.status == TransitionStatus.SUCCESS
                )

                # Record errors
                if transition_result.status != TransitionStatus.SUCCESS:
                    result.errors.append(transition_result.error or "Transition failed")

                result.events_processed += 1

            except Exception as e:
                result.errors.append(f"Error processing event '{event.name}': {str(e)}")

        result.final_state = self.current_state
        result.history = self.history.copy()
        result.success = len(result.errors) == 0

        return result

"""
State management for workflow engine.

Defines state models, transitions, and validation logic for the FSA-based workflow engine.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator


class StateStatus(str, Enum):
    """Status of a state during execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TransitionCondition(BaseModel):
    """Condition for state transition."""

    condition: str = Field(..., description="Condition expression to evaluate")
    target_state: str = Field(..., description="Target state if condition is true")
    description: Optional[str] = Field(None, description="Human-readable description")

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate the condition against the execution context.

        Args:
            context: Execution context containing variables

        Returns:
            True if condition is met, False otherwise
        """
        try:
            # Safe evaluation of simple conditions
            # Supports: ==, !=, <, >, <=, >=, in, not in, and, or
            return bool(eval(self.condition, {"__builtins__": {}}, context))
        except Exception:
            return False


class StateTransition(BaseModel):
    """Defines a transition between states."""

    from_state: str = Field(..., description="Source state name")
    to_state: str = Field(..., description="Target state name")
    conditions: List[TransitionCondition] = Field(
        default_factory=list, description="Conditions for this transition"
    )
    on_transition: Optional[Callable] = Field(
        None, description="Callback executed during transition", exclude=True
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional transition metadata"
    )

    def can_transition(self, context: Dict[str, Any]) -> bool:
        """
        Check if transition is allowed based on conditions.

        Args:
            context: Execution context

        Returns:
            True if transition is allowed
        """
        if not self.conditions:
            return True

        # All conditions must be met
        return all(cond.evaluate(context) for cond in self.conditions)


class State(BaseModel):
    """Represents a state in the workflow FSA."""

    name: str = Field(..., description="Unique state name")
    description: Optional[str] = Field(None, description="Human-readable description")
    handler: Optional[Callable] = Field(
        None, description="Function to execute in this state", exclude=True
    )
    transitions: List[StateTransition] = Field(
        default_factory=list, description="Available transitions from this state"
    )
    is_initial: bool = Field(False, description="Whether this is the initial state")
    is_final: bool = Field(False, description="Whether this is a final state")
    allow_parallel: bool = Field(
        False, description="Allow parallel execution of sub-states"
    )
    timeout_seconds: Optional[int] = Field(
        None, description="Maximum execution time for this state"
    )
    retry_count: int = Field(0, description="Number of retries on failure")
    on_enter: Optional[Callable] = Field(
        None, description="Callback when entering state", exclude=True
    )
    on_exit: Optional[Callable] = Field(
        None, description="Callback when exiting state", exclude=True
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional state metadata"
    )

    # Execution tracking
    status: StateStatus = Field(
        default=StateStatus.PENDING, description="Current execution status"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[Any] = Field(None, description="Execution result")
    attempt: int = Field(0, description="Current attempt number")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate state name format."""
        if not v or not v.strip():
            raise ValueError("State name cannot be empty")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("State name must be alphanumeric with _ or -")
        return v

    def add_transition(
        self,
        to_state: str,
        conditions: Optional[List[TransitionCondition]] = None,
        on_transition: Optional[Callable] = None,
    ) -> StateTransition:
        """
        Add a transition from this state.

        Args:
            to_state: Target state name
            conditions: Transition conditions
            on_transition: Callback during transition

        Returns:
            Created transition
        """
        transition = StateTransition(
            from_state=self.name,
            to_state=to_state,
            conditions=conditions or [],
            on_transition=on_transition,
        )
        self.transitions.append(transition)
        return transition

    def get_next_state(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Determine next state based on context and conditions.

        Args:
            context: Execution context

        Returns:
            Name of next state or None
        """
        for transition in self.transitions:
            if transition.can_transition(context):
                return transition.to_state
        return None

    def reset(self) -> None:
        """Reset state execution tracking."""
        self.status = StateStatus.PENDING
        self.error = None
        self.result = None
        self.attempt = 0


class StateGraph(BaseModel):
    """Represents the workflow state graph."""

    states: Dict[str, State] = Field(
        default_factory=dict, description="All states in the workflow"
    )
    initial_state: Optional[str] = Field(None, description="Initial state name")
    final_states: Set[str] = Field(
        default_factory=set, description="Set of final state names"
    )

    def add_state(self, state: State) -> None:
        """
        Add a state to the graph.

        Args:
            state: State to add
        """
        self.states[state.name] = state
        if state.is_initial:
            self.initial_state = state.name
        if state.is_final:
            self.final_states.add(state.name)

    def get_state(self, name: str) -> Optional[State]:
        """Get a state by name."""
        return self.states.get(name)

    def validate_graph(self) -> List[str]:
        """
        Validate the state graph for consistency.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Must have at least one state
        if not self.states:
            errors.append("State graph must have at least one state")
            return errors

        # Must have an initial state
        if not self.initial_state:
            errors.append("State graph must have an initial state")

        # Must have at least one final state
        if not self.final_states:
            errors.append("State graph must have at least one final state")

        # Validate transitions point to existing states
        for state in self.states.values():
            for transition in state.transitions:
                if transition.to_state not in self.states:
                    errors.append(
                        f"State '{state.name}' has transition to unknown state '{transition.to_state}'"
                    )

        # Check for unreachable states (except initial)
        if self.initial_state:
            reachable = self._get_reachable_states(self.initial_state)
            unreachable = set(self.states.keys()) - reachable
            if unreachable:
                errors.append(f"Unreachable states detected: {unreachable}")

        return errors

    def _get_reachable_states(self, start_state: str) -> Set[str]:
        """Get all states reachable from start_state."""
        reachable = {start_state}
        to_visit = [start_state]

        while to_visit:
            current = to_visit.pop()
            state = self.states.get(current)
            if not state:
                continue

            for transition in state.transitions:
                if transition.to_state not in reachable:
                    reachable.add(transition.to_state)
                    to_visit.append(transition.to_state)

        return reachable

    def get_execution_path(self, context: Dict[str, Any]) -> List[str]:
        """
        Get the expected execution path given the current context.

        Args:
            context: Execution context

        Returns:
            List of state names in execution order
        """
        if not self.initial_state:
            return []

        path = [self.initial_state]
        current = self.initial_state
        visited = {current}

        while current not in self.final_states:
            state = self.states.get(current)
            if not state:
                break

            next_state = state.get_next_state(context)
            if not next_state or next_state in visited:
                break

            path.append(next_state)
            visited.add(next_state)
            current = next_state

        return path

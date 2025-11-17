"""Base FSA (Finite State Automaton) class for agno."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from agno.utils.log import logger


class FSAState(Enum):
    """Base enum for FSA states."""
    INITIAL = "initial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class FSATransition:
    """Represents a state transition in an FSA."""
    from_state: str
    to_state: str
    condition: Optional[Callable[[Any], bool]] = None
    action: Optional[Callable[[Any], Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FSA(ABC):
    """Base Finite State Automaton class.

    An FSA manages state transitions and execution flow with explicit states,
    transitions, and validation rules.

    Attributes:
        name: Name of the FSA
        fsa_id: Unique identifier for the FSA instance
        current_state: Current state of the FSA
        states: Set of valid states for this FSA
        transitions: List of defined state transitions
        session_state: Dictionary to store session-level state data
        stateful: Whether FSA maintains state across invocations
        cascade_aware: Whether FSA can cascade to other FSAs
    """

    # FSA identification
    name: Optional[str] = None
    fsa_id: Optional[str] = None

    # State management
    current_state: str = field(default="initial")
    states: Set[str] = field(default_factory=lambda: {"initial", "processing", "completed", "error"})
    transitions: List[FSATransition] = field(default_factory=list)

    # Session and context
    session_state: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    # FSA configuration
    stateful: bool = True
    cascade_aware: bool = False

    # History tracking
    state_history: List[Tuple[str, float]] = field(default_factory=list)
    transition_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize FSA after dataclass initialization."""
        if not self.fsa_id:
            self.fsa_id = str(uuid4())
        if not self.name:
            self.name = self.__class__.__name__
        self._validate_initial_state()

    def _validate_initial_state(self) -> None:
        """Validate that current_state is in the set of valid states."""
        if self.current_state not in self.states:
            raise ValueError(
                f"Initial state '{self.current_state}' not in valid states: {self.states}"
            )

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        condition: Optional[Callable[[Any], bool]] = None,
        action: Optional[Callable[[Any], Any]] = None,
        **metadata
    ) -> None:
        """Add a state transition to the FSA.

        Args:
            from_state: Starting state for transition
            to_state: Destination state for transition
            condition: Optional function to check if transition is valid
            action: Optional function to execute during transition
            metadata: Additional metadata for the transition
        """
        if from_state not in self.states:
            raise ValueError(f"from_state '{from_state}' not in valid states")
        if to_state not in self.states:
            raise ValueError(f"to_state '{to_state}' not in valid states")

        transition = FSATransition(
            from_state=from_state,
            to_state=to_state,
            condition=condition,
            action=action,
            metadata=metadata
        )
        self.transitions.append(transition)
        logger.debug(f"Added transition: {from_state} -> {to_state}")

    def can_transition(self, to_state: str, context: Optional[Any] = None) -> bool:
        """Check if transition to target state is valid.

        Args:
            to_state: Target state to transition to
            context: Optional context for condition evaluation

        Returns:
            True if transition is valid, False otherwise
        """
        if to_state not in self.states:
            return False

        # Find matching transitions from current state
        matching_transitions = [
            t for t in self.transitions
            if t.from_state == self.current_state and t.to_state == to_state
        ]

        if not matching_transitions:
            return False

        # Check conditions for all matching transitions
        for transition in matching_transitions:
            if transition.condition is None or transition.condition(context):
                return True

        return False

    def transition(self, to_state: str, context: Optional[Any] = None) -> bool:
        """Transition to a new state.

        Args:
            to_state: Target state to transition to
            context: Optional context for transition

        Returns:
            True if transition succeeded, False otherwise
        """
        if not self.can_transition(to_state, context):
            logger.warning(
                f"Invalid transition from '{self.current_state}' to '{to_state}'"
            )
            return False

        # Find and execute transition action
        matching_transitions = [
            t for t in self.transitions
            if t.from_state == self.current_state and t.to_state == to_state
        ]

        for transition in matching_transitions:
            if transition.condition is None or transition.condition(context):
                # Execute action if present
                if transition.action:
                    try:
                        transition.action(context)
                    except Exception as e:
                        logger.error(f"Transition action failed: {e}")
                        return False

                # Record transition
                import time
                old_state = self.current_state
                self.current_state = to_state
                self.state_history.append((to_state, time.time()))
                self.transition_history.append({
                    "from": old_state,
                    "to": to_state,
                    "timestamp": time.time(),
                    "metadata": transition.metadata
                })

                logger.info(f"FSA '{self.name}' transitioned: {old_state} -> {to_state}")
                return True

        return False

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.current_state = "initial"
        if not self.stateful:
            self.session_state.clear()
            self.state_history.clear()
            self.transition_history.clear()
        logger.debug(f"FSA '{self.name}' reset to initial state")

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the FSA.

        This method must be implemented by concrete FSA classes.

        Args:
            **kwargs: Arguments for FSA execution

        Returns:
            Result of FSA execution
        """
        pass

    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information.

        Returns:
            Dictionary with current state details
        """
        return {
            "fsa_id": self.fsa_id,
            "name": self.name,
            "current_state": self.current_state,
            "valid_states": list(self.states),
            "transition_count": len(self.transition_history),
            "stateful": self.stateful,
            "cascade_aware": self.cascade_aware
        }

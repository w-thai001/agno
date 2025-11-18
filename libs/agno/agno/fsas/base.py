"""Base class for Finite State Automaton (FSA) implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from agno.utils.log import logger


class FSAState(Enum):
    """Base states for FSA."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass
class FSATransition:
    """Represents a state transition in the FSA."""

    from_state: FSAState
    to_state: FSAState
    trigger: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FSAContext:
    """Context for FSA execution."""

    id: str = field(default_factory=lambda: str(uuid4()))
    current_state: FSAState = FSAState.IDLE
    previous_state: Optional[FSAState] = None
    transitions: List[FSATransition] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class BaseFSA(ABC):
    """
    Base class for Finite State Automaton implementations.

    Provides core functionality for state management, transitions,
    validation, and error handling.
    """

    def __init__(self, name: Optional[str] = None, **kwargs):
        """
        Initialize the FSA.

        Args:
            name: Optional name for the FSA instance
            **kwargs: Additional configuration parameters
        """
        self.name = name or self.__class__.__name__
        self.context = FSAContext()
        self._allowed_transitions: Dict[FSAState, Set[FSAState]] = {}
        self._initialize_transitions()
        logger.debug(f"Initialized {self.name} FSA")

    @abstractmethod
    def _initialize_transitions(self) -> None:
        """
        Initialize allowed state transitions.

        Must be implemented by subclasses to define valid transitions.
        """
        pass

    def add_transition(
        self,
        from_state: FSAState,
        to_state: FSAState
    ) -> None:
        """
        Add an allowed state transition.

        Args:
            from_state: Source state
            to_state: Target state
        """
        if from_state not in self._allowed_transitions:
            self._allowed_transitions[from_state] = set()
        self._allowed_transitions[from_state].add(to_state)

    def can_transition(
        self,
        from_state: FSAState,
        to_state: FSAState
    ) -> bool:
        """
        Check if a transition is allowed.

        Args:
            from_state: Source state
            to_state: Target state

        Returns:
            True if transition is allowed, False otherwise
        """
        return (
            from_state in self._allowed_transitions
            and to_state in self._allowed_transitions[from_state]
        )

    def transition(
        self,
        to_state: FSAState,
        trigger: str = "manual",
        **metadata
    ) -> bool:
        """
        Transition to a new state.

        Args:
            to_state: Target state
            trigger: What triggered the transition
            **metadata: Additional transition metadata

        Returns:
            True if transition was successful, False otherwise
        """
        current = self.context.current_state

        if not self.can_transition(current, to_state):
            logger.warning(
                f"{self.name}: Invalid transition {current.value} -> {to_state.value}"
            )
            return False

        # Record transition
        transition = FSATransition(
            from_state=current,
            to_state=to_state,
            trigger=trigger,
            metadata=metadata
        )
        self.context.transitions.append(transition)

        # Update state
        self.context.previous_state = current
        self.context.current_state = to_state
        self.context.updated_at = datetime.utcnow()

        logger.debug(
            f"{self.name}: Transitioned {current.value} -> {to_state.value} "
            f"(trigger: {trigger})"
        )

        return True

    @property
    def state(self) -> FSAState:
        """Get current state."""
        return self.context.current_state

    @property
    def is_ready(self) -> bool:
        """Check if FSA is ready for execution."""
        return self.context.current_state == FSAState.READY

    @property
    def is_executing(self) -> bool:
        """Check if FSA is currently executing."""
        return self.context.current_state == FSAState.EXECUTING

    @property
    def is_error(self) -> bool:
        """Check if FSA is in error state."""
        return self.context.current_state == FSAState.ERROR

    @property
    def is_completed(self) -> bool:
        """Check if FSA has completed."""
        return self.context.current_state == FSAState.COMPLETED

    def add_error(self, error: str) -> None:
        """
        Add an error to the context.

        Args:
            error: Error message
        """
        self.context.errors.append(error)
        logger.error(f"{self.name}: {error}")

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.context = FSAContext()
        logger.debug(f"{self.name}: Reset to initial state")

    def get_transition_history(self) -> List[Dict[str, Any]]:
        """
        Get transition history.

        Returns:
            List of transitions with details
        """
        return [
            {
                "from": t.from_state.value,
                "to": t.to_state.value,
                "trigger": t.trigger,
                "timestamp": t.timestamp.isoformat(),
                "metadata": t.metadata,
            }
            for t in self.context.transitions
        ]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert FSA state to dictionary.

        Returns:
            Dictionary representation of FSA state
        """
        return {
            "name": self.name,
            "id": self.context.id,
            "state": self.context.current_state.value,
            "previous_state": (
                self.context.previous_state.value
                if self.context.previous_state
                else None
            ),
            "errors": self.context.errors,
            "created_at": self.context.created_at.isoformat(),
            "updated_at": self.context.updated_at.isoformat(),
            "transition_count": len(self.context.transitions),
        }

    @abstractmethod
    def validate(self, *args, **kwargs) -> Any:
        """
        Validate input/configuration.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the main FSA logic.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def error_handling(self, exception: Exception, context: dict) -> Any:
        """
        Handle errors during execution.

        Must be implemented by subclasses.

        Args:
            exception: The exception that occurred
            context: Additional context about the error

        Returns:
            Recovery action or result
        """
        pass

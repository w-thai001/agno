"""Base FSA (Finite State Automaton) implementation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class State(str, Enum):
    """Base state enum for FSAs."""

    INITIAL = "initial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Transition:
    """Represents a state transition in an FSA."""

    from_state: State
    to_state: State
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    def can_transition(self, context: Dict[str, Any]) -> bool:
        """Check if transition can occur given the context."""
        if self.condition is None:
            return True
        return self.condition(context)

    def execute_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the transition action and return updated context."""
        if self.action is None:
            return context
        return self.action(context)


class FSA:
    """Base Finite State Automaton implementation."""

    def __init__(self, name: str, initial_state: State):
        self.name = name
        self.current_state = initial_state
        self.initial_state = initial_state
        self.transitions: Dict[State, List[Transition]] = OrderedDict()
        self.context: Dict[str, Any] = {}
        self.state_history: List[State] = [initial_state]

    def add_transition(self, transition: Transition) -> None:
        """Add a transition to the FSA."""
        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        self.transitions[transition.from_state].append(transition)
        logger.debug(
            f"Transition added: {transition.from_state} -> {transition.to_state}"
        )

    def register_transitions(self, transitions: List[Transition]) -> None:
        """Register multiple transitions."""
        for transition in transitions:
            self.add_transition(transition)

    def transition(self, to_state: Optional[State] = None) -> bool:
        """
        Attempt to transition to a new state.
        If to_state is None, find and execute the first valid transition.
        """
        if to_state is None:
            # Auto-transition: find first valid transition
            return self._auto_transition()

        # Explicit transition: find transition to specified state
        if self.current_state not in self.transitions:
            logger.warning(f"No transitions defined from state: {self.current_state}")
            return False

        for transition in self.transitions[self.current_state]:
            if transition.to_state == to_state and transition.can_transition(self.context):
                self._execute_transition(transition)
                return True

        logger.warning(
            f"No valid transition from {self.current_state} to {to_state}"
        )
        return False

    def _auto_transition(self) -> bool:
        """Find and execute the first valid transition from current state."""
        if self.current_state not in self.transitions:
            return False

        for transition in self.transitions[self.current_state]:
            if transition.can_transition(self.context):
                self._execute_transition(transition)
                return True

        return False

    def _execute_transition(self, transition: Transition) -> None:
        """Execute a transition."""
        logger.info(
            f"Transitioning: {transition.from_state} -> {transition.to_state}"
        )

        # Execute action and update context
        self.context = transition.execute_action(self.context)

        # Update state
        self.current_state = transition.to_state
        self.state_history.append(self.current_state)

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.current_state = self.initial_state
        self.context = {}
        self.state_history = [self.initial_state]
        logger.info(f"FSA '{self.name}' reset to initial state")

    def is_in_state(self, state: State) -> bool:
        """Check if FSA is in a specific state."""
        return self.current_state == state

    def get_valid_transitions(self) -> List[State]:
        """Get list of states that can be transitioned to from current state."""
        if self.current_state not in self.transitions:
            return []

        valid_states = []
        for transition in self.transitions[self.current_state]:
            if transition.can_transition(self.context):
                valid_states.append(transition.to_state)

        return valid_states

    def run(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the FSA until it reaches a terminal state or no transitions available.
        Returns the final context.
        """
        if context:
            self.context.update(context)

        logger.info(f"Starting FSA '{self.name}' from state: {self.current_state}")

        max_iterations = 100  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            if not self._auto_transition():
                # No more valid transitions
                break
            iteration += 1

        if iteration >= max_iterations:
            logger.warning(f"FSA '{self.name}' reached max iterations")

        logger.info(
            f"FSA '{self.name}' completed in state: {self.current_state} "
            f"after {iteration} transitions"
        )

        return self.context

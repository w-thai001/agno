"""Event Bus with Finite State Automaton for managing state transitions and event handling."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from agno.utils.log import logger


@dataclass
class Transition:
    """Represents a state transition with an event trigger."""
    from_state: str
    to_state: str
    event: str
    guard: Optional[Callable[[Any], bool]] = None
    action: Optional[Callable[[Any], None]] = None


@dataclass
class EventBusFSA:
    """Event Bus with Finite State Automaton for state management and event handling."""
    initial_state: str
    current_state: str = field(init=False)
    transitions: List[Transition] = field(default_factory=list)
    _subscribers: Dict[str, List[Callable]] = field(default_factory=dict, init=False, repr=False)
    _valid_states: Set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the FSA with the initial state."""
        self.current_state = self.initial_state
        self._valid_states = {self.initial_state}
        for t in self.transitions:
            self._valid_states.add(t.from_state)
            self._valid_states.add(t.to_state)

    def add_transition(
        self, from_state: str, to_state: str, event: str,
        guard: Optional[Callable[[Any], bool]] = None,
        action: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """Add a state transition to the FSA."""
        transition = Transition(from_state, to_state, event, guard, action)
        self.transitions.append(transition)
        self._valid_states.add(from_state)
        self._valid_states.add(to_state)

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe a callback to an event."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Unsubscribe a callback from an event."""
        if event in self._subscribers and callback in self._subscribers[event]:
            self._subscribers[event].remove(callback)

    def publish(self, event: str, data: Any = None) -> bool:
        """Publish an event and trigger state transitions if applicable."""
        logger.debug(f"Publishing event '{event}' in state '{self.current_state}'")
        # Find applicable transition
        for transition in self.transitions:
            if transition.from_state == self.current_state and transition.event == event:
                if transition.guard and not transition.guard(data):
                    continue
                if transition.action:
                    transition.action(data)
                old_state = self.current_state
                self.current_state = transition.to_state
                logger.info(f"State transition: {old_state} -> {self.current_state} (event: {event})")
                self._notify_subscribers(event, data)
                return True
        # No transition found, just notify subscribers
        self._notify_subscribers(event, data)
        return False

    def _notify_subscribers(self, event: str, data: Any) -> None:
        """Notify all subscribers of an event."""
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback for '{event}': {e}")

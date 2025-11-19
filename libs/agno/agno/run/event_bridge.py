"""Event Bridge FSA - Finite State Automaton for event-driven state management."""

from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass


@dataclass
class Transition:
    """State transition triggered by an event."""
    from_state: str
    event: str
    to_state: str
    guard: Optional[Callable[[Any], bool]] = None
    action: Optional[Callable[[Any], None]] = None


@dataclass
class State:
    """FSA state with lifecycle hooks."""
    name: str
    on_enter: Optional[Callable[[Any], None]] = None
    on_exit: Optional[Callable[[Any], None]] = None


class EventBridgeFSA:
    """Finite State Automaton for event-driven state management."""

    def __init__(self, initial_state: str):
        self.current_state = initial_state
        self.states: Dict[str, State] = {}
        self.transitions: Dict[str, list[Transition]] = {}
        self.handlers: Dict[str, list[Callable]] = {}
        self.context: Dict[str, Any] = {}

    def add_state(self, name: str, on_enter: Callable = None, on_exit: Callable = None):
        """Add a state with optional lifecycle hooks."""
        self.states[name] = State(name, on_enter, on_exit)
        return self

    def add_transition(self, from_state: str, event: str, to_state: str,
                      guard: Callable = None, action: Callable = None):
        """Add state transition with optional guard and action."""
        key = f"{from_state}:{event}"
        self.transitions.setdefault(key, []).append(
            Transition(from_state, event, to_state, guard, action))
        return self

    def on(self, event: str, handler: Callable):
        """Register event handler."""
        self.handlers.setdefault(event, []).append(handler)
        return self

    def dispatch(self, event: str, data: Any = None) -> bool:
        """Dispatch event and execute state transition."""
        for h in self.handlers.get(event, []):
            h(data)

        for t in self.transitions.get(f"{self.current_state}:{event}", []):
            if t.guard and not t.guard(data):
                continue

            # Exit current state
            if (state := self.states.get(self.current_state)) and state.on_exit:
                state.on_exit(data)

            # Execute transition action
            if t.action:
                t.action(data)

            # Enter new state
            self.current_state = t.to_state
            if (state := self.states.get(t.to_state)) and state.on_enter:
                state.on_enter(data)

            return True
        return False

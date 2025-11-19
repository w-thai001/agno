"""Message Broker Finite State Automaton for routing and delivering messages."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from agno.models.message import Message


class BrokerState(str, Enum):
    """States in the message broker FSA."""
    IDLE = "idle"
    RECEIVING = "receiving"
    ROUTING = "routing"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class MessageBrokerFSA:
    """Finite State Automaton for message brokering with pub/sub pattern."""

    state: BrokerState = BrokerState.IDLE
    subscribers: Dict[str, Set[Callable[[Message], Any]]] = field(default_factory=dict)
    error_message: Optional[str] = None

    TRANSITIONS = {
        BrokerState.IDLE: {BrokerState.RECEIVING, BrokerState.ERROR},
        BrokerState.RECEIVING: {BrokerState.ROUTING, BrokerState.ERROR},
        BrokerState.ROUTING: {BrokerState.DELIVERING, BrokerState.ERROR},
        BrokerState.DELIVERING: {BrokerState.COMPLETED, BrokerState.ERROR},
        BrokerState.COMPLETED: {BrokerState.IDLE},
        BrokerState.ERROR: {BrokerState.IDLE},
    }

    def transition(self, new_state: BrokerState) -> bool:
        """Attempt state transition with validation."""
        if new_state not in self.TRANSITIONS.get(self.state, set()):
            self.error_message = f"Invalid transition: {self.state} -> {new_state}"
            self.state = BrokerState.ERROR
            return False
        self.state = new_state
        return True

    def subscribe(self, topic: str, handler: Callable[[Message], Any]) -> None:
        """Subscribe a handler to a topic."""
        self.subscribers.setdefault(topic, set()).add(handler)

    def unsubscribe(self, topic: str, handler: Callable[[Message], Any]) -> None:
        """Unsubscribe a handler from a topic."""
        if topic in self.subscribers:
            self.subscribers[topic].discard(handler)

    def receive(self, message: Message) -> bool:
        """Receive a message and transition to RECEIVING state."""
        return self.transition(BrokerState.RECEIVING)

    def route(self, topic: str) -> List[Callable[[Message], Any]]:
        """Route to subscribers and transition to ROUTING state."""
        if not self.transition(BrokerState.ROUTING):
            return []
        return list(self.subscribers.get(topic, set()))

    def deliver(self, message: Message, handlers: List[Callable[[Message], Any]]) -> bool:
        """Deliver message to handlers and transition to DELIVERING state."""
        if not self.transition(BrokerState.DELIVERING):
            return False
        try:
            for handler in handlers:
                handler(message)
            return self.transition(BrokerState.COMPLETED)
        except Exception as e:
            self.error_message = f"Delivery failed: {str(e)}"
            self.transition(BrokerState.ERROR)
            return False

    def process(self, message: Message, topic: str) -> bool:
        """Process a message through the complete FSA workflow."""
        if not self.receive(message):
            return False
        handlers = self.route(topic)
        if not self.deliver(message, handlers):
            return False
        self.transition(BrokerState.IDLE)
        return True

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.state = BrokerState.IDLE
        self.error_message = None

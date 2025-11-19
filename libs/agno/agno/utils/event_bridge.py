"""Event Bridge FSA for routing and managing events."""
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class BridgeState(Enum):
    """FSA States for event bridge."""
    IDLE, READY, PROCESSING, DISPATCHING = "idle", "ready", "processing", "dispatching"


class EventBridge:
    """Finite State Automaton for event routing and management."""

    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: List[Dict[str, Any]] = []
        self.state = BridgeState.IDLE

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to an event type."""
        self.handlers[event_type].append(handler)
        self.state = BridgeState.READY

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Unsubscribe a handler from an event type."""
        if event_type in self.handlers and handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            if not self.handlers[event_type]:
                del self.handlers[event_type]
            self.state = BridgeState.READY if self.handlers else BridgeState.IDLE
            return True
        return False

    def publish(self, event_type: str, data: Any = None, sync: bool = True) -> List[Any]:
        """Publish an event to all subscribers."""
        if self.state == BridgeState.IDLE:
            return []
        event = {"type": event_type, "data": data}
        if sync:
            return self._dispatch(event)
        else:
            self.event_queue.append(event)
            return []

    def _dispatch(self, event: Dict[str, Any]) -> List[Any]:
        """Dispatch event to registered handlers."""
        self.state = BridgeState.DISPATCHING
        event_type = event["type"]
        results = []
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                self.state = BridgeState.PROCESSING
                try:
                    result = handler(event["data"])
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        self.state = BridgeState.READY
        return results

    def process_queue(self) -> int:
        """Process all queued events."""
        processed = 0
        while self.event_queue:
            event = self.event_queue.pop(0)
            self._dispatch(event)
            processed += 1
        return processed

    def clear_handlers(self, event_type: Optional[str] = None) -> None:
        """Clear handlers for specific event type or all."""
        if event_type:
            self.handlers.pop(event_type, None)
        else:
            self.handlers.clear()
        self.state = BridgeState.IDLE if not self.handlers else BridgeState.READY

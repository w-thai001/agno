"""
FSA Event Bus

Event-driven communication between FSAs:
- Pub/sub messaging pattern
- Event routing and filtering
- Async event handling
- Event history and replay
- Topic-based subscriptions
- Event priority and ordering
- Dead letter queue

Enables decoupled, scalable FSA communication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict, deque
import uuid

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class EventPriority(int, Enum):
    """Event priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Event(BaseModel):
    """Event message"""
    event_id: str
    topic: str
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    timestamp: str
    source: str
    metadata: Dict[str, Any] = {}


class Subscription(BaseModel):
    """Event subscription"""
    subscription_id: str
    topic_pattern: str  # Supports wildcards
    handler: Any  # Callback function (not serializable)
    fsa_id: Optional[str] = None
    filter_condition: Optional[str] = None
    active: bool = True


class EventBusState(str, Enum):
    """States for Event Bus FSA"""
    INITIAL = "initial"
    RECEIVING = "receiving"
    ROUTING = "routing"
    DELIVERING = "delivering"
    RECORDING = "recording"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FSAEventBus(FSA):
    """
    FSA Event Bus

    Provides pub/sub messaging for decoupled FSA communication:
    - Publish events to topics
    - Subscribe to topics with pattern matching
    - Route events to subscribers
    - Maintain event history
    - Support event replay
    - Dead letter queue for failed deliveries

    Example:
        ```python
        # Create event bus
        event_bus = FSAEventBus(name="EventBus")

        # Subscribe to events
        def on_task_complete(event):
            print(f"Task completed: {event.payload}")

        event_bus.subscribe(
            topic="task.completed",
            handler=on_task_complete
        )

        # Publish event
        event_bus.publish(
            topic="task.completed",
            payload={"task_id": "123", "result": "success"}
        )

        # Subscribe with pattern
        event_bus.subscribe(
            topic="task.*",  # Matches task.started, task.completed, etc.
            handler=on_any_task_event
        )
        ```
    """

    # Subscriptions
    subscriptions: Dict[str, Subscription] = field(default_factory=dict)
    next_subscription_id: int = 1

    # Event history
    event_history: deque = field(default_factory=lambda: deque(maxlen=1000))

    # Dead letter queue
    dead_letter_queue: List[Event] = field(default_factory=list)

    # Pending events (for async delivery)
    pending_events: deque = field(default_factory=deque)

    # Statistics
    total_events_published: int = 0
    total_events_delivered: int = 0
    total_delivery_failures: int = 0

    # Configuration
    enable_history: bool = True
    enable_dead_letter_queue: bool = True
    max_delivery_retries: int = 3

    def __post_init__(self):
        """Initialize event bus"""
        self.initial_state = EventBusState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {EventBusState.SUCCESS, EventBusState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAEventBus {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup event bus workflow"""
        # INITIAL -> RECEIVING
        self.add_transition(
            EventBusState.INITIAL,
            EventBusState.RECEIVING,
            action=self._receive_event,
            description="Receive event"
        )

        # RECEIVING -> ROUTING
        self.add_transition(
            EventBusState.RECEIVING,
            EventBusState.ROUTING,
            condition=lambda ctx: ctx.get("event_received", False),
            action=self._route_event,
            description="Route event to subscribers"
        )

        # ROUTING -> DELIVERING
        self.add_transition(
            EventBusState.ROUTING,
            EventBusState.DELIVERING,
            condition=lambda ctx: ctx.get("subscribers_found", False),
            action=self._deliver_event,
            description="Deliver event to subscribers"
        )

        # ROUTING -> RECORDING (no subscribers)
        self.add_transition(
            EventBusState.ROUTING,
            EventBusState.RECORDING,
            condition=lambda ctx: not ctx.get("subscribers_found", False),
            action=self._record_undelivered,
            description="Record undelivered event"
        )

        # DELIVERING -> RECORDING
        self.add_transition(
            EventBusState.DELIVERING,
            EventBusState.RECORDING,
            condition=lambda ctx: ctx.get("delivery_complete", False),
            action=self._record_event,
            description="Record event in history"
        )

        # RECORDING -> SUCCESS
        self.add_transition(
            EventBusState.RECORDING,
            EventBusState.SUCCESS,
            condition=lambda ctx: ctx.get("recording_complete", False),
            description="Event processed"
        )

        # Error handling
        for state in EventBusState:
            if state not in [EventBusState.SUCCESS, EventBusState.FAILED]:
                self.add_transition(
                    state,
                    EventBusState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _receive_event(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Receive and validate event"""
        event = context.get("event")

        if not event:
            context["critical_error"] = True
            raise ValueError("No event provided")

        self.total_events_published += 1

        context["event_received"] = True

        if self.debug_mode:
            logger.debug(f"Event received: {event.topic}")

        return context

    def _route_event(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route event to matching subscribers"""
        event = context["event"]

        # Find matching subscribers
        matching_subs = []

        for sub in self.subscriptions.values():
            if not sub.active:
                continue

            # Check topic pattern match
            if self._topic_matches(event.topic, sub.topic_pattern):
                # Check filter condition if present
                if sub.filter_condition:
                    try:
                        # Evaluate filter
                        payload = event.payload
                        if eval(sub.filter_condition):
                            matching_subs.append(sub)
                    except Exception as e:
                        if self.debug_mode:
                            logger.warning(f"Filter evaluation failed: {e}")
                else:
                    matching_subs.append(sub)

        context["matching_subscribers"] = matching_subs
        context["subscribers_found"] = len(matching_subs) > 0

        if self.debug_mode:
            logger.debug(f"Found {len(matching_subs)} matching subscribers for {event.topic}")

        return context

    def _deliver_event(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deliver event to subscribers"""
        event = context["event"]
        subscribers = context["matching_subscribers"]

        delivered = 0
        failed = 0

        for sub in subscribers:
            try:
                # Call handler
                if sub.handler:
                    sub.handler(event)
                    delivered += 1
                    self.total_events_delivered += 1

                    if self.debug_mode:
                        logger.debug(f"Event delivered to subscription: {sub.subscription_id}")

            except Exception as e:
                failed += 1
                self.total_delivery_failures += 1

                if self.debug_mode:
                    logger.error(f"Event delivery failed: {e}")

                # Add to dead letter queue
                if self.enable_dead_letter_queue:
                    self.dead_letter_queue.append(event)

        context["delivered_count"] = delivered
        context["failed_count"] = failed
        context["delivery_complete"] = True

        return context

    def _record_event(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record event in history"""
        if self.enable_history:
            event = context["event"]
            self.event_history.append(event)

        context["recording_complete"] = True

        return context

    def _record_undelivered(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Record event with no subscribers"""
        if self.debug_mode:
            event = context["event"]
            logger.warning(f"No subscribers for event: {event.topic}")

        # Still record in history
        if self.enable_history:
            event = context["event"]
            self.event_history.append(event)

        context["recording_complete"] = True

        return context

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports wildcards)"""
        # Simple wildcard matching
        # * matches any single segment
        # ** or # matches multiple segments

        if pattern == topic:
            return True

        if "*" not in pattern and "#" not in pattern:
            return False

        # Convert to regex-like matching
        topic_parts = topic.split(".")
        pattern_parts = pattern.split(".")

        if "#" in pattern or "**" in pattern:
            # Multi-segment wildcard
            for i, part in enumerate(pattern_parts):
                if part in ["#", "**"]:
                    return True  # Matches everything from this point

        # Single-segment wildcard
        if len(topic_parts) != len(pattern_parts):
            return False

        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != "*" and pattern_part != topic_part:
                return False

        return True

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish event to topic

        Args:
            topic: Event topic
            payload: Event data
            priority: Event priority
            source: Event source identifier
            metadata: Additional metadata

        Returns:
            Event ID
        """
        # Create event
        event = Event(
            event_id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            priority=priority,
            timestamp=datetime.now().isoformat(),
            source=source,
            metadata=metadata or {}
        )

        # Reset and process event
        self.reset()

        result = self.run({"event": event})

        if self.debug_mode:
            logger.info(f"Event published: {topic} ({event.event_id})")

        return event.event_id

    def subscribe(
        self,
        topic: str,
        handler: Callable[[Event], None],
        fsa_id: Optional[str] = None,
        filter_condition: Optional[str] = None
    ) -> str:
        """
        Subscribe to topic

        Args:
            topic: Topic pattern (supports wildcards: *, #)
            handler: Callback function
            fsa_id: Optional FSA identifier
            filter_condition: Optional filter expression

        Returns:
            Subscription ID
        """
        sub_id = f"sub-{self.next_subscription_id}"
        self.next_subscription_id += 1

        subscription = Subscription(
            subscription_id=sub_id,
            topic_pattern=topic,
            handler=handler,
            fsa_id=fsa_id,
            filter_condition=filter_condition,
            active=True
        )

        self.subscriptions[sub_id] = subscription

        if self.debug_mode:
            logger.info(f"Subscription created: {sub_id} for topic {topic}")

        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from topic"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]

            if self.debug_mode:
                logger.info(f"Subscription removed: {subscription_id}")

            return True

        return False

    def pause_subscription(self, subscription_id: str) -> bool:
        """Pause subscription"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = False
            return True
        return False

    def resume_subscription(self, subscription_id: str) -> bool:
        """Resume subscription"""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = True
            return True
        return False

    def get_subscriptions(self, topic: Optional[str] = None) -> List[Subscription]:
        """Get subscriptions, optionally filtered by topic"""
        if topic:
            return [
                sub for sub in self.subscriptions.values()
                if self._topic_matches(topic, sub.topic_pattern)
            ]
        return list(self.subscriptions.values())

    def get_event_history(
        self,
        topic: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get event history, optionally filtered"""
        events = list(self.event_history)

        if topic:
            events = [e for e in events if e.topic == topic]

        if limit:
            events = events[-limit:]

        return events

    def replay_events(
        self,
        topic: Optional[str] = None,
        from_time: Optional[str] = None
    ) -> int:
        """
        Replay historical events

        Args:
            topic: Optional topic filter
            from_time: Optional start time (ISO format)

        Returns:
            Number of events replayed
        """
        events = self.get_event_history(topic=topic)

        if from_time:
            events = [
                e for e in events
                if e.timestamp >= from_time
            ]

        replayed = 0

        for event in events:
            # Re-publish event
            self.reset()
            self.run({"event": event})
            replayed += 1

        if self.debug_mode:
            logger.info(f"Replayed {replayed} events")

        return replayed

    def get_dead_letter_queue(self) -> List[Event]:
        """Get dead letter queue"""
        return self.dead_letter_queue

    def clear_dead_letter_queue(self) -> int:
        """Clear dead letter queue"""
        count = len(self.dead_letter_queue)
        self.dead_letter_queue.clear()
        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "total_events_published": self.total_events_published,
            "total_events_delivered": self.total_events_delivered,
            "total_delivery_failures": self.total_delivery_failures,
            "active_subscriptions": sum(1 for s in self.subscriptions.values() if s.active),
            "total_subscriptions": len(self.subscriptions),
            "event_history_size": len(self.event_history),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "delivery_success_rate": (
                self.total_events_delivered / max(self.total_events_published, 1) * 100
            )
        }

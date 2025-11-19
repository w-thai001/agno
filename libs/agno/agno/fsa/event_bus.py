"""Event Bus FSA for publish-subscribe event handling in agno framework."""

from __future__ import annotations

import asyncio
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional, Pattern, Union
from uuid import uuid4

from agno.utils.log import logger


@dataclass
class Event:
    """Event data structure for the event bus."""

    topic: str
    data: Any = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "topic": self.topic,
            "data": self.data,
            "event_id": self.event_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """Create event from dictionary."""
        return cls(
            topic=data.get("topic", ""),
            data=data.get("data"),
            event_id=data.get("event_id", str(uuid4())),
            metadata=data.get("metadata", {}),
        )


class EventBus:
    """
    Event Bus implementation with publish-subscribe pattern.

    Features:
    - Subscribe/unsubscribe to topics
    - Topic pattern matching (wildcards)
    - Async event handlers
    - Event history (last 100 events)
    """

    def __init__(self, name: Optional[str] = None, history_size: int = 100):
        """
        Initialize EventBus.

        Args:
            name: Optional name for the event bus
            history_size: Maximum number of events to keep in history (default: 100)
        """
        self.name = name or "EventBus"
        self.history_size = history_size
        self._subscribers: Dict[str, List[Callable]] = {}
        self._pattern_subscribers: Dict[Pattern, List[Callable]] = {}
        self._history: Deque[Event] = deque(maxlen=history_size)

    def subscribe(self, topic: Union[str, Pattern], handler: Callable) -> str:
        """
        Subscribe to a topic or pattern.

        Args:
            topic: Topic string or regex pattern to subscribe to
            handler: Callback function (can be sync or async)

        Returns:
            Subscription ID for unsubscribing

        Examples:
            # Exact topic match
            bus.subscribe("user.created", handler)

            # Pattern matching
            bus.subscribe(re.compile(r"user\\..*"), handler)
        """
        subscription_id = str(uuid4())

        if isinstance(topic, Pattern):
            if topic not in self._pattern_subscribers:
                self._pattern_subscribers[topic] = []
            self._pattern_subscribers[topic].append(handler)
            logger.debug(f"Subscribed to pattern {topic.pattern} with handler {handler.__name__}")
        else:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)
            logger.debug(f"Subscribed to topic '{topic}' with handler {handler.__name__}")

        return subscription_id

    def unsubscribe(self, topic: Union[str, Pattern], handler: Callable) -> bool:
        """
        Unsubscribe a handler from a topic or pattern.

        Args:
            topic: Topic string or regex pattern
            handler: Callback function to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        if isinstance(topic, Pattern):
            if topic in self._pattern_subscribers:
                try:
                    self._pattern_subscribers[topic].remove(handler)
                    if not self._pattern_subscribers[topic]:
                        del self._pattern_subscribers[topic]
                    logger.debug(f"Unsubscribed from pattern {topic.pattern}")
                    return True
                except ValueError:
                    return False
        else:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(handler)
                    if not self._subscribers[topic]:
                        del self._subscribers[topic]
                    logger.debug(f"Unsubscribed from topic '{topic}'")
                    return True
                except ValueError:
                    return False
        return False

    async def publish(self, topic: str, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Event:
        """
        Publish an event to all subscribers.

        Args:
            topic: Event topic
            data: Event payload
            metadata: Optional event metadata

        Returns:
            The published Event object
        """
        event = Event(topic=topic, data=data, metadata=metadata or {})

        # Add to history
        self._history.append(event)

        # Collect all matching handlers
        handlers: List[Callable] = []

        # Exact topic matches
        if topic in self._subscribers:
            handlers.extend(self._subscribers[topic])

        # Pattern matches
        for pattern, pattern_handlers in self._pattern_subscribers.items():
            if pattern.match(topic):
                handlers.extend(pattern_handlers)

        logger.debug(f"Publishing event to topic '{topic}' with {len(handlers)} handlers")

        # Execute handlers (both sync and async)
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__} for topic '{topic}': {e}")

        return event

    def publish_sync(self, topic: str, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> Event:
        """
        Synchronous version of publish for non-async contexts.

        Args:
            topic: Event topic
            data: Event payload
            metadata: Optional event metadata

        Returns:
            The published Event object
        """
        event = Event(topic=topic, data=data, metadata=metadata or {})

        # Add to history
        self._history.append(event)

        # Collect all matching handlers
        handlers: List[Callable] = []

        # Exact topic matches
        if topic in self._subscribers:
            handlers.extend(self._subscribers[topic])

        # Pattern matches
        for pattern, pattern_handlers in self._pattern_subscribers.items():
            if pattern.match(topic):
                handlers.extend(pattern_handlers)

        logger.debug(f"Publishing event (sync) to topic '{topic}' with {len(handlers)} handlers")

        # Execute only sync handlers
        for handler in handlers:
            try:
                if not asyncio.iscoroutinefunction(handler):
                    handler(event)
                else:
                    logger.warning(f"Skipping async handler {handler.__name__} in sync publish")
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__} for topic '{topic}': {e}")

        return event

    def get_history(self, topic: Optional[str] = None, limit: Optional[int] = None) -> List[Event]:
        """
        Get event history.

        Args:
            topic: Optional topic filter
            limit: Optional limit on number of events to return

        Returns:
            List of events (most recent first)
        """
        events = list(self._history)
        events.reverse()  # Most recent first

        if topic:
            events = [e for e in events if e.topic == topic]

        if limit:
            events = events[:limit]

        return events

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()
        logger.debug("Event history cleared")

    def get_subscriber_count(self, topic: Optional[str] = None) -> int:
        """
        Get count of subscribers.

        Args:
            topic: Optional topic to count subscribers for

        Returns:
            Number of subscribers
        """
        if topic:
            return len(self._subscribers.get(topic, []))
        else:
            total = sum(len(handlers) for handlers in self._subscribers.values())
            total += sum(len(handlers) for handlers in self._pattern_subscribers.values())
            return total

    def clear_subscribers(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()
        self._pattern_subscribers.clear()
        logger.debug("All subscribers cleared")

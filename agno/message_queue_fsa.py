"""Message Queue Finite State Automaton for message queuing and processing."""

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for message queue."""
    IDLE = "idle"
    ENQUEUING = "enqueuing"
    DEQUEUING = "dequeuing"
    PROCESSING = "processing"


class Priority(Enum):
    """Message priority levels."""
    HIGH = 0
    MEDIUM = 1
    LOW = 2


@dataclass
class Message:
    """Represents a queue message."""
    message_id: str
    data: Any
    priority: Priority
    consumer_group: str
    timestamp: float = field(default_factory=time.time)
    persist: bool = False
    retry_count: int = 0


class MessageQueueFSA:
    """Finite State Automaton for message queue management."""

    def __init__(self, persist_messages: bool = False):
        self.state = State.IDLE
        self.persist_messages = persist_messages
        self._queues: Dict[Priority, deque] = {
            Priority.HIGH: deque(),
            Priority.MEDIUM: deque(),
            Priority.LOW: deque()
        }
        self._consumer_groups: Dict[str, List[Message]] = {}
        self._persisted: Dict[str, Message] = {}
        self._lock = threading.Lock()
        logger.info(f"Message queue initialized (persist: {persist_messages})")

    def enqueue(
        self,
        data: Any,
        priority: Priority = Priority.MEDIUM,
        consumer_group: str = "default",
        persist: Optional[bool] = None
    ) -> str:
        """Enqueue a message."""
        with self._lock:
            self._transition(self.state, State.ENQUEUING)

            message_id = str(uuid.uuid4())
            persist = persist if persist is not None else self.persist_messages

            message = Message(
                message_id=message_id,
                data=data,
                priority=priority,
                consumer_group=consumer_group,
                persist=persist
            )

            self._queues[priority].append(message)

            if persist:
                self._persisted[message_id] = message

            logger.debug(
                f"Enqueued message {message_id} "
                f"(priority: {priority.name}, group: {consumer_group})"
            )

            self._transition(State.ENQUEUING, State.IDLE)
            return message_id

    def dequeue(self, consumer_group: str = "default") -> Optional[Message]:
        """Dequeue next message for consumer group."""
        with self._lock:
            self._transition(self.state, State.DEQUEUING)

            # Check priorities in order: HIGH, MEDIUM, LOW
            for priority in [Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
                queue = self._queues[priority]

                # Find first message for this consumer group
                for i, message in enumerate(queue):
                    if message.consumer_group == consumer_group:
                        message = queue[i]
                        del queue[i]

                        # Track in consumer group
                        if consumer_group not in self._consumer_groups:
                            self._consumer_groups[consumer_group] = []
                        self._consumer_groups[consumer_group].append(message)

                        logger.debug(
                            f"Dequeued message {message.message_id} "
                            f"(priority: {priority.name}, group: {consumer_group})"
                        )

                        self._transition(State.DEQUEUING, State.PROCESSING)
                        return message

            self._transition(State.DEQUEUING, State.IDLE)
            return None

    def acknowledge(self, message_id: str, consumer_group: str = "default") -> bool:
        """Acknowledge message processing completion."""
        with self._lock:
            if consumer_group not in self._consumer_groups:
                return False

            messages = self._consumer_groups[consumer_group]
            for i, msg in enumerate(messages):
                if msg.message_id == message_id:
                    del messages[i]
                    if not msg.persist:
                        self._persisted.pop(message_id, None)
                    logger.debug(f"Acknowledged message {message_id}")
                    self._transition(State.PROCESSING, State.IDLE)
                    return True

            return False

    def requeue(self, message_id: str, consumer_group: str = "default") -> bool:
        """Requeue message for retry."""
        with self._lock:
            if consumer_group not in self._consumer_groups:
                return False

            messages = self._consumer_groups[consumer_group]
            for i, msg in enumerate(messages):
                if msg.message_id == message_id:
                    del messages[i]
                    msg.retry_count += 1
                    self._queues[msg.priority].append(msg)
                    logger.info(f"Requeued message {message_id} (retry: {msg.retry_count})")
                    return True

            return False

    def get_queue_size(self, priority: Optional[Priority] = None) -> int:
        """Get queue size for specific priority or total."""
        with self._lock:
            if priority:
                return len(self._queues[priority])
            else:
                return sum(len(q) for q in self._queues.values())

    def get_consumer_group_size(self, consumer_group: str) -> int:
        """Get number of messages being processed by consumer group."""
        with self._lock:
            return len(self._consumer_groups.get(consumer_group, []))

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                "state": self.state.value,
                "total_queued": self.get_queue_size(),
                "high_priority": len(self._queues[Priority.HIGH]),
                "medium_priority": len(self._queues[Priority.MEDIUM]),
                "low_priority": len(self._queues[Priority.LOW]),
                "consumer_groups": {
                    group: len(messages)
                    for group, messages in self._consumer_groups.items()
                },
                "persisted_messages": len(self._persisted),
                "persist_enabled": self.persist_messages
            }

    def clear(self, priority: Optional[Priority] = None):
        """Clear queue messages."""
        with self._lock:
            if priority:
                self._queues[priority].clear()
                logger.info(f"Cleared {priority.name} priority queue")
            else:
                for queue in self._queues.values():
                    queue.clear()
                self._consumer_groups.clear()
                if not self.persist_messages:
                    self._persisted.clear()
                logger.info("Cleared all queues")

            self._transition(self.state, State.IDLE)

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state

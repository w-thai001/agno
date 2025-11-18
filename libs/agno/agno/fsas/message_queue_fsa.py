"""
Message Queue FSA: Reliable message queuing infrastructure for inter-process communication.

This module provides a comprehensive message queue implementation with support for:
- Multiple queue types (FIFO, LIFO, Priority)
- Message persistence and durability
- Delivery acknowledgment system
- Dead letter queues for failed messages
- Exchange-based message routing
- Queue monitoring and metrics
- Auto-scaling queue workers
- Thread-safe operations
"""

from __future__ import annotations

import json
import queue
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class QueueType(Enum):
    """Supported queue types."""
    FIFO = "fifo"  # First In First Out
    LIFO = "lifo"  # Last In First Out
    PRIORITY = "priority"  # Priority-based ordering


class ExchangeType(Enum):
    """Message exchange patterns."""
    DIRECT = "direct"  # Direct routing by routing key
    TOPIC = "topic"  # Pattern-based routing
    FANOUT = "fanout"  # Broadcast to all queues


class MessageState(Enum):
    """Message processing states."""
    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    DEAD_LETTER = "dead_letter"


class DeliveryMode(Enum):
    """Message delivery guarantees."""
    AT_MOST_ONCE = "at_most_once"  # Fire and forget
    AT_LEAST_ONCE = "at_least_once"  # May deliver multiple times
    EXACTLY_ONCE = "exactly_once"  # Guaranteed single delivery


# ==================== Data Classes ====================

@dataclass
class Message:
    """Represents a message in the queue system."""
    message_id: str = field(default_factory=lambda: str(uuid4()))
    payload: Any = None
    routing_key: str = ""
    priority: int = 0  # Higher values = higher priority
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    headers: Dict[str, Any] = field(default_factory=dict)
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    state: MessageState = MessageState.PENDING
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "payload": self.payload,
            "routing_key": self.routing_key,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "headers": self.headers,
            "delivery_mode": self.delivery_mode.value,
            "state": self.state.value,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """Create message from dictionary."""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["delivery_mode"] = DeliveryMode(data["delivery_mode"])
        data["state"] = MessageState(data["state"])
        return cls(**data)


@dataclass
class QueueConfig:
    """Configuration for a message queue."""
    max_size: int = 10000
    persistent: bool = True
    ttl: Optional[timedelta] = None  # Time to live for messages
    dead_letter_queue: Optional[str] = None
    consumer_timeout: timedelta = timedelta(seconds=30)
    enable_deduplication: bool = False
    deduplication_window: timedelta = timedelta(minutes=5)


@dataclass
class QueueMetrics:
    """Metrics for queue monitoring."""
    queue_name: str
    queue_type: QueueType
    total_messages: int = 0
    pending_messages: int = 0
    in_flight_messages: int = 0
    acknowledged_messages: int = 0
    rejected_messages: int = 0
    dead_letter_messages: int = 0
    avg_processing_time: float = 0.0
    throughput: float = 0.0  # Messages per second
    oldest_message_age: Optional[timedelta] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "queue_name": self.queue_name,
            "queue_type": self.queue_type.value,
            "total_messages": self.total_messages,
            "pending_messages": self.pending_messages,
            "in_flight_messages": self.in_flight_messages,
            "acknowledged_messages": self.acknowledged_messages,
            "rejected_messages": self.rejected_messages,
            "dead_letter_messages": self.dead_letter_messages,
            "avg_processing_time": self.avg_processing_time,
            "throughput": self.throughput,
            "oldest_message_age": str(self.oldest_message_age) if self.oldest_message_age else None,
        }


@dataclass
class ValidationResult:
    """Result of message validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class EnqueueResult:
    """Result of enqueue operation."""
    success: bool
    message_id: str
    queue_name: str
    error: Optional[str] = None


@dataclass
class DequeueResult:
    """Result of dequeue operation."""
    success: bool
    messages: List[Message] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class AckResult:
    """Result of acknowledgment operation."""
    success: bool
    message_id: str
    error: Optional[str] = None


@dataclass
class RejectResult:
    """Result of reject operation."""
    success: bool
    message_id: str
    requeued: bool = False
    error: Optional[str] = None


@dataclass
class RoutingResult:
    """Result of message routing."""
    success: bool
    queues_routed: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class BatchResult:
    """Result of batch processing."""
    success: bool
    processed_count: int = 0
    failed_count: int = 0
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (message_id, error)


@dataclass
class PersistenceResult:
    """Result of persistence operation."""
    success: bool
    message_id: str
    error: Optional[str] = None


@dataclass
class DeadLetterResult:
    """Result of dead letter queue operation."""
    success: bool
    message_id: str
    dead_letter_queue: str
    error: Optional[str] = None


@dataclass
class ScalingResult:
    """Result of worker scaling operation."""
    success: bool
    queue_name: str
    previous_workers: int = 0
    new_workers: int = 0
    error: Optional[str] = None


@dataclass
class QueueProcessingResult:
    """Result of queue processing pipeline."""
    success: bool
    processed_messages: int = 0
    failed_messages: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class DeleteResult:
    """Result of queue deletion."""
    success: bool
    queue_name: str
    messages_purged: int = 0
    error: Optional[str] = None


@dataclass
class PurgeResult:
    """Result of queue purge operation."""
    success: bool
    queue_name: str
    messages_purged: int = 0
    error: Optional[str] = None


# ==================== Queue Implementations ====================

class BaseQueue(ABC):
    """Abstract base class for queue implementations."""

    def __init__(self, name: str, config: QueueConfig):
        self.name = name
        self.config = config
        self.lock = threading.RLock()
        self._message_store: Dict[str, Message] = {}
        self._deduplication_cache: Set[str] = set()
        self._cache_timestamps: Dict[str, datetime] = {}

    @abstractmethod
    def put(self, message: Message) -> bool:
        """Add message to queue."""
        pass

    @abstractmethod
    def get(self, batch_size: int = 1) -> List[Message]:
        """Retrieve messages from queue."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current queue size."""
        pass

    def _check_deduplication(self, message: Message) -> bool:
        """Check if message is duplicate within deduplication window."""
        if not self.config.enable_deduplication:
            return False

        # Clean old entries
        now = datetime.utcnow()
        to_remove = []
        for msg_id, timestamp in self._cache_timestamps.items():
            if now - timestamp > self.config.deduplication_window:
                to_remove.append(msg_id)

        for msg_id in to_remove:
            self._deduplication_cache.discard(msg_id)
            self._cache_timestamps.pop(msg_id, None)

        # Check for duplicate
        if message.message_id in self._deduplication_cache:
            return True

        self._deduplication_cache.add(message.message_id)
        self._cache_timestamps[message.message_id] = now
        return False


class FIFOQueue(BaseQueue):
    """First-In-First-Out queue implementation."""

    def __init__(self, name: str, config: QueueConfig):
        super().__init__(name, config)
        self._queue: queue.Queue = queue.Queue(maxsize=config.max_size)

    def put(self, message: Message) -> bool:
        """Add message to FIFO queue."""
        with self.lock:
            if self._check_deduplication(message):
                logger.debug(f"Duplicate message {message.message_id} ignored")
                return False

            try:
                self._queue.put_nowait(message)
                self._message_store[message.message_id] = message
                return True
            except queue.Full:
                logger.warning(f"Queue {self.name} is full")
                return False

    def get(self, batch_size: int = 1) -> List[Message]:
        """Retrieve messages from FIFO queue."""
        messages = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    msg = self._queue.get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break
        return messages

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


class LIFOQueue(BaseQueue):
    """Last-In-First-Out queue implementation."""

    def __init__(self, name: str, config: QueueConfig):
        super().__init__(name, config)
        self._queue: queue.LifoQueue = queue.LifoQueue(maxsize=config.max_size)

    def put(self, message: Message) -> bool:
        """Add message to LIFO queue."""
        with self.lock:
            if self._check_deduplication(message):
                logger.debug(f"Duplicate message {message.message_id} ignored")
                return False

            try:
                self._queue.put_nowait(message)
                self._message_store[message.message_id] = message
                return True
            except queue.Full:
                logger.warning(f"Queue {self.name} is full")
                return False

    def get(self, batch_size: int = 1) -> List[Message]:
        """Retrieve messages from LIFO queue."""
        messages = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    msg = self._queue.get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break
        return messages

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


class PriorityQueue(BaseQueue):
    """Priority-based queue implementation."""

    def __init__(self, name: str, config: QueueConfig):
        super().__init__(name, config)
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=config.max_size)
        self._counter = 0  # For stable sorting

    def put(self, message: Message) -> bool:
        """Add message to priority queue."""
        with self.lock:
            if self._check_deduplication(message):
                logger.debug(f"Duplicate message {message.message_id} ignored")
                return False

            try:
                # Higher priority first, use counter for stable ordering
                priority_tuple = (-message.priority, self._counter, message)
                self._queue.put_nowait(priority_tuple)
                self._counter += 1
                self._message_store[message.message_id] = message
                return True
            except queue.Full:
                logger.warning(f"Queue {self.name} is full")
                return False

    def get(self, batch_size: int = 1) -> List[Message]:
        """Retrieve messages from priority queue."""
        messages = []
        with self.lock:
            for _ in range(batch_size):
                try:
                    _, _, msg = self._queue.get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break
        return messages

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


# ==================== Exchange Implementation ====================

class Exchange:
    """Message exchange for routing."""

    def __init__(self, name: str, exchange_type: ExchangeType):
        self.name = name
        self.exchange_type = exchange_type
        self.bindings: Dict[str, List[str]] = defaultdict(list)  # routing_key -> queue_names
        self.lock = threading.RLock()

    def bind(self, queue_name: str, routing_key: str) -> None:
        """Bind queue to routing key."""
        with self.lock:
            if queue_name not in self.bindings[routing_key]:
                self.bindings[routing_key].append(queue_name)

    def unbind(self, queue_name: str, routing_key: str) -> None:
        """Unbind queue from routing key."""
        with self.lock:
            if queue_name in self.bindings[routing_key]:
                self.bindings[routing_key].remove(queue_name)

    def route(self, routing_key: str) -> List[str]:
        """Determine which queues should receive the message."""
        with self.lock:
            if self.exchange_type == ExchangeType.DIRECT:
                return self.bindings.get(routing_key, [])

            elif self.exchange_type == ExchangeType.FANOUT:
                # Broadcast to all bound queues
                all_queues = set()
                for queues in self.bindings.values():
                    all_queues.update(queues)
                return list(all_queues)

            elif self.exchange_type == ExchangeType.TOPIC:
                # Pattern matching (simplified)
                matched_queues = set()
                for pattern, queues in self.bindings.items():
                    if self._match_topic(routing_key, pattern):
                        matched_queues.update(queues)
                return list(matched_queues)

        return []

    def _match_topic(self, routing_key: str, pattern: str) -> bool:
        """Match routing key against topic pattern."""
        # Simplified topic matching: * matches one word, # matches zero or more words
        key_parts = routing_key.split('.')
        pattern_parts = pattern.split('.')

        if '#' not in pattern and len(key_parts) != len(pattern_parts):
            return False

        i = j = 0
        while i < len(pattern_parts) and j < len(key_parts):
            if pattern_parts[i] == '#':
                if i == len(pattern_parts) - 1:
                    return True
                i += 1
                while j < len(key_parts) and key_parts[j] != pattern_parts[i]:
                    j += 1
            elif pattern_parts[i] == '*' or pattern_parts[i] == key_parts[j]:
                i += 1
                j += 1
            else:
                return False

        return i == len(pattern_parts) and j == len(key_parts)


# ==================== Main FSA Class ====================

class MessageQueueFSA:
    """
    Message Queue Finite State Automaton.

    Provides reliable message queuing infrastructure with support for multiple
    queue types, persistence, delivery guarantees, and routing.
    """

    def __init__(
        self,
        name: str = "MessageQueueFSA",
        persistence_path: Optional[Path] = None,
    ):
        """
        Initialize Message Queue FSA.

        Args:
            name: Name of the FSA instance
            persistence_path: Path for message persistence storage
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.persistence_path = persistence_path or Path("/tmp/message_queue_fsa")
        self.persistence_path.mkdir(parents=True, exist_ok=True)

        # Queue management
        self.queues: Dict[str, BaseQueue] = {}
        self.queue_configs: Dict[str, QueueConfig] = {}
        self.queue_types: Dict[str, QueueType] = {}

        # Message tracking
        self.in_flight_messages: Dict[str, Message] = {}
        self.message_history: Dict[str, List[Message]] = defaultdict(list)

        # Exchange management
        self.exchanges: Dict[str, Exchange] = {}

        # Metrics
        self.metrics: Dict[str, QueueMetrics] = {}
        self.processing_times: Dict[str, List[float]] = defaultdict(list)
        self.message_counts: Dict[str, int] = defaultdict(int)

        # Worker management
        self.workers: Dict[str, int] = defaultdict(int)

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, messages: List[Message]) -> QueueProcessingResult:
        """
        Main message processing pipeline.

        Args:
            messages: List of messages to process

        Returns:
            QueueProcessingResult with processing statistics
        """
        processed = 0
        failed = 0
        errors = []

        for message in messages:
            try:
                # Validate message
                validation = self.validate(message)
                if not validation.valid:
                    errors.append(f"Message {message.message_id}: {', '.join(validation.errors)}")
                    failed += 1
                    continue

                # Enqueue message
                result = self.enqueue(
                    message,
                    message.routing_key or "default",
                    message.priority
                )

                if result.success:
                    processed += 1
                else:
                    failed += 1
                    if result.error:
                        errors.append(f"Message {message.message_id}: {result.error}")

            except Exception as e:
                failed += 1
                errors.append(f"Message {message.message_id}: {str(e)}")
                logger.error(f"Error processing message {message.message_id}: {e}")

        return QueueProcessingResult(
            success=failed == 0,
            processed_messages=processed,
            failed_messages=failed,
            errors=errors
        )

    # ==================== Validation ====================

    def validate(self, message: Message) -> ValidationResult:
        """
        Validate message structure and payload.

        Args:
            message: Message to validate

        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []

        # Check required fields
        if not message.message_id:
            errors.append("Message ID is required")

        if message.payload is None:
            warnings.append("Message payload is empty")

        # Check priority range
        if not (0 <= message.priority <= 100):
            warnings.append(f"Priority {message.priority} outside recommended range (0-100)")

        # Check retry count
        if message.retry_count > message.max_retries:
            errors.append(f"Retry count ({message.retry_count}) exceeds max retries ({message.max_retries})")

        # Check delivery mode
        if not isinstance(message.delivery_mode, DeliveryMode):
            errors.append(f"Invalid delivery mode: {message.delivery_mode}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Queue Operations ====================

    def create_queue(
        self,
        name: str,
        queue_type: QueueType,
        config: Optional[QueueConfig] = None
    ) -> BaseQueue:
        """
        Initialize new queue.

        Args:
            name: Queue name
            queue_type: Type of queue (FIFO, LIFO, Priority)
            config: Queue configuration

        Returns:
            Created queue instance
        """
        with self.lock:
            if name in self.queues:
                logger.warning(f"Queue {name} already exists")
                return self.queues[name]

            config = config or QueueConfig()

            # Create appropriate queue type
            if queue_type == QueueType.FIFO:
                queue_instance = FIFOQueue(name, config)
            elif queue_type == QueueType.LIFO:
                queue_instance = LIFOQueue(name, config)
            elif queue_type == QueueType.PRIORITY:
                queue_instance = PriorityQueue(name, config)
            else:
                raise ValueError(f"Unknown queue type: {queue_type}")

            self.queues[name] = queue_instance
            self.queue_configs[name] = config
            self.queue_types[name] = queue_type
            self.metrics[name] = QueueMetrics(
                queue_name=name,
                queue_type=queue_type
            )

            logger.info(f"Created {queue_type.value} queue: {name}")
            return queue_instance

    def delete_queue(self, name: str) -> DeleteResult:
        """
        Remove queue.

        Args:
            name: Queue name to delete

        Returns:
            DeleteResult with deletion status
        """
        with self.lock:
            if name not in self.queues:
                return DeleteResult(
                    success=False,
                    queue_name=name,
                    error=f"Queue {name} does not exist"
                )

            # Get message count before deletion
            messages_purged = self.queues[name].size()

            # Clean up queue resources
            del self.queues[name]
            del self.queue_configs[name]
            del self.queue_types[name]
            self.metrics.pop(name, None)
            self.processing_times.pop(name, None)
            self.message_counts.pop(name, None)
            self.workers.pop(name, None)

            logger.info(f"Deleted queue: {name}")
            return DeleteResult(
                success=True,
                queue_name=name,
                messages_purged=messages_purged
            )

    def enqueue(
        self,
        message: Message,
        queue_name: str,
        priority: Optional[int] = None
    ) -> EnqueueResult:
        """
        Add message to queue.

        Args:
            message: Message to enqueue
            queue_name: Target queue name
            priority: Optional priority override

        Returns:
            EnqueueResult with operation status
        """
        try:
            with self.lock:
                # Create queue if it doesn't exist
                if queue_name not in self.queues:
                    self.create_queue(queue_name, QueueType.FIFO)

                # Override priority if specified
                if priority is not None:
                    message.priority = priority

                # Add to queue
                success = self.queues[queue_name].put(message)

                if success:
                    # Persist if configured
                    if self.queue_configs[queue_name].persistent:
                        self.persist_message(message)

                    # Update metrics
                    self.metrics[queue_name].total_messages += 1
                    self.metrics[queue_name].pending_messages += 1
                    self.message_counts[queue_name] += 1

                    logger.debug(f"Enqueued message {message.message_id} to {queue_name}")
                    return EnqueueResult(
                        success=True,
                        message_id=message.message_id,
                        queue_name=queue_name
                    )
                else:
                    return EnqueueResult(
                        success=False,
                        message_id=message.message_id,
                        queue_name=queue_name,
                        error="Queue is full"
                    )

        except Exception as e:
            logger.error(f"Error enqueuing message: {e}")
            return EnqueueResult(
                success=False,
                message_id=message.message_id,
                queue_name=queue_name,
                error=str(e)
            )

    def dequeue(
        self,
        queue_name: str,
        batch_size: int = 1
    ) -> DequeueResult:
        """
        Retrieve messages from queue.

        Args:
            queue_name: Queue to dequeue from
            batch_size: Number of messages to retrieve

        Returns:
            DequeueResult with retrieved messages
        """
        try:
            with self.lock:
                if queue_name not in self.queues:
                    return DequeueResult(
                        success=False,
                        error=f"Queue {queue_name} does not exist"
                    )

                # Get messages from queue
                messages = self.queues[queue_name].get(batch_size)

                # Mark as in-flight
                for msg in messages:
                    msg.state = MessageState.IN_FLIGHT
                    self.in_flight_messages[msg.message_id] = msg
                    self.metrics[queue_name].pending_messages -= 1
                    self.metrics[queue_name].in_flight_messages += 1

                logger.debug(f"Dequeued {len(messages)} messages from {queue_name}")
                return DequeueResult(
                    success=True,
                    messages=messages
                )

        except Exception as e:
            logger.error(f"Error dequeuing from {queue_name}: {e}")
            return DequeueResult(
                success=False,
                error=str(e)
            )

    def purge_queue(self, queue_name: str) -> PurgeResult:
        """
        Clear all messages from queue.

        Args:
            queue_name: Queue to purge

        Returns:
            PurgeResult with purge status
        """
        try:
            with self.lock:
                if queue_name not in self.queues:
                    return PurgeResult(
                        success=False,
                        queue_name=queue_name,
                        error=f"Queue {queue_name} does not exist"
                    )

                # Count messages before purge
                messages_purged = self.queues[queue_name].size()

                # Recreate queue to clear it
                queue_type = self.queue_types[queue_name]
                config = self.queue_configs[queue_name]

                if queue_type == QueueType.FIFO:
                    self.queues[queue_name] = FIFOQueue(queue_name, config)
                elif queue_type == QueueType.LIFO:
                    self.queues[queue_name] = LIFOQueue(queue_name, config)
                elif queue_type == QueueType.PRIORITY:
                    self.queues[queue_name] = PriorityQueue(queue_name, config)

                # Update metrics
                self.metrics[queue_name].pending_messages = 0

                logger.info(f"Purged {messages_purged} messages from {queue_name}")
                return PurgeResult(
                    success=True,
                    queue_name=queue_name,
                    messages_purged=messages_purged
                )

        except Exception as e:
            logger.error(f"Error purging queue {queue_name}: {e}")
            return PurgeResult(
                success=False,
                queue_name=queue_name,
                error=str(e)
            )

    # ==================== Message Acknowledgment ====================

    def acknowledge(self, message_id: str) -> AckResult:
        """
        Confirm message processing.

        Args:
            message_id: ID of message to acknowledge

        Returns:
            AckResult with acknowledgment status
        """
        try:
            with self.lock:
                if message_id not in self.in_flight_messages:
                    return AckResult(
                        success=False,
                        message_id=message_id,
                        error="Message not in flight"
                    )

                message = self.in_flight_messages.pop(message_id)
                message.state = MessageState.ACKNOWLEDGED

                # Update metrics
                queue_name = message.routing_key or "default"
                if queue_name in self.metrics:
                    self.metrics[queue_name].in_flight_messages -= 1
                    self.metrics[queue_name].acknowledged_messages += 1

                logger.debug(f"Acknowledged message {message_id}")
                return AckResult(
                    success=True,
                    message_id=message_id
                )

        except Exception as e:
            logger.error(f"Error acknowledging message {message_id}: {e}")
            return AckResult(
                success=False,
                message_id=message_id,
                error=str(e)
            )

    def reject(self, message_id: str, requeue: bool = False) -> RejectResult:
        """
        Reject failed message.

        Args:
            message_id: ID of message to reject
            requeue: Whether to requeue the message

        Returns:
            RejectResult with rejection status
        """
        try:
            with self.lock:
                if message_id not in self.in_flight_messages:
                    return RejectResult(
                        success=False,
                        message_id=message_id,
                        error="Message not in flight"
                    )

                message = self.in_flight_messages.pop(message_id)
                message.state = MessageState.REJECTED
                message.retry_count += 1

                queue_name = message.routing_key or "default"

                # Update metrics
                if queue_name in self.metrics:
                    self.metrics[queue_name].in_flight_messages -= 1
                    self.metrics[queue_name].rejected_messages += 1

                # Handle requeue or dead letter
                requeued = False
                if requeue and message.retry_count <= message.max_retries:
                    self.enqueue(message, queue_name)
                    requeued = True
                else:
                    # Send to dead letter queue
                    self.handle_dead_letter(message, Exception("Max retries exceeded"))

                logger.debug(f"Rejected message {message_id}, requeued={requeued}")
                return RejectResult(
                    success=True,
                    message_id=message_id,
                    requeued=requeued
                )

        except Exception as e:
            logger.error(f"Error rejecting message {message_id}: {e}")
            return RejectResult(
                success=False,
                message_id=message_id,
                error=str(e)
            )

    # ==================== Persistence ====================

    def persist_message(self, message: Message) -> PersistenceResult:
        """
        Save message to durable storage.

        Args:
            message: Message to persist

        Returns:
            PersistenceResult with persistence status
        """
        try:
            file_path = self.persistence_path / f"{message.message_id}.json"
            with open(file_path, 'w') as f:
                json.dump(message.to_dict(), f)

            return PersistenceResult(
                success=True,
                message_id=message.message_id
            )

        except Exception as e:
            logger.error(f"Error persisting message {message.message_id}: {e}")
            return PersistenceResult(
                success=False,
                message_id=message.message_id,
                error=str(e)
            )

    # ==================== Routing ====================

    def route_message(
        self,
        message: Message,
        routing_key: str,
        exchange: str
    ) -> RoutingResult:
        """
        Route message through exchange.

        Args:
            message: Message to route
            routing_key: Routing key for the message
            exchange: Exchange name

        Returns:
            RoutingResult with routing status
        """
        try:
            with self.lock:
                if exchange not in self.exchanges:
                    return RoutingResult(
                        success=False,
                        error=f"Exchange {exchange} does not exist"
                    )

                # Get target queues from exchange
                target_queues = self.exchanges[exchange].route(routing_key)

                if not target_queues:
                    return RoutingResult(
                        success=False,
                        error=f"No queues bound to routing key {routing_key}"
                    )

                # Enqueue to all target queues
                for queue_name in target_queues:
                    self.enqueue(message, queue_name)

                logger.debug(f"Routed message {message.message_id} to {len(target_queues)} queues")
                return RoutingResult(
                    success=True,
                    queues_routed=target_queues
                )

        except Exception as e:
            logger.error(f"Error routing message: {e}")
            return RoutingResult(
                success=False,
                error=str(e)
            )

    # ==================== Batch Processing ====================

    def process_batch(
        self,
        messages: List[Message],
        handler: Callable[[Message], bool]
    ) -> BatchResult:
        """
        Process multiple messages with handler function.

        Args:
            messages: List of messages to process
            handler: Function to process each message

        Returns:
            BatchResult with processing statistics
        """
        processed = 0
        failed = 0
        errors = []

        for message in messages:
            try:
                start_time = time.time()
                success = handler(message)
                elapsed = time.time() - start_time

                # Track processing time
                queue_name = message.routing_key or "default"
                self.processing_times[queue_name].append(elapsed)

                if success:
                    self.acknowledge(message.message_id)
                    processed += 1
                else:
                    self.reject(message.message_id, requeue=True)
                    failed += 1
                    errors.append((message.message_id, "Handler returned False"))

            except Exception as e:
                self.reject(message.message_id, requeue=True)
                failed += 1
                errors.append((message.message_id, str(e)))
                logger.error(f"Error processing message {message.message_id}: {e}")

        return BatchResult(
            success=failed == 0,
            processed_count=processed,
            failed_count=failed,
            errors=errors
        )

    # ==================== Dead Letter Queue ====================

    def handle_dead_letter(
        self,
        message: Message,
        error: Exception
    ) -> DeadLetterResult:
        """
        Process failed messages.

        Args:
            message: Failed message
            error: Error that caused failure

        Returns:
            DeadLetterResult with dead letter status
        """
        try:
            queue_name = message.routing_key or "default"
            config = self.queue_configs.get(queue_name)

            # Determine dead letter queue
            if config and config.dead_letter_queue:
                dlq_name = config.dead_letter_queue
            else:
                dlq_name = f"{queue_name}.dead_letter"

            # Create DLQ if it doesn't exist
            if dlq_name not in self.queues:
                self.create_queue(dlq_name, QueueType.FIFO)

            # Update message
            message.state = MessageState.DEAD_LETTER
            message.error = str(error)

            # Enqueue to DLQ
            self.enqueue(message, dlq_name)

            # Update metrics
            if queue_name in self.metrics:
                self.metrics[queue_name].dead_letter_messages += 1

            logger.warning(f"Moved message {message.message_id} to dead letter queue {dlq_name}")
            return DeadLetterResult(
                success=True,
                message_id=message.message_id,
                dead_letter_queue=dlq_name
            )

        except Exception as e:
            logger.error(f"Error handling dead letter for {message.message_id}: {e}")
            return DeadLetterResult(
                success=False,
                message_id=message.message_id,
                dead_letter_queue="",
                error=str(e)
            )

    # ==================== Monitoring ====================

    def monitor_queue(self, queue_name: str) -> QueueMetrics:
        """
        Get queue statistics.

        Args:
            queue_name: Queue to monitor

        Returns:
            QueueMetrics with current statistics
        """
        with self.lock:
            if queue_name not in self.metrics:
                return QueueMetrics(queue_name=queue_name, queue_type=QueueType.FIFO)

            metrics = self.metrics[queue_name]

            # Calculate average processing time
            if queue_name in self.processing_times and self.processing_times[queue_name]:
                metrics.avg_processing_time = sum(self.processing_times[queue_name]) / len(self.processing_times[queue_name])

            # Calculate throughput (messages per second)
            # This is a simplified calculation
            if self.message_counts[queue_name] > 0:
                metrics.throughput = self.message_counts[queue_name] / 60.0  # Per minute

            # Update current queue size
            if queue_name in self.queues:
                metrics.pending_messages = self.queues[queue_name].size()

            return metrics

    # ==================== Auto-scaling ====================

    def scale_workers(
        self,
        queue_name: str,
        target_throughput: int
    ) -> ScalingResult:
        """
        Auto-scale queue consumers.

        Args:
            queue_name: Queue to scale workers for
            target_throughput: Target messages per second

        Returns:
            ScalingResult with scaling status
        """
        try:
            with self.lock:
                if queue_name not in self.queues:
                    return ScalingResult(
                        success=False,
                        queue_name=queue_name,
                        error=f"Queue {queue_name} does not exist"
                    )

                previous_workers = self.workers[queue_name]

                # Simple scaling logic based on queue size and throughput
                queue_size = self.queues[queue_name].size()
                metrics = self.monitor_queue(queue_name)

                # Calculate needed workers
                if metrics.avg_processing_time > 0:
                    messages_per_worker = 1.0 / metrics.avg_processing_time
                    needed_workers = int((target_throughput / messages_per_worker) + 1)
                else:
                    needed_workers = max(1, queue_size // 100)

                # Cap workers between 1 and 10
                new_workers = max(1, min(10, needed_workers))
                self.workers[queue_name] = new_workers

                logger.info(f"Scaled workers for {queue_name}: {previous_workers} -> {new_workers}")
                return ScalingResult(
                    success=True,
                    queue_name=queue_name,
                    previous_workers=previous_workers,
                    new_workers=new_workers
                )

        except Exception as e:
            logger.error(f"Error scaling workers for {queue_name}: {e}")
            return ScalingResult(
                success=False,
                queue_name=queue_name,
                error=str(e)
            )

    # ==================== Exchange Management ====================

    def create_exchange(
        self,
        name: str,
        exchange_type: ExchangeType
    ) -> Exchange:
        """
        Create a new message exchange.

        Args:
            name: Exchange name
            exchange_type: Type of exchange (DIRECT, TOPIC, FANOUT)

        Returns:
            Created Exchange instance
        """
        with self.lock:
            if name in self.exchanges:
                logger.warning(f"Exchange {name} already exists")
                return self.exchanges[name]

            exchange = Exchange(name, exchange_type)
            self.exchanges[name] = exchange

            logger.info(f"Created {exchange_type.value} exchange: {name}")
            return exchange

    def bind_queue(
        self,
        exchange_name: str,
        queue_name: str,
        routing_key: str
    ) -> bool:
        """
        Bind queue to exchange with routing key.

        Args:
            exchange_name: Exchange to bind to
            queue_name: Queue to bind
            routing_key: Routing key for binding

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            if exchange_name not in self.exchanges:
                logger.error(f"Exchange {exchange_name} does not exist")
                return False

            if queue_name not in self.queues:
                logger.error(f"Queue {queue_name} does not exist")
                return False

            self.exchanges[exchange_name].bind(queue_name, routing_key)
            logger.info(f"Bound queue {queue_name} to exchange {exchange_name} with key {routing_key}")
            return True

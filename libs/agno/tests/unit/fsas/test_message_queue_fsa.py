"""
Comprehensive test suite for MessageQueueFSA.

Tests cover:
- Message validation
- Queue operations (FIFO, LIFO, Priority)
- Enqueue/dequeue operations
- Message acknowledgment and rejection
- Persistence
- Dead letter queue handling
- Message routing with exchanges
- Batch processing
- Queue monitoring and metrics
- Worker auto-scaling
- Queue management (create, delete, purge)
- Edge cases and error handling
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytest

from agno.fsas.message_queue_fsa import (
    AckResult,
    BatchResult,
    DeadLetterResult,
    DeleteResult,
    DeliveryMode,
    DequeueResult,
    EnqueueResult,
    Exchange,
    ExchangeType,
    Message,
    MessageQueueFSA,
    MessageState,
    PersistenceResult,
    PurgeResult,
    QueueConfig,
    QueueMetrics,
    QueueProcessingResult,
    QueueType,
    RejectResult,
    RoutingResult,
    ScalingResult,
    ValidationResult,
)


# ==================== Fixtures ====================

@pytest.fixture
def temp_persistence_path():
    """Create temporary directory for persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def message_queue_fsa(temp_persistence_path):
    """Create MessageQueueFSA instance for testing."""
    return MessageQueueFSA(
        name="TestMessageQueue",
        persistence_path=temp_persistence_path
    )


@pytest.fixture
def sample_message():
    """Create sample message for testing."""
    return Message(
        payload={"data": "test", "value": 123},
        routing_key="test.queue",
        priority=5,
        delivery_mode=DeliveryMode.AT_LEAST_ONCE
    )


@pytest.fixture
def sample_messages():
    """Create list of sample messages for batch testing."""
    return [
        Message(payload=f"message_{i}", routing_key="test.queue", priority=i)
        for i in range(10)
    ]


# ==================== Test Message Validation ====================

def test_validate_valid_message(message_queue_fsa, sample_message):
    """Test validation of a valid message."""
    result = message_queue_fsa.validate(sample_message)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_message_without_id(message_queue_fsa):
    """Test validation fails for message without ID."""
    message = Message(message_id="", payload="test")
    result = message_queue_fsa.validate(message)

    assert result.valid is False
    assert "Message ID is required" in result.errors


def test_validate_message_with_exceeded_retries(message_queue_fsa):
    """Test validation fails when retry count exceeds max."""
    message = Message(
        payload="test",
        retry_count=5,
        max_retries=3
    )
    result = message_queue_fsa.validate(message)

    assert result.valid is False
    assert any("exceeds max retries" in err for err in result.errors)


def test_validate_message_with_warnings(message_queue_fsa):
    """Test validation generates warnings for edge cases."""
    message = Message(payload=None, priority=150)
    result = message_queue_fsa.validate(message)

    assert len(result.warnings) > 0
    assert any("empty" in warn.lower() for warn in result.warnings)


# ==================== Test Queue Creation ====================

def test_create_fifo_queue(message_queue_fsa):
    """Test FIFO queue creation."""
    queue = message_queue_fsa.create_queue(
        name="test_fifo",
        queue_type=QueueType.FIFO
    )

    assert queue is not None
    assert queue.name == "test_fifo"
    assert "test_fifo" in message_queue_fsa.queues
    assert message_queue_fsa.queue_types["test_fifo"] == QueueType.FIFO


def test_create_lifo_queue(message_queue_fsa):
    """Test LIFO queue creation."""
    queue = message_queue_fsa.create_queue(
        name="test_lifo",
        queue_type=QueueType.LIFO
    )

    assert queue is not None
    assert queue.name == "test_lifo"
    assert message_queue_fsa.queue_types["test_lifo"] == QueueType.LIFO


def test_create_priority_queue(message_queue_fsa):
    """Test Priority queue creation."""
    queue = message_queue_fsa.create_queue(
        name="test_priority",
        queue_type=QueueType.PRIORITY
    )

    assert queue is not None
    assert queue.name == "test_priority"
    assert message_queue_fsa.queue_types["test_priority"] == QueueType.PRIORITY


def test_create_queue_with_config(message_queue_fsa):
    """Test queue creation with custom configuration."""
    config = QueueConfig(
        max_size=500,
        persistent=True,
        dead_letter_queue="test.dlq"
    )

    queue = message_queue_fsa.create_queue(
        name="test_configured",
        queue_type=QueueType.FIFO,
        config=config
    )

    assert queue.config.max_size == 500
    assert queue.config.persistent is True
    assert queue.config.dead_letter_queue == "test.dlq"


def test_create_duplicate_queue(message_queue_fsa):
    """Test creating queue with duplicate name returns existing queue."""
    queue1 = message_queue_fsa.create_queue("test_dup", QueueType.FIFO)
    queue2 = message_queue_fsa.create_queue("test_dup", QueueType.LIFO)

    assert queue1 is queue2
    assert message_queue_fsa.queue_types["test_dup"] == QueueType.FIFO


# ==================== Test Enqueue/Dequeue Operations ====================

def test_enqueue_message(message_queue_fsa, sample_message):
    """Test enqueuing a message to a queue."""
    result = message_queue_fsa.enqueue(sample_message, "test_queue")

    assert isinstance(result, EnqueueResult)
    assert result.success is True
    assert result.message_id == sample_message.message_id
    assert result.queue_name == "test_queue"


def test_enqueue_creates_queue_if_not_exists(message_queue_fsa, sample_message):
    """Test enqueue creates queue automatically if it doesn't exist."""
    assert "auto_queue" not in message_queue_fsa.queues

    result = message_queue_fsa.enqueue(sample_message, "auto_queue")

    assert result.success is True
    assert "auto_queue" in message_queue_fsa.queues


def test_dequeue_messages(message_queue_fsa, sample_messages):
    """Test dequeuing messages from a queue."""
    # Enqueue messages
    message_queue_fsa.create_queue("test_dequeue", QueueType.FIFO)
    for msg in sample_messages[:5]:
        message_queue_fsa.enqueue(msg, "test_dequeue")

    # Dequeue messages
    result = message_queue_fsa.dequeue("test_dequeue", batch_size=3)

    assert isinstance(result, DequeueResult)
    assert result.success is True
    assert len(result.messages) == 3
    assert all(msg.state == MessageState.IN_FLIGHT for msg in result.messages)


def test_dequeue_from_nonexistent_queue(message_queue_fsa):
    """Test dequeue fails for non-existent queue."""
    result = message_queue_fsa.dequeue("nonexistent", batch_size=1)

    assert result.success is False
    assert "does not exist" in result.error


def test_fifo_queue_ordering(message_queue_fsa):
    """Test FIFO queue maintains first-in-first-out order."""
    message_queue_fsa.create_queue("fifo_test", QueueType.FIFO)

    # Enqueue messages with identifiable payloads
    for i in range(5):
        msg = Message(payload=f"msg_{i}", routing_key="fifo_test")
        message_queue_fsa.enqueue(msg, "fifo_test")

    # Dequeue and verify order
    result = message_queue_fsa.dequeue("fifo_test", batch_size=5)
    payloads = [msg.payload for msg in result.messages]

    assert payloads == ["msg_0", "msg_1", "msg_2", "msg_3", "msg_4"]


def test_lifo_queue_ordering(message_queue_fsa):
    """Test LIFO queue maintains last-in-first-out order."""
    message_queue_fsa.create_queue("lifo_test", QueueType.LIFO)

    # Enqueue messages
    for i in range(5):
        msg = Message(payload=f"msg_{i}", routing_key="lifo_test")
        message_queue_fsa.enqueue(msg, "lifo_test")

    # Dequeue and verify order (reversed)
    result = message_queue_fsa.dequeue("lifo_test", batch_size=5)
    payloads = [msg.payload for msg in result.messages]

    assert payloads == ["msg_4", "msg_3", "msg_2", "msg_1", "msg_0"]


def test_priority_queue_ordering(message_queue_fsa):
    """Test priority queue orders by priority."""
    message_queue_fsa.create_queue("priority_test", QueueType.PRIORITY)

    # Enqueue messages with different priorities
    priorities = [1, 5, 3, 9, 2]
    for priority in priorities:
        msg = Message(payload=f"priority_{priority}", priority=priority)
        message_queue_fsa.enqueue(msg, "priority_test")

    # Dequeue and verify highest priority first
    result = message_queue_fsa.dequeue("priority_test", batch_size=5)
    priorities_out = [msg.priority for msg in result.messages]

    assert priorities_out == [9, 5, 3, 2, 1]


# ==================== Test Message Acknowledgment ====================

def test_acknowledge_message(message_queue_fsa, sample_message):
    """Test acknowledging a message."""
    # Enqueue and dequeue
    message_queue_fsa.enqueue(sample_message, "ack_test")
    dequeue_result = message_queue_fsa.dequeue("ack_test", batch_size=1)
    message = dequeue_result.messages[0]

    # Acknowledge
    result = message_queue_fsa.acknowledge(message.message_id)

    assert isinstance(result, AckResult)
    assert result.success is True
    assert result.message_id == message.message_id
    assert message.message_id not in message_queue_fsa.in_flight_messages


def test_acknowledge_non_inflight_message(message_queue_fsa):
    """Test acknowledging message not in flight fails."""
    result = message_queue_fsa.acknowledge("non_existent_id")

    assert result.success is False
    assert "not in flight" in result.error


def test_reject_message_with_requeue(message_queue_fsa, sample_message):
    """Test rejecting a message with requeue."""
    # Enqueue and dequeue
    message_queue_fsa.enqueue(sample_message, "reject_test")
    dequeue_result = message_queue_fsa.dequeue("reject_test", batch_size=1)
    message = dequeue_result.messages[0]

    # Reject with requeue
    result = message_queue_fsa.reject(message.message_id, requeue=True)

    assert isinstance(result, RejectResult)
    assert result.success is True
    assert result.requeued is True
    assert message.message_id not in message_queue_fsa.in_flight_messages


def test_reject_message_without_requeue_sends_to_dlq(message_queue_fsa):
    """Test rejecting message without requeue sends to dead letter queue."""
    # Create message with max retries already reached
    message = Message(
        payload="test",
        routing_key="dlq_test",
        retry_count=3,
        max_retries=3
    )

    # Enqueue, dequeue, and reject
    message_queue_fsa.enqueue(message, "dlq_test")
    dequeue_result = message_queue_fsa.dequeue("dlq_test", batch_size=1)
    msg = dequeue_result.messages[0]

    result = message_queue_fsa.reject(msg.message_id, requeue=False)

    assert result.success is True
    assert result.requeued is False

    # Check DLQ was created
    dlq_name = "dlq_test.dead_letter"
    assert dlq_name in message_queue_fsa.queues


# ==================== Test Persistence ====================

def test_persist_message(message_queue_fsa, sample_message, temp_persistence_path):
    """Test message persistence to disk."""
    result = message_queue_fsa.persist_message(sample_message)

    assert isinstance(result, PersistenceResult)
    assert result.success is True
    assert result.message_id == sample_message.message_id

    # Verify file was created
    file_path = temp_persistence_path / f"{sample_message.message_id}.json"
    assert file_path.exists()

    # Verify content
    with open(file_path, 'r') as f:
        data = json.load(f)
        assert data["message_id"] == sample_message.message_id
        assert data["payload"] == sample_message.payload


def test_message_serialization(sample_message):
    """Test message can be serialized and deserialized."""
    # Serialize
    data = sample_message.to_dict()

    assert isinstance(data, dict)
    assert data["message_id"] == sample_message.message_id
    assert data["payload"] == sample_message.payload

    # Deserialize
    restored = Message.from_dict(data)

    assert restored.message_id == sample_message.message_id
    assert restored.payload == sample_message.payload
    assert restored.priority == sample_message.priority
    assert restored.delivery_mode == sample_message.delivery_mode


# ==================== Test Dead Letter Queue ====================

def test_handle_dead_letter(message_queue_fsa, sample_message):
    """Test handling failed message in dead letter queue."""
    error = Exception("Processing failed")
    result = message_queue_fsa.handle_dead_letter(sample_message, error)

    assert isinstance(result, DeadLetterResult)
    assert result.success is True
    assert result.message_id == sample_message.message_id
    assert ".dead_letter" in result.dead_letter_queue

    # Verify message was added to DLQ
    assert result.dead_letter_queue in message_queue_fsa.queues


def test_custom_dead_letter_queue(message_queue_fsa, sample_message):
    """Test using custom dead letter queue configuration."""
    # Create queue with custom DLQ
    config = QueueConfig(dead_letter_queue="custom.dlq")
    message_queue_fsa.create_queue("test_custom_dlq", QueueType.FIFO, config)

    # Update message routing key
    sample_message.routing_key = "test_custom_dlq"

    # Handle dead letter
    error = Exception("Test error")
    result = message_queue_fsa.handle_dead_letter(sample_message, error)

    assert result.success is True
    assert result.dead_letter_queue == "custom.dlq"


# ==================== Test Message Routing ====================

def test_create_direct_exchange(message_queue_fsa):
    """Test creating a direct exchange."""
    exchange = message_queue_fsa.create_exchange("test_direct", ExchangeType.DIRECT)

    assert isinstance(exchange, Exchange)
    assert exchange.name == "test_direct"
    assert exchange.exchange_type == ExchangeType.DIRECT
    assert "test_direct" in message_queue_fsa.exchanges


def test_create_fanout_exchange(message_queue_fsa):
    """Test creating a fanout exchange."""
    exchange = message_queue_fsa.create_exchange("test_fanout", ExchangeType.FANOUT)

    assert exchange.exchange_type == ExchangeType.FANOUT


def test_bind_queue_to_exchange(message_queue_fsa):
    """Test binding queue to exchange."""
    # Create exchange and queue
    message_queue_fsa.create_exchange("test_exchange", ExchangeType.DIRECT)
    message_queue_fsa.create_queue("test_queue", QueueType.FIFO)

    # Bind queue
    result = message_queue_fsa.bind_queue("test_exchange", "test_queue", "test.key")

    assert result is True


def test_route_message_direct_exchange(message_queue_fsa, sample_message):
    """Test routing message through direct exchange."""
    # Setup
    message_queue_fsa.create_exchange("direct_ex", ExchangeType.DIRECT)
    message_queue_fsa.create_queue("queue1", QueueType.FIFO)
    message_queue_fsa.create_queue("queue2", QueueType.FIFO)
    message_queue_fsa.bind_queue("direct_ex", "queue1", "key1")
    message_queue_fsa.bind_queue("direct_ex", "queue2", "key2")

    # Route to key1
    result = message_queue_fsa.route_message(sample_message, "key1", "direct_ex")

    assert isinstance(result, RoutingResult)
    assert result.success is True
    assert "queue1" in result.queues_routed
    assert "queue2" not in result.queues_routed


def test_route_message_fanout_exchange(message_queue_fsa, sample_message):
    """Test routing message through fanout exchange."""
    # Setup
    message_queue_fsa.create_exchange("fanout_ex", ExchangeType.FANOUT)
    message_queue_fsa.create_queue("queue1", QueueType.FIFO)
    message_queue_fsa.create_queue("queue2", QueueType.FIFO)
    message_queue_fsa.bind_queue("fanout_ex", "queue1", "any_key")
    message_queue_fsa.bind_queue("fanout_ex", "queue2", "any_key")

    # Route message
    result = message_queue_fsa.route_message(sample_message, "any_key", "fanout_ex")

    assert result.success is True
    assert "queue1" in result.queues_routed
    assert "queue2" in result.queues_routed


def test_route_message_topic_exchange(message_queue_fsa, sample_message):
    """Test routing message through topic exchange with pattern matching."""
    # Setup
    message_queue_fsa.create_exchange("topic_ex", ExchangeType.TOPIC)
    message_queue_fsa.create_queue("queue1", QueueType.FIFO)
    message_queue_fsa.create_queue("queue2", QueueType.FIFO)
    message_queue_fsa.bind_queue("topic_ex", "queue1", "test.*")
    message_queue_fsa.bind_queue("topic_ex", "queue2", "test.specific")

    # Route with matching pattern
    result = message_queue_fsa.route_message(sample_message, "test.specific", "topic_ex")

    assert result.success is True
    assert len(result.queues_routed) > 0


# ==================== Test Batch Processing ====================

def test_process_batch_success(message_queue_fsa, sample_messages):
    """Test successful batch processing."""
    # Enqueue messages
    message_queue_fsa.create_queue("batch_test", QueueType.FIFO)
    for msg in sample_messages:
        message_queue_fsa.enqueue(msg, "batch_test")

    # Dequeue batch
    dequeue_result = message_queue_fsa.dequeue("batch_test", batch_size=5)

    # Process with handler that always succeeds
    def success_handler(message: Message) -> bool:
        return True

    result = message_queue_fsa.process_batch(dequeue_result.messages, success_handler)

    assert isinstance(result, BatchResult)
    assert result.success is True
    assert result.processed_count == 5
    assert result.failed_count == 0


def test_process_batch_with_failures(message_queue_fsa, sample_messages):
    """Test batch processing with some failures."""
    # Enqueue messages
    message_queue_fsa.create_queue("batch_fail_test", QueueType.FIFO)
    for msg in sample_messages[:5]:
        message_queue_fsa.enqueue(msg, "batch_fail_test")

    # Dequeue batch
    dequeue_result = message_queue_fsa.dequeue("batch_fail_test", batch_size=5)

    # Process with handler that fails on even indices
    def partial_handler(message: Message) -> bool:
        # Extract number from payload
        num = int(message.payload.split('_')[1])
        return num % 2 != 0

    result = message_queue_fsa.process_batch(dequeue_result.messages, partial_handler)

    assert result.success is False
    assert result.processed_count > 0
    assert result.failed_count > 0
    assert result.processed_count + result.failed_count == 5


def test_process_batch_with_exceptions(message_queue_fsa, sample_messages):
    """Test batch processing handles exceptions."""
    # Enqueue messages
    message_queue_fsa.create_queue("batch_exception_test", QueueType.FIFO)
    for msg in sample_messages[:3]:
        message_queue_fsa.enqueue(msg, "batch_exception_test")

    # Dequeue batch
    dequeue_result = message_queue_fsa.dequeue("batch_exception_test", batch_size=3)

    # Process with handler that raises exception
    def exception_handler(message: Message) -> bool:
        raise ValueError("Test exception")

    result = message_queue_fsa.process_batch(dequeue_result.messages, exception_handler)

    assert result.success is False
    assert result.failed_count == 3
    assert len(result.errors) == 3


# ==================== Test Queue Monitoring ====================

def test_monitor_queue(message_queue_fsa, sample_messages):
    """Test queue monitoring and metrics collection."""
    # Setup queue with messages
    message_queue_fsa.create_queue("monitor_test", QueueType.FIFO)
    for msg in sample_messages:
        message_queue_fsa.enqueue(msg, "monitor_test")

    # Get metrics
    metrics = message_queue_fsa.monitor_queue("monitor_test")

    assert isinstance(metrics, QueueMetrics)
    assert metrics.queue_name == "monitor_test"
    assert metrics.queue_type == QueueType.FIFO
    assert metrics.total_messages > 0
    assert metrics.pending_messages > 0


def test_monitor_nonexistent_queue(message_queue_fsa):
    """Test monitoring non-existent queue returns empty metrics."""
    metrics = message_queue_fsa.monitor_queue("nonexistent")

    assert isinstance(metrics, QueueMetrics)
    assert metrics.queue_name == "nonexistent"
    assert metrics.total_messages == 0


def test_metrics_serialization(message_queue_fsa):
    """Test queue metrics can be serialized to dictionary."""
    message_queue_fsa.create_queue("metrics_test", QueueType.FIFO)
    metrics = message_queue_fsa.monitor_queue("metrics_test")

    data = metrics.to_dict()

    assert isinstance(data, dict)
    assert data["queue_name"] == "metrics_test"
    assert "total_messages" in data
    assert "pending_messages" in data


# ==================== Test Worker Scaling ====================

def test_scale_workers(message_queue_fsa, sample_messages):
    """Test worker auto-scaling based on throughput."""
    # Setup queue with messages
    message_queue_fsa.create_queue("scale_test", QueueType.FIFO)
    for msg in sample_messages:
        message_queue_fsa.enqueue(msg, "scale_test")

    # Scale workers
    result = message_queue_fsa.scale_workers("scale_test", target_throughput=10)

    assert isinstance(result, ScalingResult)
    assert result.success is True
    assert result.queue_name == "scale_test"
    assert result.new_workers >= 1


def test_scale_workers_nonexistent_queue(message_queue_fsa):
    """Test scaling workers for non-existent queue fails."""
    result = message_queue_fsa.scale_workers("nonexistent", target_throughput=5)

    assert result.success is False
    assert "does not exist" in result.error


# ==================== Test Queue Management ====================

def test_delete_queue(message_queue_fsa, sample_messages):
    """Test deleting a queue."""
    # Create and populate queue
    message_queue_fsa.create_queue("delete_test", QueueType.FIFO)
    for msg in sample_messages[:3]:
        message_queue_fsa.enqueue(msg, "delete_test")

    # Delete queue
    result = message_queue_fsa.delete_queue("delete_test")

    assert isinstance(result, DeleteResult)
    assert result.success is True
    assert result.queue_name == "delete_test"
    assert result.messages_purged > 0
    assert "delete_test" not in message_queue_fsa.queues


def test_delete_nonexistent_queue(message_queue_fsa):
    """Test deleting non-existent queue fails."""
    result = message_queue_fsa.delete_queue("nonexistent")

    assert result.success is False
    assert "does not exist" in result.error


def test_purge_queue(message_queue_fsa, sample_messages):
    """Test purging all messages from a queue."""
    # Create and populate queue
    message_queue_fsa.create_queue("purge_test", QueueType.FIFO)
    for msg in sample_messages:
        message_queue_fsa.enqueue(msg, "purge_test")

    # Verify messages exist
    assert message_queue_fsa.queues["purge_test"].size() > 0

    # Purge queue
    result = message_queue_fsa.purge_queue("purge_test")

    assert isinstance(result, PurgeResult)
    assert result.success is True
    assert result.messages_purged > 0
    assert message_queue_fsa.queues["purge_test"].size() == 0


def test_purge_nonexistent_queue(message_queue_fsa):
    """Test purging non-existent queue fails."""
    result = message_queue_fsa.purge_queue("nonexistent")

    assert result.success is False
    assert "does not exist" in result.error


# ==================== Test Main Execute Pipeline ====================

def test_execute_pipeline(message_queue_fsa, sample_messages):
    """Test main message processing pipeline."""
    result = message_queue_fsa.execute(sample_messages)

    assert isinstance(result, QueueProcessingResult)
    assert result.success is True
    assert result.processed_messages == len(sample_messages)
    assert result.failed_messages == 0


def test_execute_pipeline_with_invalid_messages(message_queue_fsa):
    """Test execute pipeline handles invalid messages."""
    invalid_messages = [
        Message(message_id="", payload="test1"),  # Invalid: no ID
        Message(payload="test2", retry_count=10, max_retries=3),  # Invalid: retries exceeded
    ]

    result = message_queue_fsa.execute(invalid_messages)

    assert result.success is False
    assert result.failed_messages == 2
    assert len(result.errors) == 2


# ==================== Test Deduplication ====================

def test_message_deduplication(message_queue_fsa, sample_message):
    """Test message deduplication prevents duplicate processing."""
    # Create queue with deduplication enabled
    config = QueueConfig(enable_deduplication=True)
    message_queue_fsa.create_queue("dedup_test", QueueType.FIFO, config)

    # Enqueue same message twice
    result1 = message_queue_fsa.enqueue(sample_message, "dedup_test")
    result2 = message_queue_fsa.enqueue(sample_message, "dedup_test")

    assert result1.success is True
    # Second enqueue should be ignored due to deduplication
    # (Note: The implementation returns False for duplicates)

    # Queue should only have one message
    queue_size = message_queue_fsa.queues["dedup_test"].size()
    assert queue_size == 1


# ==================== Test Edge Cases ====================

def test_empty_queue_dequeue(message_queue_fsa):
    """Test dequeuing from empty queue returns empty list."""
    message_queue_fsa.create_queue("empty_test", QueueType.FIFO)
    result = message_queue_fsa.dequeue("empty_test", batch_size=5)

    assert result.success is True
    assert len(result.messages) == 0


def test_large_batch_dequeue(message_queue_fsa, sample_messages):
    """Test dequeuing with batch size larger than available messages."""
    message_queue_fsa.create_queue("large_batch_test", QueueType.FIFO)
    for msg in sample_messages[:3]:
        message_queue_fsa.enqueue(msg, "large_batch_test")

    result = message_queue_fsa.dequeue("large_batch_test", batch_size=10)

    assert result.success is True
    assert len(result.messages) == 3  # Only returns available messages


def test_concurrent_operations(message_queue_fsa, sample_messages):
    """Test thread safety with concurrent operations."""
    import threading

    message_queue_fsa.create_queue("concurrent_test", QueueType.FIFO)

    def enqueue_worker():
        for msg in sample_messages[:5]:
            message_queue_fsa.enqueue(msg, "concurrent_test")

    # Create multiple threads
    threads = [threading.Thread(target=enqueue_worker) for _ in range(3)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify all messages were enqueued
    metrics = message_queue_fsa.monitor_queue("concurrent_test")
    assert metrics.total_messages == 15  # 5 messages * 3 threads

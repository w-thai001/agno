"""
Comprehensive tests for Message Broker FSA

This test suite covers all major functionality including:
- Publish/subscribe message delivery
- Point-to-point queue operations
- Request/reply pattern with correlation IDs
- Message persistence and recovery after crash
- Consumer group load balancing
- Dead letter queue routing for failed messages
- Priority queue ordering
- Exactly-once delivery semantics
- Topic wildcard matching
- Message expiration and TTL
- Flow control and back-pressure
- Metrics collection accuracy
"""

import asyncio
import pytest
import time
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from agno.fsas.infrastructure.message_broker_fsa import (
    MessageBrokerFSA,
    Message,
    MessagePattern,
    MessagePriority,
    MessageState,
    DeliveryMode,
    MessageQueue,
    TopicManager,
    MessageRouter,
    ConsumerGroup,
    ConsumerInfo,
    DeadLetterQueue,
    PersistenceEngine,
    DeliveryTracker,
    MetricsCollector,
    PublishError,
    ConsumeError,
    DeliveryError,
)


@pytest.fixture
async def temp_storage():
    """Create temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def message_broker(temp_storage):
    """Create message broker for testing"""
    broker = MessageBrokerFSA(
        storage_dir=temp_storage,
        enable_persistence=True,
        max_queue_depth=1000
    )
    await broker.start()
    yield broker
    await broker.stop()


@pytest.fixture
def sample_message():
    """Create sample message"""
    return Message(
        message_id="test-msg-123",
        topic="test.topic",
        body={"data": "test"},
        priority=MessagePriority.NORMAL
    )


class TestPublishSubscribe:
    """Test publish/subscribe pattern"""

    @pytest.mark.asyncio
    async def test_basic_pub_sub(self, message_broker):
        """Test basic publish and subscribe"""
        received_messages = []

        async def subscriber(message: Message):
            received_messages.append(message)

        # Subscribe
        consumer_id = await message_broker.subscribe("test.topic", subscriber)

        # Publish
        msg_id = await message_broker.publish(
            topic="test.topic",
            body={"data": "hello"}
        )

        # Wait for delivery
        await asyncio.sleep(0.1)

        assert len(received_messages) == 1
        assert received_messages[0].body == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, message_broker):
        """Test multiple subscribers receive same message"""
        received1 = []
        received2 = []

        async def subscriber1(message: Message):
            received1.append(message)

        async def subscriber2(message: Message):
            received2.append(message)

        # Subscribe both
        await message_broker.subscribe("test.topic", subscriber1)
        await message_broker.subscribe("test.topic", subscriber2)

        # Publish once
        await message_broker.publish("test.topic", {"data": "broadcast"})

        # Wait for delivery
        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1
        assert received1[0].body == received2[0].body

    @pytest.mark.asyncio
    async def test_unsubscribe(self, message_broker):
        """Test unsubscribe stops message delivery"""
        received = []

        async def subscriber(message: Message):
            received.append(message)

        # Subscribe and unsubscribe
        consumer_id = await message_broker.subscribe("test.topic", subscriber)
        await message_broker.unsubscribe("test.topic", consumer_id)

        # Publish after unsubscribe
        await message_broker.publish("test.topic", {"data": "test"})

        await asyncio.sleep(0.1)

        assert len(received) == 0


class TestPointToPoint:
    """Test point-to-point queue operations"""

    @pytest.mark.asyncio
    async def test_basic_queue_consume(self, message_broker):
        """Test basic queue consumption"""
        received = []

        async def consumer(message: Message):
            received.append(message)

        # Start consuming
        await message_broker.consume("test.queue", consumer)

        # Publish
        await message_broker.publish("test.queue", {"data": "test"})

        # Wait for consumption
        await asyncio.sleep(0.2)

        assert len(received) == 1
        assert received[0].body == {"data": "test"}

    @pytest.mark.asyncio
    async def test_consumer_group_load_balancing(self, message_broker):
        """Test consumer group load balancing"""
        received1 = []
        received2 = []

        async def consumer1(message: Message):
            received1.append(message)

        async def consumer2(message: Message):
            received2.append(message)

        # Create consumer group
        await message_broker.consume("test.queue", consumer1, group_id="group1")
        await message_broker.consume("test.queue", consumer2, group_id="group1")

        # Publish multiple messages
        for i in range(10):
            await message_broker.publish("test.queue", {"data": i})

        # Wait for consumption
        await asyncio.sleep(0.5)

        # Both consumers should have received messages
        total_received = len(received1) + len(received2)
        assert total_received == 10
        assert len(received1) > 0
        assert len(received2) > 0


class TestRequestReply:
    """Test request/reply pattern"""

    @pytest.mark.asyncio
    async def test_request_reply(self, message_broker):
        """Test request/reply with correlation ID"""
        # Set up request handler
        async def request_handler(message: Message):
            # Send reply
            await message_broker.reply(
                request=message,
                body={"response": "pong"}
            )

        await message_broker.subscribe("ping", request_handler)

        # Send request
        reply = await message_broker.request(
            topic="ping",
            body={"request": "ping"},
            timeout=5.0
        )

        assert reply.body == {"response": "pong"}
        assert reply.correlation_id is not None

    @pytest.mark.asyncio
    async def test_request_timeout(self, message_broker):
        """Test request timeout"""
        with pytest.raises(DeliveryError):
            await message_broker.request(
                topic="nonexistent",
                body={"test": "data"},
                timeout=0.5
            )


class TestMessagePersistence:
    """Test message persistence and recovery"""

    @pytest.mark.asyncio
    async def test_message_persistence(self, temp_storage):
        """Test messages are persisted to disk"""
        broker = MessageBrokerFSA(
            storage_dir=temp_storage,
            enable_persistence=True
        )
        await broker.start()

        # Publish message
        msg_id = await broker.publish("test.topic", {"data": "persistent"})

        await asyncio.sleep(0.1)

        # Check message file exists
        message_file = Path(temp_storage) / "messages" / f"{msg_id}.json"
        assert message_file.exists()

        await broker.stop()

    @pytest.mark.asyncio
    async def test_wal_recovery(self, temp_storage):
        """Test recovery from WAL after crash"""
        # First broker - publish messages
        broker1 = MessageBrokerFSA(
            storage_dir=temp_storage,
            enable_persistence=True
        )
        await broker1.start()

        await broker1.publish("test.topic", {"data": "message1"})
        await broker1.publish("test.topic", {"data": "message2"})

        await asyncio.sleep(0.1)
        await broker1.stop()

        # Second broker - recover from WAL
        broker2 = MessageBrokerFSA(
            storage_dir=temp_storage,
            enable_persistence=True
        )
        await broker2.initialize()

        # Check messages were recovered
        queue = broker2.queues.get("test.topic")
        assert queue is not None
        assert queue.get_depth() > 0


class TestPriorityQueue:
    """Test priority queue ordering"""

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test messages are delivered by priority"""
        queue = MessageQueue("test", persistence_engine=None)

        # Add messages with different priorities
        msg_low = Message("1", "test", "low", priority=MessagePriority.LOW)
        msg_normal = Message("2", "test", "normal", priority=MessagePriority.NORMAL)
        msg_high = Message("3", "test", "high", priority=MessagePriority.HIGH)
        msg_critical = Message("4", "test", "critical", priority=MessagePriority.CRITICAL)

        # Enqueue in random order
        await queue.enqueue(msg_normal)
        await queue.enqueue(msg_low)
        await queue.enqueue(msg_critical)
        await queue.enqueue(msg_high)

        # Dequeue - should get in priority order
        dequeued = []
        for _ in range(4):
            msg = await queue.dequeue()
            if msg:
                dequeued.append(msg.priority)

        assert dequeued == [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW
        ]


class TestDeadLetterQueue:
    """Test dead letter queue for failed messages"""

    @pytest.mark.asyncio
    async def test_dlq_on_max_retries(self, message_broker):
        """Test message sent to DLQ after max retries"""
        failure_count = 0

        async def failing_consumer(message: Message):
            nonlocal failure_count
            failure_count += 1
            raise Exception("Consumer error")

        # Set up consumer
        await message_broker.consume("test.queue", failing_consumer)

        # Publish message with low max retries
        await message_broker.publish(
            "test.queue",
            {"data": "test"},
            delivery_mode=DeliveryMode.AT_LEAST_ONCE
        )

        # Wait for retries and DLQ
        await asyncio.sleep(2)

        # Check DLQ
        dlq_messages = message_broker.dead_letter_queue.get_messages()
        assert len(dlq_messages) > 0

    @pytest.mark.asyncio
    async def test_dlq_retry(self, message_broker):
        """Test retrying message from DLQ"""
        dlq = message_broker.dead_letter_queue

        # Add message to DLQ
        message = Message("test-id", "test.topic", {"data": "test"})
        dlq.add_message(message, "Test failure")

        # Retry message
        retried = dlq.retry_message("test-id")

        assert retried is not None
        assert retried.state == MessageState.PENDING
        assert retried.retry_count == 1


class TestDeliverySemantics:
    """Test delivery guarantee semantics"""

    @pytest.mark.asyncio
    async def test_at_most_once(self, message_broker):
        """Test at-most-once delivery (fire and forget)"""
        received = []

        async def consumer(message: Message):
            received.append(message)

        await message_broker.subscribe("test.topic", consumer)

        await message_broker.publish(
            "test.topic",
            {"data": "test"},
            delivery_mode=DeliveryMode.AT_MOST_ONCE
        )

        await asyncio.sleep(0.1)

        assert len(received) == 1
        # Message should be auto-acknowledged
        assert len(message_broker.delivery_tracker.pending_acks) == 0

    @pytest.mark.asyncio
    async def test_at_least_once(self, message_broker):
        """Test at-least-once delivery requires acknowledgment"""
        received = []

        async def consumer(message: Message):
            received.append(message)
            # Manually acknowledge
            await message_broker.acknowledge(message.message_id)

        await message_broker.subscribe("test.topic", consumer)

        msg_id = await message_broker.publish(
            "test.topic",
            {"data": "test"},
            delivery_mode=DeliveryMode.AT_LEAST_ONCE
        )

        await asyncio.sleep(0.1)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_exactly_once(self, message_broker):
        """Test exactly-once delivery prevents duplicates"""
        received = []

        async def consumer(message: Message):
            received.append(message)

        await message_broker.subscribe("test.topic", consumer)

        # Publish same message twice
        message = Message(
            message_id="duplicate-test",
            topic="test.topic",
            body={"data": "test"},
            delivery_mode=DeliveryMode.EXACTLY_ONCE
        )

        # First delivery
        await message_broker._deliver_to_subscribers(message)
        await asyncio.sleep(0.1)

        # Second delivery (should be ignored)
        await message_broker._deliver_to_subscribers(message)
        await asyncio.sleep(0.1)

        assert len(received) == 1


class TestTopicWildcards:
    """Test topic wildcard matching"""

    def test_single_level_wildcard(self):
        """Test * matches single level"""
        router = MessageRouter()

        assert router.match_topic("test.*.topic", "test.foo.topic") is True
        assert router.match_topic("test.*.topic", "test.bar.topic") is True
        assert router.match_topic("test.*.topic", "test.foo.bar.topic") is False

    def test_multi_level_wildcard(self):
        """Test # matches multiple levels"""
        router = MessageRouter()

        assert router.match_topic("test.#", "test.foo") is True
        assert router.match_topic("test.#", "test.foo.bar") is True
        assert router.match_topic("test.#", "test.foo.bar.baz") is True
        assert router.match_topic("test.#", "other.foo") is False

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, message_broker):
        """Test subscribing with wildcards"""
        received = []

        async def subscriber(message: Message):
            received.append(message)

        # Subscribe with wildcard
        await message_broker.subscribe("test.*", subscriber)

        # Publish to matching topics
        await message_broker.publish("test.foo", {"data": "1"})
        await message_broker.publish("test.bar", {"data": "2"})
        await message_broker.publish("other.topic", {"data": "3"})

        await asyncio.sleep(0.2)

        # Should receive messages from test.foo and test.bar
        assert len(received) == 2


class TestMessageExpiration:
    """Test message TTL and expiration"""

    @pytest.mark.asyncio
    async def test_message_expiration(self):
        """Test expired messages are not delivered"""
        queue = MessageQueue("test", persistence_engine=None)

        # Create message with short TTL
        message = Message(
            message_id="expire-test",
            topic="test",
            body={"data": "test"},
            ttl=0.1  # 100ms TTL
        )

        await queue.enqueue(message)

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Try to dequeue
        dequeued = await queue.dequeue()

        # Should not get expired message
        assert dequeued is None

    @pytest.mark.asyncio
    async def test_expired_messages_cleaned_up(self, message_broker):
        """Test cleanup of expired messages"""
        # Publish with short TTL
        await message_broker.publish(
            "test.topic",
            {"data": "test"},
            ttl=0.1
        )

        # Wait for cleanup
        await asyncio.sleep(2)

        # Check metrics
        metrics = message_broker.metrics_collector.get_metrics()
        assert metrics.messages_expired > 0


class TestFlowControl:
    """Test flow control and back-pressure"""

    @pytest.mark.asyncio
    async def test_backpressure_on_queue_limit(self, temp_storage):
        """Test back-pressure when queue limit reached"""
        broker = MessageBrokerFSA(
            storage_dir=temp_storage,
            enable_persistence=False,
            max_queue_depth=10  # Small limit
        )
        await broker.start()

        # Fill queue to limit
        for i in range(10):
            await broker.publish("test.queue", {"data": i})

        # Next publish should fail with back-pressure
        with pytest.raises(PublishError, match="back-pressure"):
            await broker.publish("test.queue", {"data": "overflow"})

        await broker.stop()


class TestConsumerGroups:
    """Test consumer group management"""

    def test_consumer_group_creation(self):
        """Test creating consumer group"""
        group = ConsumerGroup("test-group")

        consumer = ConsumerInfo(
            consumer_id="consumer1",
            group_id="test-group",
            topics=["test.topic"],
            callback=AsyncMock()
        )

        group.add_consumer(consumer)

        assert len(group.consumers) == 1
        assert "consumer1" in group.consumers

    def test_round_robin_selection(self):
        """Test round-robin consumer selection"""
        group = ConsumerGroup("test-group")

        # Add multiple consumers
        for i in range(3):
            consumer = ConsumerInfo(
                consumer_id=f"consumer{i}",
                group_id="test-group",
                topics=["test.topic"],
                callback=AsyncMock()
            )
            group.add_consumer(consumer)

        # Get next consumers - should cycle through
        selected = []
        for _ in range(6):
            consumer = group.get_next_consumer()
            if consumer:
                selected.append(consumer.consumer_id)

        # Should have cycled through all consumers twice
        assert selected.count("consumer0") == 2
        assert selected.count("consumer1") == 2
        assert selected.count("consumer2") == 2


class TestMetricsCollection:
    """Test metrics collection accuracy"""

    @pytest.mark.asyncio
    async def test_publish_metrics(self, message_broker):
        """Test publish metrics are recorded"""
        initial_count = message_broker.metrics_collector.metrics.messages_published

        await message_broker.publish("test.topic", {"data": "test"})

        metrics = message_broker.metrics_collector.get_metrics()
        assert metrics.messages_published == initial_count + 1

    @pytest.mark.asyncio
    async def test_delivery_metrics(self, message_broker):
        """Test delivery metrics are recorded"""
        received = []

        async def consumer(message: Message):
            received.append(message)

        await message_broker.subscribe("test.topic", consumer)
        await message_broker.publish("test.topic", {"data": "test"})

        await asyncio.sleep(0.1)

        metrics = message_broker.metrics_collector.get_metrics()
        assert metrics.messages_delivered > 0

    @pytest.mark.asyncio
    async def test_throughput_calculation(self):
        """Test throughput calculation"""
        collector = MetricsCollector()

        # Record multiple messages
        for _ in range(10):
            collector.record_publish()

        throughput = collector.calculate_throughput()

        # Should have some throughput
        assert throughput >= 0

    @pytest.mark.asyncio
    async def test_queue_depth_metrics(self, message_broker):
        """Test queue depth is tracked"""
        # Publish messages without consumers
        for i in range(5):
            await message_broker.publish("test.queue", {"data": i})

        await asyncio.sleep(0.2)

        metrics = message_broker.metrics_collector.get_metrics()
        assert metrics.total_queue_depth >= 5


class TestDeliveryTracker:
    """Test delivery tracking and acknowledgments"""

    def test_track_delivery(self):
        """Test tracking message delivery"""
        tracker = DeliveryTracker()

        message = Message("test-id", "test.topic", {"data": "test"})
        tracker.track_delivery(message)

        assert "test-id" in tracker.pending_acks

    def test_acknowledge_delivery(self):
        """Test acknowledging delivery"""
        tracker = DeliveryTracker()

        message = Message("test-id", "test.topic", {"data": "test"})
        tracker.track_delivery(message)

        result = tracker.acknowledge("test-id")

        assert result is True
        assert "test-id" not in tracker.pending_acks

    def test_duplicate_detection(self):
        """Test duplicate message detection for exactly-once"""
        tracker = DeliveryTracker()

        message = Message(
            message_id="test-id",
            topic="test.topic",
            body={"data": "test"},
            delivery_mode=DeliveryMode.EXACTLY_ONCE
        )

        tracker.track_delivery(message)

        # Check for duplicate
        is_dup = tracker.is_duplicate("test-id")

        assert is_dup is True

    @pytest.mark.asyncio
    async def test_ack_timeout(self):
        """Test acknowledgment timeout detection"""
        tracker = DeliveryTracker()
        tracker.ack_timeout = 0.1  # Short timeout

        message = Message("test-id", "test.topic", {"data": "test"})
        tracker.track_delivery(message)

        # Wait for timeout
        await asyncio.sleep(0.2)

        timed_out = tracker.get_timed_out_messages()

        assert len(timed_out) == 1
        assert timed_out[0].message_id == "test-id"


class TestMessageQueue:
    """Test message queue operations"""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        """Test basic enqueue and dequeue"""
        queue = MessageQueue("test", persistence_engine=None)

        message = Message("test-id", "test.topic", {"data": "test"})
        await queue.enqueue(message)

        dequeued = await queue.dequeue()

        assert dequeued is not None
        assert dequeued.message_id == "test-id"
        assert dequeued.state == MessageState.IN_FLIGHT

    @pytest.mark.asyncio
    async def test_acknowledge_removes_message(self):
        """Test acknowledging removes message from queue"""
        queue = MessageQueue("test", persistence_engine=None)

        message = Message("test-id", "test.topic", {"data": "test"})
        await queue.enqueue(message)

        dequeued = await queue.dequeue()
        await queue.acknowledge(dequeued.message_id)

        assert dequeued.message_id not in queue.in_flight
        assert dequeued.message_id not in queue.message_index

    @pytest.mark.asyncio
    async def test_nack_requeues_message(self):
        """Test negative ack requeues message"""
        queue = MessageQueue("test", persistence_engine=None)

        message = Message("test-id", "test.topic", {"data": "test"})
        await queue.enqueue(message)

        dequeued = await queue.dequeue()
        await queue.nack(dequeued.message_id, requeue=True)

        # Message should be back in queue
        assert queue.get_depth() > 0


class TestBrokerValidation:
    """Test broker validation and error handling"""

    def test_validation(self, message_broker):
        """Test broker validation"""
        assert message_broker.validate() is True

    def test_error_handling_info(self, message_broker):
        """Test error handling information retrieval"""
        info = message_broker.error_handling()

        assert "total_queues" in info
        assert "total_consumers" in info
        assert "metrics" in info
        assert "running" in info

    @pytest.mark.asyncio
    async def test_execute_operation(self, message_broker):
        """Test execute method for operations"""
        msg_id = await message_broker.execute(
            "publish",
            topic="test.topic",
            body={"data": "test"}
        )

        assert msg_id is not None


class TestPersistenceEngine:
    """Test persistence engine operations"""

    @pytest.mark.asyncio
    async def test_persist_and_load(self, temp_storage):
        """Test persisting and loading messages"""
        engine = PersistenceEngine(temp_storage)

        message = Message("test-id", "test.topic", {"data": "test"})
        await engine.persist_message(message)

        loaded = await engine.load_message("test-id")

        assert loaded is not None
        assert loaded.message_id == "test-id"
        assert loaded.body == {"data": "test"}

    @pytest.mark.asyncio
    async def test_delete_message(self, temp_storage):
        """Test deleting persisted message"""
        engine = PersistenceEngine(temp_storage)

        message = Message("test-id", "test.topic", {"data": "test"})
        await engine.persist_message(message)

        await engine.delete_message("test-id")

        loaded = await engine.load_message("test-id")
        assert loaded is None

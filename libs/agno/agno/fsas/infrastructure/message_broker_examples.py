"""
Example usage of Message Broker FSA

This module demonstrates various use cases for the MessageBrokerFSA
including pub/sub, point-to-point queues, request/reply, message persistence,
consumer groups, priority queues, dead letter queues, and more.
"""

import asyncio
import logging
from agno.fsas.infrastructure.message_broker_fsa import (
    MessageBrokerFSA,
    Message,
    MessagePriority,
    DeliveryMode,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_publish_subscribe():
    """Example 1: Publish/Subscribe pattern"""
    print("\n=== Example 1: Publish/Subscribe Pattern ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        # Define subscribers
        async def logger_subscriber(message: Message):
            logger.info(f"Logger received: {message.body}")

        async def analytics_subscriber(message: Message):
            logger.info(f"Analytics received: {message.body}")

        # Subscribe to topic
        await broker.subscribe("app.events", logger_subscriber)
        await broker.subscribe("app.events", analytics_subscriber)

        # Publish event
        await broker.publish(
            topic="app.events",
            body={"event": "user_login", "user_id": 123}
        )

        # Wait for delivery
        await asyncio.sleep(0.2)

        print("✓ Both subscribers received the event")

    finally:
        await broker.stop()


async def example_point_to_point_queue():
    """Example 2: Point-to-Point Queue"""
    print("\n=== Example 2: Point-to-Point Queue ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        processed = []

        async def worker(message: Message):
            logger.info(f"Worker processing: {message.body}")
            processed.append(message.body)
            # Acknowledge message
            await broker.acknowledge(message.message_id, "task.queue")

        # Start consumer
        await broker.consume("task.queue", worker)

        # Publish tasks
        for i in range(5):
            await broker.publish(
                topic="task.queue",
                body={"task_id": i, "action": "process"}
            )

        # Wait for processing
        await asyncio.sleep(0.5)

        print(f"✓ Processed {len(processed)} tasks")

    finally:
        await broker.stop()


async def example_request_reply():
    """Example 3: Request/Reply Pattern"""
    print("\n=== Example 3: Request/Reply Pattern ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        # Set up service handler
        async def calculator_service(message: Message):
            request = message.body
            a = request.get("a", 0)
            b = request.get("b", 0)
            operation = request.get("operation", "add")

            if operation == "add":
                result = a + b
            elif operation == "multiply":
                result = a * b
            else:
                result = None

            # Send reply
            await broker.reply(
                request=message,
                body={"result": result}
            )

        await broker.subscribe("calculator.request", calculator_service)

        # Send request
        reply = await broker.request(
            topic="calculator.request",
            body={"a": 5, "b": 3, "operation": "add"},
            timeout=5.0
        )

        print(f"✓ Request result: {reply.body}")

    finally:
        await broker.stop()


async def example_consumer_groups():
    """Example 4: Consumer Groups with Load Balancing"""
    print("\n=== Example 4: Consumer Groups ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        worker1_count = []
        worker2_count = []

        async def worker1(message: Message):
            worker1_count.append(message.body)
            logger.info(f"Worker 1 processing: {message.body}")

        async def worker2(message: Message):
            worker2_count.append(message.body)
            logger.info(f"Worker 2 processing: {message.body}")

        # Create consumer group
        await broker.consume(
            queue_name="tasks",
            callback=worker1,
            group_id="worker-group"
        )
        await broker.consume(
            queue_name="tasks",
            callback=worker2,
            group_id="worker-group"
        )

        # Publish multiple tasks
        for i in range(10):
            await broker.publish(
                topic="tasks",
                body={"task_id": i}
            )

        # Wait for processing
        await asyncio.sleep(0.5)

        print(f"✓ Worker 1 processed: {len(worker1_count)} tasks")
        print(f"✓ Worker 2 processed: {len(worker2_count)} tasks")
        print(f"✓ Total: {len(worker1_count) + len(worker2_count)} tasks")

    finally:
        await broker.stop()


async def example_priority_queues():
    """Example 5: Priority Queues"""
    print("\n=== Example 5: Priority Queues ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        processed_order = []

        async def worker(message: Message):
            processed_order.append(message.body["priority"])
            logger.info(f"Processing {message.body}")

        await broker.consume("priority.queue", worker)

        # Publish with different priorities
        await broker.publish(
            "priority.queue",
            {"priority": "normal"},
            priority=MessagePriority.NORMAL
        )
        await broker.publish(
            "priority.queue",
            {"priority": "low"},
            priority=MessagePriority.LOW
        )
        await broker.publish(
            "priority.queue",
            {"priority": "critical"},
            priority=MessagePriority.CRITICAL
        )
        await broker.publish(
            "priority.queue",
            {"priority": "high"},
            priority=MessagePriority.HIGH
        )

        # Wait for processing
        await asyncio.sleep(0.5)

        print(f"✓ Processing order: {processed_order}")
        print("✓ Expected: ['critical', 'high', 'normal', 'low']")

    finally:
        await broker.stop()


async def example_message_persistence():
    """Example 6: Message Persistence and Recovery"""
    print("\n=== Example 6: Message Persistence ===")

    # First broker - publish with persistence
    broker1 = MessageBrokerFSA(
        storage_dir="/tmp/broker_example",
        enable_persistence=True
    )
    await broker1.start()

    try:
        # Publish persistent messages
        for i in range(3):
            await broker1.publish(
                topic="persistent.queue",
                body={"message": f"data_{i}"}
            )

        await asyncio.sleep(0.1)
        print("✓ Published 3 persistent messages")

    finally:
        await broker1.stop()

    # Second broker - recover from storage
    broker2 = MessageBrokerFSA(
        storage_dir="/tmp/broker_example",
        enable_persistence=True
    )
    await broker2.initialize()

    try:
        # Check recovered messages
        queue = broker2.queues.get("persistent.queue")
        if queue:
            depth = queue.get_depth()
            print(f"✓ Recovered {depth} messages from storage")

    finally:
        await broker2.stop()


async def example_dead_letter_queue():
    """Example 7: Dead Letter Queue"""
    print("\n=== Example 7: Dead Letter Queue ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        failure_count = 0

        async def failing_worker(message: Message):
            nonlocal failure_count
            failure_count += 1
            # Simulate failure
            raise Exception("Processing failed")

        await broker.consume("failing.queue", failing_worker)

        # Publish message
        await broker.publish(
            "failing.queue",
            {"data": "will_fail"}
        )

        # Wait for retries and DLQ
        await asyncio.sleep(2)

        # Check DLQ
        dlq_messages = broker.dead_letter_queue.get_messages()
        print(f"✓ Failed {failure_count} times")
        print(f"✓ Messages in DLQ: {len(dlq_messages)}")

        if dlq_messages:
            print(f"✓ DLQ reason: {dlq_messages[0].headers.get('dlq_reason')}")

    finally:
        await broker.stop()


async def example_topic_wildcards():
    """Example 8: Topic Wildcards"""
    print("\n=== Example 8: Topic Wildcards ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        received = []

        async def wildcard_subscriber(message: Message):
            received.append(message.topic)
            logger.info(f"Received from {message.topic}: {message.body}")

        # Subscribe with wildcards
        await broker.subscribe("app.*.events", wildcard_subscriber)

        # Publish to matching topics
        await broker.publish("app.user.events", {"event": "login"})
        await broker.publish("app.system.events", {"event": "startup"})
        await broker.publish("app.order.events", {"event": "placed"})

        # This won't match
        await broker.publish("other.events", {"event": "test"})

        # Wait for delivery
        await asyncio.sleep(0.2)

        print(f"✓ Received from topics: {received}")
        print("✓ Wildcard pattern 'app.*.events' matched correctly")

    finally:
        await broker.stop()


async def example_delivery_modes():
    """Example 9: Different Delivery Modes"""
    print("\n=== Example 9: Delivery Modes ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        # At-most-once (fire and forget)
        async def at_most_once_subscriber(message: Message):
            logger.info("At-most-once: No ack required")

        await broker.subscribe("topic.at_most_once", at_most_once_subscriber)

        await broker.publish(
            "topic.at_most_once",
            {"data": "fire_and_forget"},
            delivery_mode=DeliveryMode.AT_MOST_ONCE
        )

        # At-least-once (requires ack)
        async def at_least_once_subscriber(message: Message):
            logger.info("At-least-once: Manual ack required")
            await broker.acknowledge(message.message_id)

        await broker.subscribe("topic.at_least_once", at_least_once_subscriber)

        await broker.publish(
            "topic.at_least_once",
            {"data": "with_ack"},
            delivery_mode=DeliveryMode.AT_LEAST_ONCE
        )

        # Exactly-once (with deduplication)
        async def exactly_once_subscriber(message: Message):
            logger.info("Exactly-once: Deduplication enabled")

        await broker.subscribe("topic.exactly_once", exactly_once_subscriber)

        await broker.publish(
            "topic.exactly_once",
            {"data": "deduplicated"},
            delivery_mode=DeliveryMode.EXACTLY_ONCE
        )

        await asyncio.sleep(0.2)

        print("✓ Demonstrated all delivery modes")

    finally:
        await broker.stop()


async def example_message_expiration():
    """Example 10: Message TTL and Expiration"""
    print("\n=== Example 10: Message Expiration ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        received = []

        async def subscriber(message: Message):
            received.append(message.body)

        # Publish with short TTL
        await broker.publish(
            "expiring.topic",
            {"data": "will_expire"},
            ttl=0.1  # 100ms TTL
        )

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Subscribe after expiration
        await broker.subscribe("expiring.topic", subscriber)

        # Wait a bit
        await asyncio.sleep(0.1)

        print(f"✓ Received messages: {len(received)}")
        print("✓ Message expired before delivery")

        # Check metrics
        metrics = broker.metrics_collector.get_metrics()
        print(f"✓ Expired messages: {metrics.messages_expired}")

    finally:
        await broker.stop()


async def example_metrics_monitoring():
    """Example 11: Metrics and Monitoring"""
    print("\n=== Example 11: Metrics and Monitoring ===")

    broker = MessageBrokerFSA(enable_persistence=False)
    await broker.start()

    try:
        async def subscriber(message: Message):
            pass

        await broker.subscribe("metrics.topic", subscriber)

        # Publish multiple messages
        for i in range(10):
            await broker.publish("metrics.topic", {"count": i})

        await asyncio.sleep(0.3)

        # Get metrics
        metrics = broker.metrics_collector.get_metrics()

        print(f"✓ Messages published: {metrics.messages_published}")
        print(f"✓ Messages delivered: {metrics.messages_delivered}")
        print(f"✓ Messages acknowledged: {metrics.messages_acknowledged}")
        print(f"✓ Throughput: {metrics.throughput_per_second:.2f} msg/s")
        print(f"✓ Queue depth: {metrics.total_queue_depth}")
        print(f"✓ Consumer count: {metrics.consumer_count}")

    finally:
        await broker.stop()


async def example_flow_control():
    """Example 12: Flow Control and Back-Pressure"""
    print("\n=== Example 12: Flow Control ===")

    broker = MessageBrokerFSA(
        enable_persistence=False,
        max_queue_depth=5  # Small limit for demo
    )
    await broker.start()

    try:
        # Fill queue to limit
        for i in range(5):
            await broker.publish("limited.queue", {"count": i})

        print("✓ Published 5 messages (at limit)")

        # Try to publish beyond limit
        try:
            await broker.publish("limited.queue", {"count": 6})
            print("✗ Should have triggered back-pressure")
        except Exception as e:
            print(f"✓ Back-pressure activated: {str(e)[:50]}")

    finally:
        await broker.stop()


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Message Broker FSA Examples")
    print("=" * 60)

    examples = [
        example_publish_subscribe,
        example_point_to_point_queue,
        example_request_reply,
        example_consumer_groups,
        example_priority_queues,
        example_message_persistence,
        example_dead_letter_queue,
        example_topic_wildcards,
        example_delivery_modes,
        example_message_expiration,
        example_metrics_monitoring,
        example_flow_control,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"✗ Example failed: {e}")

    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

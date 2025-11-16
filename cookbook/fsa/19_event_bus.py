"""📡 FSA Event Bus Example

This example demonstrates event-driven communication between FSAs using
pub/sub messaging patterns.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.event_bus import FSAEventBus, Event, EventPriority


def main():
    """Demonstrate FSA Event Bus"""

    print("\n" + "=" * 70)
    print("FSA EVENT BUS - PUB/SUB MESSAGING")
    print("=" * 70)

    # =========================================================================
    # Example 1: Basic Pub/Sub
    # =========================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: BASIC PUB/SUB")
    print("─" * 70)

    # Create event bus
    event_bus = FSAEventBus(
        name="EventBus",
        enable_history=True,
        debug_mode=True
    )

    print("\n✓ Event bus created")

    # Define event handlers
    def on_task_started(event: Event):
        print(f"  📥 Handler 1: Task started - {event.payload.get('task_id')}")

    def on_task_completed(event: Event):
        print(f"  📥 Handler 2: Task completed - {event.payload.get('task_id')}")

    # Subscribe to events
    print("\n📢 Subscribing to events:")

    sub1 = event_bus.subscribe(
        topic="task.started",
        handler=on_task_started
    )
    print(f"  ✓ Subscribed to 'task.started' ({sub1})")

    sub2 = event_bus.subscribe(
        topic="task.completed",
        handler=on_task_completed
    )
    print(f"  ✓ Subscribed to 'task.completed' ({sub2})")

    # Publish events
    print("\n📤 Publishing events:")

    event_id1 = event_bus.publish(
        topic="task.started",
        payload={"task_id": "task-001", "timestamp": "2025-01-01T10:00:00"},
        source="TaskManager"
    )
    print(f"  ✓ Published 'task.started' ({event_id1})")

    event_id2 = event_bus.publish(
        topic="task.completed",
        payload={"task_id": "task-001", "result": "success"},
        source="TaskManager"
    )
    print(f"  ✓ Published 'task.completed' ({event_id2})")

    # =========================================================================
    # Example 2: Wildcard Subscriptions
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 2: WILDCARD SUBSCRIPTIONS")
    print("=" * 70)

    print("\n🌟 Wildcard pattern matching:")
    print("  * = matches single segment")
    print("  # = matches multiple segments")

    # Create new event bus for clean demo
    wildcard_bus = FSAEventBus(name="WildcardBus", debug_mode=False)

    # Subscribe with wildcards
    def on_any_task_event(event: Event):
        print(f"  📥 Wildcard handler: {event.topic} - {event.payload}")

    def on_any_user_event(event: Event):
        print(f"  📥 User handler: {event.topic}")

    print("\n📢 Creating wildcard subscriptions:")

    wildcard_bus.subscribe(
        topic="task.*",  # Matches task.started, task.completed, etc.
        handler=on_any_task_event
    )
    print("  ✓ Subscribed to 'task.*'")

    wildcard_bus.subscribe(
        topic="user.#",  # Matches user.created, user.profile.updated, etc.
        handler=on_any_user_event
    )
    print("  ✓ Subscribed to 'user.#'")

    # Publish various events
    print("\n📤 Publishing events to wildcard topics:")

    wildcard_bus.publish(
        topic="task.started",
        payload={"task": "Build FSA"},
        source="System"
    )

    wildcard_bus.publish(
        topic="task.completed",
        payload={"task": "Build FSA", "status": "done"},
        source="System"
    )

    wildcard_bus.publish(
        topic="user.created",
        payload={"user_id": "user-123"},
        source="UserService"
    )

    wildcard_bus.publish(
        topic="user.profile.updated",
        payload={"user_id": "user-123", "field": "email"},
        source="UserService"
    )

    # =========================================================================
    # Example 3: Event Filtering
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 3: EVENT FILTERING")
    print("=" * 70)

    print("\n🔍 Filtered subscriptions:")

    filter_bus = FSAEventBus(name="FilterBus", debug_mode=False)

    # Subscribe with filter
    def on_high_priority_task(event: Event):
        print(f"  🔴 High priority: {event.payload}")

    def on_error_event(event: Event):
        print(f"  ❌ Error event: {event.payload}")

    filter_bus.subscribe(
        topic="task.*",
        handler=on_high_priority_task,
        filter_condition="payload.get('priority') == 'high'"
    )
    print("  ✓ Subscribed with filter: priority == 'high'")

    filter_bus.subscribe(
        topic="task.*",
        handler=on_error_event,
        filter_condition="payload.get('status') == 'error'"
    )
    print("  ✓ Subscribed with filter: status == 'error'")

    # Publish events (only matching ones will be delivered)
    print("\n📤 Publishing events (some will be filtered):")

    events_to_publish = [
        ("task.execute", {"id": "1", "priority": "high", "status": "running"}),
        ("task.execute", {"id": "2", "priority": "low", "status": "running"}),
        ("task.execute", {"id": "3", "priority": "normal", "status": "error"}),
        ("task.execute", {"id": "4", "priority": "high", "status": "success"}),
    ]

    for topic, payload in events_to_publish:
        print(f"\n  Publishing: {payload}")
        filter_bus.publish(topic=topic, payload=payload, source="System")

    # =========================================================================
    # Example 4: Event History & Replay
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 4: EVENT HISTORY & REPLAY")
    print("=" * 70)

    history_bus = FSAEventBus(
        name="HistoryBus",
        enable_history=True,
        debug_mode=False
    )

    # Publish several events
    print("\n📤 Publishing historical events:")

    for i in range(5):
        history_bus.publish(
            topic="data.processed",
            payload={"record_id": i + 1, "timestamp": f"2025-01-{i + 1:02d}"},
            source="DataProcessor"
        )
        print(f"  {i + 1}. Published data.processed (record {i + 1})")

    # Get event history
    history = history_bus.get_event_history()

    print(f"\n📚 Event History ({len(history)} events):")
    for i, event in enumerate(history, 1):
        print(f"  {i}. {event.topic} - {event.timestamp}")

    # Subscribe to replay
    replayed_count = [0]

    def on_replay(event: Event):
        replayed_count[0] += 1
        print(f"  🔄 Replayed: {event.payload}")

    history_bus.subscribe(
        topic="data.processed",
        handler=on_replay
    )

    # Replay events
    print(f"\n🔄 Replaying events:")
    replayed = history_bus.replay_events(topic="data.processed")

    print(f"\n✓ Replayed {replayed} events")

    # =========================================================================
    # Example 5: Event Priorities
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 5: EVENT PRIORITIES")
    print("=" * 70)

    priority_bus = FSAEventBus(name="PriorityBus", debug_mode=False)

    # Subscribe to all events
    def on_any_priority_event(event: Event):
        priority_icons = {
            EventPriority.LOW: "⚪",
            EventPriority.NORMAL: "🟢",
            EventPriority.HIGH: "🟡",
            EventPriority.CRITICAL: "🔴"
        }
        icon = priority_icons.get(event.priority, "⚫")
        print(f"  {icon} [{event.priority.name}] {event.topic}: {event.payload}")

    priority_bus.subscribe(
        topic="alert.*",
        handler=on_any_priority_event
    )

    print("\n📤 Publishing events with different priorities:")

    priorities = [
        (EventPriority.LOW, "System update available"),
        (EventPriority.NORMAL, "Backup completed"),
        (EventPriority.HIGH, "High memory usage detected"),
        (EventPriority.CRITICAL, "System failure imminent!")
    ]

    for priority, message in priorities:
        priority_bus.publish(
            topic="alert.system",
            payload={"message": message},
            priority=priority,
            source="MonitoringSystem"
        )

    # =========================================================================
    # Example 6: Dead Letter Queue
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 6: DEAD LETTER QUEUE")
    print("=" * 70)

    dlq_bus = FSAEventBus(
        name="DLQBus",
        enable_dead_letter_queue=True,
        debug_mode=False
    )

    # Subscribe with failing handler
    def failing_handler(event: Event):
        print(f"  📥 Handler called for: {event.topic}")
        raise Exception("Handler intentionally failed!")

    dlq_bus.subscribe(
        topic="test.failure",
        handler=failing_handler
    )

    print("\n📤 Publishing event to failing handler:")

    try:
        dlq_bus.publish(
            topic="test.failure",
            payload={"test": "data"},
            source="Test"
        )
    except:
        pass

    # Check dead letter queue
    dlq = dlq_bus.get_dead_letter_queue()

    print(f"\n💀 Dead Letter Queue ({len(dlq)} events):")
    for i, event in enumerate(dlq, 1):
        print(f"  {i}. {event.topic} - {event.payload}")

    # =========================================================================
    # Example 7: Subscription Management
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 7: SUBSCRIPTION MANAGEMENT")
    print("=" * 70)

    mgmt_bus = FSAEventBus(name="MgmtBus", debug_mode=False)

    # Create multiple subscriptions
    print("\n📢 Creating subscriptions:")

    def handler1(e): print(f"  Handler 1: {e.topic}")
    def handler2(e): print(f"  Handler 2: {e.topic}")
    def handler3(e): print(f"  Handler 3: {e.topic}")

    sub_a = mgmt_bus.subscribe("event.a", handler1)
    sub_b = mgmt_bus.subscribe("event.b", handler2)
    sub_c = mgmt_bus.subscribe("event.*", handler3)

    print(f"  ✓ Created 3 subscriptions")

    # List subscriptions
    subs = mgmt_bus.get_subscriptions()
    print(f"\n📋 Active Subscriptions ({len(subs)}):")
    for sub in subs:
        status = "✓ Active" if sub.active else "✗ Paused"
        print(f"  - {sub.subscription_id}: {sub.topic_pattern} ({status})")

    # Pause subscription
    print(f"\n⏸️  Pausing subscription: {sub_b}")
    mgmt_bus.pause_subscription(sub_b)

    # Publish event
    print(f"\n📤 Publishing to 'event.b' (paused subscription):")
    mgmt_bus.publish(topic="event.b", payload={"test": True}, source="Test")
    print("  (Handler 2 should not be called)")

    # Resume subscription
    print(f"\n▶️  Resuming subscription: {sub_b}")
    mgmt_bus.resume_subscription(sub_b)

    print(f"\n📤 Publishing to 'event.b' again (resumed):")
    mgmt_bus.publish(topic="event.b", payload={"test": True}, source="Test")

    # Unsubscribe
    print(f"\n🗑️  Unsubscribing: {sub_a}")
    mgmt_bus.unsubscribe(sub_a)

    remaining_subs = mgmt_bus.get_subscriptions()
    print(f"  Remaining subscriptions: {len(remaining_subs)}")

    # =========================================================================
    # Example 8: Statistics
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EXAMPLE 8: EVENT BUS STATISTICS")
    print("=" * 70)

    stats = event_bus.get_statistics()

    print(f"\n📊 Event Bus Statistics:")
    print(f"  Total Events Published: {stats['total_events_published']}")
    print(f"  Total Events Delivered: {stats['total_events_delivered']}")
    print(f"  Delivery Failures: {stats['total_delivery_failures']}")
    print(f"  Active Subscriptions: {stats['active_subscriptions']}/{stats['total_subscriptions']}")
    print(f"  Event History Size: {stats['event_history_size']}")
    print(f"  Dead Letter Queue Size: {stats['dead_letter_queue_size']}")
    print(f"  Delivery Success Rate: {stats['delivery_success_rate']:.1f}%")

    # =========================================================================
    # Best Practices
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("EVENT BUS BEST PRACTICES")
    print("=" * 70)

    practices = [
        "1. Use hierarchical topic naming (e.g., 'service.entity.action')",
        "2. Keep event payloads small and focused",
        "3. Use wildcards for cross-cutting concerns (logging, monitoring)",
        "4. Implement error handling in event handlers",
        "5. Monitor dead letter queue for failed deliveries",
        "6. Use event priorities for critical notifications",
        "7. Enable event history for debugging and replay",
        "8. Filter events at subscription level for performance",
        "9. Unsubscribe when handlers are no longer needed",
        "10. Consider async delivery for high-volume scenarios"
    ]

    for practice in practices:
        print(f"   {practice}")

    # =========================================================================
    # Common Use Cases
    # =========================================================================
    print("\n\n" + "=" * 70)
    print("COMMON USE CASES")
    print("=" * 70)

    use_cases = {
        "Microservices Communication": "Decouple services with pub/sub",
        "Workflow Coordination": "FSAs communicate via events",
        "Audit Logging": "Subscribe to all events for logging",
        "Monitoring & Alerts": "High-priority events trigger alerts",
        "Event Sourcing": "Store all events for state reconstruction",
        "CQRS": "Separate command and query models via events",
        "Real-time Updates": "Push updates to subscribers",
        "Integration": "Connect disparate systems"
    }

    for use_case, description in use_cases.items():
        print(f"   • {use_case}: {description}")

    print("\n" + "=" * 70)
    print("✅ Event bus demonstration complete!")
    print("=" * 70)

    print("\n💡 Key Takeaway: Event bus enables decoupled, scalable")
    print("   communication between FSAs using pub/sub patterns!")


if __name__ == "__main__":
    main()

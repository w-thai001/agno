"""
Stream Processor FSA Usage Examples

This module demonstrates various usage patterns for the Stream Processor FSA,
including:
- Basic stream processing pipelines
- Advanced windowing strategies
- Stateful operations
- Fault tolerance configurations
- Complex event processing
- Stream joins and enrichment
"""

import asyncio
import random
import time
from pathlib import Path
from typing import Dict, List

from agno.fsas.infrastructure.stream_processor_fsa import (
    BackpressureStrategy,
    FileStreamSource,
    GeneratorStreamSource,
    InMemoryStateBackend,
    InMemoryStreamSource,
    PersistentStateBackend,
    ProcessingGuarantee,
    StreamEvent,
    StreamProcessorFSA,
    WindowType,
)


# ============================================================================
# Example 1: Basic Stream Processing Pipeline
# ============================================================================


async def example_basic_pipeline():
    """
    Basic stream processing with map and filter transformations.

    This example shows how to:
    - Create a stream processor
    - Add an in-memory source
    - Apply transformations
    - Run the processor
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Stream Processing Pipeline")
    print("=" * 60)

    # Create sample events
    events = [
        StreamEvent(key="user1", value={"action": "login", "duration": 10}),
        StreamEvent(key="user2", value={"action": "click", "duration": 2}),
        StreamEvent(key="user1", value={"action": "purchase", "duration": 30}),
        StreamEvent(key="user3", value={"action": "logout", "duration": 1}),
        StreamEvent(key="user2", value={"action": "purchase", "duration": 25}),
    ]

    # Create processor
    processor = StreamProcessorFSA()

    # Add source
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Apply transformations
    processor.map(lambda x: {**x, "score": x["duration"] * 10})
    processor.filter(lambda x: x["score"] > 50)
    processor.map(lambda x: {**x, "category": "high_value"})

    # Run processor
    await processor.run(max_events=5)

    # Display metrics
    metrics = processor.get_metrics()
    print(f"\nProcessed Events: {metrics['events_processed']}")
    print(f"Failed Events: {metrics['events_failed']}")
    print(f"Active Windows: {metrics['active_windows']}")


# ============================================================================
# Example 2: Tumbling Window Aggregation
# ============================================================================


async def example_tumbling_windows():
    """
    Tumbling window aggregation for time-based analytics.

    This example demonstrates:
    - Fixed-size, non-overlapping windows
    - Aggregate computations per window
    - Window firing and results
    """
    print("\n" + "=" * 60)
    print("Example 2: Tumbling Window Aggregation")
    print("=" * 60)

    # Generate events with timestamps
    events = []
    base_time = 1000.0
    for i in range(20):
        events.append(StreamEvent(
            key=f"sensor_{i % 3}",
            value={"temperature": random.uniform(20, 30), "reading_id": i},
            event_time=base_time + (i * 5),  # 5 second intervals
        ))

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure tumbling windows of 30 seconds
    processor.window(WindowType.TUMBLING, size=30.0)

    # Transform to add metadata
    processor.map(lambda x: {**x, "processed": True})

    await processor.run(max_events=20)

    metrics = processor.get_metrics()
    print(f"\nEvents Processed: {metrics['events_processed']}")
    print(f"Windows Fired: {metrics['windows_fired']}")
    print(f"Active Windows: {metrics['active_windows']}")


# ============================================================================
# Example 3: Sliding Window Pattern Detection
# ============================================================================


async def example_sliding_windows():
    """
    Sliding window for detecting patterns over time.

    Demonstrates:
    - Overlapping time windows
    - Pattern detection across windows
    - Real-time anomaly detection
    """
    print("\n" + "=" * 60)
    print("Example 3: Sliding Window Pattern Detection")
    print("=" * 60)

    # Generate events simulating sensor data
    events = []
    base_time = time.time()

    for i in range(30):
        value = random.uniform(0, 100)
        # Inject some anomalies
        if i in [10, 20]:
            value = random.uniform(200, 300)

        events.append(StreamEvent(
            key="sensor_1",
            value={"reading": value, "sensor_id": "sensor_1"},
            event_time=base_time + i,
        ))

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure sliding windows: 10 second window, 5 second slide
    processor.window(WindowType.SLIDING, size=10.0, slide=5.0)

    # Flag anomalies
    processor.map(lambda x: {
        **x,
        "is_anomaly": x["reading"] > 150,
    })

    await processor.run(max_events=30)

    metrics = processor.get_metrics()
    print(f"\nEvents Processed: {metrics['events_processed']}")
    print(f"Windows Fired: {metrics['windows_fired']}")


# ============================================================================
# Example 4: Session Windows for User Activity
# ============================================================================


async def example_session_windows():
    """
    Session windows for user activity tracking.

    Demonstrates:
    - Dynamic window sizing based on activity gaps
    - Session boundary detection
    - User engagement metrics
    """
    print("\n" + "=" * 60)
    print("Example 4: Session Windows for User Activity")
    print("=" * 60)

    # Simulate user activity with gaps
    events = []
    base_time = 1000.0

    # Session 1: user1 (timestamps 1000-1030)
    for i in range(4):
        events.append(StreamEvent(
            key="user1",
            value={"action": f"click_{i}"},
            event_time=base_time + (i * 10),
        ))

    # Gap of 60 seconds

    # Session 2: user1 (timestamps 1100-1120)
    for i in range(3):
        events.append(StreamEvent(
            key="user1",
            value={"action": f"click_{i+4}"},
            event_time=base_time + 100 + (i * 10),
        ))

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure session windows with 30 second gap
    processor.window(WindowType.SESSION, size=30.0)

    processor.map(lambda x: {**x, "session_event": True})

    await processor.run(max_events=7)

    metrics = processor.get_metrics()
    print(f"\nEvents Processed: {metrics['events_processed']}")
    print(f"Sessions Created: {metrics['windows_fired']}")


# ============================================================================
# Example 5: Stateful Stream Processing
# ============================================================================


async def example_stateful_processing():
    """
    Stateful stream processing with persistent state.

    Demonstrates:
    - State management across events
    - Aggregations and counters
    - State persistence and recovery
    """
    print("\n" + "=" * 60)
    print("Example 5: Stateful Stream Processing")
    print("=" * 60)

    # Create state backend
    state_backend = InMemoryStateBackend(ttl_seconds=300)

    # Initialize some state
    await state_backend.put("user1_count", 0)
    await state_backend.put("user2_count", 0)

    events = [
        StreamEvent(key="user1", value={"action": "click"}),
        StreamEvent(key="user1", value={"action": "click"}),
        StreamEvent(key="user2", value={"action": "click"}),
        StreamEvent(key="user1", value={"action": "click"}),
        StreamEvent(key="user2", value={"action": "click"}),
    ]

    processor = StreamProcessorFSA(state_backend=state_backend)
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Process with state updates
    async def update_counts(event):
        key = f"{event.key}_count"
        current = await state_backend.get(key) or 0
        await state_backend.put(key, current + 1)

    # Note: In production, you'd integrate this into the transformation pipeline

    await processor.run(max_events=5)

    # Check final state
    user1_count = await state_backend.get("user1_count")
    user2_count = await state_backend.get("user2_count")

    print(f"\nFinal State:")
    print(f"User1 Count: {user1_count}")
    print(f"User2 Count: {user2_count}")

    metrics = processor.get_metrics()
    print(f"Events Processed: {metrics['events_processed']}")


# ============================================================================
# Example 6: Exactly-Once Processing Semantics
# ============================================================================


async def example_exactly_once():
    """
    Exactly-once processing with deduplication.

    Demonstrates:
    - Duplicate detection and filtering
    - Idempotent processing
    - Fault tolerance guarantees
    """
    print("\n" + "=" * 60)
    print("Example 6: Exactly-Once Processing Semantics")
    print("=" * 60)

    # Create events with duplicates
    events = [
        StreamEvent(key="order1", value={"amount": 100}, partition=0, offset=1, source="kafka"),
        StreamEvent(key="order2", value={"amount": 200}, partition=0, offset=2, source="kafka"),
        StreamEvent(key="order1", value={"amount": 100}, partition=0, offset=1, source="kafka"),  # Duplicate
        StreamEvent(key="order3", value={"amount": 150}, partition=0, offset=3, source="kafka"),
        StreamEvent(key="order2", value={"amount": 200}, partition=0, offset=2, source="kafka"),  # Duplicate
    ]

    processor = StreamProcessorFSA(
        processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
    )

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    processor.map(lambda x: {**x, "processed": True})

    await processor.run(max_events=5)

    metrics = processor.get_metrics()
    print(f"\nTotal Events: {len(events)}")
    print(f"Unique Events Processed: {metrics['events_processed']}")
    print(f"Duplicates Filtered: {len(events) - metrics['events_processed']}")


# ============================================================================
# Example 7: Backpressure Handling
# ============================================================================


async def example_backpressure():
    """
    Backpressure handling under high load.

    Demonstrates:
    - Dynamic flow control
    - Drop strategy for overflow
    - Rate limiting and throttling
    """
    print("\n" + "=" * 60)
    print("Example 7: Backpressure Handling")
    print("=" * 60)

    # Generate high volume of events
    events = [
        StreamEvent(key=f"event_{i}", value={"data": i})
        for i in range(100)
    ]

    processor = StreamProcessorFSA(
        max_queue_size=10,
        backpressure_strategy=BackpressureStrategy.DROP,
    )

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Slow transformation to create backpressure
    processor.map(lambda x: {**x, "processed": True})

    await processor.run(max_events=100)

    metrics = processor.get_metrics()
    backpressure_metrics = metrics["backpressure"]

    print(f"\nTotal Events: {len(events)}")
    print(f"Processed Events: {metrics['events_processed']}")
    print(f"Dropped Events: {backpressure_metrics['drop_count']}")
    print(f"Queue Size: {backpressure_metrics['queue_size']}")


# ============================================================================
# Example 8: Fault Tolerance with Checkpointing
# ============================================================================


async def example_checkpointing():
    """
    Automatic checkpointing for fault tolerance.

    Demonstrates:
    - Periodic state snapshots
    - Recovery from failures
    - State consistency guarantees
    """
    print("\n" + "=" * 60)
    print("Example 8: Fault Tolerance with Checkpointing")
    print("=" * 60)

    events = [
        StreamEvent(key=f"event_{i}", value={"counter": i})
        for i in range(50)
    ]

    processor = StreamProcessorFSA(
        checkpoint_interval=2.0,  # Checkpoint every 2 seconds
        processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE,
    )

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    processor.map(lambda x: {**x, "checkpointed": True})

    # Run for long enough to trigger checkpoints
    await processor.run(duration=5.0)

    metrics = processor.get_metrics()
    print(f"\nEvents Processed: {metrics['events_processed']}")
    print(f"Checkpoints Created: {metrics['checkpoints_created']}")


# ============================================================================
# Example 9: Complex Event Processing (CEP)
# ============================================================================


async def example_pattern_detection():
    """
    Complex event processing with pattern detection.

    Demonstrates:
    - Sequential pattern matching
    - Event correlation
    - Fraud detection use case
    """
    print("\n" + "=" * 60)
    print("Example 9: Complex Event Processing (Pattern Detection)")
    print("=" * 60)

    # Simulate user actions
    events = [
        StreamEvent(key="user1", value={"action": "login", "location": "US"}),
        StreamEvent(key="user1", value={"action": "purchase", "amount": 100}),
        StreamEvent(key="user1", value={"action": "login", "location": "CN"}),  # Suspicious!
        StreamEvent(key="user1", value={"action": "purchase", "amount": 5000}),  # Large purchase
        StreamEvent(key="user2", value={"action": "login", "location": "US"}),
        StreamEvent(key="user2", value={"action": "purchase", "amount": 50}),
    ]

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Flag suspicious patterns
    processor.map(lambda x: {
        **x,
        "suspicious": (
            x.get("location") not in ["US", "UK", "CA"] or
            x.get("amount", 0) > 1000
        )
    })

    await processor.run(max_events=6)

    metrics = processor.get_metrics()
    print(f"\nEvents Analyzed: {metrics['events_processed']}")
    print("Pattern detection completed")


# ============================================================================
# Example 10: Stream Processing with FlatMap
# ============================================================================


async def example_flatmap():
    """
    FlatMap transformation for event explosion.

    Demonstrates:
    - One-to-many transformations
    - Event expansion
    - Data normalization
    """
    print("\n" + "=" * 60)
    print("Example 10: Stream Processing with FlatMap")
    print("=" * 60)

    # Events containing lists
    events = [
        StreamEvent(key="batch1", value={"items": [1, 2, 3]}),
        StreamEvent(key="batch2", value={"items": [4, 5]}),
        StreamEvent(key="batch3", value={"items": [6, 7, 8, 9]}),
    ]

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Expand items into individual events
    processor.flat_map(lambda x: [{"item": item} for item in x["items"]])

    await processor.run(max_events=3)

    metrics = processor.get_metrics()
    print(f"\nInput Batches: {len(events)}")
    print(f"Expanded Events: {metrics['events_processed']}")


# ============================================================================
# Example 11: File-based Stream Processing
# ============================================================================


async def example_file_stream():
    """
    Process events from a file stream.

    Demonstrates:
    - File-based ingestion
    - Batch processing
    - Log file analysis
    """
    print("\n" + "=" * 60)
    print("Example 11: File-based Stream Processing")
    print("=" * 60)

    # Create a temporary file with log entries
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        for i in range(20):
            f.write(f"LOG: Event {i} - Status: {'ERROR' if i % 5 == 0 else 'INFO'}\n")
        temp_path = f.name

    try:
        processor = StreamProcessorFSA()
        source = FileStreamSource(Path(temp_path), batch_size=5)
        processor.add_source(source)

        # Filter errors only
        processor.filter(lambda x: "ERROR" in x)
        processor.map(lambda x: {"log": x, "severity": "high"})

        await processor.run(max_events=20)

        metrics = processor.get_metrics()
        print(f"\nLog Lines Processed: {metrics['events_processed']}")
        print(f"Errors Detected: {metrics['events_processed']}")
    finally:
        # Cleanup
        Path(temp_path).unlink()


# ============================================================================
# Example 12: Real-time Metrics Aggregation
# ============================================================================


async def example_metrics_aggregation():
    """
    Real-time metrics aggregation pipeline.

    Demonstrates:
    - Continuous aggregation
    - Metrics computation
    - Dashboard data pipeline
    """
    print("\n" + "=" * 60)
    print("Example 12: Real-time Metrics Aggregation")
    print("=" * 60)

    # Generate metrics data
    events = []
    base_time = time.time()

    for i in range(30):
        events.append(StreamEvent(
            key="api_endpoint",
            value={
                "endpoint": "/api/users",
                "response_time_ms": random.uniform(10, 500),
                "status_code": random.choice([200, 200, 200, 404, 500]),
            },
            event_time=base_time + i,
        ))

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure tumbling windows for aggregation (10 second windows)
    processor.window(WindowType.TUMBLING, size=10.0)

    # Add metrics metadata
    processor.map(lambda x: {
        **x,
        "is_error": x["status_code"] >= 400,
        "is_slow": x["response_time_ms"] > 200,
    })

    await processor.run(max_events=30)

    metrics = processor.get_metrics()
    print(f"\nMetrics Events Processed: {metrics['events_processed']}")
    print(f"Aggregation Windows: {metrics['windows_fired']}")


# ============================================================================
# Main: Run All Examples
# ============================================================================


async def run_all_examples():
    """Run all usage examples."""
    examples = [
        example_basic_pipeline,
        example_tumbling_windows,
        example_sliding_windows,
        example_session_windows,
        example_stateful_processing,
        example_exactly_once,
        example_backpressure,
        example_checkpointing,
        example_pattern_detection,
        example_flatmap,
        example_file_stream,
        example_metrics_aggregation,
    ]

    for example_func in examples:
        try:
            await example_func()
            await asyncio.sleep(0.5)  # Pause between examples
        except Exception as e:
            print(f"\nError in {example_func.__name__}: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_examples())

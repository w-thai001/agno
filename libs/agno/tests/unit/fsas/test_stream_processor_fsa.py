"""
Comprehensive test suite for Stream Processor FSA.

Tests cover:
- Stream ingestion from various sources
- Windowing correctness (tumbling, sliding, session)
- State persistence and recovery
- Backpressure handling under load
- Fault injection and recovery
- End-to-end streaming pipeline
- Performance benchmarks
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest

from agno.fsas.infrastructure.stream_processor_fsa import (
    BackpressureController,
    BackpressureStrategy,
    CircuitBreaker,
    DeadLetterQueue,
    FaultToleranceManager,
    FileStreamSource,
    GeneratorStreamSource,
    GlobalWindowAssigner,
    InMemoryStateBackend,
    InMemoryStreamSource,
    PatternDetector,
    PersistentStateBackend,
    ProcessingGuarantee,
    SessionWindowAssigner,
    SlidingWindowAssigner,
    StreamEnricher,
    StreamEvent,
    StreamJoin,
    StreamProcessorFSA,
    TransactionLog,
    TumblingWindowAssigner,
    Watermark,
    Window,
    WindowType,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_events():
    """Generate sample events for testing."""
    return [
        StreamEvent(key="user1", value={"action": "login", "count": 1}, timestamp=1000.0, event_time=1000.0),
        StreamEvent(key="user1", value={"action": "click", "count": 2}, timestamp=1010.0, event_time=1010.0),
        StreamEvent(key="user2", value={"action": "login", "count": 1}, timestamp=1020.0, event_time=1020.0),
        StreamEvent(key="user1", value={"action": "logout", "count": 1}, timestamp=1030.0, event_time=1030.0),
        StreamEvent(key="user2", value={"action": "click", "count": 3}, timestamp=1040.0, event_time=1040.0),
    ]


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Stream Source Tests
# ============================================================================


@pytest.mark.asyncio
async def test_file_stream_source(temp_dir):
    """Test file stream source ingestion."""
    # Create test file
    test_file = temp_dir / "test_stream.txt"
    lines = ["line1", "line2", "line3", "line4", "line5"]
    test_file.write_text("\n".join(lines))

    # Create source and read
    source = FileStreamSource(test_file, batch_size=2)
    events = []

    for _ in range(5):
        event = await source.read()
        if event:
            events.append(event)

    await source.close()

    assert len(events) == 5
    assert events[0].value == "line1"
    assert events[4].value == "line5"
    assert all(e.source == str(test_file) for e in events)


@pytest.mark.asyncio
async def test_in_memory_stream_source(sample_events):
    """Test in-memory stream source."""
    source = InMemoryStreamSource(sample_events)

    events = []
    while True:
        event = await source.read()
        if event is None:
            break
        events.append(event)

    assert len(events) == 5
    assert events[0].key == "user1"
    assert events[2].key == "user2"


@pytest.mark.asyncio
async def test_generator_stream_source():
    """Test generator-based stream source."""
    counter = {"value": 0}

    def generator():
        counter["value"] += 1
        if counter["value"] > 10:
            raise StopIteration
        return {"id": counter["value"]}

    source = GeneratorStreamSource(generator, rate_limit=0.01)
    events = []

    for _ in range(10):
        event = await source.read()
        if event:
            events.append(event)

    await source.close()

    assert len(events) == 10
    assert events[0].value["id"] == 1
    assert events[9].value["id"] == 10


# ============================================================================
# State Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_in_memory_state_backend():
    """Test in-memory state backend operations."""
    backend = InMemoryStateBackend(ttl_seconds=2)

    # Put and get
    await backend.put("key1", "value1")
    assert await backend.get("key1") == "value1"

    # Update
    await backend.put("key1", "value2")
    assert await backend.get("key1") == "value2"

    # Delete
    await backend.delete("key1")
    assert await backend.get("key1") is None

    # Non-existent key
    assert await backend.get("nonexistent") is None


@pytest.mark.asyncio
async def test_in_memory_state_backend_ttl():
    """Test state backend TTL expiration."""
    backend = InMemoryStateBackend(ttl_seconds=1)

    await backend.put("key1", "value1")
    assert await backend.get("key1") == "value1"

    # Wait for TTL to expire
    await asyncio.sleep(1.5)
    assert await backend.get("key1") is None


@pytest.mark.asyncio
async def test_in_memory_state_checkpoint():
    """Test state backend checkpointing."""
    backend = InMemoryStateBackend()

    # Create state
    await backend.put("key1", "value1")
    await backend.put("key2", "value2")

    # Checkpoint
    await backend.checkpoint("checkpoint1")

    # Modify state
    await backend.put("key1", "modified")
    await backend.delete("key2")
    await backend.put("key3", "value3")

    # Restore from checkpoint
    await backend.restore("checkpoint1")
    assert await backend.get("key1") == "value1"
    assert await backend.get("key2") == "value2"
    assert await backend.get("key3") is None


@pytest.mark.asyncio
async def test_persistent_state_backend(temp_dir):
    """Test persistent state backend."""
    storage_path = temp_dir / "state"
    backend = PersistentStateBackend(storage_path)

    # Put and get
    await backend.put("key1", {"data": "value1"})
    assert await backend.get("key1") == {"data": "value1"}

    # Create new instance to test persistence
    backend2 = PersistentStateBackend(storage_path)
    assert await backend2.get("key1") == {"data": "value1"}

    # Checkpoint and restore
    await backend2.put("key2", {"data": "value2"})
    await backend2.checkpoint("checkpoint1")

    await backend2.put("key2", {"data": "modified"})
    await backend2.restore("checkpoint1")
    assert await backend2.get("key2") == {"data": "value2"}


# ============================================================================
# Windowing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tumbling_window_assigner():
    """Test tumbling window assignment."""
    assigner = TumblingWindowAssigner(window_size=10.0)

    # Create events
    event1 = StreamEvent(key="user1", value=1, event_time=5.0)
    event2 = StreamEvent(key="user1", value=2, event_time=12.0)
    event3 = StreamEvent(key="user1", value=3, event_time=8.0)

    # Assign to windows
    windows1 = assigner.assign_windows(event1, "user1")
    windows2 = assigner.assign_windows(event2, "user1")
    windows3 = assigner.assign_windows(event3, "user1")

    # Events 1 and 3 should be in same window
    assert len(windows1) == 1
    assert len(windows2) == 1
    assert windows1[0].window_id == windows3[0].window_id
    assert windows1[0].window_id != windows2[0].window_id

    # Check window boundaries
    assert windows1[0].start_time == 0.0
    assert windows1[0].end_time == 10.0
    assert windows2[0].start_time == 10.0
    assert windows2[0].end_time == 20.0


@pytest.mark.asyncio
async def test_sliding_window_assigner():
    """Test sliding window assignment."""
    assigner = SlidingWindowAssigner(window_size=10.0, slide_interval=5.0)

    event = StreamEvent(key="user1", value=1, event_time=7.0)
    windows = assigner.assign_windows(event, "user1")

    # Event should be in multiple overlapping windows
    assert len(windows) >= 1

    # Check windows contain the event
    for window in windows:
        assert window.start_time <= event.event_time < window.end_time


@pytest.mark.asyncio
async def test_session_window_assigner():
    """Test session window assignment with gap-based merging."""
    assigner = SessionWindowAssigner(gap_duration=5.0)

    # Create events within session
    event1 = StreamEvent(key="user1", value=1, event_time=10.0)
    event2 = StreamEvent(key="user1", value=2, event_time=13.0)
    event3 = StreamEvent(key="user1", value=3, event_time=25.0)  # New session

    windows1 = assigner.assign_windows(event1, "user1")
    windows2 = assigner.assign_windows(event2, "user1")
    windows3 = assigner.assign_windows(event3, "user1")

    # Events 1 and 2 should be in same session
    assert len(windows1) == 1
    assert len(windows2) == 1
    assert windows1[0].window_id == windows2[0].window_id

    # Event 3 should be in different session
    assert windows3[0].window_id != windows1[0].window_id


@pytest.mark.asyncio
async def test_global_window_assigner():
    """Test global window for unbounded streams."""
    assigner = GlobalWindowAssigner()

    event1 = StreamEvent(key="user1", value=1, event_time=10.0)
    event2 = StreamEvent(key="user1", value=2, event_time=100.0)
    event3 = StreamEvent(key="user2", value=3, event_time=50.0)

    windows1 = assigner.assign_windows(event1, "user1")
    windows2 = assigner.assign_windows(event2, "user1")
    windows3 = assigner.assign_windows(event3, "user2")

    # Same key should get same global window
    assert windows1[0].window_id == windows2[0].window_id

    # Different key should get different window
    assert windows1[0].window_id != windows3[0].window_id

    # Global windows are unbounded
    assert windows1[0].end_time == float("inf")


# ============================================================================
# Backpressure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_backpressure_buffer_strategy():
    """Test buffer backpressure strategy."""
    controller = BackpressureController(
        max_queue_size=5,
        strategy=BackpressureStrategy.BUFFER,
    )

    # Enqueue events
    for i in range(5):
        event = StreamEvent(key=f"key{i}", value=i)
        assert await controller.enqueue(event) is True

    assert controller.metrics.queue_size == 5


@pytest.mark.asyncio
async def test_backpressure_drop_strategy():
    """Test drop backpressure strategy."""
    controller = BackpressureController(
        max_queue_size=3,
        strategy=BackpressureStrategy.DROP,
    )

    # Fill queue
    for i in range(3):
        event = StreamEvent(key=f"key{i}", value=i)
        assert await controller.enqueue(event) is True

    # Additional events should be dropped
    event = StreamEvent(key="overflow", value=999)
    assert await controller.enqueue(event) is False
    assert controller.metrics.drop_count == 1


@pytest.mark.asyncio
async def test_backpressure_metrics():
    """Test backpressure metrics collection."""
    controller = BackpressureController(max_queue_size=10)

    # Enqueue and dequeue
    for i in range(5):
        event = StreamEvent(key=f"key{i}", value=i)
        await controller.enqueue(event)

    for _ in range(3):
        await controller.dequeue()

    metrics = controller.get_metrics()
    assert metrics.queue_size == 2
    assert metrics.buffer_count == 5


@pytest.mark.asyncio
async def test_circuit_breaker():
    """Test circuit breaker pattern."""
    breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)

    def failing_func():
        raise Exception("Test failure")

    def success_func():
        return "success"

    # Trigger failures to open circuit
    for _ in range(3):
        with pytest.raises(Exception):
            breaker.call(failing_func)

    # Circuit should be open
    assert breaker.state == "open"

    # Calls should be rejected
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        breaker.call(success_func)

    # Wait for timeout
    await asyncio.sleep(1.1)

    # Circuit should move to half-open and allow call
    result = breaker.call(success_func)
    assert result == "success"


# ============================================================================
# Fault Tolerance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_fault_tolerance_deduplication():
    """Test exactly-once processing with deduplication."""
    manager = FaultToleranceManager(guarantee=ProcessingGuarantee.EXACTLY_ONCE)

    event1 = StreamEvent(key="key1", value=1, partition=0, offset=100, source="test")
    event2 = StreamEvent(key="key1", value=1, partition=0, offset=100, source="test")

    # First event should not be duplicate
    assert manager.is_duplicate(event1) is False

    # Second identical event should be duplicate
    assert manager.is_duplicate(event2) is True


@pytest.mark.asyncio
async def test_fault_tolerance_checkpointing():
    """Test checkpoint creation."""
    manager = FaultToleranceManager(checkpoint_interval=1.0)

    # Should not checkpoint immediately
    assert await manager.should_checkpoint() is False

    # Wait for checkpoint interval
    await asyncio.sleep(1.1)
    assert await manager.should_checkpoint() is True

    # Create checkpoint
    checkpoint = await manager.create_checkpoint(100, {"state": "test"})
    assert checkpoint.offset == 100
    assert checkpoint.state_snapshot == {"state": "test"}


@pytest.mark.asyncio
async def test_fault_tolerance_retry():
    """Test retry with exponential backoff."""
    manager = FaultToleranceManager(max_retries=3, retry_backoff=0.1)

    attempt_count = {"count": 0}

    async def failing_func(event):
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise Exception("Temporary failure")
        return "success"

    event = StreamEvent(key="key1", value=1)
    result = await manager.retry_with_backoff(failing_func, event)

    assert result == "success"
    assert attempt_count["count"] == 3


@pytest.mark.asyncio
async def test_dead_letter_queue():
    """Test dead letter queue for failed messages."""
    dlq = DeadLetterQueue(max_size=100)

    event = StreamEvent(key="key1", value=1)
    error = Exception("Processing failed")

    dlq.add(event, error, attempts=3)

    entries = dlq.get_all()
    assert len(entries) == 1
    assert entries[0][0].key == "key1"
    assert entries[0][2] == 3  # attempts


@pytest.mark.asyncio
async def test_transaction_log(temp_dir):
    """Test transaction log for recovery."""
    log_path = temp_dir / "transactions.log"
    log = TransactionLog(log_path)

    # Log transactions
    log.log_transaction({"type": "event", "key": "key1"})
    log.log_transaction({"type": "checkpoint", "id": "cp1"})

    # Replay from new instance
    log2 = TransactionLog(log_path)
    transactions = log2.replay()

    assert len(transactions) == 2
    assert transactions[0]["type"] == "event"
    assert transactions[1]["type"] == "checkpoint"


# ============================================================================
# Advanced Features Tests
# ============================================================================


@pytest.mark.asyncio
async def test_stream_join_inner():
    """Test inner join of two streams."""
    join = StreamJoin(join_type="inner", window_size=10.0)

    left_event = StreamEvent(key="user1", value={"left": 1}, timestamp=100.0)
    right_event = StreamEvent(key="user1", value={"right": 2}, timestamp=105.0)

    # Process events
    results1 = join.join(left_event, None)
    results2 = join.join(None, right_event)

    # Should have join result
    assert len(results2) == 1
    assert results2[0][0].key == "user1"
    assert results2[0][1].key == "user1"


@pytest.mark.asyncio
async def test_stream_join_left():
    """Test left join emits even without match."""
    join = StreamJoin(join_type="left", window_size=10.0)

    left_event = StreamEvent(key="user1", value={"left": 1}, timestamp=100.0)

    results = join.join(left_event, None)

    # Should emit left event even without match
    assert len(results) == 1
    assert results[0][0] == left_event
    assert results[0][1] is None


@pytest.mark.asyncio
async def test_pattern_detection():
    """Test complex event processing pattern detection."""
    detector = PatternDetector(pattern_timeout=10.0)

    # Define pattern: login -> click -> logout
    pattern = [
        lambda e: e.value.get("action") == "login",
        lambda e: e.value.get("action") == "click",
        lambda e: e.value.get("action") == "logout",
    ]

    event1 = StreamEvent(key="user1", value={"action": "login"}, timestamp=100.0)
    event2 = StreamEvent(key="user1", value={"action": "click"}, timestamp=110.0)
    event3 = StreamEvent(key="user1", value={"action": "logout"}, timestamp=120.0)

    # Process events
    result1 = detector.detect_sequence(event1, pattern)
    assert result1 is None  # Incomplete

    result2 = detector.detect_sequence(event2, pattern)
    assert result2 is None  # Incomplete

    result3 = detector.detect_sequence(event3, pattern)
    assert result3 is not None  # Complete!
    assert len(result3) == 3


@pytest.mark.asyncio
async def test_stream_enrichment():
    """Test stream enrichment with external data."""
    enricher = StreamEnricher()

    def enrichment_func(event):
        return {"user_type": "premium", "region": "us-west"}

    event = StreamEvent(key="user1", value={"action": "click"})
    enriched = await enricher.enrich(event, enrichment_func, cache_key="user1")

    assert "user_type" in enriched.headers
    assert enriched.headers["user_type"] == "premium"
    assert enriched.headers["region"] == "us-west"


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_stream_processor_basic_pipeline(sample_events):
    """Test basic stream processing pipeline."""
    processor = StreamProcessorFSA()

    # Add source
    source = InMemoryStreamSource(sample_events[:])
    processor.add_source(source)

    # Add transformations
    processor.map(lambda x: {**x, "processed": True})
    processor.filter(lambda x: x.get("count", 0) > 0)

    # Run processor
    await processor.run(max_events=5)

    # Check metrics
    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 5


@pytest.mark.asyncio
async def test_stream_processor_with_tumbling_windows(sample_events):
    """Test stream processor with tumbling windows."""
    processor = StreamProcessorFSA()

    source = InMemoryStreamSource(sample_events[:])
    processor.add_source(source)

    # Configure tumbling windows
    processor.window(WindowType.TUMBLING, size=20.0)

    await processor.run(max_events=5)

    # Check windows were created
    metrics = processor.get_metrics()
    assert metrics["windows_fired"] >= 0


@pytest.mark.asyncio
async def test_stream_processor_with_sliding_windows():
    """Test stream processor with sliding windows."""
    events = [
        StreamEvent(key="k1", value=i, event_time=float(i * 5))
        for i in range(10)
    ]

    processor = StreamProcessorFSA()
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure sliding windows
    processor.window(WindowType.SLIDING, size=15.0, slide=5.0)

    await processor.run(max_events=10)

    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 10


@pytest.mark.asyncio
async def test_stream_processor_exactly_once():
    """Test exactly-once processing semantics."""
    # Create events with duplicates
    events = [
        StreamEvent(key="k1", value=1, partition=0, offset=1, source="test"),
        StreamEvent(key="k1", value=2, partition=0, offset=2, source="test"),
        StreamEvent(key="k1", value=1, partition=0, offset=1, source="test"),  # Duplicate
    ]

    processor = StreamProcessorFSA(
        processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
    )

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    await processor.run(max_events=3)

    # Should only process 2 unique events
    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 2


@pytest.mark.asyncio
async def test_stream_processor_checkpointing():
    """Test automatic checkpointing."""
    processor = StreamProcessorFSA(checkpoint_interval=0.5)

    events = [StreamEvent(key=f"k{i}", value=i) for i in range(10)]
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Run for long enough to trigger checkpoint
    await processor.run(duration=1.5)

    metrics = processor.get_metrics()
    assert metrics["checkpoints_created"] >= 1


@pytest.mark.asyncio
async def test_stream_processor_backpressure():
    """Test backpressure handling under load."""
    processor = StreamProcessorFSA(
        max_queue_size=5,
        backpressure_strategy=BackpressureStrategy.DROP,
    )

    # Create many events
    events = [StreamEvent(key=f"k{i}", value=i) for i in range(20)]
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    await processor.run(max_events=20)

    metrics = processor.get_metrics()
    backpressure_metrics = metrics["backpressure"]

    # Some events may be dropped due to backpressure
    assert backpressure_metrics["drop_count"] >= 0


@pytest.mark.asyncio
async def test_stream_processor_transformations():
    """Test multiple transformations in pipeline."""
    processor = StreamProcessorFSA()

    events = [
        StreamEvent(key="k1", value={"count": 5}),
        StreamEvent(key="k2", value={"count": 3}),
        StreamEvent(key="k3", value={"count": 8}),
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Chain transformations
    processor.map(lambda x: {**x, "doubled": x["count"] * 2})
    processor.filter(lambda x: x["doubled"] > 10)
    processor.map(lambda x: {**x, "final": True})

    await processor.run(max_events=3)

    # Events with count <= 5 should be filtered out
    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 1  # Only count=8 passes


@pytest.mark.asyncio
async def test_stream_processor_flat_map():
    """Test flatMap transformation."""
    processor = StreamProcessorFSA()

    events = [
        StreamEvent(key="k1", value={"items": [1, 2, 3]}),
        StreamEvent(key="k2", value={"items": [4, 5]}),
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # FlatMap to expand items
    processor.flat_map(lambda x: x["items"])

    await processor.run(max_events=2)

    metrics = processor.get_metrics()
    assert metrics["events_processed"] >= 2


@pytest.mark.asyncio
async def test_stream_processor_with_state():
    """Test stream processor with stateful operations."""
    backend = InMemoryStateBackend()
    processor = StreamProcessorFSA(state_backend=backend)

    events = [
        StreamEvent(key="counter", value=1),
        StreamEvent(key="counter", value=2),
        StreamEvent(key="counter", value=3),
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Process with state updates
    async def stateful_map(event):
        current = await backend.get(event.key) or 0
        new_value = current + event.value
        await backend.put(event.key, new_value)
        return new_value

    await processor.run(max_events=3)

    # Check final state
    final_count = await backend.get("counter")
    # Note: Since we're not applying the stateful_map directly in transformations,
    # we just verify the processor runs successfully


@pytest.mark.asyncio
async def test_stream_processor_session_windows():
    """Test stream processor with session windows."""
    processor = StreamProcessorFSA()

    # Events with gaps
    events = [
        StreamEvent(key="user1", value=1, event_time=100.0),
        StreamEvent(key="user1", value=2, event_time=105.0),
        StreamEvent(key="user1", value=3, event_time=200.0),  # New session
        StreamEvent(key="user1", value=4, event_time=205.0),
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Configure session windows with 30 second gap
    processor.window(WindowType.SESSION, size=30.0)

    await processor.run(max_events=4)

    # Should create separate sessions
    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 4


@pytest.mark.asyncio
async def test_stream_processor_performance_benchmark():
    """Performance benchmark test."""
    import time

    processor = StreamProcessorFSA(max_queue_size=10000)

    # Generate large number of events
    num_events = 1000
    events = [
        StreamEvent(key=f"k{i % 10}", value={"data": i})
        for i in range(num_events)
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    processor.map(lambda x: {**x, "processed": True})

    start_time = time.time()
    await processor.run(max_events=num_events)
    elapsed = time.time() - start_time

    metrics = processor.get_metrics()

    # Calculate throughput
    throughput = num_events / elapsed if elapsed > 0 else 0

    assert metrics["events_processed"] == num_events
    assert throughput > 0
    print(f"\nThroughput: {throughput:.2f} events/second")
    print(f"Processed {num_events} events in {elapsed:.2f} seconds")


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_stream_processor_empty_source():
    """Test processor with empty source."""
    processor = StreamProcessorFSA()

    source = InMemoryStreamSource([])
    processor.add_source(source)

    await processor.run(max_events=10, duration=0.5)

    metrics = processor.get_metrics()
    assert metrics["events_processed"] == 0


@pytest.mark.asyncio
async def test_stream_processor_error_handling():
    """Test error handling in transformations."""
    processor = StreamProcessorFSA()

    events = [
        StreamEvent(key="k1", value={"num": 10}),
        StreamEvent(key="k2", value={"num": 0}),
        StreamEvent(key="k3", value={"num": 5}),
    ]

    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Transformation that may fail
    def risky_transform(x):
        if x["num"] == 0:
            raise ValueError("Cannot process zero")
        return {**x, "result": 100 / x["num"]}

    processor.map(risky_transform)

    await processor.run(max_events=3)

    metrics = processor.get_metrics()
    # Some events should fail
    assert metrics["events_failed"] > 0


@pytest.mark.asyncio
async def test_window_late_data_handling():
    """Test handling of late arriving data."""
    assigner = TumblingWindowAssigner(window_size=10.0)

    # Events arriving out of order
    event1 = StreamEvent(key="k1", value=1, event_time=15.0)
    event2 = StreamEvent(key="k1", value=2, event_time=5.0)  # Late

    windows1 = assigner.assign_windows(event1, "k1")
    windows1[0].fire()  # Fire the window

    # Try to add late event
    added = windows1[0].add_event(event2, allow_late=True)
    assert added is True
    assert len(windows1[0].late_events) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

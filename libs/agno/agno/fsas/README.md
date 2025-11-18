# Stream Processor FSA

A production-grade stream processing Finite State Automaton (FSA) for real-time data processing with advanced features including windowing, state management, backpressure handling, and fault tolerance.

## Features

### Core Stream Processing Engine
- **Multi-source ingestion**: Kafka, Kinesis, WebSocket, files, and custom sources
- **Event-driven pipeline architecture**: Efficient async processing
- **Stateful transformations**: map, filter, flatMap, reduce operations
- **Stream partitioning**: Parallel processing with key-based partitioning
- **Watermark-based event time processing**: Handle event time semantics
- **Late data handling**: Manage out-of-order events

### Windowing Operations
- **Tumbling Windows**: Fixed-size, non-overlapping time windows
- **Sliding Windows**: Fixed-size, overlapping windows for continuous analysis
- **Session Windows**: Dynamic windows based on activity gaps
- **Global Windows**: Unbounded streams for stateful operations
- **Custom Triggers**: Time-based, count-based, or custom predicates
- **Late Data Support**: Handle events arriving after window closure

### State Management
- **In-memory State Store**: High-performance with optional TTL
- **Persistent State Backend**: RocksDB-style durable storage
- **Checkpointing**: Automatic state snapshots for recovery
- **State Recovery**: Restore from checkpoints after failures
- **State Expiration**: Automatic cleanup with TTL
- **State Versioning**: Migration support for schema evolution

### Backpressure & Flow Control
- **Dynamic Buffer Sizing**: Adapt to throughput variations
- **Rate Limiting**: Control processing rate
- **Circuit Breaker**: Handle downstream failures gracefully
- **Adaptive Batching**: Optimize throughput vs latency
- **Overflow Strategies**: Drop, buffer, block, or sample
- **Metrics-driven**: Monitor and respond to load

### Fault Tolerance
- **Exactly-Once Semantics**: Guaranteed processing with deduplication
- **At-Least-Once**: Reliable delivery with retries
- **Checkpointing**: Snapshot isolation for recovery
- **Exponential Backoff**: Intelligent retry logic
- **Dead Letter Queue**: Handle poison messages
- **Transaction Log**: Audit trail for recovery

### Advanced Features
- **Stream Joins**: Inner, left, and outer joins with windowing
- **Pattern Detection**: Complex Event Processing (CEP) for sequences
- **Stream Enrichment**: Add external data with caching
- **Schema Evolution**: Handle dynamic schemas
- **Multi-tenancy**: Resource isolation per tenant
- **A/B Testing**: Support for multiple processing logic versions

## Installation

```bash
pip install agno
```

## Quick Start

```python
import asyncio
from agno.fsas import StreamProcessorFSA, StreamEvent, WindowType

async def main():
    # Create processor
    processor = StreamProcessorFSA()

    # Add events
    events = [
        StreamEvent(key="user1", value={"action": "click", "count": 1}),
        StreamEvent(key="user2", value={"action": "purchase", "count": 5}),
    ]

    from agno.fsas.infrastructure.stream_processor_fsa import InMemoryStreamSource
    source = InMemoryStreamSource(events)
    processor.add_source(source)

    # Apply transformations
    processor.map(lambda x: {**x, "processed": True})
    processor.filter(lambda x: x["count"] > 0)

    # Run processor
    await processor.run(max_events=2)

    # Get metrics
    metrics = processor.get_metrics()
    print(f"Processed: {metrics['events_processed']} events")

asyncio.run(main())
```

## Usage Examples

### Tumbling Windows

```python
processor = StreamProcessorFSA()
processor.add_source(source)

# 60-second tumbling windows
processor.window(WindowType.TUMBLING, size=60.0)

await processor.run()
```

### Sliding Windows

```python
# 60-second windows, sliding every 30 seconds
processor.window(WindowType.SLIDING, size=60.0, slide=30.0)
```

### Session Windows

```python
# Session windows with 30-second timeout
processor.window(WindowType.SESSION, size=30.0)
```

### Exactly-Once Processing

```python
from agno.fsas.infrastructure.stream_processor_fsa import ProcessingGuarantee

processor = StreamProcessorFSA(
    processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
)
```

### Stateful Processing

```python
from agno.fsas.infrastructure.stream_processor_fsa import InMemoryStateBackend

state_backend = InMemoryStateBackend(ttl_seconds=3600)
processor = StreamProcessorFSA(state_backend=state_backend)

# Use state in processing
await state_backend.put("counter", 0)
counter = await state_backend.get("counter")
```

### Backpressure Handling

```python
from agno.fsas.infrastructure.stream_processor_fsa import BackpressureStrategy

processor = StreamProcessorFSA(
    max_queue_size=1000,
    backpressure_strategy=BackpressureStrategy.DROP
)
```

### Fault Tolerance with Checkpointing

```python
processor = StreamProcessorFSA(
    checkpoint_interval=60.0,  # Checkpoint every 60 seconds
    processing_guarantee=ProcessingGuarantee.EXACTLY_ONCE
)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Stream Processor FSA                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌───────────────┐                   │
│  │   Sources    │─────▶│  Ingestion    │                   │
│  │ Kafka/Files  │      │  & Buffering  │                   │
│  └──────────────┘      └───────┬───────┘                   │
│                                  │                            │
│                         ┌────────▼────────┐                 │
│                         │ Transformations │                 │
│                         │  map/filter/etc │                 │
│                         └────────┬────────┘                 │
│                                  │                            │
│         ┌────────────────────────┼────────────────────┐     │
│         │                        │                    │     │
│  ┌──────▼──────┐        ┌───────▼────────┐   ┌──────▼───┐ │
│  │  Windowing  │        │ State Manager  │   │ Backpres.│ │
│  │  Tumbling   │        │  Checkpoints   │   │ Control  │ │
│  │  Sliding    │        │   Recovery     │   │          │ │
│  │  Session    │        │                │   │          │ │
│  └─────────────┘        └────────────────┘   └──────────┘ │
│         │                        │                    │     │
│         └────────────────────────┼────────────────────┘     │
│                                  │                            │
│                         ┌────────▼────────┐                 │
│                         │ Fault Tolerance │                 │
│                         │  DLQ / Retries  │                 │
│                         └────────┬────────┘                 │
│                                  │                            │
│                         ┌────────▼────────┐                 │
│                         │     Output      │                 │
│                         │  Sinks/Results  │                 │
│                         └─────────────────┘                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Performance

The Stream Processor FSA is designed for high-throughput, low-latency stream processing:

- **Throughput**: 10,000+ events/second (depending on transformations)
- **Latency**: Sub-millisecond processing per event
- **Memory**: Efficient windowing with automatic cleanup
- **Scalability**: Horizontal scaling via partitioning

## Testing

Run the comprehensive test suite:

```bash
pytest libs/agno/tests/unit/fsas/test_stream_processor_fsa.py -v
```

Run specific tests:

```bash
# Test windowing
pytest libs/agno/tests/unit/fsas/test_stream_processor_fsa.py::test_tumbling_window_assigner -v

# Test fault tolerance
pytest libs/agno/tests/unit/fsas/test_stream_processor_fsa.py::test_fault_tolerance_retry -v

# Test backpressure
pytest libs/agno/tests/unit/fsas/test_stream_processor_fsa.py::test_backpressure_drop_strategy -v
```

## Examples

Run all usage examples:

```bash
python libs/agno/agno/fsas/infrastructure/stream_processor_examples.py
```

## API Reference

### StreamProcessorFSA

Main stream processor class.

**Constructor Parameters:**
- `state_backend`: State backend for stateful operations (default: InMemoryStateBackend)
- `processing_guarantee`: Processing semantics (AT_MOST_ONCE, AT_LEAST_ONCE, EXACTLY_ONCE)
- `checkpoint_interval`: Seconds between checkpoints (default: 60.0)
- `max_queue_size`: Maximum queue size for backpressure (default: 1000)
- `backpressure_strategy`: Strategy for handling overflow (DROP, BUFFER, BLOCK, SAMPLE)

**Methods:**
- `add_source(source)`: Add a stream source
- `map(func)`: Apply map transformation
- `filter(predicate)`: Apply filter transformation
- `flat_map(func)`: Apply flatMap transformation
- `key_by(key_func)`: Partition stream by key
- `window(window_type, size, slide)`: Configure windowing
- `join(other_stream, join_type, window_size)`: Configure stream join
- `run(max_events, duration)`: Run the processor
- `get_metrics()`: Get processing metrics

### StreamEvent

Represents a single event in the stream.

**Attributes:**
- `key`: Event key for partitioning
- `value`: Event payload
- `timestamp`: Processing time timestamp
- `event_time`: Event time timestamp
- `partition`: Partition number
- `offset`: Event offset
- `headers`: Additional metadata
- `source`: Source identifier

### WindowType

Enumeration of window types:
- `TUMBLING`: Fixed-size, non-overlapping windows
- `SLIDING`: Fixed-size, overlapping windows
- `SESSION`: Dynamic windows based on gaps
- `GLOBAL`: Unbounded global window

### ProcessingGuarantee

Processing guarantee semantics:
- `AT_MOST_ONCE`: Fast, may lose events
- `AT_LEAST_ONCE`: Reliable, may duplicate
- `EXACTLY_ONCE`: Guaranteed once, with deduplication

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code follows PEP 8 style guide
3. New features include tests
4. Documentation is updated

## License

MIT License - see LICENSE file for details

# Batch Processor FSA - Usage Guide

## Overview

The Batch Processor FSA is a production-grade framework for handling large-scale batch operations with intelligent scheduling, resource management, parallel execution, fault tolerance, and comprehensive monitoring.

## Quick Start

### Basic Usage

```python
from agno.fsas import BatchProcessorFSA, BatchConfig, Priority

# Create configuration
config = BatchConfig(
    batch_size=100,
    max_workers=4,
    processing_strategy="parallel",
    enable_checkpointing=True,
)

# Create processor
processor = BatchProcessorFSA[int, int](config=config)

# Process items
items = list(range(1000))
job = processor.execute(
    items=items,
    priority=Priority.HIGH,
    job_type="data_processing"
)

# Check results
print(f"Processed {len(job.results)} items")
print(f"Job state: {job.state}")

# Get metrics
metrics = processor.get_metrics()
print(f"Success rate: {metrics.success_rate:.2%}")
print(f"Throughput: {metrics.items_per_second:.2f} items/sec")

# Cleanup
processor.shutdown(graceful=True)
```

### Custom Processor

```python
from agno.fsas import BatchProcessorBase, BatchProcessorFSA
from typing import List

class DataTransformer(BatchProcessorBase[dict, dict]):
    """Custom processor for transforming data."""

    def process_item(self, item: dict) -> dict:
        # Transform single item
        return {
            "id": item["id"],
            "value": item["value"] * 2,
            "processed": True
        }

    def process_batch(self, items: List[dict]) -> List[dict]:
        # Batch processing with custom logic
        return [self.process_item(item) for item in items]

    def validate_item(self, item: dict) -> bool:
        # Validate items before processing
        return "id" in item and "value" in item

# Use custom processor
processor = BatchProcessorFSA[dict, dict](
    config=config,
    processor=DataTransformer()
)

data = [{"id": i, "value": i * 10} for i in range(100)]
job = processor.execute(data)
```

## Advanced Features

### Priority Scheduling

```python
from agno.fsas import Priority
from datetime import datetime, timedelta

# High priority job
urgent_job = processor.execute(
    items=urgent_items,
    priority=Priority.CRITICAL,
    deadline=datetime.utcnow() + timedelta(minutes=5)
)

# Normal priority job
normal_job = processor.execute(
    items=normal_items,
    priority=Priority.NORMAL
)

# Low priority background job
background_job = processor.execute(
    items=background_items,
    priority=Priority.LOW
)
```

### Job Dependencies

```python
from agno.fsas import BatchJob

# Create jobs with dependencies
job_a = BatchJob[int](
    job_id="load_data",
    items=data_items,
    priority=Priority.HIGH
)

job_b = BatchJob[int](
    job_id="process_data",
    items=process_items,
    dependencies=["load_data"]  # Waits for job_a
)

processor.schedule_job(job_a)
processor.schedule_job(job_b)
```

### Checkpointing and Recovery

```python
# Enable checkpointing
config = BatchConfig(
    enable_checkpointing=True,
    checkpoint_interval=100,  # Checkpoint every 100 batches
    checkpoint_dir="/path/to/checkpoints"
)

processor = BatchProcessorFSA(config=config)

# Process with automatic checkpointing
job = processor.execute(large_dataset)

# Later, recover from checkpoint
checkpoint_id = "job_123_1234567890"
state = processor.recover(checkpoint_id)
if state:
    print(f"Recovered: processed {state['processed_count']} items")
```

### Resource Management

```python
# Configure resource limits
config = BatchConfig(
    batch_size=100,
    memory_limit_mb=1024,      # 1GB memory limit
    cpu_threshold=0.8,          # 80% CPU threshold
    io_rate_limit=100,          # 100 I/O ops per second
    enable_resource_monitoring=True
)

processor = BatchProcessorFSA(config=config)

# Processor automatically throttles when resources are constrained
job = processor.execute(items)
```

### Parallel Execution Strategies

```python
from agno.fsas import ProcessingStrategy

# Sequential processing
seq_config = BatchConfig(processing_strategy=ProcessingStrategy.SEQUENTIAL)

# Parallel processing with threads
par_config = BatchConfig(
    processing_strategy=ProcessingStrategy.PARALLEL,
    max_workers=8,
    use_multiprocessing=False  # Use threads
)

# Parallel processing with processes
mp_config = BatchConfig(
    processing_strategy=ProcessingStrategy.PARALLEL,
    max_workers=4,
    use_multiprocessing=True  # Use processes
)

# Adaptive strategy (chooses based on workload)
adaptive_config = BatchConfig(
    processing_strategy=ProcessingStrategy.ADAPTIVE
)
```

### Fault Tolerance

```python
# Configure fault tolerance
config = BatchConfig(
    max_retries=3,              # Retry failed items 3 times
    retry_delay=1.0,            # Initial retry delay
    retry_backoff=2.0,          # Exponential backoff
    enable_circuit_breaker=True,
    circuit_failure_threshold=5 # Open circuit after 5 failures
)

processor = BatchProcessorFSA(config=config)

# Failed items are automatically retried
job = processor.execute(items)

# Check failed items
for item, error in job.failed_items:
    print(f"Item {item} failed: {error}")

# Check dead letter queue
dlq = processor.get_dead_letter_queue()
print(f"Permanently failed jobs: {len(dlq)}")

# Retry from dead letter queue
processor.retry_dead_letter_job(dlq[0].job_id)
```

### Monitoring and Metrics

```python
# Get real-time metrics
metrics = processor.get_metrics()

print(f"Jobs processed: {metrics.total_jobs_processed}")
print(f"Items processed: {metrics.total_items_processed}")
print(f"Items failed: {metrics.total_items_failed}")
print(f"Success rate: {metrics.success_rate:.2%}")
print(f"Jobs per second: {metrics.jobs_per_second:.2f}")
print(f"Items per second: {metrics.items_per_second:.2f}")
print(f"Avg latency: {metrics.avg_job_latency_ms:.2f}ms")
print(f"P95 latency: {metrics.p95_job_latency_ms:.2f}ms")
print(f"Queue depth: {metrics.queue_depth}")
print(f"CPU usage: {metrics.cpu_usage_percent:.1f}%")
print(f"Memory usage: {metrics.memory_usage_mb:.1f}MB")

# Export in Prometheus format
prometheus_metrics = metrics.to_prometheus_format()
print(prometheus_metrics)
```

### Caching and Deduplication

```python
# Enable caching and deduplication
config = BatchConfig(
    enable_caching=True,        # Cache results
    enable_deduplication=True   # Remove duplicates
)

processor = BatchProcessorFSA(config=config)

# Items with duplicates
items = [1, 2, 3, 2, 1, 4, 3, 5]

# Processor automatically deduplicates and caches
job = processor.execute(items)  # Processes 5 unique items

# Second run uses cache
job2 = processor.execute(items)  # Much faster

# Clear cache if needed
processor.clear_cache()
processor.clear_deduplication()
```

### Multi-Tenancy

```python
# Process jobs for different tenants
tenant1_job = processor.execute(
    items=tenant1_items,
    tenant_id="tenant_1",
    priority=Priority.HIGH
)

tenant2_job = processor.execute(
    items=tenant2_items,
    tenant_id="tenant_2",
    priority=Priority.NORMAL
)

# List jobs for specific tenant
tenant1_jobs = processor.list_jobs(tenant_id="tenant_1")
```

### Batch Validation

```python
class ValidatingProcessor(BatchProcessorBase[dict, dict]):
    def validate_item(self, item: dict) -> bool:
        # Only process items with required fields
        return all(k in item for k in ["id", "data", "timestamp"])

    def process_item(self, item: dict) -> dict:
        # Process validated item
        return {"result": item["data"].upper()}

config = BatchConfig(enable_validation=True)
processor = BatchProcessorFSA(config=config, processor=ValidatingProcessor())

# Invalid items are automatically filtered out
job = processor.execute(mixed_items)
```

### Graceful Shutdown

```python
import signal

processor = BatchProcessorFSA(config=config)

def shutdown_handler(signum, frame):
    print("Shutting down gracefully...")
    processor.shutdown(graceful=True, timeout=30.0)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Process jobs
job = processor.execute(items)
```

## Configuration Options

### BatchConfig Parameters

```python
config = BatchConfig(
    # Batch sizing
    batch_size=100,              # Default batch size
    min_batch_size=1,            # Minimum batch size
    max_batch_size=10000,        # Maximum batch size
    chunking_strategy="adaptive", # Chunking strategy

    # Processing
    processing_strategy="parallel", # Processing strategy
    max_workers=4,               # Maximum workers
    use_multiprocessing=False,   # Use processes vs threads
    enable_async=False,          # Enable async processing

    # Scheduling
    enable_priority_scheduling=True,
    enable_deadline_scheduling=True,
    max_queue_depth=10000,       # Maximum queue depth

    # Resource management
    memory_limit_mb=1024,        # Memory limit
    cpu_threshold=0.8,           # CPU threshold
    io_rate_limit=100,           # I/O rate limit
    enable_resource_monitoring=True,

    # Fault tolerance
    enable_checkpointing=True,
    checkpoint_interval=100,
    checkpoint_dir="/tmp/checkpoints",
    max_retries=3,
    retry_delay=1.0,
    retry_backoff=2.0,
    enable_circuit_breaker=True,
    circuit_failure_threshold=5,
    circuit_timeout=60.0,

    # Monitoring
    enable_metrics=True,
    metrics_interval=1.0,
    enable_detailed_logging=False,

    # Advanced features
    enable_caching=True,
    enable_deduplication=True,
    enable_compression=False,
    enable_validation=True,
)
```

## Best Practices

### 1. Choose Appropriate Batch Size

```python
# For I/O bound tasks (API calls, database queries)
config = BatchConfig(batch_size=50, processing_strategy="parallel")

# For CPU bound tasks
config = BatchConfig(batch_size=1000, processing_strategy="sequential")

# Let adaptive sizing handle it
config = BatchConfig(chunking_strategy="adaptive")
```

### 2. Use Priority Levels Wisely

```python
# Critical: User-facing operations
Priority.CRITICAL

# High: Time-sensitive but not critical
Priority.HIGH

# Normal: Regular batch processing
Priority.NORMAL

# Low: Background cleanup, analytics
Priority.LOW
```

### 3. Enable Checkpointing for Long-Running Jobs

```python
config = BatchConfig(
    enable_checkpointing=True,
    checkpoint_interval=100  # More frequent for critical jobs
)
```

### 4. Monitor Resource Usage

```python
# Poll metrics regularly
import time

while processor.is_running:
    metrics = processor.get_metrics()
    if metrics.memory_usage_mb > 900:  # 90% of 1GB limit
        print("Warning: High memory usage")
    time.sleep(5)
```

### 5. Handle Errors Gracefully

```python
class RobustProcessor(BatchProcessorBase[dict, dict]):
    def on_error(self, item: dict, error: Exception) -> Optional[dict]:
        # Log error
        logger.error(f"Failed to process {item}: {error}")

        # Return default result instead of failing
        return {"status": "error", "error": str(error)}
```

## Performance Tips

1. **Use parallel processing for I/O-bound tasks**
2. **Enable caching for repeated operations**
3. **Set appropriate resource limits to prevent OOM**
4. **Use adaptive batch sizing for varying workloads**
5. **Enable deduplication to reduce redundant work**
6. **Monitor metrics to identify bottlenecks**
7. **Use checkpointing for long-running jobs**
8. **Configure circuit breakers to fail fast**

## Troubleshooting

### High Memory Usage

```python
config = BatchConfig(
    memory_limit_mb=512,         # Lower limit
    batch_size=50,               # Smaller batches
    chunking_strategy="memory_based"
)
```

### Slow Processing

```python
config = BatchConfig(
    processing_strategy="parallel",
    max_workers=8,               # More workers
    enable_caching=True          # Cache results
)
```

### Circuit Breaker Opening

```python
# Check failed items
dlq = processor.get_dead_letter_queue()

# Reset circuit breaker
processor.reset_circuit_breaker()

# Adjust thresholds
config = BatchConfig(
    circuit_failure_threshold=10,  # More tolerant
    circuit_timeout=120.0          # Longer timeout
)
```

## Example: Real-World Data Pipeline

```python
from agno.fsas import (
    BatchProcessorFSA,
    BatchConfig,
    BatchProcessorBase,
    Priority,
)
from typing import List, Dict
import requests

class DataPipeline(BatchProcessorBase[Dict, Dict]):
    """Process data from API and store results."""

    def process_item(self, item: Dict) -> Dict:
        # Fetch data from API
        response = requests.get(f"https://api.example.com/data/{item['id']}")
        data = response.json()

        # Transform data
        transformed = {
            "id": item["id"],
            "value": data["value"] * 2,
            "timestamp": data["timestamp"],
            "processed": True
        }

        # Store result (database, S3, etc.)
        # store_result(transformed)

        return transformed

    def validate_item(self, item: Dict) -> bool:
        return "id" in item and isinstance(item["id"], int)

    def on_error(self, item: Dict, error: Exception) -> Optional[Dict]:
        # Log to monitoring system
        logger.error(f"Failed to process {item['id']}: {error}")
        return None

# Configure pipeline
config = BatchConfig(
    batch_size=100,
    processing_strategy="parallel",
    max_workers=10,
    memory_limit_mb=2048,
    enable_checkpointing=True,
    checkpoint_interval=50,
    max_retries=3,
    enable_circuit_breaker=True,
    enable_metrics=True,
)

# Create processor
pipeline = BatchProcessorFSA[Dict, Dict](
    config=config,
    processor=DataPipeline()
)

# Process data
items = [{"id": i} for i in range(10000)]
job = pipeline.execute(
    items=items,
    priority=Priority.HIGH,
    job_type="data_pipeline"
)

# Report results
print(f"Processed: {len(job.results)}")
print(f"Failed: {len(job.failed_items)}")

metrics = pipeline.get_metrics()
print(f"Throughput: {metrics.items_per_second:.2f} items/sec")
print(f"Success rate: {metrics.success_rate:.2%}")

pipeline.shutdown(graceful=True)
```

## Documentation

For more details, see:
- API Reference: `libs/agno/agno/fsas/infrastructure/batch_processor_fsa.py`
- Tests: `libs/agno/tests/unit/fsas/test_batch_processor_fsa.py`
- Validation: `validate_batch_processor.py`

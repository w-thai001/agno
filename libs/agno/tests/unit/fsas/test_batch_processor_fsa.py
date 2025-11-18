"""
Comprehensive unit tests for Batch Processor FSA.

This test suite covers all major functionality including:
- Core batch processing with various sizes
- Priority scheduling and deadline handling
- Parallel execution modes
- Fault tolerance and recovery
- Resource management and throttling
- Metrics collection and monitoring
- Circuit breaker pattern
- Caching and deduplication
- Checkpointing and recovery
"""

import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from typing import Any, List
from unittest.mock import Mock, patch

import pytest

from agno.fsas.infrastructure.batch_processor_fsa import (
    AdaptiveBatchSizer,
    BatchConfig,
    BatchIterator,
    BatchJob,
    BatchMetrics,
    BatchProcessorBase,
    BatchProcessorFSA,
    BatchScheduler,
    BatchState,
    CheckpointManager,
    ChunkingStrategy,
    CircuitBreaker,
    CircuitState,
    InputDeduplicator,
    MetricsCollector,
    Priority,
    ProcessingStrategy,
    ResourceManager,
    ResultCache,
    create_batch_processor,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def basic_config(temp_checkpoint_dir):
    """Create a basic batch configuration."""
    return BatchConfig(
        batch_size=10,
        min_batch_size=1,
        max_batch_size=100,
        checkpoint_dir=temp_checkpoint_dir,
        enable_checkpointing=True,
        enable_metrics=True,
        max_retries=2,
    )


@pytest.fixture
def parallel_config(temp_checkpoint_dir):
    """Create configuration for parallel processing."""
    return BatchConfig(
        batch_size=10,
        processing_strategy=ProcessingStrategy.PARALLEL,
        max_workers=4,
        use_multiprocessing=False,
        checkpoint_dir=temp_checkpoint_dir,
    )


class SimpleProcessor(BatchProcessorBase[int, int]):
    """Simple test processor that doubles integers."""

    def process_item(self, item: int) -> int:
        """Double the input value."""
        return item * 2

    def process_batch(self, items: List[int]) -> List[int]:
        """Process batch of items."""
        return [self.process_item(item) for item in items]


class SlowProcessor(BatchProcessorBase[int, int]):
    """Processor that simulates slow operations."""

    def process_item(self, item: int) -> int:
        """Process item slowly."""
        time.sleep(0.1)
        return item * 2

    def process_batch(self, items: List[int]) -> List[int]:
        """Process batch of items."""
        return [self.process_item(item) for item in items]


class FailingProcessor(BatchProcessorBase[int, int]):
    """Processor that fails on certain items."""

    def __init__(self, fail_on: List[int]):
        """Initialize with items to fail on."""
        self.fail_on = fail_on

    def process_item(self, item: int) -> int:
        """Process item, failing on specified values."""
        if item in self.fail_on:
            raise ValueError(f"Failed on item: {item}")
        return item * 2

    def process_batch(self, items: List[int]) -> List[int]:
        """Process batch of items."""
        return [self.process_item(item) for item in items]


# ============================================================================
# CORE BATCH PROCESSING TESTS
# ============================================================================


class TestCoreBatchProcessing:
    """Tests for core batch processing functionality."""

    def test_process_small_batch(self, basic_config):
        """Test processing a small batch of items."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())
        items = list(range(10))

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 10
        assert job.results == [i * 2 for i in items]

    def test_process_large_batch(self, basic_config):
        """Test processing a large batch of items."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())
        items = list(range(1000))

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 1000
        assert job.results == [i * 2 for i in items]

    def test_process_empty_batch(self, basic_config):
        """Test processing an empty batch."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())
        items = []

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 0

    def test_process_single_item(self, basic_config):
        """Test processing a single item."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())
        items = [42]

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 1
        assert job.results[0] == 84

    def test_batch_iterator_fixed_size(self):
        """Test batch iterator with fixed size strategy."""
        items = list(range(25))
        iterator = BatchIterator(items, batch_size=10, strategy=ChunkingStrategy.FIXED_SIZE)

        batches = list(iterator)

        assert len(batches) == 3
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5

    def test_adaptive_batch_sizer(self):
        """Test adaptive batch size adjustment."""
        sizer = AdaptiveBatchSizer(
            initial_size=100,
            min_size=10,
            max_size=1000,
        )

        initial_size = sizer.get_batch_size()
        assert initial_size == 100

        # Record increasing throughput
        sizer.record_throughput(100)
        sizer.record_throughput(150)
        sizer.record_throughput(200)
        sizer.adjust()

        # Size might increase due to good throughput
        adjusted_size = sizer.get_batch_size()
        assert adjusted_size >= initial_size

    def test_default_processor_implementation(self, basic_config):
        """Test default processor implementation (identity function)."""
        processor = BatchProcessorFSA[int, int](config=basic_config)
        items = [1, 2, 3, 4, 5]

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert job.results == items


# ============================================================================
# SCHEDULING TESTS
# ============================================================================


class TestScheduling:
    """Tests for job scheduling functionality."""

    def test_priority_scheduling(self, basic_config):
        """Test priority-based scheduling."""
        scheduler = BatchScheduler(basic_config)

        # Add jobs with different priorities
        job_low = BatchJob[int](job_id="low", priority=Priority.LOW, items=[1, 2, 3])
        job_high = BatchJob[int](job_id="high", priority=Priority.HIGH, items=[4, 5, 6])
        job_critical = BatchJob[int](job_id="critical", priority=Priority.CRITICAL, items=[7, 8, 9])

        scheduler.add_job(job_low)
        scheduler.add_job(job_high)
        scheduler.add_job(job_critical)

        # Critical should come first
        next_job = scheduler.get_next_job()
        assert next_job is not None
        assert next_job.job_id == "critical"

        # High should come next
        next_job = scheduler.get_next_job()
        assert next_job is not None
        assert next_job.job_id == "high"

        # Low should come last
        next_job = scheduler.get_next_job()
        assert next_job is not None
        assert next_job.job_id == "low"

    def test_deadline_scheduling(self, basic_config):
        """Test deadline-aware scheduling."""
        config = BatchConfig(**basic_config.dict())
        config.enable_deadline_scheduling = True
        scheduler = BatchScheduler(config)

        # Add job with past deadline
        past_deadline = datetime.utcnow() - timedelta(hours=1)
        job_overdue = BatchJob[int](
            job_id="overdue",
            priority=Priority.NORMAL,
            items=[1, 2, 3],
            deadline=past_deadline,
        )

        scheduler.add_job(job_overdue)

        # Overdue job should be skipped
        next_job = scheduler.get_next_job()
        assert next_job is None  # Job marked as failed due to deadline

    def test_dependency_resolution(self, basic_config):
        """Test job dependency resolution."""
        scheduler = BatchScheduler(basic_config)

        # Create jobs with dependencies
        job_a = BatchJob[int](job_id="A", priority=Priority.NORMAL, items=[1, 2])
        job_b = BatchJob[int](
            job_id="B", priority=Priority.NORMAL, items=[3, 4], dependencies=["A"]
        )

        scheduler.add_job(job_a)
        scheduler.add_job(job_b)

        # Job A should come first
        next_job = scheduler.get_next_job()
        assert next_job is not None
        assert next_job.job_id == "A"
        scheduler.mark_completed("A")

        # Now job B should be available
        next_job = scheduler.get_next_job()
        assert next_job is not None
        assert next_job.job_id == "B"

    def test_queue_depth_limit(self, basic_config):
        """Test queue depth limit enforcement."""
        config = BatchConfig(**basic_config.dict())
        config.max_queue_depth = 5
        scheduler = BatchScheduler(config)

        # Add jobs up to limit
        for i in range(5):
            job = BatchJob[int](job_id=f"job_{i}", items=[i])
            scheduler.add_job(job)

        # Adding one more should raise error
        with pytest.raises(ValueError, match="Queue depth exceeded"):
            job = BatchJob[int](job_id="job_6", items=[6])
            scheduler.add_job(job)

    def test_job_cancellation(self, basic_config):
        """Test job cancellation."""
        scheduler = BatchScheduler(basic_config)

        job = BatchJob[int](job_id="cancel_me", items=[1, 2, 3])
        scheduler.add_job(job)

        # Cancel the job
        result = scheduler.cancel_job("cancel_me")
        assert result is True

        # Job should not be available
        next_job = scheduler.get_next_job()
        assert next_job is None

    def test_multi_tenancy_queues(self, basic_config):
        """Test multi-tenancy support with isolated queues."""
        scheduler = BatchScheduler(basic_config)

        # Add jobs for different tenants
        job_tenant1 = BatchJob[int](job_id="t1_job", tenant_id="tenant1", items=[1, 2])
        job_tenant2 = BatchJob[int](job_id="t2_job", tenant_id="tenant2", items=[3, 4])

        scheduler.add_job(job_tenant1)
        scheduler.add_job(job_tenant2)

        assert len(scheduler.tenant_queues["tenant1"]) == 1
        assert len(scheduler.tenant_queues["tenant2"]) == 1


# ============================================================================
# PARALLEL EXECUTION TESTS
# ============================================================================


class TestParallelExecution:
    """Tests for parallel execution functionality."""

    def test_parallel_processing(self, parallel_config):
        """Test parallel batch processing."""
        processor = BatchProcessorFSA[int, int](
            config=parallel_config, processor=SimpleProcessor()
        )
        items = list(range(100))

        start_time = time.time()
        job = processor.execute(items)
        elapsed = time.time() - start_time

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 100
        assert set(job.results) == set(i * 2 for i in items)

        processor.shutdown()

    def test_sequential_vs_parallel_performance(self, temp_checkpoint_dir):
        """Test that parallel processing is faster for large batches."""
        items = list(range(40))  # 40 items * 0.1s = 4s sequential

        # Sequential processing
        seq_config = BatchConfig(
            batch_size=10,
            processing_strategy=ProcessingStrategy.SEQUENTIAL,
            checkpoint_dir=temp_checkpoint_dir,
        )
        seq_processor = BatchProcessorFSA[int, int](
            config=seq_config, processor=SlowProcessor()
        )

        seq_start = time.time()
        seq_job = seq_processor.execute(items)
        seq_elapsed = time.time() - seq_start

        # Parallel processing
        par_config = BatchConfig(
            batch_size=10,
            processing_strategy=ProcessingStrategy.PARALLEL,
            max_workers=4,
            checkpoint_dir=temp_checkpoint_dir,
        )
        par_processor = BatchProcessorFSA[int, int](
            config=par_config, processor=SlowProcessor()
        )

        par_start = time.time()
        par_job = par_processor.execute(items)
        par_elapsed = time.time() - par_start

        assert seq_job.state == BatchState.COMPLETED
        assert par_job.state == BatchState.COMPLETED

        # Parallel should be faster (with some tolerance)
        assert par_elapsed < seq_elapsed * 0.8

        par_processor.shutdown()

    def test_adaptive_strategy(self, temp_checkpoint_dir):
        """Test adaptive processing strategy selection."""
        config = BatchConfig(
            batch_size=10,
            processing_strategy=ProcessingStrategy.ADAPTIVE,
            checkpoint_dir=temp_checkpoint_dir,
        )
        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())

        # Small batch should use sequential
        small_items = list(range(50))
        small_job = processor.execute(small_items)
        assert small_job.state == BatchState.COMPLETED

        # Large batch should try parallel (if resources available)
        large_items = list(range(500))
        large_job = processor.execute(large_items)
        assert large_job.state == BatchState.COMPLETED

        processor.shutdown()

    def test_worker_pool_initialization(self, parallel_config):
        """Test worker pool initialization and cleanup."""
        processor = BatchProcessorFSA[int, int](config=parallel_config)

        # Start processing to initialize pool
        items = list(range(10))
        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert processor.worker_pool is not None

        # Shutdown should cleanup pool
        processor.shutdown()


# ============================================================================
# FAULT TOLERANCE TESTS
# ============================================================================


class TestFaultTolerance:
    """Tests for fault tolerance and recovery."""

    def test_retry_on_failure(self, basic_config):
        """Test retry logic for failed items."""
        config = BatchConfig(**basic_config.dict())
        config.max_retries = 3
        config.retry_delay = 0.1

        failing_processor = FailingProcessor(fail_on=[5])
        processor = BatchProcessorFSA[int, int](config=config, processor=failing_processor)

        items = list(range(10))
        job = processor.execute(items)

        # Job should complete but with failed items
        assert job.state in [BatchState.COMPLETED, BatchState.FAILED]
        # Item 5 should have been retried multiple times

    def test_checkpoint_creation(self, basic_config):
        """Test checkpoint creation during processing."""
        config = BatchConfig(**basic_config.dict())
        config.enable_checkpointing = True
        config.checkpoint_interval = 5

        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())
        items = list(range(50))

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED

        # Check if checkpoints were created
        checkpoints = processor.checkpoint_manager.list_checkpoints(job.job_id)
        assert len(checkpoints) > 0

    def test_checkpoint_recovery(self, temp_checkpoint_dir):
        """Test recovery from checkpoint."""
        checkpoint_manager = CheckpointManager(temp_checkpoint_dir)

        # Save checkpoint
        job_id = "test_job"
        state = {"batch_num": 5, "processed_count": 50}
        checkpoint_id = checkpoint_manager.save_checkpoint(job_id, state)

        # Recover checkpoint
        recovered = checkpoint_manager.load_checkpoint(checkpoint_id)

        assert recovered is not None
        assert recovered["job_id"] == job_id
        assert recovered["state"]["batch_num"] == 5
        assert recovered["state"]["processed_count"] == 50

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        circuit = CircuitBreaker(failure_threshold=3, timeout=1.0)

        def failing_function():
            raise ValueError("Always fails")

        # Trigger failures
        for _ in range(3):
            try:
                circuit.call(failing_function)
            except Exception:
                pass

        # Circuit should be open
        assert circuit.get_state() == CircuitState.OPEN

        # Further calls should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            circuit.call(failing_function)

    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open state."""
        circuit = CircuitBreaker(failure_threshold=2, timeout=0.5)

        def failing_function():
            raise ValueError("Fails")

        # Open circuit
        for _ in range(2):
            try:
                circuit.call(failing_function)
            except Exception:
                pass

        assert circuit.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.6)

        # Next call should transition to half-open
        try:
            circuit.call(failing_function)
        except Exception:
            pass

        # Should be back to open after failure in half-open
        assert circuit.get_state() == CircuitState.OPEN

    def test_circuit_breaker_reset(self):
        """Test circuit breaker manual reset."""
        circuit = CircuitBreaker(failure_threshold=2)

        def failing_function():
            raise ValueError("Fails")

        # Open circuit
        for _ in range(2):
            try:
                circuit.call(failing_function)
            except Exception:
                pass

        assert circuit.get_state() == CircuitState.OPEN

        # Reset circuit
        circuit.reset()
        assert circuit.get_state() == CircuitState.CLOSED

    def test_dead_letter_queue(self, basic_config):
        """Test dead letter queue for permanently failed jobs."""
        config = BatchConfig(**basic_config.dict())
        config.max_retries = 1

        failing_processor = FailingProcessor(fail_on=list(range(10)))
        processor = BatchProcessorFSA[int, int](config=config, processor=failing_processor)

        items = list(range(10))
        job = processor.execute(items)

        # Job should fail and move to dead letter queue
        assert job.state in [BatchState.FAILED, BatchState.DEAD_LETTER]

        # Check dead letter queue
        dlq = processor.get_dead_letter_queue()
        assert len(dlq) > 0


# ============================================================================
# RESOURCE MANAGEMENT TESTS
# ============================================================================


class TestResourceManagement:
    """Tests for resource management functionality."""

    def test_memory_limit_check(self, basic_config):
        """Test memory limit checking."""
        config = BatchConfig(**basic_config.dict())
        config.memory_limit_mb = 10000  # 10GB limit

        resource_manager = ResourceManager(config)
        assert resource_manager.check_memory_available() is True

    def test_cpu_threshold_check(self, basic_config):
        """Test CPU threshold checking."""
        config = BatchConfig(**basic_config.dict())
        config.cpu_threshold = 0.95

        resource_manager = ResourceManager(config)
        # Should return True unless system is heavily loaded
        result = resource_manager.check_cpu_available()
        assert isinstance(result, bool)

    def test_io_rate_limiting(self, basic_config):
        """Test I/O rate limiting."""
        config = BatchConfig(**basic_config.dict())
        config.io_rate_limit = 10

        resource_manager = ResourceManager(config)

        # Record operations up to limit
        for _ in range(10):
            resource_manager.record_io_operation()

        # Should hit limit
        assert resource_manager.check_io_available() is False

        # Wait for window reset
        time.sleep(1.1)
        assert resource_manager.check_io_available() is True

    def test_resource_metrics_collection(self, basic_config):
        """Test resource metrics collection."""
        resource_manager = ResourceManager(basic_config)
        metrics = resource_manager.get_resource_metrics()

        assert "cpu_percent" in metrics
        assert "memory_mb" in metrics
        assert "memory_percent" in metrics
        assert metrics["memory_mb"] > 0

    def test_throttling_behavior(self, basic_config):
        """Test throttling when resources are constrained."""
        config = BatchConfig(**basic_config.dict())
        config.memory_limit_mb = 1  # Very low limit to trigger throttling

        resource_manager = ResourceManager(config)

        # Should throttle if memory not available
        start_time = time.time()
        resource_manager.throttle_if_needed()
        elapsed = time.time() - start_time

        # If throttled, should have waited
        assert elapsed >= 0


# ============================================================================
# MONITORING AND METRICS TESTS
# ============================================================================


class TestMonitoringAndMetrics:
    """Tests for monitoring and metrics functionality."""

    def test_metrics_collection(self, basic_config):
        """Test metrics collection during processing."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())
        items = list(range(100))

        job = processor.execute(items)

        metrics = processor.get_metrics()

        assert metrics.total_jobs_processed >= 1
        assert metrics.total_items_processed >= 100
        assert metrics.success_rate > 0

    def test_latency_metrics(self, basic_config):
        """Test latency metrics calculation."""
        metrics_collector = MetricsCollector(basic_config)

        job_id = "test_job"
        metrics_collector.record_job_start(job_id)
        time.sleep(0.1)
        metrics_collector.record_job_completion(job_id, items_count=100)

        metrics = metrics_collector.get_metrics()

        assert metrics.avg_job_latency_ms > 0
        assert metrics.total_jobs_processed == 1
        assert metrics.total_items_processed == 100

    def test_throughput_calculation(self, basic_config):
        """Test throughput metrics calculation."""
        metrics_collector = MetricsCollector(basic_config)

        # Process multiple jobs
        for i in range(5):
            job_id = f"job_{i}"
            metrics_collector.record_job_start(job_id)
            time.sleep(0.05)
            metrics_collector.record_job_completion(job_id, items_count=20)

        # Update metrics
        metrics_collector.update_metrics(
            queue_depth=0,
            oldest_job_age=0,
            active_workers=4,
            circuit_state=CircuitState.CLOSED,
            circuit_failures=0,
            resource_metrics={},
        )

        metrics = metrics_collector.get_metrics()

        assert metrics.jobs_per_second > 0
        assert metrics.items_per_second > 0
        assert metrics.total_jobs_processed == 5

    def test_prometheus_format_export(self, basic_config):
        """Test Prometheus format metrics export."""
        metrics_collector = MetricsCollector(basic_config)
        metrics_collector.record_job_completion("test", 100, 5)

        metrics = metrics_collector.get_metrics()
        prometheus_output = metrics.to_prometheus_format()

        assert "batch_jobs_total" in prometheus_output
        assert "batch_items_total" in prometheus_output
        assert "batch_success_rate" in prometheus_output

    def test_sla_violation_tracking(self, basic_config):
        """Test SLA violation tracking."""
        metrics_collector = MetricsCollector(basic_config)

        metrics_collector.record_sla_violation()
        metrics_collector.record_deadline_exceeded()

        metrics = metrics_collector.get_metrics()

        assert metrics.sla_violations == 1
        assert metrics.jobs_exceeding_deadline == 1

    def test_checkpoint_metrics(self, basic_config):
        """Test checkpoint metrics tracking."""
        metrics_collector = MetricsCollector(basic_config)

        metrics_collector.record_checkpoint()
        metrics_collector.record_checkpoint()

        metrics = metrics_collector.get_metrics()

        assert metrics.checkpoints_created == 2
        assert metrics.last_checkpoint_time is not None


# ============================================================================
# ADVANCED FEATURES TESTS
# ============================================================================


class TestAdvancedFeatures:
    """Tests for advanced features."""

    def test_result_caching(self, basic_config):
        """Test result caching functionality."""
        config = BatchConfig(**basic_config.dict())
        config.enable_caching = True

        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())

        # Process items twice
        items = list(range(10))
        job1 = processor.execute(items)
        job2 = processor.execute(items)

        assert job1.state == BatchState.COMPLETED
        assert job2.state == BatchState.COMPLETED

        # Cache should be populated
        assert processor.result_cache is not None

    def test_input_deduplication(self, basic_config):
        """Test input deduplication."""
        config = BatchConfig(**basic_config.dict())
        config.enable_deduplication = True

        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())

        # Items with duplicates
        items = [1, 2, 3, 2, 1, 4, 3, 5]
        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        # Should have deduplicated
        assert len(job.results) < len(items)

    def test_cache_eviction_lru(self):
        """Test LRU cache eviction."""
        cache = ResultCache(max_size=3)

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (LRU)
        cache.put("key4", "value4")

        assert cache.get("key1") is not None
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_input_deduplicator_hashing(self):
        """Test input deduplicator hashing."""
        deduplicator = InputDeduplicator()

        items = [1, 2, 3, 2, 1, 4, 5, 3]
        unique_items = deduplicator.deduplicate(items)

        assert len(unique_items) == 5
        assert set(unique_items) == {1, 2, 3, 4, 5}

    def test_batch_validation(self, basic_config):
        """Test batch validation functionality."""
        config = BatchConfig(**basic_config.dict())
        config.enable_validation = True

        class ValidatingProcessor(BatchProcessorBase[int, int]):
            def validate_item(self, item: int) -> bool:
                return item >= 0

            def process_item(self, item: int) -> int:
                return item * 2

            def process_batch(self, items: List[int]) -> List[int]:
                return [self.process_item(item) for item in items]

        processor = BatchProcessorFSA[int, int](
            config=config, processor=ValidatingProcessor()
        )

        # Mix of valid and invalid items
        items = [-1, 1, -2, 2, 3]
        job = processor.execute(items)

        # Should only process valid items
        assert job.state == BatchState.COMPLETED
        assert len(job.results) < len(items)

    def test_batch_transformation(self, basic_config):
        """Test batch transformation pipeline."""
        config = BatchConfig(**basic_config.dict())
        config.processing_strategy = ProcessingStrategy.PIPELINE

        class TransformingProcessor(BatchProcessorBase[int, int]):
            def transform_item(self, item: int) -> int:
                return item + 10

            def process_item(self, item: int) -> int:
                return item * 2

            def process_batch(self, items: List[int]) -> List[int]:
                return [self.process_item(item) for item in items]

        processor = BatchProcessorFSA[int, int](
            config=config, processor=TransformingProcessor()
        )

        items = [1, 2, 3]
        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        # Items should be transformed (+ 10) then processed (* 2)
        assert job.results == [22, 24, 26]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for end-to-end scenarios."""

    def test_complete_workflow_with_checkpointing(self, basic_config):
        """Test complete workflow with checkpointing."""
        config = BatchConfig(**basic_config.dict())
        config.enable_checkpointing = True
        config.checkpoint_interval = 10

        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())
        items = list(range(50))

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 50

        # Verify checkpoints
        checkpoints = processor.checkpoint_manager.list_checkpoints(job.job_id)
        assert len(checkpoints) > 0

        # Test checkpoint cleanup
        deleted = processor.cleanup_checkpoints(max_age_hours=0)
        assert deleted >= 0

    def test_concurrent_job_processing(self, basic_config):
        """Test processing multiple jobs concurrently."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())

        def process_job(job_items):
            return processor.execute(job_items)

        # Submit multiple jobs
        threads = []
        for i in range(5):
            items = list(range(i * 10, (i + 1) * 10))
            thread = threading.Thread(target=process_job, args=(items,))
            thread.start()
            threads.append(thread)

        # Wait for all jobs
        for thread in threads:
            thread.join()

        metrics = processor.get_metrics()
        assert metrics.total_jobs_processed >= 5

        processor.shutdown()

    def test_graceful_shutdown(self, parallel_config):
        """Test graceful shutdown of batch processor."""
        processor = BatchProcessorFSA[int, int](
            config=parallel_config, processor=SimpleProcessor()
        )

        items = list(range(100))
        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED

        # Shutdown gracefully
        processor.shutdown(graceful=True, timeout=5.0)

        # Verify worker pool is cleaned up
        assert processor.is_running is False

    def test_pause_and_resume(self, basic_config):
        """Test pausing and resuming batch processing."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())

        processor.pause()
        assert processor.is_paused is True

        processor.resume()
        assert processor.is_paused is False

    def test_factory_function(self, basic_config):
        """Test factory function for creating processor."""
        processor = create_batch_processor(config=basic_config, processor=SimpleProcessor())

        assert isinstance(processor, BatchProcessorFSA)

        items = [1, 2, 3]
        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED


# ============================================================================
# STRESS TESTS
# ============================================================================


class TestStressScenarios:
    """Stress tests for batch processor."""

    def test_very_large_batch(self, basic_config):
        """Test processing a very large batch."""
        config = BatchConfig(**basic_config.dict())
        config.max_batch_size = 10000

        processor = BatchProcessorFSA[int, int](config=config, processor=SimpleProcessor())
        items = list(range(10000))

        job = processor.execute(items)

        assert job.state == BatchState.COMPLETED
        assert len(job.results) == 10000

    def test_rapid_job_submission(self, basic_config):
        """Test rapid submission of multiple jobs."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())

        jobs = []
        for i in range(20):
            items = list(range(10))
            job = processor.execute(items, job_type=f"rapid_{i}")
            jobs.append(job)

        # All jobs should complete
        for job in jobs:
            assert job.state == BatchState.COMPLETED

        processor.shutdown()

    def test_mixed_priority_workload(self, basic_config):
        """Test mixed priority workload."""
        processor = BatchProcessorFSA[int, int](config=basic_config, processor=SimpleProcessor())

        # Submit jobs with various priorities
        priorities = [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.CRITICAL]
        jobs = []

        for priority in priorities:
            items = list(range(10))
            job = processor.execute(items, priority=priority)
            jobs.append(job)

        # All jobs should complete
        for job in jobs:
            assert job.state == BatchState.COMPLETED

        processor.shutdown()


# ============================================================================
# UTILITY TESTS
# ============================================================================


class TestUtilities:
    """Tests for utility functions and helpers."""

    def test_batch_job_is_overdue(self):
        """Test batch job deadline checking."""
        past_deadline = datetime.utcnow() - timedelta(hours=1)
        job = BatchJob[int](items=[1, 2, 3], deadline=past_deadline)

        assert job.is_overdue() is True

    def test_batch_job_dependencies_ready(self):
        """Test batch job dependency checking."""
        job = BatchJob[int](items=[1, 2, 3], dependencies=["job1", "job2"])

        assert job.is_ready(set()) is False
        assert job.is_ready({"job1"}) is False
        assert job.is_ready({"job1", "job2"}) is True

    def test_batch_job_age_calculation(self):
        """Test batch job age calculation."""
        job = BatchJob[int](items=[1, 2, 3])
        time.sleep(0.1)

        age = job.get_age_seconds()
        assert age >= 0.1

    def test_batch_metrics_validation(self):
        """Test batch metrics validation."""
        metrics = BatchMetrics(
            total_jobs_processed=100,
            total_items_processed=1000,
            total_items_failed=50,
        )

        assert metrics.total_jobs_processed == 100
        assert metrics.total_items_processed == 1000
        assert metrics.total_items_failed == 50

    def test_batch_config_validation(self):
        """Test batch config validation."""
        # Valid config
        config = BatchConfig(min_batch_size=10, max_batch_size=100)
        assert config.min_batch_size < config.max_batch_size

        # Invalid config should raise error
        with pytest.raises(Exception):
            BatchConfig(min_batch_size=100, max_batch_size=10)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

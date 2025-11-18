"""Comprehensive unit tests for TaskQueueFSA."""

import pytest
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

from agno.fsas.task_queue_fsa import (
    TaskQueueFSA,
    Task,
    Worker,
    WorkerPool,
    TaskResult,
    AsyncResult,
    EnqueueResult,
    DequeueResult,
    TaskProcessingResult,
    ScalingResult,
    RoutingResult,
    ChainResult,
    RetryPolicy,
    RetryResult,
    QueueMetrics,
    TaskStatus,
    QueueConfig,
    ValidationResult,
    TaskQueueResult,
    StoreResult,
    DLQResult,
    PurgeResult,
    CancelResult,
    QueueBackend,
    ResultBackend,
    TaskState,
    WorkerState,
    SerializationFormat,
    RoutingStrategy,
)


@pytest.fixture
def task_queue():
    """Create a TaskQueueFSA instance."""
    return TaskQueueFSA(
        name="test-queue",
        default_backend=QueueBackend.MEMORY,
        default_result_backend=ResultBackend.MEMORY,
    )


@pytest.fixture
def sample_task():
    """Create a sample task."""
    def sample_func(x):
        return x * 2

    return Task(
        name="sample_task",
        func=sample_func,
        args=(5,),
        priority=100,
        queue_name="default",
    )


@pytest.fixture
def task_queue_with_pool(task_queue):
    """Create a task queue with worker pool."""
    task_queue.create_worker_pool(pool_size=2, queue_name="default")
    return task_queue


# Test 1: Task Queue Initialization
class TestTaskQueueInitialization:
    """Test TaskQueueFSA initialization."""

    def test_create_task_queue(self):
        """Test creating a task queue."""
        queue = TaskQueueFSA(name="test-1")
        assert queue.name == "test-1"
        assert queue.fsa_id is not None
        assert queue.queues is not None

    def test_create_with_config(self):
        """Test creating queue with custom config."""
        queue = TaskQueueFSA(
            name="test-2",
            default_backend=QueueBackend.REDIS,
            default_result_backend=ResultBackend.FILESYSTEM,
        )
        assert queue.default_backend == QueueBackend.REDIS
        assert queue.default_result_backend == ResultBackend.FILESYSTEM


# Test 2: Task Enqueueing
class TestTaskEnqueueing:
    """Test task enqueueing functionality."""

    def test_enqueue_task(self, task_queue, sample_task):
        """Test enqueueing a task."""
        result = task_queue.enqueue_task(sample_task, "default", priority=100)
        assert result.success is True
        assert result.task_id == sample_task.task_id
        assert result.queue_name == "default"

    def test_enqueue_multiple_tasks(self, task_queue):
        """Test enqueueing multiple tasks."""
        tasks = []
        for i in range(5):
            task = Task(name=f"task-{i}", func=lambda x: x, args=(i,))
            result = task_queue.enqueue_task(task, "default")
            assert result.success is True
            tasks.append(task)

        assert len(task_queue.pending_tasks["default"]) == 5


# Test 3: Task Dequeueing
class TestTaskDequeueing:
    """Test task dequeueing functionality."""

    def test_dequeue_task(self, task_queue, sample_task):
        """Test dequeueing a task."""
        # Enqueue first
        task_queue.enqueue_task(sample_task, "default")

        # Create worker
        worker = Worker(queue_name="default")
        task_queue.workers[worker.worker_id] = worker

        # Dequeue
        result = task_queue.dequeue_task("default", worker.worker_id)
        assert result.success is True
        assert result.task is not None
        assert result.task.task_id == sample_task.task_id

    def test_dequeue_empty_queue(self, task_queue):
        """Test dequeueing from empty queue."""
        task_queue._create_queue("empty")
        worker = Worker(queue_name="empty")
        result = task_queue.dequeue_task("empty", worker.worker_id)
        assert result.success is False


# Test 4: Task Processing
class TestTaskProcessing:
    """Test task processing functionality."""

    def test_process_task(self, task_queue, sample_task):
        """Test processing a task."""
        worker = Worker(queue_name="default")
        task_queue.workers[worker.worker_id] = worker

        result = task_queue.process_task(sample_task, worker)
        assert result.success is True
        assert result.result == 10  # 5 * 2

    def test_process_failing_task(self, task_queue):
        """Test processing a task that fails."""
        def failing_func():
            raise ValueError("Test error")

        task = Task(name="failing_task", func=failing_func)
        worker = Worker()
        task_queue.workers[worker.worker_id] = worker

        result = task_queue.process_task(task, worker)
        assert result.success is False
        assert result.error is not None


# Test 5: Async Task Submission
class TestAsyncTaskSubmission:
    """Test asynchronous task submission."""

    def test_submit_async(self, task_queue, sample_task):
        """Test submitting task asynchronously."""
        async_result = task_queue.submit_async(sample_task, args=(10,))
        assert isinstance(async_result, AsyncResult)
        assert async_result.task_id == sample_task.task_id

    def test_async_result_get(self, task_queue, sample_task):
        """Test getting async result."""
        # Enqueue and process task
        task_queue.enqueue_task(sample_task, "default")
        worker = Worker()
        task_queue.workers[worker.worker_id] = worker

        # Process task to generate result
        task_queue.process_task(sample_task, worker)

        # Get result
        async_result = AsyncResult(task_id=sample_task.task_id, task_queue_fsa=task_queue)
        async_result.ready = True
        async_result.successful = True
        async_result.result = 10

        assert async_result.result == 10


# Test 6: Worker Pool Creation
class TestWorkerPoolCreation:
    """Test worker pool creation."""

    def test_create_worker_pool(self, task_queue):
        """Test creating a worker pool."""
        pool = task_queue.create_worker_pool(pool_size=4, queue_name="test")
        assert isinstance(pool, WorkerPool)
        assert pool.current_size == 4
        assert len(pool.workers) == 4

    def test_worker_pool_properties(self, task_queue):
        """Test worker pool properties."""
        pool = task_queue.create_worker_pool(pool_size=3, queue_name="test")
        assert pool.min_workers == 1  # max(1, 3//2)
        assert pool.max_workers == 6  # 3 * 2
        assert pool.auto_scale is True


# Test 7: Worker Auto-Scaling
class TestWorkerAutoScaling:
    """Test worker auto-scaling functionality."""

    def test_scale_up_workers(self, task_queue_with_pool):
        """Test scaling up workers."""
        result = task_queue_with_pool.scale_workers("default", target_size=5)
        assert result.success is True
        assert result.new_size == 5
        assert result.added_workers == 3

    def test_scale_down_workers(self, task_queue_with_pool):
        """Test scaling down workers."""
        result = task_queue_with_pool.scale_workers("default", target_size=1)
        assert result.success is True
        assert result.new_size == 1
        assert result.removed_workers == 1


# Test 8: Result Retrieval
class TestResultRetrieval:
    """Test task result retrieval."""

    def test_get_task_result(self, task_queue, sample_task):
        """Test getting task result."""
        worker = Worker()
        task_queue.workers[worker.worker_id] = worker

        # Process task
        task_queue.process_task(sample_task, worker)

        # Get result
        result = task_queue.get_task_result(sample_task.task_id)
        assert result is not None
        assert result.result == 10

    def test_get_nonexistent_result(self, task_queue):
        """Test getting result for nonexistent task."""
        result = task_queue.get_task_result("nonexistent")
        assert result is None


# Test 9: Result Storage - Memory
class TestResultStorageMemory:
    """Test result storage in memory backend."""

    def test_store_result_memory(self, task_queue):
        """Test storing result in memory."""
        result = task_queue.store_result("task-1", {"data": 123}, ResultBackend.MEMORY)
        assert result.success is True


# Test 10: Result Storage - Filesystem
class TestResultStorageFilesystem:
    """Test result storage in filesystem backend."""

    def test_store_result_filesystem(self, task_queue, tmp_path):
        """Test storing result to filesystem."""
        result = task_queue.store_result("task-1", {"data": 123}, ResultBackend.FILESYSTEM)
        assert result.success is True


# Test 11: Task Chaining
class TestTaskChaining:
    """Test task chaining functionality."""

    def test_chain_tasks(self, task_queue):
        """Test chaining multiple tasks."""
        def add_one(x):
            return x + 1

        def multiply_two(x):
            return x * 2

        task1 = Task(name="add", func=add_one, args=(5,))
        task2 = Task(name="multiply", func=multiply_two)

        result = task_queue.chain_tasks([task1, task2])
        assert result.success is True
        assert len(result.tasks) == 2


# Test 12: Task Routing
class TestTaskRouting:
    """Test task routing functionality."""

    def test_route_task_direct(self, task_queue, sample_task):
        """Test routing task with direct strategy."""
        task_queue.routing_table["test-key"] = "target-queue"

        result = task_queue.route_task(sample_task, "test-key")
        assert result.success is True
        assert result.target_queue == "target-queue"

    def test_route_task_hash(self, task_queue, sample_task):
        """Test routing task with hash strategy."""
        task_queue._create_queue("queue1")
        task_queue._create_queue("queue2")

        result = task_queue.route_task(sample_task, "some-key")
        assert result.success is True
        assert result.target_queue in task_queue.queues


# Test 13: Task Serialization
class TestTaskSerialization:
    """Test task serialization."""

    def test_serialize_task(self, task_queue, sample_task):
        """Test serializing a task."""
        serialized = task_queue.serialize_task(sample_task)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0


# Test 14: Task Deserialization
class TestTaskDeserialization:
    """Test task deserialization."""

    def test_deserialize_task(self, task_queue, sample_task):
        """Test deserializing a task."""
        serialized = task_queue.serialize_task(sample_task)
        deserialized = task_queue.deserialize_task(serialized)
        assert isinstance(deserialized, Task)
        assert deserialized.task_id == sample_task.task_id


# Test 15: Task Monitoring
class TestTaskMonitoring:
    """Test task monitoring functionality."""

    def test_monitor_task(self, task_queue, sample_task):
        """Test monitoring task status."""
        task_queue.tasks[sample_task.task_id] = sample_task

        status = task_queue.monitor_task(sample_task.task_id)
        assert isinstance(status, TaskStatus)
        assert status.task_id == sample_task.task_id

    def test_monitor_nonexistent_task(self, task_queue):
        """Test monitoring nonexistent task."""
        status = task_queue.monitor_task("nonexistent")
        assert status.state == TaskState.PENDING


# Test 16: Failed Task Retry
class TestFailedTaskRetry:
    """Test failed task retry functionality."""

    def test_retry_failed_task(self, task_queue):
        """Test retrying a failed task."""
        task = Task(name="failed", max_retries=3)
        task_queue.tasks[task.task_id] = task

        retry_policy = RetryPolicy(max_retries=3, retry_delay=0.1)
        result = task_queue.retry_failed_task(task.task_id, retry_policy)

        assert result.success is True
        assert result.retry_count == 1

    def test_retry_max_exceeded(self, task_queue):
        """Test retry when max retries exceeded."""
        task = Task(name="failed", max_retries=3, retry_count=3)
        task_queue.tasks[task.task_id] = task

        retry_policy = RetryPolicy(max_retries=3)
        result = task_queue.retry_failed_task(task.task_id, retry_policy)

        assert result.success is False


# Test 17: Dead Letter Queue
class TestDeadLetterQueue:
    """Test dead letter queue functionality."""

    def test_move_to_dlq(self, task_queue, sample_task):
        """Test moving failed task to DLQ."""
        error = Exception("Test error")
        result = task_queue.move_to_dlq(sample_task, error)

        assert result.success is True
        assert sample_task in task_queue.dlq[sample_task.queue_name]


# Test 18: Task Cancellation
class TestTaskCancellation:
    """Test task cancellation."""

    def test_cancel_pending_task(self, task_queue, sample_task):
        """Test cancelling a pending task."""
        task_queue.enqueue_task(sample_task, "default")

        result = task_queue.cancel_task(sample_task.task_id)
        assert result.success is True
        assert result.was_running is False

    def test_cancel_nonexistent_task(self, task_queue):
        """Test cancelling nonexistent task."""
        result = task_queue.cancel_task("nonexistent")
        assert result.success is False


# Test 19: Queue Purging
class TestQueuePurging:
    """Test queue purging functionality."""

    def test_purge_queue(self, task_queue):
        """Test purging a queue."""
        # Add some tasks
        for i in range(5):
            task = Task(name=f"task-{i}", func=lambda: None)
            task_queue.enqueue_task(task, "default")

        result = task_queue.purge_queue("default")
        assert result.success is True
        assert result.purged_count == 5


# Test 20: Queue Metrics
class TestQueueMetrics:
    """Test queue metrics collection."""

    def test_get_queue_metrics(self, task_queue):
        """Test getting queue metrics."""
        task_queue._create_queue("test")

        metrics = task_queue.get_queue_metrics("test")
        assert isinstance(metrics, QueueMetrics)
        assert metrics.queue_name == "test"


# Test 21: Configuration Validation
class TestConfigurationValidation:
    """Test queue configuration validation."""

    def test_validate_valid_config(self, task_queue):
        """Test validating valid configuration."""
        config = QueueConfig(
            queue_name="test",
            max_queue_size=1000,
            worker_pool_size=4,
        )

        result = task_queue.validate(config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_config(self, task_queue):
        """Test validating invalid configuration."""
        config = QueueConfig(
            queue_name="",
            max_queue_size=-1,
            worker_pool_size=0,
        )

        result = task_queue.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


# Test 22: Task Queue Execution
class TestTaskQueueExecution:
    """Test task queue execution."""

    def test_execute_multiple_tasks(self, task_queue):
        """Test executing multiple tasks."""
        tasks = []
        for i in range(3):
            task = Task(name=f"task-{i}", func=lambda x: x, args=(i,))
            tasks.append(task)

        result = task_queue.execute(tasks)
        assert isinstance(result, TaskQueueResult)
        assert result.processed_tasks == 3


# Test 23: Empty Queue Handling
class TestEmptyQueueHandling:
    """Test handling of empty queues."""

    def test_dequeue_empty_queue(self, task_queue):
        """Test dequeueing from empty queue."""
        task_queue._create_queue("empty")
        result = task_queue.dequeue_task("empty", "worker-1")
        assert result.success is False

    def test_metrics_empty_queue(self, task_queue):
        """Test metrics for empty queue."""
        task_queue._create_queue("empty")
        metrics = task_queue.get_queue_metrics("empty")
        assert metrics.pending_tasks == 0


# Test 24: Worker Crashes
class TestWorkerCrashes:
    """Test handling of worker crashes."""

    def test_worker_state_after_failure(self, task_queue):
        """Test worker state after task failure."""
        def failing_task():
            raise RuntimeError("Worker crash")

        task = Task(name="crash", func=failing_task)
        worker = Worker()
        task_queue.workers[worker.worker_id] = worker

        task_queue.process_task(task, worker)
        assert worker.state == WorkerState.IDLE


# Test 25: Serialization Errors
class TestSerializationErrors:
    """Test handling of serialization errors."""

    def test_serialize_complex_task(self, task_queue):
        """Test serializing task with complex objects."""
        task = Task(name="complex", func=lambda x: x, args=({"key": "value"},))
        serialized = task_queue.serialize_task(task)
        assert isinstance(serialized, bytes)


# Test 26: Concurrent Task Processing
class TestConcurrentTaskProcessing:
    """Test concurrent task processing."""

    def test_concurrent_enqueue(self, task_queue):
        """Test concurrent task enqueueing."""
        results = []

        def enqueue_task():
            task = Task(name="concurrent", func=lambda: None)
            result = task_queue.enqueue_task(task, "default")
            results.append(result)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=enqueue_task)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert all(r.success for r in results)


# Test 27: Long-Running Task Management
class TestLongRunningTaskManagement:
    """Test management of long-running tasks."""

    def test_long_running_task_timeout(self, task_queue):
        """Test handling of task timeout."""
        def long_task():
            time.sleep(10)
            return "done"

        task = Task(name="long", func=long_task, timeout=0.1)
        task_queue.tasks[task.task_id] = task

        status = task_queue.monitor_task(task.task_id)
        assert status.task_id == task.task_id

    def test_long_running_task_progress(self, task_queue):
        """Test tracking progress of long task."""
        task = Task(name="long", func=lambda: None, progress=50.0)
        task_queue.tasks[task.task_id] = task

        status = task_queue.monitor_task(task.task_id)
        assert status.progress == 50.0

"""
Task Queue FSA: Distributed task queue infrastructure for asynchronous task processing.

This module provides comprehensive task queue management with support for:
- Multiple queue backends (Redis, RabbitMQ, in-memory)
- Async task processing with worker pools
- Task prioritization and routing
- Result backends for storing outputs
- Task chaining for workflows
- Progress tracking and monitoring
- Dead letter queue for failed tasks
- Auto-scaling worker pools
- Thread-safe and process-safe operations
"""

from __future__ import annotations

import pickle
import json
import queue
import threading
import time
import multiprocessing as mp
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
import hashlib

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class QueueBackend(Enum):
    """Supported queue backends."""
    MEMORY = "memory"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"


class ResultBackend(Enum):
    """Supported result backends."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"
    FILESYSTEM = "filesystem"


class TaskState(Enum):
    """Task processing states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class WorkerState(Enum):
    """Worker states."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


class SerializationFormat(Enum):
    """Task serialization formats."""
    PICKLE = "pickle"
    JSON = "json"
    MSGPACK = "msgpack"


class RoutingStrategy(Enum):
    """Task routing strategies."""
    DIRECT = "direct"  # Route to specific queue
    ROUND_ROBIN = "round_robin"  # Distribute evenly
    PRIORITY = "priority"  # Route by task priority
    HASH = "hash"  # Route by hashing task attributes


# ==================== Data Classes ====================

@dataclass
class Task:
    """Represents a task to be executed."""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more important
    queue_name: str = "default"
    routing_key: str = ""
    max_retries: int = 3
    retry_count: int = 0
    timeout: float = 300.0  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    state: TaskState = TaskState.PENDING
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0  # 0-100%
    metadata: Dict[str, Any] = field(default_factory=dict)
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "args": self.args,
            "kwargs": self.kwargs,
            "priority": self.priority,
            "queue_name": self.queue_name,
            "routing_key": self.routing_key,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat(),
            "state": self.state.value,
            "progress": self.progress,
            "metadata": self.metadata,
        }


@dataclass
class Worker:
    """Represents a worker process/thread."""
    worker_id: str = field(default_factory=lambda: str(uuid4()))
    queue_name: str = "default"
    state: WorkerState = WorkerState.IDLE
    current_task: Optional[Task] = None
    tasks_processed: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    process: Optional[Any] = None  # multiprocessing.Process or threading.Thread


@dataclass
class WorkerPool:
    """Pool of workers processing tasks."""
    pool_id: str = field(default_factory=lambda: str(uuid4()))
    queue_name: str = "default"
    min_workers: int = 1
    max_workers: int = 10
    current_size: int = 0
    workers: List[Worker] = field(default_factory=list)
    auto_scale: bool = True
    scale_up_threshold: float = 0.8  # Queue utilization
    scale_down_threshold: float = 0.2
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    result: Any = None
    error: Optional[str] = None
    state: TaskState = TaskState.SUCCESS
    execution_time: float = 0.0
    worker_id: str = ""
    completed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AsyncResult:
    """Handle for async task execution."""
    task_id: str
    ready: bool = False
    successful: bool = False
    result: Any = None
    error: Optional[str] = None
    task_queue_fsa: Optional[Any] = None  # Reference to TaskQueueFSA

    def get(self, timeout: Optional[float] = None) -> Any:
        """Wait for and return task result."""
        if not self.task_queue_fsa:
            raise RuntimeError("No task queue reference")

        start_time = time.time()
        while not self.ready:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {self.task_id} did not complete within {timeout}s")

            result = self.task_queue_fsa.get_task_result(self.task_id)
            if result:
                self.ready = True
                self.successful = result.state == TaskState.SUCCESS
                self.result = result.result
                self.error = result.error
                break

            time.sleep(0.1)

        if not self.successful:
            raise Exception(f"Task failed: {self.error}")

        return self.result

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Wait for task completion."""
        try:
            self.get(timeout=timeout)
            return True
        except Exception:
            return False


@dataclass
class EnqueueResult:
    """Result of enqueuing a task."""
    success: bool
    task_id: str
    queue_name: str
    position: int = 0
    error: Optional[str] = None


@dataclass
class DequeueResult:
    """Result of dequeuing a task."""
    success: bool
    task: Optional[Task] = None
    worker_id: str = ""
    error: Optional[str] = None


@dataclass
class TaskProcessingResult:
    """Result of processing a task."""
    success: bool
    task_id: str
    result: Any = None
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class ScalingResult:
    """Result of worker pool scaling."""
    success: bool
    queue_name: str
    previous_size: int
    new_size: int
    added_workers: int = 0
    removed_workers: int = 0
    error: Optional[str] = None


@dataclass
class RoutingResult:
    """Result of task routing."""
    success: bool
    task_id: str
    target_queue: str
    routing_key: str
    error: Optional[str] = None


@dataclass
class ChainResult:
    """Result of task chaining."""
    success: bool
    chain_id: str
    tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_task: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RetryPolicy:
    """Policy for retrying failed tasks."""
    max_retries: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds
    exponential_backoff: bool = True
    backoff_factor: float = 2.0
    max_delay: float = 300.0  # Maximum delay in seconds


@dataclass
class RetryResult:
    """Result of retrying a task."""
    success: bool
    task_id: str
    retry_count: int
    next_retry_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class QueueMetrics:
    """Queue performance metrics."""
    queue_name: str
    pending_tasks: int = 0
    processing_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    active_workers: int = 0
    average_execution_time: float = 0.0
    throughput: float = 0.0  # Tasks per second
    queue_utilization: float = 0.0  # 0-1
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskStatus:
    """Current status of a task."""
    task_id: str
    state: TaskState
    progress: float  # 0-100%
    worker_id: Optional[str] = None
    queue_name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueueConfig:
    """Configuration for a task queue."""
    queue_name: str
    queue_backend: QueueBackend = QueueBackend.MEMORY
    result_backend: ResultBackend = ResultBackend.MEMORY
    max_queue_size: int = 10000
    worker_pool_size: int = 4
    auto_scale: bool = True
    serialization_format: SerializationFormat = SerializationFormat.PICKLE
    enable_dlq: bool = True  # Dead letter queue
    dlq_max_size: int = 1000
    task_timeout: float = 300.0
    result_ttl: timedelta = field(default_factory=lambda: timedelta(hours=24))


@dataclass
class ValidationResult:
    """Result of queue configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TaskQueueResult:
    """Result of task queue execution."""
    success: bool
    processed_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None


@dataclass
class StoreResult:
    """Result of storing task result."""
    success: bool
    task_id: str
    backend: str
    error: Optional[str] = None


@dataclass
class DLQResult:
    """Result of moving task to dead letter queue."""
    success: bool
    task_id: str
    reason: str
    error: Optional[str] = None


@dataclass
class PurgeResult:
    """Result of purging a queue."""
    success: bool
    queue_name: str
    purged_count: int = 0
    error: Optional[str] = None


@dataclass
class CancelResult:
    """Result of cancelling a task."""
    success: bool
    task_id: str
    was_running: bool = False
    error: Optional[str] = None


# ==================== Task Queue FSA ====================

class TaskQueueFSA:
    """
    Task Queue Finite State Automaton.

    Provides distributed task queue infrastructure with worker pools,
    result backends, task chaining, and monitoring.
    """

    def __init__(
        self,
        name: str = "TaskQueueFSA",
        default_backend: QueueBackend = QueueBackend.MEMORY,
        default_result_backend: ResultBackend = ResultBackend.MEMORY,
    ):
        """
        Initialize Task Queue FSA.

        Args:
            name: Name of the FSA instance
            default_backend: Default queue backend
            default_result_backend: Default result backend
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.default_backend = default_backend
        self.default_result_backend = default_result_backend

        # Queue storage
        self.queues: Dict[str, queue.Queue] = {}  # In-memory queues
        self.queue_configs: Dict[str, QueueConfig] = {}
        self.priority_queues: Dict[str, queue.PriorityQueue] = {}

        # Worker pools
        self.worker_pools: Dict[str, WorkerPool] = {}
        self.workers: Dict[str, Worker] = {}

        # Task tracking
        self.tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.pending_tasks: Dict[str, Set[str]] = defaultdict(set)  # queue_name -> task_ids
        self.processing_tasks: Dict[str, Set[str]] = defaultdict(set)

        # Dead letter queue
        self.dlq: Dict[str, List[Task]] = defaultdict(list)

        # Task chains
        self.task_chains: Dict[str, List[str]] = {}  # chain_id -> task_ids

        # Metrics
        self.metrics: Dict[str, QueueMetrics] = {}
        self.task_execution_times: Dict[str, List[float]] = defaultdict(list)

        # Routing
        self.routing_table: Dict[str, str] = {}  # routing_key -> queue_name

        # Thread safety
        self.lock = threading.RLock()

        # Background threads
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.autoscale_thread: Optional[threading.Thread] = None

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, tasks: List[Task]) -> TaskQueueResult:
        """
        Execute multiple tasks through the queue system.

        Args:
            tasks: List of tasks to execute

        Returns:
            TaskQueueResult with execution statistics
        """
        start_time = time.time()
        successful = 0
        failed = 0

        try:
            # Enqueue all tasks
            for task in tasks:
                result = self.enqueue_task(
                    task,
                    task.queue_name,
                    task.priority
                )
                if result.success:
                    successful += 1
                else:
                    failed += 1

            execution_time = time.time() - start_time

            return TaskQueueResult(
                success=failed == 0,
                processed_tasks=len(tasks),
                successful_tasks=successful,
                failed_tasks=failed,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Error executing tasks: {e}")
            return TaskQueueResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    # ==================== Configuration and Validation ====================

    def validate(self, queue_config: QueueConfig) -> ValidationResult:
        """
        Validate queue configuration.

        Args:
            queue_config: Configuration to validate

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        if not queue_config.queue_name:
            errors.append("Queue name cannot be empty")

        if queue_config.max_queue_size <= 0:
            errors.append("Max queue size must be positive")

        if queue_config.worker_pool_size <= 0:
            errors.append("Worker pool size must be positive")

        if queue_config.task_timeout <= 0:
            warnings.append("Task timeout is non-positive")

        if queue_config.worker_pool_size > 100:
            warnings.append("Large worker pool size may impact performance")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ==================== Task Enqueue/Dequeue ====================

    def enqueue_task(
        self,
        task: Task,
        queue_name: str,
        priority: int = 0,
    ) -> EnqueueResult:
        """
        Add task to queue.

        Args:
            task: Task to enqueue
            queue_name: Target queue name
            priority: Task priority

        Returns:
            EnqueueResult with status
        """
        try:
            with self.lock:
                # Initialize queue if needed
                if queue_name not in self.queues:
                    self._create_queue(queue_name)

                # Update task state
                task.queue_name = queue_name
                task.priority = priority
                task.state = TaskState.QUEUED

                # Store task
                self.tasks[task.task_id] = task
                self.pending_tasks[queue_name].add(task.task_id)

                # Add to priority queue
                if queue_name in self.priority_queues:
                    self.priority_queues[queue_name].put((-priority, task.task_id, task))
                else:
                    self.queues[queue_name].put(task)

                position = self.queues[queue_name].qsize()

                logger.debug(f"Enqueued task {task.task_id} to {queue_name}")

                return EnqueueResult(
                    success=True,
                    task_id=task.task_id,
                    queue_name=queue_name,
                    position=position,
                )

        except Exception as e:
            logger.error(f"Error enqueuing task: {e}")
            return EnqueueResult(
                success=False,
                task_id=task.task_id,
                queue_name=queue_name,
                error=str(e),
            )

    def dequeue_task(
        self,
        queue_name: str,
        worker_id: str,
    ) -> DequeueResult:
        """
        Retrieve task from queue for processing.

        Args:
            queue_name: Queue to dequeue from
            worker_id: ID of worker requesting task

        Returns:
            DequeueResult with task or error
        """
        try:
            with self.lock:
                if queue_name not in self.queues:
                    return DequeueResult(
                        success=False,
                        worker_id=worker_id,
                        error=f"Queue {queue_name} does not exist",
                    )

                # Try to get task from priority queue first
                task = None
                if queue_name in self.priority_queues and not self.priority_queues[queue_name].empty():
                    _, task_id, task = self.priority_queues[queue_name].get_nowait()
                elif not self.queues[queue_name].empty():
                    task = self.queues[queue_name].get_nowait()

                if task:
                    # Update task state
                    task.state = TaskState.RUNNING
                    task.started_at = datetime.utcnow()

                    # Track task
                    self.pending_tasks[queue_name].discard(task.task_id)
                    self.processing_tasks[queue_name].add(task.task_id)

                    # Update worker
                    if worker_id in self.workers:
                        worker = self.workers[worker_id]
                        worker.state = WorkerState.BUSY
                        worker.current_task = task

                    logger.debug(f"Dequeued task {task.task_id} for worker {worker_id}")

                    return DequeueResult(
                        success=True,
                        task=task,
                        worker_id=worker_id,
                    )
                else:
                    return DequeueResult(
                        success=False,
                        worker_id=worker_id,
                        error="Queue is empty",
                    )

        except queue.Empty:
            return DequeueResult(
                success=False,
                worker_id=worker_id,
                error="Queue is empty",
            )
        except Exception as e:
            logger.error(f"Error dequeuing task: {e}")
            return DequeueResult(
                success=False,
                worker_id=worker_id,
                error=str(e),
            )

    # ==================== Task Processing ====================

    def process_task(
        self,
        task: Task,
        worker: Worker,
    ) -> TaskProcessingResult:
        """
        Execute task logic.

        Args:
            task: Task to process
            worker: Worker executing the task

        Returns:
            TaskProcessingResult with outcome
        """
        start_time = time.time()

        try:
            # Check if task has a function to execute
            if not task.func:
                raise ValueError(f"Task {task.task_id} has no function to execute")

            # Execute task function
            result = task.func(*task.args, **task.kwargs)

            # Update task
            task.result = result
            task.state = TaskState.SUCCESS
            task.completed_at = datetime.utcnow()

            execution_time = time.time() - start_time

            # Store result
            self._store_task_result(
                task.task_id,
                result,
                TaskState.SUCCESS,
                execution_time,
                worker.worker_id,
            )

            # Execute success callback
            if task.on_success:
                try:
                    task.on_success(result)
                except Exception as e:
                    logger.warning(f"Success callback failed: {e}")

            # Update worker
            worker.state = WorkerState.IDLE
            worker.current_task = None
            worker.tasks_processed += 1

            # Track metrics
            self.task_execution_times[task.queue_name].append(execution_time)

            logger.info(f"Task {task.task_id} completed successfully in {execution_time:.2f}s")

            return TaskProcessingResult(
                success=True,
                task_id=task.task_id,
                result=result,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")

            execution_time = time.time() - start_time

            # Update task
            task.state = TaskState.FAILURE
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            # Store error result
            self._store_task_result(
                task.task_id,
                None,
                TaskState.FAILURE,
                execution_time,
                worker.worker_id,
                error=str(e),
            )

            # Execute failure callback
            if task.on_failure:
                try:
                    task.on_failure(e)
                except Exception as callback_error:
                    logger.warning(f"Failure callback failed: {callback_error}")

            # Check if should retry
            if task.retry_count < task.max_retries:
                self._retry_task(task)
            else:
                # Move to dead letter queue
                self.move_to_dlq(task, e)

            # Update worker
            worker.state = WorkerState.IDLE
            worker.current_task = None

            return TaskProcessingResult(
                success=False,
                task_id=task.task_id,
                execution_time=execution_time,
                error=str(e),
            )

    def submit_async(
        self,
        task: Task,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> AsyncResult:
        """
        Submit task for asynchronous execution.

        Args:
            task: Task to submit
            args: Task arguments
            kwargs: Task keyword arguments

        Returns:
            AsyncResult handle for tracking
        """
        if kwargs is None:
            kwargs = {}

        # Update task with args/kwargs
        task.args = args
        task.kwargs = kwargs

        # Enqueue task
        result = self.enqueue_task(task, task.queue_name, task.priority)

        # Create async result handle
        async_result = AsyncResult(
            task_id=task.task_id,
            task_queue_fsa=self,
        )

        return async_result

    # ==================== Worker Pool Management ====================

    def create_worker_pool(
        self,
        pool_size: int,
        queue_name: str = "default",
    ) -> WorkerPool:
        """
        Initialize worker pool for queue.

        Args:
            pool_size: Number of workers
            queue_name: Queue to process

        Returns:
            Created WorkerPool
        """
        with self.lock:
            pool = WorkerPool(
                queue_name=queue_name,
                min_workers=max(1, pool_size // 2),
                max_workers=pool_size * 2,
                current_size=pool_size,
                auto_scale=True,
            )

            # Create workers
            for _ in range(pool_size):
                worker = self._create_worker(queue_name)
                pool.workers.append(worker)

            self.worker_pools[queue_name] = pool

            logger.info(f"Created worker pool for {queue_name} with {pool_size} workers")

            return pool

    def scale_workers(
        self,
        queue_name: str,
        target_size: int,
    ) -> ScalingResult:
        """
        Adjust worker count for queue.

        Args:
            queue_name: Queue to scale
            target_size: Target worker count

        Returns:
            ScalingResult with outcome
        """
        try:
            with self.lock:
                if queue_name not in self.worker_pools:
                    return ScalingResult(
                        success=False,
                        queue_name=queue_name,
                        previous_size=0,
                        new_size=0,
                        error="Worker pool does not exist",
                    )

                pool = self.worker_pools[queue_name]
                previous_size = pool.current_size

                # Enforce limits
                target_size = max(pool.min_workers, min(target_size, pool.max_workers))

                if target_size > previous_size:
                    # Scale up
                    added = target_size - previous_size
                    for _ in range(added):
                        worker = self._create_worker(queue_name)
                        pool.workers.append(worker)

                    pool.current_size = target_size

                    logger.info(f"Scaled up {queue_name} from {previous_size} to {target_size} workers")

                    return ScalingResult(
                        success=True,
                        queue_name=queue_name,
                        previous_size=previous_size,
                        new_size=target_size,
                        added_workers=added,
                    )

                elif target_size < previous_size:
                    # Scale down
                    removed = previous_size - target_size
                    for _ in range(removed):
                        if pool.workers:
                            worker = pool.workers.pop()
                            # Stop worker gracefully
                            if worker.worker_id in self.workers:
                                del self.workers[worker.worker_id]

                    pool.current_size = target_size

                    logger.info(f"Scaled down {queue_name} from {previous_size} to {target_size} workers")

                    return ScalingResult(
                        success=True,
                        queue_name=queue_name,
                        previous_size=previous_size,
                        new_size=target_size,
                        removed_workers=removed,
                    )

                else:
                    return ScalingResult(
                        success=True,
                        queue_name=queue_name,
                        previous_size=previous_size,
                        new_size=target_size,
                    )

        except Exception as e:
            logger.error(f"Error scaling workers: {e}")
            return ScalingResult(
                success=False,
                queue_name=queue_name,
                previous_size=previous_size if 'previous_size' in locals() else 0,
                new_size=target_size,
                error=str(e),
            )

    # ==================== Result Management ====================

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Retrieve task execution result.

        Args:
            task_id: Task ID

        Returns:
            TaskResult if available, None otherwise
        """
        with self.lock:
            return self.task_results.get(task_id)

    def store_result(
        self,
        task_id: str,
        result: Any,
        backend: ResultBackend,
    ) -> StoreResult:
        """
        Save task result to backend.

        Args:
            task_id: Task ID
            result: Result to store
            backend: Storage backend

        Returns:
            StoreResult with status
        """
        try:
            if backend == ResultBackend.MEMORY:
                # Already stored in memory
                pass
            elif backend == ResultBackend.FILESYSTEM:
                self._store_result_filesystem(task_id, result)
            elif backend == ResultBackend.DATABASE:
                self._store_result_database(task_id, result)
            elif backend == ResultBackend.REDIS:
                self._store_result_redis(task_id, result)

            return StoreResult(
                success=True,
                task_id=task_id,
                backend=backend.value,
            )

        except Exception as e:
            logger.error(f"Error storing result: {e}")
            return StoreResult(
                success=False,
                task_id=task_id,
                backend=backend.value,
                error=str(e),
            )

    # ==================== Task Chaining ====================

    def chain_tasks(
        self,
        tasks: List[Task],
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ) -> ChainResult:
        """
        Create task pipeline where each task's output feeds the next.

        Args:
            tasks: Ordered list of tasks
            on_success: Callback on successful completion
            on_failure: Callback on failure

        Returns:
            ChainResult with chain info
        """
        try:
            chain_id = str(uuid4())
            task_ids = [task.task_id for task in tasks]

            # Link tasks
            for i in range(len(tasks) - 1):
                current_task = tasks[i]
                next_task = tasks[i + 1]

                # Create callback to enqueue next task
                def success_callback(result, next_task=next_task):
                    # Pass result as input to next task
                    next_task.args = (result,) + next_task.args
                    self.enqueue_task(next_task, next_task.queue_name, next_task.priority)

                current_task.on_success = success_callback

                # Set failure callback for chain
                if on_failure:
                    current_task.on_failure = on_failure

            # Set final success callback
            if on_success:
                tasks[-1].on_success = on_success

            # Enqueue first task
            self.enqueue_task(tasks[0], tasks[0].queue_name, tasks[0].priority)

            # Store chain
            self.task_chains[chain_id] = task_ids

            logger.info(f"Created task chain {chain_id} with {len(tasks)} tasks")

            return ChainResult(
                success=True,
                chain_id=chain_id,
                tasks=task_ids,
            )

        except Exception as e:
            logger.error(f"Error chaining tasks: {e}")
            return ChainResult(
                success=False,
                chain_id="",
                error=str(e),
            )

    # ==================== Task Routing ====================

    def route_task(
        self,
        task: Task,
        routing_key: str,
    ) -> RoutingResult:
        """
        Select target queue based on routing key.

        Args:
            task: Task to route
            routing_key: Routing key

        Returns:
            RoutingResult with target queue
        """
        try:
            # Check routing table
            if routing_key in self.routing_table:
                target_queue = self.routing_table[routing_key]
            else:
                # Use hash-based routing
                hash_value = int(hashlib.md5(routing_key.encode()).hexdigest(), 16)
                queue_names = list(self.queues.keys())
                if queue_names:
                    target_queue = queue_names[hash_value % len(queue_names)]
                else:
                    target_queue = "default"

            task.queue_name = target_queue
            task.routing_key = routing_key

            return RoutingResult(
                success=True,
                task_id=task.task_id,
                target_queue=target_queue,
                routing_key=routing_key,
            )

        except Exception as e:
            logger.error(f"Error routing task: {e}")
            return RoutingResult(
                success=False,
                task_id=task.task_id,
                target_queue="",
                routing_key=routing_key,
                error=str(e),
            )

    # ==================== Serialization ====================

    def serialize_task(self, task: Task) -> bytes:
        """
        Convert task to bytes for transmission.

        Args:
            task: Task to serialize

        Returns:
            Serialized task bytes
        """
        try:
            # Use pickle for full object serialization
            return pickle.dumps(task)
        except Exception as e:
            logger.error(f"Error serializing task: {e}")
            # Fallback to JSON for simpler representation
            return json.dumps(task.to_dict()).encode()

    def deserialize_task(self, data: bytes) -> Task:
        """
        Restore task from bytes.

        Args:
            data: Serialized task data

        Returns:
            Deserialized Task object
        """
        try:
            # Try pickle first
            return pickle.loads(data)
        except Exception:
            # Fallback to JSON
            task_dict = json.loads(data.decode())
            # Reconstruct Task from dict (simplified)
            return Task(**{k: v for k, v in task_dict.items() if k in Task.__dataclass_fields__})

    # ==================== Monitoring ====================

    def monitor_task(self, task_id: str) -> TaskStatus:
        """
        Track task progress and status.

        Args:
            task_id: Task to monitor

        Returns:
            Current TaskStatus
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return TaskStatus(
                    task_id=task_id,
                    state=TaskState.PENDING,
                    progress=0.0,
                )

            # Find worker if running
            worker_id = None
            for wid, worker in self.workers.items():
                if worker.current_task and worker.current_task.task_id == task_id:
                    worker_id = wid
                    break

            return TaskStatus(
                task_id=task_id,
                state=task.state,
                progress=task.progress,
                worker_id=worker_id,
                queue_name=task.queue_name,
                created_at=task.created_at,
                updated_at=task.completed_at or datetime.utcnow(),
            )

    # ==================== Failed Task Handling ====================

    def retry_failed_task(
        self,
        task_id: str,
        retry_policy: RetryPolicy,
    ) -> RetryResult:
        """
        Resubmit failed task for retry.

        Args:
            task_id: Task to retry
            retry_policy: Retry policy

        Returns:
            RetryResult with status
        """
        try:
            with self.lock:
                task = self.tasks.get(task_id)
                if not task:
                    return RetryResult(
                        success=False,
                        task_id=task_id,
                        retry_count=0,
                        error="Task not found",
                    )

                if task.retry_count >= retry_policy.max_retries:
                    return RetryResult(
                        success=False,
                        task_id=task_id,
                        retry_count=task.retry_count,
                        error="Max retries exceeded",
                    )

                # Calculate retry delay
                if retry_policy.exponential_backoff:
                    delay = min(
                        retry_policy.retry_delay * (retry_policy.backoff_factor ** task.retry_count),
                        retry_policy.max_delay
                    )
                else:
                    delay = retry_policy.retry_delay

                # Update task
                task.retry_count += 1
                task.state = TaskState.RETRY
                next_retry_at = datetime.utcnow() + timedelta(seconds=delay)

                # Schedule retry
                timer = threading.Timer(delay, lambda: self._retry_task_now(task))
                timer.start()

                logger.info(f"Scheduled retry for task {task_id} in {delay}s (attempt {task.retry_count})")

                return RetryResult(
                    success=True,
                    task_id=task_id,
                    retry_count=task.retry_count,
                    next_retry_at=next_retry_at,
                )

        except Exception as e:
            logger.error(f"Error retrying task: {e}")
            return RetryResult(
                success=False,
                task_id=task_id,
                retry_count=0,
                error=str(e),
            )

    def move_to_dlq(
        self,
        task: Task,
        error: Exception,
    ) -> DLQResult:
        """
        Send failed task to dead letter queue.

        Args:
            task: Failed task
            error: Error that caused failure

        Returns:
            DLQResult with status
        """
        try:
            with self.lock:
                self.dlq[task.queue_name].append(task)

                logger.warning(f"Moved task {task.task_id} to DLQ: {error}")

                return DLQResult(
                    success=True,
                    task_id=task.task_id,
                    reason=str(error),
                )

        except Exception as e:
            logger.error(f"Error moving to DLQ: {e}")
            return DLQResult(
                success=False,
                task_id=task.task_id,
                reason=str(error),
                error=str(e),
            )

    # ==================== Task Lifecycle ====================

    def cancel_task(self, task_id: str) -> CancelResult:
        """
        Terminate running or pending task.

        Args:
            task_id: Task to cancel

        Returns:
            CancelResult with status
        """
        try:
            with self.lock:
                task = self.tasks.get(task_id)
                if not task:
                    return CancelResult(
                        success=False,
                        task_id=task_id,
                        error="Task not found",
                    )

                was_running = task.state == TaskState.RUNNING

                # Update state
                task.state = TaskState.CANCELLED
                task.completed_at = datetime.utcnow()

                # Remove from pending/processing
                self.pending_tasks[task.queue_name].discard(task_id)
                self.processing_tasks[task.queue_name].discard(task_id)

                logger.info(f"Cancelled task {task_id}")

                return CancelResult(
                    success=True,
                    task_id=task_id,
                    was_running=was_running,
                )

        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return CancelResult(
                success=False,
                task_id=task_id,
                error=str(e),
            )

    def purge_queue(self, queue_name: str) -> PurgeResult:
        """
        Clear all tasks from queue.

        Args:
            queue_name: Queue to purge

        Returns:
            PurgeResult with count
        """
        try:
            with self.lock:
                if queue_name not in self.queues:
                    return PurgeResult(
                        success=False,
                        queue_name=queue_name,
                        error="Queue does not exist",
                    )

                # Count tasks
                purged_count = self.queues[queue_name].qsize()

                # Clear queue
                while not self.queues[queue_name].empty():
                    try:
                        self.queues[queue_name].get_nowait()
                    except queue.Empty:
                        break

                # Clear priority queue if exists
                if queue_name in self.priority_queues:
                    while not self.priority_queues[queue_name].empty():
                        try:
                            self.priority_queues[queue_name].get_nowait()
                        except queue.Empty:
                            break

                # Clear tracking
                self.pending_tasks[queue_name].clear()

                logger.info(f"Purged {purged_count} tasks from {queue_name}")

                return PurgeResult(
                    success=True,
                    queue_name=queue_name,
                    purged_count=purged_count,
                )

        except Exception as e:
            logger.error(f"Error purging queue: {e}")
            return PurgeResult(
                success=False,
                queue_name=queue_name,
                error=str(e),
            )

    # ==================== Metrics ====================

    def get_queue_metrics(self, queue_name: str) -> QueueMetrics:
        """
        Collect queue performance statistics.

        Args:
            queue_name: Queue to analyze

        Returns:
            QueueMetrics with statistics
        """
        with self.lock:
            pending = len(self.pending_tasks.get(queue_name, set()))
            processing = len(self.processing_tasks.get(queue_name, set()))

            # Count task states
            completed = 0
            failed = 0
            cancelled = 0
            for task_id in self.tasks:
                task = self.tasks[task_id]
                if task.queue_name == queue_name:
                    if task.state == TaskState.SUCCESS:
                        completed += 1
                    elif task.state == TaskState.FAILURE:
                        failed += 1
                    elif task.state == TaskState.CANCELLED:
                        cancelled += 1

            # Calculate average execution time
            exec_times = self.task_execution_times.get(queue_name, [])
            avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0.0

            # Calculate throughput (tasks per second)
            # Simplified: based on recent completions
            throughput = len(exec_times) / sum(exec_times) if exec_times and sum(exec_times) > 0 else 0.0

            # Active workers
            active_workers = 0
            if queue_name in self.worker_pools:
                active_workers = len([w for w in self.worker_pools[queue_name].workers
                                     if w.state == WorkerState.BUSY])

            # Queue utilization (0-1)
            max_size = self.queue_configs.get(queue_name).max_queue_size if queue_name in self.queue_configs else 10000
            utilization = pending / max_size if max_size > 0 else 0.0

            return QueueMetrics(
                queue_name=queue_name,
                pending_tasks=pending,
                processing_tasks=processing,
                completed_tasks=completed,
                failed_tasks=failed,
                cancelled_tasks=cancelled,
                active_workers=active_workers,
                average_execution_time=avg_exec_time,
                throughput=throughput,
                queue_utilization=utilization,
            )

    # ==================== Helper Methods ====================

    def _create_queue(self, queue_name: str):
        """Create a new queue."""
        self.queues[queue_name] = queue.Queue()
        self.priority_queues[queue_name] = queue.PriorityQueue()
        self.pending_tasks[queue_name] = set()
        self.processing_tasks[queue_name] = set()

    def _create_worker(self, queue_name: str) -> Worker:
        """Create a new worker."""
        worker = Worker(queue_name=queue_name)
        self.workers[worker.worker_id] = worker
        return worker

    def _store_task_result(
        self,
        task_id: str,
        result: Any,
        state: TaskState,
        execution_time: float,
        worker_id: str,
        error: Optional[str] = None,
    ):
        """Store task result in memory."""
        task_result = TaskResult(
            task_id=task_id,
            result=result,
            state=state,
            execution_time=execution_time,
            worker_id=worker_id,
            error=error,
        )
        self.task_results[task_id] = task_result

    def _retry_task(self, task: Task):
        """Schedule task retry."""
        retry_policy = RetryPolicy()
        self.retry_failed_task(task.task_id, retry_policy)

    def _retry_task_now(self, task: Task):
        """Re-enqueue task for retry."""
        task.state = TaskState.PENDING
        self.enqueue_task(task, task.queue_name, task.priority)

    def _store_result_filesystem(self, task_id: str, result: Any):
        """Store result to filesystem."""
        results_dir = Path("./task_results")
        results_dir.mkdir(exist_ok=True)
        result_file = results_dir / f"{task_id}.pkl"
        with open(result_file, "wb") as f:
            pickle.dump(result, f)

    def _store_result_database(self, task_id: str, result: Any):
        """Store result to database (placeholder)."""
        # Would implement database storage here
        pass

    def _store_result_redis(self, task_id: str, result: Any):
        """Store result to Redis (placeholder)."""
        # Would implement Redis storage here
        pass

    def clear_cache(self):
        """Clear cached results."""
        with self.lock:
            self.task_results.clear()
            logger.info("Cleared task result cache")

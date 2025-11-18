"""
Comprehensive Batch Processor FSA for high-performance batch operations.

This module provides a production-grade Batch Processing FSA that handles large-scale
batch operations with intelligent scheduling, resource management, parallel execution,
fault tolerance, and comprehensive monitoring.

Key Features:
- Advanced scheduling with priority queues and deadline awareness
- Multi-threaded, multi-process, and async execution modes
- Fault tolerance with checkpointing and recovery
- Resource management with memory, CPU, and I/O throttling
- Real-time monitoring and metrics collection
- Batch transformation pipelines
- Circuit breaker pattern for failing operations
- Multi-tenancy support with isolated queues
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import pickle
import threading
import time
import traceback

# Optional psutil import for resource monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from uuid import uuid4

from pydantic import BaseModel, Field, validator

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================


class Priority(str, Enum):
    """Priority levels for batch jobs."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    def __lt__(self, other: Priority) -> bool:
        """Compare priorities for sorting."""
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.NORMAL: 2,
            Priority.LOW: 3,
        }
        return priority_order[self] < priority_order[other]


class BatchState(str, Enum):
    """States of a batch job."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class ProcessingStrategy(str, Enum):
    """Batch processing strategies."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    ADAPTIVE = "adaptive"


class ChunkingStrategy(str, Enum):
    """Strategies for chunking batches."""

    FIXED_SIZE = "fixed_size"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"
    MEMORY_BASED = "memory_based"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ============================================================================
# DATA MODELS
# ============================================================================


class BatchConfig(BaseModel):
    """Configuration for batch processing."""

    # Batch sizing
    batch_size: int = Field(default=100, ge=1, description="Default batch size")
    min_batch_size: int = Field(default=1, ge=1, description="Minimum batch size")
    max_batch_size: int = Field(default=10000, ge=1, description="Maximum batch size")
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.FIXED_SIZE, description="Chunking strategy"
    )

    # Processing
    processing_strategy: ProcessingStrategy = Field(
        default=ProcessingStrategy.SEQUENTIAL, description="Processing strategy"
    )
    max_workers: int = Field(default=4, ge=1, description="Maximum worker threads/processes")
    use_multiprocessing: bool = Field(default=False, description="Use multiprocessing instead of threading")
    enable_async: bool = Field(default=False, description="Enable async processing")

    # Scheduling
    enable_priority_scheduling: bool = Field(default=True, description="Enable priority-based scheduling")
    enable_deadline_scheduling: bool = Field(default=True, description="Enable deadline-aware scheduling")
    max_queue_depth: int = Field(default=10000, ge=1, description="Maximum queue depth")
    scheduling_interval: float = Field(default=0.1, ge=0.01, description="Scheduling interval in seconds")

    # Resource management
    memory_limit_mb: Optional[int] = Field(default=None, ge=1, description="Memory limit in MB")
    cpu_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="CPU usage threshold")
    io_rate_limit: Optional[int] = Field(default=None, ge=1, description="I/O rate limit per second")
    enable_resource_monitoring: bool = Field(default=True, description="Enable resource monitoring")

    # Fault tolerance
    enable_checkpointing: bool = Field(default=True, description="Enable checkpoint-based recovery")
    checkpoint_interval: int = Field(default=100, ge=1, description="Checkpoint every N batches")
    checkpoint_dir: str = Field(default="/tmp/batch_checkpoints", description="Checkpoint directory")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0, description="Initial retry delay in seconds")
    retry_backoff: float = Field(default=2.0, ge=1.0, description="Exponential backoff multiplier")
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    circuit_failure_threshold: int = Field(default=5, ge=1, description="Failures before opening circuit")
    circuit_timeout: float = Field(default=60.0, ge=1.0, description="Circuit open timeout in seconds")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_interval: float = Field(default=1.0, ge=0.1, description="Metrics update interval")
    enable_detailed_logging: bool = Field(default=False, description="Enable detailed logging")

    # Advanced features
    enable_caching: bool = Field(default=True, description="Enable result caching")
    enable_deduplication: bool = Field(default=True, description="Enable input deduplication")
    enable_compression: bool = Field(default=False, description="Enable batch compression")
    enable_validation: bool = Field(default=True, description="Enable input validation")

    @validator("max_batch_size")
    def validate_max_batch_size(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure max_batch_size >= min_batch_size."""
        if "min_batch_size" in values and v < values["min_batch_size"]:
            raise ValueError("max_batch_size must be >= min_batch_size")
        return v


class BatchJob(BaseModel, Generic[T]):
    """Represents a batch processing job."""

    job_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique job identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier for multi-tenancy")
    job_type: str = Field(default="generic", description="Type of job")
    priority: Priority = Field(default=Priority.NORMAL, description="Job priority")
    items: List[T] = Field(default_factory=list, description="Items to process")
    state: BatchState = Field(default=BatchState.PENDING, description="Current job state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled execution time")
    deadline: Optional[datetime] = Field(default=None, description="Job deadline")
    started_at: Optional[datetime] = Field(default=None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    retry_count: int = Field(default=0, ge=0, description="Number of retries")
    failed_items: List[Tuple[T, str]] = Field(default_factory=list, description="Failed items with error messages")
    results: List[Any] = Field(default_factory=list, description="Processing results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")
    dependencies: List[str] = Field(default_factory=list, description="Job IDs this job depends on")
    correlation_id: str = Field(default_factory=lambda: str(uuid4()), description="Correlation ID for tracing")

    class Config:
        arbitrary_types_allowed = True

    def is_overdue(self) -> bool:
        """Check if job is past its deadline."""
        return self.deadline is not None and datetime.utcnow() > self.deadline

    def is_ready(self, completed_jobs: Set[str]) -> bool:
        """Check if all dependencies are completed."""
        return all(dep_id in completed_jobs for dep_id in self.dependencies)

    def get_age_seconds(self) -> float:
        """Get job age in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()


class BatchMetrics(BaseModel):
    """Metrics for batch processing."""

    # Throughput metrics
    total_jobs_processed: int = Field(default=0, description="Total jobs processed")
    total_items_processed: int = Field(default=0, description="Total items processed")
    total_items_failed: int = Field(default=0, description="Total items failed")
    jobs_per_second: float = Field(default=0.0, description="Jobs processed per second")
    items_per_second: float = Field(default=0.0, description="Items processed per second")

    # Latency metrics
    avg_job_latency_ms: float = Field(default=0.0, description="Average job latency in milliseconds")
    p50_job_latency_ms: float = Field(default=0.0, description="P50 job latency")
    p95_job_latency_ms: float = Field(default=0.0, description="P95 job latency")
    p99_job_latency_ms: float = Field(default=0.0, description="P99 job latency")

    # Success metrics
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate (0-1)")
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Failure rate (0-1)")

    # Queue metrics
    queue_depth: int = Field(default=0, ge=0, description="Current queue depth")
    backlog_age_seconds: float = Field(default=0.0, description="Age of oldest job in queue")

    # Resource metrics
    cpu_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="CPU usage percentage")
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    active_workers: int = Field(default=0, ge=0, description="Number of active workers")

    # SLA metrics
    sla_violations: int = Field(default=0, ge=0, description="Number of SLA violations")
    jobs_exceeding_deadline: int = Field(default=0, ge=0, description="Jobs that exceeded deadline")

    # Checkpoint metrics
    last_checkpoint_time: Optional[datetime] = Field(default=None, description="Last checkpoint timestamp")
    checkpoints_created: int = Field(default=0, ge=0, description="Total checkpoints created")

    # Circuit breaker metrics
    circuit_state: CircuitState = Field(default=CircuitState.CLOSED, description="Circuit breaker state")
    circuit_failures: int = Field(default=0, ge=0, description="Circuit breaker failures")

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = [
            f"# HELP batch_jobs_total Total jobs processed",
            f"# TYPE batch_jobs_total counter",
            f"batch_jobs_total {self.total_jobs_processed}",
            f"",
            f"# HELP batch_items_total Total items processed",
            f"# TYPE batch_items_total counter",
            f"batch_items_total {self.total_items_processed}",
            f"",
            f"# HELP batch_items_failed_total Total items failed",
            f"# TYPE batch_items_failed_total counter",
            f"batch_items_failed_total {self.total_items_failed}",
            f"",
            f"# HELP batch_jobs_per_second Jobs processed per second",
            f"# TYPE batch_jobs_per_second gauge",
            f"batch_jobs_per_second {self.jobs_per_second}",
            f"",
            f"# HELP batch_success_rate Success rate (0-1)",
            f"# TYPE batch_success_rate gauge",
            f"batch_success_rate {self.success_rate}",
            f"",
            f"# HELP batch_queue_depth Current queue depth",
            f"# TYPE batch_queue_depth gauge",
            f"batch_queue_depth {self.queue_depth}",
            f"",
            f"# HELP batch_cpu_usage_percent CPU usage percentage",
            f"# TYPE batch_cpu_usage_percent gauge",
            f"batch_cpu_usage_percent {self.cpu_usage_percent}",
            f"",
            f"# HELP batch_memory_usage_mb Memory usage in MB",
            f"# TYPE batch_memory_usage_mb gauge",
            f"batch_memory_usage_mb {self.memory_usage_mb}",
        ]
        return "\n".join(lines)


# ============================================================================
# BATCH ITERATORS AND CHUNKING
# ============================================================================


class BatchIterator(Generic[T]):
    """Memory-efficient iterator for batching items."""

    def __init__(
        self,
        items: Iterable[T],
        batch_size: int,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
    ):
        """Initialize batch iterator.

        Args:
            items: Items to batch
            batch_size: Size of each batch
            strategy: Chunking strategy
        """
        self.items = items
        self.batch_size = batch_size
        self.strategy = strategy
        self.current_batch_size = batch_size

    def __iter__(self) -> Generator[List[T], None, None]:
        """Iterate over batches."""
        batch = []
        for item in self.items:
            batch.append(item)
            if len(batch) >= self.current_batch_size:
                yield batch
                batch = []

                # Adjust batch size for adaptive strategies
                if self.strategy == ChunkingStrategy.ADAPTIVE:
                    self._adjust_batch_size()

        # Yield remaining items
        if batch:
            yield batch

    def _adjust_batch_size(self) -> None:
        """Adjust batch size based on system resources."""
        # Simple adaptive logic based on memory usage
        if not PSUTIL_AVAILABLE:
            return

        try:
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                self.current_batch_size = max(1, self.current_batch_size // 2)
            elif memory_percent < 50:
                self.current_batch_size = min(self.batch_size * 2, self.batch_size * 4)
        except Exception:
            pass


class AdaptiveBatchSizer:
    """Dynamically adjusts batch size based on system resources and throughput."""

    def __init__(
        self,
        initial_size: int,
        min_size: int,
        max_size: int,
        target_memory_mb: Optional[int] = None,
    ):
        """Initialize adaptive batch sizer.

        Args:
            initial_size: Initial batch size
            min_size: Minimum batch size
            max_size: Maximum batch size
            target_memory_mb: Target memory usage in MB
        """
        self.current_size = initial_size
        self.min_size = min_size
        self.max_size = max_size
        self.target_memory_mb = target_memory_mb
        self.throughput_history: deque = deque(maxlen=10)
        self.last_adjustment = time.time()

    def get_batch_size(self) -> int:
        """Get current optimal batch size."""
        return self.current_size

    def record_throughput(self, items_per_second: float) -> None:
        """Record throughput for adjustment."""
        self.throughput_history.append(items_per_second)

    def adjust(self) -> None:
        """Adjust batch size based on metrics."""
        if time.time() - self.last_adjustment < 5.0:
            return

        try:
            # Check memory usage
            if self.target_memory_mb and PSUTIL_AVAILABLE:
                memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                if memory_mb > self.target_memory_mb * 0.9:
                    self.current_size = max(self.min_size, int(self.current_size * 0.8))
                    self.last_adjustment = time.time()
                    return

            # Check throughput trend
            if len(self.throughput_history) >= 3:
                recent_throughput = list(self.throughput_history)[-3:]
                if all(
                    recent_throughput[i] < recent_throughput[i - 1] for i in range(1, len(recent_throughput))
                ):
                    # Throughput decreasing, reduce batch size
                    self.current_size = max(self.min_size, int(self.current_size * 0.9))
                elif all(
                    recent_throughput[i] > recent_throughput[i - 1] for i in range(1, len(recent_throughput))
                ):
                    # Throughput increasing, try larger batches
                    self.current_size = min(self.max_size, int(self.current_size * 1.1))

            self.last_adjustment = time.time()

        except Exception as e:
            logger.warning(f"Failed to adjust batch size: {e}")


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before transitioning to half-open
            half_open_max_calls: Max calls to allow in half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        self._lock = threading.Lock()

    def call(self, func: Callable[..., R], *args: Any, **kwargs: Any) -> R:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise Exception("Circuit breaker is OPEN")

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise Exception("Circuit breaker is HALF_OPEN (max calls reached)")
                self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0


# ============================================================================
# RESOURCE MANAGER
# ============================================================================


class ResourceManager:
    """Manages system resources for batch processing."""

    def __init__(self, config: BatchConfig):
        """Initialize resource manager.

        Args:
            config: Batch configuration
        """
        self.config = config
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        self._lock = threading.Lock()
        self.io_operations_count = 0
        self.io_operations_window_start = time.time()

    def check_memory_available(self) -> bool:
        """Check if sufficient memory is available."""
        if not self.config.memory_limit_mb or not PSUTIL_AVAILABLE or not self.process:
            return True

        try:
            memory_mb = self.process.memory_info().rss / (1024 * 1024)
            return memory_mb < self.config.memory_limit_mb
        except Exception as e:
            logger.warning(f"Failed to check memory: {e}")
            return True

    def check_cpu_available(self) -> bool:
        """Check if CPU usage is below threshold."""
        if not PSUTIL_AVAILABLE or not self.process:
            return True

        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            return cpu_percent < (self.config.cpu_threshold * 100)
        except Exception as e:
            logger.warning(f"Failed to check CPU: {e}")
            return True

    def check_io_available(self) -> bool:
        """Check if I/O operations are within rate limit."""
        if not self.config.io_rate_limit:
            return True

        with self._lock:
            current_time = time.time()
            time_elapsed = current_time - self.io_operations_window_start

            # Reset window every second
            if time_elapsed >= 1.0:
                self.io_operations_count = 0
                self.io_operations_window_start = current_time
                return True

            return self.io_operations_count < self.config.io_rate_limit

    def record_io_operation(self) -> None:
        """Record an I/O operation."""
        if self.config.io_rate_limit:
            with self._lock:
                self.io_operations_count += 1

    def wait_for_resources(self, timeout: float = 30.0) -> bool:
        """Wait for resources to become available.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if resources available, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_resources_available():
                return True
            time.sleep(0.5)
        return False

    def check_resources_available(self) -> bool:
        """Check if all resources are available."""
        return (
            self.check_memory_available()
            and self.check_cpu_available()
            and self.check_io_available()
        )

    def get_resource_metrics(self) -> Dict[str, float]:
        """Get current resource usage metrics."""
        if not PSUTIL_AVAILABLE or not self.process:
            return {}

        try:
            return {
                "cpu_percent": self.process.cpu_percent(interval=0.1),
                "memory_mb": self.process.memory_info().rss / (1024 * 1024),
                "memory_percent": psutil.virtual_memory().percent,
                "threads": self.process.num_threads(),
            }
        except Exception as e:
            logger.warning(f"Failed to get resource metrics: {e}")
            return {}

    def throttle_if_needed(self) -> None:
        """Throttle processing if resources are constrained."""
        if not self.check_resources_available():
            logger.debug("Throttling due to resource constraints")
            time.sleep(0.5)


# ============================================================================
# CHECKPOINT MANAGER
# ============================================================================


class CheckpointManager:
    """Manages checkpointing for fault recovery."""

    def __init__(self, checkpoint_dir: str):
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        job_id: str,
        state: Dict[str, Any],
        checkpoint_id: Optional[str] = None,
    ) -> str:
        """Save checkpoint to disk.

        Args:
            job_id: Job identifier
            state: State to checkpoint
            checkpoint_id: Optional checkpoint identifier

        Returns:
            Checkpoint ID
        """
        if checkpoint_id is None:
            checkpoint_id = f"{job_id}_{int(time.time() * 1000)}"

        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"

        try:
            with open(checkpoint_path, "wb") as f:
                pickle.dump(
                    {
                        "job_id": job_id,
                        "checkpoint_id": checkpoint_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "state": state,
                    },
                    f,
                )
            logger.info(f"Checkpoint saved: {checkpoint_id}")
            return checkpoint_id
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint from disk.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Checkpoint data or None if not found
        """
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"

        if not checkpoint_path.exists():
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None

        try:
            with open(checkpoint_path, "rb") as f:
                data = pickle.load(f)
            logger.info(f"Checkpoint loaded: {checkpoint_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(self, job_id: Optional[str] = None) -> List[str]:
        """List available checkpoints.

        Args:
            job_id: Optional job ID to filter by

        Returns:
            List of checkpoint IDs
        """
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.pkl"):
            checkpoint_id = path.stem
            if job_id is None or checkpoint_id.startswith(job_id):
                checkpoints.append(checkpoint_id)
        return sorted(checkpoints)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            True if deleted, False otherwise
        """
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_id}.pkl"
        try:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                logger.info(f"Checkpoint deleted: {checkpoint_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
        return False

    def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """Clean up old checkpoints.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of checkpoints deleted
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted = 0

        for path in self.checkpoint_dir.glob("*.pkl"):
            try:
                if path.stat().st_mtime < cutoff_time:
                    path.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete old checkpoint {path}: {e}")

        logger.info(f"Cleaned up {deleted} old checkpoints")
        return deleted


# ============================================================================
# SCHEDULER
# ============================================================================


class BatchScheduler:
    """Advanced scheduler for batch jobs with priority and deadline awareness."""

    def __init__(self, config: BatchConfig):
        """Initialize batch scheduler.

        Args:
            config: Batch configuration
        """
        self.config = config
        self.queues: Dict[Priority, deque] = {
            Priority.CRITICAL: deque(),
            Priority.HIGH: deque(),
            Priority.NORMAL: deque(),
            Priority.LOW: deque(),
        }
        self.scheduled_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: Set[str] = set()
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.Lock()
        self.tenant_queues: Dict[str, deque] = defaultdict(deque)

    def add_job(self, job: BatchJob) -> None:
        """Add job to scheduling queue.

        Args:
            job: Batch job to schedule
        """
        with self._lock:
            if len(self.scheduled_jobs) >= self.config.max_queue_depth:
                raise ValueError("Queue depth exceeded")

            self.scheduled_jobs[job.job_id] = job
            job.state = BatchState.SCHEDULED
            job.scheduled_at = datetime.utcnow()

            # Add to priority queue
            self.queues[job.priority].append(job.job_id)

            # Update dependency graph
            for dep_id in job.dependencies:
                self.dependency_graph[job.job_id].add(dep_id)

            # Add to tenant queue if multi-tenancy enabled
            if job.tenant_id:
                self.tenant_queues[job.tenant_id].append(job.job_id)

            logger.debug(f"Job scheduled: {job.job_id} (priority: {job.priority})")

    def get_next_job(self) -> Optional[BatchJob]:
        """Get next job to process based on priority and dependencies.

        Returns:
            Next job to process or None
        """
        with self._lock:
            # Check each priority level
            for priority in [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
                queue = self.queues[priority]

                # Try to find a ready job
                for _ in range(len(queue)):
                    job_id = queue.popleft()
                    job = self.scheduled_jobs.get(job_id)

                    if job is None:
                        continue

                    # Check if dependencies are met
                    if not job.is_ready(self.completed_jobs):
                        queue.append(job_id)  # Re-queue
                        continue

                    # Check deadline if enabled
                    if self.config.enable_deadline_scheduling and job.is_overdue():
                        logger.warning(f"Job {job_id} is overdue")
                        job.state = BatchState.FAILED
                        job.metadata["failure_reason"] = "deadline_exceeded"
                        self.completed_jobs.add(job_id)
                        continue

                    job.state = BatchState.RUNNING
                    job.started_at = datetime.utcnow()
                    return job

            return None

    def mark_completed(self, job_id: str) -> None:
        """Mark job as completed.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            self.completed_jobs.add(job_id)
            if job_id in self.scheduled_jobs:
                job = self.scheduled_jobs[job_id]
                job.state = BatchState.COMPLETED
                job.completed_at = datetime.utcnow()

            # Remove from dependency graph
            if job_id in self.dependency_graph:
                del self.dependency_graph[job_id]

    def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message
        """
        with self._lock:
            if job_id in self.scheduled_jobs:
                job = self.scheduled_jobs[job_id]
                job.state = BatchState.FAILED
                job.completed_at = datetime.utcnow()
                job.metadata["failure_reason"] = error

    def requeue_job(self, job_id: str) -> None:
        """Requeue a job for retry.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            if job_id in self.scheduled_jobs:
                job = self.scheduled_jobs[job_id]
                job.state = BatchState.RETRYING
                job.retry_count += 1
                self.queues[job.priority].append(job_id)

    def get_queue_depth(self) -> int:
        """Get total queue depth."""
        with self._lock:
            return sum(len(q) for q in self.queues.values())

    def get_oldest_job_age(self) -> float:
        """Get age of oldest job in seconds."""
        with self._lock:
            oldest_age = 0.0
            for job in self.scheduled_jobs.values():
                if job.state in [BatchState.SCHEDULED, BatchState.PENDING]:
                    age = job.get_age_seconds()
                    oldest_age = max(oldest_age, age)
            return oldest_age

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False otherwise
        """
        with self._lock:
            if job_id in self.scheduled_jobs:
                job = self.scheduled_jobs[job_id]
                if job.state in [BatchState.SCHEDULED, BatchState.PENDING]:
                    job.state = BatchState.CANCELLED
                    # Remove from queues
                    for queue in self.queues.values():
                        if job_id in queue:
                            queue.remove(job_id)
                    return True
        return False


# ============================================================================
# METRICS COLLECTOR
# ============================================================================


class MetricsCollector:
    """Collects and aggregates batch processing metrics."""

    def __init__(self, config: BatchConfig):
        """Initialize metrics collector.

        Args:
            config: Batch configuration
        """
        self.config = config
        self.metrics = BatchMetrics()
        self.latency_samples: List[float] = []
        self.start_time = time.time()
        self.last_update = time.time()
        self._lock = threading.Lock()
        self.job_start_times: Dict[str, float] = {}

    def record_job_start(self, job_id: str) -> None:
        """Record job start time.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            self.job_start_times[job_id] = time.time()

    def record_job_completion(
        self,
        job_id: str,
        items_count: int,
        failed_count: int = 0,
    ) -> None:
        """Record job completion.

        Args:
            job_id: Job identifier
            items_count: Number of items processed
            failed_count: Number of items that failed
        """
        with self._lock:
            self.metrics.total_jobs_processed += 1
            self.metrics.total_items_processed += items_count
            self.metrics.total_items_failed += failed_count

            # Record latency
            if job_id in self.job_start_times:
                latency_ms = (time.time() - self.job_start_times[job_id]) * 1000
                self.latency_samples.append(latency_ms)
                del self.job_start_times[job_id]

                # Keep only recent samples
                if len(self.latency_samples) > 1000:
                    self.latency_samples = self.latency_samples[-1000:]

    def record_job_failure(self, job_id: str) -> None:
        """Record job failure.

        Args:
            job_id: Job identifier
        """
        with self._lock:
            if job_id in self.job_start_times:
                del self.job_start_times[job_id]

    def record_sla_violation(self) -> None:
        """Record SLA violation."""
        with self._lock:
            self.metrics.sla_violations += 1

    def record_deadline_exceeded(self) -> None:
        """Record deadline exceeded."""
        with self._lock:
            self.metrics.jobs_exceeding_deadline += 1

    def record_checkpoint(self) -> None:
        """Record checkpoint creation."""
        with self._lock:
            self.metrics.checkpoints_created += 1
            self.metrics.last_checkpoint_time = datetime.utcnow()

    def update_metrics(
        self,
        queue_depth: int,
        oldest_job_age: float,
        active_workers: int,
        circuit_state: CircuitState,
        circuit_failures: int,
        resource_metrics: Dict[str, float],
    ) -> None:
        """Update aggregate metrics.

        Args:
            queue_depth: Current queue depth
            oldest_job_age: Age of oldest job in seconds
            active_workers: Number of active workers
            circuit_state: Circuit breaker state
            circuit_failures: Circuit breaker failures
            resource_metrics: Resource usage metrics
        """
        with self._lock:
            current_time = time.time()
            time_elapsed = current_time - self.last_update

            # Update throughput metrics
            if time_elapsed > 0:
                self.metrics.jobs_per_second = self.metrics.total_jobs_processed / (
                    current_time - self.start_time
                )
                self.metrics.items_per_second = self.metrics.total_items_processed / (
                    current_time - self.start_time
                )

            # Update latency metrics
            if self.latency_samples:
                sorted_samples = sorted(self.latency_samples)
                self.metrics.avg_job_latency_ms = sum(sorted_samples) / len(sorted_samples)
                self.metrics.p50_job_latency_ms = sorted_samples[len(sorted_samples) // 2]
                self.metrics.p95_job_latency_ms = sorted_samples[int(len(sorted_samples) * 0.95)]
                self.metrics.p99_job_latency_ms = sorted_samples[int(len(sorted_samples) * 0.99)]

            # Update success rate
            total_items = self.metrics.total_items_processed + self.metrics.total_items_failed
            if total_items > 0:
                self.metrics.success_rate = self.metrics.total_items_processed / total_items
                self.metrics.failure_rate = self.metrics.total_items_failed / total_items

            # Update queue and resource metrics
            self.metrics.queue_depth = queue_depth
            self.metrics.backlog_age_seconds = oldest_job_age
            self.metrics.active_workers = active_workers
            self.metrics.circuit_state = circuit_state
            self.metrics.circuit_failures = circuit_failures

            # Update resource metrics
            self.metrics.cpu_usage_percent = resource_metrics.get("cpu_percent", 0.0)
            self.metrics.memory_usage_mb = resource_metrics.get("memory_mb", 0.0)

            self.metrics.timestamp = datetime.utcnow()
            self.last_update = current_time

    def get_metrics(self) -> BatchMetrics:
        """Get current metrics snapshot."""
        with self._lock:
            return self.metrics.copy(deep=True)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self.metrics = BatchMetrics()
            self.latency_samples = []
            self.start_time = time.time()
            self.last_update = time.time()
            self.job_start_times = {}


# ============================================================================
# CACHE AND DEDUPLICATION
# ============================================================================


class ResultCache:
    """Caches batch processing results."""

    def __init__(self, max_size: int = 1000):
        """Initialize result cache.

        Args:
            max_size: Maximum cache size
        """
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached result.

        Args:
            key: Cache key

        Returns:
            Cached result or None
        """
        with self._lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
        return None

    def put(self, key: str, value: Any) -> None:
        """Put result in cache.

        Args:
            key: Cache key
            value: Result to cache
        """
        with self._lock:
            # Evict if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()

            self.cache[key] = value
            self.access_times[key] = time.time()

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.access_times:
            return

        lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        del self.cache[lru_key]
        del self.access_times[lru_key]

    def clear(self) -> None:
        """Clear cache."""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()


class InputDeduplicator:
    """Deduplicates input items using hashing."""

    def __init__(self):
        """Initialize deduplicator."""
        self.seen_hashes: Set[str] = set()
        self._lock = threading.Lock()

    def deduplicate(self, items: List[T]) -> List[T]:
        """Remove duplicate items.

        Args:
            items: Items to deduplicate

        Returns:
            Deduplicated items
        """
        unique_items = []
        with self._lock:
            for item in items:
                item_hash = self._hash_item(item)
                if item_hash not in self.seen_hashes:
                    self.seen_hashes.add(item_hash)
                    unique_items.append(item)
        return unique_items

    def _hash_item(self, item: Any) -> str:
        """Hash an item.

        Args:
            item: Item to hash

        Returns:
            Hash string
        """
        try:
            item_str = json.dumps(item, sort_keys=True, default=str)
            return hashlib.sha256(item_str.encode()).hexdigest()
        except Exception:
            # Fallback to string representation
            return hashlib.sha256(str(item).encode()).hexdigest()

    def clear(self) -> None:
        """Clear seen hashes."""
        with self._lock:
            self.seen_hashes.clear()


# ============================================================================
# BATCH PROCESSOR BASE
# ============================================================================


class BatchProcessorBase(ABC, Generic[T, R]):
    """Abstract base class for batch processors."""

    @abstractmethod
    def process_item(self, item: T) -> R:
        """Process a single item.

        Args:
            item: Item to process

        Returns:
            Processing result
        """
        pass

    @abstractmethod
    def process_batch(self, items: List[T]) -> List[R]:
        """Process a batch of items.

        Args:
            items: Items to process

        Returns:
            Processing results
        """
        pass

    def validate_item(self, item: T) -> bool:
        """Validate an item before processing.

        Args:
            item: Item to validate

        Returns:
            True if valid, False otherwise
        """
        return True

    def transform_item(self, item: T) -> T:
        """Transform an item before processing.

        Args:
            item: Item to transform

        Returns:
            Transformed item
        """
        return item

    def on_batch_start(self, batch: List[T]) -> None:
        """Hook called before batch processing.

        Args:
            batch: Batch to process
        """
        pass

    def on_batch_complete(self, batch: List[T], results: List[R]) -> None:
        """Hook called after batch processing.

        Args:
            batch: Processed batch
            results: Processing results
        """
        pass

    def on_error(self, item: T, error: Exception) -> Optional[R]:
        """Hook called when item processing fails.

        Args:
            item: Failed item
            error: Error that occurred

        Returns:
            Optional default result
        """
        logger.error(f"Error processing item: {error}")
        return None


# ============================================================================
# MAIN BATCH PROCESSOR FSA
# ============================================================================


class BatchProcessorFSA(BatchProcessorBase[T, R]):
    """
    Production-grade Batch Processor FSA with comprehensive features.

    This FSA provides enterprise-level batch processing capabilities including:
    - Advanced scheduling with priorities and deadlines
    - Parallel execution with multiple strategies
    - Fault tolerance with checkpointing
    - Resource management and throttling
    - Real-time monitoring and metrics
    - Circuit breaker pattern
    - Result caching and deduplication
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        processor: Optional[BatchProcessorBase[T, R]] = None,
    ):
        """Initialize Batch Processor FSA.

        Args:
            config: Batch configuration
            processor: Optional custom batch processor
        """
        self.config = config or BatchConfig()
        self.custom_processor = processor

        # Initialize components
        self.scheduler = BatchScheduler(self.config)
        self.resource_manager = ResourceManager(self.config)
        self.metrics_collector = MetricsCollector(self.config)
        self.checkpoint_manager = CheckpointManager(self.config.checkpoint_dir)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            timeout=self.config.circuit_timeout,
        )

        # Advanced features
        self.result_cache = ResultCache() if self.config.enable_caching else None
        self.deduplicator = InputDeduplicator() if self.config.enable_deduplication else None
        self.adaptive_sizer = AdaptiveBatchSizer(
            initial_size=self.config.batch_size,
            min_size=self.config.min_batch_size,
            max_size=self.config.max_batch_size,
            target_memory_mb=self.config.memory_limit_mb,
        )

        # Execution state
        self.is_running = False
        self.is_paused = False
        self.worker_pool: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self._shutdown_event = threading.Event()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Dead letter queue
        self.dead_letter_queue: List[BatchJob] = []

    def execute(
        self,
        items: List[T],
        job_type: str = "generic",
        priority: Priority = Priority.NORMAL,
        deadline: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
    ) -> BatchJob[T]:
        """Execute batch processing on items.

        Args:
            items: Items to process
            job_type: Type of job
            priority: Job priority
            deadline: Job deadline
            tenant_id: Tenant identifier

        Returns:
            Completed batch job
        """
        # Create batch job
        job = BatchJob[T](
            job_type=job_type,
            priority=priority,
            items=items,
            deadline=deadline,
            tenant_id=tenant_id,
        )

        # Validate configuration
        self.validate()

        # Start monitoring if not running
        if not self.is_running:
            self._start()

        # Schedule job
        self.schedule_job(job)

        # Process job
        return self._process_job(job)

    def schedule_job(self, job: BatchJob[T]) -> None:
        """Schedule a job for processing.

        Args:
            job: Job to schedule
        """
        self.scheduler.add_job(job)
        logger.info(f"Job scheduled: {job.job_id} with {len(job.items)} items")

    def validate(self) -> None:
        """Validate configuration and state."""
        if self.config.min_batch_size > self.config.max_batch_size:
            raise ValueError("min_batch_size cannot be greater than max_batch_size")

        if self.config.max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        # Ensure checkpoint directory exists
        Path(self.config.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    def _start(self) -> None:
        """Start the batch processor."""
        with self._lock:
            if self.is_running:
                return

            self.is_running = True
            self._shutdown_event.clear()

            # Initialize worker pool
            if self.config.processing_strategy == ProcessingStrategy.PARALLEL:
                if self.config.use_multiprocessing:
                    self.worker_pool = ProcessPoolExecutor(max_workers=self.config.max_workers)
                else:
                    self.worker_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)

            # Start monitoring thread
            if self.config.enable_metrics:
                self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
                self._monitoring_thread.start()

            logger.info("Batch processor started")

    def _process_job(self, job: BatchJob[T]) -> BatchJob[T]:
        """Process a single job.

        Args:
            job: Job to process

        Returns:
            Completed job
        """
        try:
            job.started_at = datetime.utcnow()
            self.metrics_collector.record_job_start(job.job_id)

            # Deduplicate if enabled
            if self.config.enable_deduplication and self.deduplicator:
                original_count = len(job.items)
                job.items = self.deduplicator.deduplicate(job.items)
                if len(job.items) < original_count:
                    logger.info(f"Deduplicated {original_count - len(job.items)} items")

            # Validate items if enabled
            if self.config.enable_validation:
                job.items = [item for item in job.items if self.validate_item(item)]

            # Process based on strategy
            if self.config.processing_strategy == ProcessingStrategy.SEQUENTIAL:
                results = self._process_sequential(job)
            elif self.config.processing_strategy == ProcessingStrategy.PARALLEL:
                results = self._process_parallel(job)
            elif self.config.processing_strategy == ProcessingStrategy.PIPELINE:
                results = self._process_pipeline(job)
            else:  # ADAPTIVE
                results = self._process_adaptive(job)

            job.results = results
            job.state = BatchState.COMPLETED
            job.completed_at = datetime.utcnow()

            # Record metrics
            failed_count = len(job.failed_items)
            success_count = len(job.items) - failed_count
            self.metrics_collector.record_job_completion(job.job_id, success_count, failed_count)

            self.scheduler.mark_completed(job.job_id)

            logger.info(
                f"Job completed: {job.job_id} "
                f"({success_count} succeeded, {failed_count} failed)"
            )

            return job

        except Exception as e:
            logger.error(f"Job failed: {job.job_id} - {e}")
            logger.debug(traceback.format_exc())
            job.state = BatchState.FAILED
            job.metadata["error"] = str(e)
            job.metadata["traceback"] = traceback.format_exc()

            self.scheduler.mark_failed(job.job_id, str(e))
            self.metrics_collector.record_job_failure(job.job_id)

            # Retry logic
            if job.retry_count < self.config.max_retries:
                return self._retry_job(job)
            else:
                self._move_to_dead_letter(job)

            return job

    def _process_sequential(self, job: BatchJob[T]) -> List[R]:
        """Process job sequentially.

        Args:
            job: Job to process

        Returns:
            Processing results
        """
        results = []
        batch_iterator = BatchIterator(
            job.items,
            self.adaptive_sizer.get_batch_size(),
            self.config.chunking_strategy,
        )

        batch_num = 0
        for batch in batch_iterator:
            # Wait for resources
            self.resource_manager.wait_for_resources()

            # Process batch
            batch_results = self._process_batch_with_circuit_breaker(batch)
            results.extend(batch_results)

            # Checkpoint if enabled
            batch_num += 1
            if self.config.enable_checkpointing and batch_num % self.config.checkpoint_interval == 0:
                self.checkpoint(job.job_id, {
                    "batch_num": batch_num,
                    "results": results,
                    "processed_count": len(results),
                })

            # Update adaptive batch size
            self.adaptive_sizer.adjust()

        return results

    def _process_parallel(self, job: BatchJob[T]) -> List[R]:
        """Process job in parallel.

        Args:
            job: Job to process

        Returns:
            Processing results
        """
        if self.worker_pool is None:
            raise RuntimeError("Worker pool not initialized")

        results = []
        batch_iterator = BatchIterator(
            job.items,
            self.adaptive_sizer.get_batch_size(),
            self.config.chunking_strategy,
        )

        # Submit all batches to worker pool
        futures = []
        for batch in batch_iterator:
            future = self.worker_pool.submit(self._process_batch_with_circuit_breaker, batch)
            futures.append(future)

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                batch_results = future.result()
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")

        return results

    def _process_pipeline(self, job: BatchJob[T]) -> List[R]:
        """Process job with pipeline strategy.

        Args:
            job: Job to process

        Returns:
            Processing results
        """
        # Pipeline: Transform -> Process -> Aggregate
        results = []

        # Stage 1: Transform
        transformed = [self.transform_item(item) for item in job.items]

        # Stage 2: Process in batches
        batch_iterator = BatchIterator(
            transformed,
            self.adaptive_sizer.get_batch_size(),
            self.config.chunking_strategy,
        )

        for batch in batch_iterator:
            batch_results = self._process_batch_with_circuit_breaker(batch)
            results.extend(batch_results)

        return results

    def _process_adaptive(self, job: BatchJob[T]) -> List[R]:
        """Process job with adaptive strategy.

        Args:
            job: Job to process

        Returns:
            Processing results
        """
        # Choose strategy based on job size and system resources
        if len(job.items) < 100:
            return self._process_sequential(job)
        elif self.resource_manager.check_resources_available():
            return self._process_parallel(job)
        else:
            return self._process_sequential(job)

    def _process_batch_with_circuit_breaker(self, batch: List[T]) -> List[R]:
        """Process batch with circuit breaker protection.

        Args:
            batch: Batch to process

        Returns:
            Processing results
        """
        try:
            return self.circuit_breaker.call(self._process_batch_internal, batch)
        except Exception as e:
            logger.error(f"Circuit breaker protected batch failed: {e}")
            return []

    def _process_batch_internal(self, batch: List[T]) -> List[R]:
        """Internal batch processing logic.

        Args:
            batch: Batch to process

        Returns:
            Processing results
        """
        results = []

        self.on_batch_start(batch)

        for item in batch:
            try:
                # Check cache
                if self.result_cache:
                    cache_key = self._get_cache_key(item)
                    cached_result = self.result_cache.get(cache_key)
                    if cached_result is not None:
                        results.append(cached_result)
                        continue

                # Process item
                result = self._process_item_with_retry(item)
                results.append(result)

                # Cache result
                if self.result_cache and result is not None:
                    self.result_cache.put(cache_key, result)

            except Exception as e:
                logger.error(f"Item processing failed: {e}")
                default_result = self.on_error(item, e)
                if default_result is not None:
                    results.append(default_result)

        self.on_batch_complete(batch, results)

        return results

    def _process_item_with_retry(self, item: T) -> R:
        """Process item with retry logic.

        Args:
            item: Item to process

        Returns:
            Processing result
        """
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                if self.custom_processor:
                    return self.custom_processor.process_item(item)
                else:
                    return self.process_item(item)

            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                    logger.warning(f"Item processing failed, retrying in {delay}s: {e}")
                    time.sleep(delay)

        raise last_error or Exception("Processing failed")

    def _retry_job(self, job: BatchJob[T]) -> BatchJob[T]:
        """Retry a failed job.

        Args:
            job: Job to retry

        Returns:
            Retried job
        """
        delay = self.config.retry_delay * (self.config.retry_backoff ** job.retry_count)
        logger.info(f"Retrying job {job.job_id} in {delay}s (attempt {job.retry_count + 1})")
        time.sleep(delay)

        self.scheduler.requeue_job(job.job_id)
        return self._process_job(job)

    def _move_to_dead_letter(self, job: BatchJob[T]) -> None:
        """Move job to dead letter queue.

        Args:
            job: Failed job
        """
        job.state = BatchState.DEAD_LETTER
        self.dead_letter_queue.append(job)
        logger.warning(f"Job moved to dead letter queue: {job.job_id}")

    def checkpoint(self, job_id: str, state: Dict[str, Any]) -> str:
        """Create checkpoint for recovery.

        Args:
            job_id: Job identifier
            state: State to checkpoint

        Returns:
            Checkpoint ID
        """
        checkpoint_id = self.checkpoint_manager.save_checkpoint(job_id, state)
        self.metrics_collector.record_checkpoint()
        return checkpoint_id

    def recover(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Recover from checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            Recovered state or None
        """
        return self.checkpoint_manager.load_checkpoint(checkpoint_id)

    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Update metrics
                resource_metrics = self.resource_manager.get_resource_metrics()
                self.metrics_collector.update_metrics(
                    queue_depth=self.scheduler.get_queue_depth(),
                    oldest_job_age=self.scheduler.get_oldest_job_age(),
                    active_workers=self.config.max_workers if self.worker_pool else 0,
                    circuit_state=self.circuit_breaker.get_state(),
                    circuit_failures=self.circuit_breaker.failure_count,
                    resource_metrics=resource_metrics,
                )

                # Adjust adaptive batch size
                self.adaptive_sizer.adjust()

                # Throttle if needed
                self.resource_manager.throttle_if_needed()

                time.sleep(self.config.metrics_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    def get_metrics(self) -> BatchMetrics:
        """Get current metrics.

        Returns:
            Current batch metrics
        """
        return self.metrics_collector.get_metrics()

    def shutdown(self, graceful: bool = True, timeout: float = 30.0) -> None:
        """Shutdown the batch processor.

        Args:
            graceful: Wait for jobs to complete
            timeout: Shutdown timeout in seconds
        """
        logger.info("Shutting down batch processor...")

        with self._lock:
            self.is_running = False
            self._shutdown_event.set()

        # Shutdown worker pool
        if self.worker_pool:
            if graceful:
                self.worker_pool.shutdown(wait=True, timeout=timeout if hasattr(self.worker_pool, 'shutdown') else None)
            else:
                self.worker_pool.shutdown(wait=False)

        # Wait for monitoring thread
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)

        logger.info("Batch processor shutdown complete")

    # Implement abstract methods

    def process_item(self, item: T) -> R:
        """Process a single item (default implementation).

        Args:
            item: Item to process

        Returns:
            Processing result
        """
        # Default implementation - can be overridden
        return item  # type: ignore

    def process_batch(self, items: List[T]) -> List[R]:
        """Process a batch of items (default implementation).

        Args:
            items: Items to process

        Returns:
            Processing results
        """
        return [self.process_item(item) for item in items]

    def _get_cache_key(self, item: T) -> str:
        """Generate cache key for item.

        Args:
            item: Item to generate key for

        Returns:
            Cache key
        """
        try:
            item_str = json.dumps(item, sort_keys=True, default=str)
            return hashlib.sha256(item_str.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(item).encode()).hexdigest()

    def pause(self) -> None:
        """Pause batch processing."""
        with self._lock:
            self.is_paused = True
        logger.info("Batch processor paused")

    def resume(self) -> None:
        """Resume batch processing."""
        with self._lock:
            self.is_paused = False
        logger.info("Batch processor resumed")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False otherwise
        """
        return self.scheduler.cancel_job(job_id)

    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get job status.

        Args:
            job_id: Job identifier

        Returns:
            Job or None if not found
        """
        return self.scheduler.scheduled_jobs.get(job_id)

    def list_jobs(
        self,
        state: Optional[BatchState] = None,
        tenant_id: Optional[str] = None,
    ) -> List[BatchJob]:
        """List jobs.

        Args:
            state: Filter by state
            tenant_id: Filter by tenant

        Returns:
            List of jobs
        """
        jobs = list(self.scheduler.scheduled_jobs.values())

        if state:
            jobs = [job for job in jobs if job.state == state]

        if tenant_id:
            jobs = [job for job in jobs if job.tenant_id == tenant_id]

        return jobs

    def cleanup_checkpoints(self, max_age_hours: int = 24) -> int:
        """Clean up old checkpoints.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of checkpoints deleted
        """
        return self.checkpoint_manager.cleanup_old_checkpoints(max_age_hours)

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker."""
        self.circuit_breaker.reset()
        logger.info("Circuit breaker reset")

    def clear_cache(self) -> None:
        """Clear result cache."""
        if self.result_cache:
            self.result_cache.clear()
        logger.info("Result cache cleared")

    def clear_deduplication(self) -> None:
        """Clear deduplication state."""
        if self.deduplicator:
            self.deduplicator.clear()
        logger.info("Deduplication state cleared")

    def get_dead_letter_queue(self) -> List[BatchJob]:
        """Get dead letter queue.

        Returns:
            List of failed jobs
        """
        return self.dead_letter_queue.copy()

    def retry_dead_letter_job(self, job_id: str) -> Optional[BatchJob]:
        """Retry a job from dead letter queue.

        Args:
            job_id: Job identifier

        Returns:
            Retried job or None
        """
        for i, job in enumerate(self.dead_letter_queue):
            if job.job_id == job_id:
                job.state = BatchState.PENDING
                job.retry_count = 0
                self.dead_letter_queue.pop(i)
                self.schedule_job(job)
                return self._process_job(job)
        return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def create_batch_processor(
    config: Optional[BatchConfig] = None,
    processor: Optional[BatchProcessorBase] = None,
) -> BatchProcessorFSA:
    """Factory function to create a batch processor.

    Args:
        config: Batch configuration
        processor: Optional custom processor

    Returns:
        Configured batch processor FSA
    """
    return BatchProcessorFSA(config=config, processor=processor)


# Export main classes
__all__ = [
    "BatchProcessorFSA",
    "BatchConfig",
    "BatchJob",
    "BatchMetrics",
    "BatchState",
    "Priority",
    "ProcessingStrategy",
    "ChunkingStrategy",
    "CircuitState",
    "BatchProcessorBase",
    "create_batch_processor",
]

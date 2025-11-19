"""
Bulkhead Isolation Pattern

Implements bulkhead pattern for limiting concurrent execution and isolating
failures. Prevents resource exhaustion and cascading failures across services.

The bulkhead pattern is named after the compartments in a ship's hull that
prevent the entire ship from sinking if one compartment is breached.
"""

import asyncio
import threading
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, TypeVar, Any, Dict
from queue import Queue, Full
from functools import wraps

from agno.exceptions import BulkheadFullError

T = TypeVar('T')


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead isolation"""
    # Maximum concurrent executions
    max_concurrent: int = 10

    # Maximum queue size for waiting requests
    max_queued: int = 10

    # Timeout for waiting in queue (seconds)
    queue_timeout: float = 5.0

    # Rejection handler
    on_rejection: Optional[Callable[[str], None]] = None

    # Enable metrics
    enable_metrics: bool = True


@dataclass
class BulkheadMetrics:
    """Metrics for bulkhead monitoring"""
    bulkhead_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Current state
    concurrent_executions: int = 0
    queued_requests: int = 0

    # Historical metrics
    total_requests: int = 0
    successful_requests: int = 0
    rejected_requests: int = 0
    timeout_requests: int = 0

    # Capacity metrics
    max_concurrent_seen: int = 0
    max_queued_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary"""
        return {
            "bulkhead_name": self.bulkhead_name,
            "timestamp": datetime.utcnow().isoformat(),
            "current_state": {
                "concurrent_executions": self.concurrent_executions,
                "queued_requests": self.queued_requests
            },
            "totals": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "rejected_requests": self.rejected_requests,
                "timeout_requests": self.timeout_requests
            },
            "capacity": {
                "max_concurrent_seen": self.max_concurrent_seen,
                "max_queued_seen": self.max_queued_seen
            },
            "utilization": {
                "concurrent_pct": (self.concurrent_executions / self.max_concurrent_seen * 100)
                if self.max_concurrent_seen > 0 else 0,
                "success_rate": (self.successful_requests / self.total_requests * 100)
                if self.total_requests > 0 else 0
            }
        }


class Bulkhead:
    """
    Bulkhead isolation pattern implementation.

    Limits concurrent executions and provides queueing for excess requests.
    Thread-safe and supports both sync and async execution.

    Example:
        ```python
        bulkhead = Bulkhead(
            name="database_pool",
            config=BulkheadConfig(max_concurrent=5, max_queued=10)
        )

        # Sync execution
        result = bulkhead.execute(lambda: db.query(sql))

        # Async execution
        result = await bulkhead.execute_async(async_db_query)
        ```
    """

    def __init__(self, name: str, config: Optional[BulkheadConfig] = None):
        """
        Initialize bulkhead.

        Args:
            name: Unique identifier for this bulkhead
            config: Configuration (uses defaults if not provided)
        """
        self.name = name
        self.config = config or BulkheadConfig()

        # Semaphores for concurrent execution limits
        self._semaphore = threading.Semaphore(self.config.max_concurrent)
        self._async_semaphore = asyncio.Semaphore(self.config.max_concurrent)

        # Queue for waiting requests
        self._queue: Queue = Queue(maxsize=self.config.max_queued)

        # Metrics
        self._metrics = BulkheadMetrics(bulkhead_name=name) if self.config.enable_metrics else None
        self._lock = threading.RLock()

    def execute(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Execute function with bulkhead protection (sync).

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of func

        Raises:
            BulkheadFullError: If bulkhead is full
        """
        self._record_request()

        # Try to acquire semaphore
        if not self._semaphore.acquire(timeout=self.config.queue_timeout):
            self._record_rejection()
            raise BulkheadFullError(
                message=f"Bulkhead '{self.name}' is full. Max concurrent: {self.config.max_concurrent}, Queue size: {self.config.max_queued}",
                bulkhead_name=self.name,
                max_concurrent=self.config.max_concurrent
            )

        try:
            self._record_execution_start()
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            raise
        finally:
            self._record_execution_end()
            self._semaphore.release()

    async def execute_async(self, func: Callable[..., Any], *args, **kwargs) -> T:
        """
        Execute async function with bulkhead protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of func

        Raises:
            BulkheadFullError: If bulkhead is full
        """
        self._record_request()

        # Try to acquire semaphore with timeout
        try:
            await asyncio.wait_for(
                self._async_semaphore.acquire(),
                timeout=self.config.queue_timeout
            )
        except asyncio.TimeoutError:
            self._record_rejection()
            raise BulkheadFullError(
                message=f"Bulkhead '{self.name}' is full. Max concurrent: {self.config.max_concurrent}, Queue size: {self.config.max_queued}",
                bulkhead_name=self.name,
                max_concurrent=self.config.max_concurrent
            )

        try:
            self._record_execution_start()
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            raise
        finally:
            self._record_execution_end()
            self._async_semaphore.release()

    @contextmanager
    def context(self):
        """
        Context manager for bulkhead protection (sync).

        Example:
            ```python
            with bulkhead.context():
                # Protected code
                result = expensive_operation()
            ```
        """
        self._record_request()

        if not self._semaphore.acquire(timeout=self.config.queue_timeout):
            self._record_rejection()
            raise BulkheadFullError(
                message=f"Bulkhead '{self.name}' is full. Max concurrent: {self.config.max_concurrent}, Queue size: {self.config.max_queued}",
                bulkhead_name=self.name,
                max_concurrent=self.config.max_concurrent
            )

        try:
            self._record_execution_start()
            yield
            self._record_success()
        finally:
            self._record_execution_end()
            self._semaphore.release()

    @asynccontextmanager
    async def context_async(self):
        """
        Async context manager for bulkhead protection.

        Example:
            ```python
            async with bulkhead.context_async():
                # Protected code
                result = await expensive_operation()
            ```
        """
        self._record_request()

        try:
            await asyncio.wait_for(
                self._async_semaphore.acquire(),
                timeout=self.config.queue_timeout
            )
        except asyncio.TimeoutError:
            self._record_rejection()
            raise BulkheadFullError(
                message=f"Bulkhead '{self.name}' is full. Max concurrent: {self.config.max_concurrent}, Queue size: {self.config.max_queued}",
                bulkhead_name=self.name,
                max_concurrent=self.config.max_concurrent
            )

        try:
            self._record_execution_start()
            yield
            self._record_success()
        finally:
            self._record_execution_end()
            self._async_semaphore.release()

    def _record_request(self) -> None:
        """Record incoming request"""
        if self._metrics:
            with self._lock:
                self._metrics.total_requests += 1

    def _record_execution_start(self) -> None:
        """Record execution start"""
        if self._metrics:
            with self._lock:
                self._metrics.concurrent_executions += 1
                self._metrics.max_concurrent_seen = max(
                    self._metrics.max_concurrent_seen,
                    self._metrics.concurrent_executions
                )

    def _record_execution_end(self) -> None:
        """Record execution end"""
        if self._metrics:
            with self._lock:
                self._metrics.concurrent_executions -= 1

    def _record_success(self) -> None:
        """Record successful execution"""
        if self._metrics:
            with self._lock:
                self._metrics.successful_requests += 1

    def _record_rejection(self) -> None:
        """Record rejected request"""
        if self._metrics:
            with self._lock:
                self._metrics.rejected_requests += 1

        if self.config.on_rejection:
            self.config.on_rejection(self.name)

    def get_metrics(self) -> Optional[BulkheadMetrics]:
        """Get bulkhead metrics"""
        return self._metrics

    def get_state(self) -> Dict[str, Any]:
        """Get current bulkhead state"""
        with self._lock:
            return {
                "name": self.name,
                "concurrent_executions": self._metrics.concurrent_executions if self._metrics else 0,
                "max_concurrent": self.config.max_concurrent,
                "max_queued": self.config.max_queued
            }


def bulkhead(name: str, config: Optional[BulkheadConfig] = None) -> Callable:
    """
    Decorator to wrap functions with bulkhead protection.

    Example:
        ```python
        @bulkhead(name="db_pool", config=BulkheadConfig(max_concurrent=5))
        def query_database(sql):
            return db.execute(sql)
        ```
    """
    bh = Bulkhead(name=name, config=config)

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await bh.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return bh.execute(func, *args, **kwargs)
            return sync_wrapper

    return decorator

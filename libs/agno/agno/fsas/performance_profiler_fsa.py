"""
Performance Profiler FSA - Execution profiling and performance monitoring system.

Features:
- Execution time tracking (wall clock + CPU time)
- Memory usage monitoring (current, peak, delta)
- Function call counting and timing
- Event timeline recording
- Resource utilization tracking (CPU, memory percentages)
- Nested profiling support (parent/child task relationships)
- Context manager and decorator support
- Thread-safe operations
- JSON export for analysis
"""

import functools
import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Callable
from statistics import mean, median

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class ProfileEvent:
    """Represents a performance event."""
    timestamp: float
    event_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileRecord:
    """Represents a complete profiling record for a task."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    start_cpu_time: Optional[float] = None
    end_cpu_time: Optional[float] = None
    memory_start: Optional[int] = None
    memory_peak: Optional[int] = None
    memory_end: Optional[int] = None
    events: List[ProfileEvent] = field(default_factory=list)
    parent_task_id: Optional[str] = None
    call_count: int = 1

    def elapsed_time(self) -> Optional[float]:
        """Calculate elapsed wall clock time."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    def cpu_time(self) -> Optional[float]:
        """Calculate elapsed CPU time."""
        if self.end_cpu_time is not None and self.start_cpu_time is not None:
            return self.end_cpu_time - self.start_cpu_time
        return None

    def memory_delta(self) -> Optional[int]:
        """Calculate memory usage change."""
        if self.memory_end is not None and self.memory_start is not None:
            return self.memory_end - self.memory_start
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_time": self.elapsed_time(),
            "cpu_time": self.cpu_time(),
            "memory_start": self.memory_start,
            "memory_peak": self.memory_peak,
            "memory_end": self.memory_end,
            "memory_delta": self.memory_delta(),
            "events": [asdict(e) for e in self.events],
            "parent_task_id": self.parent_task_id,
            "call_count": self.call_count,
        }


class PerformanceProfilerFSA:
    """Performance profiler with execution timing and memory monitoring."""

    def __init__(self, enable_memory_tracking: bool = True):
        """
        Initialize the performance profiler.

        Args:
            enable_memory_tracking: Enable memory usage tracking (requires psutil)
        """
        self._metrics: Dict[str, List[ProfileRecord]] = {}
        self._active_tasks: Dict[str, ProfileRecord] = {}
        self._lock = threading.RLock()
        self._enable_memory = enable_memory_tracking and PSUTIL_AVAILABLE
        self._process = psutil.Process() if PSUTIL_AVAILABLE else None
        self._current_parent: Optional[str] = None

    def _get_memory_info(self) -> Optional[int]:
        """Get current memory usage in bytes."""
        if self._enable_memory and self._process:
            try:
                return self._process.memory_info().rss
            except Exception:
                pass
        return None

    def _get_cpu_time(self) -> Optional[float]:
        """Get current CPU time."""
        try:
            return time.process_time()
        except Exception:
            return None

    def start_profiling(self, task_id: str, parent_task_id: Optional[str] = None) -> None:
        """
        Begin profiling for a specific task.

        Args:
            task_id: Unique identifier for the task
            parent_task_id: Optional parent task ID for nested profiling
        """
        with self._lock:
            # If task is already active, increment call count
            if task_id in self._active_tasks:
                self._active_tasks[task_id].call_count += 1
                return

            record = ProfileRecord(
                task_id=task_id,
                start_time=time.perf_counter(),
                start_cpu_time=self._get_cpu_time(),
                memory_start=self._get_memory_info(),
                parent_task_id=parent_task_id or self._current_parent,
            )
            self._active_tasks[task_id] = record

    def stop_profiling(self, task_id: str) -> Dict[str, Any]:
        """
        Stop profiling and return metrics.

        Args:
            task_id: Task identifier to stop profiling

        Returns:
            Dictionary containing performance metrics
        """
        with self._lock:
            if task_id not in self._active_tasks:
                raise ValueError(f"Task '{task_id}' is not being profiled")

            record = self._active_tasks[task_id]
            record.end_time = time.perf_counter()
            record.end_cpu_time = self._get_cpu_time()
            record.memory_end = self._get_memory_info()

            # Track peak memory if available
            if self._enable_memory and self._process:
                try:
                    record.memory_peak = max(
                        record.memory_start or 0,
                        record.memory_end or 0,
                    )
                except Exception:
                    pass

            # Store completed record
            if task_id not in self._metrics:
                self._metrics[task_id] = []
            self._metrics[task_id].append(record)

            # Remove from active tasks
            del self._active_tasks[task_id]

            return record.to_dict()

    def get_metrics(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieve performance metrics for a task.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary containing task metrics and statistics
        """
        with self._lock:
            if task_id not in self._metrics:
                return {
                    "task_id": task_id,
                    "executions": 0,
                    "records": [],
                }

            records = self._metrics[task_id]
            elapsed_times = [r.elapsed_time() for r in records if r.elapsed_time() is not None]
            cpu_times = [r.cpu_time() for r in records if r.cpu_time() is not None]
            memory_deltas = [r.memory_delta() for r in records if r.memory_delta() is not None]

            return {
                "task_id": task_id,
                "executions": len(records),
                "total_elapsed_time": sum(elapsed_times) if elapsed_times else 0,
                "mean_elapsed_time": mean(elapsed_times) if elapsed_times else 0,
                "median_elapsed_time": median(elapsed_times) if elapsed_times else 0,
                "min_elapsed_time": min(elapsed_times) if elapsed_times else 0,
                "max_elapsed_time": max(elapsed_times) if elapsed_times else 0,
                "mean_cpu_time": mean(cpu_times) if cpu_times else 0,
                "mean_memory_delta": mean(memory_deltas) if memory_deltas else 0,
                "total_events": sum(len(r.events) for r in records),
                "records": [r.to_dict() for r in records],
            }

    def get_summary(self) -> Dict[str, Any]:
        """
        Get aggregate performance summary for all tasks.

        Returns:
            Dictionary containing summary statistics
        """
        with self._lock:
            all_tasks = list(self._metrics.keys())
            total_executions = sum(len(self._metrics[t]) for t in all_tasks)

            all_elapsed_times = []
            all_cpu_times = []
            all_memory_deltas = []

            for task_id in all_tasks:
                for record in self._metrics[task_id]:
                    if record.elapsed_time() is not None:
                        all_elapsed_times.append(record.elapsed_time())
                    if record.cpu_time() is not None:
                        all_cpu_times.append(record.cpu_time())
                    if record.memory_delta() is not None:
                        all_memory_deltas.append(record.memory_delta())

            # Calculate percentiles
            def percentile(data: List[float], p: float) -> float:
                if not data:
                    return 0.0
                sorted_data = sorted(data)
                k = (len(sorted_data) - 1) * p
                f = int(k)
                c = f + 1
                if c >= len(sorted_data):
                    return sorted_data[-1]
                return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

            return {
                "total_tasks": len(all_tasks),
                "total_executions": total_executions,
                "active_tasks": len(self._active_tasks),
                "tasks": all_tasks,
                "total_elapsed_time": sum(all_elapsed_times) if all_elapsed_times else 0,
                "mean_elapsed_time": mean(all_elapsed_times) if all_elapsed_times else 0,
                "median_elapsed_time": median(all_elapsed_times) if all_elapsed_times else 0,
                "p95_elapsed_time": percentile(all_elapsed_times, 0.95) if all_elapsed_times else 0,
                "p99_elapsed_time": percentile(all_elapsed_times, 0.99) if all_elapsed_times else 0,
                "mean_cpu_time": mean(all_cpu_times) if all_cpu_times else 0,
                "mean_memory_delta": mean(all_memory_deltas) if all_memory_deltas else 0,
                "memory_tracking_enabled": self._enable_memory,
            }

    def record_event(
        self, task_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a custom performance event.

        Args:
            task_id: Task identifier
            event_type: Type of event (e.g., "checkpoint", "error", "milestone")
            metadata: Optional metadata dictionary
        """
        with self._lock:
            if task_id not in self._active_tasks:
                raise ValueError(f"Task '{task_id}' is not being profiled")

            event = ProfileEvent(
                timestamp=time.perf_counter(),
                event_type=event_type,
                metadata=metadata or {},
            )
            self._active_tasks[task_id].events.append(event)

    def clear_metrics(self, task_id: Optional[str] = None) -> None:
        """
        Clear metrics for a task or all tasks.

        Args:
            task_id: Optional task identifier. If None, clears all metrics.
        """
        with self._lock:
            if task_id is None:
                self._metrics.clear()
            elif task_id in self._metrics:
                del self._metrics[task_id]

    @contextmanager
    def profile(self, task_id: str, parent_task_id: Optional[str] = None):
        """
        Context manager for profiling a code block.

        Args:
            task_id: Task identifier
            parent_task_id: Optional parent task ID

        Yields:
            ProfileRecord for the task

        Example:
            with profiler.profile("my_task"):
                # code to profile
                pass
        """
        self.start_profiling(task_id, parent_task_id)
        old_parent = self._current_parent
        self._current_parent = task_id
        try:
            yield self._active_tasks.get(task_id)
        finally:
            self._current_parent = old_parent
            self.stop_profiling(task_id)

    def profile_function(self, task_id: Optional[str] = None) -> Callable:
        """
        Decorator for profiling function execution.

        Args:
            task_id: Optional task identifier (defaults to function name)

        Returns:
            Decorated function

        Example:
            @profiler.profile_function()
            def my_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                tid = task_id or func.__name__
                with self.profile(tid):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def export_json(self, task_id: Optional[str] = None) -> str:
        """
        Export metrics to JSON format.

        Args:
            task_id: Optional task identifier. If None, exports all metrics.

        Returns:
            JSON string containing metrics
        """
        with self._lock:
            if task_id is not None:
                data = self.get_metrics(task_id)
            else:
                data = {
                    "summary": self.get_summary(),
                    "tasks": {tid: self.get_metrics(tid) for tid in self._metrics.keys()},
                }
            return json.dumps(data, indent=2)

    def get_active_tasks(self) -> List[str]:
        """
        Get list of currently active task IDs.

        Returns:
            List of active task identifiers
        """
        with self._lock:
            return list(self._active_tasks.keys())

    def is_profiling(self, task_id: str) -> bool:
        """
        Check if a task is currently being profiled.

        Args:
            task_id: Task identifier

        Returns:
            True if task is active, False otherwise
        """
        with self._lock:
            return task_id in self._active_tasks

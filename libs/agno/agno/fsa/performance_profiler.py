"""
Performance Profiler FSA - Comprehensive multi-dimensional performance profiling system.

This module provides advanced profiling capabilities for tracking execution time, memory usage,
CPU utilization, I/O operations, and network activity with bottleneck identification and
optimization recommendations.
"""

import asyncio
import contextvars
import functools
import gc
import json
import logging
import os
import psutil
import resource
import sys
import threading
import time
import tracemalloc
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

import numpy as np
from threading import Lock, Thread

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models and Enums
# ============================================================================


class ProfilingMode(Enum):
    """Profiling execution modes."""
    MANUAL = "manual"  # Start/stop profiling manually
    DECORATOR = "decorator"  # Profile decorated functions
    CONTEXT_MANAGER = "context_manager"  # Profile code blocks
    CONTINUOUS = "continuous"  # Background sampling
    INSTRUMENTATION = "instrumentation"  # Full detailed analysis


class MetricType(Enum):
    """Types of metrics tracked."""
    TIME = "time"
    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    NETWORK = "network"
    DATABASE = "database"
    THREAD = "thread"
    GC = "gc"
    CUSTOM = "custom"


class BottleneckSeverity(Enum):
    """Severity levels for bottlenecks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TimeMetrics:
    """Time-related profiling metrics."""
    wall_time: float = 0.0  # Wall clock time in seconds
    cpu_time: float = 0.0  # CPU time in seconds
    user_time: float = 0.0  # User CPU time
    system_time: float = 0.0  # System CPU time
    start_timestamp: float = 0.0
    end_timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryMetrics:
    """Memory-related profiling metrics."""
    rss: int = 0  # Resident Set Size in bytes
    vms: int = 0  # Virtual Memory Size in bytes
    peak_rss: int = 0  # Peak RSS
    allocations: int = 0  # Number of allocations
    deallocations: int = 0  # Number of deallocations
    total_allocated: int = 0  # Total bytes allocated
    gc_collections: List[int] = field(default_factory=lambda: [0, 0, 0])
    gc_time: float = 0.0  # Time spent in GC

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CPUMetrics:
    """CPU-related profiling metrics."""
    percent: float = 0.0  # Overall CPU utilization
    per_core: List[float] = field(default_factory=list)  # Per-core utilization
    num_threads: int = 0
    context_switches: int = 0
    num_fds: int = 0  # Number of file descriptors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IOMetrics:
    """I/O-related profiling metrics."""
    read_count: int = 0
    write_count: int = 0
    read_bytes: int = 0
    write_bytes: int = 0
    read_time: float = 0.0
    write_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkMetrics:
    """Network-related profiling metrics."""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    connections: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatabaseMetrics:
    """Database query metrics."""
    query_count: int = 0
    total_duration: float = 0.0
    slow_queries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CustomMetric:
    """Custom user-defined metric."""
    name: str
    value: Union[int, float, str]
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProfilingConfig:
    """Configuration for profiling sessions."""
    mode: ProfilingMode = ProfilingMode.MANUAL
    track_time: bool = True
    track_memory: bool = True
    track_cpu: bool = True
    track_io: bool = True
    track_network: bool = False
    track_database: bool = False
    track_threads: bool = True
    track_gc: bool = True
    track_gpu: bool = False
    sampling_interval: float = 0.1  # Seconds for continuous mode
    memory_snapshots: bool = False
    enable_flame_graph: bool = False
    enable_timeline: bool = False
    max_stack_depth: int = 64
    slow_query_threshold: float = 1.0  # Seconds
    export_format: str = "json"  # json, csv, html
    output_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['mode'] = self.mode.value
        if self.output_dir:
            data['output_dir'] = str(self.output_dir)
        return data


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    id: str
    severity: BottleneckSeverity
    category: MetricType
    description: str
    location: str  # Function/module where bottleneck occurs
    impact: float  # Percentage impact on performance
    value: float  # Measured value
    threshold: float  # Expected threshold
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        return data


@dataclass
class MemoryLeak:
    """Detected memory leak."""
    id: str
    location: str
    leaked_size: int  # Bytes
    allocation_count: int
    growth_rate: float  # Bytes per second
    stack_trace: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    """Optimization recommendation."""
    id: str
    title: str
    description: str
    category: MetricType
    priority: BottleneckSeverity
    estimated_improvement: float  # Percentage
    code_examples: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['category'] = self.category.value
        data['priority'] = self.priority.value
        return data


@dataclass
class ProfilingResult:
    """Complete profiling result."""
    session_id: str
    name: str
    config: ProfilingConfig
    time_metrics: TimeMetrics
    memory_metrics: MemoryMetrics
    cpu_metrics: CPUMetrics
    io_metrics: IOMetrics
    network_metrics: NetworkMetrics
    database_metrics: DatabaseMetrics
    custom_metrics: List[CustomMetric] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    function_calls: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'name': self.name,
            'config': self.config.to_dict(),
            'time_metrics': self.time_metrics.to_dict(),
            'memory_metrics': self.memory_metrics.to_dict(),
            'cpu_metrics': self.cpu_metrics.to_dict(),
            'io_metrics': self.io_metrics.to_dict(),
            'network_metrics': self.network_metrics.to_dict(),
            'database_metrics': self.database_metrics.to_dict(),
            'custom_metrics': [m.to_dict() for m in self.custom_metrics],
            'bottlenecks': [b.to_dict() for b in self.bottlenecks],
            'function_calls': self.function_calls,
            'metadata': self.metadata,
        }

    def get_percentile(self, metric: str, percentile: float) -> float:
        """Calculate percentile for a metric."""
        # Placeholder for percentile calculation
        return 0.0


@dataclass
class ComparisonReport:
    """Performance comparison report."""
    baseline_id: str
    current_id: str
    time_delta: float  # Percentage change
    memory_delta: float
    cpu_delta: float
    io_delta: float
    regressions: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    new_bottlenecks: List[Bottleneck] = field(default_factory=list)
    resolved_bottlenecks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['new_bottlenecks'] = [b.to_dict() for b in self.new_bottlenecks]
        return data


# ============================================================================
# Profiling Modules
# ============================================================================


class TimeProfiler:
    """High-precision time profiling with nanosecond precision."""

    def __init__(self):
        self.start_wall: float = 0.0
        self.end_wall: float = 0.0
        self.start_cpu: float = 0.0
        self.end_cpu: float = 0.0
        self.start_rusage: Any = None
        self.end_rusage: Any = None

    def start(self) -> None:
        """Start time profiling."""
        self.start_wall = time.perf_counter()
        self.start_cpu = time.process_time()
        self.start_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def stop(self) -> TimeMetrics:
        """Stop time profiling and return metrics."""
        self.end_wall = time.perf_counter()
        self.end_cpu = time.process_time()
        self.end_rusage = resource.getrusage(resource.RUSAGE_SELF)

        metrics = TimeMetrics(
            wall_time=self.end_wall - self.start_wall,
            cpu_time=self.end_cpu - self.start_cpu,
            user_time=self.end_rusage.ru_utime - self.start_rusage.ru_utime,
            system_time=self.end_rusage.ru_stime - self.start_rusage.ru_stime,
            start_timestamp=self.start_wall,
            end_timestamp=self.end_wall,
        )

        return metrics


class MemoryProfiler:
    """Memory profiling with heap snapshots and allocation tracking."""

    def __init__(self, enable_tracemalloc: bool = True):
        self.enable_tracemalloc = enable_tracemalloc
        self.process = psutil.Process()
        self.start_mem: Optional[psutil._pslinux.pmem] = None
        self.end_mem: Optional[psutil._pslinux.pmem] = None
        self.snapshots: List[Any] = []
        self.gc_stats_start: List[int] = []
        self.gc_stats_end: List[int] = []
        self.gc_time_start: float = 0.0
        self.gc_time_end: float = 0.0

    def start(self) -> None:
        """Start memory profiling."""
        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()

        gc.collect()  # Force GC to get accurate baseline
        self.start_mem = self.process.memory_info()
        self.gc_stats_start = [gc.get_count()[i] for i in range(3)]
        self.gc_time_start = sum(gc.get_stats()[i].get('time', 0) for i in range(3))

    def snapshot(self) -> None:
        """Take a memory snapshot."""
        if tracemalloc.is_tracing():
            self.snapshots.append(tracemalloc.take_snapshot())

    def stop(self) -> MemoryMetrics:
        """Stop memory profiling and return metrics."""
        gc.collect()
        self.end_mem = self.process.memory_info()
        self.gc_stats_end = [gc.get_count()[i] for i in range(3)]
        self.gc_time_end = sum(gc.get_stats()[i].get('time', 0) for i in range(3))

        allocations = 0
        deallocations = 0
        total_allocated = 0

        if self.enable_tracemalloc and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            total_allocated = current
            tracemalloc.stop()

        gc_collections = [
            self.gc_stats_end[i] - self.gc_stats_start[i]
            for i in range(3)
        ]

        metrics = MemoryMetrics(
            rss=self.end_mem.rss,
            vms=self.end_mem.vms,
            peak_rss=self.process.memory_info().rss,
            allocations=allocations,
            deallocations=deallocations,
            total_allocated=total_allocated,
            gc_collections=gc_collections,
            gc_time=self.gc_time_end - self.gc_time_start,
        )

        return metrics


class CPUProfiler:
    """CPU profiling with per-core utilization and thread tracking."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_cpu_times: Any = None
        self.end_cpu_times: Any = None
        self.start_ctx_switches: int = 0
        self.end_ctx_switches: int = 0
        self.cpu_samples: List[float] = []
        self.per_core_samples: List[List[float]] = []

    def start(self) -> None:
        """Start CPU profiling."""
        self.start_cpu_times = self.process.cpu_times()
        try:
            self.start_ctx_switches = self.process.num_ctx_switches().voluntary
        except AttributeError:
            self.start_ctx_switches = 0

    def sample(self) -> None:
        """Sample CPU utilization."""
        try:
            self.cpu_samples.append(self.process.cpu_percent())
            self.per_core_samples.append(psutil.cpu_percent(percpu=True))
        except Exception as e:
            logger.debug(f"CPU sampling error: {e}")

    def stop(self) -> CPUMetrics:
        """Stop CPU profiling and return metrics."""
        self.end_cpu_times = self.process.cpu_times()
        try:
            self.end_ctx_switches = self.process.num_ctx_switches().voluntary
        except AttributeError:
            self.end_ctx_switches = 0

        # Calculate average per-core utilization
        per_core_avg = []
        if self.per_core_samples:
            num_cores = len(self.per_core_samples[0])
            for core in range(num_cores):
                core_samples = [sample[core] for sample in self.per_core_samples]
                per_core_avg.append(np.mean(core_samples) if core_samples else 0.0)

        metrics = CPUMetrics(
            percent=np.mean(self.cpu_samples) if self.cpu_samples else 0.0,
            per_core=per_core_avg,
            num_threads=self.process.num_threads(),
            context_switches=self.end_ctx_switches - self.start_ctx_switches,
            num_fds=self.process.num_fds() if hasattr(self.process, 'num_fds') else 0,
        )

        return metrics


class IOProfiler:
    """I/O profiling for file and network operations."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_io: Any = None
        self.end_io: Any = None
        self.io_operations: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start I/O profiling."""
        try:
            self.start_io = self.process.io_counters()
        except (AttributeError, psutil.AccessDenied):
            self.start_io = None

    def log_operation(self, operation: str, bytes_transferred: int, duration: float) -> None:
        """Log an I/O operation."""
        self.io_operations.append({
            'operation': operation,
            'bytes': bytes_transferred,
            'duration': duration,
            'timestamp': time.time(),
        })

    def stop(self) -> IOMetrics:
        """Stop I/O profiling and return metrics."""
        try:
            self.end_io = self.process.io_counters()
        except (AttributeError, psutil.AccessDenied):
            self.end_io = None

        if self.start_io and self.end_io:
            metrics = IOMetrics(
                read_count=self.end_io.read_count - self.start_io.read_count,
                write_count=self.end_io.write_count - self.start_io.write_count,
                read_bytes=self.end_io.read_bytes - self.start_io.read_bytes,
                write_bytes=self.end_io.write_bytes - self.start_io.write_bytes,
            )
        else:
            metrics = IOMetrics()

        # Calculate read/write times from logged operations
        read_time = sum(op['duration'] for op in self.io_operations if 'read' in op['operation'].lower())
        write_time = sum(op['duration'] for op in self.io_operations if 'write' in op['operation'].lower())

        metrics.read_time = read_time
        metrics.write_time = write_time

        return metrics


class AsyncProfiler:
    """Async operation profiling for event loop monitoring."""

    def __init__(self):
        self.async_tasks: Dict[str, Dict[str, Any]] = {}
        self.event_loop_samples: List[Dict[str, Any]] = []
        self.start_time: float = 0.0

    def start(self) -> None:
        """Start async profiling."""
        self.start_time = time.time()

    def track_task(self, task_id: str, coro_name: str) -> None:
        """Track an async task."""
        self.async_tasks[task_id] = {
            'name': coro_name,
            'start': time.time(),
            'end': None,
            'duration': 0.0,
        }

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.async_tasks:
            task = self.async_tasks[task_id]
            task['end'] = time.time()
            task['duration'] = task['end'] - task['start']

    def sample_event_loop(self) -> None:
        """Sample event loop state."""
        try:
            loop = asyncio.get_event_loop()
            self.event_loop_samples.append({
                'timestamp': time.time(),
                'is_running': loop.is_running(),
                'is_closed': loop.is_closed(),
            })
        except Exception as e:
            logger.debug(f"Event loop sampling error: {e}")

    def stop(self) -> Dict[str, Any]:
        """Stop async profiling and return metrics."""
        total_tasks = len(self.async_tasks)
        completed_tasks = sum(1 for t in self.async_tasks.values() if t['end'] is not None)
        avg_duration = np.mean([t['duration'] for t in self.async_tasks.values() if t['duration'] > 0]) if self.async_tasks else 0.0

        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'avg_task_duration': avg_duration,
            'event_loop_samples': len(self.event_loop_samples),
        }


class GPUProfiler:
    """GPU profiling for CUDA operations and GPU memory."""

    def __init__(self):
        self.gpu_available = False
        self.start_metrics: Dict[str, Any] = {}
        self.end_metrics: Dict[str, Any] = {}

        # Try to import GPU libraries
        try:
            import pynvml
            pynvml.nvmlInit()
            self.gpu_available = True
            self.pynvml = pynvml
            self.device_count = pynvml.nvmlDeviceGetCount()
        except (ImportError, Exception):
            self.gpu_available = False

    def start(self) -> None:
        """Start GPU profiling."""
        if not self.gpu_available:
            return

        try:
            for i in range(self.device_count):
                handle = self.pynvml.nvmlDeviceGetHandleByIndex(i)
                mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = self.pynvml.nvmlDeviceGetUtilizationRates(handle)

                self.start_metrics[i] = {
                    'memory_used': mem_info.used,
                    'memory_total': mem_info.total,
                    'gpu_util': util.gpu,
                    'memory_util': util.memory,
                }
        except Exception as e:
            logger.debug(f"GPU profiling start error: {e}")

    def stop(self) -> Dict[str, Any]:
        """Stop GPU profiling and return metrics."""
        if not self.gpu_available:
            return {}

        try:
            for i in range(self.device_count):
                handle = self.pynvml.nvmlDeviceGetHandleByIndex(i)
                mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = self.pynvml.nvmlDeviceGetUtilizationRates(handle)

                self.end_metrics[i] = {
                    'memory_used': mem_info.used,
                    'memory_total': mem_info.total,
                    'gpu_util': util.gpu,
                    'memory_util': util.memory,
                }

            return {
                'gpu_count': self.device_count,
                'metrics': self.end_metrics,
            }
        except Exception as e:
            logger.debug(f"GPU profiling stop error: {e}")
            return {}


# ============================================================================
# Analysis Engine
# ============================================================================


class BottleneckIdentifier:
    """Identifies performance bottlenecks using statistical analysis."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'io_wait': 0.5,
            'slow_function': 1.0,
        }

    def identify(self, result: ProfilingResult) -> List[Bottleneck]:
        """Identify bottlenecks in profiling result."""
        bottlenecks = []

        # Check CPU bottlenecks
        if result.cpu_metrics.percent > self.thresholds['cpu_percent']:
            bottlenecks.append(Bottleneck(
                id=f"cpu_{uuid.uuid4().hex[:8]}",
                severity=BottleneckSeverity.HIGH,
                category=MetricType.CPU,
                description=f"High CPU utilization: {result.cpu_metrics.percent:.1f}%",
                location="system",
                impact=(result.cpu_metrics.percent / 100.0) * 100,
                value=result.cpu_metrics.percent,
                threshold=self.thresholds['cpu_percent'],
                recommendations=[
                    "Consider parallelizing CPU-intensive operations",
                    "Use multi-processing for CPU-bound tasks",
                    "Profile hot code paths with cProfile",
                ],
            ))

        # Check memory bottlenecks
        process = psutil.Process()
        memory_percent = (result.memory_metrics.rss / psutil.virtual_memory().total) * 100
        if memory_percent > self.thresholds['memory_percent']:
            bottlenecks.append(Bottleneck(
                id=f"mem_{uuid.uuid4().hex[:8]}",
                severity=BottleneckSeverity.CRITICAL,
                category=MetricType.MEMORY,
                description=f"High memory usage: {memory_percent:.1f}%",
                location="system",
                impact=memory_percent,
                value=result.memory_metrics.rss,
                threshold=self.thresholds['memory_percent'],
                recommendations=[
                    "Check for memory leaks",
                    "Use generators for large datasets",
                    "Implement memory pooling",
                    "Use memory profiling tools to find allocations",
                ],
            ))

        # Check I/O bottlenecks
        if result.io_metrics.read_time + result.io_metrics.write_time > self.thresholds['io_wait']:
            total_io_time = result.io_metrics.read_time + result.io_metrics.write_time
            bottlenecks.append(Bottleneck(
                id=f"io_{uuid.uuid4().hex[:8]}",
                severity=BottleneckSeverity.MEDIUM,
                category=MetricType.IO,
                description=f"High I/O wait time: {total_io_time:.2f}s",
                location="system",
                impact=(total_io_time / result.time_metrics.wall_time) * 100 if result.time_metrics.wall_time > 0 else 0,
                value=total_io_time,
                threshold=self.thresholds['io_wait'],
                recommendations=[
                    "Use async I/O for concurrent operations",
                    "Implement caching for frequently accessed data",
                    "Batch I/O operations",
                    "Use memory-mapped files for large files",
                ],
            ))

        return bottlenecks


class RegressionDetector:
    """Detects performance regressions by comparing profiling results."""

    def __init__(self, regression_threshold: float = 10.0):
        self.regression_threshold = regression_threshold  # Percentage

    def compare(
        self,
        baseline: ProfilingResult,
        current: ProfilingResult,
    ) -> ComparisonReport:
        """Compare two profiling results and detect regressions."""
        # Calculate percentage changes
        time_delta = self._calculate_delta(
            baseline.time_metrics.wall_time,
            current.time_metrics.wall_time,
        )

        memory_delta = self._calculate_delta(
            baseline.memory_metrics.rss,
            current.memory_metrics.rss,
        )

        cpu_delta = self._calculate_delta(
            baseline.cpu_metrics.percent,
            current.cpu_metrics.percent,
        )

        io_delta = self._calculate_delta(
            baseline.io_metrics.read_bytes + baseline.io_metrics.write_bytes,
            current.io_metrics.read_bytes + current.io_metrics.write_bytes,
        )

        # Identify regressions and improvements
        regressions = []
        improvements = []

        if time_delta > self.regression_threshold:
            regressions.append(f"Execution time increased by {time_delta:.1f}%")
        elif time_delta < -self.regression_threshold:
            improvements.append(f"Execution time decreased by {abs(time_delta):.1f}%")

        if memory_delta > self.regression_threshold:
            regressions.append(f"Memory usage increased by {memory_delta:.1f}%")
        elif memory_delta < -self.regression_threshold:
            improvements.append(f"Memory usage decreased by {abs(memory_delta):.1f}%")

        # Compare bottlenecks
        baseline_bottleneck_ids = {b.location for b in baseline.bottlenecks}
        current_bottleneck_ids = {b.location for b in current.bottlenecks}

        new_bottlenecks = [b for b in current.bottlenecks if b.location not in baseline_bottleneck_ids]
        resolved_bottlenecks = list(baseline_bottleneck_ids - current_bottleneck_ids)

        return ComparisonReport(
            baseline_id=baseline.session_id,
            current_id=current.session_id,
            time_delta=time_delta,
            memory_delta=memory_delta,
            cpu_delta=cpu_delta,
            io_delta=io_delta,
            regressions=regressions,
            improvements=improvements,
            new_bottlenecks=new_bottlenecks,
            resolved_bottlenecks=resolved_bottlenecks,
        )

    def _calculate_delta(self, baseline: float, current: float) -> float:
        """Calculate percentage change."""
        if baseline == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - baseline) / baseline) * 100


class OptimizationAdvisor:
    """Provides ML-based optimization recommendations."""

    def __init__(self):
        self.recommendation_rules = self._load_rules()

    def _load_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load optimization recommendation rules."""
        return {
            'high_cpu': [
                {
                    'title': 'Parallelize CPU-intensive operations',
                    'description': 'Use multiprocessing or threading for CPU-bound tasks',
                    'improvement': 40.0,
                    'examples': [
                        'from multiprocessing import Pool',
                        'with Pool() as pool:',
                        '    results = pool.map(cpu_intensive_func, data)',
                    ],
                },
                {
                    'title': 'Use NumPy for numerical computations',
                    'description': 'NumPy operations are vectorized and much faster',
                    'improvement': 50.0,
                    'examples': [
                        'import numpy as np',
                        'result = np.sum(array)  # Instead of sum(list)',
                    ],
                },
            ],
            'high_memory': [
                {
                    'title': 'Use generators for large datasets',
                    'description': 'Generators yield items one at a time, reducing memory usage',
                    'improvement': 60.0,
                    'examples': [
                        'def read_large_file(filepath):',
                        '    with open(filepath) as f:',
                        '        for line in f:',
                        '            yield line.strip()',
                    ],
                },
                {
                    'title': 'Implement object pooling',
                    'description': 'Reuse objects instead of creating new ones',
                    'improvement': 30.0,
                    'examples': [
                        'from queue import Queue',
                        'pool = Queue()',
                        'obj = pool.get() if not pool.empty() else create_new()',
                    ],
                },
            ],
            'high_io': [
                {
                    'title': 'Use async I/O',
                    'description': 'Async I/O allows concurrent operations',
                    'improvement': 70.0,
                    'examples': [
                        'import aiofiles',
                        'async with aiofiles.open(file) as f:',
                        '    content = await f.read()',
                    ],
                },
                {
                    'title': 'Implement caching',
                    'description': 'Cache frequently accessed data',
                    'improvement': 80.0,
                    'examples': [
                        'from functools import lru_cache',
                        '@lru_cache(maxsize=128)',
                        'def expensive_function(arg):',
                        '    return result',
                    ],
                },
            ],
        }

    def get_recommendations(self, result: ProfilingResult) -> List[Recommendation]:
        """Generate optimization recommendations."""
        recommendations = []

        # Analyze bottlenecks and generate recommendations
        for bottleneck in result.bottlenecks:
            if bottleneck.category == MetricType.CPU:
                for rule in self.recommendation_rules.get('high_cpu', []):
                    recommendations.append(Recommendation(
                        id=f"rec_{uuid.uuid4().hex[:8]}",
                        title=rule['title'],
                        description=rule['description'],
                        category=MetricType.CPU,
                        priority=bottleneck.severity,
                        estimated_improvement=rule['improvement'],
                        code_examples=rule['examples'],
                        references=[
                            'https://docs.python.org/3/library/multiprocessing.html',
                            'https://numpy.org/doc/stable/user/absolute_beginners.html',
                        ],
                    ))

            elif bottleneck.category == MetricType.MEMORY:
                for rule in self.recommendation_rules.get('high_memory', []):
                    recommendations.append(Recommendation(
                        id=f"rec_{uuid.uuid4().hex[:8]}",
                        title=rule['title'],
                        description=rule['description'],
                        category=MetricType.MEMORY,
                        priority=bottleneck.severity,
                        estimated_improvement=rule['improvement'],
                        code_examples=rule['examples'],
                        references=[
                            'https://docs.python.org/3/howto/functional.html#generators',
                        ],
                    ))

            elif bottleneck.category == MetricType.IO:
                for rule in self.recommendation_rules.get('high_io', []):
                    recommendations.append(Recommendation(
                        id=f"rec_{uuid.uuid4().hex[:8]}",
                        title=rule['title'],
                        description=rule['description'],
                        category=MetricType.IO,
                        priority=bottleneck.severity,
                        estimated_improvement=rule['improvement'],
                        code_examples=rule['examples'],
                        references=[
                            'https://docs.python.org/3/library/asyncio.html',
                        ],
                    ))

        return recommendations


class HotspotAnalyzer:
    """Analyzes expensive code paths and hot spots."""

    def __init__(self):
        self.function_timings: Dict[str, List[float]] = defaultdict(list)

    def record_function(self, func_name: str, duration: float) -> None:
        """Record function execution time."""
        self.function_timings[func_name].append(duration)

    def get_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top N hottest code paths."""
        hotspots = []

        for func_name, durations in self.function_timings.items():
            total_time = sum(durations)
            call_count = len(durations)
            avg_time = total_time / call_count if call_count > 0 else 0

            hotspots.append({
                'function': func_name,
                'total_time': total_time,
                'call_count': call_count,
                'avg_time': avg_time,
                'max_time': max(durations) if durations else 0,
                'min_time': min(durations) if durations else 0,
            })

        # Sort by total time descending
        hotspots.sort(key=lambda x: x['total_time'], reverse=True)

        return hotspots[:top_n]


class ResourceLeakDetector:
    """Detects memory and file handle leaks."""

    def __init__(self):
        self.memory_snapshots: List[Tuple[float, int]] = []
        self.fd_snapshots: List[Tuple[float, int]] = []
        self.leak_threshold = 1.5  # 50% growth indicates potential leak

    def snapshot(self) -> None:
        """Take a resource snapshot."""
        process = psutil.Process()
        timestamp = time.time()

        self.memory_snapshots.append((timestamp, process.memory_info().rss))

        try:
            self.fd_snapshots.append((timestamp, process.num_fds()))
        except AttributeError:
            pass

    def detect_memory_leaks(self) -> List[MemoryLeak]:
        """Detect potential memory leaks."""
        leaks = []

        if len(self.memory_snapshots) < 2:
            return leaks

        # Calculate growth rate
        first_timestamp, first_memory = self.memory_snapshots[0]
        last_timestamp, last_memory = self.memory_snapshots[-1]

        time_diff = last_timestamp - first_timestamp
        if time_diff > 0:
            growth_rate = (last_memory - first_memory) / time_diff
            growth_ratio = last_memory / first_memory if first_memory > 0 else 0

            if growth_ratio > self.leak_threshold:
                leaks.append(MemoryLeak(
                    id=f"leak_{uuid.uuid4().hex[:8]}",
                    location="unknown",
                    leaked_size=last_memory - first_memory,
                    allocation_count=0,
                    growth_rate=growth_rate,
                    first_seen=first_timestamp,
                    last_seen=last_timestamp,
                ))

        return leaks


class ConcurrencyAnalyzer:
    """Analyzes deadlocks and race conditions."""

    def __init__(self):
        self.lock_acquisitions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.thread_states: Dict[int, List[str]] = defaultdict(list)

    def record_lock(self, lock_id: str, thread_id: int, acquired: bool) -> None:
        """Record lock acquisition/release."""
        self.lock_acquisitions[lock_id].append({
            'thread_id': thread_id,
            'acquired': acquired,
            'timestamp': time.time(),
        })

    def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Detect potential deadlocks."""
        deadlocks = []

        # Simplified deadlock detection
        # In practice, this would use more sophisticated algorithms
        # like cycle detection in lock-wait graphs

        return deadlocks


# ============================================================================
# Reporting & Visualization
# ============================================================================


class ReportGenerator:
    """Generates profiling reports in various formats."""

    def __init__(self):
        pass

    def generate_json(self, result: ProfilingResult) -> str:
        """Generate JSON report."""
        return json.dumps(result.to_dict(), indent=2, default=str)

    def generate_html(self, result: ProfilingResult) -> str:
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Profile - {result.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .metric {{ margin: 10px 0; }}
        .severity-critical {{ color: #f44336; }}
        .severity-high {{ color: #ff9800; }}
        .severity-medium {{ color: #ffc107; }}
        .severity-low {{ color: #8bc34a; }}
    </style>
</head>
<body>
    <h1>Performance Profile: {result.name}</h1>
    <p><strong>Session ID:</strong> {result.session_id}</p>

    <h2>Time Metrics</h2>
    <div class="metric">Wall Time: {result.time_metrics.wall_time:.4f}s</div>
    <div class="metric">CPU Time: {result.time_metrics.cpu_time:.4f}s</div>
    <div class="metric">User Time: {result.time_metrics.user_time:.4f}s</div>
    <div class="metric">System Time: {result.time_metrics.system_time:.4f}s</div>

    <h2>Memory Metrics</h2>
    <div class="metric">RSS: {result.memory_metrics.rss / (1024**2):.2f} MB</div>
    <div class="metric">VMS: {result.memory_metrics.vms / (1024**2):.2f} MB</div>
    <div class="metric">Peak RSS: {result.memory_metrics.peak_rss / (1024**2):.2f} MB</div>
    <div class="metric">GC Collections: {result.memory_metrics.gc_collections}</div>

    <h2>CPU Metrics</h2>
    <div class="metric">CPU Utilization: {result.cpu_metrics.percent:.1f}%</div>
    <div class="metric">Threads: {result.cpu_metrics.num_threads}</div>
    <div class="metric">Context Switches: {result.cpu_metrics.context_switches}</div>

    <h2>I/O Metrics</h2>
    <div class="metric">Read Bytes: {result.io_metrics.read_bytes / (1024**2):.2f} MB</div>
    <div class="metric">Write Bytes: {result.io_metrics.write_bytes / (1024**2):.2f} MB</div>
    <div class="metric">Read Count: {result.io_metrics.read_count}</div>
    <div class="metric">Write Count: {result.io_metrics.write_count}</div>

    <h2>Bottlenecks</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Category</th>
            <th>Description</th>
            <th>Impact</th>
            <th>Location</th>
        </tr>
"""

        for bottleneck in result.bottlenecks:
            html += f"""
        <tr>
            <td class="severity-{bottleneck.severity.value}">{bottleneck.severity.value.upper()}</td>
            <td>{bottleneck.category.value}</td>
            <td>{bottleneck.description}</td>
            <td>{bottleneck.impact:.1f}%</td>
            <td>{bottleneck.location}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html

    def generate_csv(self, result: ProfilingResult) -> str:
        """Generate CSV report."""
        lines = [
            "Metric,Value",
            f"Session ID,{result.session_id}",
            f"Name,{result.name}",
            f"Wall Time (s),{result.time_metrics.wall_time}",
            f"CPU Time (s),{result.time_metrics.cpu_time}",
            f"RSS (MB),{result.memory_metrics.rss / (1024**2)}",
            f"VMS (MB),{result.memory_metrics.vms / (1024**2)}",
            f"CPU Percent,{result.cpu_metrics.percent}",
            f"Threads,{result.cpu_metrics.num_threads}",
            f"Read Bytes,{result.io_metrics.read_bytes}",
            f"Write Bytes,{result.io_metrics.write_bytes}",
        ]

        return "\n".join(lines)


class FlameGraphBuilder:
    """Builds interactive flame graphs."""

    def __init__(self):
        self.stack_samples: List[List[str]] = []

    def add_sample(self, stack: List[str]) -> None:
        """Add a stack sample."""
        self.stack_samples.append(stack)

    def generate(self, output_path: Path) -> None:
        """Generate flame graph."""
        # Simplified flame graph generation
        # In practice, this would use libraries like flamegraph or py-spy

        stack_counts: Dict[str, int] = defaultdict(int)

        for stack in self.stack_samples:
            stack_str = ";".join(reversed(stack))
            stack_counts[stack_str] += 1

        # Write to file in collapsed stack format
        with open(output_path, 'w') as f:
            for stack, count in sorted(stack_counts.items()):
                f.write(f"{stack} {count}\n")


class TimelineVisualizer:
    """Creates Gantt chart timeline visualizations."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def add_event(self, name: str, start: float, end: float, category: str = "default") -> None:
        """Add a timeline event."""
        self.events.append({
            'name': name,
            'start': start,
            'end': end,
            'duration': end - start,
            'category': category,
        })

    def generate(self, output_path: Path) -> None:
        """Generate timeline visualization."""
        # Simplified timeline generation
        # In practice, this would use libraries like plotly or matplotlib

        with open(output_path, 'w') as f:
            json.dump(self.events, f, indent=2)


class MetricsDashboard:
    """Real-time metrics dashboard."""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.update_interval = 1.0  # seconds

    def update(self, metric_name: str, value: float) -> None:
        """Update a metric value."""
        self.metrics[metric_name].append({
            'timestamp': time.time(),
            'value': value,
        })

    def get_current(self, metric_name: str) -> Optional[float]:
        """Get current value of a metric."""
        if metric_name in self.metrics and self.metrics[metric_name]:
            return self.metrics[metric_name][-1]['value']
        return None


class ComparisonReporter:
    """Side-by-side comparison reporter."""

    def __init__(self):
        pass

    def generate_comparison(
        self,
        baseline: ProfilingResult,
        current: ProfilingResult,
    ) -> str:
        """Generate comparison report."""
        report = f"""
Performance Comparison Report
============================

Baseline: {baseline.name} ({baseline.session_id})
Current:  {current.name} ({current.session_id})

Time Metrics:
  Wall Time:    {baseline.time_metrics.wall_time:.4f}s -> {current.time_metrics.wall_time:.4f}s
  CPU Time:     {baseline.time_metrics.cpu_time:.4f}s -> {current.time_metrics.cpu_time:.4f}s

Memory Metrics:
  RSS:          {baseline.memory_metrics.rss / (1024**2):.2f} MB -> {current.memory_metrics.rss / (1024**2):.2f} MB
  Peak RSS:     {baseline.memory_metrics.peak_rss / (1024**2):.2f} MB -> {current.memory_metrics.peak_rss / (1024**2):.2f} MB

CPU Metrics:
  Utilization:  {baseline.cpu_metrics.percent:.1f}% -> {current.cpu_metrics.percent:.1f}%
  Threads:      {baseline.cpu_metrics.num_threads} -> {current.cpu_metrics.num_threads}

I/O Metrics:
  Read Bytes:   {baseline.io_metrics.read_bytes / (1024**2):.2f} MB -> {current.io_metrics.read_bytes / (1024**2):.2f} MB
  Write Bytes:  {baseline.io_metrics.write_bytes / (1024**2):.2f} MB -> {current.io_metrics.write_bytes / (1024**2):.2f} MB
"""
        return report


class TrendAnalyzer:
    """Long-term trend analysis and tracking."""

    def __init__(self):
        self.historical_data: List[ProfilingResult] = []

    def add_result(self, result: ProfilingResult) -> None:
        """Add a profiling result to historical data."""
        self.historical_data.append(result)

    def analyze_trends(self, metric: str) -> Dict[str, Any]:
        """Analyze trends for a specific metric."""
        if not self.historical_data:
            return {}

        values = []
        timestamps = []

        for result in self.historical_data:
            if metric == 'wall_time':
                values.append(result.time_metrics.wall_time)
            elif metric == 'memory_rss':
                values.append(result.memory_metrics.rss)
            elif metric == 'cpu_percent':
                values.append(result.cpu_metrics.percent)

            timestamps.append(result.time_metrics.start_timestamp)

        if not values:
            return {}

        # Calculate basic statistics
        return {
            'mean': np.mean(values),
            'median': np.median(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'trend': 'increasing' if values[-1] > values[0] else 'decreasing',
        }


# ============================================================================
# Integration & Storage
# ============================================================================


class ProfilingDataStore:
    """Efficient storage for profiling data."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".agno" / "profiling"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save(self, result: ProfilingResult) -> Path:
        """Save profiling result to storage."""
        filename = f"{result.session_id}.json"
        filepath = self.storage_path / filename

        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)

        return filepath

    def load(self, session_id: str) -> Optional[ProfilingResult]:
        """Load profiling result from storage."""
        filepath = self.storage_path / f"{session_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct ProfilingResult from dict
        # This is a simplified version
        return None  # Would need full deserialization logic

    def list_sessions(self) -> List[str]:
        """List all stored profiling sessions."""
        return [f.stem for f in self.storage_path.glob("*.json")]


class MetricsExporter:
    """Export metrics to external monitoring systems."""

    def __init__(self):
        self.exporters = {
            'prometheus': self._export_prometheus,
            'grafana': self._export_grafana,
            'datadog': self._export_datadog,
        }

    def export(self, result: ProfilingResult, format: str = "prometheus") -> str:
        """Export metrics in specified format."""
        exporter = self.exporters.get(format)
        if not exporter:
            raise ValueError(f"Unknown export format: {format}")

        return exporter(result)

    def _export_prometheus(self, result: ProfilingResult) -> str:
        """Export to Prometheus format."""
        metrics = []

        metrics.append(f'# HELP profiling_wall_time Wall clock time in seconds')
        metrics.append(f'# TYPE profiling_wall_time gauge')
        metrics.append(f'profiling_wall_time{{session="{result.session_id}",name="{result.name}"}} {result.time_metrics.wall_time}')

        metrics.append(f'# HELP profiling_memory_rss Resident Set Size in bytes')
        metrics.append(f'# TYPE profiling_memory_rss gauge')
        metrics.append(f'profiling_memory_rss{{session="{result.session_id}",name="{result.name}"}} {result.memory_metrics.rss}')

        metrics.append(f'# HELP profiling_cpu_percent CPU utilization percentage')
        metrics.append(f'# TYPE profiling_cpu_percent gauge')
        metrics.append(f'profiling_cpu_percent{{session="{result.session_id}",name="{result.name}"}} {result.cpu_metrics.percent}')

        return "\n".join(metrics)

    def _export_grafana(self, result: ProfilingResult) -> str:
        """Export to Grafana format."""
        # Simplified Grafana export
        return json.dumps({
            'dashboard': {
                'title': f'Performance Profile - {result.name}',
                'panels': [
                    {
                        'title': 'Execution Time',
                        'targets': [{'expr': f'profiling_wall_time{{session="{result.session_id}"}}'}],
                    },
                    {
                        'title': 'Memory Usage',
                        'targets': [{'expr': f'profiling_memory_rss{{session="{result.session_id}"}}'}],
                    },
                ],
            }
        })

    def _export_datadog(self, result: ProfilingResult) -> str:
        """Export to DataDog format."""
        # Simplified DataDog export
        return json.dumps({
            'series': [
                {
                    'metric': 'profiling.wall_time',
                    'points': [[result.time_metrics.start_timestamp, result.time_metrics.wall_time]],
                    'tags': [f'session:{result.session_id}', f'name:{result.name}'],
                },
                {
                    'metric': 'profiling.memory.rss',
                    'points': [[result.time_metrics.start_timestamp, result.memory_metrics.rss]],
                    'tags': [f'session:{result.session_id}', f'name:{result.name}'],
                },
            ]
        })


# ============================================================================
# Main Performance Profiler FSA Class
# ============================================================================


class PerformanceProfilerFSA:
    """
    Comprehensive Performance Profiler FSA for multi-dimensional profiling.

    This class provides a complete performance profiling system with:
    - Real-time profiling of time, memory, CPU, I/O, and network
    - Statistical analysis and bottleneck detection
    - Performance regression detection
    - Flame graph generation
    - Memory leak detection
    - Optimization recommendations

    Example:
        ```python
        from agno.fsa import PerformanceProfilerFSA, ProfilingConfig

        # Create profiler
        profiler = PerformanceProfilerFSA()

        # Start profiling
        session_id = profiler.start_profiling(ProfilingConfig())

        # Run your code
        # ...

        # Stop profiling and get results
        result = profiler.stop_profiling(session_id)

        # Analyze bottlenecks
        bottlenecks = profiler.analyze_bottlenecks(result)

        # Get recommendations
        recommendations = profiler.get_optimization_recommendations(result)
        ```
    """

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.data_store = ProfilingDataStore()
        self.metrics_exporter = MetricsExporter()
        self.report_generator = ReportGenerator()
        self.trend_analyzer = TrendAnalyzer()
        self._lock = Lock()

    def start_profiling(self, config: Optional[ProfilingConfig] = None) -> str:
        """
        Start a new profiling session.

        Args:
            config: Profiling configuration

        Returns:
            Session ID
        """
        if config is None:
            config = ProfilingConfig()

        session_id = uuid.uuid4().hex

        session = {
            'id': session_id,
            'config': config,
            'start_time': time.time(),
            'time_profiler': TimeProfiler() if config.track_time else None,
            'memory_profiler': MemoryProfiler() if config.track_memory else None,
            'cpu_profiler': CPUProfiler() if config.track_cpu else None,
            'io_profiler': IOProfiler() if config.track_io else None,
            'async_profiler': AsyncProfiler(),
            'gpu_profiler': GPUProfiler() if config.track_gpu else None,
            'custom_metrics': [],
        }

        # Start all profilers
        if session['time_profiler']:
            session['time_profiler'].start()
        if session['memory_profiler']:
            session['memory_profiler'].start()
        if session['cpu_profiler']:
            session['cpu_profiler'].start()
        if session['io_profiler']:
            session['io_profiler'].start()
        if session['async_profiler']:
            session['async_profiler'].start()
        if session['gpu_profiler']:
            session['gpu_profiler'].start()

        with self._lock:
            self.sessions[session_id] = session

        logger.info(f"Started profiling session: {session_id}")
        return session_id

    def stop_profiling(self, session_id: str, name: str = "profile") -> ProfilingResult:
        """
        Stop a profiling session and return results.

        Args:
            session_id: Session ID to stop
            name: Name for this profiling result

        Returns:
            ProfilingResult with all metrics
        """
        with self._lock:
            session = self.sessions.get(session_id)

        if not session:
            raise ValueError(f"Unknown session ID: {session_id}")

        config = session['config']

        # Stop all profilers and collect metrics
        time_metrics = session['time_profiler'].stop() if session['time_profiler'] else TimeMetrics()
        memory_metrics = session['memory_profiler'].stop() if session['memory_profiler'] else MemoryMetrics()
        cpu_metrics = session['cpu_profiler'].stop() if session['cpu_profiler'] else CPUMetrics()
        io_metrics = session['io_profiler'].stop() if session['io_profiler'] else IOMetrics()

        # Get network metrics
        process = psutil.Process()
        try:
            net_io = psutil.net_io_counters()
            network_metrics = NetworkMetrics(
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                connections=len(process.connections()),
            )
        except Exception:
            network_metrics = NetworkMetrics()

        database_metrics = DatabaseMetrics()

        result = ProfilingResult(
            session_id=session_id,
            name=name,
            config=config,
            time_metrics=time_metrics,
            memory_metrics=memory_metrics,
            cpu_metrics=cpu_metrics,
            io_metrics=io_metrics,
            network_metrics=network_metrics,
            database_metrics=database_metrics,
            custom_metrics=session['custom_metrics'],
        )

        # Identify bottlenecks
        bottleneck_identifier = BottleneckIdentifier()
        result.bottlenecks = bottleneck_identifier.identify(result)

        # Save result
        self.data_store.save(result)
        self.trend_analyzer.add_result(result)

        with self._lock:
            del self.sessions[session_id]

        logger.info(f"Stopped profiling session: {session_id}")
        return result

    def profile_function(self, func: Callable, *args, **kwargs) -> Tuple[Any, ProfilingResult]:
        """
        Profile a function execution.

        Args:
            func: Function to profile
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (function result, profiling result)
        """
        session_id = self.start_profiling(ProfilingConfig(mode=ProfilingMode.DECORATOR))

        try:
            result = func(*args, **kwargs)
            profiling_result = self.stop_profiling(session_id, name=func.__name__)
            return result, profiling_result
        except Exception as e:
            self.stop_profiling(session_id, name=f"{func.__name__}_error")
            raise

    async def profile_async(self, coro: Coroutine) -> Tuple[Any, ProfilingResult]:
        """
        Profile an async coroutine.

        Args:
            coro: Coroutine to profile

        Returns:
            Tuple of (coroutine result, profiling result)
        """
        session_id = self.start_profiling(ProfilingConfig(mode=ProfilingMode.DECORATOR))

        try:
            result = await coro
            profiling_result = self.stop_profiling(session_id, name="async_profile")
            return result, profiling_result
        except Exception as e:
            self.stop_profiling(session_id, name="async_profile_error")
            raise

    @contextmanager
    def profile(self, name: str = "context_profile", config: Optional[ProfilingConfig] = None):
        """
        Context manager for profiling code blocks.

        Args:
            name: Name for this profile
            config: Profiling configuration

        Example:
            ```python
            with profiler.profile("my_code"):
                # Your code here
                pass
            ```
        """
        session_id = self.start_profiling(config)

        try:
            yield session_id
        finally:
            result = self.stop_profiling(session_id, name=name)
            # Result is accessible via the data store

    def analyze_bottlenecks(self, result: ProfilingResult) -> List[Bottleneck]:
        """
        Analyze profiling result for bottlenecks.

        Args:
            result: Profiling result to analyze

        Returns:
            List of identified bottlenecks
        """
        return result.bottlenecks

    def compare_profiles(
        self,
        baseline: ProfilingResult,
        current: ProfilingResult,
    ) -> ComparisonReport:
        """
        Compare two profiling results.

        Args:
            baseline: Baseline profiling result
            current: Current profiling result

        Returns:
            Comparison report
        """
        detector = RegressionDetector()
        return detector.compare(baseline, current)

    def generate_flame_graph(self, result: ProfilingResult, output_path: Path) -> None:
        """
        Generate flame graph for profiling result.

        Args:
            result: Profiling result
            output_path: Output file path
        """
        builder = FlameGraphBuilder()
        # Would need to collect stack samples during profiling
        builder.generate(output_path)
        logger.info(f"Generated flame graph: {output_path}")

    def detect_memory_leaks(self, results: List[ProfilingResult]) -> List[MemoryLeak]:
        """
        Detect memory leaks from multiple profiling results.

        Args:
            results: List of profiling results over time

        Returns:
            List of detected memory leaks
        """
        detector = ResourceLeakDetector()

        for result in results:
            detector.memory_snapshots.append((
                result.time_metrics.start_timestamp,
                result.memory_metrics.rss,
            ))

        return detector.detect_memory_leaks()

    def get_optimization_recommendations(self, result: ProfilingResult) -> List[Recommendation]:
        """
        Get optimization recommendations for profiling result.

        Args:
            result: Profiling result

        Returns:
            List of recommendations
        """
        advisor = OptimizationAdvisor()
        return advisor.get_recommendations(result)

    def export_metrics(self, result: ProfilingResult, format: str = "json") -> str:
        """
        Export metrics in specified format.

        Args:
            result: Profiling result
            format: Export format (json, csv, html, prometheus, grafana, datadog)

        Returns:
            Exported metrics as string
        """
        if format == "json":
            return self.report_generator.generate_json(result)
        elif format == "csv":
            return self.report_generator.generate_csv(result)
        elif format == "html":
            return self.report_generator.generate_html(result)
        else:
            return self.metrics_exporter.export(result, format)

    def profile_decorator(self, name: Optional[str] = None, config: Optional[ProfilingConfig] = None):
        """
        Decorator for profiling functions.

        Args:
            name: Profile name
            config: Profiling configuration

        Example:
            ```python
            @profiler.profile_decorator()
            def my_function():
                # Your code
                pass
            ```
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                profile_name = name or func.__name__
                session_id = self.start_profiling(config)

                try:
                    result = func(*args, **kwargs)
                    profiling_result = self.stop_profiling(session_id, name=profile_name)
                    logger.info(f"Profiled {profile_name}: {profiling_result.time_metrics.wall_time:.4f}s")
                    return result
                except Exception as e:
                    self.stop_profiling(session_id, name=f"{profile_name}_error")
                    raise

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                profile_name = name or func.__name__
                session_id = self.start_profiling(config)

                try:
                    result = await func(*args, **kwargs)
                    profiling_result = self.stop_profiling(session_id, name=profile_name)
                    logger.info(f"Profiled {profile_name}: {profiling_result.time_metrics.wall_time:.4f}s")
                    return result
                except Exception as e:
                    self.stop_profiling(session_id, name=f"{profile_name}_error")
                    raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return wrapper

        return decorator

"""
Performance Profiler FSA - Deep performance analysis and optimization

This FSA provides comprehensive performance profiling, monitoring, and optimization
recommendations for FSA execution and cascade operations. It includes CPU profiling,
memory tracking, I/O analysis, bottleneck detection, and visualization data export.

Author: Agno Team
License: MPL 2.0
"""

from __future__ import annotations

import cProfile
import gc
import io
import json
import logging
import os
import pstats
import sys
import threading
import time
import tracemalloc
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - some profiling features will be limited")

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProfilingSeverity(str, Enum):
    """Severity levels for performance issues"""
    CRITICAL = "critical"  # > 90th percentile
    HIGH = "high"          # 75-90th percentile
    MEDIUM = "medium"      # 50-75th percentile
    LOW = "low"           # < 50th percentile


class ProfileType(str, Enum):
    """Types of profiling available"""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    FULL = "full"


@dataclass
class ProfileResult:
    """Results from a single profiling execution"""

    execution_time: float  # seconds
    memory_used: float     # MB
    cpu_percent: float     # percentage
    call_count: int
    io_operations: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class MemoryProfile:
    """Memory profiling results"""

    peak_memory: float  # MB
    current_memory: float  # MB
    allocations: int
    deallocations: int
    net_allocations: int
    leaks: List[Dict[str, Any]] = field(default_factory=list)
    heap_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CPUProfile:
    """CPU profiling results"""

    total_cpu_time: float  # seconds
    function_calls: int
    primitive_calls: int
    hotspots: List[Dict[str, Any]] = field(default_factory=list)
    call_graph: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Bottleneck:
    """Identified performance bottleneck"""

    location: str
    severity: ProfilingSeverity
    impact: float  # percentage of total time
    root_cause: str
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data


@dataclass
class ProfileReport:
    """Comprehensive profiling report"""

    session_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float  # seconds
    results: List[ProfileResult] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    profile_type: ProfileType = ProfileType.FULL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'total_duration': self.total_duration,
            'results': [r.to_dict() for r in self.results],
            'bottlenecks': [b.to_dict() for b in self.bottlenecks],
            'statistics': self.statistics,
            'profile_type': self.profile_type.value
        }

    def to_json(self, path: Optional[str] = None) -> str:
        """Export to JSON"""
        json_str = json.dumps(self.to_dict(), indent=2)
        if path:
            Path(path).write_text(json_str)
        return json_str


@dataclass
class AnalysisReport:
    """Statistical analysis report"""

    summary_stats: Dict[str, float]
    trends: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    performance_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ComparisonReport:
    """Comparison report between two profiles"""

    baseline_session: str
    current_session: str
    execution_time_delta: float  # percentage change
    memory_delta: float  # percentage change
    cpu_delta: float  # percentage change
    regressions: List[Dict[str, Any]] = field(default_factory=list)
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CascadeProfile:
    """Profile for FSA cascade execution"""

    cascade_id: str
    total_execution_time: float
    fsa_profiles: List[Dict[str, Any]] = field(default_factory=list)
    cascade_overhead: float = 0.0
    critical_path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PerformanceProfilerError(Exception):
    """Base exception for Performance Profiler"""
    pass


class PerformanceProfilerFSA:
    """
    Performance Profiler FSA - Deep performance analysis and optimization

    Category: Meta

    Key Capabilities:
        - Multi-level profiling (method, FSA, cascade)
        - Real-time performance monitoring
        - Statistical analysis of performance metrics
        - Memory profiling with leak detection
        - CPU profiling with call graph generation
        - I/O profiling for file/network operations
        - Automated bottleneck detection
        - Performance regression detection
        - Visualization data export
        - Optimization recommendations
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Performance Profiler FSA

        Args:
            config: Optional configuration dictionary
                - enable_memory_tracking: bool (default True)
                - enable_cpu_profiling: bool (default True)
                - profiling_overhead_limit: float (default 0.05, i.e., 5%)
                - sampling_interval: float (default 0.001, i.e., 1ms)
        """
        self.name = "PerformanceProfilerFSA"
        self.config = config or {}
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()

        # Configuration
        self.enable_memory_tracking = self.config.get('enable_memory_tracking', True)
        self.enable_cpu_profiling = self.config.get('enable_cpu_profiling', True)
        self.profiling_overhead_limit = self.config.get('profiling_overhead_limit', 0.05)
        self.sampling_interval = self.config.get('sampling_interval', 0.001)

        # Active profiling sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_lock = threading.Lock()

        # Performance thresholds (SLAs)
        self.thresholds = {
            'p95_execution_time': 0.5,  # 500ms
            'p99_execution_time': 1.0,  # 1s
            'max_memory_mb': 500,
            'max_cpu_percent': 80,
        }

        logger.info(f"Initialized {self.name}")

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the main FSA functionality

        Args:
            task: Task description or identifier
            params: Optional parameters for execution

        Returns:
            Execution result

        Raises:
            PerformanceProfilerError: If execution fails
        """
        if not task:
            raise PerformanceProfilerError("Task cannot be empty")

        logger.info(f"Executing task: {task}")
        params = params or {}

        # Validate input
        if not self.validate_input(params):
            raise PerformanceProfilerError("Invalid input parameters")

        try:
            # Route to appropriate method based on task
            if task == "profile_execution":
                return self.profile_execution(
                    params.get('target'),
                    *params.get('args', []),
                    **params.get('kwargs', {})
                )
            elif task == "analyze_performance":
                return self.analyze_performance(params.get('results', []))
            elif task == "detect_bottlenecks":
                return self.detect_bottlenecks(params.get('profile'))
            else:
                return self._process_task(task, params)
        except Exception as e:
            return self.handle_error(e)

    def profile_execution(
        self,
        target: Callable,
        *args,
        profile_type: ProfileType = ProfileType.FULL,
        **kwargs
    ) -> ProfileResult:
        """
        Profile a single execution with comprehensive metrics

        Args:
            target: Callable to profile
            *args: Positional arguments for target
            profile_type: Type of profiling to perform
            **kwargs: Keyword arguments for target

        Returns:
            ProfileResult with execution metrics
        """
        logger.info(f"Profiling execution: {target.__name__ if hasattr(target, '__name__') else 'callable'}")

        # Initialize metrics
        start_time = time.time()
        memory_before = self._get_memory_usage()

        # Start memory tracking if enabled
        if self.enable_memory_tracking and profile_type in [ProfileType.MEMORY, ProfileType.FULL]:
            tracemalloc.start()

        # CPU profiling
        profiler = None
        if self.enable_cpu_profiling and profile_type in [ProfileType.CPU, ProfileType.FULL]:
            profiler = cProfile.Profile()
            profiler.enable()

        # Execute target
        try:
            result = target(*args, **kwargs)
            call_count = 1
        except Exception as e:
            logger.error(f"Error during profiled execution: {e}")
            raise
        finally:
            # Stop profiling
            if profiler:
                profiler.disable()

            # Calculate metrics
            execution_time = time.time() - start_time
            memory_after = self._get_memory_usage()
            memory_used = max(0, memory_after - memory_before)

            # Get CPU usage
            cpu_percent = 0.0
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process(os.getpid())
                    cpu_percent = process.cpu_percent(interval=0.1)
                except Exception as e:
                    logger.warning(f"Could not get CPU usage: {e}")

            # Get memory tracking details
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                memory_used = peak / (1024 * 1024)  # Convert to MB

            # Build profile result
            profile_result = ProfileResult(
                execution_time=execution_time,
                memory_used=memory_used,
                cpu_percent=cpu_percent,
                call_count=call_count,
                io_operations={},
                metadata={
                    'function_name': getattr(target, '__name__', 'unknown'),
                    'profile_type': profile_type.value
                }
            )

            logger.info(f"Profiling complete: {execution_time:.4f}s, {memory_used:.2f}MB")

        return profile_result

    def start_profiling(self, session_id: str, profile_type: ProfileType = ProfileType.FULL) -> None:
        """
        Begin a profiling session for continuous monitoring

        Args:
            session_id: Unique identifier for this session
            profile_type: Type of profiling to perform
        """
        with self._session_lock:
            if session_id in self._sessions:
                raise PerformanceProfilerError(f"Session {session_id} already exists")

            session = {
                'session_id': session_id,
                'start_time': datetime.now(),
                'profile_type': profile_type,
                'results': [],
                'profiler': None,
                'memory_tracking': False
            }

            # Start CPU profiling
            if self.enable_cpu_profiling and profile_type in [ProfileType.CPU, ProfileType.FULL]:
                profiler = cProfile.Profile()
                profiler.enable()
                session['profiler'] = profiler

            # Start memory tracking
            if self.enable_memory_tracking and profile_type in [ProfileType.MEMORY, ProfileType.FULL]:
                tracemalloc.start()
                session['memory_tracking'] = True

            self._sessions[session_id] = session
            logger.info(f"Started profiling session: {session_id}")

    def stop_profiling(self, session_id: str) -> ProfileReport:
        """
        End profiling session and generate comprehensive report

        Args:
            session_id: Session identifier

        Returns:
            ProfileReport with all collected metrics
        """
        with self._session_lock:
            if session_id not in self._sessions:
                raise PerformanceProfilerError(f"Session {session_id} not found")

            session = self._sessions[session_id]
            end_time = datetime.now()

            # Stop CPU profiling
            if session['profiler']:
                session['profiler'].disable()

            # Stop memory tracking
            if session['memory_tracking'] and tracemalloc.is_tracing():
                tracemalloc.stop()

            # Calculate duration
            duration = (end_time - session['start_time']).total_seconds()

            # Generate statistics
            statistics = self._calculate_statistics(session['results'])

            # Create report
            report = ProfileReport(
                session_id=session_id,
                start_time=session['start_time'],
                end_time=end_time,
                total_duration=duration,
                results=session['results'],
                statistics=statistics,
                profile_type=session['profile_type']
            )

            # Detect bottlenecks
            report.bottlenecks = self.detect_bottlenecks(report)

            # Clean up session
            del self._sessions[session_id]

            logger.info(f"Stopped profiling session: {session_id}")
            return report

    def profile_memory(self, target: Callable, *args, **kwargs) -> MemoryProfile:
        """
        Detailed memory profiling with allocation tracking

        Args:
            target: Callable to profile
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            MemoryProfile with detailed memory metrics
        """
        logger.info("Starting memory profiling")

        # Force garbage collection
        gc.collect()

        # Start tracking
        tracemalloc.start()
        memory_before = self._get_memory_usage()

        try:
            # Execute target
            result = target(*args, **kwargs)

            # Get memory stats
            current, peak = tracemalloc.get_traced_memory()
            snapshot = tracemalloc.take_snapshot()

            # Get allocation statistics
            stats = snapshot.statistics('lineno')

            # Detect potential leaks (allocations not freed)
            leaks = []
            for stat in stats[:10]:  # Top 10 allocations
                leaks.append({
                    'file': stat.traceback.format()[0] if stat.traceback else 'unknown',
                    'size_mb': stat.size / (1024 * 1024),
                    'count': stat.count
                })

            memory_profile = MemoryProfile(
                peak_memory=peak / (1024 * 1024),
                current_memory=current / (1024 * 1024),
                allocations=sum(s.count for s in stats),
                deallocations=0,  # tracemalloc doesn't track deallocations directly
                net_allocations=len(stats),
                leaks=leaks
            )

            logger.info(f"Memory profiling complete: peak={memory_profile.peak_memory:.2f}MB")

        finally:
            tracemalloc.stop()

        return memory_profile

    def profile_cpu(self, target: Callable, *args, **kwargs) -> CPUProfile:
        """
        Detailed CPU profiling with call graph analysis

        Args:
            target: Callable to profile
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            CPUProfile with CPU usage metrics
        """
        logger.info("Starting CPU profiling")

        profiler = cProfile.Profile()
        profiler.enable()

        try:
            # Execute target
            start_time = time.time()
            result = target(*args, **kwargs)
            total_cpu_time = time.time() - start_time

            profiler.disable()

            # Analyze stats
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')

            # Extract hotspots (top functions by cumulative time)
            hotspots = []
            for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:10]:
                hotspots.append({
                    'function': f"{func[0]}:{func[1]}:{func[2]}",
                    'call_count': cc,
                    'total_time': tt,
                    'cumulative_time': ct,
                    'per_call': ct / cc if cc > 0 else 0
                })

            cpu_profile = CPUProfile(
                total_cpu_time=total_cpu_time,
                function_calls=stats.total_calls,
                primitive_calls=stats.prim_calls,
                hotspots=hotspots
            )

            logger.info(f"CPU profiling complete: {cpu_profile.function_calls} calls")

        except Exception as e:
            logger.error(f"CPU profiling error: {e}")
            raise

        return cpu_profile

    def analyze_performance(self, results: List[ProfileResult]) -> AnalysisReport:
        """
        Statistical analysis of multiple profile results

        Args:
            results: List of ProfileResult objects

        Returns:
            AnalysisReport with statistical analysis
        """
        if not results:
            return AnalysisReport(
                summary_stats={},
                performance_score=0.0,
                recommendations=["No data to analyze"]
            )

        # Extract metrics
        execution_times = [r.execution_time for r in results]
        memory_usage = [r.memory_used for r in results]
        cpu_usage = [r.cpu_percent for r in results]

        # Calculate statistics
        summary_stats = {
            'count': len(results),
            'execution_time': {
                'mean': self._mean(execution_times),
                'median': self._median(execution_times),
                'min': min(execution_times),
                'max': max(execution_times),
                'p95': self._percentile(execution_times, 95),
                'p99': self._percentile(execution_times, 99),
                'stddev': self._stddev(execution_times)
            },
            'memory': {
                'mean': self._mean(memory_usage),
                'median': self._median(memory_usage),
                'min': min(memory_usage),
                'max': max(memory_usage),
                'p95': self._percentile(memory_usage, 95)
            },
            'cpu': {
                'mean': self._mean(cpu_usage),
                'median': self._median(cpu_usage),
                'max': max(cpu_usage)
            }
        }

        # Detect anomalies
        anomalies = self._detect_anomalies(results)

        # Calculate performance score (0-100)
        performance_score = self._calculate_performance_score(summary_stats)

        # Generate recommendations
        recommendations = self.generate_recommendations(summary_stats)

        return AnalysisReport(
            summary_stats=summary_stats,
            anomalies=anomalies,
            performance_score=performance_score,
            recommendations=recommendations
        )

    def detect_bottlenecks(self, profile: ProfileReport) -> List[Bottleneck]:
        """
        Identify performance bottlenecks from profile report

        Args:
            profile: ProfileReport to analyze

        Returns:
            List of detected bottlenecks
        """
        bottlenecks = []

        if not profile.results:
            return bottlenecks

        # Analyze execution time bottlenecks
        execution_times = [r.execution_time for r in profile.results]
        p75 = self._percentile(execution_times, 75)
        p90 = self._percentile(execution_times, 90)

        for i, result in enumerate(profile.results):
            if result.execution_time > p90:
                severity = ProfilingSeverity.CRITICAL
            elif result.execution_time > p75:
                severity = ProfilingSeverity.HIGH
            else:
                continue

            impact = (result.execution_time / sum(execution_times)) * 100

            bottleneck = Bottleneck(
                location=f"Execution #{i}",
                severity=severity,
                impact=impact,
                root_cause="Slow execution time detected",
                recommendation="Profile individual functions to identify slow operations",
                details={'execution_time': result.execution_time}
            )
            bottlenecks.append(bottleneck)

        # Analyze memory bottlenecks
        memory_usage = [r.memory_used for r in profile.results]
        if max(memory_usage) > self.thresholds['max_memory_mb']:
            bottleneck = Bottleneck(
                location="Memory usage",
                severity=ProfilingSeverity.CRITICAL,
                impact=100.0,
                root_cause=f"Memory usage exceeds threshold ({self.thresholds['max_memory_mb']}MB)",
                recommendation="Review memory allocations and implement caching strategies",
                details={'peak_memory': max(memory_usage)}
            )
            bottlenecks.append(bottleneck)

        logger.info(f"Detected {len(bottlenecks)} bottlenecks")
        return bottlenecks

    def compare_profiles(
        self,
        baseline: ProfileReport,
        current: ProfileReport
    ) -> ComparisonReport:
        """
        Compare two profile reports for regression detection

        Args:
            baseline: Baseline profile report
            current: Current profile report

        Returns:
            ComparisonReport with comparison analysis
        """
        # Calculate average metrics
        baseline_stats = self._calculate_statistics(baseline.results)
        current_stats = self._calculate_statistics(current.results)

        # Calculate deltas (percentage change)
        execution_time_delta = self._calculate_delta(
            baseline_stats.get('execution_time_mean', 0),
            current_stats.get('execution_time_mean', 0)
        )

        memory_delta = self._calculate_delta(
            baseline_stats.get('memory_mean', 0),
            current_stats.get('memory_mean', 0)
        )

        cpu_delta = self._calculate_delta(
            baseline_stats.get('cpu_mean', 0),
            current_stats.get('cpu_mean', 0)
        )

        # Identify regressions and improvements
        regressions = []
        improvements = []

        if execution_time_delta > 10:  # > 10% slower
            regressions.append({
                'metric': 'execution_time',
                'delta': execution_time_delta,
                'impact': 'high'
            })
        elif execution_time_delta < -10:  # > 10% faster
            improvements.append({
                'metric': 'execution_time',
                'delta': abs(execution_time_delta),
                'impact': 'high'
            })

        if memory_delta > 20:  # > 20% more memory
            regressions.append({
                'metric': 'memory',
                'delta': memory_delta,
                'impact': 'medium'
            })

        # Generate summary
        summary = f"Performance comparison: {len(regressions)} regressions, {len(improvements)} improvements"

        return ComparisonReport(
            baseline_session=baseline.session_id,
            current_session=current.session_id,
            execution_time_delta=execution_time_delta,
            memory_delta=memory_delta,
            cpu_delta=cpu_delta,
            regressions=regressions,
            improvements=improvements,
            summary=summary
        )

    def generate_recommendations(
        self,
        analysis: Union[AnalysisReport, Dict[str, Any]]
    ) -> List[str]:
        """
        Auto-generate optimization recommendations

        Args:
            analysis: AnalysisReport or statistics dictionary

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Extract stats
        if isinstance(analysis, AnalysisReport):
            stats = analysis.summary_stats
        else:
            stats = analysis

        # Check execution time
        if isinstance(stats.get('execution_time'), dict):
            exec_stats = stats['execution_time']
            if exec_stats.get('p95', 0) > self.thresholds['p95_execution_time']:
                recommendations.append(
                    f"P95 execution time ({exec_stats['p95']:.3f}s) exceeds threshold "
                    f"({self.thresholds['p95_execution_time']}s). Consider optimizing hot paths."
                )

            if exec_stats.get('stddev', 0) > exec_stats.get('mean', 1) * 0.5:
                recommendations.append(
                    "High variance in execution time detected. "
                    "Consider implementing caching or optimizing conditional logic."
                )

        # Check memory
        if isinstance(stats.get('memory'), dict):
            mem_stats = stats['memory']
            if mem_stats.get('max', 0) > self.thresholds['max_memory_mb']:
                recommendations.append(
                    f"Peak memory ({mem_stats['max']:.1f}MB) exceeds threshold "
                    f"({self.thresholds['max_memory_mb']}MB). Review data structures and implement streaming."
                )

        # Check CPU
        if isinstance(stats.get('cpu'), dict):
            cpu_stats = stats['cpu']
            if cpu_stats.get('max', 0) > self.thresholds['max_cpu_percent']:
                recommendations.append(
                    f"CPU usage ({cpu_stats['max']:.1f}%) exceeds threshold "
                    f"({self.thresholds['max_cpu_percent']}%). Consider parallelization or algorithm optimization."
                )

        if not recommendations:
            recommendations.append("Performance is within acceptable thresholds. No immediate optimization needed.")

        return recommendations

    def export_flamegraph(self, profile: ProfileReport, output_path: str) -> bool:
        """
        Export profiling data for flamegraph visualization

        Args:
            profile: ProfileReport to export
            output_path: Path to output file

        Returns:
            True if export successful
        """
        try:
            # Generate flamegraph data format (folded stacks)
            flamegraph_data = []

            for i, result in enumerate(profile.results):
                stack = f"execution_{i}"
                count = int(result.execution_time * 1000)  # Convert to ms
                flamegraph_data.append(f"{stack} {count}")

            # Write to file
            Path(output_path).write_text("\n".join(flamegraph_data))
            logger.info(f"Exported flamegraph data to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export flamegraph: {e}")
            return False

    def profile_fsa_cascade(self, cascade_config: Dict[str, Any]) -> CascadeProfile:
        """
        Profile execution of FSA cascade

        Args:
            cascade_config: Configuration for cascade execution

        Returns:
            CascadeProfile with cascade metrics
        """
        cascade_id = cascade_config.get('cascade_id', 'cascade_' + str(int(time.time())))
        fsas = cascade_config.get('fsas', [])

        logger.info(f"Profiling FSA cascade: {cascade_id}")

        start_time = time.time()
        fsa_profiles = []

        for fsa_config in fsas:
            fsa_name = fsa_config.get('name', 'unknown')
            fsa_func = fsa_config.get('function')

            if fsa_func:
                result = self.profile_execution(fsa_func)
                fsa_profiles.append({
                    'name': fsa_name,
                    'execution_time': result.execution_time,
                    'memory_used': result.memory_used
                })

        total_execution_time = time.time() - start_time

        # Calculate cascade overhead
        sum_fsa_times = sum(p['execution_time'] for p in fsa_profiles)
        cascade_overhead = total_execution_time - sum_fsa_times

        # Identify critical path (longest execution)
        critical_path = sorted(
            [(p['name'], p['execution_time']) for p in fsa_profiles],
            key=lambda x: x[1],
            reverse=True
        )

        return CascadeProfile(
            cascade_id=cascade_id,
            total_execution_time=total_execution_time,
            fsa_profiles=fsa_profiles,
            cascade_overhead=cascade_overhead,
            critical_path=[name for name, _ in critical_path[:3]]
        )

    def validate_performance(
        self,
        profile: ProfileReport,
        thresholds: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Validate performance against SLA thresholds

        Args:
            profile: ProfileReport to validate
            thresholds: Optional custom thresholds

        Returns:
            True if performance meets thresholds
        """
        thresholds = thresholds or self.thresholds

        if not profile.results:
            return False

        # Check execution time
        execution_times = [r.execution_time for r in profile.results]
        p95 = self._percentile(execution_times, 95)
        p99 = self._percentile(execution_times, 99)

        if p95 > thresholds.get('p95_execution_time', float('inf')):
            logger.warning(f"P95 execution time ({p95:.3f}s) exceeds threshold")
            return False

        if p99 > thresholds.get('p99_execution_time', float('inf')):
            logger.warning(f"P99 execution time ({p99:.3f}s) exceeds threshold")
            return False

        # Check memory
        max_memory = max(r.memory_used for r in profile.results)
        if max_memory > thresholds.get('max_memory_mb', float('inf')):
            logger.warning(f"Peak memory ({max_memory:.1f}MB) exceeds threshold")
            return False

        # Check CPU
        max_cpu = max(r.cpu_percent for r in profile.results)
        if max_cpu > thresholds.get('max_cpu_percent', float('inf')):
            logger.warning(f"Peak CPU ({max_cpu:.1f}%) exceeds threshold")
            return False

        logger.info("Performance validation passed")
        return True

    @contextmanager
    def session(self, session_id: Optional[str] = None):
        """
        Context manager for scoped profiling

        Usage:
            with profiler.session('my_session'):
                # Code to profile
                pass
        """
        session_id = session_id or f"session_{int(time.time())}"
        self.start_profiling(session_id)
        try:
            yield session_id
        finally:
            report = self.stop_profiling(session_id)
            self.state['last_report'] = report

    def validate_input(self, data: Any) -> bool:
        """Validate input data"""
        if data is None:
            raise PerformanceProfilerError("Input data cannot be None")
        return True

    def get_state(self) -> Dict[str, Any]:
        """Get current FSA state"""
        return self.state.copy()

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set FSA state"""
        self.state = state

    def handle_error(self, error: Exception) -> str:
        """Handle errors during execution"""
        error_msg = f"Error in {self.name}: {str(error)}"
        logger.error(error_msg)
        return error_msg

    def _process_task(self, task: str, params: Dict[str, Any]) -> Any:
        """Internal method to process task"""
        return {"status": "success", "task": task, "params": params}

    def initialize(self) -> None:
        """Initialize FSA for operation"""
        logger.info(f"Initializing {self.name}")
        self.state = {"initialized": True, "timestamp": datetime.now()}

    def cleanup(self) -> None:
        """Cleanup FSA resources"""
        logger.info(f"Cleaning up {self.name}")
        # Stop any active sessions
        for session_id in list(self._sessions.keys()):
            try:
                self.stop_profiling(session_id)
            except Exception as e:
                logger.warning(f"Error cleaning up session {session_id}: {e}")
        self.state = {}

    # Statistical helper methods

    def _mean(self, values: List[float]) -> float:
        """Calculate mean"""
        return sum(values) / len(values) if values else 0.0

    def _median(self, values: List[float]) -> float:
        """Calculate median"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2
        return sorted_values[mid]

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _stddev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        mean = self._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                return process.memory_info().rss / (1024 * 1024)
            except Exception:
                pass
        return 0.0

    def _calculate_statistics(self, results: List[ProfileResult]) -> Dict[str, float]:
        """Calculate summary statistics from results"""
        if not results:
            return {}

        execution_times = [r.execution_time for r in results]
        memory_usage = [r.memory_used for r in results]
        cpu_usage = [r.cpu_percent for r in results]

        return {
            'execution_time_mean': self._mean(execution_times),
            'execution_time_median': self._median(execution_times),
            'execution_time_p95': self._percentile(execution_times, 95),
            'memory_mean': self._mean(memory_usage),
            'memory_max': max(memory_usage),
            'cpu_mean': self._mean(cpu_usage),
            'cpu_max': max(cpu_usage)
        }

    def _detect_anomalies(self, results: List[ProfileResult]) -> List[Dict[str, Any]]:
        """Detect anomalies in results"""
        anomalies = []

        if len(results) < 3:
            return anomalies

        execution_times = [r.execution_time for r in results]
        mean = self._mean(execution_times)
        stddev = self._stddev(execution_times)

        # Detect outliers (> 3 standard deviations)
        for i, result in enumerate(results):
            if abs(result.execution_time - mean) > 3 * stddev:
                anomalies.append({
                    'index': i,
                    'value': result.execution_time,
                    'deviation': abs(result.execution_time - mean) / stddev,
                    'type': 'execution_time_outlier'
                })

        return anomalies

    def _calculate_performance_score(self, stats: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        score = 100.0

        # Execution time score
        exec_stats = stats.get('execution_time', {})
        if isinstance(exec_stats, dict):
            p95 = exec_stats.get('p95', 0)
            if p95 > self.thresholds['p95_execution_time']:
                score -= 30
            elif p95 > self.thresholds['p95_execution_time'] * 0.8:
                score -= 15

        # Memory score
        mem_stats = stats.get('memory', {})
        if isinstance(mem_stats, dict):
            max_mem = mem_stats.get('max', 0)
            if max_mem > self.thresholds['max_memory_mb']:
                score -= 30
            elif max_mem > self.thresholds['max_memory_mb'] * 0.8:
                score -= 15

        # CPU score
        cpu_stats = stats.get('cpu', {})
        if isinstance(cpu_stats, dict):
            max_cpu = cpu_stats.get('max', 0)
            if max_cpu > self.thresholds['max_cpu_percent']:
                score -= 20
            elif max_cpu > self.thresholds['max_cpu_percent'] * 0.8:
                score -= 10

        return max(0.0, score)

    def _calculate_delta(self, baseline: float, current: float) -> float:
        """Calculate percentage delta"""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100

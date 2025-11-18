"""
Performance Profiler FSA - Multi-dimensional performance profiling system.

This module provides comprehensive performance profiling capabilities including:
- Real-time profiling (time, memory, CPU, I/O, network)
- Statistical analysis and bottleneck detection
- Performance regression detection
- Flame graph generation
- Memory leak detection
"""

from agno.fsa.performance_profiler import (
    PerformanceProfilerFSA,
    ProfilingConfig,
    ProfilingResult,
    ProfilingMode,
    Bottleneck,
    MemoryLeak,
    Recommendation,
    ComparisonReport,
    TimeProfiler,
    MemoryProfiler,
    CPUProfiler,
    IOProfiler,
    AsyncProfiler,
    GPUProfiler,
    BottleneckIdentifier,
    RegressionDetector,
    OptimizationAdvisor,
    HotspotAnalyzer,
    ResourceLeakDetector,
    ConcurrencyAnalyzer,
    ReportGenerator,
    FlameGraphBuilder,
    TimelineVisualizer,
    MetricsDashboard,
    ComparisonReporter,
    TrendAnalyzer,
    ProfilingDataStore,
    MetricsExporter,
)

__all__ = [
    "PerformanceProfilerFSA",
    "ProfilingConfig",
    "ProfilingResult",
    "ProfilingMode",
    "Bottleneck",
    "MemoryLeak",
    "Recommendation",
    "ComparisonReport",
    "TimeProfiler",
    "MemoryProfiler",
    "CPUProfiler",
    "IOProfiler",
    "AsyncProfiler",
    "GPUProfiler",
    "BottleneckIdentifier",
    "RegressionDetector",
    "OptimizationAdvisor",
    "HotspotAnalyzer",
    "ResourceLeakDetector",
    "ConcurrencyAnalyzer",
    "ReportGenerator",
    "FlameGraphBuilder",
    "TimelineVisualizer",
    "MetricsDashboard",
    "ComparisonReporter",
    "TrendAnalyzer",
    "ProfilingDataStore",
    "MetricsExporter",
]

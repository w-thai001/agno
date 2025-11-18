"""
Comprehensive test suite for Performance Profiler FSA.

This test suite covers all profiling modes, metrics tracking, bottleneck detection,
memory leak detection, regression detection, and reporting functionality.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from agno.fsa.performance_profiler import (
    PerformanceProfilerFSA,
    ProfilingConfig,
    ProfilingMode,
    ProfilingResult,
    Bottleneck,
    BottleneckSeverity,
    MetricType,
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
    TimeMetrics,
    MemoryMetrics,
    CPUMetrics,
    IOMetrics,
    NetworkMetrics,
    DatabaseMetrics,
    CustomMetric,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def profiler():
    """Create a Performance Profiler FSA instance."""
    return PerformanceProfilerFSA()


@pytest.fixture
def config():
    """Create a default profiling config."""
    return ProfilingConfig()


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_result():
    """Create a sample profiling result."""
    return ProfilingResult(
        session_id="test_session_123",
        name="test_profile",
        config=ProfilingConfig(),
        time_metrics=TimeMetrics(
            wall_time=1.5,
            cpu_time=1.2,
            user_time=0.9,
            system_time=0.3,
            start_timestamp=time.time(),
            end_timestamp=time.time() + 1.5,
        ),
        memory_metrics=MemoryMetrics(
            rss=100 * 1024 * 1024,  # 100 MB
            vms=200 * 1024 * 1024,  # 200 MB
            peak_rss=120 * 1024 * 1024,
            allocations=1000,
            deallocations=800,
            total_allocated=50 * 1024 * 1024,
            gc_collections=[5, 2, 1],
            gc_time=0.05,
        ),
        cpu_metrics=CPUMetrics(
            percent=75.0,
            per_core=[70.0, 80.0, 75.0, 70.0],
            num_threads=8,
            context_switches=500,
            num_fds=20,
        ),
        io_metrics=IOMetrics(
            read_count=100,
            write_count=50,
            read_bytes=10 * 1024 * 1024,  # 10 MB
            write_bytes=5 * 1024 * 1024,  # 5 MB
            read_time=0.2,
            write_time=0.1,
        ),
        network_metrics=NetworkMetrics(
            bytes_sent=1024 * 1024,  # 1 MB
            bytes_recv=2 * 1024 * 1024,  # 2 MB
            packets_sent=100,
            packets_recv=200,
            connections=5,
        ),
        database_metrics=DatabaseMetrics(
            query_count=20,
            total_duration=0.5,
            slow_queries=[],
        ),
    )


# ============================================================================
# TimeProfiler Tests
# ============================================================================


class TestTimeProfiler:
    """Tests for TimeProfiler."""

    def test_time_profiler_initialization(self):
        """Test TimeProfiler initialization."""
        profiler = TimeProfiler()
        assert profiler.start_wall == 0.0
        assert profiler.end_wall == 0.0
        assert profiler.start_cpu == 0.0
        assert profiler.end_cpu == 0.0

    def test_time_profiler_start(self):
        """Test starting time profiling."""
        profiler = TimeProfiler()
        profiler.start()
        assert profiler.start_wall > 0
        assert profiler.start_cpu >= 0
        assert profiler.start_rusage is not None

    def test_time_profiler_stop(self):
        """Test stopping time profiling."""
        profiler = TimeProfiler()
        profiler.start()
        time.sleep(0.1)
        metrics = profiler.stop()

        assert isinstance(metrics, TimeMetrics)
        assert metrics.wall_time >= 0.1
        assert metrics.cpu_time >= 0
        assert metrics.user_time >= 0
        assert metrics.system_time >= 0

    def test_time_profiler_precision(self):
        """Test nanosecond precision timing."""
        profiler = TimeProfiler()
        profiler.start()
        # Very short operation
        _ = sum(range(100))
        metrics = profiler.stop()

        assert metrics.wall_time > 0
        assert metrics.wall_time < 0.01  # Should be very fast

    def test_time_profiler_cpu_time_accuracy(self):
        """Test CPU time accuracy."""
        profiler = TimeProfiler()
        profiler.start()

        # CPU-bound operation
        _ = sum(i * i for i in range(100000))

        metrics = profiler.stop()
        assert metrics.cpu_time > 0
        assert metrics.user_time > 0


# ============================================================================
# MemoryProfiler Tests
# ============================================================================


class TestMemoryProfiler:
    """Tests for MemoryProfiler."""

    def test_memory_profiler_initialization(self):
        """Test MemoryProfiler initialization."""
        profiler = MemoryProfiler()
        assert profiler.enable_tracemalloc is True
        assert profiler.start_mem is None
        assert profiler.end_mem is None

    def test_memory_profiler_start(self):
        """Test starting memory profiling."""
        profiler = MemoryProfiler()
        profiler.start()
        assert profiler.start_mem is not None
        assert len(profiler.gc_stats_start) == 3

    def test_memory_profiler_stop(self):
        """Test stopping memory profiling."""
        profiler = MemoryProfiler()
        profiler.start()

        # Allocate some memory
        data = [0] * 10000

        metrics = profiler.stop()
        assert isinstance(metrics, MemoryMetrics)
        assert metrics.rss > 0
        assert metrics.vms > 0

    def test_memory_profiler_snapshots(self):
        """Test memory snapshots."""
        profiler = MemoryProfiler()
        profiler.start()

        profiler.snapshot()
        data = [0] * 100000
        profiler.snapshot()

        assert len(profiler.snapshots) == 2

        metrics = profiler.stop()
        assert metrics is not None

    def test_memory_profiler_gc_tracking(self):
        """Test garbage collection tracking."""
        profiler = MemoryProfiler()
        profiler.start()

        # Create and delete objects to trigger GC
        for _ in range(10):
            _ = [0] * 10000

        metrics = profiler.stop()
        assert len(metrics.gc_collections) == 3
        assert metrics.gc_time >= 0

    def test_memory_profiler_without_tracemalloc(self):
        """Test memory profiling without tracemalloc."""
        profiler = MemoryProfiler(enable_tracemalloc=False)
        profiler.start()
        metrics = profiler.stop()
        assert isinstance(metrics, MemoryMetrics)


# ============================================================================
# CPUProfiler Tests
# ============================================================================


class TestCPUProfiler:
    """Tests for CPUProfiler."""

    def test_cpu_profiler_initialization(self):
        """Test CPUProfiler initialization."""
        profiler = CPUProfiler()
        assert profiler.start_cpu_times is None
        assert profiler.end_cpu_times is None
        assert len(profiler.cpu_samples) == 0

    def test_cpu_profiler_start(self):
        """Test starting CPU profiling."""
        profiler = CPUProfiler()
        profiler.start()
        assert profiler.start_cpu_times is not None

    def test_cpu_profiler_sampling(self):
        """Test CPU sampling."""
        profiler = CPUProfiler()
        profiler.start()

        for _ in range(3):
            profiler.sample()
            time.sleep(0.1)

        assert len(profiler.cpu_samples) >= 3
        assert len(profiler.per_core_samples) >= 3

    def test_cpu_profiler_stop(self):
        """Test stopping CPU profiling."""
        profiler = CPUProfiler()
        profiler.start()

        # CPU-intensive work
        _ = sum(i * i for i in range(100000))

        profiler.sample()
        metrics = profiler.stop()

        assert isinstance(metrics, CPUMetrics)
        assert metrics.num_threads > 0

    def test_cpu_profiler_per_core_metrics(self):
        """Test per-core CPU metrics."""
        profiler = CPUProfiler()
        profiler.start()

        for _ in range(5):
            profiler.sample()
            time.sleep(0.05)

        metrics = profiler.stop()
        assert isinstance(metrics.per_core, list)


# ============================================================================
# IOProfiler Tests
# ============================================================================


class TestIOProfiler:
    """Tests for IOProfiler."""

    def test_io_profiler_initialization(self):
        """Test IOProfiler initialization."""
        profiler = IOProfiler()
        assert profiler.start_io is None
        assert profiler.end_io is None
        assert len(profiler.io_operations) == 0

    def test_io_profiler_start(self):
        """Test starting I/O profiling."""
        profiler = IOProfiler()
        profiler.start()

    def test_io_profiler_log_operation(self):
        """Test logging I/O operations."""
        profiler = IOProfiler()
        profiler.start()

        profiler.log_operation("read", 1024, 0.01)
        profiler.log_operation("write", 2048, 0.02)

        assert len(profiler.io_operations) == 2
        assert profiler.io_operations[0]['operation'] == "read"
        assert profiler.io_operations[0]['bytes'] == 1024

    def test_io_profiler_stop(self):
        """Test stopping I/O profiling."""
        profiler = IOProfiler()
        profiler.start()

        profiler.log_operation("read", 1024, 0.01)
        profiler.log_operation("write", 2048, 0.02)

        metrics = profiler.stop()
        assert isinstance(metrics, IOMetrics)
        assert metrics.read_time == 0.01
        assert metrics.write_time == 0.02

    def test_io_profiler_with_file_operations(self, temp_dir):
        """Test I/O profiling with actual file operations."""
        profiler = IOProfiler()
        profiler.start()

        # Perform file operations
        test_file = temp_dir / "test.txt"
        start = time.time()
        with open(test_file, 'w') as f:
            f.write("test data" * 1000)
        write_duration = time.time() - start

        profiler.log_operation("write", len("test data") * 1000, write_duration)

        start = time.time()
        with open(test_file, 'r') as f:
            _ = f.read()
        read_duration = time.time() - start

        profiler.log_operation("read", len("test data") * 1000, read_duration)

        metrics = profiler.stop()
        assert metrics.read_time > 0
        assert metrics.write_time > 0


# ============================================================================
# AsyncProfiler Tests
# ============================================================================


class TestAsyncProfiler:
    """Tests for AsyncProfiler."""

    def test_async_profiler_initialization(self):
        """Test AsyncProfiler initialization."""
        profiler = AsyncProfiler()
        assert len(profiler.async_tasks) == 0
        assert len(profiler.event_loop_samples) == 0

    def test_async_profiler_track_task(self):
        """Test tracking async tasks."""
        profiler = AsyncProfiler()
        profiler.start()

        profiler.track_task("task1", "my_coroutine")
        assert "task1" in profiler.async_tasks
        assert profiler.async_tasks["task1"]["name"] == "my_coroutine"

    def test_async_profiler_complete_task(self):
        """Test completing async tasks."""
        profiler = AsyncProfiler()
        profiler.start()

        profiler.track_task("task1", "my_coroutine")
        time.sleep(0.1)
        profiler.complete_task("task1")

        assert profiler.async_tasks["task1"]["end"] is not None
        assert profiler.async_tasks["task1"]["duration"] >= 0.1

    def test_async_profiler_stop(self):
        """Test stopping async profiling."""
        profiler = AsyncProfiler()
        profiler.start()

        profiler.track_task("task1", "coro1")
        profiler.complete_task("task1")
        profiler.track_task("task2", "coro2")
        profiler.complete_task("task2")

        metrics = profiler.stop()
        assert metrics["total_tasks"] == 2
        assert metrics["completed_tasks"] == 2
        assert metrics["avg_task_duration"] >= 0


# ============================================================================
# GPUProfiler Tests
# ============================================================================


class TestGPUProfiler:
    """Tests for GPUProfiler."""

    def test_gpu_profiler_initialization(self):
        """Test GPUProfiler initialization."""
        profiler = GPUProfiler()
        # GPU may not be available in test environment
        assert isinstance(profiler.gpu_available, bool)

    def test_gpu_profiler_without_gpu(self):
        """Test GPU profiling without GPU available."""
        profiler = GPUProfiler()
        profiler.start()
        metrics = profiler.stop()
        # Should handle gracefully
        assert isinstance(metrics, dict)


# ============================================================================
# BottleneckIdentifier Tests
# ============================================================================


class TestBottleneckIdentifier:
    """Tests for BottleneckIdentifier."""

    def test_bottleneck_identifier_initialization(self):
        """Test BottleneckIdentifier initialization."""
        identifier = BottleneckIdentifier()
        assert 'cpu_percent' in identifier.thresholds
        assert 'memory_percent' in identifier.thresholds

    def test_bottleneck_identifier_custom_thresholds(self):
        """Test custom thresholds."""
        thresholds = {'cpu_percent': 50.0, 'memory_percent': 60.0}
        identifier = BottleneckIdentifier(thresholds=thresholds)
        assert identifier.thresholds['cpu_percent'] == 50.0

    def test_identify_cpu_bottleneck(self, sample_result):
        """Test identifying CPU bottlenecks."""
        identifier = BottleneckIdentifier(thresholds={'cpu_percent': 50.0})
        bottlenecks = identifier.identify(sample_result)

        cpu_bottlenecks = [b for b in bottlenecks if b.category == MetricType.CPU]
        assert len(cpu_bottlenecks) > 0
        assert cpu_bottlenecks[0].severity in [BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL]

    def test_identify_io_bottleneck(self, sample_result):
        """Test identifying I/O bottlenecks."""
        identifier = BottleneckIdentifier(thresholds={'io_wait': 0.1})
        bottlenecks = identifier.identify(sample_result)

        io_bottlenecks = [b for b in bottlenecks if b.category == MetricType.IO]
        assert len(io_bottlenecks) > 0

    def test_bottleneck_recommendations(self, sample_result):
        """Test that bottlenecks include recommendations."""
        identifier = BottleneckIdentifier()
        bottlenecks = identifier.identify(sample_result)

        for bottleneck in bottlenecks:
            assert len(bottleneck.recommendations) > 0


# ============================================================================
# RegressionDetector Tests
# ============================================================================


class TestRegressionDetector:
    """Tests for RegressionDetector."""

    def test_regression_detector_initialization(self):
        """Test RegressionDetector initialization."""
        detector = RegressionDetector()
        assert detector.regression_threshold == 10.0

    def test_regression_detector_custom_threshold(self):
        """Test custom regression threshold."""
        detector = RegressionDetector(regression_threshold=5.0)
        assert detector.regression_threshold == 5.0

    def test_detect_time_regression(self, sample_result):
        """Test detecting time regression."""
        detector = RegressionDetector(regression_threshold=10.0)

        baseline = sample_result
        current = ProfilingResult(
            session_id="current_123",
            name="current",
            config=ProfilingConfig(),
            time_metrics=TimeMetrics(
                wall_time=2.0,  # 33% slower
                cpu_time=1.5,
            ),
            memory_metrics=baseline.memory_metrics,
            cpu_metrics=baseline.cpu_metrics,
            io_metrics=baseline.io_metrics,
            network_metrics=baseline.network_metrics,
            database_metrics=baseline.database_metrics,
        )

        report = detector.compare(baseline, current)
        assert len(report.regressions) > 0
        assert any("time" in r.lower() for r in report.regressions)

    def test_detect_memory_regression(self, sample_result):
        """Test detecting memory regression."""
        detector = RegressionDetector(regression_threshold=10.0)

        baseline = sample_result
        current = ProfilingResult(
            session_id="current_123",
            name="current",
            config=ProfilingConfig(),
            time_metrics=baseline.time_metrics,
            memory_metrics=MemoryMetrics(
                rss=150 * 1024 * 1024,  # 50% more memory
                vms=baseline.memory_metrics.vms,
            ),
            cpu_metrics=baseline.cpu_metrics,
            io_metrics=baseline.io_metrics,
            network_metrics=baseline.network_metrics,
            database_metrics=baseline.database_metrics,
        )

        report = detector.compare(baseline, current)
        assert len(report.regressions) > 0
        assert any("memory" in r.lower() for r in report.regressions)

    def test_detect_improvements(self, sample_result):
        """Test detecting performance improvements."""
        detector = RegressionDetector(regression_threshold=10.0)

        baseline = sample_result
        current = ProfilingResult(
            session_id="current_123",
            name="current",
            config=ProfilingConfig(),
            time_metrics=TimeMetrics(
                wall_time=1.0,  # 33% faster
                cpu_time=0.8,
            ),
            memory_metrics=baseline.memory_metrics,
            cpu_metrics=baseline.cpu_metrics,
            io_metrics=baseline.io_metrics,
            network_metrics=baseline.network_metrics,
            database_metrics=baseline.database_metrics,
        )

        report = detector.compare(baseline, current)
        assert len(report.improvements) > 0


# ============================================================================
# OptimizationAdvisor Tests
# ============================================================================


class TestOptimizationAdvisor:
    """Tests for OptimizationAdvisor."""

    def test_optimization_advisor_initialization(self):
        """Test OptimizationAdvisor initialization."""
        advisor = OptimizationAdvisor()
        assert 'high_cpu' in advisor.recommendation_rules
        assert 'high_memory' in advisor.recommendation_rules

    def test_get_cpu_recommendations(self, sample_result):
        """Test getting CPU optimization recommendations."""
        # Add CPU bottleneck
        sample_result.bottlenecks.append(Bottleneck(
            id="cpu_test",
            severity=BottleneckSeverity.HIGH,
            category=MetricType.CPU,
            description="High CPU usage",
            location="test",
            impact=75.0,
            value=75.0,
            threshold=50.0,
        ))

        advisor = OptimizationAdvisor()
        recommendations = advisor.get_recommendations(sample_result)

        cpu_recs = [r for r in recommendations if r.category == MetricType.CPU]
        assert len(cpu_recs) > 0
        assert all(len(r.code_examples) > 0 for r in cpu_recs)

    def test_get_memory_recommendations(self, sample_result):
        """Test getting memory optimization recommendations."""
        sample_result.bottlenecks.append(Bottleneck(
            id="mem_test",
            severity=BottleneckSeverity.CRITICAL,
            category=MetricType.MEMORY,
            description="High memory usage",
            location="test",
            impact=85.0,
            value=85.0,
            threshold=70.0,
        ))

        advisor = OptimizationAdvisor()
        recommendations = advisor.get_recommendations(sample_result)

        mem_recs = [r for r in recommendations if r.category == MetricType.MEMORY]
        assert len(mem_recs) > 0

    def test_recommendations_have_references(self, sample_result):
        """Test that recommendations include references."""
        sample_result.bottlenecks.append(Bottleneck(
            id="io_test",
            severity=BottleneckSeverity.MEDIUM,
            category=MetricType.IO,
            description="High I/O wait",
            location="test",
            impact=50.0,
            value=1.0,
            threshold=0.5,
        ))

        advisor = OptimizationAdvisor()
        recommendations = advisor.get_recommendations(sample_result)

        for rec in recommendations:
            assert len(rec.references) > 0


# ============================================================================
# HotspotAnalyzer Tests
# ============================================================================


class TestHotspotAnalyzer:
    """Tests for HotspotAnalyzer."""

    def test_hotspot_analyzer_initialization(self):
        """Test HotspotAnalyzer initialization."""
        analyzer = HotspotAnalyzer()
        assert len(analyzer.function_timings) == 0

    def test_record_function(self):
        """Test recording function timings."""
        analyzer = HotspotAnalyzer()
        analyzer.record_function("func1", 0.5)
        analyzer.record_function("func1", 0.3)
        analyzer.record_function("func2", 1.0)

        assert len(analyzer.function_timings["func1"]) == 2
        assert len(analyzer.function_timings["func2"]) == 1

    def test_get_hotspots(self):
        """Test getting hottest code paths."""
        analyzer = HotspotAnalyzer()

        # Simulate function calls
        analyzer.record_function("slow_func", 2.0)
        analyzer.record_function("slow_func", 1.8)
        analyzer.record_function("fast_func", 0.1)
        analyzer.record_function("fast_func", 0.15)
        analyzer.record_function("medium_func", 0.5)

        hotspots = analyzer.get_hotspots(top_n=3)
        assert len(hotspots) == 3
        assert hotspots[0]["function"] == "slow_func"
        assert hotspots[0]["total_time"] >= 3.8

    def test_hotspot_statistics(self):
        """Test hotspot statistics."""
        analyzer = HotspotAnalyzer()

        durations = [0.5, 0.3, 0.7, 0.4, 0.6]
        for d in durations:
            analyzer.record_function("test_func", d)

        hotspots = analyzer.get_hotspots()
        assert hotspots[0]["call_count"] == 5
        assert hotspots[0]["avg_time"] == pytest.approx(0.5, rel=0.1)


# ============================================================================
# ResourceLeakDetector Tests
# ============================================================================


class TestResourceLeakDetector:
    """Tests for ResourceLeakDetector."""

    def test_resource_leak_detector_initialization(self):
        """Test ResourceLeakDetector initialization."""
        detector = ResourceLeakDetector()
        assert len(detector.memory_snapshots) == 0
        assert detector.leak_threshold == 1.5

    def test_snapshot(self):
        """Test taking resource snapshots."""
        detector = ResourceLeakDetector()
        detector.snapshot()
        time.sleep(0.1)
        detector.snapshot()

        assert len(detector.memory_snapshots) >= 2

    def test_detect_memory_leak(self):
        """Test detecting memory leaks."""
        detector = ResourceLeakDetector()

        # Simulate growing memory usage
        base_memory = 100 * 1024 * 1024
        detector.memory_snapshots = [
            (time.time(), base_memory),
            (time.time() + 1, base_memory * 1.6),  # 60% growth
            (time.time() + 2, base_memory * 2.0),  # 100% growth
        ]

        leaks = detector.detect_memory_leaks()
        assert len(leaks) > 0
        assert leaks[0].leaked_size > 0

    def test_no_leak_detected_stable_memory(self):
        """Test no leak detected with stable memory."""
        detector = ResourceLeakDetector()

        base_memory = 100 * 1024 * 1024
        detector.memory_snapshots = [
            (time.time(), base_memory),
            (time.time() + 1, base_memory * 1.05),
            (time.time() + 2, base_memory * 1.1),
        ]

        leaks = detector.detect_memory_leaks()
        assert len(leaks) == 0


# ============================================================================
# Report Generation Tests
# ============================================================================


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_report_generator_initialization(self):
        """Test ReportGenerator initialization."""
        generator = ReportGenerator()
        assert generator is not None

    def test_generate_json(self, sample_result):
        """Test JSON report generation."""
        generator = ReportGenerator()
        json_report = generator.generate_json(sample_result)

        assert isinstance(json_report, str)
        data = json.loads(json_report)
        assert data["session_id"] == sample_result.session_id
        assert data["name"] == sample_result.name

    def test_generate_html(self, sample_result):
        """Test HTML report generation."""
        generator = ReportGenerator()
        html_report = generator.generate_html(sample_result)

        assert isinstance(html_report, str)
        assert "<!DOCTYPE html>" in html_report
        assert sample_result.name in html_report
        assert sample_result.session_id in html_report

    def test_generate_csv(self, sample_result):
        """Test CSV report generation."""
        generator = ReportGenerator()
        csv_report = generator.generate_csv(sample_result)

        assert isinstance(csv_report, str)
        lines = csv_report.split("\n")
        assert len(lines) > 5
        assert "Metric,Value" in lines[0]


# ============================================================================
# Data Store Tests
# ============================================================================


class TestProfilingDataStore:
    """Tests for ProfilingDataStore."""

    def test_data_store_initialization(self, temp_dir):
        """Test ProfilingDataStore initialization."""
        store = ProfilingDataStore(storage_path=temp_dir)
        assert store.storage_path == temp_dir

    def test_save_result(self, temp_dir, sample_result):
        """Test saving profiling result."""
        store = ProfilingDataStore(storage_path=temp_dir)
        filepath = store.save(sample_result)

        assert filepath.exists()
        assert filepath.name == f"{sample_result.session_id}.json"

    def test_list_sessions(self, temp_dir, sample_result):
        """Test listing stored sessions."""
        store = ProfilingDataStore(storage_path=temp_dir)
        store.save(sample_result)

        sessions = store.list_sessions()
        assert sample_result.session_id in sessions


# ============================================================================
# Metrics Exporter Tests
# ============================================================================


class TestMetricsExporter:
    """Tests for MetricsExporter."""

    def test_metrics_exporter_initialization(self):
        """Test MetricsExporter initialization."""
        exporter = MetricsExporter()
        assert 'prometheus' in exporter.exporters
        assert 'grafana' in exporter.exporters
        assert 'datadog' in exporter.exporters

    def test_export_prometheus(self, sample_result):
        """Test Prometheus export."""
        exporter = MetricsExporter()
        output = exporter.export(sample_result, format="prometheus")

        assert isinstance(output, str)
        assert "profiling_wall_time" in output
        assert "profiling_memory_rss" in output
        assert sample_result.session_id in output

    def test_export_grafana(self, sample_result):
        """Test Grafana export."""
        exporter = MetricsExporter()
        output = exporter.export(sample_result, format="grafana")

        assert isinstance(output, str)
        data = json.loads(output)
        assert "dashboard" in data

    def test_export_datadog(self, sample_result):
        """Test DataDog export."""
        exporter = MetricsExporter()
        output = exporter.export(sample_result, format="datadog")

        assert isinstance(output, str)
        data = json.loads(output)
        assert "series" in data


# ============================================================================
# PerformanceProfilerFSA Main Class Tests
# ============================================================================


class TestPerformanceProfilerFSA:
    """Tests for main PerformanceProfilerFSA class."""

    def test_profiler_initialization(self, profiler):
        """Test profiler initialization."""
        assert len(profiler.sessions) == 0
        assert profiler.data_store is not None
        assert profiler.metrics_exporter is not None

    def test_start_profiling(self, profiler):
        """Test starting a profiling session."""
        session_id = profiler.start_profiling()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert session_id in profiler.sessions

    def test_start_profiling_with_config(self, profiler, config):
        """Test starting profiling with custom config."""
        session_id = profiler.start_profiling(config)
        assert session_id in profiler.sessions
        assert profiler.sessions[session_id]['config'] == config

    def test_stop_profiling(self, profiler):
        """Test stopping a profiling session."""
        session_id = profiler.start_profiling()
        time.sleep(0.1)
        result = profiler.stop_profiling(session_id)

        assert isinstance(result, ProfilingResult)
        assert result.session_id == session_id
        assert result.time_metrics.wall_time >= 0.1
        assert session_id not in profiler.sessions

    def test_stop_unknown_session(self, profiler):
        """Test stopping unknown session raises error."""
        with pytest.raises(ValueError):
            profiler.stop_profiling("unknown_session_id")

    def test_profile_function(self, profiler):
        """Test profiling a function."""
        def test_func(n):
            return sum(range(n))

        result, profile_result = profiler.profile_function(test_func, 10000)

        assert result == sum(range(10000))
        assert isinstance(profile_result, ProfilingResult)
        assert profile_result.time_metrics.wall_time > 0

    def test_profile_function_with_exception(self, profiler):
        """Test profiling a function that raises exception."""
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            profiler.profile_function(failing_func)

    @pytest.mark.asyncio
    async def test_profile_async(self, profiler):
        """Test profiling async coroutine."""
        async def async_func():
            await asyncio.sleep(0.1)
            return "done"

        result, profile_result = await profiler.profile_async(async_func())

        assert result == "done"
        assert isinstance(profile_result, ProfilingResult)
        assert profile_result.time_metrics.wall_time >= 0.1

    def test_profile_context_manager(self, profiler):
        """Test profiling with context manager."""
        with profiler.profile("test_context") as session_id:
            time.sleep(0.1)
            assert session_id in profiler.sessions

        # Session should be cleaned up after context
        assert session_id not in profiler.sessions

    def test_profile_decorator(self, profiler):
        """Test profiling decorator."""
        @profiler.profile_decorator(name="decorated_func")
        def decorated_func(n):
            return sum(range(n))

        result = decorated_func(1000)
        assert result == sum(range(1000))

    @pytest.mark.asyncio
    async def test_profile_decorator_async(self, profiler):
        """Test profiling decorator on async function."""
        @profiler.profile_decorator(name="async_decorated")
        async def async_decorated():
            await asyncio.sleep(0.05)
            return "async_done"

        result = await async_decorated()
        assert result == "async_done"

    def test_analyze_bottlenecks(self, profiler, sample_result):
        """Test analyzing bottlenecks."""
        bottlenecks = profiler.analyze_bottlenecks(sample_result)
        assert isinstance(bottlenecks, list)

    def test_compare_profiles(self, profiler, sample_result):
        """Test comparing two profiles."""
        baseline = sample_result
        current = ProfilingResult(
            session_id="current_123",
            name="current",
            config=ProfilingConfig(),
            time_metrics=TimeMetrics(wall_time=2.0, cpu_time=1.5),
            memory_metrics=baseline.memory_metrics,
            cpu_metrics=baseline.cpu_metrics,
            io_metrics=baseline.io_metrics,
            network_metrics=baseline.network_metrics,
            database_metrics=baseline.database_metrics,
        )

        report = profiler.compare_profiles(baseline, current)
        assert isinstance(report, ComparisonReport)
        assert report.baseline_id == baseline.session_id
        assert report.current_id == current.session_id

    def test_get_optimization_recommendations(self, profiler, sample_result):
        """Test getting optimization recommendations."""
        # Add a bottleneck
        sample_result.bottlenecks.append(Bottleneck(
            id="test_bottleneck",
            severity=BottleneckSeverity.HIGH,
            category=MetricType.CPU,
            description="High CPU",
            location="test",
            impact=80.0,
            value=80.0,
            threshold=50.0,
        ))

        recommendations = profiler.get_optimization_recommendations(sample_result)
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_export_metrics_json(self, profiler, sample_result):
        """Test exporting metrics as JSON."""
        output = profiler.export_metrics(sample_result, format="json")
        assert isinstance(output, str)
        data = json.loads(output)
        assert data["session_id"] == sample_result.session_id

    def test_export_metrics_html(self, profiler, sample_result):
        """Test exporting metrics as HTML."""
        output = profiler.export_metrics(sample_result, format="html")
        assert isinstance(output, str)
        assert "<!DOCTYPE html>" in output

    def test_export_metrics_csv(self, profiler, sample_result):
        """Test exporting metrics as CSV."""
        output = profiler.export_metrics(sample_result, format="csv")
        assert isinstance(output, str)
        assert "Metric,Value" in output

    def test_export_metrics_prometheus(self, profiler, sample_result):
        """Test exporting metrics to Prometheus."""
        output = profiler.export_metrics(sample_result, format="prometheus")
        assert isinstance(output, str)
        assert "profiling_wall_time" in output


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_profiling_workflow(self, profiler):
        """Test complete profiling workflow."""
        # Start profiling
        config = ProfilingConfig(
            track_time=True,
            track_memory=True,
            track_cpu=True,
            track_io=True,
        )
        session_id = profiler.start_profiling(config)

        # Simulate workload
        data = []
        for i in range(10000):
            data.append(i * i)

        time.sleep(0.1)

        # Stop profiling
        result = profiler.stop_profiling(session_id, name="integration_test")

        # Verify result
        assert result.time_metrics.wall_time > 0
        assert result.memory_metrics.rss > 0
        assert result.cpu_metrics.num_threads > 0

        # Analyze bottlenecks
        bottlenecks = profiler.analyze_bottlenecks(result)
        assert isinstance(bottlenecks, list)

        # Get recommendations
        recommendations = profiler.get_optimization_recommendations(result)
        assert isinstance(recommendations, list)

        # Export metrics
        json_export = profiler.export_metrics(result, format="json")
        assert isinstance(json_export, str)

    def test_baseline_comparison_workflow(self, profiler):
        """Test baseline comparison workflow."""
        # Create baseline
        session_id = profiler.start_profiling()
        time.sleep(0.1)
        baseline = profiler.stop_profiling(session_id, name="baseline")

        # Create current profile
        session_id = profiler.start_profiling()
        time.sleep(0.15)
        current = profiler.stop_profiling(session_id, name="current")

        # Compare
        report = profiler.compare_profiles(baseline, current)

        assert isinstance(report, ComparisonReport)
        assert report.time_delta != 0

    def test_memory_leak_detection_workflow(self, profiler):
        """Test memory leak detection workflow."""
        results = []

        # Simulate multiple profiling sessions with growing memory
        for i in range(3):
            session_id = profiler.start_profiling()
            # Simulate memory growth
            _ = [0] * (10000 * (i + 1))
            time.sleep(0.05)
            result = profiler.stop_profiling(session_id, name=f"session_{i}")
            results.append(result)

        # Detect leaks
        leaks = profiler.detect_memory_leaks(results)
        assert isinstance(leaks, list)

    def test_concurrent_profiling_sessions(self, profiler):
        """Test multiple concurrent profiling sessions."""
        session1 = profiler.start_profiling()
        session2 = profiler.start_profiling()

        time.sleep(0.1)

        result1 = profiler.stop_profiling(session1, name="session1")
        result2 = profiler.stop_profiling(session2, name="session2")

        assert result1.session_id != result2.session_id
        assert result1.time_metrics.wall_time >= 0.1
        assert result2.time_metrics.wall_time >= 0.1


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance tests for the profiler itself."""

    def test_profiler_overhead(self, profiler):
        """Test profiler overhead is minimal."""
        # Time without profiling
        start = time.perf_counter()
        _ = sum(range(10000))
        baseline_time = time.perf_counter() - start

        # Time with profiling
        session_id = profiler.start_profiling()
        start = time.perf_counter()
        _ = sum(range(10000))
        profiled_time = time.perf_counter() - start
        profiler.stop_profiling(session_id)

        # Overhead should be less than 50%
        overhead = (profiled_time - baseline_time) / baseline_time
        assert overhead < 0.5

    def test_rapid_session_creation(self, profiler):
        """Test rapid session creation and cleanup."""
        session_ids = []

        # Create many sessions rapidly
        for _ in range(100):
            session_id = profiler.start_profiling()
            session_ids.append(session_id)

        # Clean them up
        for session_id in session_ids:
            profiler.stop_profiling(session_id)

        assert len(profiler.sessions) == 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_profiling_session(self, profiler):
        """Test profiling session with no activity."""
        session_id = profiler.start_profiling()
        result = profiler.stop_profiling(session_id)

        assert result.time_metrics.wall_time >= 0
        assert isinstance(result, ProfilingResult)

    def test_profiling_with_disabled_trackers(self, profiler):
        """Test profiling with all trackers disabled."""
        config = ProfilingConfig(
            track_time=False,
            track_memory=False,
            track_cpu=False,
            track_io=False,
        )

        session_id = profiler.start_profiling(config)
        result = profiler.stop_profiling(session_id)

        assert isinstance(result, ProfilingResult)

    def test_comparison_with_zero_baseline(self, profiler):
        """Test comparison when baseline has zero values."""
        baseline = ProfilingResult(
            session_id="baseline",
            name="baseline",
            config=ProfilingConfig(),
            time_metrics=TimeMetrics(wall_time=0.0, cpu_time=0.0),
            memory_metrics=MemoryMetrics(),
            cpu_metrics=CPUMetrics(),
            io_metrics=IOMetrics(),
            network_metrics=NetworkMetrics(),
            database_metrics=DatabaseMetrics(),
        )

        current = ProfilingResult(
            session_id="current",
            name="current",
            config=ProfilingConfig(),
            time_metrics=TimeMetrics(wall_time=1.0, cpu_time=0.5),
            memory_metrics=MemoryMetrics(),
            cpu_metrics=CPUMetrics(),
            io_metrics=IOMetrics(),
            network_metrics=NetworkMetrics(),
            database_metrics=DatabaseMetrics(),
        )

        report = profiler.compare_profiles(baseline, current)
        assert isinstance(report, ComparisonReport)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

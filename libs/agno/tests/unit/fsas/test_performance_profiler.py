"""
Comprehensive tests for Performance Profiler FSA

Tests cover profiling execution, memory tracking, CPU profiling, bottleneck detection,
statistical analysis, and report generation.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from agno.fsas.performance_profiler import (
    AnalysisReport,
    Bottleneck,
    CascadeProfile,
    ComparisonReport,
    CPUProfile,
    MemoryProfile,
    PerformanceProfilerError,
    PerformanceProfilerFSA,
    ProfileReport,
    ProfileResult,
    ProfileType,
    ProfilingSeverity,
)


@pytest.fixture
def profiler():
    """Create Performance Profiler FSA instance"""
    return PerformanceProfilerFSA()


@pytest.fixture
def sample_function():
    """Sample function to profile"""
    def compute_fibonacci(n):
        """Calculate fibonacci number"""
        if n <= 1:
            return n
        return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)
    return compute_fibonacci


@pytest.fixture
def memory_intensive_function():
    """Function that allocates memory"""
    def allocate_memory():
        """Allocate some memory"""
        data = [i * 2 for i in range(10000)]
        return sum(data)
    return allocate_memory


@pytest.fixture
def sample_profile_results():
    """Create sample profile results"""
    return [
        ProfileResult(
            execution_time=0.1,
            memory_used=10.0,
            cpu_percent=50.0,
            call_count=1
        ),
        ProfileResult(
            execution_time=0.15,
            memory_used=12.0,
            cpu_percent=55.0,
            call_count=1
        ),
        ProfileResult(
            execution_time=0.2,
            memory_used=15.0,
            cpu_percent=60.0,
            call_count=1
        ),
        ProfileResult(
            execution_time=0.12,
            memory_used=11.0,
            cpu_percent=52.0,
            call_count=1
        ),
        ProfileResult(
            execution_time=0.18,
            memory_used=14.0,
            cpu_percent=58.0,
            call_count=1
        ),
    ]


class TestPerformanceProfilerInitialization:
    """Test Performance Profiler FSA initialization"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        profiler = PerformanceProfilerFSA()
        assert profiler is not None
        assert profiler.name == "PerformanceProfilerFSA"
        assert profiler.enable_memory_tracking is True
        assert profiler.enable_cpu_profiling is True

    def test_init_with_config(self):
        """Test initialization with custom configuration"""
        config = {
            "enable_memory_tracking": False,
            "enable_cpu_profiling": True,
            "profiling_overhead_limit": 0.1,
            "sampling_interval": 0.002
        }
        profiler = PerformanceProfilerFSA(config=config)
        assert profiler.enable_memory_tracking is False
        assert profiler.enable_cpu_profiling is True
        assert profiler.profiling_overhead_limit == 0.1
        assert profiler.sampling_interval == 0.002

    def test_thresholds_initialized(self, profiler):
        """Test that performance thresholds are initialized"""
        assert 'p95_execution_time' in profiler.thresholds
        assert 'p99_execution_time' in profiler.thresholds
        assert 'max_memory_mb' in profiler.thresholds
        assert 'max_cpu_percent' in profiler.thresholds


class TestProfileExecution:
    """Test profile_execution method"""

    def test_profile_simple_function(self, profiler, sample_function):
        """Test profiling a simple function"""
        result = profiler.profile_execution(sample_function, 10)

        assert isinstance(result, ProfileResult)
        assert result.execution_time > 0
        assert result.call_count == 1
        assert 'function_name' in result.metadata

    def test_profile_with_args_kwargs(self, profiler):
        """Test profiling with arguments and keyword arguments"""
        def test_func(a, b, c=3):
            return a + b + c

        result = profiler.profile_execution(test_func, 1, 2, c=5)
        assert isinstance(result, ProfileResult)
        assert result.execution_time > 0

    def test_profile_memory_tracking(self, profiler, memory_intensive_function):
        """Test that memory tracking works"""
        result = profiler.profile_execution(
            memory_intensive_function,
            profile_type=ProfileType.MEMORY
        )

        assert isinstance(result, ProfileResult)
        assert result.memory_used >= 0

    def test_profile_cpu_tracking(self, profiler, sample_function):
        """Test CPU profiling"""
        result = profiler.profile_execution(
            sample_function,
            10,
            profile_type=ProfileType.CPU
        )

        assert isinstance(result, ProfileResult)
        assert result.cpu_percent >= 0

    def test_profile_function_with_exception(self, profiler):
        """Test profiling function that raises exception"""
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            profiler.profile_execution(failing_function)


class TestProfilingSession:
    """Test profiling session management"""

    def test_start_stop_session(self, profiler):
        """Test starting and stopping a profiling session"""
        session_id = "test_session"

        # Start session
        profiler.start_profiling(session_id)
        assert session_id in profiler._sessions

        # Stop session
        report = profiler.stop_profiling(session_id)
        assert isinstance(report, ProfileReport)
        assert report.session_id == session_id
        assert session_id not in profiler._sessions

    def test_start_duplicate_session(self, profiler):
        """Test that starting duplicate session raises error"""
        session_id = "duplicate_session"

        profiler.start_profiling(session_id)

        with pytest.raises(PerformanceProfilerError, match="already exists"):
            profiler.start_profiling(session_id)

        # Cleanup
        profiler.stop_profiling(session_id)

    def test_stop_nonexistent_session(self, profiler):
        """Test that stopping nonexistent session raises error"""
        with pytest.raises(PerformanceProfilerError, match="not found"):
            profiler.stop_profiling("nonexistent_session")

    def test_session_context_manager(self, profiler):
        """Test session context manager"""
        with profiler.session() as session_id:
            assert session_id in profiler._sessions

        # Session should be stopped after context exit
        assert session_id not in profiler._sessions
        assert 'last_report' in profiler.state

    def test_session_with_custom_id(self, profiler):
        """Test session context manager with custom ID"""
        custom_id = "my_custom_session"

        with profiler.session(custom_id) as session_id:
            assert session_id == custom_id


class TestMemoryProfiling:
    """Test memory profiling functionality"""

    def test_profile_memory_basic(self, profiler, memory_intensive_function):
        """Test basic memory profiling"""
        memory_profile = profiler.profile_memory(memory_intensive_function)

        assert isinstance(memory_profile, MemoryProfile)
        assert memory_profile.peak_memory >= 0
        assert memory_profile.current_memory >= 0
        assert memory_profile.allocations >= 0

    def test_profile_memory_with_args(self, profiler):
        """Test memory profiling with arguments"""
        def allocate_list(size):
            return [0] * size

        memory_profile = profiler.profile_memory(allocate_list, 10000)

        assert isinstance(memory_profile, MemoryProfile)
        assert memory_profile.peak_memory > 0

    def test_profile_memory_leaks_detected(self, profiler):
        """Test that potential memory leaks are detected"""
        def create_large_object():
            large_list = [0] * 100000
            return sum(large_list)

        memory_profile = profiler.profile_memory(create_large_object)

        assert isinstance(memory_profile.leaks, list)
        # Should have some allocation information
        assert memory_profile.allocations > 0


class TestCPUProfiling:
    """Test CPU profiling functionality"""

    def test_profile_cpu_basic(self, profiler, sample_function):
        """Test basic CPU profiling"""
        cpu_profile = profiler.profile_cpu(sample_function, 12)

        assert isinstance(cpu_profile, CPUProfile)
        assert cpu_profile.total_cpu_time > 0
        assert cpu_profile.function_calls > 0
        assert len(cpu_profile.hotspots) > 0

    def test_profile_cpu_hotspots(self, profiler):
        """Test that CPU hotspots are identified"""
        def cpu_intensive():
            total = 0
            for i in range(10000):
                total += i ** 2
            return total

        cpu_profile = profiler.profile_cpu(cpu_intensive)

        assert len(cpu_profile.hotspots) > 0
        # Check hotspot structure
        for hotspot in cpu_profile.hotspots:
            assert 'function' in hotspot
            assert 'call_count' in hotspot
            assert 'total_time' in hotspot


class TestStatisticalAnalysis:
    """Test statistical analysis functionality"""

    def test_analyze_performance_basic(self, profiler, sample_profile_results):
        """Test basic performance analysis"""
        analysis = profiler.analyze_performance(sample_profile_results)

        assert isinstance(analysis, AnalysisReport)
        assert 'execution_time' in analysis.summary_stats
        assert 'memory' in analysis.summary_stats
        assert 'cpu' in analysis.summary_stats

    def test_analyze_performance_statistics(self, profiler, sample_profile_results):
        """Test that all statistics are calculated"""
        analysis = profiler.analyze_performance(sample_profile_results)

        exec_stats = analysis.summary_stats['execution_time']
        assert 'mean' in exec_stats
        assert 'median' in exec_stats
        assert 'min' in exec_stats
        assert 'max' in exec_stats
        assert 'p95' in exec_stats
        assert 'p99' in exec_stats
        assert 'stddev' in exec_stats

    def test_analyze_performance_empty_results(self, profiler):
        """Test analysis with empty results"""
        analysis = profiler.analyze_performance([])

        assert isinstance(analysis, AnalysisReport)
        assert analysis.performance_score == 0.0
        assert len(analysis.recommendations) > 0

    def test_performance_score_calculation(self, profiler, sample_profile_results):
        """Test that performance score is calculated"""
        analysis = profiler.analyze_performance(sample_profile_results)

        assert 0 <= analysis.performance_score <= 100

    def test_anomaly_detection(self, profiler):
        """Test anomaly detection in results"""
        # Create results with an outlier
        results = [
            ProfileResult(execution_time=0.1, memory_used=10, cpu_percent=50, call_count=1),
            ProfileResult(execution_time=0.12, memory_used=12, cpu_percent=52, call_count=1),
            ProfileResult(execution_time=0.11, memory_used=11, cpu_percent=51, call_count=1),
            ProfileResult(execution_time=5.0, memory_used=100, cpu_percent=90, call_count=1),  # Outlier
        ]

        analysis = profiler.analyze_performance(results)

        # Should detect the outlier
        assert len(analysis.anomalies) > 0


class TestBottleneckDetection:
    """Test bottleneck detection functionality"""

    def test_detect_bottlenecks_basic(self, profiler, sample_profile_results):
        """Test basic bottleneck detection"""
        from datetime import datetime
        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        bottlenecks = profiler.detect_bottlenecks(report)

        assert isinstance(bottlenecks, list)
        for bottleneck in bottlenecks:
            assert isinstance(bottleneck, Bottleneck)
            assert bottleneck.location
            assert bottleneck.severity
            assert bottleneck.recommendation

    def test_detect_memory_bottleneck(self, profiler):
        """Test detection of memory bottlenecks"""
        from datetime import datetime
        # Create results that exceed memory threshold
        results = [
            ProfileResult(
                execution_time=0.1,
                memory_used=600,  # Exceeds default threshold of 500MB
                cpu_percent=50,
                call_count=1
            )
        ]

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=results
        )

        bottlenecks = profiler.detect_bottlenecks(report)

        # Should detect memory bottleneck
        memory_bottlenecks = [b for b in bottlenecks if 'memory' in b.location.lower()]
        assert len(memory_bottlenecks) > 0

    def test_detect_bottleneck_severity(self, profiler):
        """Test bottleneck severity classification"""
        from datetime import datetime
        # Create results with varying execution times
        results = [
            ProfileResult(execution_time=0.1, memory_used=10, cpu_percent=50, call_count=1),
            ProfileResult(execution_time=0.2, memory_used=10, cpu_percent=50, call_count=1),
            ProfileResult(execution_time=1.5, memory_used=10, cpu_percent=50, call_count=1),  # Slow
        ]

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=2.0,
            results=results
        )

        bottlenecks = profiler.detect_bottlenecks(report)

        # Should have severity levels
        if bottlenecks:
            assert bottlenecks[0].severity in [
                ProfilingSeverity.CRITICAL,
                ProfilingSeverity.HIGH,
                ProfilingSeverity.MEDIUM,
                ProfilingSeverity.LOW
            ]


class TestProfileComparison:
    """Test profile comparison and regression detection"""

    def test_compare_profiles_basic(self, profiler, sample_profile_results):
        """Test basic profile comparison"""
        from datetime import datetime

        # Create baseline report
        baseline = ProfileReport(
            session_id="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results[:3]
        )

        # Create current report with slightly different metrics
        current_results = [
            ProfileResult(
                execution_time=r.execution_time * 1.2,  # 20% slower
                memory_used=r.memory_used * 1.1,  # 10% more memory
                cpu_percent=r.cpu_percent,
                call_count=r.call_count
            )
            for r in sample_profile_results[:3]
        ]

        current = ProfileReport(
            session_id="current",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.2,
            results=current_results
        )

        comparison = profiler.compare_profiles(baseline, current)

        assert isinstance(comparison, ComparisonReport)
        assert comparison.baseline_session == "baseline"
        assert comparison.current_session == "current"

    def test_compare_profiles_regression_detection(self, profiler, sample_profile_results):
        """Test regression detection in profile comparison"""
        from datetime import datetime

        baseline = ProfileReport(
            session_id="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        # Create significantly slower results
        slower_results = [
            ProfileResult(
                execution_time=r.execution_time * 1.5,  # 50% slower
                memory_used=r.memory_used,
                cpu_percent=r.cpu_percent,
                call_count=r.call_count
            )
            for r in sample_profile_results
        ]

        current = ProfileReport(
            session_id="current",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.5,
            results=slower_results
        )

        comparison = profiler.compare_profiles(baseline, current)

        # Should detect regression
        assert len(comparison.regressions) > 0

    def test_compare_profiles_improvements(self, profiler, sample_profile_results):
        """Test improvement detection in profile comparison"""
        from datetime import datetime

        baseline = ProfileReport(
            session_id="baseline",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        # Create faster results
        faster_results = [
            ProfileResult(
                execution_time=r.execution_time * 0.7,  # 30% faster
                memory_used=r.memory_used,
                cpu_percent=r.cpu_percent,
                call_count=r.call_count
            )
            for r in sample_profile_results
        ]

        current = ProfileReport(
            session_id="current",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=0.7,
            results=faster_results
        )

        comparison = profiler.compare_profiles(baseline, current)

        # Should detect improvements
        assert len(comparison.improvements) > 0


class TestRecommendations:
    """Test optimization recommendation generation"""

    def test_generate_recommendations_basic(self, profiler):
        """Test basic recommendation generation"""
        stats = {
            'execution_time': {
                'mean': 0.1,
                'p95': 0.3,
                'stddev': 0.05
            },
            'memory': {
                'mean': 50,
                'max': 100
            },
            'cpu': {
                'mean': 60,
                'max': 70
            }
        }

        recommendations = profiler.generate_recommendations(stats)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    def test_recommendations_for_slow_execution(self, profiler):
        """Test recommendations for slow execution"""
        stats = {
            'execution_time': {
                'mean': 2.0,
                'p95': 5.0,  # Exceeds threshold
                'stddev': 1.0
            },
            'memory': {'mean': 50, 'max': 100},
            'cpu': {'mean': 50, 'max': 60}
        }

        recommendations = profiler.generate_recommendations(stats)

        # Should recommend optimization for slow execution
        assert any('execution time' in r.lower() for r in recommendations)

    def test_recommendations_for_high_memory(self, profiler):
        """Test recommendations for high memory usage"""
        stats = {
            'execution_time': {'mean': 0.1, 'p95': 0.2, 'stddev': 0.05},
            'memory': {
                'mean': 400,
                'max': 600  # Exceeds threshold
            },
            'cpu': {'mean': 50, 'max': 60}
        }

        recommendations = profiler.generate_recommendations(stats)

        # Should recommend memory optimization
        assert any('memory' in r.lower() for r in recommendations)


class TestCascadeProfiling:
    """Test FSA cascade profiling"""

    def test_profile_cascade_basic(self, profiler):
        """Test basic cascade profiling"""
        def fsa1():
            time.sleep(0.01)
            return "fsa1"

        def fsa2():
            time.sleep(0.02)
            return "fsa2"

        def fsa3():
            time.sleep(0.015)
            return "fsa3"

        cascade_config = {
            'cascade_id': 'test_cascade',
            'fsas': [
                {'name': 'FSA1', 'function': fsa1},
                {'name': 'FSA2', 'function': fsa2},
                {'name': 'FSA3', 'function': fsa3}
            ]
        }

        cascade_profile = profiler.profile_fsa_cascade(cascade_config)

        assert isinstance(cascade_profile, CascadeProfile)
        assert cascade_profile.cascade_id == 'test_cascade'
        assert len(cascade_profile.fsa_profiles) == 3
        assert cascade_profile.total_execution_time > 0

    def test_cascade_critical_path(self, profiler):
        """Test critical path identification in cascade"""
        def fast_fsa():
            return "fast"

        def slow_fsa():
            time.sleep(0.05)
            return "slow"

        cascade_config = {
            'cascade_id': 'critical_path_test',
            'fsas': [
                {'name': 'FastFSA', 'function': fast_fsa},
                {'name': 'SlowFSA', 'function': slow_fsa}
            ]
        }

        cascade_profile = profiler.profile_fsa_cascade(cascade_config)

        # Critical path should contain the slow FSA
        assert 'SlowFSA' in cascade_profile.critical_path


class TestPerformanceValidation:
    """Test performance validation against thresholds"""

    def test_validate_performance_pass(self, profiler):
        """Test validation passes for good performance"""
        from datetime import datetime

        # Create results within thresholds
        results = [
            ProfileResult(
                execution_time=0.1,
                memory_used=50,
                cpu_percent=40,
                call_count=1
            )
            for _ in range(5)
        ]

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=0.5,
            results=results
        )

        assert profiler.validate_performance(report) is True

    def test_validate_performance_fail_execution_time(self, profiler):
        """Test validation fails for slow execution"""
        from datetime import datetime

        # Create results that exceed execution time threshold
        results = [
            ProfileResult(
                execution_time=2.0,  # Exceeds thresholds
                memory_used=50,
                cpu_percent=40,
                call_count=1
            )
            for _ in range(5)
        ]

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=10.0,
            results=results
        )

        assert profiler.validate_performance(report) is False

    def test_validate_performance_custom_thresholds(self, profiler):
        """Test validation with custom thresholds"""
        from datetime import datetime

        results = [
            ProfileResult(
                execution_time=0.3,
                memory_used=50,
                cpu_percent=40,
                call_count=1
            )
        ]

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=0.3,
            results=results
        )

        # Strict thresholds
        strict_thresholds = {
            'p95_execution_time': 0.2,
            'p99_execution_time': 0.3,
            'max_memory_mb': 100,
            'max_cpu_percent': 50
        }

        assert profiler.validate_performance(report, strict_thresholds) is False


class TestReportExport:
    """Test report export functionality"""

    def test_profile_report_to_dict(self, sample_profile_results):
        """Test ProfileReport serialization to dict"""
        from datetime import datetime

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert 'session_id' in report_dict
        assert 'start_time' in report_dict
        assert 'total_duration' in report_dict
        assert 'results' in report_dict

    def test_profile_report_to_json(self, sample_profile_results, tmp_path):
        """Test ProfileReport export to JSON"""
        from datetime import datetime

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        json_path = tmp_path / "report.json"
        json_str = report.to_json(str(json_path))

        assert json_path.exists()
        assert len(json_str) > 0

    def test_export_flamegraph(self, profiler, sample_profile_results, tmp_path):
        """Test flamegraph data export"""
        from datetime import datetime

        report = ProfileReport(
            session_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=1.0,
            results=sample_profile_results
        )

        output_path = tmp_path / "flamegraph.txt"
        success = profiler.export_flamegraph(report, str(output_path))

        assert success is True
        assert output_path.exists()


class TestErrorHandling:
    """Test error handling in Performance Profiler"""

    def test_validate_input_none(self, profiler):
        """Test validation rejects None input"""
        with pytest.raises(PerformanceProfilerError, match="cannot be None"):
            profiler.validate_input(None)

    def test_execute_invalid_task(self, profiler):
        """Test handling of invalid task"""
        with pytest.raises(PerformanceProfilerError, match="cannot be empty"):
            profiler.execute("")

    def test_cleanup_with_active_sessions(self, profiler):
        """Test cleanup handles active sessions gracefully"""
        profiler.start_profiling("session1")
        profiler.start_profiling("session2")

        # Cleanup should stop all sessions
        profiler.cleanup()

        assert len(profiler._sessions) == 0


class TestStatisticalHelpers:
    """Test statistical helper methods"""

    def test_mean_calculation(self, profiler):
        """Test mean calculation"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        mean = profiler._mean(values)
        assert mean == 3.0

    def test_median_calculation(self, profiler):
        """Test median calculation"""
        # Odd number of values
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        median = profiler._median(values)
        assert median == 3.0

        # Even number of values
        values = [1.0, 2.0, 3.0, 4.0]
        median = profiler._median(values)
        assert median == 2.5

    def test_percentile_calculation(self, profiler):
        """Test percentile calculation"""
        values = list(range(1, 101))  # 1 to 100
        p95 = profiler._percentile(values, 95)
        assert p95 >= 95

    def test_stddev_calculation(self, profiler):
        """Test standard deviation calculation"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stddev = profiler._stddev(values)
        assert stddev > 0

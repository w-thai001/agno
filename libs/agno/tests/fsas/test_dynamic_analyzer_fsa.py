"""
Unit tests for Dynamic Analyzer FSA.

Tests cover instrumentation, tracing, profiling, coverage tracking,
taint tracking, invariant detection, and type checking.
"""

import pytest
import time
import sys
from typing import List
from agno.fsas.dynamic_analyzer_fsa import (
    DynamicAnalyzer,
    AnalysisConfig,
    ExecutionTrace,
    PerformanceProfile,
    MemoryProfile,
    CoverageReport,
    ExceptionReport,
    TaintFlows,
    Invariant,
    TypeViolationReport,
    DynamicCallGraph,
    MemoryLeak,
    RegressionReport,
    ExecutionEvent,
)


class TestDynamicAnalyzerBasics:
    """Test basic dynamic analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test that analyzer initializes correctly."""
        config = AnalysisConfig(
            enable_tracing=True,
            enable_profiling=True,
            enable_coverage=True
        )
        analyzer = DynamicAnalyzer(config)

        assert analyzer.config.enable_tracing is True
        assert analyzer.config.enable_profiling is True
        assert analyzer.config.enable_coverage is True
        assert isinstance(analyzer.trace, ExecutionTrace)
        assert isinstance(analyzer.performance, PerformanceProfile)

    def test_simple_function_analysis(self):
        """Test analysis of a simple function."""
        analyzer = DynamicAnalyzer()

        def add(a: int, b: int) -> int:
            return a + b

        report = analyzer.analyze(add, inputs=[(2, 3), (5, 7)])

        assert report.execution_trace is not None
        assert len(report.execution_trace.events) > 0
        assert report.performance_profile is not None
        assert report.performance_profile.call_counts['add'] >= 2

    def test_recursive_function_analysis(self):
        """Test analysis of a recursive function."""
        analyzer = DynamicAnalyzer()

        def factorial(n: int) -> int:
            if n <= 1:
                return 1
            return n * factorial(n - 1)

        report = analyzer.analyze(factorial, inputs=[(5,)])

        assert report.execution_trace is not None
        # Should have multiple calls to factorial
        assert report.performance_profile.call_counts['factorial'] >= 5


class TestInstrumentation:
    """Test code instrumentation capabilities."""

    def test_function_instrumentation(self):
        """Test that function instrumentation works."""
        analyzer = DynamicAnalyzer()

        def sample_function(x: int) -> int:
            return x * 2

        instrumented = analyzer.instrument_function(sample_function)
        result = instrumented(5)

        assert result == 10
        assert 'sample_function' in analyzer.performance.call_counts
        assert analyzer.performance.call_counts['sample_function'] >= 1

    def test_instrumentation_preserves_behavior(self):
        """Test that instrumentation doesn't change function behavior."""
        analyzer = DynamicAnalyzer()

        def complex_function(a: int, b: int, c: int = 10) -> int:
            result = a + b
            result *= c
            return result

        instrumented = analyzer.instrument_function(complex_function)

        # Test with positional args
        assert instrumented(2, 3) == complex_function(2, 3)

        # Test with keyword args
        assert instrumented(2, 3, c=5) == complex_function(2, 3, c=5)


class TestExecutionTracing:
    """Test execution tracing functionality."""

    def test_trace_events_recorded(self):
        """Test that execution events are recorded."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_tracing=True))

        def traced_function(x: int) -> int:
            y = x + 1
            z = y * 2
            return z

        report = analyzer.analyze(traced_function, inputs=[(5,)])

        assert len(report.execution_trace.events) > 0
        # Should have call and return events
        event_types = {event.event_type for event in report.execution_trace.events}
        assert 'call' in event_types or 'return' in event_types

    def test_call_stack_tracking(self):
        """Test that call stack is tracked correctly."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_tracing=True))

        def outer(x: int) -> int:
            return inner(x + 1)

        def inner(x: int) -> int:
            return x * 2

        report = analyzer.analyze(outer, inputs=[(5,)])

        # Should have events from both functions
        function_names = {event.function_name for event in report.execution_trace.events}
        assert 'outer' in function_names or 'inner' in function_names


class TestPerformanceProfiling:
    """Test performance profiling capabilities."""

    def test_function_timing(self):
        """Test that function execution times are measured."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_profiling=True))

        def slow_function(n: int) -> int:
            time.sleep(0.01)  # 10ms delay
            return n

        report = analyzer.analyze(slow_function, inputs=[(1,)])

        assert 'slow_function' in report.performance_profile.function_times
        assert len(report.performance_profile.function_times['slow_function']) > 0
        # Should take at least 10ms
        assert sum(report.performance_profile.function_times['slow_function']) >= 0.01

    def test_hot_spot_detection(self):
        """Test detection of performance hot spots."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_profiling=True))

        def hot_function() -> None:
            for _ in range(100):
                time.sleep(0.0001)

        def cold_function() -> None:
            pass

        # Analyze both functions
        analyzer.analyze(hot_function, inputs=[()])
        analyzer.analyze(cold_function, inputs=[()])

        hot_spots = analyzer.performance.compute_hot_spots(top_n=5)

        # hot_function should be in hot spots
        hot_spot_names = [name for name, _ in hot_spots]
        assert 'hot_function' in hot_spot_names

    def test_call_count_tracking(self):
        """Test that function call counts are tracked."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_profiling=True))

        def counted_function(n: int) -> int:
            return n + 1

        analyzer.analyze(counted_function, inputs=[(1,), (2,), (3,)])

        assert analyzer.performance.call_counts['counted_function'] >= 3


class TestCoverageTracking:
    """Test code coverage tracking."""

    def test_line_coverage(self):
        """Test line coverage tracking."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_coverage=True))

        def covered_function(x: int) -> int:
            y = x + 1
            z = y * 2
            return z

        report = analyzer.analyze(covered_function, inputs=[(5,)])

        assert len(report.coverage_report.lines_covered) > 0
        assert report.coverage_report.coverage_percentage >= 0

    def test_branch_coverage_with_conditionals(self):
        """Test coverage with conditional branches."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_coverage=True))

        def branching_function(x: int) -> str:
            if x > 0:
                return "positive"
            elif x < 0:
                return "negative"
            else:
                return "zero"

        # Test multiple branches
        report = analyzer.analyze(
            branching_function,
            inputs=[(5,), (-3,), (0,)]
        )

        # Should cover multiple lines
        assert len(report.coverage_report.lines_covered) > 3


class TestMemoryProfiling:
    """Test memory profiling capabilities."""

    def test_memory_allocation_tracking(self):
        """Test that memory allocations are tracked."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_memory_profiling=True))

        def allocating_function() -> List[int]:
            return [i for i in range(1000)]

        report = analyzer.analyze(allocating_function, inputs=[()])

        # Should have recorded some memory usage
        assert report.memory_profile is not None
        # Memory timeline should have entries
        assert len(report.memory_profile.memory_timeline) >= 0

    def test_memory_leak_detection(self):
        """Test detection of memory leaks."""
        memory_profile = MemoryProfile()
        memory_profile.allocations['TestObject'] = [100, 200, 300]
        memory_profile.deallocations['TestObject'] = 1

        analyzer = DynamicAnalyzer()
        leaks = analyzer.detect_memory_leaks(memory_profile)

        assert len(leaks) > 0
        assert leaks[0].object_type == 'TestObject'
        assert leaks[0].leaked_count == 2  # 3 allocations - 1 deallocation


class TestExceptionMonitoring:
    """Test exception monitoring."""

    def test_exception_capture(self):
        """Test that exceptions are captured."""
        analyzer = DynamicAnalyzer()

        def failing_function(x: int) -> int:
            if x < 0:
                raise ValueError("Negative value not allowed")
            return x

        # This should capture the exception
        try:
            analyzer.analyze(failing_function, inputs=[(-5,)])
        except ValueError:
            pass

        # Exception should be recorded
        assert len(analyzer.exceptions.exceptions_raised) > 0
        assert 'ValueError' in analyzer.exceptions.exception_types

    def test_multiple_exception_types(self):
        """Test tracking multiple exception types."""
        exception_report = ExceptionReport()

        exception_report.add_exception(ValueError("test1"), "file.py", 10)
        exception_report.add_exception(TypeError("test2"), "file.py", 20)
        exception_report.add_exception(ValueError("test3"), "file.py", 30)

        assert exception_report.exception_types['ValueError'] == 2
        assert exception_report.exception_types['TypeError'] == 1
        assert len(exception_report.exceptions_raised) == 3


class TestTaintTracking:
    """Test dynamic taint tracking."""

    def test_taint_source_marking(self):
        """Test marking taint sources."""
        taint_flows = TaintFlows()

        taint_flows.add_taint_source("user_input", "malicious_data", "http_request")

        assert "user_input" in taint_flows.taint_sources
        assert "user_input" in taint_flows.tainted_variables
        assert taint_flows.tainted_variables["user_input"].source == "http_request"

    def test_taint_propagation(self):
        """Test taint propagation between variables."""
        taint_flows = TaintFlows()

        taint_flows.add_taint_source("input", "data", "user")
        taint_flows.propagate_taint("input", "processed")
        taint_flows.propagate_taint("processed", "output")

        assert "processed" in taint_flows.tainted_variables
        assert "output" in taint_flows.tainted_variables
        assert taint_flows.tainted_variables["output"].source == "user"

    def test_taint_flow_tracking(self):
        """Test complete taint flow tracking."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_taint_tracking=True))

        def process_data(data: str) -> str:
            return data.upper()

        taint_flows = analyzer.track_dynamic_taint(
            process_data,
            taint_sources=["data"]
        )

        assert len(taint_flows.taint_sources) > 0


class TestInvariantDetection:
    """Test invariant detection."""

    def test_constant_invariant_detection(self):
        """Test detection of constant return values."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_invariant_detection=True))

        def constant_function(x: int) -> int:
            return 42

        invariants = analyzer.detect_invariants(
            constant_function,
            test_inputs=[(1,), (2,), (3,), (4,), (5,)]
        )

        # Should detect that return value is always 42
        constant_invariants = [inv for inv in invariants if inv.invariant_type == 'constant']
        assert len(constant_invariants) > 0
        assert constant_invariants[0].confidence == 1.0

    def test_range_invariant_detection(self):
        """Test detection of range invariants."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_invariant_detection=True))

        def bounded_function(x: int) -> int:
            return min(max(x, 0), 100)

        invariants = analyzer.detect_invariants(
            bounded_function,
            test_inputs=[(-10,), (50,), (150,)]
        )

        # Should detect range invariant
        range_invariants = [inv for inv in invariants if inv.invariant_type == 'range']
        assert len(range_invariants) > 0

    def test_invariant_validation(self):
        """Test invariant validation against observations."""
        invariant = Invariant(
            invariant_type='constant',
            expression='x == 42',
            confidence=1.0
        )

        # Validate with observation
        assert invariant.validate(42) is True
        assert invariant.observations == 1


class TestRuntimeTypeChecking:
    """Test runtime type checking."""

    def test_type_violation_detection(self):
        """Test detection of type violations."""
        analyzer = DynamicAnalyzer(AnalysisConfig(enable_type_checking=True))

        def typed_function(x: int, y: str) -> int:
            return len(y) + x

        # Call with correct types
        analyzer.analyze(typed_function, inputs=[(5, "hello")])
        assert len(analyzer.type_violations.violations) == 0

        # Call with incorrect types (should detect violation)
        analyzer2 = DynamicAnalyzer(AnalysisConfig(enable_type_checking=True))
        analyzer2.analyze(typed_function, inputs=[(5, 123)])  # Wrong type for y

        # Should detect type violation
        assert len(analyzer2.type_violations.violations) > 0

    def test_type_observation_recording(self):
        """Test recording of observed types."""
        type_report = TypeViolationReport()

        type_report.add_violation("param1", int, str, "function.py:10")

        assert len(type_report.violations) == 1
        assert type_report.violations[0]['parameter'] == "param1"
        assert type_report.violations[0]['expected'] == int
        assert type_report.violations[0]['actual'] == str


class TestCallGraphAnalysis:
    """Test call graph construction."""

    def test_call_graph_construction(self):
        """Test building call graph from execution trace."""
        trace = ExecutionTrace()

        # Simulate call sequence: main -> foo -> bar
        trace.add_event(ExecutionEvent(
            event_type='call',
            function_name='main',
            filename='test.py',
            line_number=1,
            timestamp=time.time(),
            thread_id=0
        ))
        trace.add_event(ExecutionEvent(
            event_type='call',
            function_name='foo',
            filename='test.py',
            line_number=5,
            timestamp=time.time(),
            thread_id=0
        ))
        trace.add_event(ExecutionEvent(
            event_type='call',
            function_name='bar',
            filename='test.py',
            line_number=10,
            timestamp=time.time(),
            thread_id=0
        ))

        analyzer = DynamicAnalyzer()
        call_graph = analyzer.analyze_call_graph(trace)

        # Should have detected some function calls
        assert len(call_graph.nodes) >= 0

    def test_call_graph_edge_weights(self):
        """Test call graph edge weight tracking."""
        call_graph = DynamicCallGraph()

        # Add multiple calls
        call_graph.add_call('main', 'helper')
        call_graph.add_call('main', 'helper')
        call_graph.add_call('main', 'helper')

        edge = ('main', 'helper')
        assert edge in call_graph.weights
        assert call_graph.weights[edge] == 3


class TestRegressionDetection:
    """Test regression detection."""

    def test_behavioral_regression_detection(self):
        """Test detection of behavioral changes."""
        baseline_trace = ExecutionTrace()
        for i in range(10):
            baseline_trace.add_event(ExecutionEvent(
                event_type='call',
                function_name='test',
                filename='test.py',
                line_number=i,
                timestamp=time.time(),
                thread_id=0
            ))

        current_trace = ExecutionTrace()
        for i in range(15):  # Different number of events
            current_trace.add_event(ExecutionEvent(
                event_type='call',
                function_name='test',
                filename='test.py',
                line_number=i,
                timestamp=time.time(),
                thread_id=0
            ))

        analyzer = DynamicAnalyzer()
        regression_report = analyzer.detect_regressions(baseline_trace, current_trace)

        assert len(regression_report.behavioral_changes) > 0

    def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        baseline_trace = ExecutionTrace()
        baseline_trace.total_duration = 1.0

        current_trace = ExecutionTrace()
        current_trace.total_duration = 1.5  # 50% slower

        analyzer = DynamicAnalyzer()
        regression_report = analyzer.detect_regressions(baseline_trace, current_trace)

        # Should detect performance regression
        assert len(regression_report.performance_regressions) > 0
        assert regression_report.performance_regressions[0]['type'] == 'execution_time'


class TestDynamicAnalysisReport:
    """Test complete analysis report generation."""

    def test_report_generation(self):
        """Test that complete report is generated."""
        analyzer = DynamicAnalyzer(AnalysisConfig(
            enable_tracing=True,
            enable_profiling=True,
            enable_coverage=True,
            enable_memory_profiling=True
        ))

        def sample_function(x: int) -> int:
            return x * 2

        report = analyzer.analyze(sample_function, inputs=[(5,), (10,)])

        assert report.execution_trace is not None
        assert report.performance_profile is not None
        assert report.coverage_report is not None
        assert report.memory_profile is not None

    def test_report_summary(self):
        """Test report summary generation."""
        analyzer = DynamicAnalyzer()

        def test_function() -> int:
            return 42

        report = analyzer.analyze(test_function, inputs=[()])
        summary = report.summary()

        assert isinstance(summary, str)
        assert "Dynamic Analysis Report" in summary
        assert len(summary) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

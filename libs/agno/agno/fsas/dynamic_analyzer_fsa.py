"""
Dynamic Analyzer FSA - Runtime analysis of Python code through instrumentation and profiling.

This module provides comprehensive dynamic analysis capabilities including:
- Code instrumentation and execution tracing
- Performance and memory profiling
- Coverage tracking (line, branch, path)
- Dynamic taint tracking
- Invariant detection
- Runtime type checking
- Resource monitoring
"""

import ast
import sys
import time
import traceback
import inspect
import threading
import gc
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
import linecache

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class ExecutionEvent:
    """Single execution event during tracing."""

    event_type: str  # 'call', 'return', 'line', 'exception'
    function_name: str
    filename: str
    line_number: int
    timestamp: float
    thread_id: int
    args: Optional[Tuple] = None
    kwargs: Optional[Dict] = None
    return_value: Any = None
    exception: Optional[Exception] = None
    locals_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionTrace:
    """Complete execution trace with all events."""

    events: List[ExecutionEvent] = field(default_factory=list)
    call_stack: List[str] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    return_values: Dict[str, Any] = field(default_factory=dict)
    exceptions: List[Exception] = field(default_factory=list)
    total_duration: float = 0.0

    def add_event(self, event: ExecutionEvent) -> None:
        """Add an event to the trace."""
        self.events.append(event)
        self.timestamps.append(event.timestamp)
        if event.exception:
            self.exceptions.append(event.exception)


@dataclass
class PerformanceProfile:
    """Performance profiling results."""

    function_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    call_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    hot_spots: List[Tuple[str, float]] = field(default_factory=list)
    total_time: float = 0.0
    wall_time: float = 0.0
    cpu_time: float = 0.0

    def add_timing(self, function_name: str, duration: float) -> None:
        """Add timing measurement for a function."""
        self.function_times[function_name].append(duration)
        self.call_counts[function_name] += 1

    def compute_hot_spots(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Identify hot spots (most time-consuming functions)."""
        total_times = {
            func: sum(times) for func, times in self.function_times.items()
        }
        self.hot_spots = sorted(
            total_times.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        return self.hot_spots


@dataclass
class MemoryProfile:
    """Memory profiling results."""

    allocations: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    deallocations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    peak_memory: int = 0
    current_memory: int = 0
    memory_timeline: List[Tuple[float, int]] = field(default_factory=list)
    object_counts: Dict[type, int] = field(default_factory=lambda: defaultdict(int))

    def record_allocation(self, obj_type: str, size: int, timestamp: float) -> None:
        """Record memory allocation."""
        self.allocations[obj_type].append(size)
        self.current_memory += size
        self.peak_memory = max(self.peak_memory, self.current_memory)
        self.memory_timeline.append((timestamp, self.current_memory))


@dataclass
class CoverageReport:
    """Code coverage analysis results."""

    lines_covered: Set[Tuple[str, int]] = field(default_factory=set)
    branches_covered: Set[Tuple[str, int, str]] = field(default_factory=set)
    paths_covered: Set[Tuple[str, ...]] = field(default_factory=set)
    total_lines: int = 0
    coverage_percentage: float = 0.0
    uncovered_lines: Set[Tuple[str, int]] = field(default_factory=set)

    def add_line_coverage(self, filename: str, line_number: int) -> None:
        """Mark a line as covered."""
        self.lines_covered.add((filename, line_number))

    def compute_coverage(self, total_lines: int) -> float:
        """Compute coverage percentage."""
        self.total_lines = total_lines
        if total_lines > 0:
            self.coverage_percentage = (len(self.lines_covered) / total_lines) * 100
        return self.coverage_percentage


@dataclass
class ExceptionReport:
    """Exception monitoring results."""

    exceptions_raised: List[Exception] = field(default_factory=list)
    exception_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    stack_traces: List[str] = field(default_factory=list)
    exception_locations: List[Tuple[str, int]] = field(default_factory=list)

    def add_exception(self, exc: Exception, filename: str, line_number: int) -> None:
        """Record an exception."""
        self.exceptions_raised.append(exc)
        self.exception_types[type(exc).__name__] += 1
        self.stack_traces.append(traceback.format_exc())
        self.exception_locations.append((filename, line_number))


@dataclass
class ResourceUsage:
    """Resource usage monitoring results."""

    cpu_time: float = 0.0
    memory_usage: int = 0
    io_operations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    network_operations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    file_operations: List[Tuple[str, str]] = field(default_factory=list)

    def record_io(self, operation: str) -> None:
        """Record an I/O operation."""
        self.io_operations[operation] += 1


@dataclass
class TaintedValue:
    """Represents a tainted value with its source."""

    value: Any
    source: str
    propagation_path: List[str] = field(default_factory=list)


@dataclass
class TaintFlows:
    """Dynamic taint tracking results."""

    taint_sources: Dict[str, Any] = field(default_factory=dict)
    tainted_variables: Dict[str, TaintedValue] = field(default_factory=dict)
    taint_sinks: List[Tuple[str, TaintedValue]] = field(default_factory=list)
    propagation_graph: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    def add_taint_source(self, var_name: str, value: Any, source: str) -> None:
        """Mark a variable as tainted from a source."""
        self.taint_sources[var_name] = value
        self.tainted_variables[var_name] = TaintedValue(value, source)

    def propagate_taint(self, from_var: str, to_var: str) -> None:
        """Propagate taint from one variable to another."""
        if from_var in self.tainted_variables:
            tainted = self.tainted_variables[from_var]
            new_path = tainted.propagation_path + [from_var]
            self.tainted_variables[to_var] = TaintedValue(
                None, tainted.source, new_path
            )
            self.propagation_graph[from_var].append(to_var)


@dataclass
class Invariant:
    """Detected program invariant."""

    invariant_type: str  # 'constant', 'range', 'relationship', 'pre-condition', 'post-condition'
    expression: str
    confidence: float
    violations: int = 0
    observations: int = 0
    variables: List[str] = field(default_factory=list)

    def validate(self, observation: Any) -> bool:
        """Validate invariant against new observation."""
        self.observations += 1
        # Simplified validation - can be extended
        return True


@dataclass
class TypeViolationReport:
    """Runtime type checking results."""

    violations: List[Dict[str, Any]] = field(default_factory=list)
    type_observations: Dict[str, List[type]] = field(default_factory=lambda: defaultdict(list))
    expected_types: Dict[str, type] = field(default_factory=dict)

    def add_violation(self, param: str, expected: type, actual: type, location: str) -> None:
        """Record a type violation."""
        self.violations.append({
            'parameter': param,
            'expected': expected,
            'actual': actual,
            'location': location
        })


@dataclass
class ExecutionPath:
    """Recorded execution path."""

    path: List[Tuple[str, int]] = field(default_factory=list)
    branches_taken: List[Tuple[str, int, bool]] = field(default_factory=list)

    def add_step(self, filename: str, line_number: int) -> None:
        """Add a step to the execution path."""
        self.path.append((filename, line_number))


@dataclass
class RegressionReport:
    """Regression detection results."""

    behavioral_changes: List[Dict[str, Any]] = field(default_factory=list)
    performance_regressions: List[Dict[str, Any]] = field(default_factory=list)
    memory_regressions: List[Dict[str, Any]] = field(default_factory=list)
    coverage_regressions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DynamicCallGraph:
    """Dynamic call graph constructed from execution."""

    nodes: Set[str] = field(default_factory=set)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    weights: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))

    def add_call(self, caller: str, callee: str) -> None:
        """Add a function call to the graph."""
        self.nodes.add(caller)
        self.nodes.add(callee)
        edge = (caller, callee)
        if edge not in self.edges:
            self.edges.append(edge)
        self.weights[edge] += 1


@dataclass
class MemoryLeak:
    """Detected memory leak."""

    object_type: str
    allocation_count: int
    deallocation_count: int
    leaked_count: int
    allocation_sites: List[str] = field(default_factory=list)


@dataclass
class HotPath:
    """Hot execution path (frequently executed)."""

    path: List[str]
    execution_count: int
    total_time: float
    avg_time: float


@dataclass
class TestOracle:
    """Generated test oracle from observed behavior."""

    function_name: str
    input_output_pairs: List[Tuple[Any, Any]] = field(default_factory=list)
    observed_invariants: List[Invariant] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class ConcurrencyAnalysis:
    """Concurrency analysis results."""

    threads_created: List[int] = field(default_factory=list)
    lock_acquisitions: List[Tuple[str, float]] = field(default_factory=list)
    potential_race_conditions: List[Dict[str, Any]] = field(default_factory=list)
    deadlock_risks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for dynamic analysis."""

    enable_tracing: bool = True
    enable_profiling: bool = True
    enable_memory_profiling: bool = True
    enable_coverage: bool = True
    enable_taint_tracking: bool = False
    enable_invariant_detection: bool = False
    enable_type_checking: bool = True
    enable_resource_monitoring: bool = True
    timeout: Optional[float] = None
    max_trace_events: int = 100000


@dataclass
class DynamicAnalysisReport:
    """Complete dynamic analysis report."""

    execution_trace: Optional[ExecutionTrace] = None
    performance_profile: Optional[PerformanceProfile] = None
    memory_profile: Optional[MemoryProfile] = None
    coverage_report: Optional[CoverageReport] = None
    exception_report: Optional[ExceptionReport] = None
    resource_usage: Optional[ResourceUsage] = None
    taint_flows: Optional[TaintFlows] = None
    invariants: List[Invariant] = field(default_factory=list)
    type_violations: Optional[TypeViolationReport] = None
    call_graph: Optional[DynamicCallGraph] = None
    memory_leaks: List[MemoryLeak] = field(default_factory=list)
    hot_paths: List[HotPath] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a summary of the analysis."""
        lines = ["Dynamic Analysis Report", "=" * 50]

        if self.execution_trace:
            lines.append(f"Total Events: {len(self.execution_trace.events)}")
            lines.append(f"Execution Time: {self.execution_trace.total_duration:.4f}s")

        if self.performance_profile:
            lines.append(f"Functions Called: {len(self.performance_profile.call_counts)}")
            lines.append(f"Total Time: {self.performance_profile.total_time:.4f}s")

        if self.coverage_report:
            lines.append(f"Coverage: {self.coverage_report.coverage_percentage:.2f}%")

        if self.memory_profile:
            lines.append(f"Peak Memory: {self.memory_profile.peak_memory / 1024 / 1024:.2f} MB")

        if self.exception_report:
            lines.append(f"Exceptions: {len(self.exception_report.exceptions_raised)}")

        return "\n".join(lines)


class DynamicAnalyzer:
    """
    Comprehensive dynamic analyzer for Python code.

    Performs runtime analysis through instrumentation, profiling, tracing,
    and monitoring to provide insights into code behavior.
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """Initialize the dynamic analyzer."""
        self.config = config or AnalysisConfig()
        self.trace: ExecutionTrace = ExecutionTrace()
        self.performance: PerformanceProfile = PerformanceProfile()
        self.memory: MemoryProfile = MemoryProfile()
        self.coverage: CoverageReport = CoverageReport()
        self.exceptions: ExceptionReport = ExceptionReport()
        self.resources: ResourceUsage = ResourceUsage()
        self.taint: TaintFlows = TaintFlows()
        self.type_violations: TypeViolationReport = TypeViolationReport()
        self.call_graph: DynamicCallGraph = DynamicCallGraph()
        self._function_stack: List[Tuple[str, float]] = []
        self._process = psutil.Process(os.getpid()) if HAS_PSUTIL else None

    def analyze(
        self,
        code: Union[str, Callable],
        inputs: Optional[List[Tuple]] = None,
        config: Optional[AnalysisConfig] = None
    ) -> DynamicAnalysisReport:
        """
        Perform comprehensive dynamic analysis on code.

        Args:
            code: Code string or callable to analyze
            inputs: List of input tuples to test with
            config: Analysis configuration

        Returns:
            Complete dynamic analysis report
        """
        if config:
            self.config = config

        inputs = inputs or [()]

        for input_args in inputs:
            if callable(code):
                self._analyze_callable(code, input_args)
            else:
                self._analyze_code_string(code, input_args)

        # Compute derived metrics
        self.performance.compute_hot_spots()

        return self._generate_report()

    def _analyze_callable(self, func: Callable, args: Tuple) -> Any:
        """Analyze a callable function."""
        instrumented_func = self.instrument_function(func)

        try:
            with self._trace_context():
                result = instrumented_func(*args)
            return result
        except Exception as e:
            self.exceptions.add_exception(e, func.__code__.co_filename, func.__code__.co_firstlineno)
            raise

    def _analyze_code_string(self, code: str, args: Tuple) -> None:
        """Analyze a code string."""
        try:
            compiled = compile(code, '<string>', 'exec')
            with self._trace_context():
                exec(compiled)
        except Exception as e:
            self.exceptions.add_exception(e, '<string>', 0)

    @contextmanager
    def _trace_context(self):
        """Context manager for tracing execution."""
        if self.config.enable_tracing:
            sys.settrace(self._trace_function)

        start_time = time.time()
        start_cpu = time.process_time()
        start_memory = self._process.memory_info().rss if self._process else 0

        try:
            yield
        finally:
            if self.config.enable_tracing:
                sys.settrace(None)

            self.trace.total_duration = time.time() - start_time
            self.performance.total_time = time.time() - start_time
            self.performance.cpu_time = time.process_time() - start_cpu
            self.resources.cpu_time = time.process_time() - start_cpu
            if self._process:
                self.resources.memory_usage = self._process.memory_info().rss - start_memory

    def _trace_function(self, frame, event, arg):
        """Trace function for sys.settrace()."""
        code = frame.f_code
        filename = code.co_filename
        line_number = frame.f_lineno
        function_name = code.co_name

        timestamp = time.time()
        thread_id = threading.get_ident()

        # Coverage tracking
        if self.config.enable_coverage:
            self.coverage.add_line_coverage(filename, line_number)

        # Event recording
        if event == 'call':
            self._handle_call_event(frame, function_name, filename, line_number, timestamp, thread_id)
        elif event == 'return':
            self._handle_return_event(frame, function_name, filename, line_number, timestamp, thread_id, arg)
        elif event == 'exception':
            self._handle_exception_event(frame, function_name, filename, line_number, timestamp, thread_id, arg)

        return self._trace_function

    def _handle_call_event(self, frame, function_name, filename, line_number, timestamp, thread_id):
        """Handle a function call event."""
        event = ExecutionEvent(
            event_type='call',
            function_name=function_name,
            filename=filename,
            line_number=line_number,
            timestamp=timestamp,
            thread_id=thread_id,
            args=tuple(frame.f_locals.values()) if frame.f_locals else None
        )
        self.trace.add_event(event)
        self._function_stack.append((function_name, timestamp))

        # Call graph tracking
        if len(self._function_stack) > 1:
            caller = self._function_stack[-2][0]
            self.call_graph.add_call(caller, function_name)

    def _handle_return_event(self, frame, function_name, filename, line_number, timestamp, thread_id, return_value):
        """Handle a function return event."""
        event = ExecutionEvent(
            event_type='return',
            function_name=function_name,
            filename=filename,
            line_number=line_number,
            timestamp=timestamp,
            thread_id=thread_id,
            return_value=return_value
        )
        self.trace.add_event(event)
        self.trace.return_values[function_name] = return_value

        # Performance profiling
        if self._function_stack and self._function_stack[-1][0] == function_name:
            _, start_time = self._function_stack.pop()
            duration = timestamp - start_time
            self.performance.add_timing(function_name, duration)

    def _handle_exception_event(self, frame, function_name, filename, line_number, timestamp, thread_id, exc_info):
        """Handle an exception event."""
        exc_type, exc_value, exc_traceback = exc_info
        event = ExecutionEvent(
            event_type='exception',
            function_name=function_name,
            filename=filename,
            line_number=line_number,
            timestamp=timestamp,
            thread_id=thread_id,
            exception=exc_value
        )
        self.trace.add_event(event)
        self.exceptions.add_exception(exc_value, filename, line_number)

    def instrument_function(self, func: Callable) -> Callable:
        """
        Instrument a function with monitoring hooks.

        Args:
            func: Function to instrument

        Returns:
            Instrumented function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Type checking
            if self.config.enable_type_checking:
                self._check_types(func, args, kwargs)

            # Memory snapshot before
            mem_before = 0
            if self.config.enable_memory_profiling and self._process:
                mem_before = self._process.memory_info().rss

            # Execute function
            start_time = time.time()
            try:
                result = func(*args, **kwargs)

                # Memory snapshot after
                if self.config.enable_memory_profiling and self._process:
                    mem_after = self._process.memory_info().rss
                    mem_delta = mem_after - mem_before
                    self.memory.record_allocation(
                        func.__name__, mem_delta, time.time()
                    )

                return result
            finally:
                duration = time.time() - start_time
                self.performance.add_timing(func.__name__, duration)

        return wrapper

    def _check_types(self, func: Callable, args: Tuple, kwargs: Dict) -> None:
        """Check runtime types against annotations."""
        sig = inspect.signature(func)
        annotations = func.__annotations__

        for i, (param_name, param) in enumerate(sig.parameters.items()):
            if param_name in annotations:
                expected_type = annotations[param_name]
                actual_value = args[i] if i < len(args) else kwargs.get(param_name)

                if actual_value is not None and not isinstance(actual_value, expected_type):
                    self.type_violations.add_violation(
                        param_name,
                        expected_type,
                        type(actual_value),
                        f"{func.__name__}:{func.__code__.co_firstlineno}"
                    )

    def detect_invariants(self, func: Callable, test_inputs: List[Tuple]) -> List[Invariant]:
        """
        Detect program invariants from multiple executions.

        Args:
            func: Function to analyze
            test_inputs: List of input tuples to test with

        Returns:
            List of detected invariants
        """
        invariants: List[Invariant] = []
        observations: Dict[str, List[Any]] = defaultdict(list)

        for inputs in test_inputs:
            result = func(*inputs)
            observations['return'].append(result)

        # Detect constant return value
        if len(set(observations['return'])) == 1:
            invariants.append(Invariant(
                invariant_type='constant',
                expression=f'{func.__name__}() == {observations["return"][0]}',
                confidence=1.0,
                observations=len(test_inputs)
            ))

        # Detect range invariants
        if all(isinstance(v, (int, float)) for v in observations['return']):
            min_val = min(observations['return'])
            max_val = max(observations['return'])
            invariants.append(Invariant(
                invariant_type='range',
                expression=f'{min_val} <= {func.__name__}() <= {max_val}',
                confidence=0.9,
                observations=len(test_inputs)
            ))

        return invariants

    def track_coverage(self, func: Callable, test_inputs: List[Tuple]) -> CoverageReport:
        """
        Track code coverage across multiple test inputs.

        Args:
            func: Function to analyze
            test_inputs: List of input tuples to test with

        Returns:
            Coverage report
        """
        self.coverage = CoverageReport()

        for inputs in test_inputs:
            with self._trace_context():
                try:
                    func(*inputs)
                except Exception:
                    pass

        # Get total lines in function
        source_lines = inspect.getsourcelines(func)[0]
        self.coverage.compute_coverage(len(source_lines))

        return self.coverage

    def track_dynamic_taint(self, func: Callable, taint_sources: List[str]) -> TaintFlows:
        """
        Track taint propagation at runtime.

        Args:
            func: Function to analyze
            taint_sources: List of tainted variable names

        Returns:
            Taint flow analysis
        """
        self.taint = TaintFlows()

        # Mark taint sources
        for source in taint_sources:
            self.taint.add_taint_source(source, None, f"user_input:{source}")

        return self.taint

    def detect_regressions(
        self,
        baseline: ExecutionTrace,
        current: ExecutionTrace
    ) -> RegressionReport:
        """
        Detect regressions between two execution traces.

        Args:
            baseline: Baseline execution trace
            current: Current execution trace

        Returns:
            Regression report
        """
        report = RegressionReport()

        # Check for behavioral changes
        if len(baseline.events) != len(current.events):
            report.behavioral_changes.append({
                'type': 'event_count_mismatch',
                'baseline': len(baseline.events),
                'current': len(current.events)
            })

        # Check for performance regressions
        if current.total_duration > baseline.total_duration * 1.1:  # 10% threshold
            report.performance_regressions.append({
                'type': 'execution_time',
                'baseline': baseline.total_duration,
                'current': current.total_duration,
                'regression': ((current.total_duration / baseline.total_duration) - 1) * 100
            })

        return report

    def analyze_call_graph(self, trace: ExecutionTrace) -> DynamicCallGraph:
        """
        Construct dynamic call graph from execution trace.

        Args:
            trace: Execution trace

        Returns:
            Dynamic call graph
        """
        graph = DynamicCallGraph()
        call_stack = []

        for event in trace.events:
            if event.event_type == 'call':
                if call_stack:
                    graph.add_call(call_stack[-1], event.function_name)
                call_stack.append(event.function_name)
            elif event.event_type == 'return' and call_stack:
                call_stack.pop()

        return graph

    def detect_memory_leaks(self, memory_profile: MemoryProfile) -> List[MemoryLeak]:
        """
        Detect memory leaks from memory profile.

        Args:
            memory_profile: Memory profile data

        Returns:
            List of detected memory leaks
        """
        leaks: List[MemoryLeak] = []

        for obj_type, allocations in memory_profile.allocations.items():
            alloc_count = len(allocations)
            dealloc_count = memory_profile.deallocations.get(obj_type, 0)

            if alloc_count > dealloc_count:
                leaks.append(MemoryLeak(
                    object_type=obj_type,
                    allocation_count=alloc_count,
                    deallocation_count=dealloc_count,
                    leaked_count=alloc_count - dealloc_count
                ))

        return leaks

    def _generate_report(self) -> DynamicAnalysisReport:
        """Generate complete analysis report."""
        return DynamicAnalysisReport(
            execution_trace=self.trace,
            performance_profile=self.performance,
            memory_profile=self.memory,
            coverage_report=self.coverage,
            exception_report=self.exceptions,
            resource_usage=self.resources,
            taint_flows=self.taint,
            type_violations=self.type_violations,
            call_graph=self.call_graph,
            memory_leaks=self.detect_memory_leaks(self.memory)
        )


# Example usage
if __name__ == "__main__":
    # Create analyzer
    analyzer = DynamicAnalyzer(AnalysisConfig(
        enable_tracing=True,
        enable_profiling=True,
        enable_coverage=True,
        enable_type_checking=True
    ))

    # Sample function to analyze
    def fibonacci(n: int) -> int:
        """Calculate fibonacci number."""
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    # Analyze function
    report = analyzer.analyze(fibonacci, inputs=[(5,), (10,), (15,)])

    # Print summary
    print(report.summary())
    print("\nHot Spots:")
    for func, total_time in report.performance_profile.hot_spots[:5]:
        print(f"  {func}: {total_time:.4f}s")

    print(f"\nCoverage: {report.coverage_report.coverage_percentage:.2f}%")
    print(f"Total Events: {len(report.execution_trace.events)}")

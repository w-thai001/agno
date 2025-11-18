"""
Performance Profiler FSA - Example Usage

This module demonstrates various ways to use the Performance Profiler FSA
for deep performance analysis, bottleneck detection, and optimization.
"""

import time
from pathlib import Path

from agno.fsas.performance_profiler import (
    PerformanceProfilerFSA,
    ProfileType,
)


# Sample FSA implementations to profile
def fibonacci_recursive(n: int) -> int:
    """Recursive fibonacci (intentionally inefficient for demo)"""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """Iterative fibonacci (more efficient)"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def memory_intensive_task():
    """Task that allocates significant memory"""
    large_list = [i ** 2 for i in range(100000)]
    matrix = [[j * i for j in range(1000)] for i in range(1000)]
    return sum(large_list) + len(matrix)


def cpu_intensive_task():
    """CPU-bound computation"""
    result = 0
    for i in range(1000000):
        result += i ** 2
    return result


def io_simulation_task():
    """Simulate I/O-bound task"""
    time.sleep(0.1)  # Simulate I/O wait
    return "I/O complete"


def example_basic_profiling():
    """Example 1: Basic function profiling"""
    print("\n" + "="*60)
    print("Example 1: Basic Function Profiling")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Profile a simple function
    result = profiler.profile_execution(fibonacci_iterative, 20)

    print(f"Function: fibonacci_iterative(20)")
    print(f"  Execution Time: {result.execution_time*1000:.2f}ms")
    print(f"  Memory Used: {result.memory_used:.2f}MB")
    print(f"  CPU Usage: {result.cpu_percent:.1f}%")
    print(f"  Call Count: {result.call_count}")

    return result


def example_compare_algorithms():
    """Example 2: Compare performance of different algorithms"""
    print("\n" + "="*60)
    print("Example 2: Algorithm Comparison")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Profile recursive version
    print("\nProfiling recursive fibonacci...")
    recursive_result = profiler.profile_execution(
        fibonacci_recursive,
        15,  # Small number due to exponential complexity
        profile_type=ProfileType.FULL
    )

    # Profile iterative version
    print("Profiling iterative fibonacci...")
    iterative_result = profiler.profile_execution(
        fibonacci_iterative,
        15,
        profile_type=ProfileType.FULL
    )

    # Compare results
    print("\nComparison:")
    print(f"  Recursive: {recursive_result.execution_time*1000:.2f}ms")
    print(f"  Iterative: {iterative_result.execution_time*1000:.2f}ms")

    speedup = recursive_result.execution_time / iterative_result.execution_time
    print(f"  Speedup: {speedup:.1f}x faster")

    if speedup > 2:
        print("  ✓ Iterative implementation is significantly faster!")

    return recursive_result, iterative_result


def example_memory_profiling():
    """Example 3: Detailed memory profiling"""
    print("\n" + "="*60)
    print("Example 3: Memory Profiling")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Profile memory usage
    print("Profiling memory-intensive task...")
    memory_profile = profiler.profile_memory(memory_intensive_task)

    print(f"\nMemory Profile:")
    print(f"  Peak Memory: {memory_profile.peak_memory:.2f}MB")
    print(f"  Current Memory: {memory_profile.current_memory:.2f}MB")
    print(f"  Total Allocations: {memory_profile.allocations:,}")
    print(f"  Net Allocations: {memory_profile.net_allocations:,}")

    print(f"\nTop Memory Allocations:")
    for i, leak in enumerate(memory_profile.leaks[:5], 1):
        print(f"  {i}. {leak['size_mb']:.2f}MB - {leak['count']} allocations")

    return memory_profile


def example_cpu_profiling():
    """Example 4: CPU profiling with hotspot detection"""
    print("\n" + "="*60)
    print("Example 4: CPU Profiling")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Profile CPU usage
    print("Profiling CPU-intensive task...")
    cpu_profile = profiler.profile_cpu(cpu_intensive_task)

    print(f"\nCPU Profile:")
    print(f"  Total CPU Time: {cpu_profile.total_cpu_time*1000:.2f}ms")
    print(f"  Function Calls: {cpu_profile.function_calls:,}")
    print(f"  Primitive Calls: {cpu_profile.primitive_calls:,}")

    print(f"\nTop CPU Hotspots:")
    for i, hotspot in enumerate(cpu_profile.hotspots[:5], 1):
        print(f"  {i}. {hotspot['function']}")
        print(f"     Calls: {hotspot['call_count']}, "
              f"Cumulative: {hotspot['cumulative_time']*1000:.2f}ms")

    return cpu_profile


def example_profiling_session():
    """Example 5: Continuous profiling session"""
    print("\n" + "="*60)
    print("Example 5: Profiling Session")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Start a profiling session
    session_id = "continuous_monitoring"
    profiler.start_profiling(session_id, profile_type=ProfileType.FULL)

    print(f"Started profiling session: {session_id}")

    # Simulate multiple operations
    print("\nRunning operations...")
    for i in range(5):
        fibonacci_iterative(20)
        time.sleep(0.05)
        print(f"  Operation {i+1} complete")

    # Stop profiling and get report
    report = profiler.stop_profiling(session_id)

    print(f"\nProfiling Session Report:")
    print(f"  Session ID: {report.session_id}")
    print(f"  Duration: {report.total_duration:.2f}s")
    print(f"  Profile Type: {report.profile_type.value}")
    print(f"  Statistics:")
    print(f"    Execution Time (mean): {report.statistics.get('execution_time_mean', 0)*1000:.2f}ms")
    print(f"    Memory (mean): {report.statistics.get('memory_mean', 0):.2f}MB")

    return report


def example_context_manager():
    """Example 6: Using context manager for scoped profiling"""
    print("\n" + "="*60)
    print("Example 6: Context Manager Profiling")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Use context manager
    print("Profiling with context manager...")
    with profiler.session("my_operation") as session_id:
        print(f"  Session started: {session_id}")

        # Operations to profile
        result = fibonacci_iterative(25)
        time.sleep(0.05)
        cpu_intensive_task()

        print(f"  Operations complete")

    # Report is automatically generated and stored
    report = profiler.state.get('last_report')

    if report:
        print(f"\nSession Report:")
        print(f"  Duration: {report.total_duration:.2f}s")
        print(f"  Results Collected: {len(report.results)}")

    return report


def example_statistical_analysis():
    """Example 7: Statistical analysis of multiple runs"""
    print("\n" + "="*60)
    print("Example 7: Statistical Analysis")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Run multiple iterations and collect results
    print("Running 10 iterations for statistical analysis...")
    results = []
    for i in range(10):
        result = profiler.profile_execution(fibonacci_iterative, 25)
        results.append(result)
        print(f"  Iteration {i+1}: {result.execution_time*1000:.2f}ms")

    # Analyze performance
    analysis = profiler.analyze_performance(results)

    print(f"\nStatistical Analysis:")
    exec_stats = analysis.summary_stats.get('execution_time', {})
    print(f"  Count: {analysis.summary_stats.get('count', 0)}")
    print(f"  Mean: {exec_stats.get('mean', 0)*1000:.2f}ms")
    print(f"  Median: {exec_stats.get('median', 0)*1000:.2f}ms")
    print(f"  Min: {exec_stats.get('min', 0)*1000:.2f}ms")
    print(f"  Max: {exec_stats.get('max', 0)*1000:.2f}ms")
    print(f"  P95: {exec_stats.get('p95', 0)*1000:.2f}ms")
    print(f"  P99: {exec_stats.get('p99', 0)*1000:.2f}ms")
    print(f"  StdDev: {exec_stats.get('stddev', 0)*1000:.2f}ms")

    print(f"\nPerformance Score: {analysis.performance_score:.1f}/100")

    print(f"\nRecommendations:")
    for i, rec in enumerate(analysis.recommendations, 1):
        print(f"  {i}. {rec}")

    if analysis.anomalies:
        print(f"\nAnomalies Detected: {len(analysis.anomalies)}")
        for anomaly in analysis.anomalies[:3]:
            print(f"  - {anomaly['type']} at iteration {anomaly['index']}")

    return analysis


def example_bottleneck_detection():
    """Example 8: Bottleneck detection"""
    print("\n" + "="*60)
    print("Example 8: Bottleneck Detection")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Create a mix of fast and slow operations
    print("Running operations with varying performance...")
    results = []

    # Fast operations
    for _ in range(5):
        results.append(profiler.profile_execution(fibonacci_iterative, 15))

    # Slow operation (bottleneck)
    print("  Including slow operation...")
    results.append(profiler.profile_execution(fibonacci_recursive, 20))

    # More fast operations
    for _ in range(4):
        results.append(profiler.profile_execution(fibonacci_iterative, 15))

    # Create report
    from datetime import datetime
    from agno.fsas.performance_profiler import ProfileReport

    report = ProfileReport(
        session_id="bottleneck_test",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=sum(r.execution_time for r in results),
        results=results
    )

    # Detect bottlenecks
    bottlenecks = profiler.detect_bottlenecks(report)

    print(f"\nBottleneck Analysis:")
    print(f"  Total Bottlenecks Found: {len(bottlenecks)}")

    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"\n  Bottleneck {i}:")
        print(f"    Location: {bottleneck.location}")
        print(f"    Severity: {bottleneck.severity.value}")
        print(f"    Impact: {bottleneck.impact:.1f}% of total time")
        print(f"    Root Cause: {bottleneck.root_cause}")
        print(f"    Recommendation: {bottleneck.recommendation}")

    return bottlenecks


def example_regression_detection():
    """Example 9: Performance regression detection"""
    print("\n" + "="*60)
    print("Example 9: Regression Detection")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Baseline performance
    print("Collecting baseline performance...")
    baseline_results = []
    for _ in range(5):
        result = profiler.profile_execution(fibonacci_iterative, 25)
        baseline_results.append(result)

    # Simulate performance regression (using slower algorithm)
    print("Collecting current performance (with regression)...")
    current_results = []
    for _ in range(5):
        # Simulate regression with slightly more work
        result = profiler.profile_execution(fibonacci_iterative, 30)
        current_results.append(result)

    # Create reports
    from datetime import datetime
    from agno.fsas.performance_profiler import ProfileReport

    baseline_report = ProfileReport(
        session_id="baseline_v1.0",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=sum(r.execution_time for r in baseline_results),
        results=baseline_results
    )

    current_report = ProfileReport(
        session_id="current_v1.1",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=sum(r.execution_time for r in current_results),
        results=current_results
    )

    # Compare profiles
    comparison = profiler.compare_profiles(baseline_report, current_report)

    print(f"\nPerformance Comparison:")
    print(f"  Baseline: {comparison.baseline_session}")
    print(f"  Current: {comparison.current_session}")
    print(f"  Execution Time Change: {comparison.execution_time_delta:+.1f}%")
    print(f"  Memory Change: {comparison.memory_delta:+.1f}%")
    print(f"  CPU Change: {comparison.cpu_delta:+.1f}%")

    if comparison.regressions:
        print(f"\n  ⚠ Regressions Detected: {len(comparison.regressions)}")
        for reg in comparison.regressions:
            print(f"    - {reg['metric']}: {reg['delta']:+.1f}% ({reg['impact']} impact)")

    if comparison.improvements:
        print(f"\n  ✓ Improvements Found: {len(comparison.improvements)}")
        for imp in comparison.improvements:
            print(f"    - {imp['metric']}: {imp['delta']:.1f}% faster")

    print(f"\n  Summary: {comparison.summary}")

    return comparison


def example_cascade_profiling():
    """Example 10: FSA cascade profiling"""
    print("\n" + "="*60)
    print("Example 10: FSA Cascade Profiling")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Define a cascade of FSA operations
    def data_ingestion():
        """FSA 1: Data ingestion"""
        time.sleep(0.05)
        return [i for i in range(1000)]

    def data_processing():
        """FSA 2: Data processing"""
        time.sleep(0.1)
        return fibonacci_iterative(25)

    def data_validation():
        """FSA 3: Data validation"""
        time.sleep(0.03)
        return True

    def data_export():
        """FSA 4: Data export"""
        time.sleep(0.07)
        return "exported"

    # Profile cascade
    cascade_config = {
        'cascade_id': 'data_pipeline',
        'fsas': [
            {'name': 'DataIngestion', 'function': data_ingestion},
            {'name': 'DataProcessing', 'function': data_processing},
            {'name': 'DataValidation', 'function': data_validation},
            {'name': 'DataExport', 'function': data_export}
        ]
    }

    print("Profiling FSA cascade...")
    cascade_profile = profiler.profile_fsa_cascade(cascade_config)

    print(f"\nCascade Profile:")
    print(f"  Cascade ID: {cascade_profile.cascade_id}")
    print(f"  Total Execution Time: {cascade_profile.total_execution_time*1000:.2f}ms")
    print(f"  Cascade Overhead: {cascade_profile.cascade_overhead*1000:.2f}ms")

    print(f"\n  FSA Performance:")
    for fsa in cascade_profile.fsa_profiles:
        print(f"    {fsa['name']}: {fsa['execution_time']*1000:.2f}ms "
              f"({fsa['memory_used']:.2f}MB)")

    print(f"\n  Critical Path (slowest FSAs):")
    for i, fsa_name in enumerate(cascade_profile.critical_path, 1):
        print(f"    {i}. {fsa_name}")

    return cascade_profile


def example_report_export():
    """Example 11: Export profiling reports"""
    print("\n" + "="*60)
    print("Example 11: Report Export")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Profile some operations
    print("Profiling operations for export...")
    results = []
    for i in range(5):
        result = profiler.profile_execution(fibonacci_iterative, 20)
        results.append(result)

    # Create report
    from datetime import datetime
    from agno.fsas.performance_profiler import ProfileReport

    report = ProfileReport(
        session_id="export_example",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=sum(r.execution_time for r in results),
        results=results
    )

    # Export to JSON
    json_str = report.to_json()
    print(f"\nJSON Export:")
    print(f"  Size: {len(json_str)} bytes")
    print(f"  Preview: {json_str[:100]}...")

    # Export to file
    output_path = "/tmp/profile_report.json"
    report.to_json(output_path)
    print(f"\n  Saved to: {output_path}")

    # Export flamegraph data
    flamegraph_path = "/tmp/flamegraph.txt"
    success = profiler.export_flamegraph(report, flamegraph_path)
    if success:
        print(f"  Flamegraph data saved to: {flamegraph_path}")

    return report


def example_performance_validation():
    """Example 12: Validate performance against SLAs"""
    print("\n" + "="*60)
    print("Example 12: Performance Validation")
    print("="*60)

    profiler = PerformanceProfilerFSA()

    # Run operations
    print("Running operations...")
    results = []
    for _ in range(10):
        result = profiler.profile_execution(fibonacci_iterative, 20)
        results.append(result)

    # Create report
    from datetime import datetime
    from agno.fsas.performance_profiler import ProfileReport

    report = ProfileReport(
        session_id="validation_test",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_duration=sum(r.execution_time for r in results),
        results=results
    )

    # Validate against default thresholds
    print("\nValidating against default thresholds...")
    passed = profiler.validate_performance(report)

    print(f"  P95 Execution Time Threshold: {profiler.thresholds['p95_execution_time']}s")
    print(f"  P99 Execution Time Threshold: {profiler.thresholds['p99_execution_time']}s")
    print(f"  Max Memory Threshold: {profiler.thresholds['max_memory_mb']}MB")
    print(f"  Max CPU Threshold: {profiler.thresholds['max_cpu_percent']}%")

    if passed:
        print("\n  ✓ Performance validation PASSED")
    else:
        print("\n  ✗ Performance validation FAILED")

    # Validate with custom strict thresholds
    print("\nValidating against strict thresholds...")
    strict_thresholds = {
        'p95_execution_time': 0.001,  # 1ms
        'p99_execution_time': 0.002,  # 2ms
        'max_memory_mb': 50,
        'max_cpu_percent': 50
    }

    strict_passed = profiler.validate_performance(report, strict_thresholds)

    if strict_passed:
        print("  ✓ Strict validation PASSED")
    else:
        print("  ✗ Strict validation FAILED (expected)")

    return passed


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*80)
    print(" Performance Profiler FSA - Comprehensive Examples ".center(80, "="))
    print("="*80)

    examples = [
        example_basic_profiling,
        example_compare_algorithms,
        example_memory_profiling,
        example_cpu_profiling,
        example_profiling_session,
        example_context_manager,
        example_statistical_analysis,
        example_bottleneck_detection,
        example_regression_detection,
        example_cascade_profiling,
        example_report_export,
        example_performance_validation,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print(" Examples Complete ".center(80, "="))
    print("="*80)


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_basic_profiling()
    # example_compare_algorithms()
    # example_memory_profiling()
    # example_cpu_profiling()
    # example_statistical_analysis()
    # example_bottleneck_detection()

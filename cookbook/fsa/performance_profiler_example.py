"""
Minimal example of the Performance Profiler FSA.

This script demonstrates how to use the PerformanceProfiler to track
execution time, memory usage, and identify bottlenecks.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path to import agno
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "agno"))

from agno.fsa import PerformanceProfiler, ProfileBlock, print_performance_report


# Example functions to profile
def fast_operation():
    """A fast operation."""
    total = 0
    for i in range(1000):
        total += i
    return total


def slow_operation():
    """A slow operation (bottleneck)."""
    time.sleep(0.5)  # Simulate slow processing
    data = [i ** 2 for i in range(10000)]
    return sum(data)


def memory_intensive_operation():
    """A memory-intensive operation."""
    # Create large data structures
    data = [list(range(10000)) for _ in range(100)]
    return len(data)


def recursive_fibonacci(n):
    """Inefficient recursive Fibonacci (for demonstration)."""
    if n <= 1:
        return n
    return recursive_fibonacci(n - 1) + recursive_fibonacci(n - 2)


def example_basic_profiling():
    """Example 1: Basic profiling with start/stop."""
    print("\n🚀 EXAMPLE 1: Basic Profiling\n")

    profiler = PerformanceProfiler()

    # Profile individual operations
    profiler.start("fast_operation")
    fast_operation()
    profiler.stop("fast_operation")

    profiler.start("slow_operation")
    slow_operation()
    profiler.stop("slow_operation")

    profiler.start("memory_intensive")
    memory_intensive_operation()
    profiler.stop("memory_intensive")

    # Generate and print report
    report = profiler.end_profiling()
    print_performance_report(report)


def example_context_manager():
    """Example 2: Using context manager for profiling."""
    print("\n🚀 EXAMPLE 2: Context Manager Profiling\n")

    profiler = PerformanceProfiler()

    # Use context manager
    with ProfileBlock(profiler, "fast_loop"):
        for _ in range(5):
            fast_operation()

    with ProfileBlock(profiler, "slow_processing"):
        slow_operation()

    with ProfileBlock(profiler, "data_processing"):
        memory_intensive_operation()

    # Generate and print report
    report = profiler.end_profiling()
    print_performance_report(report)


def example_function_profiling():
    """Example 3: Profile function calls directly."""
    print("\n🚀 EXAMPLE 3: Function Call Profiling\n")

    profiler = PerformanceProfiler()

    # Profile function calls
    result1 = profiler.profile(fast_operation)
    result2 = profiler.profile(slow_operation)
    result3 = profiler.profile(recursive_fibonacci, 20)

    print(f"  Results: {result1}, {result2}, {result3}")

    # Generate and print report
    report = profiler.end_profiling()
    print_performance_report(report)


def example_multiple_calls():
    """Example 4: Profile multiple calls to same function."""
    print("\n🚀 EXAMPLE 4: Multiple Calls Profiling\n")

    profiler = PerformanceProfiler()

    # Call same function multiple times
    for i in range(3):
        with ProfileBlock(profiler, "fast_operation"):
            fast_operation()

    for i in range(2):
        with ProfileBlock(profiler, "slow_operation"):
            slow_operation()

    # Generate and print report
    report = profiler.end_profiling()
    print_performance_report(report)


def example_nested_profiling():
    """Example 5: Nested profiling blocks."""
    print("\n🚀 EXAMPLE 5: Nested Profiling\n")

    profiler = PerformanceProfiler()

    with ProfileBlock(profiler, "outer_operation"):
        time.sleep(0.1)

        with ProfileBlock(profiler, "inner_fast"):
            fast_operation()

        with ProfileBlock(profiler, "inner_slow"):
            slow_operation()

        time.sleep(0.1)

    # Generate and print report
    report = profiler.end_profiling()
    print_performance_report(report)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("PERFORMANCE PROFILER FSA - MINIMAL EXAMPLES")
    print("=" * 80)

    examples = [
        example_basic_profiling,
        example_context_manager,
        example_function_profiling,
        example_multiple_calls,
        example_nested_profiling,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {example_func.__name__}: {e}\n")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

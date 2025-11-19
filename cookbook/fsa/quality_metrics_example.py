"""
Example usage of the Quality Metrics Calculator FSA.

This script demonstrates how to use the QualityMetricsCalculator to analyze
code quality metrics including complexity, coverage, duplication, and more.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import agno
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "agno"))

from agno.fsa import QualityMetricsCalculator


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def print_metrics_report(results):
    """Print a formatted metrics report."""
    print_separator("=")
    print("CODE QUALITY METRICS REPORT")
    print_separator("=")

    # Print quality scores
    scores = results["quality_scores"]
    if scores:
        print("\n📊 QUALITY SCORES:")
        print_separator("-")
        print(f"  Overall Score:          {scores.overall_score:.2f}/100")
        print(f"  Maintainability Index:  {scores.maintainability_index:.2f}/100")
        print(f"  Complexity Score:       {scores.complexity_score:.2f}/100")
        print(f"  Code Coverage:          {scores.code_coverage:.2f}%")
        print(f"  Duplication Score:      {scores.duplication_score:.2f}/100")
        print(f"  Technical Debt Ratio:   {scores.technical_debt_ratio:.3f}")

    # Print file metrics
    metrics = results["metrics"]
    if metrics:
        print("\n📁 FILE METRICS:")
        print_separator("-")
        for file_path, file_metrics in metrics.items():
            filename = os.path.basename(file_path)
            print(f"\n  {filename}:")
            print(f"    Lines of Code:      {file_metrics.lines_of_code}")
            print(f"    Functions:          {file_metrics.function_count}")
            print(f"    Classes:            {file_metrics.class_count}")
            print(f"    Complexity:         {file_metrics.cyclomatic_complexity}")
            print(f"    Avg Func Complexity: {file_metrics.avg_function_complexity:.2f}")
            print(f"    Comment Lines:      {file_metrics.comment_lines}")

    # Print duplication data
    duplication = results["duplication_data"]
    if duplication:
        print("\n🔄 DUPLICATION ANALYSIS:")
        print_separator("-")
        print(f"  Total Lines:        {duplication['total_lines']}")
        print(f"  Duplicated Lines:   {duplication['duplicated_lines']}")
        print(f"  Duplication:        {duplication['duplication_percentage']:.2f}%")

        if duplication["duplicate_blocks"]:
            print(f"\n  Top Duplicate Blocks:")
            for block in duplication["duplicate_blocks"][:3]:
                print(f"    - '{block['line'][:60]}...'")
                print(f"      Appears {block['count']} times in {len(block['files'])} file(s)")

    # Print recommendations
    recommendations = results["recommendations"]
    if recommendations:
        print("\n💡 RECOMMENDATIONS:")
        print_separator("-")
        for i, rec in enumerate(recommendations, 1):
            severity_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "info": "🟢",
            }.get(rec["severity"], "⚪")

            print(f"\n  {i}. [{severity_emoji} {rec['severity'].upper()}] {rec['category']}")
            print(f"     {rec['message']}")

            if rec.get("details"):
                print(f"     Details:")
                for detail in rec["details"][:3]:
                    print(f"       - {detail}")

    # Print FSA state
    print(f"\n🤖 FSA State: {results['current_state']}")

    # Print errors if any
    if results.get("errors"):
        print("\n❌ ERRORS:")
        print_separator("-")
        for error in results["errors"]:
            print(f"  - {error}")

    print_separator("=")


def example_basic_usage():
    """Example 1: Basic usage with file paths."""
    print("\n🚀 EXAMPLE 1: Basic Usage with File Paths\n")

    # Get the directory containing this script
    script_dir = Path(__file__).parent

    # List of code files to analyze
    code_files = [
        str(script_dir / "sample_code_1.py"),
        str(script_dir / "sample_code_2.py"),
        str(script_dir / "sample_code_3.py"),
    ]

    # Create calculator
    calculator = QualityMetricsCalculator()

    # Calculate metrics
    results = calculator.calculate(code_files=code_files)

    # Print report
    print_metrics_report(results)


def example_with_test_results():
    """Example 2: Usage with test results."""
    print("\n🚀 EXAMPLE 2: With Test Results\n")

    script_dir = Path(__file__).parent

    code_files = [
        str(script_dir / "sample_code_1.py"),
        str(script_dir / "sample_code_2.py"),
    ]

    # Simulate test results
    test_results = {
        "total_tests": 25,
        "passed_tests": 22,
        "failed_tests": 3,
        "coverage_percentage": 75.5,
        "lines_covered": 120,
        "lines_total": 159,
    }

    # Create calculator
    calculator = QualityMetricsCalculator()

    # Calculate metrics with test results
    results = calculator.calculate(
        code_files=code_files,
        test_results=test_results,
        execution_logs=["Test suite completed", "3 tests failed"],
    )

    # Print report
    print_metrics_report(results)


def example_with_inline_code():
    """Example 3: Usage with inline code content."""
    print("\n🚀 EXAMPLE 3: With Inline Code Content\n")

    # Define code files with inline content
    code_files = [
        {
            "path": "inline_example.py",
            "content": '''"""Simple example module."""

def factorial(n):
    """Calculate factorial."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


class MathUtils:
    """Math utility functions."""

    @staticmethod
    def is_prime(n):
        """Check if number is prime."""
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    @staticmethod
    def gcd(a, b):
        """Calculate greatest common divisor."""
        while b:
            a, b = b, a % b
        return a
''',
        }
    ]

    # Create calculator
    calculator = QualityMetricsCalculator()

    # Calculate metrics
    results = calculator.calculate(code_files=code_files)

    # Print report
    print_metrics_report(results)


def example_fsa_state_transitions():
    """Example 4: Observing FSA state transitions."""
    print("\n🚀 EXAMPLE 4: FSA State Transitions\n")

    script_dir = Path(__file__).parent
    code_files = [str(script_dir / "sample_code_1.py")]

    # Create calculator with logging
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    calculator = QualityMetricsCalculator()

    print("Initial State:", calculator.current_state)
    print("\nRunning FSA...\n")

    # Calculate metrics
    results = calculator.calculate(code_files=code_files)

    print("\nFinal State:", calculator.current_state)
    print("State History:", " -> ".join(str(s) for s in calculator.state_history))


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("QUALITY METRICS CALCULATOR FSA - EXAMPLES")
    print("=" * 80)

    examples = [
        ("Basic Usage", example_basic_usage),
        ("With Test Results", example_with_test_results),
        ("Inline Code Content", example_with_inline_code),
        ("FSA State Transitions", example_fsa_state_transitions),
    ]

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
            print("\n")
        except Exception as e:
            print(f"\n❌ Error in example '{name}': {e}\n")

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

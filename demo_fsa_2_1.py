#!/usr/bin/env python3
"""
Demo script for FSA-2.1: Code Quality Validator

This script demonstrates the code quality validation capabilities
on the provided sample JavaScript code.
"""

import sys
import json
from pathlib import Path

# Add the agno library to the path
sys.path.insert(0, str(Path(__file__).parent / "libs" / "agno"))

from agno.fsa import CodeQualityValidator, Priority


def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_metrics(metrics_dict: dict) -> None:
    """Print quality metrics in a formatted table."""
    print("\n📊 Quality Metrics:")
    print("-" * 70)
    print(f"{'Metric':<20} {'Score':<10} {'Rating'}")
    print("-" * 70)

    def get_rating(score: float) -> str:
        if score >= 90:
            return "✅ Excellent"
        elif score >= 75:
            return "🟢 Good"
        elif score >= 60:
            return "🟡 Fair"
        elif score >= 40:
            return "🟠 Poor"
        else:
            return "🔴 Critical"

    for metric, score in metrics_dict.items():
        if metric != "overall":
            print(f"{metric.capitalize():<20} {score:<10.2f} {get_rating(score)}")

    print("-" * 70)
    print(f"{'Overall Score':<20} {metrics_dict['overall']:<10.2f} {get_rating(metrics_dict['overall'])}")
    print("-" * 70)


def print_suggestions(suggestions: list) -> None:
    """Print improvement suggestions grouped by priority."""
    if not suggestions:
        print("\n✅ No issues found! Code quality is excellent.")
        return

    print(f"\n📋 Found {len(suggestions)} improvement suggestion(s):")
    print()

    # Group by priority
    priority_groups = {
        Priority.CRITICAL: [],
        Priority.HIGH: [],
        Priority.MEDIUM: [],
        Priority.LOW: [],
    }

    for suggestion in suggestions:
        priority_groups[Priority(suggestion["priority"])].append(suggestion)

    # Priority icons
    priority_icons = {
        Priority.CRITICAL: "🔴",
        Priority.HIGH: "🟠",
        Priority.MEDIUM: "🟡",
        Priority.LOW: "🔵",
    }

    for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
        group_suggestions = priority_groups[priority]
        if not group_suggestions:
            continue

        print(f"\n{priority_icons[priority]} {priority.value.upper()} Priority ({len(group_suggestions)} issues)")
        print("-" * 70)

        for idx, suggestion in enumerate(group_suggestions, 1):
            print(f"\n  [{idx}] {suggestion['category'].upper()}")
            print(f"      Issue: {suggestion['issue']}")
            print(f"      Suggestion: {suggestion['suggestion']}")

            if suggestion.get("line"):
                print(f"      Line: {suggestion['line']}")

            if suggestion.get("code_snippet"):
                print(f"      Current: {suggestion['code_snippet']}")

            if suggestion.get("fixed_code"):
                print(f"      Improved: {suggestion['fixed_code']}")


def validate_sample_code() -> None:
    """Run validation on the sample JavaScript code."""
    print_section_header("FSA-2.1: Code Quality Validator Demo")

    # Sample code from requirements
    sample_code = """function badCode(x){var y=x*2;return y}"""

    print("\n📝 Sample Code to Validate:")
    print("-" * 70)
    print(sample_code)
    print("-" * 70)

    # Initialize validator
    print("\n⚙️  Initializing Code Quality Validator...")
    validator = CodeQualityValidator()

    # Validate code
    print("🔍 Running validation...")
    result = validator.validateCode(sample_code, "javascript")

    # Display results
    print_section_header("Validation Results")

    # Print metrics
    print_metrics(result.metrics.to_dict())

    # Print suggestions
    print_suggestions([s.to_dict() for s in result.suggestions])

    # Generate improved code
    print_section_header("Suggested Improved Code")
    print()
    improved_code = """/**
 * Doubles the input value.
 * @param {number} x - The input value to double
 * @returns {number} The doubled value
 */
function doubleValue(x) {
  const result = x * 2;
  return result;
}"""
    print(improved_code)

    # Summary
    print_section_header("Summary")
    print(f"\n✓ Analyzed: 1 JavaScript function")
    print(f"✓ Overall Quality Score: {result.metrics.overall:.2f}/100")
    print(f"✓ Issues Found: {len(result.suggestions)}")
    print(f"✓ Critical Issues: {len([s for s in result.suggestions if s.priority == Priority.CRITICAL])}")
    print(f"✓ High Priority: {len([s for s in result.suggestions if s.priority == Priority.HIGH])}")
    print(f"✓ Medium Priority: {len([s for s in result.suggestions if s.priority == Priority.MEDIUM])}")
    print(f"✓ Low Priority: {len([s for s in result.suggestions if s.priority == Priority.LOW])}")

    print("\n" + "=" * 70)
    print()


def validate_python_sample() -> None:
    """Run validation on a sample Python code."""
    print_section_header("Bonus: Python Code Validation Demo")

    # Sample Python code with issues
    sample_code = """def BadFunction(x,y):
  result=x+y
  return result
"""

    print("\n📝 Sample Python Code to Validate:")
    print("-" * 70)
    print(sample_code)
    print("-" * 70)

    # Validate code
    validator = CodeQualityValidator()
    print("\n🔍 Running validation...")
    result = validator.validateCode(sample_code, "python")

    # Display results
    print_metrics(result.metrics.to_dict())
    print_suggestions([s.to_dict() for s in result.suggestions])

    print("\n💡 Suggested improved code:")
    improved_code = '''"""Module for mathematical operations."""


def add_numbers(x, y):
    """
    Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        The sum of x and y
    """
    result = x + y
    return result
'''
    print(improved_code)


if __name__ == "__main__":
    # Validate JavaScript sample (main requirement)
    validate_sample_code()

    # Validate Python sample (bonus demo)
    validate_python_sample()

    print("\n✅ Demo completed successfully!")
    print("\n💡 Integration Points:")
    print("   • FSA-1.1 (Prompt Optimizer): Will optimize suggestion messages")
    print("   • FSA-1.2 (Template Library): Will validate against code templates")
    print()

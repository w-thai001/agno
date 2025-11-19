"""
Minimal example of the Code Smell Detector FSA.

This script demonstrates how to use the CodeSmellDetector to identify
common code smells like long methods, large classes, and duplicate code.
"""

import sys
from pathlib import Path

# Add parent directory to path to import agno
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "agno"))

from agno.fsa import CodeSmellDetector, print_smell_report


def example_basic_detection():
    """Example 1: Basic smell detection on sample files."""
    print("\n🚀 EXAMPLE 1: Basic Smell Detection\n")

    detector = CodeSmellDetector()

    # Analyze existing sample files
    sample_dir = Path(__file__).parent
    code_files = [
        str(sample_dir / "sample_code_1.py"),
        str(sample_dir / "sample_code_2.py"),
    ]

    # Detect smells
    report = detector.detect(code_files)

    # Print report
    print_smell_report(report)


def example_inline_smelly_code():
    """Example 2: Detect smells in inline code with various issues."""
    print("\n🚀 EXAMPLE 2: Smelly Code Detection\n")

    detector = CodeSmellDetector()

    # Create code with multiple smells
    smelly_code = {
        "path": "smelly_code.py",
        "content": '''
def long_method_with_many_issues(param1, param2, param3, param4, param5, param6):
    """This method has multiple code smells."""
    result = 0

    # Long method smell (many lines)
    for i in range(100):
        if i % 2 == 0:
            if i % 3 == 0:
                if i % 5 == 0:
                    if i % 7 == 0:
                        # Deep nesting smell (5 levels)
                        if i % 11 == 0:
                            result += i

    # More lines to make it long
    data = []
    for i in range(10):
        data.append(i)

    for i in range(10):
        data.append(i)

    for i in range(10):
        data.append(i)

    for i in range(10):
        data.append(i)

    for i in range(10):
        data.append(i)

    # Duplicate code smell
    x = 1
    y = 2
    z = x + y
    result += z

    # More duplicate
    x = 1
    y = 2
    z = x + y
    result += z

    # Even more duplicate
    x = 1
    y = 2
    z = x + y
    result += z

    return result


class VeryLargeClass:
    """This class has too many methods."""

    def method_1(self): pass
    def method_2(self): pass
    def method_3(self): pass
    def method_4(self): pass
    def method_5(self): pass
    def method_6(self): pass
    def method_7(self): pass
    def method_8(self): pass
    def method_9(self): pass
    def method_10(self): pass
    def method_11(self): pass
    def method_12(self): pass
    def method_13(self): pass
    def method_14(self): pass
    def method_15(self): pass
    def method_16(self): pass
    def method_17(self): pass
    def method_18(self): pass
    def method_19(self): pass
    def method_20(self): pass
    def method_21(self): pass
    def method_22(self): pass
''',
    }

    # Detect smells
    report = detector.detect([smelly_code])

    # Print report
    print_smell_report(report)


def example_clean_code():
    """Example 3: Clean code with no smells."""
    print("\n🚀 EXAMPLE 3: Clean Code (No Smells)\n")

    detector = CodeSmellDetector()

    clean_code = {
        "path": "clean_code.py",
        "content": '''
"""Well-written module with no code smells."""

class Calculator:
    """Simple calculator with clean methods."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b

    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b

    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


def process_data(items):
    """Process a list of items."""
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
''',
    }

    # Detect smells
    report = detector.detect([clean_code])

    # Print report
    print_smell_report(report)


def example_custom_thresholds():
    """Example 4: Use detector with adjusted thresholds."""
    print("\n🚀 EXAMPLE 4: Custom Thresholds\n")

    # Create detector with stricter thresholds
    detector = CodeSmellDetector()
    detector.max_method_lines = 30  # Stricter than default 50
    detector.max_parameters = 3  # Stricter than default 5
    detector.max_class_methods = 10  # Stricter than default 20

    code = {
        "path": "moderate_code.py",
        "content": '''
def method_with_moderate_length(a, b, c, d):
    """This method is 35 lines - OK with default, bad with strict."""
    result = 0
    for i in range(10):
        result += i

    for i in range(10):
        result += i

    for i in range(10):
        result += i

    for i in range(10):
        result += i

    for i in range(10):
        result += i

    for i in range(10):
        result += i

    for i in range(10):
        result += i

    return result
''',
    }

    # Detect smells with custom thresholds
    report = detector.detect([code])

    # Print report
    print_smell_report(report)


def example_fsa_states():
    """Example 5: Observe FSA state transitions."""
    print("\n🚀 EXAMPLE 5: FSA State Transitions\n")

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    detector = CodeSmellDetector()

    print("Initial State:", detector.current_state)
    print("\nRunning detection FSA...\n")

    code = {
        "path": "test.py",
        "content": "def hello(): print('Hello')\n",
    }

    report = detector.detect([code])

    print("\nFinal State:", detector.current_state)
    print("State History:", " -> ".join(str(s) for s in detector.state_history))
    print(f"\nResult: {report.total_smells} smells detected")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("CODE SMELL DETECTOR FSA - MINIMAL EXAMPLES")
    print("=" * 80)

    examples = [
        example_basic_detection,
        example_inline_smelly_code,
        example_clean_code,
        example_custom_thresholds,
        example_fsa_states,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Error in {example_func.__name__}: {e}\n")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

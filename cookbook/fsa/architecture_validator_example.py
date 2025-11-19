"""
Minimal example of the Architecture Validator FSA.

This script demonstrates how to use the ArchitectureValidator to check
system design patterns, layer separation, and detect violations.
"""

import sys
from pathlib import Path

# Add parent directory to path to import agno
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs" / "agno"))

from agno.fsa import ArchitectureValidator, LayerDefinition, print_architecture_report


def example_basic_validation():
    """Example 1: Basic architecture validation with default layers."""
    print("\n🚀 EXAMPLE 1: Basic Architecture Validation\n")

    # Create validator with default 3-tier architecture
    validator = ArchitectureValidator()

    # Get sample architecture files
    sample_dir = Path(__file__).parent / "sample_architecture"
    code_files = [
        str(sample_dir / "ui" / "user_controller.py"),
        str(sample_dir / "ui" / "bad_controller.py"),
        str(sample_dir / "services" / "user_service.py"),
        str(sample_dir / "repositories" / "user_repository.py"),
    ]

    # Validate architecture
    report = validator.validate(code_files)

    # Print report
    print_architecture_report(report)


def example_custom_layers():
    """Example 2: Validation with custom layer definitions."""
    print("\n🚀 EXAMPLE 2: Custom Layer Definitions\n")

    # Define custom layers
    custom_layers = [
        LayerDefinition(
            name="api",
            paths=["api", "controllers"],
            allowed_dependencies=["domain", "infrastructure"],
        ),
        LayerDefinition(
            name="domain",
            paths=["domain", "models", "services"],
            allowed_dependencies=[],  # Domain should be independent
        ),
        LayerDefinition(
            name="infrastructure",
            paths=["infrastructure", "repositories", "database"],
            allowed_dependencies=["domain"],
        ),
    ]

    # Create validator with custom layers
    validator = ArchitectureValidator(layers=custom_layers)

    # Get sample files
    sample_dir = Path(__file__).parent / "sample_architecture"
    code_files = [
        str(sample_dir / "ui" / "user_controller.py"),
        str(sample_dir / "services" / "user_service.py"),
    ]

    # Validate
    report = validator.validate(code_files)

    # Print report
    print_architecture_report(report)


def example_inline_code():
    """Example 3: Validation with inline code."""
    print("\n🚀 EXAMPLE 3: Inline Code Validation\n")

    validator = ArchitectureValidator()

    # Define code files inline
    code_files = [
        {
            "path": "ui/view.py",
            "content": '''
import sqlalchemy  # Architecture violation!

class UserView:
    def __init__(self):
        self.db = sqlalchemy.create_engine("sqlite://")

    def render(self):
        pass
''',
        },
        {
            "path": "services/service.py",
            "content": '''
class UserService:
    def process(self):
        pass

    def validate(self):
        pass

    def transform(self):
        pass
''',
        },
    ]

    # Validate
    report = validator.validate(code_files)

    # Print report
    print_architecture_report(report)


def example_god_class_detection():
    """Example 4: Detecting god classes (anti-pattern)."""
    print("\n🚀 EXAMPLE 4: God Class Detection\n")

    validator = ArchitectureValidator()

    # Create a god class example
    methods = "\n    ".join([f"def method_{i}(self): pass" for i in range(25)])

    code_files = [
        {
            "path": "services/god_class.py",
            "content": f'''
class GodClass:
    """A class with too many responsibilities."""

    {methods}
''',
        }
    ]

    # Validate
    report = validator.validate(code_files)

    # Print report
    print_architecture_report(report)


def example_fsa_states():
    """Example 5: Observing FSA state transitions."""
    print("\n🚀 EXAMPLE 5: FSA State Transitions\n")

    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    validator = ArchitectureValidator()

    print("Initial State:", validator.current_state)
    print("\nRunning validation FSA...\n")

    sample_dir = Path(__file__).parent / "sample_architecture"
    code_files = [str(sample_dir / "ui" / "user_controller.py")]

    report = validator.validate(code_files)

    print("\nFinal State:", validator.current_state)
    print("State History:", " -> ".join(str(s) for s in validator.state_history))
    print(f"\nValidation Result: {len(report.errors)} errors, {len(report.warnings)} warnings")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ARCHITECTURE VALIDATOR FSA - MINIMAL EXAMPLES")
    print("=" * 80)

    examples = [
        example_basic_validation,
        example_custom_layers,
        example_inline_code,
        example_god_class_detection,
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

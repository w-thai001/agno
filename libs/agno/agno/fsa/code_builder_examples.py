"""
Examples for Multi-Step Code Builder with FSA.

Demonstrates various code generation workflows and patterns.
"""

import asyncio
from pathlib import Path
import tempfile

from agno.fsa.code_builder import (
    BuildPlan,
    BuildStep,
    CodeLanguage,
    MultiStepCodeBuilder,
    TemplateCodeGenerator,
    PythonSyntaxValidator,
    ImportValidator,
)


async def example_simple_module():
    """Example: Build a simple Python module."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Simple Python Module")
    print("=" * 60)

    # Create build plan
    plan = BuildPlan(
        name="math_utils",
        description="Mathematical utility functions",
        language=CodeLanguage.PYTHON,
    )

    plan.add_artifact(
        "math_utils.py",
        "Mathematical utility functions",
    )

    plan.add_artifact(
        "__init__.py",
        "Package initialization",
    )

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="math_utils_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Add validators
    builder.add_validator(PythonSyntaxValidator())
    builder.add_validator(ImportValidator())

    # Add template generator
    templates = {
        "math_utils": '''"""
Mathematical utility functions.
"""

def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def power(base: float, exponent: float) -> float:
    """Raise base to exponent."""
    return base ** exponent
''',
        "init": '''"""
Math utilities package.
"""

from .math_utils import add, multiply, power

__all__ = ["add", "multiply", "power"]
''',
    }

    generator = TemplateCodeGenerator(templates)
    builder.add_generator("template", generator)

    # Update plan with templates
    plan.artifacts[0]["template"] = "math_utils"
    plan.artifacts[1]["template"] = "init"

    # Execute build
    result = await builder.build()

    # Print results
    print(f"\nBuild success: {result['success']}")
    print(f"Output directory: {result['output_dir']}")
    print(f"\nGenerated files:")
    for path, info in result['artifacts'].items():
        status = "✓" if info['is_valid'] else "✗"
        print(f"  {status} {path}")
        if info['errors']:
            for error in info['errors']:
                print(f"      Error: {error}")

    return result


async def example_multi_file_project():
    """Example: Build a multi-file project with dependencies."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Multi-File Project")
    print("=" * 60)

    # Create build plan
    plan = BuildPlan(
        name="data_processor",
        description="Data processing library",
        language=CodeLanguage.PYTHON,
    )

    plan.add_artifact(
        "models.py",
        "Data models",
    )

    plan.add_artifact(
        "processors.py",
        "Data processors",
        dependencies=["models.py"],
    )

    plan.add_artifact(
        "validators.py",
        "Data validators",
        dependencies=["models.py"],
    )

    plan.add_artifact(
        "main.py",
        "Main entry point",
        dependencies=["models.py", "processors.py", "validators.py"],
    )

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="data_processor_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Add validators
    builder.add_validator(PythonSyntaxValidator())

    # Execute build (will create scaffolding)
    result = await builder.build()

    # Print results
    print(f"\nBuild success: {result['success']}")
    print(f"Generated {len(result['artifacts'])} files")

    # Show dependency order
    print("\nDependency order:")
    for artifact_spec in plan.artifacts:
        deps = ", ".join(artifact_spec.get("dependencies", [])) or "None"
        print(f"  {artifact_spec['path']} depends on: {deps}")

    return result


async def example_custom_build_steps():
    """Example: Custom build steps."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Custom Build Steps")
    print("=" * 60)

    # Create build plan with custom steps
    plan = BuildPlan(
        name="custom_build",
        description="Custom build workflow",
        language=CodeLanguage.PYTHON,
        steps=[
            BuildStep.PLAN,
            BuildStep.SCAFFOLD,
            BuildStep.IMPLEMENT,
            BuildStep.VALIDATE,
            BuildStep.FINALIZE,
            # Skip optimization and testing
        ],
    )

    plan.add_artifact("app.py", "Application entry point")

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="custom_build_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Execute build
    result = await builder.build()

    # Print which steps were executed
    print("\nExecuted steps:")
    for step_id, step_result in result['steps'].items():
        status = "✓" if step_result['status'] == 'completed' else "✗"
        print(f"  {status} {step_id}: {step_result['duration']:.2f}s")

    return result


async def example_validation_errors():
    """Example: Handling validation errors."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Validation Errors")
    print("=" * 60)

    # Create build plan
    plan = BuildPlan(
        name="invalid_code",
        description="Example with validation errors",
        language=CodeLanguage.PYTHON,
    )

    plan.add_artifact("broken.py", "Code with syntax errors")

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="invalid_code_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Add template with syntax error
    templates = {
        "broken": '''
def broken_function(:  # Syntax error
    print("This won't parse")
    return
''',
    }

    generator = TemplateCodeGenerator(templates)
    builder.add_generator("template", generator)
    plan.artifacts[0]["template"] = "broken"

    # Execute build
    result = await builder.build()

    # Show errors
    print(f"\nBuild success: {result['success']}")
    print("\nValidation errors:")
    for path, info in result['artifacts'].items():
        if info['errors']:
            print(f"  {path}:")
            for error in info['errors']:
                print(f"    - {error}")

    return result


async def example_build_with_requirements():
    """Example: Build with requirements and constraints."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Build with Requirements")
    print("=" * 60)

    # Create build plan
    plan = BuildPlan(
        name="api_client",
        description="HTTP API client library",
        language=CodeLanguage.PYTHON,
    )

    # Add requirements
    plan.add_requirement("Must support GET, POST, PUT, DELETE methods")
    plan.add_requirement("Must handle authentication")
    plan.add_requirement("Must include error handling")
    plan.add_requirement("Must be async-compatible")

    # Add constraints
    plan.add_constraint("No external dependencies except standard library")
    plan.add_constraint("Must be Python 3.8+ compatible")

    # Add artifacts
    plan.add_artifact("client.py", "API client implementation")
    plan.add_artifact("auth.py", "Authentication handlers")
    plan.add_artifact("exceptions.py", "Custom exceptions")

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="api_client_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Execute build
    result = await builder.build()

    # Print plan details
    print("\nRequirements:")
    for req in plan.requirements:
        print(f"  - {req}")

    print("\nConstraints:")
    for constraint in plan.constraints:
        print(f"  - {constraint}")

    print(f"\nBuild success: {result['success']}")
    print(f"Generated {len(result['artifacts'])} files")

    return result


async def example_incremental_build():
    """Example: Incremental build with context access."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Incremental Build")
    print("=" * 60)

    # Create build plan
    plan = BuildPlan(
        name="incremental",
        description="Incremental build example",
        language=CodeLanguage.PYTHON,
    )

    plan.add_artifact("version.py", "Version information")
    plan.add_artifact("config.py", "Configuration")

    # Create builder
    output_dir = Path(tempfile.mkdtemp(prefix="incremental_"))
    builder = MultiStepCodeBuilder(plan, output_dir)

    # Execute build
    result = await builder.build()

    # Access build context
    context = builder.get_context()

    print(f"\nBuild metadata:")
    for key, value in context.metadata.items():
        print(f"  {key}: {value}")

    print(f"\nGenerated artifacts:")
    for path, artifact in context.artifacts.items():
        print(f"  {path}: {len(artifact.content)} bytes")

    return result


async def run_all_examples():
    """Run all examples."""
    await example_simple_module()
    await example_multi_file_project()
    await example_custom_build_steps()
    await example_validation_errors()
    await example_build_with_requirements()
    await example_incremental_build()


if __name__ == "__main__":
    asyncio.run(run_all_examples())

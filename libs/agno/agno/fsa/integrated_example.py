"""
Integrated FSA Example - All Components Working Together

This example demonstrates how all 5 FSA components can work together
in a complete development workflow:

1. Task Deconstruction (MLA)
2. Code Building (Multi-Step)
3. Code Optimization (RSI)
4. Quality Validation
5. Workflow Orchestration

This represents a complete automated development pipeline.
"""

import asyncio
from pathlib import Path
import tempfile

from agno.fsa.orchestrator import FSA, FSAContext, FSAExecutor, FSAOrchestrator
from agno.fsa.code_builder import (
    BuildPlan,
    CodeLanguage,
    MultiStepCodeBuilder,
    TemplateCodeGenerator,
)
from agno.fsa.mla_deconstructor import (
    Goal,
    Task,
    TaskCategory,
    TaskComplexity,
    ImpactMetrics,
    MLATaskDeconstructor,
)
from agno.fsa.rsi_optimizer import RSICodeOptimizer
from agno.fsa.quality_validator import QualityValidator, QualityGate


# Custom FSA Executors for Integration
# =====================================

class TaskDeconstructionExecutor(FSAExecutor):
    """FSA executor for task deconstruction."""

    async def execute(self, context: FSAContext):
        """Deconstruct project goal into tasks."""
        print("\n🎯 PHASE 1: Task Deconstruction (MLA)")
        print("=" * 60)

        # Create goal
        goal = Goal(
            title="Build Python Utility Library",
            description="Create a reusable Python utility library with common functions",
        )

        goal.add_success_criterion("Library is well-documented")
        goal.add_success_criterion("Code meets quality standards")
        goal.add_success_criterion("Includes comprehensive tests")

        # Add high-level tasks
        design_task = Task(
            id="design",
            title="Design Library Architecture",
            category=TaskCategory.PLANNING,
            complexity=TaskComplexity.MODERATE,
            estimated_hours=4.0,
            impact=ImpactMetrics(
                direct_value=8.0,
                reusability=9.0,
                enablement=10.0,
                strategic_value=9.0,
            ),
        )

        implement_task = Task(
            id="implement",
            title="Implement Core Functions",
            category=TaskCategory.IMPLEMENTATION,
            complexity=TaskComplexity.COMPLEX,
            estimated_hours=16.0,
            impact=ImpactMetrics(
                direct_value=10.0,
                reusability=8.0,
            ),
        )
        implement_task.add_dependency("design")

        test_task = Task(
            id="test",
            title="Write Tests",
            category=TaskCategory.TESTING,
            complexity=TaskComplexity.MODERATE,
            estimated_hours=8.0,
            impact=ImpactMetrics(
                direct_value=7.0,
                risk_reduction=10.0,
            ),
        )
        test_task.add_dependency("implement")

        goal.add_task(design_task)
        goal.add_task(implement_task)
        goal.add_task(test_task)

        # Deconstruct
        deconstructor = MLATaskDeconstructor()
        result = deconstructor.deconstruct(goal, auto_generate_subtasks=True)

        result.print_summary()

        # Store in context
        context.set("task_deconstruction", result)
        context.set("build_plan_ready", True)

        return {
            "total_tasks": len(result.all_tasks),
            "high_leverage_tasks": len(result.get_high_leverage_tasks()),
            "alignment_score": result.alignment_score,
        }


class CodeBuildingExecutor(FSAExecutor):
    """FSA executor for code building."""

    def validate(self, context: FSAContext) -> bool:
        """Validate that task deconstruction is complete."""
        return context.has("build_plan_ready")

    async def execute(self, context: FSAContext):
        """Build code based on deconstructed tasks."""
        print("\n🏗️  PHASE 2: Code Building (Multi-Step)")
        print("=" * 60)

        # Create build plan
        plan = BuildPlan(
            name="python_utils",
            description="Python utility library",
            language=CodeLanguage.PYTHON,
        )

        plan.add_artifact(
            "utils/string_utils.py",
            "String manipulation utilities",
        )

        plan.add_artifact(
            "utils/math_utils.py",
            "Mathematical utilities",
        )

        plan.add_artifact(
            "utils/__init__.py",
            "Package initialization",
        )

        plan.add_artifact(
            "tests/test_string_utils.py",
            "Tests for string utilities",
        )

        # Create builder
        output_dir = Path(tempfile.mkdtemp(prefix="python_utils_"))
        builder = MultiStepCodeBuilder(plan, output_dir)

        # Add templates
        templates = {
            "string_utils": '''"""
String manipulation utilities.
"""

def capitalize_words(text: str) -> str:
    """Capitalize first letter of each word."""
    return " ".join(word.capitalize() for word in text.split())


def reverse_string(text: str) -> str:
    """Reverse a string."""
    return text[::-1]


def is_palindrome(text: str) -> bool:
    """Check if text is a palindrome."""
    cleaned = "".join(c.lower() for c in text if c.isalnum())
    return cleaned == cleaned[::-1]
''',
            "math_utils": '''"""
Mathematical utilities.
"""

def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n: int) -> bool:
    """Check if n is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
''',
            "init": '''"""
Python utilities library.
"""

from .string_utils import capitalize_words, reverse_string, is_palindrome
from .math_utils import factorial, fibonacci, is_prime

__all__ = [
    "capitalize_words",
    "reverse_string",
    "is_palindrome",
    "factorial",
    "fibonacci",
    "is_prime",
]

__version__ = "1.0.0"
''',
            "test_string_utils": '''"""
Tests for string utilities.
"""

from utils.string_utils import capitalize_words, reverse_string, is_palindrome


def test_capitalize_words():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("HELLO WORLD") == "Hello World"


def test_reverse_string():
    assert reverse_string("hello") == "olleh"
    assert reverse_string("abc") == "cba"


def test_is_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("hello") == False
    assert is_palindrome("A man a plan a canal Panama") == True
''',
        }

        generator = TemplateCodeGenerator(templates)
        builder.add_generator("template", generator)

        # Assign templates
        plan.artifacts[0]["template"] = "string_utils"
        plan.artifacts[1]["template"] = "math_utils"
        plan.artifacts[2]["template"] = "init"
        plan.artifacts[3]["template"] = "test_string_utils"

        # Build
        result = await builder.build()

        print(f"\n✓ Build {'succeeded' if result['success'] else 'failed'}")
        print(f"  Output directory: {result['output_dir']}")
        print(f"  Artifacts generated: {len(result['artifacts'])}")

        # Store in context
        context.set("build_result", result)
        context.set("code_artifacts", builder.get_context().artifacts)

        return result


class CodeOptimizationExecutor(FSAExecutor):
    """FSA executor for code optimization."""

    def validate(self, context: FSAContext) -> bool:
        """Validate that code building is complete."""
        return context.has("code_artifacts")

    async def execute(self, context: FSAContext):
        """Optimize generated code."""
        print("\n⚡ PHASE 3: Code Optimization (RSI)")
        print("=" * 60)

        artifacts = context.get("code_artifacts")

        # Optimize each artifact
        optimizer = RSICodeOptimizer()
        optimization_results = {}

        for path, artifact in artifacts.items():
            if path.endswith(".py") and not path.endswith("__init__.py"):
                print(f"\nOptimizing {path}...")

                result = await optimizer.optimize(
                    code=artifact.content,
                    max_iterations=3,
                )

                optimization_results[path] = result

                print(f"  Quality improvement: {result.improvement['quality_improvement']:+.1f}")

                # Update artifact with optimized code
                artifact.content = result.optimized_code

        # Store in context
        context.set("optimization_results", optimization_results)

        return {
            "optimized_files": len(optimization_results),
            "average_improvement": sum(
                r.improvement["quality_improvement"]
                for r in optimization_results.values()
            ) / max(len(optimization_results), 1),
        }


class QualityValidationExecutor(FSAExecutor):
    """FSA executor for quality validation."""

    def validate(self, context: FSAContext) -> bool:
        """Validate that optimization is complete."""
        return context.has("optimization_results")

    async def execute(self, context: FSAContext):
        """Validate code quality."""
        print("\n✅ PHASE 4: Quality Validation")
        print("=" * 60)

        artifacts = context.get("code_artifacts")

        # Create quality gate
        gate = QualityGate(
            max_critical=0,
            max_errors=0,
            max_warnings=5,
            min_quality_score=75.0,
        )

        # Validate each artifact
        validator = QualityValidator()
        validation_results = {}
        all_passed = True

        for path, artifact in artifacts.items():
            if path.endswith(".py"):
                result = validator.validate(
                    artifact.content,
                    file_path=path,
                    quality_gate=gate,
                )

                validation_results[path] = result

                passed = result.quality_score >= gate.min_quality_score
                status = "✓" if passed else "✗"
                all_passed = all_passed and passed

                print(f"  {status} {path}: {result.quality_score:.1f}/100")

        print(f"\n{'✓' if all_passed else '✗'} Overall quality gate: {'PASSED' if all_passed else 'FAILED'}")

        # Store in context
        context.set("validation_results", validation_results)
        context.set("quality_gate_passed", all_passed)

        return {
            "files_validated": len(validation_results),
            "quality_gate_passed": all_passed,
            "average_quality": sum(
                r.quality_score for r in validation_results.values()
            ) / max(len(validation_results), 1),
        }


class FinalReportExecutor(FSAExecutor):
    """FSA executor for final reporting."""

    async def execute(self, context: FSAContext):
        """Generate final report."""
        print("\n📊 PHASE 5: Final Report")
        print("=" * 60)

        # Gather results
        task_result = context.get("task_deconstruction")
        build_result = context.get("build_result")
        opt_results = context.get("optimization_results")
        val_results = context.get("validation_results")

        print("\n🎯 Task Deconstruction:")
        print(f"  Total tasks: {len(task_result.all_tasks)}")
        print(f"  High-leverage tasks: {len(task_result.get_high_leverage_tasks())}")
        print(f"  Goal alignment: {task_result.alignment_score:.1f}/100")

        print("\n🏗️  Code Building:")
        print(f"  Artifacts generated: {len(build_result['artifacts'])}")
        print(f"  Build success: {build_result['success']}")
        print(f"  Output: {build_result['output_dir']}")

        print("\n⚡ Code Optimization:")
        total_improvement = sum(
            r.improvement["quality_improvement"]
            for r in opt_results.values()
        )
        print(f"  Files optimized: {len(opt_results)}")
        print(f"  Average improvement: {total_improvement / max(len(opt_results), 1):.1f} points")

        print("\n✅ Quality Validation:")
        avg_quality = sum(r.quality_score for r in val_results.values()) / max(len(val_results), 1)
        print(f"  Files validated: {len(val_results)}")
        print(f"  Average quality: {avg_quality:.1f}/100")
        print(f"  Quality gate: {'✓ PASSED' if context.get('quality_gate_passed') else '✗ FAILED'}")

        print("\n" + "=" * 60)
        print("🎉 COMPLETE DEVELOPMENT WORKFLOW FINISHED!")
        print("=" * 60)

        return {
            "workflow_completed": True,
            "overall_success": build_result['success'] and context.get('quality_gate_passed'),
        }


# Main Integration
# ================

async def run_integrated_workflow():
    """Run complete integrated FSA workflow."""
    print("\n" + "=" * 60)
    print("INTEGRATED FSA WORKFLOW")
    print("Demonstrating all 5 FSA components working together")
    print("=" * 60)

    # Create orchestrator
    orchestrator = FSAOrchestrator()

    # Define FSAs in dependency order
    task_decon_fsa = FSA(
        id="task_deconstruction",
        name="Task Deconstruction (MLA)",
        executor=TaskDeconstructionExecutor(),
        priority=100,
    )

    code_build_fsa = FSA(
        id="code_building",
        name="Code Building (Multi-Step)",
        executor=CodeBuildingExecutor(),
        dependencies=["task_deconstruction"],
        priority=90,
    )

    optimization_fsa = FSA(
        id="optimization",
        name="Code Optimization (RSI)",
        executor=CodeOptimizationExecutor(),
        dependencies=["code_building"],
        priority=80,
    )

    validation_fsa = FSA(
        id="validation",
        name="Quality Validation",
        executor=QualityValidationExecutor(),
        dependencies=["optimization"],
        priority=70,
    )

    report_fsa = FSA(
        id="final_report",
        name="Final Report",
        executor=FinalReportExecutor(),
        dependencies=["validation"],
        priority=60,
    )

    # Add FSAs to orchestrator
    orchestrator.add_fsa(task_decon_fsa)
    orchestrator.add_fsa(code_build_fsa)
    orchestrator.add_fsa(optimization_fsa)
    orchestrator.add_fsa(validation_fsa)
    orchestrator.add_fsa(report_fsa)

    # Execute workflow
    results = await orchestrator.execute()

    # Show orchestration summary
    print("\n" + "=" * 60)
    print("ORCHESTRATION SUMMARY")
    print("=" * 60)

    summary = orchestrator.get_summary()
    print(f"Total FSAs: {summary['total_fsas']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total duration: {summary['total_duration']:.2f}s")

    print("\nFSA Execution Timeline:")
    for fsa_id, result in results.items():
        status_icon = "✓" if result.success else "✗"
        print(f"  {status_icon} {fsa_id}: {result.duration:.2f}s")

    return results


if __name__ == "__main__":
    # Run the integrated workflow
    results = asyncio.run(run_integrated_workflow())

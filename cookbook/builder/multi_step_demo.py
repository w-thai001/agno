"""
FSA-3.1: Multi-Step Code Builder - Demonstration

This demo showcases the Multi-Step Code Builder orchestrating all FSA components:
- FSA-1.1: Prompt Optimizer - Optimizes prompts for each step
- FSA-1.2: Code Template Library - Selects appropriate templates
- FSA-2.1: Code Quality Validator - Validates generated code
- FSA-2.2: Multi-Model Orchestrator - Routes tasks to optimal models

The demo builds a complete REST API with database project step-by-step.

Run: python cookbook/builder/multi_step_demo.py
"""

from agno.builder import MultiStepCodeBuilder


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_step(step, index: int, total: int):
    """Print step information."""
    status_icons = {
        "pending": "⏸",
        "in_progress": "▶",
        "completed": "✓",
        "failed": "✗",
        "rolled_back": "↩",
    }

    icon = status_icons.get(step.status.value, "•")
    quality = f" (quality: {step.quality_score}/100)" if step.quality_score else ""

    print(f"{icon} Step {index}/{total}: {step.name}")
    print(f"   Type: {step.step_type.value}")
    print(f"   Status: {step.status.value.upper()}{quality}")

    if step.dependencies:
        print(f"   Dependencies: {', '.join(step.dependencies)}")

    if step.execution_time_ms:
        print(f"   Execution time: {step.execution_time_ms:.0f}ms")

    if step.error:
        print(f"   Error: {step.error}")

    print()


def demo_task_decomposition():
    """Demonstrate task decomposition."""
    print_section("Demo 1: Task Decomposition")

    builder = MultiStepCodeBuilder()

    requirements = """
    Build a REST API for a blog platform with the following features:
    - User authentication and authorization
    - CRUD operations for blog posts
    - Database storage with SQLite
    - API endpoints for posts, users, and comments
    - Error handling and validation
    - Unit tests for all endpoints
    """

    print("Project Requirements:")
    print(requirements)
    print("\n" + "-" * 80 + "\n")

    steps = builder.decomposeTask(requirements, "python")

    print(f"Task decomposed into {len(steps)} sequential steps:\n")

    for i, step in enumerate(steps, 1):
        print(f"{i}. {step.name}")
        print(f"   Type: {step.step_type.value}")
        print(f"   Description: {step.description}")
        if step.dependencies:
            print(f"   Depends on: {', '.join(step.dependencies)}")
        if step.template_ids:
            print(f"   Templates: {', '.join(step.template_ids)}")
        print()


def demo_simple_project():
    """Demonstrate building a simple project."""
    print_section("Demo 2: Simple API Project Build")

    builder = MultiStepCodeBuilder(
        use_orchestrator=False,  # Disable FSA-2.2 for demo (no API key needed)
        min_quality_score=70,
        enable_rollback=True,
    )

    requirements = """
    Build a simple REST API with:
    - Database connection for user data
    - API endpoint to get users
    - Error handling
    """

    print("Building project: Simple REST API")
    print("-" * 80)

    result = builder.buildProject(
        requirements=requirements,
        project_name="simple_api",
        language="python",
    )

    print(f"\nBuild Result: {result.summary}\n")
    print("-" * 80)

    # Show all steps
    print(f"\nStep Execution Details:\n")
    for i, step in enumerate(result.steps, 1):
        print_step(step, i, len(result.steps))

    # Show generated files
    if result.generated_files:
        print("-" * 80)
        print(f"\nGenerated Files ({len(result.generated_files)}):\n")
        for filename, code in result.generated_files.items():
            print(f"📄 {filename}")
            print(f"   Length: {len(code)} characters")
            print(f"   Preview: {code[:100].strip()}...")
            print()


def demo_complex_project():
    """Demonstrate building a complex project with database."""
    print_section("Demo 3: Complex REST API with Database")

    builder = MultiStepCodeBuilder(
        use_orchestrator=False,
        min_quality_score=70,
        enable_rollback=True,
    )

    requirements = """
    Build a complete REST API for a task management system:
    - SQLite database with tasks table (id, title, description, status, created_at)
    - Database connection management with connection pooling
    - API endpoints: GET /tasks, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id
    - Input validation and error handling
    - Business logic for task status transitions
    - Comprehensive unit tests
    """

    print("Building project: Task Management API")
    print("Requirements:")
    print(requirements)
    print("\n" + "-" * 80 + "\n")

    result = builder.buildProject(
        requirements=requirements,
        project_name="task_management_api",
        language="python",
    )

    print(f"\n{'=' * 80}")
    print(f"  BUILD SUMMARY")
    print(f"{'=' * 80}\n")

    print(result.summary)
    print()

    # Statistics
    print(f"Total Steps: {result.total_steps}")
    print(f"Completed: {result.completed_steps}")
    print(f"Failed: {result.failed_steps}")
    print(f"Overall Quality Score: {result.overall_quality_score:.1f}/100")
    print(f"Total Execution Time: {result.total_execution_time_ms:.0f}ms")
    print(f"Success: {'YES ✓' if result.success else 'NO ✗'}")

    # Show step progression
    print(f"\n{'=' * 80}")
    print(f"  STEP EXECUTION TIMELINE")
    print(f"{'=' * 80}\n")

    for i, step in enumerate(result.steps, 1):
        print_step(step, i, len(result.steps))

    # Show validation details for completed steps
    print(f"{'=' * 80}")
    print(f"  QUALITY VALIDATION DETAILS")
    print(f"{'=' * 80}\n")

    for step in result.steps:
        if step.status.value == "completed" and step.validation_result:
            validation = step.validation_result
            print(f"📊 {step.name}")
            print(f"   Overall: {validation.report.overall_score}/100")

            for dim_name, dim_score in validation.report.dimensions.items():
                status = "✓" if dim_score.score >= 70 else "⚠" if dim_score.score >= 50 else "✗"
                print(f"   {status} {dim_name}: {dim_score.score}/100")

            if validation.top_issues:
                print(f"   Issues: {len(validation.top_issues)}")
                for issue in validation.top_issues[:2]:
                    print(f"     - {issue.severity.value}: {issue.message}")

            print()

    # Show generated files with previews
    print(f"{'=' * 80}")
    print(f"  GENERATED FILES")
    print(f"{'=' * 80}\n")

    if result.generated_files:
        for filename, code in result.generated_files.items():
            print(f"📄 {filename}")
            print(f"   Size: {len(code)} characters")
            print(f"   Lines: {len(code.splitlines())}")
            print(f"\n   Preview:")
            lines = code.splitlines()[:10]
            for line in lines:
                print(f"   {line}")
            if len(code.splitlines()) > 10:
                print(f"   ... ({len(code.splitlines()) - 10} more lines)")
            print()
    else:
        print("No files generated")


def demo_fsa_integration():
    """Demonstrate integration with all FSA components."""
    print_section("Demo 4: FSA Component Integration")

    builder = MultiStepCodeBuilder(
        use_orchestrator=False,
        min_quality_score=80,
    )

    print("FSA Components Integrated:\n")
    print("1. FSA-1.1: Prompt Optimizer")
    print("   - Optimizes prompts for each build step")
    print("   - Generates structured analysis requests")
    print("   - Available for AI-assisted code generation")
    print()

    print("2. FSA-1.2: Code Template Library")
    print("   - Provides high-quality code templates")
    print("   - 8 built-in templates (Python, JavaScript)")
    print("   - Template selection based on step type")
    print()

    print("3. FSA-2.1: Code Quality Validator")
    print("   - Validates all generated code")
    print("   - Multi-dimensional analysis (syntax, security, style, performance)")
    print("   - Enforces minimum quality thresholds")
    print()

    print("4. FSA-2.2: Multi-Model Orchestrator")
    print("   - Routes tasks to optimal Claude models")
    print("   - Cost optimization")
    print("   - Performance tracking")
    print("   - (Disabled in demo - requires API key)")
    print()

    print("-" * 80)
    print("\nBuilding sample project to demonstrate integration...\n")

    requirements = "Build a REST API with database storage and error handling"

    result = builder.buildProject(
        requirements=requirements,
        project_name="fsa_integration_demo",
        language="python",
    )

    print(f"\nIntegration Test Result: {result.summary}\n")

    # Show how each FSA was used
    print("FSA Component Usage:\n")

    for i, step in enumerate(result.steps, 1):
        print(f"Step {i}: {step.name}")

        # FSA-1.2 usage
        if step.template_ids:
            print(f"  FSA-1.2: Used templates: {', '.join(step.template_ids)}")

        # FSA-2.1 usage
        if step.validation_result:
            print(
                f"  FSA-2.1: Validated (score: {step.validation_result.report.overall_score}/100)"
            )

        print()


def demo_statistics():
    """Demonstrate build statistics tracking."""
    print_section("Demo 5: Build Statistics & Tracking")

    builder = MultiStepCodeBuilder(min_quality_score=75)

    # Build multiple projects
    projects = [
        ("Simple API", "Build a REST API with 2 endpoints"),
        ("Database Project", "Build database schema and connection utilities"),
        ("Complete App", "Build a REST API with database, auth, and tests"),
    ]

    print("Building multiple projects to gather statistics...\n")

    for project_name, requirements in projects:
        print(f"Building: {project_name}...")
        result = builder.buildProject(
            requirements=requirements,
            project_name=project_name.lower().replace(" ", "_"),
            language="python",
        )
        print(f"  Result: {result.completed_steps}/{result.total_steps} steps completed")
        print(f"  Quality: {result.overall_quality_score:.1f}/100\n")

    # Get statistics
    stats = builder.get_build_statistics()

    print("-" * 80)
    print("\nOverall Build Statistics:")
    print("-" * 80)
    print(f"Total Steps Executed: {stats['total_steps_executed']}")
    print(f"Completed Steps: {stats['completed_steps']}")
    print(f"Failed Steps: {stats['failed_steps']}")
    print(f"Success Rate: {stats['success_rate']*100:.1f}%")
    print(f"Average Quality Score: {stats['average_quality_score']:.1f}/100")


def demo_quality_threshold():
    """Demonstrate quality threshold enforcement."""
    print_section("Demo 6: Quality Threshold Enforcement")

    print("Testing with different quality thresholds:\n")

    thresholds = [50, 70, 90]
    requirements = "Build a simple API with database connection"

    for threshold in thresholds:
        print(f"Threshold: {threshold}/100")
        print("-" * 40)

        builder = MultiStepCodeBuilder(min_quality_score=threshold)
        result = builder.buildProject(
            requirements=requirements,
            project_name=f"api_threshold_{threshold}",
            language="python",
        )

        print(f"Completed: {result.completed_steps}/{result.total_steps}")
        print(f"Quality: {result.overall_quality_score:.1f}/100")
        print(f"Success: {'YES' if result.success else 'NO'}")
        print()


def main():
    """Run all demos."""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  FSA-3.1: MULTI-STEP CODE BUILDER DEMONSTRATION  ".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\nOrchestrating all FSA components:")
    print("  • FSA-1.1: Prompt Optimizer")
    print("  • FSA-1.2: Code Template Library")
    print("  • FSA-2.1: Code Quality Validator")
    print("  • FSA-2.2: Multi-Model Orchestrator")

    try:
        demo_task_decomposition()
        demo_simple_project()
        demo_complex_project()
        demo_fsa_integration()
        demo_statistics()
        demo_quality_threshold()

        # Final summary
        print_section("Demo Complete!")
        print("The Multi-Step Code Builder successfully demonstrated:")
        print("  ✓ Task decomposition into sequential steps")
        print("  ✓ Integration with FSA-1.2 Code Template Library")
        print("  ✓ Code generation using templates")
        print("  ✓ Validation with FSA-2.1 Code Quality Validator")
        print("  ✓ Quality threshold enforcement")
        print("  ✓ Progress tracking and statistics")
        print("  ✓ Multi-project build capability")
        print("  ✓ Dependency management between steps")
        print("\nKey Features:")
        print("  • buildProject(requirements, project_name) - Build complete projects")
        print("  • decomposeTask(requirements, language) - Break into steps")
        print("  • executeStep(step, budget) - Execute individual steps")
        print("  • validateStep(step) - Validate with FSA-2.1")
        print("  • rollback(steps, from_step) - Rollback capabilities")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

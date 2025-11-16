"""
Examples for MLA Task Deconstructor and Goal Aligner.

Demonstrates task decomposition, prioritization, and goal alignment.
"""

from agno.fsa.mla_deconstructor import (
    Goal,
    Task,
    TaskCategory,
    TaskComplexity,
    ImpactMetrics,
    MLATaskDeconstructor,
)


def example_simple_goal():
    """Example: Simple goal with manual task breakdown."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Simple Goal with Manual Tasks")
    print("=" * 60)

    # Create goal
    goal = Goal(
        title="Build a REST API",
        description="Create a REST API for user management",
    )
    goal.add_success_criterion("API supports CRUD operations")
    goal.add_success_criterion("API is documented with OpenAPI/Swagger")
    goal.add_success_criterion("API includes authentication")

    # Manually add tasks
    task1 = Task(
        id="design_api",
        title="Design API Schema",
        description="Design database schema and API endpoints",
        category=TaskCategory.PLANNING,
        complexity=TaskComplexity.MODERATE,
        estimated_hours=4.0,
        impact=ImpactMetrics(
            direct_value=8.0,
            reusability=7.0,
            enablement=9.0,  # Enables all other tasks
            strategic_value=8.0,
        ),
    )

    task2 = Task(
        id="implement_crud",
        title="Implement CRUD Operations",
        description="Implement Create, Read, Update, Delete endpoints",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=12.0,
        impact=ImpactMetrics(
            direct_value=9.0,
            reusability=6.0,
            enablement=5.0,
        ),
    )
    task2.add_dependency("design_api")

    task3 = Task(
        id="add_auth",
        title="Add Authentication",
        description="Implement JWT-based authentication",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=8.0,
        impact=ImpactMetrics(
            direct_value=10.0,
            reusability=8.0,  # Auth is highly reusable
            strategic_value=9.0,
            risk_reduction=9.0,
        ),
    )
    task3.add_dependency("implement_crud")

    task4 = Task(
        id="write_docs",
        title="Write API Documentation",
        description="Create OpenAPI/Swagger documentation",
        category=TaskCategory.DOCUMENTATION,
        complexity=TaskComplexity.SIMPLE,
        estimated_hours=3.0,
        impact=ImpactMetrics(
            direct_value=6.0,
            reusability=7.0,
            learning_value=5.0,
        ),
    )
    task4.add_dependency("implement_crud")

    goal.add_task(task1)
    goal.add_task(task2)
    goal.add_task(task3)
    goal.add_task(task4)

    # Deconstruct and analyze
    deconstructor = MLATaskDeconstructor()
    result = deconstructor.deconstruct(goal, auto_generate_subtasks=False)

    # Print results
    result.print_summary()

    # Get suggestions
    suggestions = deconstructor.suggest_optimizations(result)
    if suggestions:
        print("\n💡 Optimization Suggestions:")
        for suggestion in suggestions:
            print(f"  - {suggestion}")


def example_auto_decomposition():
    """Example: Automatic task decomposition."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Automatic Task Decomposition")
    print("=" * 60)

    # Create goal with high-level tasks only
    goal = Goal(
        title="Build AI Agent System",
        description="Create a production-ready AI agent framework",
    )
    goal.add_success_criterion("Framework is modular and extensible")
    goal.add_success_criterion("Supports multiple AI models")
    goal.add_success_criterion("Includes monitoring and logging")

    # Add high-level tasks (will be auto-decomposed)
    task1 = Task(
        id="core_framework",
        title="Build Core Framework",
        description="Create the foundational agent framework",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.VERY_COMPLEX,
        estimated_hours=40.0,
        impact=ImpactMetrics(
            direct_value=10.0,
            reusability=10.0,
            enablement=10.0,
            strategic_value=10.0,
        ),
    )

    task2 = Task(
        id="model_integration",
        title="Integrate AI Models",
        description="Add support for multiple AI model providers",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=24.0,
        impact=ImpactMetrics(
            direct_value=9.0,
            reusability=9.0,
            strategic_value=8.0,
        ),
    )
    task2.add_dependency("core_framework")

    task3 = Task(
        id="monitoring",
        title="Add Monitoring and Logging",
        description="Implement comprehensive monitoring and logging",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=16.0,
        impact=ImpactMetrics(
            direct_value=7.0,
            reusability=8.0,
            risk_reduction=9.0,
            strategic_value=7.0,
        ),
    )

    goal.add_task(task1)
    goal.add_task(task2)
    goal.add_task(task3)

    # Deconstruct with auto-generation
    deconstructor = MLATaskDeconstructor()
    result = deconstructor.deconstruct(
        goal,
        auto_generate_subtasks=True,
        max_depth=2,
    )

    # Print results
    result.print_summary()

    print(f"\n📊 Task Breakdown:")
    print(f"  Root tasks: {len(goal.tasks)}")
    print(f"  Total tasks (with subtasks): {len(result.all_tasks)}")

    # Show task hierarchy
    print("\n🌳 Task Hierarchy:")
    for task in goal.tasks:
        print(f"\n  {task.title}")
        for subtask in task.subtasks:
            print(f"    └─ {subtask.title}")


def example_high_leverage_focus():
    """Example: Focus on high-leverage tasks."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: High-Leverage Task Focus")
    print("=" * 60)

    goal = Goal(
        title="Optimize Development Workflow",
        description="Improve team productivity and code quality",
    )

    # Add various tasks with different leverage profiles
    tasks_data = [
        {
            "id": "ci_cd",
            "title": "Implement CI/CD Pipeline",
            "category": TaskCategory.INTEGRATION,
            "complexity": TaskComplexity.COMPLEX,
            "hours": 16.0,
            "impact": ImpactMetrics(
                direct_value=8.0,
                reusability=9.0,
                enablement=8.0,
                time_efficiency=10.0,
                risk_reduction=9.0,
            ),
        },
        {
            "id": "code_review",
            "title": "Establish Code Review Process",
            "category": TaskCategory.PLANNING,
            "complexity": TaskComplexity.SIMPLE,
            "hours": 4.0,
            "impact": ImpactMetrics(
                direct_value=7.0,
                reusability=8.0,
                learning_value=8.0,
                strategic_value=7.0,
            ),
        },
        {
            "id": "testing",
            "title": "Set Up Automated Testing",
            "category": TaskCategory.TESTING,
            "complexity": TaskComplexity.COMPLEX,
            "hours": 20.0,
            "impact": ImpactMetrics(
                direct_value=9.0,
                reusability=9.0,
                risk_reduction=10.0,
                strategic_value=8.0,
            ),
        },
        {
            "id": "documentation",
            "title": "Write Developer Documentation",
            "category": TaskCategory.DOCUMENTATION,
            "complexity": TaskComplexity.MODERATE,
            "hours": 8.0,
            "impact": ImpactMetrics(
                direct_value=6.0,
                reusability=7.0,
                learning_value=9.0,
            ),
        },
        {
            "id": "refactoring",
            "title": "Refactor Legacy Code",
            "category": TaskCategory.OPTIMIZATION,
            "complexity": TaskComplexity.VERY_COMPLEX,
            "hours": 40.0,
            "impact": ImpactMetrics(
                direct_value=5.0,
                reusability=4.0,
                risk_reduction=6.0,
            ),
        },
    ]

    for task_data in tasks_data:
        task = Task(
            id=task_data["id"],
            title=task_data["title"],
            category=task_data["category"],
            complexity=task_data["complexity"],
            estimated_hours=task_data["hours"],
            impact=task_data["impact"],
        )
        goal.add_task(task)

    # Deconstruct
    deconstructor = MLATaskDeconstructor()
    result = deconstructor.deconstruct(goal, auto_generate_subtasks=False)

    # Show high-leverage tasks
    print("\n🎯 High-Leverage Tasks (≥70):")
    high_leverage = result.get_high_leverage_tasks()

    for task in high_leverage:
        print(f"\n  {task.title}")
        print(f"    Leverage Score: {task.leverage_score:.1f}")
        print(f"    Estimated Hours: {task.estimated_hours}")
        print(f"    ROI: {task.leverage_score / task.estimated_hours:.1f} leverage per hour")

    # Calculate total effort
    total_hours = sum(t.estimated_hours for t in result.all_tasks)
    high_leverage_hours = sum(t.estimated_hours for t in high_leverage)

    print(f"\n📊 Effort Distribution:")
    print(f"  Total effort: {total_hours} hours")
    print(f"  High-leverage effort: {high_leverage_hours} hours ({high_leverage_hours/total_hours*100:.1f}%)")
    print(f"  Recommendation: Focus on high-leverage tasks first for maximum impact")


def example_dependency_management():
    """Example: Complex dependency management."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Dependency Management")
    print("=" * 60)

    goal = Goal(
        title="Launch SaaS Platform",
        description="Build and launch a multi-tenant SaaS platform",
    )

    # Create tasks with complex dependencies
    tasks = []

    # Foundation tasks
    t1 = Task(
        id="infrastructure",
        title="Set Up Infrastructure",
        category=TaskCategory.DEPLOYMENT,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=16.0,
    )
    tasks.append(t1)

    # Core platform
    t2 = Task(
        id="backend",
        title="Build Backend API",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.VERY_COMPLEX,
        estimated_hours=80.0,
    )
    t2.add_dependency("infrastructure")
    tasks.append(t2)

    t3 = Task(
        id="frontend",
        title="Build Frontend UI",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=60.0,
    )
    t3.add_dependency("backend")
    tasks.append(t3)

    # Supporting systems
    t4 = Task(
        id="auth_system",
        title="Implement Authentication System",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=24.0,
    )
    t4.add_dependency("backend")
    tasks.append(t4)

    t5 = Task(
        id="billing",
        title="Integrate Billing System",
        category=TaskCategory.INTEGRATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=32.0,
    )
    t5.add_dependency("backend")
    t5.add_dependency("auth_system")
    tasks.append(t5)

    # Testing and deployment
    t6 = Task(
        id="testing",
        title="End-to-End Testing",
        category=TaskCategory.TESTING,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=24.0,
    )
    t6.add_dependency("frontend")
    t6.add_dependency("auth_system")
    t6.add_dependency("billing")
    tasks.append(t6)

    t7 = Task(
        id="launch",
        title="Production Launch",
        category=TaskCategory.DEPLOYMENT,
        complexity=TaskComplexity.MODERATE,
        estimated_hours=8.0,
    )
    t7.add_dependency("testing")
    tasks.append(t7)

    for task in tasks:
        # Set reasonable impact metrics
        task.impact = ImpactMetrics(
            direct_value=7.0,
            reusability=6.0,
            enablement=7.0,
        )
        goal.add_task(task)

    # Deconstruct
    deconstructor = MLATaskDeconstructor()
    result = deconstructor.deconstruct(goal, auto_generate_subtasks=False)

    # Show dependency graph
    print("\n📊 Dependency Graph:")
    for task in result.prioritized_tasks:
        deps = ", ".join(task.dependencies) if task.dependencies else "None"
        print(f"  {task.id}")
        print(f"    Dependencies: {deps}")
        print(f"    Leverage: {task.leverage_score:.1f}")

    # Show execution order (simplified)
    print("\n🔄 Suggested Execution Order:")
    completed = set()
    level = 1

    while len(completed) < len(tasks):
        # Find tasks that can be executed now
        ready = [
            t for t in tasks
            if t.id not in completed and all(dep in completed for dep in t.dependencies)
        ]

        if ready:
            print(f"\n  Level {level}:")
            for task in ready:
                print(f"    - {task.title}")
                completed.add(task.id)
            level += 1
        else:
            break

    if result.dependency_issues:
        print(f"\n⚠️  Dependency Issues:")
        for issue in result.dependency_issues:
            print(f"    - {issue}")


def example_custom_leverage_weights():
    """Example: Custom leverage weight configuration."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Custom Leverage Weights")
    print("=" * 60)

    goal = Goal(
        title="Research and Prototype",
        description="Research new technology and build prototype",
    )

    # Add research-focused tasks
    task1 = Task(
        id="research",
        title="Technology Research",
        category=TaskCategory.RESEARCH,
        complexity=TaskComplexity.MODERATE,
        estimated_hours=16.0,
        impact=ImpactMetrics(
            direct_value=6.0,
            reusability=8.0,
            learning_value=10.0,  # High learning value
            strategic_value=9.0,
        ),
    )

    task2 = Task(
        id="prototype",
        title="Build Prototype",
        category=TaskCategory.IMPLEMENTATION,
        complexity=TaskComplexity.COMPLEX,
        estimated_hours=24.0,
        impact=ImpactMetrics(
            direct_value=8.0,
            reusability=7.0,
            learning_value=8.0,
            strategic_value=8.0,
        ),
    )

    goal.add_task(task1)
    goal.add_task(task2)

    # Standard weights
    print("\n📊 With Standard Weights:")
    deconstructor_standard = MLATaskDeconstructor()
    result_standard = deconstructor_standard.deconstruct(goal, auto_generate_subtasks=False)

    for task in result_standard.prioritized_tasks:
        print(f"  {task.title}: {task.leverage_score:.1f}")

    # Custom weights emphasizing learning and strategy
    print("\n📊 With Learning-Focused Weights:")
    custom_weights = {
        "direct_value": 0.10,
        "reusability": 0.15,
        "enablement": 0.10,
        "strategic_value": 0.25,  # Increased
        "learning_value": 0.30,   # Significantly increased
        "time_efficiency": 0.05,
        "risk_reduction": 0.05,
    }

    deconstructor_custom = MLATaskDeconstructor(leverage_weights=custom_weights)
    result_custom = deconstructor_custom.deconstruct(goal, auto_generate_subtasks=False)

    for task in result_custom.prioritized_tasks:
        print(f"  {task.title}: {task.leverage_score:.1f}")

    print("\n💡 Notice how weights affect prioritization!")


def run_all_examples():
    """Run all examples."""
    example_simple_goal()
    example_auto_decomposition()
    example_high_leverage_focus()
    example_dependency_management()
    example_custom_leverage_weights()


if __name__ == "__main__":
    run_all_examples()

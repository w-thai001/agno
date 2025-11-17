#!/usr/bin/env python3
"""
Dependency Optimizer FSA Demo

This demo showcases real-world usage of the Dependency Optimizer FSA for
analyzing and optimizing task dependency graphs, such as build pipelines,
data processing workflows, or microservice orchestration.

Scenario: Build Pipeline Optimization
- Multiple build tasks with dependencies
- Identifies parallel execution opportunities
- Calculates critical path
- Optimizes redundant dependencies
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agno.fsa.dependency_optimizer import (
    DependencyOptimizerFSA,
    FSAState,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_build_pipeline():
    """Demonstrate build pipeline optimization."""
    print_section("DEMO: Build Pipeline Optimization")

    fsa = DependencyOptimizerFSA()

    # Define build tasks
    tasks = {
        "setup_env": "Setup Build Environment",
        "install_deps": "Install Dependencies",
        "lint_code": "Lint Source Code",
        "type_check": "Type Checking",
        "unit_tests": "Run Unit Tests",
        "build_frontend": "Build Frontend Assets",
        "build_backend": "Build Backend Services",
        "integration_tests": "Run Integration Tests",
        "security_scan": "Security Vulnerability Scan",
        "package": "Package Application",
        "deploy": "Deploy to Staging",
    }

    # Add all tasks
    print("Adding build tasks...")
    for task_id, task_name in tasks.items():
        fsa.add_node(task_id, task_name)
        print(f"  ✓ {task_name}")

    # Define dependencies (realistic build pipeline)
    print("\nDefining task dependencies...")
    dependencies = [
        ("install_deps", "setup_env"),
        ("lint_code", "install_deps"),
        ("type_check", "install_deps"),
        ("unit_tests", "install_deps"),
        ("build_frontend", "install_deps"),
        ("build_backend", "install_deps"),
        ("build_frontend", "lint_code"),  # Frontend needs linting
        ("build_backend", "type_check"),  # Backend needs type checking
        ("integration_tests", "build_frontend"),
        ("integration_tests", "build_backend"),
        ("integration_tests", "unit_tests"),
        ("security_scan", "build_frontend"),
        ("security_scan", "build_backend"),
        ("package", "integration_tests"),
        ("package", "security_scan"),
        ("deploy", "package"),
    ]

    for dependent, dependency in dependencies:
        fsa.add_dependency(dependent, dependency, weight=1.0)
        print(f"  → {tasks[dependent]} depends on {tasks[dependency]}")

    # Validate the graph
    print_section("Step 1: Validate Dependency Graph")
    if fsa.validate_graph():
        print("✓ Graph is valid - no circular dependencies detected")
    else:
        print(f"✗ Graph validation failed: {fsa.error_message}")
        return

    # Get statistics
    print_section("Step 2: Graph Statistics")
    stats = fsa.get_stats()
    print(f"Total Tasks:          {stats['node_count']}")
    print(f"Total Dependencies:   {stats['edge_count']}")
    print(f"Source Tasks:         {stats['source_nodes']}")
    print(f"Sink Tasks:           {stats['sink_nodes']}")
    print(f"Avg In-Degree:        {stats['avg_in_degree']:.2f}")
    print(f"Max In-Degree:        {stats['max_in_degree']}")

    # Get execution order
    print_section("Step 3: Sequential Execution Order")
    order = fsa.get_execution_order()
    print("Tasks in topological order:")
    for i, task_id in enumerate(order, 1):
        print(f"  {i:2d}. {tasks[task_id]}")

    # Find parallel execution groups
    print_section("Step 4: Parallel Execution Opportunities")
    groups = fsa.find_parallel_groups()
    print(f"Identified {len(groups)} execution stages:\n")

    total_sequential_time = len(order)
    total_parallel_time = len(groups)

    for stage, group in enumerate(groups, 1):
        print(f"Stage {stage} - Can run {len(group)} task(s) in parallel:")
        for task_id in group:
            print(f"  • {tasks[task_id]}")
        print()

    print(f"Performance Improvement:")
    print(f"  Sequential execution: {total_sequential_time} time units")
    print(f"  Parallel execution:   {total_parallel_time} time units")
    speedup = total_sequential_time / total_parallel_time
    print(f"  Speedup:              {speedup:.2f}x faster")

    # Find critical path
    print_section("Step 5: Critical Path Analysis")
    critical_path = fsa.get_critical_path()
    print(f"Critical path length: {len(critical_path)} tasks\n")
    print("Tasks on critical path (bottleneck):")
    for i, task_id in enumerate(critical_path, 1):
        print(f"  {i}. {tasks[task_id]}")

    print("\n💡 Optimization Tip: Focus on optimizing tasks on the critical path")
    print("   to reduce overall build time.")

    # Optimize graph
    print_section("Step 6: Graph Optimization")
    print("Checking for redundant dependencies...")
    removed = fsa.optimize_graph()

    if removed > 0:
        print(f"✓ Removed {removed} redundant (transitive) dependencies")
        print(f"  New edge count: {fsa.get_stats()['edge_count']}")
    else:
        print("✓ No redundant dependencies found - graph is already optimal")

    # Final summary
    print_section("Summary")
    final_stats = fsa.get_stats()
    print(f"FSA State:               {final_stats['state']}")
    print(f"Total Tasks:             {final_stats['node_count']}")
    print(f"Dependencies:            {final_stats['edge_count']}")
    print(f"Execution Stages:        {final_stats['parallel_groups_count']}")
    print(f"Max Parallel Tasks:      {final_stats['max_parallelism']}")
    print(f"Critical Path Length:    {final_stats['critical_path_length']}")
    print(f"\n✓ Build pipeline successfully optimized!")


def demo_circular_dependency_detection():
    """Demonstrate circular dependency detection."""
    print_section("DEMO: Circular Dependency Detection")

    fsa = DependencyOptimizerFSA()

    print("Creating a task graph with circular dependencies...\n")

    # Add tasks
    tasks = {
        "task_a": "Task A",
        "task_b": "Task B",
        "task_c": "Task C",
        "task_d": "Task D",
    }

    for task_id, task_name in tasks.items():
        fsa.add_node(task_id, task_name)

    # Create a circular dependency: A -> B -> C -> D -> A
    print("Adding dependencies:")
    fsa.add_dependency("task_b", "task_a")
    print("  ✓ Task B depends on Task A")

    fsa.add_dependency("task_c", "task_b")
    print("  ✓ Task C depends on Task B")

    fsa.add_dependency("task_d", "task_c")
    print("  ✓ Task D depends on Task C")

    fsa.add_dependency("task_a", "task_d")
    print("  ✓ Task A depends on Task D (creates cycle!)")

    # Try to validate
    print("\nValidating graph...")
    if fsa.validate_graph():
        print("✓ Graph is valid")
    else:
        print(f"✗ Validation failed!")
        print(f"   Error: {fsa.error_message}")
        print(f"   FSA State: {fsa.state.value}")

    print("\n💡 The FSA correctly detected the circular dependency and")
    print("   transitioned to ERROR state, preventing invalid execution.")


def demo_microservice_orchestration():
    """Demonstrate microservice deployment orchestration."""
    print_section("DEMO: Microservice Deployment Orchestration")

    fsa = DependencyOptimizerFSA()

    print("Planning microservice deployment...\n")

    # Define microservices and infrastructure
    services = {
        # Infrastructure
        "vpc": "Create VPC",
        "security_groups": "Configure Security Groups",
        "database": "Deploy Database",
        "cache": "Deploy Redis Cache",
        "message_queue": "Deploy Message Queue",

        # Application services
        "auth_service": "Deploy Auth Service",
        "user_service": "Deploy User Service",
        "payment_service": "Deploy Payment Service",
        "notification_service": "Deploy Notification Service",
        "api_gateway": "Deploy API Gateway",

        # Post-deployment
        "smoke_tests": "Run Smoke Tests",
        "dns_update": "Update DNS Records",
    }

    # Add all services
    for service_id, service_name in services.items():
        metadata = {
            "category": "infrastructure" if service_id in ["vpc", "security_groups", "database", "cache", "message_queue"] else "application"
        }
        fsa.add_node(service_id, service_name, metadata=metadata)

    # Define deployment dependencies
    dependencies = [
        # Infrastructure dependencies
        ("security_groups", "vpc"),
        ("database", "vpc"),
        ("cache", "vpc"),
        ("message_queue", "vpc"),

        # Service dependencies
        ("auth_service", "database"),
        ("auth_service", "security_groups"),

        ("user_service", "database"),
        ("user_service", "auth_service"),
        ("user_service", "security_groups"),

        ("payment_service", "database"),
        ("payment_service", "auth_service"),
        ("payment_service", "security_groups"),

        ("notification_service", "message_queue"),
        ("notification_service", "security_groups"),

        ("api_gateway", "auth_service"),
        ("api_gateway", "user_service"),
        ("api_gateway", "payment_service"),
        ("api_gateway", "notification_service"),

        # Post-deployment
        ("smoke_tests", "api_gateway"),
        ("dns_update", "smoke_tests"),
    ]

    for dependent, dependency in dependencies:
        fsa.add_dependency(dependent, dependency)

    # Validate
    print("Validating deployment plan...")
    if not fsa.validate_graph():
        print(f"✗ Invalid plan: {fsa.error_message}")
        return

    print("✓ Deployment plan is valid\n")

    # Get parallel deployment stages
    groups = fsa.find_parallel_groups()
    print(f"Deployment Stages ({len(groups)} stages):\n")

    for stage, group in enumerate(groups, 1):
        print(f"Stage {stage}:")
        for service_id in group:
            print(f"  • {services[service_id]}")
        print()

    # Critical path
    critical_path = fsa.get_critical_path()
    print("Critical Deployment Path:")
    for service_id in critical_path:
        print(f"  → {services[service_id]}")

    print(f"\n💡 The critical path shows the minimum deployment time.")
    print(f"   Total stages: {len(groups)}")


def main():
    """Run all demos."""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║         Dependency Optimizer FSA - Interactive Demo             ║
    ║                                                                  ║
    ║  Showcasing production-ready dependency graph optimization      ║
    ║  for build pipelines, task scheduling, and orchestration        ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    try:
        # Demo 1: Build Pipeline
        demo_build_pipeline()

        # Demo 2: Circular Dependency Detection
        demo_circular_dependency_detection()

        # Demo 3: Microservice Orchestration
        demo_microservice_orchestration()

        print_section("All Demos Completed Successfully!")
        print("✓ Dependency Optimizer FSA is ready for production use\n")

    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

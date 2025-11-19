#!/usr/bin/env python3
"""Quick test of the Workflow Orchestrator"""

import sys
import time
from typing import Any, Dict

# Add the libs/agno directory to the path
sys.path.insert(0, "/home/user/agno/libs/agno")

from agno.workflow.orchestrator import Task, WorkflowOrchestrator


def test_simple_workflow():
    """Test a simple workflow"""
    print("Testing Workflow Orchestrator FSA...")
    print("=" * 60)

    def task_a(context: Dict[str, Any]) -> str:
        print("  ✓ Executing Task A...")
        time.sleep(0.5)
        context["a_result"] = "A completed"
        return "Result from A"

    def task_b(context: Dict[str, Any]) -> str:
        print("  ✓ Executing Task B (depends on A)...")
        time.sleep(0.5)
        return f"B used: {context.get('a_result')}"

    def task_c(context: Dict[str, Any]) -> str:
        print("  ✓ Executing Task C (parallel with B)...")
        time.sleep(0.5)
        return "Result from C"

    def task_d(context: Dict[str, Any]) -> str:
        print("  ✓ Executing Task D (depends on B and C)...")
        time.sleep(0.5)
        return "All tasks completed!"

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="test_workflow", max_parallel_tasks=2, auto_persist=False
    )

    # Add tasks
    orchestrator.add_task(Task(task_id="a", name="Task A", func=task_a))
    orchestrator.add_task(
        Task(task_id="b", name="Task B", func=task_b, dependencies=["a"])
    )
    orchestrator.add_task(
        Task(task_id="c", name="Task C", func=task_c, dependencies=["a"])
    )
    orchestrator.add_task(
        Task(task_id="d", name="Task D", func=task_d, dependencies=["b", "c"])
    )

    # Execute
    print("\nExecuting workflow...")
    print("-" * 60)
    results = orchestrator.execute()

    # Print results
    print("-" * 60)
    print("\nResults:")
    for task_id, result in results.items():
        status = "✓" if result.success else "✗"
        print(
            f"  {status} {task_id}: {result.output} (took {result.duration:.2f}s)"
        )

    # Print metrics
    metrics = orchestrator.get_metrics()
    print("\nMetrics:")
    print(f"  Total tasks: {metrics.total_tasks}")
    print(f"  Completed: {metrics.completed_tasks}")
    print(f"  Failed: {metrics.failed_tasks}")
    print(f"  Progress: {metrics.get_progress_percentage():.0f}%")
    print(f"  Total duration: {metrics.duration:.2f}s")

    # Verify DAG structure
    print("\nDAG Validation:")
    is_valid, error = orchestrator.dag.validate()
    print(f"  Valid: {is_valid}")
    if error:
        print(f"  Error: {error}")

    # Test topological sort
    print("\nTopological Order:")
    topo_order = orchestrator.dag.topological_sort()
    print(f"  {' -> '.join(topo_order)}")

    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)

    return orchestrator.workflow_state.value == "completed"


if __name__ == "__main__":
    success = test_simple_workflow()
    sys.exit(0 if success else 1)

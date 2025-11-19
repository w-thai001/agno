"""
Comprehensive examples demonstrating the Workflow Orchestrator FSA.

This module contains various examples showcasing:
1. Simple linear workflow
2. Parallel task execution
3. Complex DAG with multiple dependencies
4. Error handling and retry mechanisms
5. State persistence and recovery
6. Conditional task execution
7. Real-world data pipeline example
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict

from agno.utils.log import logger
from agno.workflow.orchestrator import Task, WorkflowOrchestrator


# ==================== Example 1: Simple Linear Workflow ====================


def example_1_simple_linear_workflow():
    """
    Example 1: Simple linear workflow with sequential tasks.

    This demonstrates the basics of task creation and execution.
    """
    print("\n" + "=" * 60)
    print("Example 1: Simple Linear Workflow")
    print("=" * 60)

    def task_a(context: Dict[str, Any]) -> str:
        print("  Executing Task A...")
        time.sleep(1)
        return "Result from A"

    def task_b(context: Dict[str, Any]) -> str:
        print("  Executing Task B...")
        time.sleep(1)
        return "Result from B"

    def task_c(context: Dict[str, Any]) -> str:
        print("  Executing Task C...")
        time.sleep(1)
        return "Result from C"

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="simple_linear", auto_persist=False
    )

    # Create tasks: A -> B -> C
    orchestrator.add_task(Task(task_id="a", name="Task A", func=task_a))
    orchestrator.add_task(
        Task(task_id="b", name="Task B", func=task_b, dependencies=["a"])
    )
    orchestrator.add_task(
        Task(task_id="c", name="Task C", func=task_c, dependencies=["b"])
    )

    # Execute
    results = orchestrator.execute()

    # Print results
    print("\nResults:")
    for task_id, result in results.items():
        print(f"  {task_id}: {result.output} (duration: {result.duration:.2f}s)")

    print(f"\nWorkflow Status: {orchestrator.workflow_state.value}")


# ==================== Example 2: Parallel Task Execution ====================


def example_2_parallel_execution():
    """
    Example 2: Parallel task execution with fan-out/fan-in pattern.

    This demonstrates how independent tasks run in parallel.
    """
    print("\n" + "=" * 60)
    print("Example 2: Parallel Task Execution")
    print("=" * 60)

    def extract_data(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Extracting data from source...")
        time.sleep(2)
        return {"data": [1, 2, 3, 4, 5]}

    def process_batch_1(context: Dict[str, Any]) -> str:
        print("  Processing batch 1...")
        time.sleep(3)
        return "Batch 1 processed"

    def process_batch_2(context: Dict[str, Any]) -> str:
        print("  Processing batch 2...")
        time.sleep(3)
        return "Batch 2 processed"

    def process_batch_3(context: Dict[str, Any]) -> str:
        print("  Processing batch 3...")
        time.sleep(3)
        return "Batch 3 processed"

    def aggregate_results(context: Dict[str, Any]) -> str:
        print("  Aggregating all results...")
        time.sleep(1)
        return "All batches aggregated"

    # Create orchestrator with parallel execution
    orchestrator = WorkflowOrchestrator(
        workflow_id="parallel_execution", max_parallel_tasks=3, auto_persist=False
    )

    # Create tasks with fan-out/fan-in pattern
    #       batch1
    #      /       \
    # extract -- batch2 -- aggregate
    #      \       /
    #       batch3

    orchestrator.add_task(Task(task_id="extract", name="Extract", func=extract_data))

    orchestrator.add_task(
        Task(
            task_id="batch1",
            name="Process Batch 1",
            func=process_batch_1,
            dependencies=["extract"],
        )
    )
    orchestrator.add_task(
        Task(
            task_id="batch2",
            name="Process Batch 2",
            func=process_batch_2,
            dependencies=["extract"],
        )
    )
    orchestrator.add_task(
        Task(
            task_id="batch3",
            name="Process Batch 3",
            func=process_batch_3,
            dependencies=["extract"],
        )
    )

    orchestrator.add_task(
        Task(
            task_id="aggregate",
            name="Aggregate Results",
            func=aggregate_results,
            dependencies=["batch1", "batch2", "batch3"],
        )
    )

    # Execute and measure time
    start_time = time.time()
    results = orchestrator.execute()
    total_time = time.time() - start_time

    # Print results
    print("\nResults:")
    for task_id, result in results.items():
        print(f"  {task_id}: {result.output}")

    print(f"\nTotal execution time: {total_time:.2f}s")
    print("Note: Tasks ran in parallel, saving significant time!")


# ==================== Example 3: Error Handling and Retry ====================


def example_3_error_handling_and_retry():
    """
    Example 3: Error handling with automatic retry mechanism.

    This demonstrates retry logic and failure propagation.
    """
    print("\n" + "=" * 60)
    print("Example 3: Error Handling and Retry")
    print("=" * 60)

    attempt_counter = {"count": 0}

    def flaky_task(context: Dict[str, Any]) -> str:
        attempt_counter["count"] += 1
        print(f"  Flaky task attempt {attempt_counter['count']}")

        # Fail first 2 attempts, succeed on 3rd
        if attempt_counter["count"] < 3:
            raise Exception(f"Simulated failure (attempt {attempt_counter['count']})")

        return "Success after retries"

    def failing_task(context: Dict[str, Any]) -> str:
        print("  This task will always fail...")
        raise Exception("Permanent failure")

    def dependent_task(context: Dict[str, Any]) -> str:
        print("  This should be skipped...")
        return "Should not execute"

    def on_failure_callback(task: Task, error: str):
        print(f"  Callback: Task {task.name} failed with error: {error}")

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="error_handling", auto_persist=False
    )

    # Create tasks
    orchestrator.add_task(
        Task(
            task_id="flaky",
            name="Flaky Task",
            func=flaky_task,
            retry_count=3,
            retry_delay=0.5,
        )
    )

    orchestrator.add_task(
        Task(
            task_id="failing",
            name="Failing Task",
            func=failing_task,
            retry_count=2,
            retry_delay=0.5,
            on_failure=on_failure_callback,
        )
    )

    orchestrator.add_task(
        Task(
            task_id="dependent",
            name="Dependent Task",
            func=dependent_task,
            dependencies=["failing"],
        )
    )

    # Execute
    results = orchestrator.execute()

    # Print results
    print("\nResults:")
    for task_id, result in results.items():
        status = "✓ Success" if result.success else "✗ Failed"
        print(f"  {task_id}: {status}")
        if not result.success:
            print(f"    Error: {result.error}")
        if result.retry_count > 0:
            print(f"    Retries: {result.retry_count}")

    # Check task states
    print("\nTask States:")
    for task_id, task in orchestrator.dag.tasks.items():
        print(f"  {task_id}: {task.state.value}")


# ==================== Example 4: Complex DAG ====================


def example_4_complex_dag():
    """
    Example 4: Complex DAG with multiple dependency paths.

    This demonstrates a realistic workflow with complex dependencies.
    """
    print("\n" + "=" * 60)
    print("Example 4: Complex DAG Workflow")
    print("=" * 60)

    # Define task functions
    def init_project(context: Dict[str, Any]) -> str:
        print("  Initializing project...")
        time.sleep(1)
        context["project_id"] = "PRJ-001"
        return "Project initialized"

    def fetch_config(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Fetching configuration...")
        time.sleep(1)
        return {"env": "production", "region": "us-west"}

    def setup_database(context: Dict[str, Any]) -> str:
        print(f"  Setting up database for {context.get('project_id')}...")
        time.sleep(2)
        return "Database ready"

    def setup_cache(context: Dict[str, Any]) -> str:
        print("  Setting up cache...")
        time.sleep(1)
        return "Cache ready"

    def deploy_api(context: Dict[str, Any]) -> str:
        print("  Deploying API...")
        time.sleep(2)
        return "API deployed"

    def deploy_workers(context: Dict[str, Any]) -> str:
        print("  Deploying workers...")
        time.sleep(2)
        return "Workers deployed"

    def run_migrations(context: Dict[str, Any]) -> str:
        print("  Running database migrations...")
        time.sleep(1)
        return "Migrations complete"

    def smoke_tests(context: Dict[str, Any]) -> str:
        print("  Running smoke tests...")
        time.sleep(1)
        return "Tests passed"

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="complex_deployment", max_parallel_tasks=3, auto_persist=False
    )

    # Build complex DAG
    #              init
    #             /    \
    #        config    db
    #           |       |
    #        cache   migrate
    #           |    /   \
    #          api  workers
    #            \    /
    #            tests

    orchestrator.add_tasks(
        [
            Task(task_id="init", name="Initialize", func=init_project),
            Task(
                task_id="config",
                name="Fetch Config",
                func=fetch_config,
                dependencies=["init"],
            ),
            Task(
                task_id="db",
                name="Setup Database",
                func=setup_database,
                dependencies=["init"],
            ),
            Task(
                task_id="cache",
                name="Setup Cache",
                func=setup_cache,
                dependencies=["config"],
            ),
            Task(
                task_id="migrate",
                name="Run Migrations",
                func=run_migrations,
                dependencies=["db"],
            ),
            Task(
                task_id="api",
                name="Deploy API",
                func=deploy_api,
                dependencies=["cache", "migrate"],
            ),
            Task(
                task_id="workers",
                name="Deploy Workers",
                func=deploy_workers,
                dependencies=["migrate"],
            ),
            Task(
                task_id="tests",
                name="Smoke Tests",
                func=smoke_tests,
                dependencies=["api", "workers"],
            ),
        ]
    )

    # Execute
    start_time = time.time()
    results = orchestrator.execute()
    total_time = time.time() - start_time

    # Print results
    print("\nExecution Summary:")
    print(f"  Total tasks: {len(results)}")
    print(f"  Successful: {sum(1 for r in results.values() if r.success)}")
    print(f"  Total time: {total_time:.2f}s")

    metrics = orchestrator.get_metrics()
    print(f"  Progress: {metrics.get_progress_percentage():.1f}%")


# ==================== Example 5: State Persistence and Recovery ====================


def example_5_state_persistence():
    """
    Example 5: State persistence and workflow recovery.

    This demonstrates saving workflow state and resuming from failures.
    """
    print("\n" + "=" * 60)
    print("Example 5: State Persistence and Recovery")
    print("=" * 60)

    def long_task_1(context: Dict[str, Any]) -> str:
        print("  Executing long task 1...")
        time.sleep(1)
        return "Task 1 complete"

    def long_task_2(context: Dict[str, Any]) -> str:
        print("  Executing long task 2...")
        time.sleep(1)
        return "Task 2 complete"

    def problematic_task(context: Dict[str, Any]) -> str:
        print("  Executing problematic task...")
        # Simulating a failure that requires manual intervention
        if not context.get("fixed"):
            raise Exception("Simulated error - needs fixing")
        return "Task fixed and completed"

    def final_task(context: Dict[str, Any]) -> str:
        print("  Executing final task...")
        time.sleep(1)
        return "All done!"

    # First execution - will fail
    print("\nFirst attempt (will fail):")
    orchestrator = WorkflowOrchestrator(
        workflow_id="persistent_workflow",
        auto_persist=True,
        state_dir=Path(".workflow_state_demo"),
    )

    orchestrator.add_tasks(
        [
            Task(task_id="task1", name="Long Task 1", func=long_task_1),
            Task(task_id="task2", name="Long Task 2", func=long_task_2),
            Task(
                task_id="problem",
                name="Problematic Task",
                func=problematic_task,
                dependencies=["task1", "task2"],
            ),
            Task(
                task_id="final",
                name="Final Task",
                func=final_task,
                dependencies=["problem"],
            ),
        ]
    )

    try:
        orchestrator.execute(context={})
    except Exception as e:
        print(f"\nWorkflow failed as expected: {e}")

    print(f"\nWorkflow state: {orchestrator.workflow_state.value}")
    print("State has been persisted to disk.")

    # Second execution - resume with fix
    print("\n" + "-" * 60)
    print("Second attempt (resuming with fix):")

    # Create new orchestrator instance
    orchestrator2 = WorkflowOrchestrator(
        workflow_id="persistent_workflow",
        auto_persist=True,
        state_dir=Path(".workflow_state_demo"),
    )

    # Re-register tasks (required after recovery)
    orchestrator2.add_tasks(
        [
            Task(task_id="task1", name="Long Task 1", func=long_task_1),
            Task(task_id="task2", name="Long Task 2", func=long_task_2),
            Task(
                task_id="problem",
                name="Problematic Task",
                func=problematic_task,
                dependencies=["task1", "task2"],
            ),
            Task(
                task_id="final",
                name="Final Task",
                func=final_task,
                dependencies=["problem"],
            ),
        ]
    )

    # Execute with fix
    results = orchestrator2.execute(context={"fixed": True}, resume=True)

    print("\nResults:")
    for task_id, result in results.items():
        status = "✓" if result.success else "✗"
        print(f"  {status} {task_id}: {result.output}")

    print("\nNote: Tasks 1 and 2 were not re-executed (loaded from state)")


# ==================== Example 6: Monitoring and Metrics ====================


def example_6_monitoring():
    """
    Example 6: Real-time monitoring and metrics collection.

    This demonstrates how to monitor workflow execution in real-time.
    """
    print("\n" + "=" * 60)
    print("Example 6: Execution Monitoring")
    print("=" * 60)

    def monitored_task(name: str, duration: float):
        """Helper to create monitored tasks"""

        def task_func(context: Dict[str, Any]) -> str:
            print(f"  Running {name}...")
            time.sleep(duration)
            return f"{name} completed"

        return task_func

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="monitored_workflow", max_parallel_tasks=2, auto_persist=False
    )

    # Add monitored tasks
    orchestrator.add_tasks(
        [
            Task(task_id="t1", name="Task 1", func=monitored_task("Task 1", 2)),
            Task(task_id="t2", name="Task 2", func=monitored_task("Task 2", 2)),
            Task(
                task_id="t3",
                name="Task 3",
                func=monitored_task("Task 3", 1),
                dependencies=["t1"],
            ),
            Task(
                task_id="t4",
                name="Task 4",
                func=monitored_task("Task 4", 1),
                dependencies=["t2"],
            ),
            Task(
                task_id="t5",
                name="Task 5",
                func=monitored_task("Task 5", 2),
                dependencies=["t3", "t4"],
            ),
        ]
    )

    # Execute with monitoring
    print("\nStarting workflow execution...\n")

    async def execute_with_monitoring():
        # Start execution in background
        execution_task = asyncio.create_task(orchestrator.execute_async())

        # Monitor progress
        while orchestrator.workflow_state.value == "running":
            await asyncio.sleep(0.5)
            metrics = orchestrator.get_metrics()

            print(
                f"\rProgress: {metrics.get_progress_percentage():.0f}% "
                f"[Completed: {metrics.completed_tasks}/{metrics.total_tasks}, "
                f"Running: {metrics.running_tasks}]",
                end="",
            )

        await execution_task
        print()  # New line after progress

    asyncio.run(execute_with_monitoring())

    # Final metrics
    metrics = orchestrator.get_metrics()
    print("\nFinal Metrics:")
    print(f"  Total tasks: {metrics.total_tasks}")
    print(f"  Completed: {metrics.completed_tasks}")
    print(f"  Failed: {metrics.failed_tasks}")
    print(f"  Duration: {metrics.duration:.2f}s")
    print(f"  Progress: {metrics.get_progress_percentage():.0f}%")


# ==================== Example 7: Real-World Data Pipeline ====================


def example_7_data_pipeline():
    """
    Example 7: Real-world data pipeline with ETL operations.

    This demonstrates a complete ETL pipeline with realistic tasks.
    """
    print("\n" + "=" * 60)
    print("Example 7: Real-World Data Pipeline")
    print("=" * 60)

    # Simulate data pipeline tasks
    def validate_schema(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Validating data schema...")
        time.sleep(1)
        return {"schema_valid": True, "records": 1000}

    def extract_from_api(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Extracting data from API...")
        time.sleep(2)
        return {"api_records": 500}

    def extract_from_database(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Extracting data from database...")
        time.sleep(2)
        return {"db_records": 500}

    def clean_data(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Cleaning and normalizing data...")
        time.sleep(2)
        return {"cleaned_records": 950}

    def enrich_data(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Enriching data with external sources...")
        time.sleep(2)
        return {"enriched_records": 950}

    def aggregate_metrics(context: Dict[str, Any]) -> Dict[str, Any]:
        print("  Calculating aggregate metrics...")
        time.sleep(1)
        return {"metrics": {"total": 950, "avg_value": 42.5}}

    def load_to_warehouse(context: Dict[str, Any]) -> str:
        print("  Loading data to warehouse...")
        time.sleep(2)
        return "Data loaded successfully"

    def generate_report(context: Dict[str, Any]) -> str:
        print("  Generating analytics report...")
        time.sleep(1)
        return "Report generated"

    def send_notifications(context: Dict[str, Any]) -> str:
        print("  Sending completion notifications...")
        time.sleep(1)
        return "Notifications sent"

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="data_pipeline", max_parallel_tasks=4, auto_persist=True
    )

    # Build ETL pipeline
    orchestrator.add_tasks(
        [
            # Validation
            Task(task_id="validate", name="Validate Schema", func=validate_schema),
            # Extraction (parallel)
            Task(
                task_id="extract_api",
                name="Extract from API",
                func=extract_from_api,
                dependencies=["validate"],
            ),
            Task(
                task_id="extract_db",
                name="Extract from DB",
                func=extract_from_database,
                dependencies=["validate"],
            ),
            # Transformation
            Task(
                task_id="clean",
                name="Clean Data",
                func=clean_data,
                dependencies=["extract_api", "extract_db"],
            ),
            Task(
                task_id="enrich",
                name="Enrich Data",
                func=enrich_data,
                dependencies=["clean"],
            ),
            Task(
                task_id="aggregate",
                name="Aggregate Metrics",
                func=aggregate_metrics,
                dependencies=["enrich"],
            ),
            # Loading (parallel)
            Task(
                task_id="load",
                name="Load to Warehouse",
                func=load_to_warehouse,
                dependencies=["aggregate"],
            ),
            Task(
                task_id="report",
                name="Generate Report",
                func=generate_report,
                dependencies=["aggregate"],
            ),
            # Notification
            Task(
                task_id="notify",
                name="Send Notifications",
                func=send_notifications,
                dependencies=["load", "report"],
            ),
        ]
    )

    # Execute pipeline
    print("\nExecuting ETL pipeline...\n")
    start_time = time.time()
    results = orchestrator.execute()
    total_time = time.time() - start_time

    # Print summary
    print("\n" + "=" * 60)
    print("Pipeline Execution Summary")
    print("=" * 60)
    print(f"Total execution time: {total_time:.2f}s")
    print(f"Tasks completed: {len([r for r in results.values() if r.success])}/{len(results)}")

    status = orchestrator.get_status()
    print(f"Workflow status: {status['state']}")
    print(f"Progress: {status['metrics']['progress_percentage']:.0f}%")


# ==================== Main Runner ====================


def run_all_examples():
    """Run all examples in sequence"""
    print("\n" + "=" * 60)
    print("WORKFLOW ORCHESTRATOR FSA - COMPREHENSIVE EXAMPLES")
    print("=" * 60)

    examples = [
        example_1_simple_linear_workflow,
        example_2_parallel_execution,
        example_3_error_handling_and_retry,
        example_4_complex_dag,
        example_5_state_persistence,
        example_6_monitoring,
        example_7_data_pipeline,
    ]

    for i, example in enumerate(examples, 1):
        try:
            example()
            time.sleep(1)  # Pause between examples
        except Exception as e:
            print(f"\nExample {i} encountered an error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run individual example or all
    import sys

    if len(sys.argv) > 1:
        example_num = int(sys.argv[1])
        examples = [
            example_1_simple_linear_workflow,
            example_2_parallel_execution,
            example_3_error_handling_and_retry,
            example_4_complex_dag,
            example_5_state_persistence,
            example_6_monitoring,
            example_7_data_pipeline,
        ]
        if 1 <= example_num <= len(examples):
            examples[example_num - 1]()
        else:
            print(f"Invalid example number. Choose 1-{len(examples)}")
    else:
        run_all_examples()

"""
Production-ready example of WorkflowOrchestrator with a 5-step data pipeline.

This example demonstrates:
- Complex DAG with parallel execution
- Retry logic with exponential backoff
- Resource pooling for API rate limiting
- Checkpoint/resume functionality
- Error handling and recovery

The workflow represents a typical data processing pipeline:
1. Fetch raw data from API
2. Validate data quality (parallel with step 3)
3. Enrich data from external source (parallel with step 2)
4. Transform and aggregate data (depends on steps 2 & 3)
5. Store results in database
"""

import asyncio
import random
import time
from typing import Any, Dict

from agno.workflow.orchestrator import (
    OrchestratorState,
    ResourcePool,
    WorkflowOrchestrator,
    WorkflowStep,
)


# ============================================================================
# Step Functions
# ============================================================================


async def fetch_raw_data(workflow_id: str, step_id: str, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Step 1: Fetch raw data from external API."""
    print(f"[{step_id}] Fetching raw data from API...")

    # Simulate API call
    await asyncio.sleep(1.0)

    # Simulate occasional failures (20% chance)
    if random.random() < 0.2:
        raise Exception("API temporarily unavailable")

    raw_data = {
        "records": [
            {"id": 1, "value": 100, "category": "A"},
            {"id": 2, "value": 200, "category": "B"},
            {"id": 3, "value": 150, "category": "A"},
            {"id": 4, "value": 300, "category": "C"},
            {"id": 5, "value": 250, "category": "B"},
        ],
        "fetch_timestamp": time.time(),
    }

    print(f"[{step_id}] Fetched {len(raw_data['records'])} records")

    # Store in shared context
    context["raw_data"] = raw_data

    return raw_data


async def validate_data(
    workflow_id: str, step_id: str, context: Dict[str, Any], results: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """Step 2: Validate data quality (runs in parallel with enrich_data)."""
    print(f"[{step_id}] Validating data quality...")

    # Get raw data from previous step
    raw_data = results.get("fetch_raw_data", {})
    records = raw_data.get("records", [])

    # Simulate validation
    await asyncio.sleep(0.5)

    validation_results = {
        "total_records": len(records),
        "valid_records": len([r for r in records if r.get("value", 0) > 0]),
        "invalid_records": len([r for r in records if r.get("value", 0) <= 0]),
        "quality_score": 0.95,
        "validation_timestamp": time.time(),
    }

    print(
        f"[{step_id}] Validation complete: {validation_results['valid_records']}/{validation_results['total_records']} valid"
    )

    return validation_results


async def enrich_data(
    workflow_id: str, step_id: str, context: Dict[str, Any], results: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """Step 3: Enrich data from external source (runs in parallel with validate_data)."""
    print(f"[{step_id}] Enriching data from external source...")

    # Get raw data from previous step
    raw_data = results.get("fetch_raw_data", {})
    records = raw_data.get("records", [])

    # Simulate external API calls for enrichment
    await asyncio.sleep(1.5)

    # Add enrichment metadata
    category_metadata = {
        "A": {"name": "Premium", "discount": 0.1},
        "B": {"name": "Standard", "discount": 0.05},
        "C": {"name": "Basic", "discount": 0.0},
    }

    enriched_records = []
    for record in records:
        category = record.get("category", "")
        metadata = category_metadata.get(category, {})
        enriched_record = {
            **record,
            "category_name": metadata.get("name", "Unknown"),
            "discount_rate": metadata.get("discount", 0.0),
        }
        enriched_records.append(enriched_record)

    enrichment_result = {"enriched_records": enriched_records, "enrichment_timestamp": time.time()}

    print(f"[{step_id}] Enriched {len(enriched_records)} records")

    return enrichment_result


async def transform_and_aggregate(
    workflow_id: str, step_id: str, context: Dict[str, Any], results: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """Step 4: Transform and aggregate data (depends on both validation and enrichment)."""
    print(f"[{step_id}] Transforming and aggregating data...")

    # Get results from dependencies
    validation_results = results.get("validate_data", {})
    enrichment_result = results.get("enrich_data", {})

    enriched_records = enrichment_result.get("enriched_records", [])

    # Simulate transformation
    await asyncio.sleep(0.8)

    # Calculate aggregated metrics
    category_totals = {}
    for record in enriched_records:
        category = record.get("category_name", "Unknown")
        value = record.get("value", 0)
        discount = record.get("discount_rate", 0)
        final_value = value * (1 - discount)

        if category not in category_totals:
            category_totals[category] = {"count": 0, "total_value": 0, "avg_value": 0}

        category_totals[category]["count"] += 1
        category_totals[category]["total_value"] += final_value

    # Calculate averages
    for category, data in category_totals.items():
        data["avg_value"] = data["total_value"] / data["count"]

    transformed_data = {
        "aggregated_metrics": category_totals,
        "total_records": len(enriched_records),
        "quality_score": validation_results.get("quality_score", 0),
        "transform_timestamp": time.time(),
    }

    print(f"[{step_id}] Aggregated data into {len(category_totals)} categories")

    # Store in context for final step
    context["transformed_data"] = transformed_data

    return transformed_data


async def store_results(
    workflow_id: str, step_id: str, context: Dict[str, Any], results: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """Step 5: Store results in database."""
    print(f"[{step_id}] Storing results in database...")

    # Get transformed data
    transformed_data = results.get("transform_and_aggregate", {})

    # Simulate database write
    await asyncio.sleep(0.5)

    # Simulate occasional write failures (10% chance)
    if random.random() < 0.1:
        raise Exception("Database write failed")

    storage_result = {
        "records_stored": transformed_data.get("total_records", 0),
        "categories_stored": len(transformed_data.get("aggregated_metrics", {})),
        "storage_timestamp": time.time(),
        "database": "production_db",
    }

    print(f"[{step_id}] Stored {storage_result['records_stored']} records")

    return storage_result


# ============================================================================
# Main Example
# ============================================================================


async def run_example():
    """Run the complete 5-step workflow example."""
    print("=" * 80)
    print("Workflow Orchestrator Example: Data Pipeline")
    print("=" * 80)

    # Define resource pools for rate limiting
    api_pool = ResourcePool(name="api_calls", max_concurrent=2)
    db_pool = ResourcePool(name="database", max_concurrent=1)

    # Define workflow steps with dependencies
    steps = [
        # Step 1: Fetch raw data (no dependencies)
        WorkflowStep(
            step_id="fetch_raw_data",
            name="Fetch Raw Data",
            function=fetch_raw_data,
            dependencies=[],
            retry_count=3,
            retry_delay=1.0,
            retry_backoff=2.0,
            timeout=10.0,
            required=True,
            resource_pool="api_calls",
        ),
        # Step 2: Validate data (depends on fetch, runs in parallel with enrich)
        WorkflowStep(
            step_id="validate_data",
            name="Validate Data Quality",
            function=validate_data,
            dependencies=["fetch_raw_data"],
            retry_count=2,
            retry_delay=0.5,
            retry_backoff=2.0,
            timeout=5.0,
            required=True,
        ),
        # Step 3: Enrich data (depends on fetch, runs in parallel with validate)
        WorkflowStep(
            step_id="enrich_data",
            name="Enrich Data",
            function=enrich_data,
            dependencies=["fetch_raw_data"],
            retry_count=3,
            retry_delay=1.0,
            retry_backoff=2.0,
            timeout=15.0,
            required=True,
            resource_pool="api_calls",
        ),
        # Step 4: Transform and aggregate (depends on both validate and enrich)
        WorkflowStep(
            step_id="transform_and_aggregate",
            name="Transform and Aggregate",
            function=transform_and_aggregate,
            dependencies=["validate_data", "enrich_data"],
            retry_count=2,
            retry_delay=0.5,
            retry_backoff=2.0,
            timeout=10.0,
            required=True,
        ),
        # Step 5: Store results (depends on transform)
        WorkflowStep(
            step_id="store_results",
            name="Store Results",
            function=store_results,
            dependencies=["transform_and_aggregate"],
            retry_count=3,
            retry_delay=1.0,
            retry_backoff=2.0,
            timeout=10.0,
            required=True,
            resource_pool="database",
        ),
    ]

    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        workflow_id="data_pipeline_v1",
        steps=steps,
        max_parallelism=3,  # Allow up to 3 steps to run in parallel
        checkpoint_interval=5.0,  # Checkpoint every 5 seconds
        enable_checkpointing=True,
    )

    # Add resource pools
    orchestrator.add_resource_pool(api_pool)
    orchestrator.add_resource_pool(db_pool)

    # Initial context
    initial_context = {
        "pipeline_run_id": "run_001",
        "environment": "production",
        "user_id": "user_123",
    }

    print("\nStarting workflow execution...")
    print("-" * 80)

    # Execute workflow
    try:
        result = await orchestrator.execute(initial_context=initial_context)

        print("\n" + "=" * 80)
        print("Workflow Execution Complete!")
        print("=" * 80)

        # Display results
        workflow_result = result["workflow_result"]
        print(f"\nWorkflow ID: {workflow_result['workflow_id']}")
        print(f"State: {workflow_result['state']}")
        print(f"Total Steps: {workflow_result['total_steps']}")
        print(f"Completed Steps: {workflow_result['completed_steps']}")
        print(f"Failed Steps: {workflow_result['failed_steps']}")
        print(f"Execution Time: {workflow_result['execution_time']:.2f}s")

        # Display step execution details
        print("\n" + "-" * 80)
        print("Step Execution Details:")
        print("-" * 80)
        for step_id, step_result in result["step_results"].items():
            print(f"\n{step_id}:")
            print(f"  Status: {step_result.status.value}")
            print(f"  Execution Time: {step_result.execution_time:.2f}s")
            print(f"  Attempts: {step_result.attempt}")
            if step_result.error:
                print(f"  Error: {step_result.error}")

        # Display final data
        if "transformed_data" in workflow_result["context"]:
            transformed_data = workflow_result["context"]["transformed_data"]
            print("\n" + "-" * 80)
            print("Final Aggregated Metrics:")
            print("-" * 80)
            for category, metrics in transformed_data["aggregated_metrics"].items():
                print(f"\n{category}:")
                print(f"  Count: {metrics['count']}")
                print(f"  Total Value: ${metrics['total_value']:.2f}")
                print(f"  Average Value: ${metrics['avg_value']:.2f}")

        # Show execution graph
        print("\n" + "-" * 80)
        print("Execution Graph:")
        print("-" * 80)
        graph = orchestrator.get_execution_graph()
        for node in graph["nodes"]:
            deps = ", ".join(node["dependencies"]) if node["dependencies"] else "None"
            print(f"{node['name']} ({node['id']}): {node['status']} [deps: {deps}]")

        return result

    except Exception as e:
        print(f"\nWorkflow execution failed: {e}")
        raise


async def run_checkpoint_resume_example():
    """Example demonstrating checkpoint and resume functionality."""
    print("\n" + "=" * 80)
    print("Checkpoint/Resume Example")
    print("=" * 80)

    # Define simple steps for demonstration
    async def step_a(**kwargs):
        print("Executing Step A...")
        await asyncio.sleep(1)
        return {"result": "A"}

    async def step_b(**kwargs):
        print("Executing Step B...")
        await asyncio.sleep(1)
        return {"result": "B"}

    async def step_c(**kwargs):
        print("Executing Step C...")
        await asyncio.sleep(1)
        # Simulate failure
        raise Exception("Step C failed - will be retried on resume")

    steps = [
        WorkflowStep(step_id="step_a", name="Step A", function=step_a, dependencies=[], retry_count=1),
        WorkflowStep(step_id="step_b", name="Step B", function=step_b, dependencies=["step_a"], retry_count=1),
        WorkflowStep(
            step_id="step_c", name="Step C", function=step_c, dependencies=["step_b"], retry_count=1, required=False
        ),
    ]

    orchestrator = WorkflowOrchestrator(
        workflow_id="checkpoint_demo", steps=steps, max_parallelism=2, enable_checkpointing=True
    )

    print("\nFirst execution (will fail at Step C)...")
    try:
        await orchestrator.execute()
    except Exception as e:
        print(f"Execution failed as expected: {e}")

    # Get checkpoint
    if orchestrator.checkpoints:
        checkpoint = orchestrator.checkpoints[-1]
        print(f"\nCheckpoint created at {checkpoint.checkpoint_time}")
        print(f"Completed steps: {checkpoint.completed_steps}")
        print(f"Failed steps: {checkpoint.failed_steps}")

        # Create new orchestrator and resume
        print("\nResuming from checkpoint...")
        new_orchestrator = WorkflowOrchestrator(
            workflow_id="checkpoint_demo",
            steps=steps,
            max_parallelism=2,
            enable_checkpointing=True,
        )

        result = await new_orchestrator.execute(resume_from_checkpoint=checkpoint)
        print(f"\nResumed workflow state: {result['workflow_result']['state']}")


# ============================================================================
# Entry Point
# ============================================================================


if __name__ == "__main__":
    # Run main example
    result = asyncio.run(run_example())

    print("\n\n")

    # Run checkpoint/resume example
    asyncio.run(run_checkpoint_resume_example())

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)

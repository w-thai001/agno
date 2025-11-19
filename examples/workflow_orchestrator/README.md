# Workflow Orchestrator Examples

This directory contains production-ready examples of using the Agno Workflow Orchestrator FSA.

## Overview

The Workflow Orchestrator is a powerful FSA-based system for executing complex workflows with:

- **DAG-based dependency resolution** - Automatically determines execution order based on step dependencies
- **Parallel execution** - Executes independent steps in parallel for maximum efficiency
- **Automatic retry with exponential backoff** - Handles transient failures gracefully
- **Checkpoint/resume** - Supports long-running workflows that can be paused and resumed
- **Resource pooling** - Throttles execution to respect API rate limits and resource constraints

## Installation

First, install the required dependencies:

```bash
pip install networkx
```

## Examples

### 1. Data Pipeline Example (`data_pipeline_example.py`)

A comprehensive 5-step data processing pipeline demonstrating all orchestrator features:

```
Step 1: Fetch Raw Data
         ├─> Step 2: Validate Data ────┐
         └─> Step 3: Enrich Data ───────┤
                                        ├─> Step 4: Transform & Aggregate
                                        │            └─> Step 5: Store Results
```

**Features demonstrated:**
- Complex DAG with parallel execution (steps 2 & 3 run in parallel)
- Retry logic with exponential backoff
- Resource pools for API rate limiting
- Timeout handling
- Error recovery
- Shared context across steps

**Run the example:**

```bash
cd /home/user/agno
python examples/workflow_orchestrator/data_pipeline_example.py
```

**Expected output:**
```
========================================================================
Workflow Orchestrator Example: Data Pipeline
========================================================================

Starting workflow execution...
------------------------------------------------------------------------
[fetch_raw_data] Fetching raw data from API...
[fetch_raw_data] Fetched 5 records
[validate_data] Validating data quality...
[enrich_data] Enriching data from external source...
[enrich_data] Enriched 5 records
[validate_data] Validation complete: 5/5 valid
[transform_and_aggregate] Transforming and aggregating data...
[transform_and_aggregate] Aggregated data into 3 categories
[store_results] Storing results in database...
[store_results] Stored 5 records

========================================================================
Workflow Execution Complete!
========================================================================

Workflow ID: data_pipeline_v1
State: completed
Total Steps: 5
Completed Steps: 5
Failed Steps: 0
Execution Time: X.XXs
```

## Usage

### Basic Workflow

```python
import asyncio
from agno.workflow.orchestrator import (
    WorkflowOrchestrator,
    WorkflowStep,
    ResourcePool,
)

# Define step functions
async def step1(**kwargs):
    print("Step 1 executing...")
    return {"result": "data_from_step1"}

async def step2(results, **kwargs):
    # Access results from dependencies
    data = results.get("step1", {})
    print(f"Step 2 executing with data: {data}")
    return {"result": "data_from_step2"}

# Define workflow
steps = [
    WorkflowStep(
        step_id="step1",
        name="First Step",
        function=step1,
        dependencies=[],  # No dependencies
        retry_count=3,
        retry_delay=1.0,
        retry_backoff=2.0,
    ),
    WorkflowStep(
        step_id="step2",
        name="Second Step",
        function=step2,
        dependencies=["step1"],  # Depends on step1
        retry_count=2,
    ),
]

# Create orchestrator
orchestrator = WorkflowOrchestrator(
    workflow_id="my_workflow",
    steps=steps,
    max_parallelism=5,
)

# Execute
result = await orchestrator.execute(
    initial_context={"user_id": "123"}
)

print(f"Workflow state: {result['workflow_result']['state']}")
```

### With Resource Pools

```python
# Define resource pools for rate limiting
api_pool = ResourcePool(name="api_calls", max_concurrent=2)
db_pool = ResourcePool(name="database", max_concurrent=1)

# Assign steps to resource pools
steps = [
    WorkflowStep(
        step_id="fetch_data",
        name="Fetch from API",
        function=fetch_data,
        dependencies=[],
        resource_pool="api_calls",  # Limited to 2 concurrent
    ),
    WorkflowStep(
        step_id="save_data",
        name="Save to DB",
        function=save_data,
        dependencies=["fetch_data"],
        resource_pool="database",  # Limited to 1 concurrent
    ),
]

orchestrator = WorkflowOrchestrator(steps=steps)
orchestrator.add_resource_pool(api_pool)
orchestrator.add_resource_pool(db_pool)
```

### Checkpoint and Resume

```python
# First execution
orchestrator = WorkflowOrchestrator(
    steps=steps,
    enable_checkpointing=True,
    checkpoint_interval=10.0,  # Checkpoint every 10 seconds
)

try:
    result = await orchestrator.execute()
except Exception:
    # Save checkpoint
    checkpoint = orchestrator.checkpoints[-1]

# Later, resume from checkpoint
new_orchestrator = WorkflowOrchestrator(steps=steps)
result = await new_orchestrator.execute(
    resume_from_checkpoint=checkpoint
)
```

## Step Function Signature

Step functions receive the following parameters:

```python
async def my_step(
    workflow_id: str,      # ID of the workflow
    step_id: str,          # ID of this step
    context: Dict,         # Shared context (mutable)
    results: Dict,         # Results from dependency steps
    attempt: int,          # Current attempt number (for retries)
    **kwargs               # Additional kwargs from WorkflowStep.kwargs
) -> Any:
    """Step function implementation."""

    # Access results from dependencies
    previous_result = results.get("previous_step_id")

    # Update shared context
    context["my_data"] = "shared_value"

    # Return result (available to dependent steps)
    return {"output": "my_result"}
```

## Configuration Options

### WorkflowStep

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `step_id` | str | Required | Unique identifier for the step |
| `name` | str | Required | Human-readable name |
| `function` | Callable | Required | Step function to execute |
| `dependencies` | List[str] | `[]` | List of step IDs this step depends on |
| `retry_count` | int | `3` | Number of retry attempts |
| `retry_delay` | float | `1.0` | Initial delay between retries (seconds) |
| `retry_backoff` | float | `2.0` | Exponential backoff multiplier |
| `timeout` | float | `None` | Step timeout in seconds |
| `required` | bool | `True` | Whether step failure stops the workflow |
| `resource_pool` | str | `None` | Name of resource pool to use |
| `kwargs` | Dict | `{}` | Additional kwargs passed to function |

### WorkflowOrchestrator

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workflow_id` | str | Auto-generated | Unique workflow identifier |
| `steps` | List[WorkflowStep] | `[]` | Workflow steps |
| `max_parallelism` | int | `10` | Maximum concurrent steps |
| `checkpoint_interval` | float | `None` | Seconds between checkpoints |
| `enable_checkpointing` | bool | `True` | Enable checkpoint functionality |
| `resource_pools` | Dict | `{}` | Resource pools for throttling |

## Advanced Features

### Error Handling

```python
# Non-required step (won't stop workflow if it fails)
WorkflowStep(
    step_id="optional_step",
    name="Optional Processing",
    function=optional_function,
    required=False,  # Failure won't stop workflow
)
```

### Custom Retry Strategy

```python
WorkflowStep(
    step_id="api_call",
    name="External API Call",
    function=call_api,
    retry_count=5,          # Try 5 times
    retry_delay=0.5,        # Start with 0.5s delay
    retry_backoff=3.0,      # Triple the delay each time
    timeout=30.0,           # 30s timeout per attempt
)
# Retry delays: 0.5s, 1.5s, 4.5s, 13.5s, 40.5s
```

### Execution Graph

```python
result = await orchestrator.execute()

# Get visual representation of execution
graph = orchestrator.get_execution_graph()
for node in graph["nodes"]:
    print(f"{node['name']}: {node['status']}")
```

## Best Practices

1. **Use meaningful step IDs** - They appear in logs and help with debugging
2. **Set appropriate timeouts** - Prevent steps from hanging indefinitely
3. **Mark optional steps as non-required** - Allow workflows to complete partially
4. **Use resource pools for external APIs** - Respect rate limits
5. **Enable checkpointing for long workflows** - Allow resumption after failures
6. **Structure dependencies carefully** - Maximize parallel execution
7. **Return structured data from steps** - Make results easy to consume

## Integration with Agno

The Workflow Orchestrator can be integrated with Agno workflows:

```python
from agno.workflow import Workflow
from agno.workflow.orchestrator import WorkflowOrchestrator, WorkflowStep

class MyWorkflow(Workflow):
    def run(self):
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            workflow_id=self.workflow_id,
            steps=self.define_steps(),
            max_parallelism=5,
        )

        # Execute and return result
        import asyncio
        result = asyncio.run(orchestrator.execute(
            initial_context={
                "session_id": self.session_id,
                "user_id": self.user_id,
            }
        ))

        # Update workflow session state with results
        self.session_state["orchestrator_results"] = result

        return result
```

## Troubleshooting

### Workflow gets stuck

Check for:
- Circular dependencies in your DAG
- All required steps completing successfully
- Sufficient `max_parallelism` setting

### Steps not running in parallel

Ensure:
- Steps don't have unnecessary dependencies
- `max_parallelism` is greater than 1
- Resource pools aren't too restrictive

### Memory issues with checkpoints

- Reduce `checkpoint_interval` or disable checkpointing
- Limit the size of data stored in context
- Return minimal data from step functions

## License

This example is part of the Agno framework.

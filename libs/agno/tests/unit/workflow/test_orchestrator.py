"""Unit tests for WorkflowOrchestrator."""

import asyncio
import time
from typing import Any, Dict

import pytest

from agno.workflow.orchestrator import (
    OrchestratorState,
    ResourcePool,
    StepStatus,
    WorkflowOrchestrator,
    WorkflowStep,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def simple_steps():
    """Simple linear workflow: A -> B -> C"""

    async def step_a(**kwargs):
        await asyncio.sleep(0.1)
        return {"value": "A"}

    async def step_b(**kwargs):
        await asyncio.sleep(0.1)
        return {"value": "B"}

    async def step_c(**kwargs):
        await asyncio.sleep(0.1)
        return {"value": "C"}

    return [
        WorkflowStep(step_id="step_a", name="Step A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="step_b", name="Step B", function=step_b, dependencies=["step_a"]),
        WorkflowStep(step_id="step_c", name="Step C", function=step_c, dependencies=["step_b"]),
    ]


@pytest.fixture
def parallel_steps():
    """Workflow with parallel execution:
          A
         / \\
        B   C
         \\ /
          D
    """

    async def step_a(**kwargs):
        await asyncio.sleep(0.1)
        return {"value": "A"}

    async def step_b(**kwargs):
        await asyncio.sleep(0.2)
        return {"value": "B"}

    async def step_c(**kwargs):
        await asyncio.sleep(0.2)
        return {"value": "C"}

    async def step_d(results, **kwargs):
        await asyncio.sleep(0.1)
        b_value = results.get("step_b", {}).get("value")
        c_value = results.get("step_c", {}).get("value")
        return {"value": f"{b_value}+{c_value}"}

    return [
        WorkflowStep(step_id="step_a", name="Step A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="step_b", name="Step B", function=step_b, dependencies=["step_a"]),
        WorkflowStep(step_id="step_c", name="Step C", function=step_c, dependencies=["step_a"]),
        WorkflowStep(step_id="step_d", name="Step D", function=step_d, dependencies=["step_b", "step_c"]),
    ]


# ============================================================================
# Basic Tests
# ============================================================================


@pytest.mark.asyncio
async def test_simple_workflow_execution(simple_steps):
    """Test basic sequential workflow execution."""
    orchestrator = WorkflowOrchestrator(workflow_id="test_simple", steps=simple_steps, max_parallelism=1)

    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["workflow_result"]["completed_steps"] == 3
    assert result["workflow_result"]["failed_steps"] == 0
    assert len(result["step_results"]) == 3
    assert orchestrator.state == OrchestratorState.COMPLETED


@pytest.mark.asyncio
async def test_parallel_workflow_execution(parallel_steps):
    """Test workflow with parallel execution."""
    orchestrator = WorkflowOrchestrator(workflow_id="test_parallel", steps=parallel_steps, max_parallelism=5)

    start_time = time.time()
    result = await orchestrator.execute()
    execution_time = time.time() - start_time

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["workflow_result"]["completed_steps"] == 4
    assert result["workflow_result"]["failed_steps"] == 0

    # Verify steps B and C ran in parallel
    # Sequential: A(0.1) + B(0.2) + C(0.2) + D(0.1) = 0.6s
    # Parallel: A(0.1) + max(B(0.2), C(0.2)) + D(0.1) = 0.4s
    assert execution_time < 0.5  # Should be closer to 0.4s

    # Verify step D received results from B and C
    step_d_result = result["step_results"]["step_d"]
    assert step_d_result.output["value"] == "B+C"


@pytest.mark.asyncio
async def test_dag_building():
    """Test DAG construction and cycle detection."""

    async def step_func(**kwargs):
        return {}

    # Valid DAG
    steps = [
        WorkflowStep(step_id="a", name="A", function=step_func, dependencies=[]),
        WorkflowStep(step_id="b", name="B", function=step_func, dependencies=["a"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()
    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value


@pytest.mark.asyncio
async def test_circular_dependency_detection():
    """Test that circular dependencies are detected."""

    async def step_func(**kwargs):
        return {}

    # Circular dependency: A -> B -> C -> A
    steps = [
        WorkflowStep(step_id="a", name="A", function=step_func, dependencies=["c"]),
        WorkflowStep(step_id="b", name="B", function=step_func, dependencies=["a"]),
        WorkflowStep(step_id="c", name="C", function=step_func, dependencies=["b"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)

    with pytest.raises(ValueError, match="cycles"):
        await orchestrator.execute()


@pytest.mark.asyncio
async def test_invalid_dependency():
    """Test that invalid dependencies are detected."""

    async def step_func(**kwargs):
        return {}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_func, dependencies=["nonexistent"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)

    with pytest.raises(ValueError, match="unknown step"):
        await orchestrator.execute()


# ============================================================================
# Retry Logic Tests
# ============================================================================


@pytest.mark.asyncio
async def test_retry_with_eventual_success():
    """Test retry logic with eventual success."""
    attempt_count = {"count": 0}

    async def flaky_step(**kwargs):
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise Exception("Temporary failure")
        return {"success": True}

    steps = [
        WorkflowStep(
            step_id="flaky",
            name="Flaky Step",
            function=flaky_step,
            dependencies=[],
            retry_count=5,
            retry_delay=0.1,
            retry_backoff=1.5,
        ),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["step_results"]["flaky"].status == StepStatus.COMPLETED
    assert result["step_results"]["flaky"].attempt == 3
    assert attempt_count["count"] == 3


@pytest.mark.asyncio
async def test_retry_exhaustion():
    """Test that steps fail after exhausting retries."""
    attempt_count = {"count": 0}

    async def always_fail(**kwargs):
        attempt_count["count"] += 1
        raise Exception("Permanent failure")

    steps = [
        WorkflowStep(
            step_id="failing",
            name="Always Fails",
            function=always_fail,
            dependencies=[],
            retry_count=3,
            retry_delay=0.05,
            retry_backoff=1.0,
        ),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.FAILED.value
    assert result["step_results"]["failing"].status == StepStatus.FAILED
    assert result["step_results"]["failing"].attempt == 3
    assert attempt_count["count"] == 3


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test exponential backoff timing."""
    timestamps = []

    async def track_attempts(**kwargs):
        timestamps.append(time.time())
        if len(timestamps) < 3:
            raise Exception("Retry me")
        return {}

    steps = [
        WorkflowStep(
            step_id="backoff",
            name="Backoff Test",
            function=track_attempts,
            dependencies=[],
            retry_count=3,
            retry_delay=0.1,  # Initial delay
            retry_backoff=2.0,  # Double each time
        ),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    await orchestrator.execute()

    # Verify backoff delays
    # Attempt 1 -> wait 0.1s -> Attempt 2 -> wait 0.2s -> Attempt 3
    delay1 = timestamps[1] - timestamps[0]
    delay2 = timestamps[2] - timestamps[1]

    assert 0.08 < delay1 < 0.15  # ~0.1s
    assert 0.18 < delay2 < 0.25  # ~0.2s (doubled)


# ============================================================================
# Resource Pool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_resource_pool_throttling():
    """Test that resource pools limit concurrency."""
    concurrent_count = {"current": 0, "max": 0}

    async def track_concurrency(**kwargs):
        concurrent_count["current"] += 1
        concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["current"])
        await asyncio.sleep(0.1)
        concurrent_count["current"] -= 1
        return {}

    # Create 5 steps but limit to 2 concurrent via resource pool
    steps = [
        WorkflowStep(
            step_id=f"step_{i}",
            name=f"Step {i}",
            function=track_concurrency,
            dependencies=[],
            resource_pool="limited",
        )
        for i in range(5)
    ]

    orchestrator = WorkflowOrchestrator(steps=steps, max_parallelism=10)
    orchestrator.add_resource_pool(ResourcePool(name="limited", max_concurrent=2))

    await orchestrator.execute()

    # Max concurrent should be 2 (resource pool limit)
    assert concurrent_count["max"] == 2


@pytest.mark.asyncio
async def test_global_parallelism_limit():
    """Test global max_parallelism setting."""
    concurrent_count = {"current": 0, "max": 0}

    async def track_concurrency(**kwargs):
        concurrent_count["current"] += 1
        concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["current"])
        await asyncio.sleep(0.1)
        concurrent_count["current"] -= 1
        return {}

    # Create 10 steps with global limit of 3
    steps = [
        WorkflowStep(step_id=f"step_{i}", name=f"Step {i}", function=track_concurrency, dependencies=[])
        for i in range(10)
    ]

    orchestrator = WorkflowOrchestrator(steps=steps, max_parallelism=3)
    await orchestrator.execute()

    # Max concurrent should be 3 (global limit)
    assert concurrent_count["max"] == 3


# ============================================================================
# Context and Results Tests
# ============================================================================


@pytest.mark.asyncio
async def test_shared_context():
    """Test that context is shared across steps."""

    async def step_a(context, **kwargs):
        context["shared_value"] = "from_A"
        return {"a": 1}

    async def step_b(context, **kwargs):
        assert context.get("shared_value") == "from_A"
        context["shared_value"] = "from_B"
        return {"b": 2}

    async def step_c(context, **kwargs):
        assert context.get("shared_value") == "from_B"
        return {"c": 3}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="b", name="B", function=step_b, dependencies=["a"]),
        WorkflowStep(step_id="c", name="C", function=step_c, dependencies=["b"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute(initial_context={"initial": "value"})

    # Verify context
    assert result["workflow_result"]["context"]["initial"] == "value"
    assert result["workflow_result"]["context"]["shared_value"] == "from_B"


@pytest.mark.asyncio
async def test_dependency_results():
    """Test that steps receive results from dependencies."""

    async def step_a(**kwargs):
        return {"value": 10}

    async def step_b(**kwargs):
        return {"value": 20}

    async def step_c(results, **kwargs):
        a_value = results.get("step_a", {}).get("value", 0)
        b_value = results.get("step_b", {}).get("value", 0)
        return {"sum": a_value + b_value}

    steps = [
        WorkflowStep(step_id="step_a", name="A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="step_b", name="B", function=step_b, dependencies=[]),
        WorkflowStep(step_id="step_c", name="C", function=step_c, dependencies=["step_a", "step_b"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["step_results"]["step_c"].output["sum"] == 30


# ============================================================================
# Checkpoint Tests
# ============================================================================


@pytest.mark.asyncio
async def test_checkpoint_creation():
    """Test that checkpoints are created."""

    async def step_a(**kwargs):
        await asyncio.sleep(0.2)
        return {}

    async def step_b(**kwargs):
        await asyncio.sleep(0.2)
        return {}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="b", name="B", function=step_b, dependencies=["a"]),
    ]

    orchestrator = WorkflowOrchestrator(
        steps=steps, enable_checkpointing=True, checkpoint_interval=0.15  # Checkpoint every 0.15s
    )

    await orchestrator.execute()

    # Should have created at least one checkpoint
    assert len(orchestrator.checkpoints) > 0


@pytest.mark.asyncio
async def test_checkpoint_resume():
    """Test resuming from checkpoint."""

    async def step_a(**kwargs):
        return {"a": 1}

    async def step_b(**kwargs):
        raise Exception("Step B fails")

    async def step_c(**kwargs):
        return {"c": 3}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_a, dependencies=[], retry_count=1),
        WorkflowStep(step_id="b", name="B", function=step_b, dependencies=["a"], retry_count=1, required=False),
        WorkflowStep(step_id="c", name="C", function=step_c, dependencies=["a"], retry_count=1),
    ]

    # First execution
    orchestrator1 = WorkflowOrchestrator(workflow_id="checkpoint_test", steps=steps, enable_checkpointing=True)

    result1 = await orchestrator1.execute()

    # Step A and C should complete, B should fail
    assert "a" in result1["step_results"]
    assert "c" in result1["step_results"]
    assert result1["step_results"]["b"].status == StepStatus.FAILED

    # Create checkpoint
    checkpoint = orchestrator1._create_checkpoint()
    assert "a" in checkpoint.completed_steps
    assert "c" in checkpoint.completed_steps
    assert "b" in checkpoint.failed_steps

    # Resume from checkpoint
    orchestrator2 = WorkflowOrchestrator(workflow_id="checkpoint_test", steps=steps)
    orchestrator2.load_checkpoint(checkpoint)

    # Verify loaded state
    assert "a" in orchestrator2.completed_steps
    assert "c" in orchestrator2.completed_steps
    assert "b" in orchestrator2.failed_steps


# ============================================================================
# Timeout Tests
# ============================================================================


@pytest.mark.asyncio
async def test_step_timeout():
    """Test that steps timeout correctly."""

    async def slow_step(**kwargs):
        await asyncio.sleep(2.0)
        return {}

    steps = [
        WorkflowStep(
            step_id="slow",
            name="Slow Step",
            function=slow_step,
            dependencies=[],
            timeout=0.1,  # 100ms timeout
            retry_count=1,
        ),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.FAILED.value
    assert result["step_results"]["slow"].status == StepStatus.FAILED


# ============================================================================
# Required vs Optional Steps Tests
# ============================================================================


@pytest.mark.asyncio
async def test_required_step_failure_stops_workflow():
    """Test that required step failure stops the workflow."""

    async def step_a(**kwargs):
        return {}

    async def step_b(**kwargs):
        raise Exception("Required step failed")

    async def step_c(**kwargs):
        return {}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="b", name="B", function=step_b, dependencies=["a"], required=True, retry_count=1),
        WorkflowStep(step_id="c", name="C", function=step_c, dependencies=["b"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.FAILED.value
    assert "a" in result["step_results"]
    assert "b" in result["step_results"]
    assert "c" not in result["step_results"]  # Should not execute


@pytest.mark.asyncio
async def test_optional_step_failure_continues_workflow():
    """Test that optional step failure doesn't stop the workflow."""

    async def step_a(**kwargs):
        return {}

    async def step_b(**kwargs):
        raise Exception("Optional step failed")

    async def step_c(**kwargs):
        return {}

    steps = [
        WorkflowStep(step_id="a", name="A", function=step_a, dependencies=[]),
        WorkflowStep(step_id="b", name="B", function=step_b, dependencies=[], required=False, retry_count=1),
        WorkflowStep(step_id="c", name="C", function=step_c, dependencies=["a"]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert "a" in result["step_results"]
    assert "b" in result["step_results"]
    assert "c" in result["step_results"]
    assert result["step_results"]["b"].status == StepStatus.FAILED
    assert result["step_results"]["c"].status == StepStatus.COMPLETED


# ============================================================================
# Execution Graph Tests
# ============================================================================


@pytest.mark.asyncio
async def test_execution_graph(parallel_steps):
    """Test execution graph generation."""
    orchestrator = WorkflowOrchestrator(steps=parallel_steps)
    await orchestrator.execute()

    graph = orchestrator.get_execution_graph()

    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == 4  # A, B, C, D

    # Check node data
    node_ids = [node["id"] for node in graph["nodes"]]
    assert "step_a" in node_ids
    assert "step_b" in node_ids
    assert "step_c" in node_ids
    assert "step_d" in node_ids

    # All steps should be completed
    for node in graph["nodes"]:
        assert node["status"] == "completed"


# ============================================================================
# Sync Function Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sync_function_execution():
    """Test that synchronous functions work correctly."""

    def sync_step(**kwargs):
        time.sleep(0.1)
        return {"sync": True}

    steps = [
        WorkflowStep(step_id="sync", name="Sync Step", function=sync_step, dependencies=[]),
    ]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["step_results"]["sync"].output["sync"] is True


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_empty_workflow():
    """Test workflow with no steps."""
    orchestrator = WorkflowOrchestrator(steps=[])
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["workflow_result"]["completed_steps"] == 0


@pytest.mark.asyncio
async def test_single_step_workflow():
    """Test workflow with single step."""

    async def single_step(**kwargs):
        return {"result": "done"}

    steps = [WorkflowStep(step_id="only", name="Only Step", function=single_step, dependencies=[])]

    orchestrator = WorkflowOrchestrator(steps=steps)
    result = await orchestrator.execute()

    assert result["workflow_result"]["state"] == OrchestratorState.COMPLETED.value
    assert result["workflow_result"]["completed_steps"] == 1
    assert result["step_results"]["only"].output["result"] == "done"

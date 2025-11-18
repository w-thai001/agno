"""
Comprehensive test suite for WorkflowEngineFSA.

Tests cover:
- Workflow definition and validation
- DAG construction and cycle detection
- Task execution with context
- Conditional branching
- Parallel task execution
- Workflow scheduling
- State tracking
- Task failure handling with retry
- Compensation logic
- Workflow versioning
- Workflow analysis
- State persistence and recovery
- Workflow resumption
- Workflow visualization
- Metrics collection
- Edge cases and error handling
- Concurrent workflow execution
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from agno.fsas.workflow_engine_fsa import (
    BranchResult,
    Change,
    CompensationResult,
    Condition,
    DAG,
    DecisionNode,
    FailureHandlingResult,
    ParallelResult,
    PersistenceResult,
    ResumeResult,
    RetryPolicy,
    Schedule,
    ScheduleResult,
    StateEntry,
    Task,
    TaskResult,
    TaskStatus,
    TaskType,
    ValidationResult,
    VersionEntry,
    WorkflowAnalysis,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowEngineFSA,
    WorkflowExecutionResult,
    WorkflowMetrics,
    WorkflowState,
    WorkflowStatus,
    WorkflowVisualization,
)


# ==================== Fixtures ====================

@pytest.fixture
def temp_persistence_path():
    """Create temporary directory for persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def workflow_engine_fsa(temp_persistence_path):
    """Create WorkflowEngineFSA instance for testing."""
    return WorkflowEngineFSA(
        name="TestWorkflowEngine",
        persistence_path=temp_persistence_path,
        max_parallel_tasks=4
    )


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    return [
        Task(task_id="task1", name="Task 1", task_type=TaskType.SIMPLE),
        Task(task_id="task2", name="Task 2", task_type=TaskType.SIMPLE),
        Task(task_id="task3", name="Task 3", task_type=TaskType.SIMPLE),
    ]


@pytest.fixture
def simple_workflow(workflow_engine_fsa, sample_tasks):
    """Create simple workflow for testing."""
    dependencies = {
        "task2": ["task1"],
        "task3": ["task2"]
    }

    return workflow_engine_fsa.define_workflow(
        name="Simple Workflow",
        tasks=sample_tasks,
        dependencies=dependencies
    )


# ==================== Test Workflow Definition ====================

def test_define_workflow(workflow_engine_fsa, sample_tasks):
    """Test workflow definition."""
    dependencies = {
        "task2": ["task1"],
        "task3": ["task2"]
    }

    workflow = workflow_engine_fsa.define_workflow(
        name="Test Workflow",
        tasks=sample_tasks,
        dependencies=dependencies
    )

    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.name == "Test Workflow"
    assert len(workflow.tasks) == 3
    assert workflow.start_task == "task1"
    assert "task3" in workflow.end_tasks


def test_workflow_definition_stores_correctly(workflow_engine_fsa, simple_workflow):
    """Test workflow is stored in engine."""
    stored = workflow_engine_fsa.get_workflow(simple_workflow.workflow_id)

    assert stored is not None
    assert stored.workflow_id == simple_workflow.workflow_id


# ==================== Test Workflow Validation ====================

def test_validate_valid_workflow(workflow_engine_fsa, simple_workflow):
    """Test validation of valid workflow."""
    result = workflow_engine_fsa.validate(simple_workflow)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_empty_workflow(workflow_engine_fsa):
    """Test validation fails for empty workflow."""
    workflow = WorkflowDefinition(name="Empty")

    result = workflow_engine_fsa.validate(workflow)

    assert result.valid is False
    assert any("no tasks" in err.lower() for err in result.errors)


def test_validate_workflow_with_missing_dependency(workflow_engine_fsa):
    """Test validation fails for missing dependency."""
    tasks = [Task(task_id="task1", name="Task 1")]
    dependencies = {"task1": ["nonexistent"]}

    workflow = WorkflowDefinition(
        name="Invalid",
        tasks={t.task_id: t for t in tasks},
        dependencies=dependencies
    )

    result = workflow_engine_fsa.validate(workflow)

    assert result.valid is False


def test_validate_workflow_with_cycle(workflow_engine_fsa):
    """Test validation detects circular dependencies."""
    tasks = [
        Task(task_id="task1", name="Task 1"),
        Task(task_id="task2", name="Task 2"),
    ]
    dependencies = {
        "task1": ["task2"],
        "task2": ["task1"]  # Circular dependency
    }

    workflow = WorkflowDefinition(
        name="Circular",
        tasks={t.task_id: t for t in tasks},
        dependencies=dependencies
    )

    result = workflow_engine_fsa.validate(workflow)

    assert result.valid is False
    assert any("circular" in err.lower() for err in result.errors)


# ==================== Test DAG Construction ====================

def test_build_dag(workflow_engine_fsa, sample_tasks):
    """Test DAG construction."""
    tasks_dict = {t.task_id: t for t in sample_tasks}
    dependencies = {"task2": ["task1"], "task3": ["task2"]}

    dag = workflow_engine_fsa.build_dag(tasks_dict, dependencies)

    assert isinstance(dag, DAG)
    assert len(dag.nodes) == 3
    assert "task1" in dag.nodes


def test_dag_cycle_detection(workflow_engine_fsa):
    """Test DAG detects cycles."""
    tasks = {
        "task1": Task(task_id="task1"),
        "task2": Task(task_id="task2"),
    }
    dependencies = {
        "task1": ["task2"],
        "task2": ["task1"]
    }

    dag = workflow_engine_fsa.build_dag(tasks, dependencies)

    assert dag.has_cycle() is True


def test_dag_topological_sort(workflow_engine_fsa, sample_tasks):
    """Test DAG topological sorting."""
    tasks_dict = {t.task_id: t for t in sample_tasks}
    dependencies = {"task2": ["task1"], "task3": ["task2"]}

    dag = workflow_engine_fsa.build_dag(tasks_dict, dependencies)
    sorted_nodes = dag.topological_sort()

    assert sorted_nodes == ["task1", "task2", "task3"]


# ==================== Test Task Execution ====================

def test_execute_task(workflow_engine_fsa):
    """Test individual task execution."""
    context = WorkflowContext(workflow_id="test")

    def handler(ctx):
        ctx.set("output", "success")
        return {"result": "completed"}

    task = Task(task_id="test_task", name="Test", handler=handler)

    result = workflow_engine_fsa.execute_task(task, context)

    assert isinstance(result, TaskResult)
    assert result.success is True
    assert result.output["result"] == "completed"
    assert context.get("output") == "success"


def test_execute_task_without_handler(workflow_engine_fsa):
    """Test task execution without handler (mock execution)."""
    context = WorkflowContext(workflow_id="test")
    task = Task(task_id="test_task", name="Test")

    result = workflow_engine_fsa.execute_task(task, context)

    assert result.success is True
    assert result.output is not None


def test_execute_task_with_exception(workflow_engine_fsa):
    """Test task execution handles exceptions."""
    context = WorkflowContext(workflow_id="test")

    def failing_handler(ctx):
        raise ValueError("Task failed")

    task = Task(task_id="failing_task", name="Failing", handler=failing_handler)

    result = workflow_engine_fsa.execute_task(task, context)

    assert result.success is False
    assert result.error is not None


# ==================== Test Conditional Branching ====================

def test_evaluate_condition_with_predicate(workflow_engine_fsa):
    """Test condition evaluation with predicate function."""
    context = WorkflowContext(workflow_id="test")
    context.set("value", 10)

    condition = Condition(
        predicate=lambda ctx: ctx.get("value") > 5
    )

    result = workflow_engine_fsa.evaluate_condition(condition, context)

    assert result is True


def test_evaluate_condition_with_expression(workflow_engine_fsa):
    """Test condition evaluation with expression."""
    context = WorkflowContext(workflow_id="test")
    context.set("value", 10)

    condition = Condition(
        expression="context.get('value') > 5"
    )

    result = workflow_engine_fsa.evaluate_condition(condition, context)

    assert result is True


def test_branch_workflow(workflow_engine_fsa):
    """Test workflow branching logic."""
    context = WorkflowContext(workflow_id="test")
    context.set("value", 10)

    condition1 = Condition(predicate=lambda ctx: ctx.get("value") > 20)
    condition2 = Condition(predicate=lambda ctx: ctx.get("value") > 5)

    decision_node = DecisionNode(
        conditions=[
            (condition1, "task_high"),
            (condition2, "task_mid")
        ],
        default_task="task_low"
    )

    result = workflow_engine_fsa.branch_workflow(decision_node, context)

    assert isinstance(result, BranchResult)
    assert result.success is True
    assert result.selected_branch == "task_mid"


def test_branch_workflow_default(workflow_engine_fsa):
    """Test workflow branching uses default when no condition matches."""
    context = WorkflowContext(workflow_id="test")
    context.set("value", 1)

    condition = Condition(predicate=lambda ctx: ctx.get("value") > 10)

    decision_node = DecisionNode(
        conditions=[(condition, "task_high")],
        default_task="task_default"
    )

    result = workflow_engine_fsa.branch_workflow(decision_node, context)

    assert result.success is True
    assert result.selected_branch == "task_default"


# ==================== Test Parallel Execution ====================

def test_execute_parallel(workflow_engine_fsa):
    """Test parallel task execution."""
    context = WorkflowContext(workflow_id="test")

    tasks = [
        Task(task_id=f"parallel_task_{i}", name=f"Parallel Task {i}")
        for i in range(3)
    ]

    result = workflow_engine_fsa.execute_parallel(tasks, context)

    assert isinstance(result, ParallelResult)
    assert result.success is True
    assert len(result.task_results) == 3
    assert len(result.failed_tasks) == 0


def test_execute_parallel_with_failures(workflow_engine_fsa):
    """Test parallel execution handles task failures."""
    context = WorkflowContext(workflow_id="test")

    def failing_handler(ctx):
        raise Exception("Failed")

    tasks = [
        Task(task_id="task1", name="Task 1"),
        Task(task_id="task2", name="Task 2", handler=failing_handler),
        Task(task_id="task3", name="Task 3"),
    ]

    result = workflow_engine_fsa.execute_parallel(tasks, context)

    assert result.success is False
    assert len(result.failed_tasks) > 0
    assert "task2" in result.failed_tasks


# ==================== Test Workflow Scheduling ====================

def test_schedule_workflow(workflow_engine_fsa, simple_workflow):
    """Test workflow scheduling."""
    schedule = Schedule(
        cron_expression="0 0 * * *",
        start_time=datetime.utcnow()
    )

    result = workflow_engine_fsa.schedule_workflow(simple_workflow, schedule)

    assert isinstance(result, ScheduleResult)
    assert result.success is True
    assert result.next_run is not None


# ==================== Test State Tracking ====================

def test_track_state(workflow_engine_fsa, simple_workflow):
    """Test workflow state tracking."""
    # Initialize workflow state
    workflow_engine_fsa.workflow_states[simple_workflow.workflow_id] = WorkflowState(
        workflow_id=simple_workflow.workflow_id,
        status=WorkflowStatus.RUNNING
    )

    task = simple_workflow.tasks["task1"]
    entry = workflow_engine_fsa.track_state(
        simple_workflow.workflow_id,
        task,
        TaskStatus.COMPLETED
    )

    assert isinstance(entry, StateEntry)
    assert entry.workflow_id == simple_workflow.workflow_id
    assert entry.task_id == task.task_id


# ==================== Test Error Handling ====================

def test_handle_task_failure_with_retry(workflow_engine_fsa):
    """Test task failure handling with retry."""
    task = Task(task_id="failing_task", max_retries=3, retry_count=0)
    error = Exception("Task failed")
    retry_policy = RetryPolicy(max_retries=3)

    result = workflow_engine_fsa.handle_task_failure(task, error, retry_policy)

    assert isinstance(result, FailureHandlingResult)
    assert result.success is True
    assert result.action_taken == "retry"
    assert task.retry_count == 1


def test_handle_task_failure_max_retries_exceeded(workflow_engine_fsa):
    """Test task failure when max retries exceeded."""
    task = Task(task_id="failing_task", max_retries=3, retry_count=3)
    error = Exception("Task failed")
    retry_policy = RetryPolicy(max_retries=3)

    result = workflow_engine_fsa.handle_task_failure(task, error, retry_policy)

    assert result.success is False
    assert result.action_taken == "fail"


# ==================== Test Compensation ====================

def test_compensate_workflow(workflow_engine_fsa, simple_workflow):
    """Test workflow compensation logic."""
    # Setup workflow state
    state = WorkflowState(
        workflow_id=simple_workflow.workflow_id,
        status=WorkflowStatus.RUNNING,
        completed_tasks=["task1", "task2"]
    )
    workflow_engine_fsa.workflow_states[simple_workflow.workflow_id] = state

    # Register compensation handlers
    compensated_tasks = []

    def compensation_handler(ctx):
        compensated_tasks.append("compensated")

    workflow_engine_fsa.register_compensation_handler("task1", compensation_handler)
    workflow_engine_fsa.register_compensation_handler("task2", compensation_handler)

    # Compensate
    failed_task = simple_workflow.tasks["task3"]
    result = workflow_engine_fsa.compensate_workflow(simple_workflow.workflow_id, failed_task)

    assert isinstance(result, CompensationResult)
    assert result.success is True
    assert len(compensated_tasks) == 2


# ==================== Test Workflow Versioning ====================

def test_version_workflow(workflow_engine_fsa, simple_workflow):
    """Test workflow versioning."""
    changes = [
        Change(change_type="added", affected_element="task4", description="Added new task")
    ]

    entry = workflow_engine_fsa.version_workflow(simple_workflow, "2.0.0", changes)

    assert isinstance(entry, VersionEntry)
    assert entry.version == "2.0.0"
    assert entry.workflow_id == simple_workflow.workflow_id
    assert len(entry.changes) == 1


def test_version_workflow_updates_definition(workflow_engine_fsa, simple_workflow):
    """Test versioning updates workflow definition."""
    workflow_engine_fsa.version_workflow(simple_workflow, "2.0.0", [])

    assert simple_workflow.version == "2.0.0"


# ==================== Test Workflow Analysis ====================

def test_analyze_workflow(workflow_engine_fsa, simple_workflow):
    """Test workflow analysis."""
    analysis = workflow_engine_fsa.analyze_workflow(simple_workflow)

    assert isinstance(analysis, WorkflowAnalysis)
    assert analysis.workflow_id == simple_workflow.workflow_id
    assert analysis.total_tasks == 3
    assert analysis.critical_path_length > 0


def test_analyze_workflow_finds_parallelizable_tasks(workflow_engine_fsa):
    """Test analysis identifies parallelizable tasks."""
    tasks = [
        Task(task_id="task1", name="Task 1"),
        Task(task_id="task2", name="Task 2"),
        Task(task_id="task3", name="Task 3"),
    ]
    dependencies = {
        "task2": ["task1"],
        "task3": ["task1"]  # task2 and task3 can run in parallel
    }

    workflow = workflow_engine_fsa.define_workflow("Parallel", tasks, dependencies)
    analysis = workflow_engine_fsa.analyze_workflow(workflow)

    assert analysis.parallelizable_tasks >= 2


# ==================== Test State Persistence ====================

def test_persist_workflow_state(workflow_engine_fsa, temp_persistence_path):
    """Test workflow state persistence."""
    state = WorkflowState(
        workflow_id="test_workflow",
        status=WorkflowStatus.RUNNING,
        completed_tasks=["task1"],
        context=WorkflowContext(workflow_id="test_workflow", data={"key": "value"})
    )

    result = workflow_engine_fsa.persist_workflow_state("test_workflow", state)

    assert isinstance(result, PersistenceResult)
    assert result.success is True

    # Verify file was created
    files = list(temp_persistence_path.glob("test_workflow_*.json"))
    assert len(files) == 1


def test_persist_workflow_state_creates_valid_json(workflow_engine_fsa, temp_persistence_path):
    """Test persisted state is valid JSON."""
    state = WorkflowState(
        workflow_id="test_workflow",
        status=WorkflowStatus.COMPLETED,
        started_at=datetime.utcnow()
    )

    workflow_engine_fsa.persist_workflow_state("test_workflow", state)

    # Read and parse JSON
    files = list(temp_persistence_path.glob("test_workflow_*.json"))
    with open(files[0], 'r') as f:
        data = json.load(f)

    assert data["workflow_id"] == "test_workflow"
    assert data["status"] == "completed"


# ==================== Test Workflow Resumption ====================

def test_resume_workflow(workflow_engine_fsa, temp_persistence_path):
    """Test workflow resumption from checkpoint."""
    # Create and persist state
    state = WorkflowState(
        workflow_id="resume_test",
        status=WorkflowStatus.PAUSED,
        current_task="task2",
        completed_tasks=["task1"],
        context=WorkflowContext(workflow_id="resume_test", data={"progress": 50})
    )

    workflow_engine_fsa.persist_workflow_state("resume_test", state)

    # Resume workflow
    result = workflow_engine_fsa.resume_workflow("resume_test")

    assert isinstance(result, ResumeResult)
    assert result.success is True
    assert result.resumed_from_task == "task2"

    # Verify state was restored
    restored_state = workflow_engine_fsa.get_workflow_state("resume_test")
    assert restored_state is not None
    assert "task1" in restored_state.completed_tasks


def test_resume_workflow_no_checkpoint(workflow_engine_fsa):
    """Test resumption fails when no checkpoint exists."""
    result = workflow_engine_fsa.resume_workflow("nonexistent")

    assert result.success is False
    assert "no checkpoints" in result.error.lower()


# ==================== Test Workflow Visualization ====================

def test_visualize_workflow_mermaid(workflow_engine_fsa, simple_workflow):
    """Test workflow visualization in Mermaid format."""
    viz = workflow_engine_fsa.visualize_workflow(simple_workflow, format="mermaid")

    assert isinstance(viz, WorkflowVisualization)
    assert viz.format == "mermaid"
    assert "graph TD" in viz.content
    assert "task1" in viz.content


def test_visualize_workflow_dot(workflow_engine_fsa, simple_workflow):
    """Test workflow visualization in DOT format."""
    viz = workflow_engine_fsa.visualize_workflow(simple_workflow, format="dot")

    assert viz.format == "dot"
    assert "digraph workflow" in viz.content
    assert "->" in viz.content


def test_visualize_workflow_json(workflow_engine_fsa, simple_workflow):
    """Test workflow visualization in JSON format."""
    viz = workflow_engine_fsa.visualize_workflow(simple_workflow, format="json")

    assert viz.format == "json"
    data = json.loads(viz.content)
    assert data["workflow_id"] == simple_workflow.workflow_id


# ==================== Test Workflow Metrics ====================

def test_get_workflow_metrics(workflow_engine_fsa):
    """Test workflow metrics collection."""
    workflow_id = "metrics_test"

    # Update metrics
    workflow_engine_fsa.update_metrics(workflow_id, success=True, execution_time=1.5)
    workflow_engine_fsa.update_metrics(workflow_id, success=True, execution_time=2.0)
    workflow_engine_fsa.update_metrics(workflow_id, success=False, execution_time=0.5)

    metrics = workflow_engine_fsa.get_workflow_metrics(workflow_id)

    assert isinstance(metrics, WorkflowMetrics)
    assert metrics.total_executions == 3
    assert metrics.successful_executions == 2
    assert metrics.failed_executions == 1
    assert metrics.avg_execution_time > 0


# ==================== Test Main Workflow Execution ====================

def test_execute_workflow(workflow_engine_fsa, simple_workflow):
    """Test full workflow execution."""
    result = workflow_engine_fsa.execute(simple_workflow)

    assert isinstance(result, WorkflowExecutionResult)
    assert result.success is True
    assert result.status == WorkflowStatus.COMPLETED
    assert result.completed_tasks == 3


def test_execute_workflow_with_handlers(workflow_engine_fsa):
    """Test workflow execution with task handlers."""
    executed_tasks = []

    def make_handler(task_name):
        def handler(ctx):
            executed_tasks.append(task_name)
            return {"executed": task_name}
        return handler

    tasks = [
        Task(task_id="task1", name="Task 1", handler=make_handler("Task 1")),
        Task(task_id="task2", name="Task 2", handler=make_handler("Task 2")),
    ]
    dependencies = {"task2": ["task1"]}

    workflow = workflow_engine_fsa.define_workflow("Handler Test", tasks, dependencies)
    result = workflow_engine_fsa.execute(workflow)

    assert result.success is True
    assert len(executed_tasks) == 2
    assert executed_tasks == ["Task 1", "Task 2"]


def test_execute_workflow_with_failure(workflow_engine_fsa):
    """Test workflow execution handles task failures."""
    def failing_handler(ctx):
        raise Exception("Task failed")

    tasks = [
        Task(task_id="task1", name="Task 1"),
        Task(task_id="task2", name="Task 2", handler=failing_handler, max_retries=0),
        Task(task_id="task3", name="Task 3"),
    ]
    dependencies = {"task2": ["task1"], "task3": ["task2"]}

    workflow = workflow_engine_fsa.define_workflow("Failing", tasks, dependencies)
    result = workflow_engine_fsa.execute(workflow)

    assert result.success is False
    assert result.failed_tasks > 0


# ==================== Test Workflow Context ====================

def test_workflow_context_get_set(workflow_engine_fsa):
    """Test workflow context data operations."""
    context = WorkflowContext(workflow_id="test")

    context.set("key1", "value1")
    context.set("key2", 42)

    assert context.get("key1") == "value1"
    assert context.get("key2") == 42
    assert context.get("nonexistent", "default") == "default"


# ==================== Test Edge Cases ====================

def test_execute_empty_workflow(workflow_engine_fsa):
    """Test execution of workflow with no tasks."""
    workflow = WorkflowDefinition(name="Empty", tasks={}, dependencies={})

    result = workflow_engine_fsa.execute(workflow)

    assert result.success is False


def test_concurrent_workflow_execution(workflow_engine_fsa):
    """Test thread safety with concurrent workflow executions."""
    import threading

    results = []
    lock = threading.Lock()

    def execute_workflow():
        tasks = [Task(task_id=f"task_{threading.get_ident()}", name="Task")]
        workflow = workflow_engine_fsa.define_workflow(
            f"Concurrent_{threading.get_ident()}",
            tasks,
            {}
        )
        result = workflow_engine_fsa.execute(workflow)
        with lock:
            results.append(result)

    # Create multiple threads
    threads = [threading.Thread(target=execute_workflow) for _ in range(5)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify all workflows completed
    assert len(results) == 5


def test_long_running_workflow_with_checkpoints(workflow_engine_fsa, simple_workflow):
    """Test long-running workflow with state checkpointing."""
    # Execute workflow
    result = workflow_engine_fsa.execute(simple_workflow)

    # Verify state was tracked
    state = workflow_engine_fsa.get_workflow_state(simple_workflow.workflow_id)
    assert state is not None
    assert len(state.checkpoints) > 0


def test_complex_multi_branch_workflow(workflow_engine_fsa):
    """Test complex workflow with multiple branching paths."""
    tasks = [
        Task(task_id="start", name="Start"),
        Task(task_id="branch1", name="Branch 1"),
        Task(task_id="branch2", name="Branch 2"),
        Task(task_id="merge", name="Merge"),
    ]

    dependencies = {
        "branch1": ["start"],
        "branch2": ["start"],
        "merge": ["branch1", "branch2"]
    }

    workflow = workflow_engine_fsa.define_workflow("Multi-Branch", tasks, dependencies)
    result = workflow_engine_fsa.execute(workflow)

    assert result.success is True
    assert result.completed_tasks == 4

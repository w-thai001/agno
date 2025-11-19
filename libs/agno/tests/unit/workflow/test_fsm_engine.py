"""
Comprehensive test suite for Workflow Engine FSA.

Tests cover:
- State management and transitions
- Conditional branching
- Parallel execution
- Error handling and retries
- Progress tracking
- Context management
"""

import time
from typing import Any

import pytest

from agno.run.response import RunEvent
from agno.workflow.engine import (
    ExecutionContext,
    State,
    StateStatus,
    StateTransition,
    TransitionCondition,
    WorkflowEngine,
    WorkflowEngineConfig,
)
from agno.workflow.engine.state import StateGraph


# Fixtures


@pytest.fixture
def basic_config():
    """Basic workflow engine configuration."""
    return WorkflowEngineConfig(
        name="test_engine",
        max_parallel_tasks=3,
        default_timeout_seconds=10,
        enable_progress_tracking=True,
    )


@pytest.fixture
def engine(basic_config):
    """Basic workflow engine instance."""
    return WorkflowEngine(name="test_workflow", config=basic_config)


@pytest.fixture
def execution_context():
    """Basic execution context."""
    return ExecutionContext(workflow_id="test-123", variables={"test": True})


# State Management Tests


def test_state_creation():
    """Test creating a state with various configurations."""
    state = State(
        name="test_state",
        description="A test state",
        is_initial=True,
        retry_count=3,
        timeout_seconds=30,
    )

    assert state.name == "test_state"
    assert state.description == "A test state"
    assert state.is_initial is True
    assert state.is_final is False
    assert state.retry_count == 3
    assert state.timeout_seconds == 30
    assert state.status == StateStatus.PENDING


def test_state_name_validation():
    """Test state name validation."""
    # Valid names
    State(name="valid_name")
    State(name="valid-name")
    State(name="ValidName123")

    # Invalid names
    with pytest.raises(ValueError):
        State(name="")

    with pytest.raises(ValueError):
        State(name="invalid name")  # Space not allowed

    with pytest.raises(ValueError):
        State(name="invalid@name")  # Special char not allowed


def test_state_transitions():
    """Test adding and evaluating state transitions."""
    state = State(name="start", is_initial=True)

    # Add simple transition
    transition = state.add_transition("next")
    assert transition.from_state == "start"
    assert transition.to_state == "next"
    assert len(state.transitions) == 1

    # Add conditional transition
    condition = TransitionCondition(
        condition="value > 10", target_state="high", description="Value is high"
    )
    state.add_transition("high", conditions=[condition])
    assert len(state.transitions) == 2


def test_transition_condition_evaluation():
    """Test condition evaluation for transitions."""
    condition = TransitionCondition(condition="x > 5", target_state="next")

    # Should evaluate to True
    assert condition.evaluate({"x": 10}) is True

    # Should evaluate to False
    assert condition.evaluate({"x": 3}) is False

    # Should handle missing variables safely
    assert condition.evaluate({}) is False


def test_complex_condition_evaluation():
    """Test complex condition expressions."""
    # Multiple conditions
    cond1 = TransitionCondition(condition="x > 5 and y < 10", target_state="next")
    assert cond1.evaluate({"x": 7, "y": 8}) is True
    assert cond1.evaluate({"x": 3, "y": 8}) is False

    # String comparison
    cond2 = TransitionCondition(condition="status == 'completed'", target_state="done")
    assert cond2.evaluate({"status": "completed"}) is True
    assert cond2.evaluate({"status": "pending"}) is False

    # In operator
    cond3 = TransitionCondition(condition="'error' in tags", target_state="error")
    assert cond3.evaluate({"tags": ["error", "critical"]}) is True
    assert cond3.evaluate({"tags": ["info"]}) is False


def test_state_reset():
    """Test resetting state execution tracking."""
    state = State(name="test")
    state.status = StateStatus.COMPLETED
    state.result = {"data": "test"}
    state.error = "Some error"
    state.attempt = 3

    state.reset()

    assert state.status == StateStatus.PENDING
    assert state.result is None
    assert state.error is None
    assert state.attempt == 0


# State Graph Tests


def test_state_graph_creation():
    """Test creating and populating a state graph."""
    graph = StateGraph()

    start = State(name="start", is_initial=True)
    process = State(name="process")
    end = State(name="end", is_final=True)

    graph.add_state(start)
    graph.add_state(process)
    graph.add_state(end)

    assert len(graph.states) == 3
    assert graph.initial_state == "start"
    assert "end" in graph.final_states


def test_state_graph_validation():
    """Test state graph validation."""
    graph = StateGraph()

    # Empty graph should fail
    errors = graph.validate_graph()
    assert len(errors) > 0
    assert any("at least one state" in e for e in errors)

    # Add initial state
    start = State(name="start", is_initial=True)
    start.add_transition("end")
    graph.add_state(start)

    # Missing final state
    errors = graph.validate_graph()
    assert any("final state" in e for e in errors)

    # Add final state
    end = State(name="end", is_final=True)
    graph.add_state(end)

    # Should pass validation now
    errors = graph.validate_graph()
    assert len(errors) == 0


def test_state_graph_invalid_transitions():
    """Test validation catches invalid transitions."""
    graph = StateGraph()

    start = State(name="start", is_initial=True)
    start.add_transition("nonexistent")  # Invalid target
    graph.add_state(start)

    errors = graph.validate_graph()
    assert any("unknown state" in e for e in errors)


def test_state_graph_unreachable_states():
    """Test detection of unreachable states."""
    graph = StateGraph()

    start = State(name="start", is_initial=True)
    start.add_transition("end")
    graph.add_state(start)

    end = State(name="end", is_final=True)
    graph.add_state(end)

    # Add isolated state
    isolated = State(name="isolated")
    graph.add_state(isolated)

    errors = graph.validate_graph()
    assert any("unreachable" in e.lower() for e in errors)


def test_get_next_state():
    """Test determining next state based on context."""
    state = State(name="check")

    # Add conditional transitions
    cond_high = TransitionCondition(condition="value > 100", target_state="high")
    cond_med = TransitionCondition(
        condition="value > 50 and value <= 100", target_state="medium"
    )

    state.add_transition("high", conditions=[cond_high])
    state.add_transition("medium", conditions=[cond_med])
    state.add_transition("low")  # Default transition

    # Test different contexts
    assert state.get_next_state({"value": 150}) == "high"
    assert state.get_next_state({"value": 75}) == "medium"
    assert state.get_next_state({"value": 25}) == "low"


# Execution Context Tests


def test_execution_context_variables():
    """Test execution context variable management."""
    ctx = ExecutionContext(workflow_id="test-123")

    # Set and get variables
    ctx.set("key1", "value1")
    ctx.set("key2", 42)

    assert ctx.get("key1") == "value1"
    assert ctx.get("key2") == 42
    assert ctx.get("missing", "default") == "default"

    # Check existence
    assert ctx.has("key1") is True
    assert ctx.has("missing") is False

    # Update multiple
    ctx.update({"key3": True, "key4": [1, 2, 3]})
    assert ctx.get("key3") is True
    assert ctx.get("key4") == [1, 2, 3]

    # Delete
    ctx.delete("key1")
    assert ctx.has("key1") is False


def test_execution_context_state_tracking():
    """Test tracking state executions."""
    ctx = ExecutionContext(workflow_id="test-123")

    # Start first state
    exec1 = ctx.start_state_execution("state1", attempt=1)
    assert exec1.state_name == "state1"
    assert exec1.status == StateStatus.RUNNING
    assert ctx.current_state == "state1"

    time.sleep(0.01)  # Small delay for duration
    ctx.complete_state_execution(result={"success": True})

    # Check completion
    last_exec = ctx.get_last_execution("state1")
    assert last_exec is not None
    assert last_exec.status == StateStatus.COMPLETED
    assert last_exec.result == {"success": True}
    assert last_exec.duration_ms is not None
    assert last_exec.duration_ms > 0


def test_execution_context_path_tracking():
    """Test execution path tracking."""
    ctx = ExecutionContext(workflow_id="test-123")

    # Execute several states
    ctx.start_state_execution("start")
    ctx.complete_state_execution()

    ctx.start_state_execution("process")
    ctx.complete_state_execution()

    ctx.start_state_execution("end")
    ctx.complete_state_execution()

    # Check path
    path = ctx.get_execution_path()
    assert path == ["start", "process", "end"]

    # Check visited
    assert ctx.has_visited_state("process") is True
    assert ctx.has_visited_state("unknown") is False


def test_execution_context_statistics():
    """Test execution statistics calculation."""
    ctx = ExecutionContext(workflow_id="test-123")

    # Execute state multiple times
    for i in range(3):
        ctx.start_state_execution("retry_state", attempt=i + 1)
        time.sleep(0.01)
        if i < 2:
            ctx.complete_state_execution(error="Failed")
        else:
            ctx.complete_state_execution(result="Success")

    stats = ctx.get_state_statistics()
    assert "retry_state" in stats
    assert stats["retry_state"]["total_executions"] == 3
    assert stats["retry_state"]["successful"] == 1
    assert stats["retry_state"]["failed"] == 2
    assert stats["retry_state"]["avg_duration_ms"] > 0


# Workflow Engine Tests


def test_workflow_engine_creation(basic_config):
    """Test creating a workflow engine."""
    engine = WorkflowEngine(name="test", config=basic_config)

    assert engine.name == "test"
    assert engine.config.name == "test_engine"
    assert len(engine.state_graph.states) == 0


def test_add_state_to_engine(engine):
    """Test adding states to workflow engine."""

    def handler(ctx):
        return "result"

    state = State(name="test_state", is_initial=True)
    added_state = engine.add_state(state, handler=handler)

    assert added_state.name == "test_state"
    assert engine.state_graph.get_state("test_state") is not None
    assert "test_state" in engine.state_handlers


def test_simple_workflow_execution(engine):
    """Test executing a simple linear workflow."""

    results = []

    def start_handler(ctx):
        results.append("start")
        ctx.set("step", 1)

    def process_handler(ctx):
        results.append("process")
        ctx.set("step", 2)

    def end_handler(ctx):
        results.append("end")

    # Define states
    start = State(name="start", is_initial=True)
    process = State(name="process")
    end = State(name="end", is_final=True)

    # Define transitions
    start.add_transition("process")
    process.add_transition("end")

    # Add to engine
    engine.add_state(start, handler=start_handler)
    engine.add_state(process, handler=process_handler)
    engine.add_state(end, handler=end_handler)

    # Execute
    responses = list(engine.run())

    # Check execution
    assert results == ["start", "process", "end"]

    # Check events
    events = [r.event for r in responses]
    assert RunEvent.run_started.value in events
    assert RunEvent.run_completed.value in events

    # Check final result
    final_response = responses[-1]
    assert final_response.event == RunEvent.run_completed.value
    assert final_response.content["status"] == "completed"


def test_conditional_branching(engine):
    """Test workflow with conditional branching."""

    execution_path = []

    def check_handler(ctx):
        execution_path.append("check")
        value = ctx.get("value")
        ctx.set("checked", True)

    def high_handler(ctx):
        execution_path.append("high")

    def low_handler(ctx):
        execution_path.append("low")

    def end_handler(ctx):
        execution_path.append("end")

    # Define states
    check = State(name="check", is_initial=True)
    high = State(name="high")
    low = State(name="low")
    end = State(name="end", is_final=True)

    # Conditional transitions
    high_cond = TransitionCondition(condition="value > 50", target_state="high")
    check.add_transition("high", conditions=[high_cond])
    check.add_transition("low")  # Default

    high.add_transition("end")
    low.add_transition("end")

    # Add to engine
    engine.add_state(check, handler=check_handler)
    engine.add_state(high, handler=high_handler)
    engine.add_state(low, handler=low_handler)
    engine.add_state(end, handler=end_handler)

    # Execute with high value
    execution_path.clear()
    list(engine.run(value=75))
    assert execution_path == ["check", "high", "end"]

    # Reset and execute with low value
    engine.reset()
    execution_path.clear()
    list(engine.run(value=25))
    assert execution_path == ["check", "low", "end"]


def test_state_retry_on_failure(engine):
    """Test state retry mechanism on failure."""

    attempt_count = []

    def failing_handler(ctx):
        attempt_count.append(len(attempt_count) + 1)
        if len(attempt_count) < 3:
            raise ValueError(f"Attempt {len(attempt_count)} failed")
        return "success"

    # State with 2 retries (total 3 attempts)
    start = State(name="start", is_initial=True, retry_count=2)
    end = State(name="end", is_final=True)

    start.add_transition("end")

    engine.add_state(start, handler=failing_handler)
    engine.add_state(end)

    # Execute
    responses = list(engine.run())

    # Should succeed on 3rd attempt
    assert len(attempt_count) == 3
    assert any(
        r.content.get("status") == "completed"
        for r in responses
        if isinstance(r.content, dict)
    )


def test_state_failure_after_retries(engine):
    """Test workflow failure after exhausting retries."""

    def always_fail_handler(ctx):
        raise ValueError("Persistent failure")

    start = State(name="start", is_initial=True, retry_count=1)
    end = State(name="end", is_final=True)

    start.add_transition("end")

    engine.add_state(start, handler=always_fail_handler)
    engine.add_state(end)

    # Execute - should fail
    responses = list(engine.run())

    # Check for error event
    events = [r.event for r in responses]
    assert RunEvent.run_error.value in events


def test_state_callbacks(engine):
    """Test on_enter and on_exit callbacks."""

    callback_log = []

    def on_enter(ctx):
        callback_log.append("enter")

    def handler(ctx):
        callback_log.append("execute")

    def on_exit(ctx):
        callback_log.append("exit")

    start = State(name="start", is_initial=True)
    end = State(name="end", is_final=True)

    start.add_transition("end")

    engine.add_state(start, handler=handler, on_enter=on_enter, on_exit=on_exit)
    engine.add_state(end)

    list(engine.run())

    assert callback_log == ["enter", "execute", "exit"]


def test_workflow_validation(engine):
    """Test workflow validation."""

    # No states - should fail
    errors = engine.validate()
    assert len(errors) > 0

    # Add initial but no final - should fail
    start = State(name="start", is_initial=True)
    engine.add_state(start)
    errors = engine.validate()
    assert any("final state" in e for e in errors)

    # Add final state - should pass
    end = State(name="end", is_final=True)
    start.add_transition("end")
    engine.add_state(end)
    errors = engine.validate()
    assert len(errors) == 0


def test_parallel_execution(engine):
    """Test parallel task execution."""

    results = []

    def task1(ctx):
        time.sleep(0.01)
        results.append(1)
        return "task1_result"

    def task2(ctx):
        time.sleep(0.01)
        results.append(2)
        return "task2_result"

    def task3(ctx):
        time.sleep(0.01)
        results.append(3)
        return "task3_result"

    ctx = ExecutionContext(workflow_id="test")

    # Execute in parallel
    task_results = engine.execute_parallel([task1, task2, task3], ctx)

    # All tasks should complete
    assert len(task_results) == 3
    assert "task1_result" in task_results
    assert "task2_result" in task_results
    assert "task3_result" in task_results


def test_progress_tracking(engine):
    """Test progress event emission."""

    def handler(ctx):
        pass

    start = State(name="start", is_initial=True)
    process = State(name="process")
    end = State(name="end", is_final=True)

    start.add_transition("process")
    process.add_transition("end")

    engine.add_state(start, handler=handler)
    engine.add_state(process, handler=handler)
    engine.add_state(end)

    # Execute with progress tracking enabled
    responses = list(engine.run())

    # Check for progress events
    progress_events = [
        r
        for r in responses
        if isinstance(r.content, dict)
        and r.content.get("status") in ["state_started", "state_completed", "transition"]
    ]

    assert len(progress_events) > 0


def test_context_to_dict():
    """Test context serialization for condition evaluation."""
    ctx = ExecutionContext(workflow_id="test")
    ctx.set("var1", "value1")
    ctx.set("var2", 42)

    ctx_dict = ctx.to_dict()

    assert ctx_dict["var1"] == "value1"
    assert ctx_dict["var2"] == 42
    assert "_context" in ctx_dict
    assert ctx_dict["_context"]["workflow_id"] == "test"


def test_workflow_with_input_parameters(engine):
    """Test passing input parameters to workflow."""

    captured_params = {}

    def handler(ctx):
        captured_params["name"] = ctx.get("name")
        captured_params["age"] = ctx.get("age")

    start = State(name="start", is_initial=True, is_final=True)
    engine.add_state(start, handler=handler)

    # Execute with parameters
    list(engine.run(name="Alice", age=30))

    assert captured_params["name"] == "Alice"
    assert captured_params["age"] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

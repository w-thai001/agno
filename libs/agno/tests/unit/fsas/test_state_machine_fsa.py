"""
Comprehensive tests for State Machine FSA implementation.

Tests cover:
- Basic state machine creation and execution
- State definition with entry/exit actions
- Transition definition with guards
- Event handling and state changes
- Guard condition evaluation
- Action execution with context
- Transition history tracking
- State consistency validation
- State persistence and recovery
- Workflow orchestration
- Transition pattern analysis
- Edge cases and error handling
- Complex multi-state workflows
"""

from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import pytest

from agno.fsas.state_machine_fsa import (
    StateMachineFSA,
    State,
    Event,
    Transition,
    Context,
    StateMachineConfig,
    WorkflowDefinition,
    TransitionStatus,
    PersistenceFormat,
)


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================


@pytest.fixture
def temp_persistence_path():
    """Create a temporary directory for persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def simple_state_machine():
    """Create a simple state machine for testing."""
    fsm = StateMachineFSA(name="TestMachine")

    # Define states
    idle = fsm.define_state("idle", is_initial=True)
    running = fsm.define_state("running")
    stopped = fsm.define_state("stopped", is_final=True)

    # Define events
    start_event = Event(name="start")
    stop_event = Event(name="stop")

    # Define transitions
    fsm.define_transition(idle, running, start_event)
    fsm.define_transition(running, stopped, stop_event)

    fsm.current_state = idle
    return fsm


@pytest.fixture
def action_tracking_machine():
    """Create a state machine that tracks action executions."""
    fsm = StateMachineFSA(name="ActionTracking")

    actions_executed = []

    def entry_action(ctx: Context):
        actions_executed.append(f"entry_{ctx.get('target_state', 'unknown')}")
        return "entered"

    def exit_action(ctx: Context):
        actions_executed.append(f"exit_{ctx.get('current_state', 'unknown')}")
        return "exited"

    def transition_action(ctx: Context):
        actions_executed.append("transition")
        return "transitioned"

    # Store reference for verification
    fsm.context.set("actions_executed", actions_executed)

    # Define states with entry/exit actions
    state_a = fsm.define_state("A", entry_action=entry_action, exit_action=exit_action, is_initial=True)
    state_b = fsm.define_state("B", entry_action=entry_action, exit_action=exit_action)

    # Define transition with action
    event = Event(name="go")
    fsm.define_transition(state_a, state_b, event, action=transition_action)

    fsm.current_state = state_a
    return fsm


# ============================================================================
# Test Cases
# ============================================================================


def test_basic_state_machine_creation_and_execution(simple_state_machine):
    """Test basic state machine creation and event execution."""
    fsm = simple_state_machine

    # Verify initial state
    assert fsm.current_state.name == "idle"
    assert fsm.current_state.is_initial is True

    # Create events
    events = [Event(name="start"), Event(name="stop")]

    # Execute state machine
    result = fsm.execute(fsm.current_state, events)

    # Verify execution
    assert result.success is True
    assert result.events_processed == 2
    assert result.final_state.name == "stopped"
    assert len(result.history) == 2
    assert len(result.errors) == 0


def test_state_definition_with_entry_exit_actions(action_tracking_machine):
    """Test state definition with entry and exit actions."""
    fsm = action_tracking_machine
    actions_executed = fsm.context.get("actions_executed")

    # Clear any initial actions
    actions_executed.clear()

    # Set context for tracking
    fsm.context.set("current_state", "A")
    fsm.context.set("target_state", "B")

    # Trigger transition
    event = Event(name="go")
    result = fsm.handle_event(fsm.current_state, event)

    # Verify transition succeeded
    assert result.status == TransitionStatus.SUCCESS
    assert result.from_state.name == "A"
    assert result.to_state.name == "B"

    # Verify actions were executed in correct order
    assert len(actions_executed) == 3
    assert actions_executed[0] == "exit_A"  # Exit old state
    assert actions_executed[1] == "transition"  # Transition action
    assert actions_executed[2] == "entry_B"  # Enter new state


def test_transition_definition_with_guards():
    """Test transition definition with guard conditions."""
    fsm = StateMachineFSA(name="GuardTest")

    # Define guard that checks context value
    def require_permission(ctx: Context) -> bool:
        return ctx.get("has_permission", False)

    # Define states
    locked = fsm.define_state("locked", is_initial=True)
    unlocked = fsm.define_state("unlocked")

    # Define transition with guard
    unlock_event = Event(name="unlock")
    fsm.define_transition(locked, unlocked, unlock_event, guard=require_permission)

    fsm.current_state = locked

    # Test transition without permission
    fsm.context.set("has_permission", False)
    result = fsm.handle_event(locked, unlock_event)
    assert result.status == TransitionStatus.BLOCKED
    assert result.guard_passed is False
    assert fsm.current_state.name == "locked"

    # Test transition with permission
    fsm.context.set("has_permission", True)
    result = fsm.handle_event(locked, unlock_event)
    assert result.status == TransitionStatus.SUCCESS
    assert result.guard_passed is True
    assert fsm.current_state.name == "unlocked"


def test_event_handling_and_state_changes(simple_state_machine):
    """Test event handling and state transitions."""
    fsm = simple_state_machine

    # Initial state
    assert fsm.current_state.name == "idle"

    # Handle start event
    start_event = Event(name="start")
    result = fsm.handle_event(fsm.current_state, start_event)

    assert result.status == TransitionStatus.SUCCESS
    assert fsm.current_state.name == "running"

    # Handle stop event
    stop_event = Event(name="stop")
    result = fsm.handle_event(fsm.current_state, stop_event)

    assert result.status == TransitionStatus.SUCCESS
    assert fsm.current_state.name == "stopped"
    assert fsm.current_state.is_final is True


def test_guard_condition_evaluation():
    """Test guard condition evaluation with various conditions."""
    fsm = StateMachineFSA(name="GuardEval")

    # Define multiple guards
    def always_true(ctx: Context) -> bool:
        return True

    def always_false(ctx: Context) -> bool:
        return False

    def check_counter(ctx: Context) -> bool:
        return ctx.get("counter", 0) > 5

    # Define states
    start = fsm.define_state("start", is_initial=True)
    always_ok = fsm.define_state("always_ok")
    never_ok = fsm.define_state("never_ok")
    conditional = fsm.define_state("conditional")

    # Define transitions with different guards
    event = Event(name="test")
    fsm.define_transition(start, always_ok, event, guard=always_true, priority=3)
    fsm.define_transition(start, never_ok, event, guard=always_false, priority=2)
    fsm.define_transition(start, conditional, event, guard=check_counter, priority=1)

    fsm.current_state = start

    # Test with counter < 5 (should go to always_ok due to priority)
    fsm.context.set("counter", 3)
    result = fsm.handle_event(start, event)
    assert result.to_state.name == "always_ok"
    assert result.guard_passed is True


def test_action_execution_with_context():
    """Test action execution with context passing and modification."""
    fsm = StateMachineFSA(name="ContextTest")

    # Define action that modifies context
    def increment_counter(ctx: Context):
        current = ctx.get("counter", 0)
        ctx.set("counter", current + 1)
        return current + 1

    def double_value(ctx: Context):
        counter = ctx.get("counter", 0)
        ctx.set("counter", counter * 2)
        return counter * 2

    # Define states and transitions
    s1 = fsm.define_state("s1", is_initial=True)
    s2 = fsm.define_state("s2")
    s3 = fsm.define_state("s3")

    e1 = Event(name="increment")
    e2 = Event(name="double")

    fsm.define_transition(s1, s2, e1, action=increment_counter)
    fsm.define_transition(s2, s3, e2, action=double_value)

    fsm.current_state = s1
    fsm.context.set("counter", 5)

    # Execute transitions
    result1 = fsm.handle_event(s1, e1)
    assert result1.action_result.success is True
    assert result1.action_result.result == 6
    assert fsm.context.get("counter") == 6

    result2 = fsm.handle_event(s2, e2)
    assert result2.action_result.success is True
    assert result2.action_result.result == 12
    assert fsm.context.get("counter") == 12


def test_transition_history_tracking(simple_state_machine):
    """Test transition history tracking and audit trail."""
    fsm = simple_state_machine

    # Execute multiple transitions
    events = [
        Event(name="start", payload={"reason": "user_request"}),
        Event(name="stop", payload={"reason": "completed"}),
    ]

    fsm.execute(fsm.current_state, events)

    # Verify history
    assert len(fsm.history) == 2

    # Check first transition
    assert fsm.history[0].from_state == "idle"
    assert fsm.history[0].to_state == "running"
    assert fsm.history[0].event == "start"
    assert fsm.history[0].success is True

    # Check second transition
    assert fsm.history[1].from_state == "running"
    assert fsm.history[1].to_state == "stopped"
    assert fsm.history[1].event == "stop"
    assert fsm.history[1].success is True

    # Verify timestamps are ordered
    assert fsm.history[0].timestamp <= fsm.history[1].timestamp


def test_state_consistency_validation():
    """Test state consistency validation."""
    fsm = StateMachineFSA(name="ConsistencyTest")

    # Define state with required context
    state = fsm.define_state(
        "validated_state",
        metadata={
            "required_context": ["user_id", "session_token"]
        }
    )

    # Test with missing required context
    ctx = Context()
    ctx.set("user_id", "12345")  # Missing session_token

    report = fsm.validate_state_consistency(state, ctx)
    assert report.is_consistent is False
    assert len(report.errors) == 1
    assert "session_token" in report.errors[0]

    # Test with all required context
    ctx.set("session_token", "abc123")
    report = fsm.validate_state_consistency(state, ctx)
    assert report.is_consistent is True
    assert len(report.errors) == 0


def test_state_persistence_and_recovery(temp_persistence_path):
    """Test state persistence and recovery."""
    fsm = StateMachineFSA(name="PersistenceTest", persistence_path=temp_persistence_path)

    # Create state and context
    state = fsm.define_state("test_state")
    fsm.current_state = state
    fsm.context.set("important_data", "must_preserve")
    fsm.context.set("counter", 42)

    # Add some history
    event = Event(name="test_event")
    fsm.track_transition(state, state, event, datetime.now())

    # Persist state
    result = fsm.persist_state(state, fsm.context, format=PersistenceFormat.JSON)
    assert result.success is True
    assert result.persistence_id is not None

    # Create new FSM and restore state
    fsm2 = StateMachineFSA(name="PersistenceTest", persistence_path=temp_persistence_path)
    restore_result = fsm2.restore_state(result.persistence_id)

    assert restore_result.success is True
    assert restore_result.state.name == "test_state"
    assert restore_result.context.get("important_data") == "must_preserve"
    assert restore_result.context.get("counter") == 42
    assert len(fsm2.history) == 1


def test_workflow_orchestration():
    """Test workflow orchestration for multi-step processes."""
    fsm = StateMachineFSA(name="WorkflowTest")

    # Define states for a document approval workflow
    draft = fsm.define_state("draft", is_initial=True)
    review = fsm.define_state("review")
    approved = fsm.define_state("approved")
    published = fsm.define_state("published", is_final=True)

    # Define events
    submit = Event(name="submit")
    approve = Event(name="approve")
    publish = Event(name="publish")

    # Define transitions
    fsm.define_transition(draft, review, submit)
    fsm.define_transition(review, approved, approve)
    fsm.define_transition(approved, published, publish)

    # Create workflow definition
    workflow = WorkflowDefinition(
        name="DocumentApproval",
        steps=[submit, approve, publish],
        initial_state=draft,
        expected_final_state=published,
        timeout=60.0
    )

    # Execute workflow
    result = fsm.orchestrate_workflow(workflow)

    assert result.success is True
    assert result.steps_completed == 3
    assert result.final_state.name == "published"
    assert len(result.transition_history) == 3
    assert len(result.errors) == 0


def test_transition_pattern_analysis():
    """Test transition pattern analysis."""
    fsm = StateMachineFSA(name="AnalysisTest")

    # Create some history
    s1 = State(name="state1")
    s2 = State(name="state2")
    s3 = State(name="state3")

    base_time = datetime.now()

    history = [
        fsm.track_transition(s1, s2, Event(name="e1"), base_time, success=True),
        fsm.track_transition(s2, s3, Event(name="e2"), base_time + timedelta(seconds=1), success=True),
        fsm.track_transition(s3, s1, Event(name="e3"), base_time + timedelta(seconds=2), success=True),
        fsm.track_transition(s1, s2, Event(name="e1"), base_time + timedelta(seconds=3), success=True),
        fsm.track_transition(s2, s2, Event(name="loop"), base_time + timedelta(seconds=4), success=True),
        fsm.track_transition(s2, s2, Event(name="loop"), base_time + timedelta(seconds=5), success=True),
        fsm.track_transition(s2, s3, Event(name="e2"), base_time + timedelta(seconds=6), success=False),
    ]

    # Analyze transitions
    analysis = fsm.analyze_transitions(history)

    assert analysis.total_transitions == 7
    assert analysis.successful_transitions == 6
    assert analysis.failed_transitions == 1
    assert "state1" in analysis.state_frequencies
    assert "state2" in analysis.state_frequencies
    assert "e1" in analysis.event_frequencies
    assert analysis.event_frequencies["e1"] == 2
    assert len(analysis.common_paths) > 0
    assert any("loop" in anomaly.lower() for anomaly in analysis.anomalies)


def test_edge_case_invalid_states():
    """Test edge cases with invalid states and transitions."""
    fsm = StateMachineFSA(name="EdgeCaseTest")

    # Define valid states
    state_a = fsm.define_state("A", is_initial=True)
    state_b = fsm.define_state("B")

    # Define event
    event = Event(name="go")

    # Define transition
    fsm.define_transition(state_a, state_b, event)

    fsm.current_state = state_a

    # Try invalid event
    invalid_event = Event(name="invalid")
    result = fsm.handle_event(state_a, invalid_event)

    assert result.status == TransitionStatus.BLOCKED
    assert fsm.current_state.name == "A"  # Should remain in same state
    assert result.error is not None


def test_circular_transitions():
    """Test handling of circular transitions."""
    fsm = StateMachineFSA(name="CircularTest")

    # Create circular state graph
    s1 = fsm.define_state("s1", is_initial=True)
    s2 = fsm.define_state("s2")
    s3 = fsm.define_state("s3")

    e_next = Event(name="next")

    # Create cycle: s1 -> s2 -> s3 -> s1
    fsm.define_transition(s1, s2, e_next)
    fsm.define_transition(s2, s3, e_next)
    fsm.define_transition(s3, s1, e_next)

    fsm.current_state = s1

    # Execute multiple cycles
    events = [Event(name="next") for _ in range(6)]  # 2 complete cycles
    result = fsm.execute(s1, events)

    assert result.success is True
    assert result.events_processed == 6
    assert result.final_state.name == "s1"  # Should be back at start
    assert len(result.history) == 6


def test_error_handling_scenarios():
    """Test comprehensive error handling."""
    fsm = StateMachineFSA(name="ErrorTest")

    # Define action that raises exception
    def failing_action(ctx: Context):
        raise ValueError("Intentional failure")

    # Define states
    start = fsm.define_state("start", is_initial=True)
    end = fsm.define_state("end")

    # Define transition with failing action
    event = Event(name="fail")
    fsm.define_transition(start, end, event, action=failing_action)

    fsm.current_state = start

    # Handle event that will fail
    result = fsm.handle_event(start, event)

    assert result.status == TransitionStatus.FAILED
    assert result.action_result is not None
    assert result.action_result.success is False
    assert "Intentional failure" in result.action_result.error
    assert fsm.current_state.name == "start"  # Should remain in original state


def test_complex_multi_state_workflow():
    """Test complex multi-state workflow with guards and actions."""
    fsm = StateMachineFSA(name="ComplexWorkflow")

    # Track workflow progress
    workflow_data = {"step": 0, "validated": False, "processed": False}
    fsm.context.set("workflow_data", workflow_data)

    # Define guards
    def is_validated(ctx: Context) -> bool:
        return ctx.get("workflow_data", {}).get("validated", False)

    def is_processed(ctx: Context) -> bool:
        return ctx.get("workflow_data", {}).get("processed", False)

    # Define actions
    def validate(ctx: Context):
        data = ctx.get("workflow_data", {})
        data["validated"] = True
        data["step"] = 1
        return "validated"

    def process(ctx: Context):
        data = ctx.get("workflow_data", {})
        data["processed"] = True
        data["step"] = 2
        return "processed"

    # Define states
    init = fsm.define_state("init", is_initial=True)
    validating = fsm.define_state("validating")
    processing = fsm.define_state("processing")
    completed = fsm.define_state("completed", is_final=True)

    # Define events
    e_validate = Event(name="validate")
    e_process = Event(name="process")
    e_complete = Event(name="complete")

    # Define transitions with guards and actions
    fsm.define_transition(init, validating, e_validate, action=validate)
    fsm.define_transition(validating, processing, e_process, guard=is_validated, action=process)
    fsm.define_transition(processing, completed, e_complete, guard=is_processed)

    # Execute workflow
    events = [e_validate, e_process, e_complete]
    result = fsm.execute(init, events)

    assert result.success is True
    assert result.final_state.name == "completed"
    assert fsm.context.get("workflow_data")["validated"] is True
    assert fsm.context.get("workflow_data")["processed"] is True
    assert fsm.context.get("workflow_data")["step"] == 2


def test_state_machine_validation():
    """Test state machine configuration validation."""
    # Create invalid configuration (no initial state)
    config = StateMachineConfig(
        name="InvalidConfig",
        states=[
            State(name="s1"),
            State(name="s2"),
            State(name="unreachable"),
        ],
        transitions=[
            Transition(
                from_state=State(name="s1"),
                to_state=State(name="s2"),
                event=Event(name="go")
            )
        ]
    )

    fsm = StateMachineFSA(name="ValidationTest")
    result = fsm.validate(config)

    assert result.is_valid is False
    assert len(result.errors) > 0
    assert any("initial state" in error.lower() for error in result.errors)

    # Create valid configuration
    valid_config = StateMachineConfig(
        name="ValidConfig",
        states=[
            State(name="start", is_initial=True),
            State(name="end", is_final=True),
        ],
        transitions=[
            Transition(
                from_state=State(name="start"),
                to_state=State(name="end"),
                event=Event(name="finish")
            )
        ],
        initial_state=State(name="start", is_initial=True)
    )

    result = fsm.validate(valid_config)
    assert result.is_valid is True
    assert len(result.errors) == 0

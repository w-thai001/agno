"""
Unit tests for base FSA framework.
"""

import pytest
from typing import Iterator

from agno.fsa.base import (
    FSA,
    State,
    StateContext,
    StateStatus,
    Transition,
)
from agno.run.response import RunResponse, RunEvent


class TestStateContext:
    """Tests for StateContext class"""

    def test_initialization(self):
        """Test StateContext initialization"""
        context = StateContext()

        assert context.data == {}
        assert context.metadata == {}
        assert context.error is None
        assert context.retry_count == 0
        assert context.state_history == []

    def test_set_and_get(self):
        """Test setting and getting values"""
        context = StateContext()

        context.set("key1", "value1")
        assert context.get("key1") == "value1"
        assert context.get("nonexistent") is None
        assert context.get("nonexistent", "default") == "default"

    def test_update(self):
        """Test updating multiple values"""
        context = StateContext()

        context.update(key1="value1", key2="value2")
        assert context.get("key1") == "value1"
        assert context.get("key2") == "value2"

    def test_error_handling(self):
        """Test error state management"""
        context = StateContext()

        error = ValueError("Test error")
        context.set_error(error)
        assert context.error == error

        context.clear_error()
        assert context.error is None

    def test_retry_count(self):
        """Test retry counter management"""
        context = StateContext()

        assert context.retry_count == 0

        count = context.increment_retry()
        assert count == 1
        assert context.retry_count == 1

        context.increment_retry()
        assert context.retry_count == 2

        context.reset_retry()
        assert context.retry_count == 0

    def test_state_history(self):
        """Test state history tracking"""
        context = StateContext()

        context.add_to_history("STATE_A")
        context.add_to_history("STATE_B")
        context.add_to_history("STATE_C")

        assert context.state_history == ["STATE_A", "STATE_B", "STATE_C"]


class TestState:
    """Tests for State class"""

    def test_state_initialization(self):
        """Test State initialization"""
        state = State(name="TEST_STATE")

        assert state.name == "TEST_STATE"
        assert state.agent is None
        assert state.on_enter is None
        assert state.on_exit is None
        assert state.execute_func is None
        assert state.is_terminal is False
        assert state.max_retries == 3
        assert state.status == StateStatus.PENDING

    def test_state_enter_exit(self):
        """Test state entry and exit callbacks"""
        entered = []
        exited = []

        def on_enter_callback(ctx: StateContext):
            entered.append(ctx.get("test_value"))

        def on_exit_callback(ctx: StateContext):
            exited.append(ctx.get("test_value"))

        state = State(
            name="TEST_STATE",
            on_enter=on_enter_callback,
            on_exit=on_exit_callback,
        )

        context = StateContext()
        context.set("test_value", "test")

        state.enter(context)
        assert entered == ["test"]
        assert state.status == StateStatus.IN_PROGRESS
        assert context.state_history == ["TEST_STATE"]

        state.exit(context)
        assert exited == ["test"]

    def test_state_execute_with_func(self):
        """Test state execution with custom function"""
        def execute_func(ctx: StateContext) -> StateContext:
            ctx.set("executed", True)
            return ctx

        state = State(
            name="TEST_STATE",
            execute_func=execute_func,
        )

        context = StateContext()
        responses = list(state.execute(context))

        assert len(responses) > 0
        assert context.get("executed") is True
        assert state.status == StateStatus.COMPLETED

    def test_state_execute_error(self):
        """Test state execution with error"""
        def execute_func(ctx: StateContext) -> StateContext:
            raise ValueError("Test error")

        state = State(
            name="TEST_STATE",
            execute_func=execute_func,
        )

        context = StateContext()

        with pytest.raises(ValueError):
            list(state.execute(context))

        assert context.error is not None
        assert state.status == StateStatus.FAILED


class TestTransition:
    """Tests for Transition class"""

    def test_transition_initialization(self):
        """Test Transition initialization"""
        transition = Transition(
            from_state="A",
            to_state="B",
            condition=lambda ctx: True,
        )

        assert transition.from_state == "A"
        assert transition.to_state == "B"
        assert transition.priority == 0

    def test_should_transition_true(self):
        """Test transition condition evaluation (True)"""
        transition = Transition(
            from_state="A",
            to_state="B",
            condition=lambda ctx: ctx.get("ready") is True,
        )

        context = StateContext()
        context.set("ready", True)

        assert transition.should_transition(context) is True

    def test_should_transition_false(self):
        """Test transition condition evaluation (False)"""
        transition = Transition(
            from_state="A",
            to_state="B",
            condition=lambda ctx: ctx.get("ready") is True,
        )

        context = StateContext()
        context.set("ready", False)

        assert transition.should_transition(context) is False

    def test_should_transition_error(self):
        """Test transition condition with error"""
        def bad_condition(ctx: StateContext) -> bool:
            raise ValueError("Condition error")

        transition = Transition(
            from_state="A",
            to_state="B",
            condition=bad_condition,
        )

        context = StateContext()

        # Should return False on error
        assert transition.should_transition(context) is False


class TestFSA:
    """Tests for FSA class"""

    def test_fsa_initialization(self):
        """Test FSA initialization"""
        fsa = FSA(name="test_fsa", initial_state="START")

        assert fsa.name == "test_fsa"
        assert fsa.initial_state == "START"
        assert fsa.current_state is None
        assert fsa.states == {}
        assert fsa.transitions == []
        assert fsa.max_iterations == 100

    def test_add_state(self):
        """Test adding states to FSA"""
        fsa = FSA(name="test_fsa", initial_state="START")

        state1 = State(name="START")
        state2 = State(name="END", is_terminal=True)

        fsa.add_state(state1)
        fsa.add_state(state2)

        assert "START" in fsa.states
        assert "END" in fsa.states
        assert fsa.states["START"] == state1
        assert fsa.states["END"] == state2

    def test_add_transition(self):
        """Test adding transitions to FSA"""
        fsa = FSA(name="test_fsa", initial_state="START")

        fsa.add_state(State(name="START"))
        fsa.add_state(State(name="END"))

        transition = Transition(
            from_state="START",
            to_state="END",
            condition=lambda ctx: True,
        )

        fsa.add_transition(transition)

        assert len(fsa.transitions) == 1
        assert fsa.transitions[0] == transition

    def test_add_transition_invalid_state(self):
        """Test adding transition with invalid states"""
        fsa = FSA(name="test_fsa", initial_state="START")

        fsa.add_state(State(name="START"))

        transition = Transition(
            from_state="START",
            to_state="NONEXISTENT",
            condition=lambda ctx: True,
        )

        with pytest.raises(ValueError):
            fsa.add_transition(transition)

    def test_get_next_state_terminal(self):
        """Test get_next_state with terminal state"""
        fsa = FSA(name="test_fsa", initial_state="START")

        fsa.add_state(State(name="START", is_terminal=True))
        fsa.current_state = "START"

        context = StateContext()
        next_state = fsa.get_next_state(context)

        assert next_state is None

    def test_get_next_state_with_transitions(self):
        """Test get_next_state with valid transitions"""
        fsa = FSA(name="test_fsa", initial_state="START")

        fsa.add_state(State(name="START"))
        fsa.add_state(State(name="MIDDLE"))
        fsa.add_state(State(name="END"))

        # Add transitions with different priorities
        fsa.add_transition(Transition(
            from_state="START",
            to_state="MIDDLE",
            condition=lambda ctx: ctx.get("go_middle") is True,
            priority=10,
        ))

        fsa.add_transition(Transition(
            from_state="START",
            to_state="END",
            condition=lambda ctx: True,  # Always true
            priority=5,
        ))

        fsa.current_state = "START"
        context = StateContext()

        # Should go to MIDDLE (higher priority, condition met)
        context.set("go_middle", True)
        next_state = fsa.get_next_state(context)
        assert next_state == "MIDDLE"

        # Should go to END (MIDDLE condition not met, END always true)
        context.set("go_middle", False)
        next_state = fsa.get_next_state(context)
        assert next_state == "END"

    def test_simple_fsa_execution(self):
        """Test simple FSA execution"""
        fsa = FSA(name="test_fsa", initial_state="START")

        # Define execution functions
        def start_func(ctx: StateContext) -> StateContext:
            ctx.set("step", 1)
            return ctx

        def end_func(ctx: StateContext) -> StateContext:
            ctx.set("step", 2)
            return ctx

        # Add states
        fsa.add_state(State(name="START", execute_func=start_func))
        fsa.add_state(State(name="END", execute_func=end_func, is_terminal=True))

        # Add transition
        fsa.add_transition(Transition(
            from_state="START",
            to_state="END",
            condition=lambda ctx: ctx.get("step") == 1,
        ))

        # Execute
        responses = list(fsa.run())

        # Verify execution
        assert fsa.context.get("step") == 2
        assert fsa.context.state_history == ["START", "END"]

        # Verify events
        events = [r.event for r in responses]
        assert RunEvent.workflow_started.value in events
        assert RunEvent.workflow_completed.value in events

    def test_fsa_execution_with_error(self):
        """Test FSA execution with error state"""
        fsa = FSA(name="test_fsa", initial_state="START")

        def error_func(ctx: StateContext) -> StateContext:
            raise ValueError("Test error")

        # Add states
        fsa.add_state(State(name="START", execute_func=error_func))
        fsa.add_state(State(name="ERROR", is_terminal=True))

        # Add transition to error state
        fsa.add_transition(Transition(
            from_state="START",
            to_state="ERROR",
            condition=lambda ctx: ctx.error is not None,
        ))

        # Execute
        responses = list(fsa.run())

        # Verify error was caught
        assert fsa.context.error is not None
        assert "ERROR" in fsa.context.state_history

    def test_fsa_max_iterations(self):
        """Test FSA max iterations limit"""
        fsa = FSA(name="test_fsa", initial_state="START", max_iterations=5)

        # Create states that loop
        fsa.add_state(State(name="START", execute_func=lambda ctx: ctx))
        fsa.add_state(State(name="LOOP", execute_func=lambda ctx: ctx))

        # Add circular transitions
        fsa.add_transition(Transition(
            from_state="START",
            to_state="LOOP",
            condition=lambda ctx: True,
        ))

        fsa.add_transition(Transition(
            from_state="LOOP",
            to_state="START",
            condition=lambda ctx: True,
        ))

        # Execute
        responses = list(fsa.run())

        # Should have stopped at max iterations
        assert len(fsa.context.state_history) <= fsa.max_iterations + 1

    def test_fsa_visualize(self):
        """Test FSA visualization"""
        fsa = FSA(name="test_fsa", initial_state="START")

        fsa.add_state(State(name="START"))
        fsa.add_state(State(name="END", is_terminal=True))

        fsa.add_transition(Transition(
            from_state="START",
            to_state="END",
            condition=lambda ctx: True,
        ))

        viz = fsa.visualize()

        assert "test_fsa" in viz
        assert "START" in viz
        assert "END" in viz
        assert "terminal" in viz
        assert "->" in viz

    def test_fsa_method_chaining(self):
        """Test FSA method chaining"""
        fsa = FSA(name="test_fsa", initial_state="START")

        # Should support chaining
        result = (fsa
                  .add_state(State(name="START"))
                  .add_state(State(name="END", is_terminal=True))
                  .add_transition(Transition(
                      from_state="START",
                      to_state="END",
                      condition=lambda ctx: True,
                  )))

        assert result == fsa
        assert len(fsa.states) == 2
        assert len(fsa.transitions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

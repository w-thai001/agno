"""Tests for FSA base class."""

import pytest
from agno.fsa.base import FSA, FSAState, FSATransition


class SimpleFSA(FSA):
    """Simple FSA for testing."""

    def run(self, **kwargs):
        """Run the FSA."""
        return {"status": "completed"}


class TestFSATransition:
    """Tests for FSATransition."""

    def test_transition_initialization(self):
        """Test FSATransition initialization."""
        transition = FSATransition(from_state="a", to_state="b")
        assert transition.from_state == "a"
        assert transition.to_state == "b"
        assert transition.condition is None
        assert transition.action is None
        assert transition.metadata == {}

    def test_transition_with_condition(self):
        """Test FSATransition with condition."""
        condition = lambda x: x > 0
        transition = FSATransition(from_state="a", to_state="b", condition=condition)
        assert transition.condition is not None
        assert transition.condition(5) is True
        assert transition.condition(-1) is False

    def test_transition_with_action(self):
        """Test FSATransition with action."""
        result = []
        action = lambda x: result.append(x)
        transition = FSATransition(from_state="a", to_state="b", action=action)
        transition.action("test")
        assert "test" in result

    def test_transition_with_metadata(self):
        """Test FSATransition with metadata."""
        transition = FSATransition(
            from_state="a",
            to_state="b",
            metadata={"key": "value"}
        )
        assert transition.metadata["key"] == "value"


class TestFSA:
    """Tests for base FSA class."""

    def test_initialization(self):
        """Test FSA initialization."""
        fsa = SimpleFSA()
        assert fsa.name == "SimpleFSA"
        assert fsa.current_state == "initial"
        assert fsa.fsa_id is not None
        assert isinstance(fsa.states, set)

    def test_custom_name(self):
        """Test FSA with custom name."""
        fsa = SimpleFSA(name="CustomFSA")
        assert fsa.name == "CustomFSA"

    def test_custom_initial_state(self):
        """Test FSA with custom initial state."""
        fsa = SimpleFSA(
            current_state="processing",
            states={"initial", "processing", "completed"}
        )
        assert fsa.current_state == "processing"

    def test_invalid_initial_state(self):
        """Test FSA with invalid initial state raises error."""
        with pytest.raises(ValueError, match="not in valid states"):
            SimpleFSA(
                current_state="invalid",
                states={"initial", "completed"}
            )

    def test_add_transition(self):
        """Test adding transitions."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        assert len(fsa.transitions) > 0
        assert any(
            t.from_state == "initial" and t.to_state == "processing"
            for t in fsa.transitions
        )

    def test_add_transition_with_condition(self):
        """Test adding transition with condition."""
        fsa = SimpleFSA()
        condition = lambda x: x is not None
        fsa.add_transition("initial", "processing", condition=condition)
        transition = fsa.transitions[-1]
        assert transition.condition is not None

    def test_add_transition_with_action(self):
        """Test adding transition with action."""
        fsa = SimpleFSA()
        action = lambda x: print(f"Transitioning: {x}")
        fsa.add_transition("initial", "processing", action=action)
        transition = fsa.transitions[-1]
        assert transition.action is not None

    def test_add_transition_invalid_from_state(self):
        """Test adding transition with invalid from_state."""
        fsa = SimpleFSA()
        with pytest.raises(ValueError, match="from_state.*not in valid states"):
            fsa.add_transition("invalid", "processing")

    def test_add_transition_invalid_to_state(self):
        """Test adding transition with invalid to_state."""
        fsa = SimpleFSA()
        with pytest.raises(ValueError, match="to_state.*not in valid states"):
            fsa.add_transition("initial", "invalid")

    def test_can_transition_valid(self):
        """Test can_transition with valid transition."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        assert fsa.can_transition("processing") is True

    def test_can_transition_invalid_state(self):
        """Test can_transition with invalid state."""
        fsa = SimpleFSA()
        assert fsa.can_transition("nonexistent") is False

    def test_can_transition_no_transition_defined(self):
        """Test can_transition when no transition is defined."""
        fsa = SimpleFSA()
        # No transitions added
        fsa.transitions = []
        assert fsa.can_transition("completed") is False

    def test_can_transition_with_failing_condition(self):
        """Test can_transition with failing condition."""
        fsa = SimpleFSA()
        condition = lambda x: x == "allow"
        fsa.add_transition("initial", "processing", condition=condition)
        assert fsa.can_transition("processing", "deny") is False

    def test_can_transition_with_passing_condition(self):
        """Test can_transition with passing condition."""
        fsa = SimpleFSA()
        condition = lambda x: x == "allow"
        fsa.add_transition("initial", "processing", condition=condition)
        assert fsa.can_transition("processing", "allow") is True

    def test_transition_success(self):
        """Test successful transition."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        result = fsa.transition("processing")
        assert result is True
        assert fsa.current_state == "processing"

    def test_transition_invalid(self):
        """Test invalid transition."""
        fsa = SimpleFSA()
        # No transition defined
        result = fsa.transition("processing")
        assert result is False
        assert fsa.current_state == "initial"

    def test_transition_executes_action(self):
        """Test transition executes action."""
        fsa = SimpleFSA()
        executed = []
        action = lambda x: executed.append("action_executed")
        fsa.add_transition("initial", "processing", action=action)
        fsa.transition("processing", "context")
        assert "action_executed" in executed

    def test_transition_records_history(self):
        """Test transition records history."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        initial_history_len = len(fsa.transition_history)
        fsa.transition("processing")
        assert len(fsa.transition_history) == initial_history_len + 1
        assert len(fsa.state_history) > 0

    def test_transition_failed_action(self):
        """Test transition with failed action."""
        fsa = SimpleFSA()
        action = lambda x: 1 / 0  # Will raise ZeroDivisionError
        fsa.add_transition("initial", "processing", action=action)
        result = fsa.transition("processing")
        assert result is False
        assert fsa.current_state == "initial"

    def test_reset(self):
        """Test FSA reset."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        fsa.transition("processing")
        assert fsa.current_state == "processing"
        fsa.reset()
        assert fsa.current_state == "initial"

    def test_reset_clears_state_for_stateless(self):
        """Test reset clears state for stateless FSA."""
        fsa = SimpleFSA(stateful=False)
        fsa.session_state["key"] = "value"
        fsa.reset()
        assert "key" not in fsa.session_state

    def test_reset_preserves_state_for_stateful(self):
        """Test reset preserves state for stateful FSA."""
        fsa = SimpleFSA(stateful=True)
        fsa.session_state["key"] = "value"
        fsa.reset()
        assert fsa.session_state["key"] == "value"

    def test_get_state_info(self):
        """Test get_state_info."""
        fsa = SimpleFSA()
        info = fsa.get_state_info()
        assert info["name"] == "SimpleFSA"
        assert info["current_state"] == "initial"
        assert "fsa_id" in info
        assert "valid_states" in info
        assert "transition_count" in info
        assert info["stateful"] is True

    def test_session_state(self):
        """Test session state management."""
        fsa = SimpleFSA()
        fsa.session_state["key"] = "value"
        assert fsa.session_state["key"] == "value"

    def test_context(self):
        """Test context management."""
        fsa = SimpleFSA()
        fsa.context["key"] = "value"
        assert fsa.context["key"] == "value"

    def test_stateful_flag(self):
        """Test stateful flag."""
        fsa = SimpleFSA(stateful=True)
        assert fsa.stateful is True
        fsa2 = SimpleFSA(stateful=False)
        assert fsa2.stateful is False

    def test_cascade_aware_flag(self):
        """Test cascade_aware flag."""
        fsa = SimpleFSA(cascade_aware=True)
        assert fsa.cascade_aware is True
        fsa2 = SimpleFSA(cascade_aware=False)
        assert fsa2.cascade_aware is False

    def test_run_method(self):
        """Test run method."""
        fsa = SimpleFSA()
        result = fsa.run()
        assert result["status"] == "completed"

    def test_multiple_transitions(self):
        """Test multiple state transitions."""
        fsa = SimpleFSA()
        fsa.add_transition("initial", "processing")
        fsa.add_transition("processing", "completed")

        assert fsa.transition("processing")
        assert fsa.current_state == "processing"

        assert fsa.transition("completed")
        assert fsa.current_state == "completed"

        assert len(fsa.transition_history) >= 2

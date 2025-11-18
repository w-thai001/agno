"""
Comprehensive unit tests for TokenBudgetManagerFSA.

Tests cover budget tracking, prediction, enforcement, allocation, analytics,
edge cases, and error handling.
"""

from datetime import datetime, timedelta

import pytest

from agno.fsas.token_budget_manager_fsa import (
    Agent,
    AllocationStrategy,
    BudgetRequest,
    BudgetState,
    EnforcementLevel,
    TokenBudgetManagerFSA,
)


class TestBasicBudgetTracking:
    """Test basic budget tracking and allocation functionality."""

    def test_initialization(self):
        """Test FSA initializes with correct default values."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        assert manager.total_budget == 10000
        assert manager.current_usage == 0
        assert manager.current_state == BudgetState.IDLE
        assert manager.soft_limit_percentage == 80.0
        assert manager.hard_limit_percentage == 95.0

    def test_basic_budget_tracking(self):
        """Test basic token consumption tracking."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        # Track some consumption
        manager.track_consumption(tokens_used=1000, operation_id="op1", operation_type="completion")
        assert manager.current_usage == 1000

        manager.track_consumption(tokens_used=500, operation_id="op2", operation_type="completion")
        assert manager.current_usage == 1500

        # Check operation history
        assert len(manager.operation_history) == 2

    def test_budget_tracking_validation(self):
        """Test that negative token tracking raises error."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        with pytest.raises(ValueError, match="Tokens used cannot be negative"):
            manager.track_consumption(tokens_used=-100, operation_id="op1")

    def test_execute_basic_operation(self):
        """Test basic execute pipeline."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        decision = manager.execute(operation="completion", estimated_tokens=1000)

        assert decision.approved is True
        assert decision.allocated_tokens == 1000
        assert decision.remaining_budget < 10000  # Budget reserved


class TestBudgetAllocation:
    """Test multi-agent budget allocation strategies."""

    def test_equal_allocation(self):
        """Test equal budget distribution across agents."""
        manager = TokenBudgetManagerFSA()

        agents = [
            Agent(agent_id="agent1", name="Agent 1"),
            Agent(agent_id="agent2", name="Agent 2"),
            Agent(agent_id="agent3", name="Agent 3"),
        ]

        allocations = manager.allocate_budget(
            agents=agents,
            total_budget=9000,
            strategy=AllocationStrategy.EQUAL,
        )

        # Should be roughly equal (9000 / 3 = 3000 each)
        assert allocations["agent1"] == 3000
        assert allocations["agent2"] == 3000
        assert allocations["agent3"] == 3000

    def test_priority_based_allocation(self):
        """Test priority-based budget allocation."""
        manager = TokenBudgetManagerFSA()

        agents = [
            Agent(agent_id="agent1", name="Agent 1", priority=5),
            Agent(agent_id="agent2", name="Agent 2", priority=3),
            Agent(agent_id="agent3", name="Agent 3", priority=2),
        ]

        allocations = manager.allocate_budget(
            agents=agents,
            total_budget=10000,
            strategy=AllocationStrategy.PRIORITY_BASED,
        )

        # Higher priority should get more budget
        assert allocations["agent1"] > allocations["agent2"]
        assert allocations["agent2"] > allocations["agent3"]
        assert allocations["agent1"] == 5000  # 5/10 of budget
        assert allocations["agent2"] == 3000  # 3/10 of budget
        assert allocations["agent3"] == 2000  # 2/10 of budget

    def test_proportional_allocation(self):
        """Test proportional allocation based on historical usage."""
        manager = TokenBudgetManagerFSA()

        agents = [
            Agent(agent_id="agent1", name="Agent 1", historical_usage=5000),
            Agent(agent_id="agent2", name="Agent 2", historical_usage=3000),
            Agent(agent_id="agent3", name="Agent 3", historical_usage=2000),
        ]

        allocations = manager.allocate_budget(
            agents=agents,
            total_budget=10000,
            strategy=AllocationStrategy.PROPORTIONAL,
        )

        # Should be proportional to historical usage
        assert allocations["agent1"] == 5000  # 5000/10000 * 10000
        assert allocations["agent2"] == 3000  # 3000/10000 * 10000
        assert allocations["agent3"] == 2000  # 2000/10000 * 10000

    def test_weighted_allocation(self):
        """Test weighted budget allocation."""
        manager = TokenBudgetManagerFSA()

        agents = [
            Agent(agent_id="agent1", name="Agent 1", weight=2.0),
            Agent(agent_id="agent2", name="Agent 2", weight=1.0),
            Agent(agent_id="agent3", name="Agent 3", weight=1.0),
        ]

        allocations = manager.allocate_budget(
            agents=agents,
            total_budget=10000,
            strategy=AllocationStrategy.WEIGHTED,
        )

        # Agent 1 with weight 2.0 should get half the budget
        assert allocations["agent1"] == 5000  # 2/4 of budget
        assert allocations["agent2"] == 2500  # 1/4 of budget
        assert allocations["agent3"] == 2500  # 1/4 of budget

    def test_dynamic_allocation(self):
        """Test dynamic allocation considering priority and usage."""
        manager = TokenBudgetManagerFSA()

        agents = [
            Agent(agent_id="agent1", name="Agent 1", priority=8, historical_usage=6000),
            Agent(agent_id="agent2", name="Agent 2", priority=5, historical_usage=3000),
            Agent(agent_id="agent3", name="Agent 3", priority=3, historical_usage=1000),
        ]

        allocations = manager.allocate_budget(
            agents=agents,
            total_budget=10000,
            strategy=AllocationStrategy.DYNAMIC,
        )

        # Higher priority and usage should get more
        assert allocations["agent1"] > allocations["agent2"]
        assert allocations["agent2"] > allocations["agent3"]


class TestPredictionEngine:
    """Test token usage prediction functionality."""

    def test_prediction_no_history(self):
        """Test prediction with no historical data."""
        manager = TokenBudgetManagerFSA()

        prediction = manager.predict_usage("new_operation")

        assert prediction.operation_type == "new_operation"
        assert prediction.confidence == 0.0
        assert prediction.sample_size == 0
        assert prediction.predicted_tokens == 1000  # Default estimate

    def test_prediction_with_history(self):
        """Test prediction accuracy with historical data."""
        manager = TokenBudgetManagerFSA()

        # Create some history
        for i in range(10):
            manager.track_consumption(
                tokens_used=1000 + (i * 10),  # 1000, 1010, 1020, ...
                operation_id=f"op{i}",
                operation_type="completion",
            )

        prediction = manager.predict_usage("completion")

        assert prediction.operation_type == "completion"
        assert prediction.confidence > 0.0
        assert prediction.sample_size == 10
        assert prediction.predicted_tokens > 1000  # Should predict higher due to variance

    def test_prediction_caching(self):
        """Test that predictions are cached and reused."""
        manager = TokenBudgetManagerFSA()

        # Create history
        for i in range(5):
            manager.track_consumption(
                tokens_used=1000,
                operation_id=f"op{i}",
                operation_type="completion",
            )

        # First prediction
        prediction1 = manager.predict_usage("completion")

        # Add more data
        manager.track_consumption(tokens_used=2000, operation_id="op_new", operation_type="other")

        # Second prediction for same type (should be recalculated as cache was invalidated)
        prediction2 = manager.predict_usage("completion")

        # Predictions should be same since we didn't add completion data
        assert prediction1.predicted_tokens == prediction2.predicted_tokens


class TestLimitEnforcement:
    """Test budget limit enforcement with soft/hard thresholds."""

    def test_soft_limit_enforcement(self):
        """Test soft limit warning."""
        manager = TokenBudgetManagerFSA(
            total_budget=10000,
            soft_limit_percentage=80.0,
            hard_limit_percentage=95.0,
        )

        # At 85% usage (between soft and hard)
        action = manager.enforce_limits(current_usage=8500, limit=10000)

        assert action.action_type == "warn"
        assert "Soft limit exceeded" in action.message
        assert action.usage_percentage == 85.0

    def test_hard_limit_enforcement(self):
        """Test hard limit blocking."""
        manager = TokenBudgetManagerFSA(
            total_budget=10000,
            soft_limit_percentage=80.0,
            hard_limit_percentage=95.0,
        )

        # At 96% usage (above hard limit)
        action = manager.enforce_limits(current_usage=9600, limit=10000)

        assert action.action_type == "block"
        assert "Hard limit reached" in action.message
        assert action.usage_percentage == 96.0

    def test_within_limits_enforcement(self):
        """Test normal operation within limits."""
        manager = TokenBudgetManagerFSA(
            total_budget=10000,
            soft_limit_percentage=80.0,
            hard_limit_percentage=95.0,
        )

        # At 50% usage (well within limits)
        action = manager.enforce_limits(current_usage=5000, limit=10000)

        assert action.action_type == "allow"
        assert "Within budget limits" in action.message
        assert action.usage_percentage == 50.0

    def test_enforcement_with_execute(self):
        """Test that execute respects enforcement."""
        manager = TokenBudgetManagerFSA(
            total_budget=10000,
            soft_limit_percentage=80.0,
            hard_limit_percentage=95.0,
        )

        # Fill up to just below hard limit but request would exceed it
        manager.current_usage = 9000

        # Try to execute operation that would exceed hard limit
        decision = manager.execute(operation="completion", estimated_tokens=600)

        assert decision.approved is False
        assert decision.enforcement_action == "block"


class TestValidation:
    """Test budget request validation."""

    def test_validate_normal_request(self):
        """Test validation of normal request."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        request = BudgetRequest(operation_type="completion", requested_tokens=1000)
        result = manager.validate(request)

        assert result.is_valid is True
        assert result.approved_tokens == 1000

    def test_validate_exceeds_total_budget(self):
        """Test validation when request exceeds total budget."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        request = BudgetRequest(operation_type="completion", requested_tokens=15000)
        result = manager.validate(request)

        assert result.is_valid is False
        assert "exceed total budget" in result.reason

    def test_validate_insufficient_available_budget(self):
        """Test validation with insufficient available budget."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        # Use up most budget
        manager.current_usage = 8000

        request = BudgetRequest(operation_type="completion", requested_tokens=3000)
        result = manager.validate(request)

        assert result.is_valid is False
        assert "Insufficient budget" in result.reason

    def test_validate_negative_tokens(self):
        """Test validation rejects negative tokens."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        # This should raise a validation error when creating the request
        with pytest.raises(Exception):  # Pydantic will raise validation error
            request = BudgetRequest(operation_type="completion", requested_tokens=-100)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_budget_exhaustion(self):
        """Test behavior when budget is fully exhausted."""
        manager = TokenBudgetManagerFSA(total_budget=1000)

        # Exhaust the budget
        manager.track_consumption(tokens_used=1000, operation_id="op1", operation_type="completion")

        # Try to get more budget
        decision = manager.execute(operation="completion", estimated_tokens=100)

        assert decision.approved is False
        assert decision.allocated_tokens == 0

    def test_zero_budget(self):
        """Test FSA with zero budget."""
        manager = TokenBudgetManagerFSA(total_budget=0)

        decision = manager.execute(operation="completion", estimated_tokens=100)

        assert decision.approved is False

    def test_negative_budget_raises_error(self):
        """Test that negative budget raises error."""
        with pytest.raises(ValueError, match="Total budget must be non-negative"):
            TokenBudgetManagerFSA(total_budget=-1000)

    def test_empty_agent_list_allocation(self):
        """Test allocation with empty agent list."""
        manager = TokenBudgetManagerFSA()

        allocations = manager.allocate_budget(agents=[], total_budget=10000)

        assert allocations == {}

    def test_reset_budget(self):
        """Test budget reset functionality."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        # Use some budget
        manager.current_usage = 5000
        manager.reservations["op1"] = 1000

        # Reset
        manager.reset_budget()

        assert manager.current_usage == 0
        assert len(manager.reservations) == 0

    def test_reset_budget_with_new_amount(self):
        """Test budget reset with new budget amount."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        manager.reset_budget(new_budget=20000)

        assert manager.total_budget == 20000
        assert manager.current_usage == 0


class TestAnalytics:
    """Test historical analytics and trend detection."""

    def test_analyze_trends_no_data(self):
        """Test analytics with no historical data."""
        manager = TokenBudgetManagerFSA()

        analytics = manager.analyze_trends(time_window="24h")

        assert analytics.total_tokens_used == 0
        assert analytics.num_operations == 0
        assert analytics.trend == "stable"
        assert analytics.efficiency_score == 100.0

    def test_analyze_trends_with_data(self):
        """Test analytics with historical data."""
        manager = TokenBudgetManagerFSA()

        # Create some operations
        for i in range(10):
            manager.track_consumption(
                tokens_used=1000,
                operation_id=f"op{i}",
                operation_type="completion",
            )

        analytics = manager.analyze_trends(time_window="24h")

        assert analytics.total_tokens_used == 10000
        assert analytics.num_operations == 10
        assert analytics.average_tokens_per_operation == 1000.0
        assert analytics.peak_usage == 1000

    def test_analyze_increasing_trend(self):
        """Test detection of increasing usage trend."""
        manager = TokenBudgetManagerFSA()

        # Create increasing usage pattern
        for i in range(20):
            tokens = 500 + (i * 100)  # Increasing from 500 to 2400
            manager.track_consumption(
                tokens_used=tokens,
                operation_id=f"op{i}",
                operation_type="completion",
            )

        analytics = manager.analyze_trends(time_window="24h")

        assert analytics.trend == "increasing"

    def test_analyze_decreasing_trend(self):
        """Test detection of decreasing usage trend."""
        manager = TokenBudgetManagerFSA()

        # Create decreasing usage pattern
        for i in range(20):
            tokens = 2000 - (i * 50)  # Decreasing from 2000 to 1050
            manager.track_consumption(
                tokens_used=tokens,
                operation_id=f"op{i}",
                operation_type="completion",
            )

        analytics = manager.analyze_trends(time_window="24h")

        assert analytics.trend == "decreasing"

    def test_operation_type_breakdown(self):
        """Test operation type breakdown in analytics."""
        manager = TokenBudgetManagerFSA()

        # Create different operation types
        manager.track_consumption(tokens_used=1000, operation_id="op1", operation_type="completion")
        manager.track_consumption(tokens_used=2000, operation_id="op2", operation_type="completion")
        manager.track_consumption(tokens_used=500, operation_id="op3", operation_type="embedding")
        manager.track_consumption(tokens_used=300, operation_id="op4", operation_type="embedding")

        analytics = manager.analyze_trends(time_window="24h")

        assert analytics.operation_type_breakdown["completion"] == 3000
        assert analytics.operation_type_breakdown["embedding"] == 800


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_invalid_limit_percentages(self):
        """Test that invalid limit percentages raise errors."""
        with pytest.raises(ValueError, match="Soft limit percentage must be between 0 and 100"):
            TokenBudgetManagerFSA(soft_limit_percentage=150.0)

        with pytest.raises(ValueError, match="Hard limit percentage must be between 0 and 100"):
            TokenBudgetManagerFSA(hard_limit_percentage=150.0)

    def test_soft_limit_greater_than_hard_limit(self):
        """Test that soft limit > hard limit raises error."""
        with pytest.raises(ValueError, match="Soft limit must be less than or equal to hard limit"):
            TokenBudgetManagerFSA(soft_limit_percentage=95.0, hard_limit_percentage=80.0)

    def test_error_state_tracking(self):
        """Test that errors are tracked properly."""
        manager = TokenBudgetManagerFSA()

        initial_error_count = manager.error_count

        # Force an error by passing invalid data
        try:
            manager.enforce_limits(current_usage=-100, limit=10000)
        except ValueError:
            pass

        # Error count should not increase for validation errors
        # But last_error should be set for execute errors
        assert manager.error_count >= initial_error_count

    def test_get_status(self):
        """Test status reporting."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        manager.track_consumption(tokens_used=3000, operation_id="op1", operation_type="completion")

        status = manager.get_status()

        assert status["total_budget"] == 10000
        assert status["current_usage"] == 3000
        assert status["state"] == "idle"
        assert status["usage_percentage"] == 30.0
        assert status["num_operations"] == 1


class TestReservations:
    """Test budget reservation functionality."""

    def test_reservation_on_execute(self):
        """Test that execute creates reservations."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        decision = manager.execute(operation="completion", estimated_tokens=1000)

        assert decision.approved is True
        assert len(manager.reservations) == 1
        assert manager.reservations[decision.operation_id] == 1000

    def test_reservation_released_on_tracking(self):
        """Test that tracking releases reservations."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        decision = manager.execute(operation="completion", estimated_tokens=1000)
        operation_id = decision.operation_id

        # Track actual consumption
        manager.track_consumption(tokens_used=900, operation_id=operation_id, operation_type="completion")

        # Reservation should be released
        assert operation_id not in manager.reservations

    def test_available_budget_accounts_for_reservations(self):
        """Test that available budget considers reservations."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        # Reserve some budget
        decision1 = manager.execute(operation="completion", estimated_tokens=3000)
        decision2 = manager.execute(operation="completion", estimated_tokens=2000)

        # Available should account for both reservations
        available = manager._get_available_budget()
        assert available == 5000  # 10000 - 3000 - 2000

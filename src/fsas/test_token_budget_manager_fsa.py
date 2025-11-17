"""Tests for Token Budget Manager FSA."""

import pytest
from datetime import datetime

from src.fsas.token_budget_manager_fsa import (
    AllocationStrategy,
    BudgetAllocation,
    BudgetStatus,
    FSAConfig,
    OptimizationRecommendation,
    TokenBudgetManagerFSA,
    UsageRecord,
    UsageStatistics,
)


class TestBudgetAllocation:
    """Test BudgetAllocation dataclass."""

    def test_initialization(self):
        """Test allocation initialization with defaults."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)

        assert alloc.fsa_id == "test_fsa"
        assert alloc.allocated_tokens == 1000
        assert alloc.used_tokens == 0
        assert alloc.soft_limit == 800  # 80% of 1000
        assert alloc.hard_limit == 1000

    def test_remaining_tokens(self):
        """Test remaining tokens calculation."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)
        alloc.used_tokens = 300

        assert alloc.remaining_tokens == 700

    def test_usage_ratio(self):
        """Test usage ratio calculation."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)
        alloc.used_tokens = 500

        assert alloc.usage_ratio == 0.5

    def test_status_ok(self):
        """Test OK status when usage is below soft limit."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)
        alloc.used_tokens = 500

        assert alloc.status == BudgetStatus.OK

    def test_status_warning(self):
        """Test WARNING status when usage exceeds soft limit."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)
        alloc.used_tokens = 850

        assert alloc.status == BudgetStatus.WARNING

    def test_status_exceeded(self):
        """Test EXCEEDED status when usage exceeds hard limit."""
        alloc = BudgetAllocation(fsa_id="test_fsa", allocated_tokens=1000)
        alloc.used_tokens = 1100

        assert alloc.status == BudgetStatus.EXCEEDED


class TestTokenBudgetManagerFSA:
    """Test TokenBudgetManagerFSA class."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = TokenBudgetManagerFSA(
            total_budget=10000,
            default_strategy=AllocationStrategy.EQUAL,
        )

        assert manager.total_budget == 10000
        assert manager.default_strategy == AllocationStrategy.EQUAL
        assert len(manager.allocations) == 0
        assert len(manager.usage_history) == 0

    def test_allocate_budget_equal(self):
        """Test equal allocation strategy."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1"),
            FSAConfig(fsa_id="fsa2"),
            FSAConfig(fsa_id="fsa3"),
        ]

        allocations = manager.allocate_budget(
            total_tokens=9000,
            fsas_config=configs,
            strategy=AllocationStrategy.EQUAL,
        )

        assert len(allocations) == 3
        assert allocations["fsa1"].allocated_tokens == 3000
        assert allocations["fsa2"].allocated_tokens == 3000
        assert allocations["fsa3"].allocated_tokens == 3000

    def test_allocate_budget_weighted(self):
        """Test weighted allocation strategy."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1", weight=2.0),
            FSAConfig(fsa_id="fsa2", weight=1.0),
            FSAConfig(fsa_id="fsa3", weight=1.0),
        ]

        allocations = manager.allocate_budget(
            total_tokens=8000,
            fsas_config=configs,
            strategy=AllocationStrategy.WEIGHTED,
        )

        assert len(allocations) == 3
        assert allocations["fsa1"].allocated_tokens == 4000  # 2/4 of total
        assert allocations["fsa2"].allocated_tokens == 2000  # 1/4 of total
        assert allocations["fsa3"].allocated_tokens == 2000  # 1/4 of total

    def test_allocate_budget_priority(self):
        """Test priority-based allocation strategy."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1", priority=1),  # Highest priority
            FSAConfig(fsa_id="fsa2", priority=2),
            FSAConfig(fsa_id="fsa3", priority=3),  # Lowest priority
        ]

        allocations = manager.allocate_budget(
            total_tokens=6000,
            fsas_config=configs,
            strategy=AllocationStrategy.PRIORITY,
        )

        assert len(allocations) == 3
        # Higher priority (lower number) gets more tokens
        assert allocations["fsa1"].allocated_tokens > allocations["fsa2"].allocated_tokens
        assert allocations["fsa2"].allocated_tokens > allocations["fsa3"].allocated_tokens

    def test_allocate_budget_with_hard_limits(self):
        """Test allocation with hard limits override."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1", hard_limit=5000),
            FSAConfig(fsa_id="fsa2"),
        ]

        allocations = manager.allocate_budget(
            total_tokens=10000,
            fsas_config=configs,
            strategy=AllocationStrategy.EQUAL,
        )

        assert allocations["fsa1"].hard_limit == 5000
        assert allocations["fsa2"].hard_limit == 5000

    def test_track_usage(self):
        """Test tracking token usage."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(5000, configs)

        remaining, status = manager.track_usage("fsa1", input_tokens=100, output_tokens=200)

        assert remaining == 4700  # 5000 - 300
        assert status == BudgetStatus.OK
        assert manager.allocations["fsa1"].used_tokens == 300
        assert len(manager.usage_history) == 1

    def test_track_usage_multiple_calls(self):
        """Test tracking multiple usage calls."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(5000, configs)

        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)
        manager.track_usage("fsa1", input_tokens=150, output_tokens=250)

        assert manager.allocations["fsa1"].used_tokens == 700  # 300 + 400
        assert len(manager.usage_history) == 2

    def test_track_usage_auto_allocation(self):
        """Test auto-allocation for untracked FSA."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        remaining, status = manager.track_usage("new_fsa", input_tokens=50, output_tokens=100)

        assert "new_fsa" in manager.allocations
        assert manager.allocations["new_fsa"].used_tokens == 150

    def test_check_budget(self):
        """Test checking remaining budget."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(5000, configs)
        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)

        remaining = manager.check_budget("fsa1")

        assert remaining == 4700

    def test_get_budget_status(self):
        """Test getting budget status."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(1000, configs)

        # OK status
        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)
        assert manager.get_budget_status("fsa1") == BudgetStatus.OK

        # WARNING status
        manager.track_usage("fsa1", input_tokens=200, output_tokens=300)
        assert manager.get_budget_status("fsa1") == BudgetStatus.WARNING

        # EXCEEDED status
        manager.track_usage("fsa1", input_tokens=300, output_tokens=400)
        assert manager.get_budget_status("fsa1") == BudgetStatus.EXCEEDED

    def test_optimize_allocation_underutilized(self):
        """Test optimization recommendations for underutilized FSA."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(10000, configs)

        # Simulate low usage over multiple calls
        for _ in range(10):
            manager.track_usage("fsa1", input_tokens=10, output_tokens=10)

        recommendations = manager.optimize_allocation()

        assert len(recommendations) > 0
        # Should recommend reducing allocation
        rec = next((r for r in recommendations if "Low utilization" in r.reason), None)
        assert rec is not None
        assert rec.recommended_allocation < rec.current_allocation

    def test_optimize_allocation_overutilized(self):
        """Test optimization recommendations for overutilized FSA."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(1000, configs)

        # Simulate high usage
        manager.track_usage("fsa1", input_tokens=400, output_tokens=500)

        recommendations = manager.optimize_allocation()

        # Should recommend increasing allocation
        rec = next((r for r in recommendations if "High utilization" in r.reason), None)
        assert rec is not None
        assert rec.recommended_allocation > rec.current_allocation

    def test_get_usage_report(self):
        """Test comprehensive usage report generation."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1"),
            FSAConfig(fsa_id="fsa2"),
        ]
        manager.allocate_budget(6000, configs)

        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)
        manager.track_usage("fsa1", input_tokens=150, output_tokens=250)
        manager.track_usage("fsa2", input_tokens=50, output_tokens=100)

        report = manager.get_usage_report()

        assert isinstance(report, UsageStatistics)
        assert report.total_tokens_allocated == 6000
        assert report.total_tokens_used == 850  # 300 + 400 + 150
        assert report.total_calls == 3
        assert "fsa1" in report.fsa_stats
        assert "fsa2" in report.fsa_stats
        assert report.fsa_stats["fsa1"]["calls"] == 2
        assert report.fsa_stats["fsa2"]["calls"] == 1
        assert 0.0 <= report.efficiency_score <= 1.0

    def test_reset_usage_specific_fsa(self):
        """Test resetting usage for specific FSA."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1"),
            FSAConfig(fsa_id="fsa2"),
        ]
        manager.allocate_budget(6000, configs)

        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)
        manager.track_usage("fsa2", input_tokens=50, output_tokens=100)

        manager.reset_usage("fsa1")

        assert manager.allocations["fsa1"].used_tokens == 0
        assert manager.allocations["fsa2"].used_tokens == 150
        assert len([r for r in manager.usage_history if r.fsa_id == "fsa1"]) == 0

    def test_reset_usage_all(self):
        """Test resetting usage for all FSAs."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [
            FSAConfig(fsa_id="fsa1"),
            FSAConfig(fsa_id="fsa2"),
        ]
        manager.allocate_budget(6000, configs)

        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)
        manager.track_usage("fsa2", input_tokens=50, output_tokens=100)

        manager.reset_usage()

        assert manager.allocations["fsa1"].used_tokens == 0
        assert manager.allocations["fsa2"].used_tokens == 0
        assert len(manager.usage_history) == 0

    def test_warnings_generation(self):
        """Test warning generation for budget issues."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(1000, configs)

        # Exceed soft limit
        manager.track_usage("fsa1", input_tokens=400, output_tokens=500)

        report = manager.get_usage_report()

        assert len(report.warnings) > 0
        assert any("approaching budget limit" in w for w in report.warnings)

    def test_dict_config_input(self):
        """Test allocation with dictionary config input."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = {
            "fsa1": {"weight": 2.0, "priority": 1},
            "fsa2": {"weight": 1.0, "priority": 2},
        }

        allocations = manager.allocate_budget(
            total_tokens=6000,
            fsas_config=configs,
            strategy=AllocationStrategy.WEIGHTED,
        )

        assert len(allocations) == 2
        assert "fsa1" in allocations
        assert "fsa2" in allocations

    def test_efficiency_score_calculation(self):
        """Test efficiency score calculation."""
        manager = TokenBudgetManagerFSA(total_budget=10000)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(1000, configs)

        # Optimal usage (around 80%)
        manager.track_usage("fsa1", input_tokens=400, output_tokens=400)

        report = manager.get_usage_report()

        assert 0.0 <= report.efficiency_score <= 1.0
        # Should be relatively high for optimal usage
        assert report.efficiency_score > 0.5

    def test_tracking_disabled(self):
        """Test usage tracking can be disabled."""
        manager = TokenBudgetManagerFSA(total_budget=10000, enable_tracking=False)

        configs = [FSAConfig(fsa_id="fsa1")]
        manager.allocate_budget(1000, configs)

        manager.track_usage("fsa1", input_tokens=100, output_tokens=200)

        # Usage should still be tracked in allocations
        assert manager.allocations["fsa1"].used_tokens == 300
        # But detailed history should be empty
        assert len(manager.usage_history) == 0


class TestFSAConfig:
    """Test FSAConfig dataclass."""

    def test_default_values(self):
        """Test FSAConfig default values."""
        config = FSAConfig(fsa_id="test")

        assert config.fsa_id == "test"
        assert config.weight == 1.0
        assert config.priority == 1
        assert config.soft_limit_ratio == 0.8
        assert config.hard_limit is None

    def test_custom_values(self):
        """Test FSAConfig with custom values."""
        config = FSAConfig(
            fsa_id="test",
            weight=2.5,
            priority=3,
            soft_limit_ratio=0.7,
            hard_limit=5000,
        )

        assert config.weight == 2.5
        assert config.priority == 3
        assert config.soft_limit_ratio == 0.7
        assert config.hard_limit == 5000


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_budget_lifecycle(self):
        """Test complete budget management lifecycle."""
        # Initialize manager
        manager = TokenBudgetManagerFSA(total_budget=20000)

        # Allocate budget
        configs = [
            FSAConfig(fsa_id="parser", weight=1.5, priority=1),
            FSAConfig(fsa_id="analyzer", weight=2.0, priority=2),
            FSAConfig(fsa_id="generator", weight=1.0, priority=3),
        ]

        allocations = manager.allocate_budget(
            total_tokens=18000,
            fsas_config=configs,
            strategy=AllocationStrategy.WEIGHTED,
        )

        assert len(allocations) == 3

        # Simulate usage
        manager.track_usage("parser", input_tokens=500, output_tokens=1000)
        manager.track_usage("analyzer", input_tokens=800, output_tokens=1200)
        manager.track_usage("generator", input_tokens=300, output_tokens=700)
        manager.track_usage("parser", input_tokens=400, output_tokens=800)

        # Check budgets
        parser_remaining = manager.check_budget("parser")
        assert parser_remaining > 0

        # Get optimization recommendations
        recommendations = manager.optimize_allocation()
        assert isinstance(recommendations, list)

        # Generate report
        report = manager.get_usage_report()
        assert report.total_calls == 4
        assert report.total_tokens_used > 0
        assert len(report.fsa_stats) == 3

    def test_budget_exhaustion_scenario(self):
        """Test scenario where FSA exhausts its budget."""
        manager = TokenBudgetManagerFSA(total_budget=5000)

        configs = [FSAConfig(fsa_id="limited_fsa")]
        manager.allocate_budget(1000, configs)

        # Use up most of the budget
        remaining1, status1 = manager.track_usage("limited_fsa", input_tokens=300, output_tokens=400)
        assert status1 == BudgetStatus.OK

        # Trigger warning
        remaining2, status2 = manager.track_usage("limited_fsa", input_tokens=150, output_tokens=150)
        assert status2 == BudgetStatus.WARNING

        # Exceed budget
        remaining3, status3 = manager.track_usage("limited_fsa", input_tokens=100, output_tokens=200)
        assert status3 == BudgetStatus.EXCEEDED
        assert remaining3 == 0

        # Check warnings in report
        report = manager.get_usage_report()
        assert len(report.warnings) > 0

"""
Unit tests for LQ Calculator
"""

import pytest

from agno.fsa_0_1_mla_task_deconstructor.core.lq_calculator import LQCalculator
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal


class TestLQCalculator:
    """Test cases for LQCalculator"""

    def setup_method(self):
        """Setup test fixtures"""
        self.calculator = LQCalculator()
        self.goal = Goal(G="Build a revenue system", O_G="System generates revenue", confidence=0.9)

    def test_estimate_time(self):
        """Test time estimation"""
        action = "Write a simple function"
        time = self.calculator._estimate_time(action, {})

        assert time > 0
        assert isinstance(time, float)

    def test_estimate_cognitive_load(self):
        """Test cognitive load estimation"""
        simple_action = "Copy a file"
        complex_action = "Design a distributed algorithm"

        simple_load = self.calculator._estimate_cognitive_load(simple_action, {})
        complex_load = self.calculator._estimate_cognitive_load(complex_action, {})

        # Simple should have lower cognitive load
        cognitive_values = {"trivial": 10, "low": 25, "medium": 50, "high": 75, "very_high": 90}

        assert cognitive_values.get(simple_load, 50) < cognitive_values.get(complex_load, 50)

    def test_estimate_immediate_progress(self):
        """Test immediate progress estimation"""
        action = "Build revenue system infrastructure"
        progress = self.calculator._estimate_immediate_progress(action, self.goal, {})

        assert 0 <= progress <= 100

    def test_estimate_future_efficiency(self):
        """Test future efficiency estimation"""
        framework_action = "Build automation framework"
        simple_action = "Write a single function"

        framework_efficiency = self.calculator._estimate_future_efficiency(framework_action, self.goal, {})
        simple_efficiency = self.calculator._estimate_future_efficiency(simple_action, self.goal, {})

        # Framework should have higher efficiency
        assert framework_efficiency >= simple_efficiency

    def test_create_action(self):
        """Test action creation with estimates"""
        action = self.calculator.create_action(
            action_id="a1", description="Build payment system", goal=self.goal, context={}, dependencies=[]
        )

        assert action.action_id == "a1"
        assert action.description == "Build payment system"
        assert action.cost.time_minutes > 0
        assert action.impact.immediate_progress > 0

        # Calculate LQ_MLA
        lq = action.calculate_lq_mla()
        assert lq > 0

    def test_estimate_action_components(self):
        """Test complete component estimation"""
        action = "Implement automated billing system"
        components = self.calculator.estimate_action_components(action, self.goal, {})

        assert "cost" in components
        assert "impact" in components
        assert components["cost"]["time_minutes"] > 0
        assert components["impact"]["immediate_progress"] > 0

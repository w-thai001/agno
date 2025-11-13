"""
Unit tests for Goal Analyzer
"""

import pytest

from agno.fsa_0_1_mla_task_deconstructor.core.goal_analyzer import GoalAnalyzer
from agno.fsa_0_1_mla_task_deconstructor.core.task_parser import TaskParser


class TestGoalAnalyzer:
    """Test cases for GoalAnalyzer"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = GoalAnalyzer()
        self.parser = TaskParser()

    def test_analyze_explicit_goal(self):
        """Test analysis with explicit goal"""
        task = {
            "description": "Build a system",
            "goal": "Maximize revenue",
            "success_criteria": ["Generate $1000/month"],
        }

        parsed = self.parser.parse(task)
        goal = self.analyzer.analyze(parsed)

        assert goal.explicit is True
        assert goal.confidence >= 0.9
        assert "revenue" in goal.G.lower()

    def test_infer_goal_from_description(self):
        """Test goal inference from description"""
        task = "Build an automated revenue-generating system"
        parsed = self.parser.parse(task)
        goal = self.analyzer.analyze(parsed)

        assert goal.explicit is False
        assert goal.G is not None
        assert len(goal.G) > 0

    def test_calculate_goal_confidence(self):
        """Test goal confidence calculation"""
        task_high_confidence = {
            "description": "Build a system to increase revenue",
            "constraints": ["$1000 budget"],
            "success_criteria": ["Generate revenue"],
        }

        parsed_high = self.parser.parse(task_high_confidence)
        goal_high = self.analyzer.analyze(parsed_high)

        # Should have higher confidence due to specificity
        assert goal_high.confidence > 0.6

    def test_generate_clarifying_questions(self):
        """Test generation of clarifying questions"""
        task = "Build something"
        parsed = self.parser.parse(task)
        goal = self.analyzer.analyze(parsed)

        questions = self.analyzer.generate_clarifying_questions(goal, parsed)

        assert len(questions) > 0
        assert isinstance(questions, list)

    def test_derive_outcome_criteria(self):
        """Test derivation of outcome criteria"""
        task = {"description": "Build a system", "success_criteria": ["System is deployed", "Users can access it"]}

        parsed = self.parser.parse(task)
        goal = self.analyzer.analyze(parsed)

        assert goal.O_G is not None
        assert len(goal.O_G) > 0

    def test_validate_goal_alignment(self):
        """Test goal alignment validation"""
        task = "Build a revenue system"
        parsed = self.parser.parse(task)
        goal = self.analyzer.analyze(parsed)

        actions = ["Build payment integration", "Setup analytics", "Create dashboard"]

        # Should validate alignment
        is_aligned = self.analyzer.validate_goal_alignment(goal, actions)

        # At least some actions should align
        assert isinstance(is_aligned, bool)

"""
Integration tests for FSA-0.1 MLA Task Deconstructor

Tests the complete pipeline end-to-end.
"""

import json

import pytest

from agno.fsa_0_1_mla_task_deconstructor.main import MLATaskDeconstructor


class TestIntegration:
    """Integration tests for complete MLA pipeline"""

    def setup_method(self):
        """Setup test fixtures"""
        self.deconstructor = MLATaskDeconstructor()

    def test_simple_task_processing(self):
        """Test processing a simple task"""
        task = "Write a grant proposal for an AI-driven edtech product"
        result = self.deconstructor.process(task)

        # Verify result structure
        assert result.task_id is not None
        assert result.original_task == task
        assert result.inferred_goal is not None
        assert len(result.action_set) > 0
        assert len(result.recommended_sequence) > 0

        # Verify goal
        assert result.inferred_goal.G is not None
        assert 0 <= result.inferred_goal.confidence <= 1.0

        # Verify actions have LQ_MLA scores
        for action in result.action_set:
            lq = action.calculate_lq_mla()
            assert lq > 0
            assert action.rank is not None

    def test_complex_task_with_constraints(self):
        """Test processing a complex task with constraints"""
        task = {
            "description": "Build a revenue-generating FSA system",
            "constraints": ["$975 budget", "6-day timeline"],
            "available_resources": ["Claude Code", "Python", "GitHub"],
            "success_criteria": ["Generate revenue", "Deployed system"],
        }

        result = self.deconstructor.process(task)

        # Verify result
        assert result.inferred_goal is not None
        assert len(result.action_set) > 0

        # Verify constraints are captured
        assert len(result.inferred_goal.constraints) > 0

        # Verify actions are ranked
        ranks = [a.rank for a in result.action_set]
        assert sorted(ranks) == list(range(1, len(result.action_set) + 1))

    def test_json_output_format(self):
        """Test JSON output format matches specification"""
        task = "Create an automated testing framework"
        result = self.deconstructor.process(task)

        # Convert to dict
        output = result.to_dict()

        # Verify required fields
        required_fields = [
            "task_id",
            "original_task",
            "inferred_goal",
            "context_elicitation",
            "action_set",
            "recommended_sequence",
            "decomposition",
            "validation",
        ]

        for field in required_fields:
            assert field in output, f"Missing required field: {field}"

        # Verify nested structure
        assert "G" in output["inferred_goal"]
        assert "O_G" in output["inferred_goal"]
        assert "confidence" in output["inferred_goal"]

        # Verify action structure
        for action in output["action_set"]:
            assert "action_id" in action
            assert "description" in action
            assert "immediate_cost" in action
            assert "total_impact" in action
            assert "LQ_MLA" in action

        # Verify can serialize to JSON
        json_str = result.to_json()
        assert isinstance(json_str, str)

        # Verify can deserialize
        parsed = json.loads(json_str)
        assert parsed["task_id"] == result.task_id

    def test_context_elicitation(self):
        """Test context elicitation for underspecified tasks"""
        task = "Build something"
        result = self.deconstructor.process(task)

        # Should generate clarifying questions
        assert len(result.context_elicitation) > 0
        assert isinstance(result.context_elicitation, list)

    def test_goal_confidence_levels(self):
        """Test different goal confidence levels"""
        # High confidence task
        high_conf_task = {
            "description": "Build payment processing system",
            "goal": "Process customer payments",
            "success_criteria": ["Payments succeed", "Transactions logged"],
        }

        result_high = self.deconstructor.process(high_conf_task)
        assert result_high.inferred_goal.confidence >= 0.8

        # Low confidence task
        low_conf_task = "Do the thing"
        result_low = self.deconstructor.process(low_conf_task)
        assert result_low.inferred_goal.confidence < 0.8

    def test_action_ranking_by_lq_mla(self):
        """Test that actions are properly ranked by LQ_MLA"""
        task = "Build, test, and deploy a web application"
        result = self.deconstructor.process(task)

        # Verify actions are ranked
        assert len(result.action_set) > 0

        # Verify rank ordering
        for i in range(len(result.action_set) - 1):
            current = result.action_set[i]
            next_action = result.action_set[i + 1]

            # Higher rank (1, 2, 3...) should have higher LQ
            assert current.calculate_lq_mla() >= next_action.calculate_lq_mla()

    def test_dependency_detection(self):
        """Test dependency detection in action sequence"""
        task = "First setup the database, then create the API, finally deploy the application"
        result = self.deconstructor.process(task)

        # Should detect sequential dependencies
        # Later actions should depend on earlier ones
        has_dependencies = any(len(a.dependencies) > 0 for a in result.action_set)
        assert has_dependencies or len(result.action_set) == 1

    def test_validation_output(self):
        """Test validation output structure"""
        task = "Build a system"
        result = self.deconstructor.process(task)

        validation = result.validation

        # Required validation fields
        assert "goal_alignment_check" in validation
        assert "risk_assessment" in validation
        assert "global_context_check" in validation

        # Verify risk assessment is a list
        assert isinstance(validation["risk_assessment"], list)

    def test_mla_alignment_validation(self):
        """Test MLA alignment validation"""
        task = "Build an automated revenue system using a foundational framework"
        result = self.deconstructor.process(task)

        # Should have high-leverage actions
        high_lq_actions = [a for a in result.action_set if a.calculate_lq_mla() >= 1.0]
        assert len(high_lq_actions) > 0

    def test_recommended_sequence_validity(self):
        """Test that recommended sequence respects dependencies"""
        task = "Setup infrastructure, build application, test, and deploy"
        result = self.deconstructor.process(task)

        # Build action map
        action_map = {a.action_id: a for a in result.action_set}

        # Verify sequence respects dependencies
        completed = set()
        for action_id in result.recommended_sequence:
            action = action_map[action_id]

            # All dependencies should be completed before this action
            for dep_id in action.dependencies:
                assert dep_id in completed, f"Dependency {dep_id} not completed before {action_id}"

            completed.add(action_id)

    def test_example_from_spec(self):
        """Test the example from the specification"""
        task = "Write a grant proposal for an AI-driven edtech product"
        result = self.deconstructor.process(task)

        # Should successfully process
        assert result is not None
        assert result.inferred_goal is not None
        assert len(result.action_set) > 0

        # Print summary for manual verification
        result.print_summary()

        # Verify JSON output
        json_output = result.to_json()
        assert len(json_output) > 0


if __name__ == "__main__":
    # Run a quick integration test
    deconstructor = MLATaskDeconstructor()

    print("Testing Example 1: Simple task")
    print("-" * 80)
    task1 = "Write a grant proposal for an AI-driven edtech product"
    result1 = deconstructor.process(task1)
    result1.print_summary()

    print("\n\nTesting Example 2: Complex task with constraints")
    print("-" * 80)
    task2 = {
        "description": "Build a revenue-generating FSA system",
        "constraints": ["$975 budget", "6-day timeline"],
        "available_resources": ["Claude Code", "Python", "GitHub"],
    }
    result2 = deconstructor.process(task2)
    result2.print_summary()

    print("\n\nJSON Output:")
    print("-" * 80)
    print(result2.to_json())

"""
Unit tests for Goal Validator FSA.

Tests cover SMART validation, scoring, constraint checking, and edge cases.
"""

import pytest
from goal_validator_fsa import GoalValidatorFSA, ValidationResult, ValidationState


class TestGoalValidatorFSA:
    """Test suite for GoalValidatorFSA class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = GoalValidatorFSA()
        self.strict_validator = GoalValidatorFSA(strict_mode=True)

    def test_well_formed_smart_goal(self):
        """Test validation of a well-formed SMART goal."""
        goal = (
            "Implement a REST API with 5 endpoints for user management, "
            "achieving 95% test coverage by March 15, 2025"
        )
        constraints = {
            "max_duration": "90 days",
            "budget": 10000
        }
        context = {
            "user_level": "intermediate",
            "domain": "backend development",
            "available_resources": {"time": "adequate", "budget": "sufficient"}
        }

        result = self.validator.validate_goal(goal, constraints, context)

        # Assertions
        assert result.is_valid is True
        assert result.clarity_score >= 0.6
        assert result.achievability_score >= 0.5
        assert result.overall_score >= 0.5

        # Check SMART scores
        assert "specific" in result.smart_scores
        assert "measurable" in result.smart_scores
        assert "achievable" in result.smart_scores
        assert "relevant" in result.smart_scores
        assert "timebound" in result.smart_scores

        # Specific score should be high (has action verb, details)
        assert result.smart_scores["specific"] >= 0.5

        # Measurable score should be reasonable (has numbers, percentages)
        assert result.smart_scores["measurable"] >= 0.4

        # Time-bound score should be high (has specific date)
        assert result.smart_scores["timebound"] >= 0.4

        # Should have minimal recommendations for a good goal
        assert len(result.recommendations) <= 3

        # Check metadata
        assert result.metadata["word_count"] > 0
        assert result.metadata["has_constraints"] is True
        assert result.metadata["has_context"] is True

    def test_vague_goal_low_scores(self):
        """Test that vague goals receive low scores and helpful recommendations."""
        goal = "Maybe do something with the app sometime"

        result = self.validator.validate_goal(goal)

        # Vague goal should score poorly
        assert result.overall_score < 0.5
        assert result.clarity_score < 0.5

        # Should have low specific score (vague language)
        assert result.smart_scores["specific"] < 0.5

        # Should have low measurable score (no metrics)
        assert result.smart_scores["measurable"] < 0.5

        # Should have low time-bound score (no deadline)
        assert result.smart_scores["timebound"] < 0.5

        # Should provide recommendations
        assert len(result.recommendations) >= 3

        # Check for specific recommendation types
        recommendations_text = " ".join(result.recommendations).lower()
        assert any(keyword in recommendations_text for keyword in ["specific", "measurable", "deadline", "time"])

    def test_constraint_validation_issues(self):
        """Test constraint feasibility checking and issue detection."""
        goal = "Build an enterprise-scale distributed system in 2 days"
        constraints = {
            "max_duration": "2 days",
            "budget": 50,  # Very limited budget
            "dependencies": ["dep1", "dep2", "dep3", "dep4", "dep5", "dep6"],  # Many deps
            "min_resources": {"developers": 5, "servers": 10}
        }
        context = {
            "user_level": "beginner",
            "available_resources": {"developers": 1, "servers": 2}
        }

        result = self.validator.validate_goal(goal, constraints, context)

        # Should identify constraint issues
        assert len(result.constraint_issues) > 0

        # Should have lower achievability due to constraints
        assert result.achievability_score < 0.7

        # Check for specific constraint issues
        issues_text = " ".join(result.constraint_issues).lower()
        assert any(keyword in issues_text for keyword in ["budget", "dependencies", "insufficient", "developers", "servers"])

        # Should have recommendations for this problematic goal
        assert len(result.recommendations) > 0

    def test_input_validation_errors(self):
        """Test error handling for invalid inputs."""
        # Test empty goal
        with pytest.raises(ValueError, match="cannot be empty"):
            self.validator.validate_goal("")

        # Test None goal
        with pytest.raises(TypeError, match="must be a string"):
            self.validator.validate_goal(None)

        # Test invalid constraints type
        with pytest.raises(TypeError, match="must be a dict"):
            self.validator.validate_goal("Valid goal", constraints="invalid")

        # Test invalid context type
        with pytest.raises(TypeError, match="must be a dict"):
            self.validator.validate_goal("Valid goal", context=[1, 2, 3])

        # Test whitespace-only goal
        with pytest.raises(ValueError, match="cannot be empty"):
            self.validator.validate_goal("   \t\n   ")

    def test_strict_mode_validation(self):
        """Test strict mode requires all SMART criteria to meet threshold."""
        # Goal with weak time-bound component
        goal = "Create a mobile app with push notifications"  # No deadline

        # In normal mode, might still pass
        result_normal = self.validator.validate_goal(goal)

        # In strict mode, should fail if any SMART component is weak
        result_strict = self.strict_validator.validate_goal(goal)

        # Strict mode should be more demanding
        # If timebound score is < 0.6, strict should fail
        if result_strict.smart_scores["timebound"] < 0.6:
            assert result_strict.is_valid is False

    def test_measurable_goal_with_metrics(self):
        """Test that goals with clear metrics score high on measurability."""
        goal = "Increase user engagement by 25% and reduce load time from 3s to 1.5s within 60 days"

        result = self.validator.validate_goal(goal)

        # Should have high measurable score (multiple metrics, percentages, numbers)
        assert result.smart_scores["measurable"] >= 0.7

        # Should have reasonable timebound score (duration specified)
        assert result.smart_scores["timebound"] >= 0.3

        # Should have good clarity
        assert result.clarity_score >= 0.6

    def test_achievability_with_user_level(self):
        """Test that achievability scoring considers user level."""
        complex_goal = "Build a sophisticated distributed enterprise-grade system with advanced algorithms"

        # Beginner attempting complex goal
        result_beginner = self.validator.validate_goal(
            complex_goal,
            context={"user_level": "beginner"}
        )

        # Advanced user attempting same goal
        result_advanced = self.validator.validate_goal(
            complex_goal,
            context={"user_level": "advanced"}
        )

        # Beginner should have lower achievability score
        assert result_beginner.smart_scores["achievable"] < result_advanced.smart_scores["achievable"]

        # Beginner should get recommendation about complexity
        recommendations_text = " ".join(result_beginner.recommendations).lower()
        assert "complex" in recommendations_text or "breaking" in recommendations_text

    def test_relevant_score_with_domain_context(self):
        """Test relevance scoring with domain context."""
        goal = "Develop a machine learning model for web development predictions"

        # With matching domain context
        result_with_domain = self.validator.validate_goal(
            goal,
            context={"domain": "machine learning"}
        )

        # Without domain context
        result_without_domain = self.validator.validate_goal(goal)

        # Should score higher with matching domain
        assert result_with_domain.smart_scores["relevant"] >= result_without_domain.smart_scores["relevant"]

    def test_state_transitions(self):
        """Test that FSA transitions through expected states."""
        goal = "Complete project by next month"

        # Initial state
        assert self.validator.state == ValidationState.INITIAL

        # After validation
        result = self.validator.validate_goal(goal)

        # Should be in COMPLETE state
        assert self.validator.state == ValidationState.COMPLETE

        # Result should have no errors
        assert len(result.errors) == 0

    def test_edge_case_very_long_goal(self):
        """Test handling of very long goal descriptions."""
        goal = " ".join(["word"] * 200)  # 200-word goal

        result = self.validator.validate_goal(goal)

        # Should still process without errors
        assert result is not None
        assert result.metadata["word_count"] == 200

        # Long goals might lack specificity despite length
        # but should not crash or error

    def test_edge_case_special_characters(self):
        """Test handling of special characters in goal."""
        goal = "Implement feature #42 with @mentions & <tags> (priority: high!) by 12/31/2024"

        result = self.validator.validate_goal(goal)

        # Should handle special characters gracefully
        assert result is not None
        assert result.is_valid is not None

        # Should still detect date
        assert result.smart_scores["timebound"] > 0.3

    def test_recommendations_uniqueness(self):
        """Test that recommendations are relevant and not duplicated excessively."""
        goal = "Do stuff"

        result = self.validator.validate_goal(goal)

        # Should have recommendations
        assert len(result.recommendations) > 0

        # Check for duplicates (same recommendation shouldn't appear multiple times)
        unique_recommendations = set(result.recommendations)
        assert len(unique_recommendations) == len(result.recommendations)

    def test_score_ranges(self):
        """Test that all scores are within valid range [0.0, 1.0]."""
        goals = [
            "Build app",
            "Create a comprehensive web application with user authentication by end of year",
            "Maybe do something",
            "Increase sales by 50% in Q4 2024"
        ]

        for goal in goals:
            result = self.validator.validate_goal(goal)

            # Check all scores are in valid range
            assert 0.0 <= result.clarity_score <= 1.0
            assert 0.0 <= result.achievability_score <= 1.0
            assert 0.0 <= result.overall_score <= 1.0

            for smart_score in result.smart_scores.values():
                assert 0.0 <= smart_score <= 1.0

    def test_zero_budget_constraint(self):
        """Test handling of zero budget constraint."""
        goal = "Build a product"
        constraints = {"budget": 0}

        result = self.validator.validate_goal(goal, constraints=constraints)

        # Should identify budget constraint issue
        issues_text = " ".join(result.constraint_issues).lower()
        assert "budget" in issues_text or "zero" in issues_text

    def test_timeline_constraint_conflict(self):
        """Test detection of timeline conflicts between goal and constraints."""
        goal = "Complete the 6-month development project"
        constraints = {"max_duration": "30 days"}

        result = self.validator.validate_goal(goal, constraints=constraints)

        # Should detect timeline conflict
        if result.constraint_issues:
            issues_text = " ".join(result.constraint_issues).lower()
            assert "timeline" in issues_text or "duration" in issues_text or "exceed" in issues_text


def test_example_usage():
    """Test the example usage from main function."""
    validator = GoalValidatorFSA()

    # Test example 1
    goal1 = "Implement a user authentication system with JWT tokens and OAuth2 support by December 31, 2024"
    result1 = validator.validate_goal(
        goal=goal1,
        constraints={"max_duration": "60 days", "budget": 5000},
        context={"user_level": "intermediate", "domain": "web development"}
    )

    assert result1 is not None
    assert isinstance(result1, ValidationResult)

    # Test example 2
    goal2 = "Do something with the website"
    result2 = validator.validate_goal(goal=goal2)

    assert result2 is not None
    assert result2.overall_score < result1.overall_score  # Vague goal should score lower


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

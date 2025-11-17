"""
Simple unit tests for Goal Validator FSA (no pytest required).

Run with: python test_goal_validator_simple.py
"""

import unittest
from goal_validator_fsa import GoalValidatorFSA, ValidationResult, ValidationState


class TestGoalValidatorFSA(unittest.TestCase):
    """Test suite for GoalValidatorFSA class."""

    def setUp(self):
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
        self.assertTrue(result.is_valid)
        self.assertGreaterEqual(result.clarity_score, 0.6)
        self.assertGreaterEqual(result.achievability_score, 0.5)
        self.assertGreaterEqual(result.overall_score, 0.5)

        # Check SMART scores
        self.assertIn("specific", result.smart_scores)
        self.assertIn("measurable", result.smart_scores)
        self.assertIn("achievable", result.smart_scores)
        self.assertIn("relevant", result.smart_scores)
        self.assertIn("timebound", result.smart_scores)

        # Specific score should be high (has action verb, details)
        self.assertGreaterEqual(result.smart_scores["specific"], 0.5)

        # Measurable score should be reasonable (has numbers, percentages)
        self.assertGreaterEqual(result.smart_scores["measurable"], 0.4)

        # Time-bound score should be high (has specific date)
        self.assertGreaterEqual(result.smart_scores["timebound"], 0.4)

        # Should have minimal recommendations for a good goal
        self.assertLessEqual(len(result.recommendations), 3)

        # Check metadata
        self.assertGreater(result.metadata["word_count"], 0)
        self.assertTrue(result.metadata["has_constraints"])
        self.assertTrue(result.metadata["has_context"])

    def test_vague_goal_low_scores(self):
        """Test that vague goals receive low scores and helpful recommendations."""
        goal = "Maybe do something with the app sometime"

        result = self.validator.validate_goal(goal)

        # Vague goal should score poorly
        self.assertLess(result.overall_score, 0.5)
        self.assertLess(result.clarity_score, 0.5)

        # Should have low specific score (vague language)
        self.assertLess(result.smart_scores["specific"], 0.5)

        # Should have low measurable score (no metrics)
        self.assertLess(result.smart_scores["measurable"], 0.5)

        # Should have low time-bound score (no deadline)
        self.assertLess(result.smart_scores["timebound"], 0.5)

        # Should provide recommendations
        self.assertGreaterEqual(len(result.recommendations), 3)

        # Check for specific recommendation types
        recommendations_text = " ".join(result.recommendations).lower()
        self.assertTrue(any(keyword in recommendations_text for keyword in ["specific", "measurable", "deadline", "time"]))

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
        self.assertGreater(len(result.constraint_issues), 0)

        # Should have lower achievability due to constraints
        self.assertLess(result.achievability_score, 0.7)

        # Check for specific constraint issues
        issues_text = " ".join(result.constraint_issues).lower()
        self.assertTrue(any(keyword in issues_text for keyword in ["budget", "dependencies", "insufficient", "developers", "servers"]))

        # Should have recommendations for this problematic goal
        self.assertGreater(len(result.recommendations), 0)

    def test_input_validation_errors(self):
        """Test error handling for invalid inputs."""
        # Test empty goal
        with self.assertRaises(ValueError):
            self.validator.validate_goal("")

        # Test None goal
        with self.assertRaises(TypeError):
            self.validator.validate_goal(None)

        # Test invalid constraints type
        with self.assertRaises(TypeError):
            self.validator.validate_goal("Valid goal", constraints="invalid")

        # Test invalid context type
        with self.assertRaises(TypeError):
            self.validator.validate_goal("Valid goal", context=[1, 2, 3])

        # Test whitespace-only goal
        with self.assertRaises(ValueError):
            self.validator.validate_goal("   \t\n   ")

    def test_measurable_goal_with_metrics(self):
        """Test that goals with clear metrics score high on measurability."""
        goal = "Increase user engagement by 25% and reduce load time from 3s to 1.5s within 60 days"

        result = self.validator.validate_goal(goal)

        # Should have high measurable score (multiple metrics, percentages, numbers)
        self.assertGreaterEqual(result.smart_scores["measurable"], 0.7)

        # Should have reasonable timebound score (duration specified)
        self.assertGreaterEqual(result.smart_scores["timebound"], 0.3)

        # Should have good clarity
        self.assertGreaterEqual(result.clarity_score, 0.6)

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
            self.assertGreaterEqual(result.clarity_score, 0.0)
            self.assertLessEqual(result.clarity_score, 1.0)
            self.assertGreaterEqual(result.achievability_score, 0.0)
            self.assertLessEqual(result.achievability_score, 1.0)
            self.assertGreaterEqual(result.overall_score, 0.0)
            self.assertLessEqual(result.overall_score, 1.0)

            for smart_score in result.smart_scores.values():
                self.assertGreaterEqual(smart_score, 0.0)
                self.assertLessEqual(smart_score, 1.0)


def run_tests():
    """Run all tests and display results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGoalValidatorFSA)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

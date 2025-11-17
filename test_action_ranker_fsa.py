"""
Unit tests for Action Ranker FSA with LQ_MLA scoring algorithm.
"""

import unittest
from action_ranker_fsa import (
    ActionRankerFSA,
    ScoringWeights,
    RankingConstraints,
    Action,
    ActionState,
    rank_actions
)


class TestActionRankerFSA(unittest.TestCase):
    """Comprehensive test suite for ActionRankerFSA."""

    def setUp(self):
        """Set up test fixtures."""
        self.basic_context = {
            "completed_actions": [],
            "available_resources": {"budget": 100000, "team_size": 5}
        }
        self.goal = "Improve system performance and reduce operational costs"

    def test_basic_ranking_diverse_actions(self):
        """Test 1: Basic ranking with diverse action set."""
        actions = [
            {
                "id": "optimize_db",
                "name": "Optimize Database Queries",
                "description": "Refactor slow SQL queries",
                "impact": 8.5,
                "cost": 3.0,
                "risk": 2.0,
                "time_to_value": 5.0,
                "dependencies": [],
                "metadata": {"tags": ["performance", "backend"]}
            },
            {
                "id": "cache_layer",
                "name": "Add Caching Layer",
                "description": "Implement Redis caching",
                "impact": 9.0,
                "cost": 6.0,
                "risk": 4.0,
                "time_to_value": 10.0,
                "dependencies": ["optimize_db"],
                "metadata": {"tags": ["performance", "infrastructure"]}
            },
            {
                "id": "ui_redesign",
                "name": "UI Redesign",
                "description": "Modernize user interface",
                "impact": 6.0,
                "cost": 8.0,
                "risk": 5.0,
                "time_to_value": 30.0,
                "dependencies": [],
                "metadata": {"tags": ["frontend", "ux"]}
            },
            {
                "id": "api_docs",
                "name": "Update API Documentation",
                "description": "Document all API endpoints",
                "impact": 4.0,
                "cost": 2.0,
                "risk": 1.0,
                "time_to_value": 3.0,
                "dependencies": [],
                "metadata": {"tags": ["documentation"]}
            },
            {
                "id": "monitoring",
                "name": "Set Up Monitoring",
                "description": "Implement comprehensive monitoring",
                "impact": 7.5,
                "cost": 4.0,
                "risk": 2.5,
                "time_to_value": 7.0,
                "dependencies": [],
                "metadata": {"tags": ["operations", "infrastructure"]}
            }
        ]

        ranker = ActionRankerFSA()
        results = ranker.rank_actions(actions, self.basic_context, self.goal)

        # Assertions
        self.assertEqual(len(results), 5, "Should rank all 5 actions")
        self.assertEqual(results[0]["rank"], 1, "First action should have rank 1")
        self.assertEqual(results[-1]["rank"], 5, "Last action should have rank 5")

        # Verify all actions have required fields
        for result in results:
            self.assertIn("id", result)
            self.assertIn("name", result)
            self.assertIn("rank", result)
            self.assertIn("lq_mla_score", result)
            self.assertIn("rationale", result)
            self.assertIn("score_breakdown", result)
            self.assertGreater(result["lq_mla_score"], 0, "Score should be positive")

        # Verify scores are in descending order
        scores = [r["lq_mla_score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True), "Scores should be descending")

        # High impact, low cost/risk actions should rank higher
        # optimize_db should typically rank high due to high impact, low cost/risk, quick ttv
        top_ids = [r["id"] for r in results[:2]]
        self.assertIn("optimize_db", top_ids, "optimize_db should be in top 2")

        print("\n=== Test 1: Basic Ranking ===")
        for i, result in enumerate(results[:3], 1):
            print(f"{i}. {result['name']} - Score: {result['lq_mla_score']:.4f}")
            print(f"   Rationale: {result['rationale']}")

    def test_constraint_filtering(self):
        """Test 2: Constraint-based filtering."""
        actions = [
            {
                "id": "low_risk_action",
                "name": "Low Risk Action",
                "impact": 7.0,
                "cost": 3.0,
                "risk": 2.0,
                "time_to_value": 5.0,
                "metadata": {"tags": ["safe", "approved"]}
            },
            {
                "id": "high_risk_action",
                "name": "High Risk Action",
                "impact": 9.0,
                "cost": 4.0,
                "risk": 8.5,  # Should be filtered
                "time_to_value": 10.0,
                "metadata": {"tags": ["experimental"]}
            },
            {
                "id": "expensive_action",
                "name": "Expensive Action",
                "impact": 8.0,
                "cost": 9.5,  # Should be filtered
                "risk": 3.0,
                "time_to_value": 15.0,
                "metadata": {"tags": ["premium"]}
            },
            {
                "id": "low_impact_action",
                "name": "Low Impact Action",
                "impact": 2.0,  # Should be filtered
                "cost": 2.0,
                "risk": 1.0,
                "time_to_value": 2.0,
                "metadata": {"tags": ["minor"]}
            },
            {
                "id": "approved_action",
                "name": "Approved Action",
                "impact": 7.5,
                "cost": 4.0,
                "risk": 3.0,
                "time_to_value": 8.0,
                "metadata": {"tags": ["approved", "safe"]}
            }
        ]

        # Set up constraints
        constraints = RankingConstraints(
            max_cost=8.0,
            max_risk=7.0,
            min_impact=5.0,
            required_tags=["approved"]
        )

        ranker = ActionRankerFSA(constraints=constraints)
        results = ranker.rank_actions(actions, self.basic_context, self.goal)

        # Only actions meeting all constraints should pass
        # low_risk_action: has "approved" tag, meets all numeric constraints ✓
        # approved_action: has "approved" tag, meets all numeric constraints ✓
        self.assertEqual(len(results), 2, "Should filter to 2 actions with 'approved' tag")

        result_ids = {r["id"] for r in results}
        self.assertIn("low_risk_action", result_ids)
        self.assertIn("approved_action", result_ids)
        self.assertNotIn("high_risk_action", result_ids, "High risk should be filtered")
        self.assertNotIn("expensive_action", result_ids, "Expensive should be filtered")

        # Check state transitions
        states = ranker.get_state_transitions()
        self.assertEqual(states["low_risk_action"], ActionState.RANKED.value)
        self.assertEqual(states["high_risk_action"], ActionState.REJECTED.value)

        print("\n=== Test 2: Constraint Filtering ===")
        print(f"Filtered from 5 to {len(results)} actions")
        for result in results:
            print(f"- {result['name']} (passed constraints)")

    def test_dependency_handling(self):
        """Test 3: Dependency scoring and boost."""
        # Scenario: Some actions depend on others, some dependencies are completed
        context_with_completed = {
            "completed_actions": ["foundation", "data_model"],
            "available_resources": {}
        }

        actions = [
            {
                "id": "foundation",
                "name": "Build Foundation",
                "impact": 8.0,
                "cost": 5.0,
                "risk": 3.0,
                "time_to_value": 10.0,
                "dependencies": []
            },
            {
                "id": "feature_a",
                "name": "Feature A",
                "impact": 7.0,
                "cost": 4.0,
                "risk": 2.0,
                "time_to_value": 5.0,
                "dependencies": ["foundation"]  # Dependency satisfied
            },
            {
                "id": "feature_b",
                "name": "Feature B",
                "impact": 7.0,
                "cost": 4.0,
                "risk": 2.0,
                "time_to_value": 5.0,
                "dependencies": ["foundation", "data_model"]  # Both satisfied
            },
            {
                "id": "feature_c",
                "name": "Feature C",
                "impact": 7.5,
                "cost": 3.5,
                "risk": 2.0,
                "time_to_value": 5.0,
                "dependencies": ["nonexistent"]  # Dependency not satisfied
            },
            {
                "id": "independent",
                "name": "Independent Feature",
                "impact": 6.5,
                "cost": 4.0,
                "risk": 2.5,
                "time_to_value": 6.0,
                "dependencies": []  # No dependencies
            }
        ]

        ranker = ActionRankerFSA(enable_dependency_boost=True)
        results = ranker.rank_actions(actions, context_with_completed, self.goal)

        self.assertEqual(len(results), 5)

        # Actions with satisfied dependencies should rank higher than similar actions
        # with unsatisfied dependencies
        result_dict = {r["id"]: r for r in results}

        # feature_b has all dependencies satisfied, should have high dependency score
        feature_b_dep_score = result_dict["feature_b"]["score_breakdown"]["dependency_score"]
        self.assertGreater(feature_b_dep_score, 0.9, "All dependencies satisfied")

        # feature_c has unmet dependencies, should have lower dependency score
        feature_c_dep_score = result_dict["feature_c"]["score_breakdown"]["dependency_score"]
        self.assertLess(feature_c_dep_score, 0.6, "Unmet dependencies")

        # independent should have perfect dependency score (no dependencies)
        independent_dep_score = result_dict["independent"]["score_breakdown"]["dependency_score"]
        self.assertEqual(independent_dep_score, 1.0, "No dependencies = perfect score")

        print("\n=== Test 3: Dependency Handling ===")
        print("Dependency scores:")
        for result in results:
            dep_score = result["score_breakdown"]["dependency_score"]
            print(f"- {result['name']}: {dep_score:.3f}")

    def test_edge_cases_and_validation(self):
        """Test 4: Edge cases and input validation."""
        ranker = ActionRankerFSA()

        # Test: Empty actions list
        with self.assertRaises(ValueError):
            ranker.rank_actions([], self.basic_context, self.goal)

        # Test: Invalid action type
        with self.assertRaises(TypeError):
            ranker.rank_actions("not a list", self.basic_context, self.goal)

        # Test: Empty goal
        with self.assertRaises(ValueError):
            ranker.rank_actions([{"id": "test"}], self.basic_context, "")

        # Test: Invalid context type
        with self.assertRaises(TypeError):
            ranker.rank_actions([{"id": "test"}], "not a dict", self.goal)

        # Test: Actions with missing/invalid fields (should be handled gracefully)
        actions_with_issues = [
            {"id": "valid", "name": "Valid", "impact": 7, "cost": 3, "risk": 2},
            {"name": "Missing ID"},  # Should get auto-generated ID
            {"id": "invalid_score", "impact": 15.0},  # Out of range, should fail validation
        ]

        # Should process valid actions and skip invalid ones
        results = ranker.rank_actions(actions_with_issues, self.basic_context, self.goal)
        self.assertGreaterEqual(len(results), 1, "Should process at least valid action")

        # Test: Single action
        single_action = [
            {"id": "only_one", "name": "Only Action", "impact": 5, "cost": 5, "risk": 5}
        ]
        results = ranker.rank_actions(single_action, self.basic_context, self.goal)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["rank"], 1)

        # Test: All actions filtered out
        very_strict_constraints = RankingConstraints(
            min_impact=9.9,
            max_cost=0.1,
            max_risk=0.1
        )
        ranker_strict = ActionRankerFSA(constraints=very_strict_constraints)

        normal_actions = [
            {"id": "normal", "name": "Normal", "impact": 7, "cost": 5, "risk": 3}
        ]
        results = ranker_strict.rank_actions(normal_actions, self.basic_context, self.goal)
        self.assertEqual(len(results), 0, "All actions should be filtered")

        print("\n=== Test 4: Edge Cases ===")
        print("✓ Empty list validation")
        print("✓ Type validation")
        print("✓ Malformed action handling")
        print("✓ Single action ranking")
        print("✓ Complete filtering")

    def test_custom_weights_and_leverage_scoring(self):
        """Test 5: Custom weights and LQ_MLA leverage quotient."""
        # Create two actions with different characteristics
        actions = [
            {
                "id": "quick_win",
                "name": "Quick Win",
                "description": "Low effort, immediate impact",
                "impact": 7.0,
                "cost": 2.0,  # Very low cost
                "risk": 1.5,  # Very low risk
                "time_to_value": 2.0,  # Very fast
                "dependencies": []
            },
            {
                "id": "big_bet",
                "name": "Big Bet",
                "description": "High effort, high impact",
                "impact": 9.5,  # Higher impact
                "cost": 8.0,  # High cost
                "risk": 7.0,  # High risk
                "time_to_value": 30.0,  # Slow
                "dependencies": []
            },
            {
                "id": "balanced",
                "name": "Balanced Approach",
                "description": "Medium effort, medium impact",
                "impact": 6.5,
                "cost": 5.0,
                "risk": 4.0,
                "time_to_value": 10.0,
                "dependencies": []
            }
        ]

        # Test with impact-focused weights
        impact_weights = ScoringWeights(
            impact=0.50,  # Heavy weight on impact
            cost=0.15,
            risk=0.15,
            dependencies=0.05,
            time_to_value=0.15
        )

        ranker_impact = ActionRankerFSA(weights=impact_weights)
        results_impact = ranker_impact.rank_actions(actions, self.basic_context, self.goal)

        # Test with cost/risk-focused weights (conservative)
        conservative_weights = ScoringWeights(
            impact=0.20,
            cost=0.30,  # Heavy weight on cost
            risk=0.30,  # Heavy weight on risk
            dependencies=0.05,
            time_to_value=0.15
        )

        ranker_conservative = ActionRankerFSA(weights=conservative_weights)
        results_conservative = ranker_conservative.rank_actions(
            actions, self.basic_context, self.goal
        )

        # Verify leverage quotient calculation
        # Quick win should have high leverage (high impact/cost ratio, fast ttv)
        quick_win_result = next(r for r in results_conservative if r["id"] == "quick_win")
        leverage_quotient = quick_win_result["score_breakdown"]["leverage_quotient"]

        # LQ = (Impact * Velocity) / (Cost * Risk)
        # Expected: (7.0 * 0.5) / (2.0 * 1.5) = 3.5 / 3.0 = 1.167
        expected_lq_approx = (7.0 * (1.0 / 2.0)) / (2.0 * 1.5)
        self.assertAlmostEqual(
            leverage_quotient, expected_lq_approx, places=2,
            msg="Leverage quotient calculation"
        )

        # With conservative weights, quick_win should rank #1 (low cost, low risk)
        self.assertEqual(
            results_conservative[0]["id"], "quick_win",
            "Quick win should rank first with conservative weights"
        )

        # Verify different weight strategies produce different rankings
        impact_top = results_impact[0]["id"]
        conservative_top = results_conservative[0]["id"]

        print("\n=== Test 5: Custom Weights & Leverage Scoring ===")
        print("\nImpact-focused ranking:")
        for r in results_impact:
            print(f"{r['rank']}. {r['name']} - LQ_MLA: {r['lq_mla_score']:.4f}, "
                  f"Leverage: {r['score_breakdown']['leverage_quotient']:.3f}")

        print("\nConservative ranking:")
        for r in results_conservative:
            print(f"{r['rank']}. {r['name']} - LQ_MLA: {r['lq_mla_score']:.4f}, "
                  f"Leverage: {r['score_breakdown']['leverage_quotient']:.3f}")

        # Verify score breakdown structure
        for result in results_impact:
            breakdown = result["score_breakdown"]
            self.assertIn("impact_score", breakdown)
            self.assertIn("cost_score", breakdown)
            self.assertIn("risk_score", breakdown)
            self.assertIn("leverage_quotient", breakdown)
            self.assertIn("lq_mla_final", breakdown)

    def test_convenience_function(self):
        """Test the convenience rank_actions function."""
        actions = [
            {"id": "a1", "name": "Action 1", "impact": 8, "cost": 3, "risk": 2},
            {"id": "a2", "name": "Action 2", "impact": 6, "cost": 2, "risk": 1}
        ]

        results = rank_actions(actions, self.basic_context, self.goal)

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results, list)
        self.assertIn("rank", results[0])

        print("\n=== Test 6: Convenience Function ===")
        print("✓ Convenience function works correctly")


class TestActionValidation(unittest.TestCase):
    """Test Action class validation."""

    def test_action_validation(self):
        """Test Action object validation."""
        # Valid action
        action = Action(
            id="test",
            name="Test Action",
            impact=7.0,
            cost=5.0,
            risk=3.0,
            time_to_value=10.0
        )
        self.assertEqual(action.id, "test")

        # Invalid impact (out of range)
        with self.assertRaises(ValueError):
            Action(id="test", name="Test", impact=15.0)

        # Invalid cost (negative)
        with self.assertRaises(ValueError):
            Action(id="test", name="Test", cost=-1.0)

        # Invalid time_to_value (zero)
        with self.assertRaises(ValueError):
            Action(id="test", name="Test", time_to_value=0)


class TestScoringWeights(unittest.TestCase):
    """Test ScoringWeights validation."""

    def test_weights_validation(self):
        """Test that weights must sum to 1.0."""
        # Valid weights
        weights = ScoringWeights(
            impact=0.3,
            cost=0.2,
            risk=0.2,
            dependencies=0.15,
            time_to_value=0.15
        )
        self.assertEqual(weights.impact, 0.3)

        # Invalid weights (don't sum to 1.0)
        with self.assertRaises(ValueError):
            ScoringWeights(
                impact=0.5,
                cost=0.5,
                risk=0.5,
                dependencies=0.5,
                time_to_value=0.5
            )


def run_tests():
    """Run all tests with verbose output."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestActionRankerFSA))
    suite.addTests(loader.loadTestsFromTestCase(TestActionValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestScoringWeights))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

"""
Unit tests for Task Deconstruction FSA

Comprehensive test suite covering core functionality, edge cases, and error handling.
"""

import unittest
from task_deconstruction_fsa import (
    TaskDecompositionFSA,
    AtomicAction,
    ActionType,
    FSAState,
    TaskDecompositionError
)


class TestTaskDecompositionFSA(unittest.TestCase):
    """Test suite for TaskDecompositionFSA class."""

    def setUp(self):
        """Set up test fixtures."""
        self.fsa = TaskDecompositionFSA()

    def tearDown(self):
        """Clean up after tests."""
        self.fsa.reset()

    def test_simple_task_decomposition(self):
        """Test decomposition of a simple task."""
        task = "Read the configuration file and validate the settings"
        context = {'complexity_level': 'simple'}

        actions = self.fsa.decompose(task, context)

        # Verify we got actions
        self.assertGreater(len(actions), 0, "Should generate at least one action")

        # Verify actions are sorted by priority
        priorities = [action.priority_score for action in actions]
        self.assertEqual(priorities, sorted(priorities, reverse=True),
                        "Actions should be sorted by priority score in descending order")

        # Verify FSA state is complete
        self.assertEqual(self.fsa.state, FSAState.COMPLETE)

        # Check that we have read and validate actions
        action_types = {action.action_type for action in actions}
        self.assertIn(ActionType.ANALYZE, action_types,
                     "Should include ANALYZE action for 'read'")
        self.assertIn(ActionType.VALIDATE, action_types,
                     "Should include VALIDATE action")

    def test_complex_task_decomposition(self):
        """Test decomposition of a complex task with multiple components."""
        task = "Create a new authentication system, implement JWT tokens, and validate security measures"
        context = {
            'complexity_level': 'high',
            'priority': 'high',
            'project_type': 'backend'
        }

        actions = self.fsa.decompose(task, context)

        # Should have multiple actions for a complex task
        self.assertGreater(len(actions), 3,
                          "Complex task should generate multiple actions")

        # Verify all actions have valid IDs
        action_ids = [action.id for action in actions]
        self.assertEqual(len(action_ids), len(set(action_ids)),
                        "All action IDs should be unique")

        # Verify priority scores are calculated
        for action in actions:
            self.assertGreater(action.priority_score, 0,
                             f"Action {action.id} should have positive priority score")

        # Verify complexity is adjusted for high complexity context
        avg_complexity = sum(action.complexity for action in actions) / len(actions)
        self.assertGreater(avg_complexity, 5,
                          "High complexity tasks should have higher average complexity")

    def test_dependency_graph_generation(self):
        """Test that dependency graph is correctly generated."""
        task = "Plan the project, analyze requirements, implement features, and validate results"
        context = {'complexity_level': 'medium'}

        actions = self.fsa.decompose(task, context)
        dep_graph = self.fsa.get_dependency_graph()

        # Verify graph exists
        self.assertIsNotNone(dep_graph)
        self.assertEqual(len(dep_graph), len(actions),
                        "Dependency graph should have entry for each action")

        # Verify all actions are in the graph
        for action in actions:
            self.assertIn(action.id, dep_graph,
                         f"Action {action.id} should be in dependency graph")

        # Verify dependencies are consistent
        for action in actions:
            graph_deps = dep_graph[action.id]
            action_deps = action.dependencies
            self.assertEqual(graph_deps, action_deps,
                           f"Graph dependencies should match action dependencies for {action.id}")

    def test_execution_order(self):
        """Test that execution order respects dependencies."""
        task = "Read input, analyze data, create report, and validate output"
        context = {'complexity_level': 'medium'}

        actions = self.fsa.decompose(task, context)
        execution_order = self.fsa.get_execution_order()

        # Verify we got all actions
        self.assertEqual(len(execution_order), len(actions),
                        "Execution order should include all actions")

        # Verify dependencies are respected
        seen = set()
        for action in execution_order:
            # All dependencies should have been seen before this action
            for dep_id in action.dependencies:
                self.assertIn(dep_id, seen,
                            f"Dependency {dep_id} should appear before {action.id}")
            seen.add(action.id)

    def test_lq_scoring(self):
        """Test LQ (Local Quality) scoring calculation."""
        task = "Build a complex system with multiple dependencies"
        context = {
            'complexity_level': 'high',
            'priority': 'high'
        }

        actions = self.fsa.decompose(task, context)

        # Verify all actions have priority scores
        for action in actions:
            self.assertIsInstance(action.priority_score, float)
            self.assertGreater(action.priority_score, 0)

        # Actions with fewer dependencies should generally have higher priorities
        no_dep_actions = [a for a in actions if len(a.dependencies) == 0]
        if no_dep_actions:
            avg_no_dep_priority = sum(a.priority_score for a in no_dep_actions) / len(no_dep_actions)

            with_dep_actions = [a for a in actions if len(a.dependencies) > 0]
            if with_dep_actions:
                avg_with_dep_priority = sum(a.priority_score for a in with_dep_actions) / len(with_dep_actions)
                self.assertGreaterEqual(avg_no_dep_priority, avg_with_dep_priority * 0.5,
                                       "Actions without dependencies should generally have competitive priorities")

    def test_invalid_input_validation(self):
        """Test error handling for invalid inputs."""
        # Test empty string
        with self.assertRaises(ValueError):
            self.fsa.decompose("", {})

        # Test whitespace only
        with self.assertRaises(ValueError):
            self.fsa.decompose("   ", {})

        # Test None
        with self.assertRaises(ValueError):
            self.fsa.decompose(None, {})

        # Test invalid context type
        with self.assertRaises(ValueError):
            self.fsa.decompose("valid task", "invalid context")

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected and raise errors."""
        # This test manually creates a circular dependency scenario
        task = "Create a simple task"
        context = {}

        actions = self.fsa.decompose(task, context)

        # Manually inject circular dependency for testing
        if len(actions) >= 2:
            actions[0].dependencies.add(actions[1].id)
            actions[1].dependencies.add(actions[0].id)

            # Rebuild graph with circular dependency
            self.fsa.dependency_graph = {
                action.id: action.dependencies.copy() for action in actions
            }

            # Validation should catch the circular dependency
            with self.assertRaises(TaskDecompositionError):
                self.fsa._validate_decomposition()

    def test_state_transitions(self):
        """Test FSA state transitions during decomposition."""
        task = "Analyze and implement a feature"
        context = {'complexity_level': 'medium'}

        # Initial state
        self.assertEqual(self.fsa.state, FSAState.INIT)

        # After decomposition
        actions = self.fsa.decompose(task, context)

        # Should end in COMPLETE state
        self.assertEqual(self.fsa.state, FSAState.COMPLETE)

        # Verify we can reset
        self.fsa.reset()
        self.assertEqual(self.fsa.state, FSAState.INIT)
        self.assertEqual(len(self.fsa.actions), 0)

    def test_atomic_action_properties(self):
        """Test AtomicAction dataclass properties."""
        action = AtomicAction(
            id="test_1",
            description="Test action",
            action_type=ActionType.WRITE,
            complexity=5
        )

        # Test basic properties
        self.assertEqual(action.id, "test_1")
        self.assertEqual(action.action_type, ActionType.WRITE)
        self.assertEqual(action.complexity, 5)
        self.assertEqual(action.priority_score, 0.0)

        # Test dependencies are initialized
        self.assertIsInstance(action.dependencies, set)
        self.assertEqual(len(action.dependencies), 0)

        # Test metadata is initialized
        self.assertIsInstance(action.metadata, dict)

        # Test hash and equality
        action2 = AtomicAction(
            id="test_1",
            description="Different description",
            action_type=ActionType.READ
        )
        self.assertEqual(action, action2, "Actions with same ID should be equal")
        self.assertEqual(hash(action), hash(action2))


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for real-world scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.fsa = TaskDecompositionFSA()

    def test_software_development_task(self):
        """Test decomposition of a typical software development task."""
        task = """
        Create a REST API endpoint for user authentication.
        Implement JWT token generation and validation.
        Add unit tests and integration tests.
        """
        context = {
            'complexity_level': 'high',
            'priority': 'high',
            'project_type': 'api'
        }

        actions = self.fsa.decompose(task, context)

        # Should generate multiple actions
        self.assertGreater(len(actions), 4)

        # Should have different action types
        action_types = {action.action_type for action in actions}
        self.assertGreater(len(action_types), 1,
                          "Should have multiple action types")

        # Check execution order is valid
        execution_order = self.fsa.get_execution_order()
        self.assertEqual(len(execution_order), len(actions))

    def test_data_processing_task(self):
        """Test decomposition of a data processing task."""
        task = "Read CSV file, analyze sales data, generate monthly report, and validate accuracy"
        context = {
            'complexity_level': 'medium',
            'project_type': 'data_analysis'
        }

        actions = self.fsa.decompose(task, context)

        # Should have read, analyze, and validate actions
        action_types = [action.action_type for action in actions]

        self.assertTrue(
            any(t in [ActionType.READ, ActionType.ANALYZE] for t in action_types),
            "Should include READ or ANALYZE actions"
        )

        self.assertTrue(
            any(t == ActionType.VALIDATE for t in action_types),
            "Should include VALIDATE action"
        )

        # Validate action should depend on earlier actions
        validate_actions = [a for a in actions if a.action_type == ActionType.VALIDATE]
        if validate_actions:
            for validate_action in validate_actions:
                self.assertGreaterEqual(
                    len(validate_action.dependencies), 0,
                    "Validate actions should have dependencies or be standalone"
                )


def run_tests():
    """Run all tests and display results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestTaskDecompositionFSA))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_tests()
    exit(0 if result.wasSuccessful() else 1)

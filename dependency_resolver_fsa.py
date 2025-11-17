"""
Dependency Resolver FSA - Manages action dependencies and builds dependency graphs.

This module implements a Finite State Automaton (FSA) for resolving dependencies
between actions/tasks, building directed acyclic graphs (DAG), and determining
optimal execution order with parallel execution opportunities.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class FSAState(Enum):
    """States of the Dependency Resolver FSA."""
    INITIAL = "initial"                    # Starting state
    VALIDATING = "validating"              # Validating dependencies
    BUILDING_GRAPH = "building_graph"      # Building dependency graph
    DETECTING_CYCLES = "detecting_cycles"  # Checking for circular dependencies
    SORTING = "sorting"                    # Performing topological sort
    COMPLETED = "completed"                # Successfully resolved
    ERROR = "error"                        # Error state


class DependencyError(Exception):
    """Base exception for dependency resolution errors."""
    pass


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""
    pass


class MissingDependencyError(DependencyError):
    """Raised when a required dependency is missing."""
    pass


class ConflictingDependencyError(DependencyError):
    """Raised when conflicting dependencies are detected."""
    pass


@dataclass
class Action:
    """Represents an action/task with dependencies.

    Attributes:
        id: Unique identifier for the action
        name: Human-readable name
        dependencies: List of action IDs this action depends on
        metadata: Additional metadata for the action
    """
    id: str
    name: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Action):
            return self.id == other.id
        return False


@dataclass
class DependencyWarning:
    """Represents a warning about dependencies.

    Attributes:
        action_id: The action ID with the warning
        message: Warning message
        severity: Warning severity (low, medium, high)
    """
    action_id: str
    message: str
    severity: str = "medium"


@dataclass
class ExecutionPlan:
    """Represents the resolved execution plan.

    Attributes:
        execution_order: List of action IDs in execution order
        parallel_groups: Groups of actions that can be executed in parallel
        warnings: List of dependency warnings
        errors: List of dependency errors
    """
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    warnings: List[DependencyWarning] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class DependencyResolverFSA:
    """
    Finite State Automaton for resolving action dependencies.

    This FSA manages the complete lifecycle of dependency resolution:
    1. Validates input actions and dependencies
    2. Builds a directed acyclic graph (DAG)
    3. Detects circular dependencies
    4. Performs topological sorting
    5. Identifies parallel execution opportunities

    Attributes:
        state: Current FSA state
        actions: Dictionary of actions by ID
        graph: Adjacency list representing dependency graph
        reverse_graph: Reverse adjacency list for inverse dependencies
        execution_plan: Resolved execution plan
    """

    def __init__(self):
        """Initialize the Dependency Resolver FSA."""
        self.state: FSAState = FSAState.INITIAL
        self.actions: Dict[str, Action] = {}
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.execution_plan: ExecutionPlan = ExecutionPlan()
        self._in_degree: Dict[str, int] = {}
        self._visited: Set[str] = set()
        self._rec_stack: Set[str] = set()

    def resolve(self, actions: List[Action]) -> ExecutionPlan:
        """
        Main entry point for dependency resolution.

        Args:
            actions: List of actions to resolve

        Returns:
            ExecutionPlan with resolved execution order and parallel groups

        Raises:
            DependencyError: If resolution fails
        """
        try:
            # Transition through FSA states
            self._transition_to(FSAState.VALIDATING)
            self._validate_actions(actions)

            self._transition_to(FSAState.BUILDING_GRAPH)
            self._build_graph()

            self._transition_to(FSAState.DETECTING_CYCLES)
            self._detect_cycles()

            self._transition_to(FSAState.SORTING)
            self._topological_sort()

            # Identify parallel execution opportunities
            self._identify_parallel_groups()

            self._transition_to(FSAState.COMPLETED)
            return self.execution_plan

        except DependencyError as e:
            self._transition_to(FSAState.ERROR)
            self.execution_plan.errors.append(str(e))
            raise

    def _transition_to(self, new_state: FSAState):
        """
        Transition to a new FSA state.

        Args:
            new_state: The state to transition to
        """
        # Define valid state transitions
        valid_transitions = {
            FSAState.INITIAL: [FSAState.VALIDATING],
            FSAState.VALIDATING: [FSAState.BUILDING_GRAPH, FSAState.ERROR],
            FSAState.BUILDING_GRAPH: [FSAState.DETECTING_CYCLES, FSAState.ERROR],
            FSAState.DETECTING_CYCLES: [FSAState.SORTING, FSAState.ERROR],
            FSAState.SORTING: [FSAState.COMPLETED, FSAState.ERROR],
            FSAState.COMPLETED: [],
            FSAState.ERROR: [],
        }

        if new_state not in valid_transitions.get(self.state, []):
            if new_state != FSAState.ERROR:  # Always allow transition to ERROR
                raise ValueError(
                    f"Invalid state transition from {self.state} to {new_state}"
                )

        self.state = new_state

    def _validate_actions(self, actions: List[Action]):
        """
        Validate actions and their dependencies.

        Performs validation checks:
        - No duplicate action IDs
        - All dependencies reference existing actions
        - No self-dependencies

        Args:
            actions: List of actions to validate

        Raises:
            MissingDependencyError: If a dependency is missing
            ConflictingDependencyError: If duplicate IDs or self-deps found
        """
        # Check for duplicate action IDs
        action_ids = [action.id for action in actions]
        if len(action_ids) != len(set(action_ids)):
            duplicates = [aid for aid in action_ids if action_ids.count(aid) > 1]
            raise ConflictingDependencyError(
                f"Duplicate action IDs found: {set(duplicates)}"
            )

        # Store actions by ID
        self.actions = {action.id: action for action in actions}

        # Validate each action's dependencies
        for action in actions:
            # Check for self-dependencies
            if action.id in action.dependencies:
                raise ConflictingDependencyError(
                    f"Action '{action.id}' depends on itself"
                )

            # Check that all dependencies exist
            for dep_id in action.dependencies:
                if dep_id not in self.actions:
                    raise MissingDependencyError(
                        f"Action '{action.id}' depends on non-existent action '{dep_id}'"
                    )

            # Add warning for actions with no dependencies (potential orphans)
            if not action.dependencies and len(actions) > 1:
                # Check if this action is a dependency of others
                is_dependency = any(
                    action.id in other.dependencies
                    for other in actions if other.id != action.id
                )
                if not is_dependency:
                    self.execution_plan.warnings.append(
                        DependencyWarning(
                            action_id=action.id,
                            message=f"Action '{action.id}' has no dependencies and is not a dependency of others",
                            severity="low"
                        )
                    )

    def _build_graph(self):
        """
        Build directed acyclic graph (DAG) from action dependencies.

        Creates:
        - graph: Adjacency list (action -> dependents)
        - reverse_graph: Reverse adjacency list (action -> dependencies)
        - in_degree: Count of incoming edges for each node
        """
        # Initialize in-degree counter
        self._in_degree = {action_id: 0 for action_id in self.actions}

        # Build graph and reverse graph
        for action_id, action in self.actions.items():
            # Initialize node in graph even if it has no dependents
            if action_id not in self.graph:
                self.graph[action_id] = []

            # For each dependency, create edge: dependency -> action
            for dep_id in action.dependencies:
                # dependency -> action (action depends on dependency)
                self.graph[dep_id].append(action_id)
                # Reverse: action -> dependency
                self.reverse_graph[action_id].append(dep_id)
                # Increment in-degree for action
                self._in_degree[action_id] += 1

    def _detect_cycles(self):
        """
        Detect circular dependencies using depth-first search (DFS).

        Uses a recursive DFS with a recursion stack to detect back edges,
        which indicate cycles in the dependency graph.

        Raises:
            CircularDependencyError: If a cycle is detected
        """
        self._visited = set()
        self._rec_stack = set()

        # Check each node for cycles
        for action_id in self.actions:
            if action_id not in self._visited:
                cycle_path = self._dfs_cycle_detection(action_id)
                if cycle_path:
                    raise CircularDependencyError(
                        f"Circular dependency detected: {' -> '.join(cycle_path)}"
                    )

    def _dfs_cycle_detection(self, node: str, path: Optional[List[str]] = None) -> Optional[List[str]]:
        """
        Perform DFS to detect cycles.

        Args:
            node: Current node being visited
            path: Current path being explored

        Returns:
            List of nodes forming a cycle, or None if no cycle found
        """
        if path is None:
            path = []

        # Mark node as visited and add to recursion stack
        self._visited.add(node)
        self._rec_stack.add(node)
        path.append(node)

        # Visit all neighbors
        for neighbor in self.graph.get(node, []):
            # If neighbor not visited, recurse
            if neighbor not in self._visited:
                cycle = self._dfs_cycle_detection(neighbor, path[:])
                if cycle:
                    return cycle
            # If neighbor in recursion stack, cycle detected
            elif neighbor in self._rec_stack:
                # Find the cycle in the path
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]

        # Remove from recursion stack (backtrack)
        self._rec_stack.remove(node)
        return None

    def _topological_sort(self):
        """
        Perform topological sort using Kahn's algorithm.

        Produces a linear ordering of actions such that for every directed
        edge (u, v), action u comes before action v in the ordering.

        The result is stored in self.execution_plan.execution_order.
        """
        # Create a copy of in-degree to avoid modifying the original
        in_degree = self._in_degree.copy()

        # Queue of nodes with no incoming edges
        queue = deque([
            action_id for action_id, degree in in_degree.items()
            if degree == 0
        ])

        execution_order = []

        while queue:
            # Remove node with no dependencies
            current = queue.popleft()
            execution_order.append(current)

            # Reduce in-degree for all dependent nodes
            for dependent in self.graph.get(current, []):
                in_degree[dependent] -= 1

                # If dependent now has no dependencies, add to queue
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we haven't processed all nodes, there's a cycle
        # (This should have been caught in cycle detection, but double-check)
        if len(execution_order) != len(self.actions):
            remaining = set(self.actions.keys()) - set(execution_order)
            raise CircularDependencyError(
                f"Unable to resolve dependencies for: {remaining}"
            )

        self.execution_plan.execution_order = execution_order

    def _identify_parallel_groups(self):
        """
        Identify groups of actions that can be executed in parallel.

        Actions can be executed in parallel if:
        1. They have the same depth in the dependency graph
        2. They don't depend on each other

        This uses a level-order traversal approach where each level
        represents actions that can be executed in parallel.
        """
        # Calculate depth (level) for each action
        depth = {action_id: 0 for action_id in self.actions}

        # Use topological order to calculate depths
        for action_id in self.execution_plan.execution_order:
            # Depth is 1 + max depth of all dependencies
            if self.reverse_graph[action_id]:
                depth[action_id] = 1 + max(
                    depth[dep_id] for dep_id in self.reverse_graph[action_id]
                )

        # Group actions by depth
        max_depth = max(depth.values()) if depth else 0
        parallel_groups = [[] for _ in range(max_depth + 1)]

        for action_id, d in depth.items():
            parallel_groups[d].append(action_id)

        # Filter out empty groups and store
        self.execution_plan.parallel_groups = [
            group for group in parallel_groups if group
        ]

    def get_dependencies(self, action_id: str) -> List[str]:
        """
        Get all dependencies for an action.

        Args:
            action_id: ID of the action

        Returns:
            List of action IDs that this action depends on
        """
        if action_id not in self.actions:
            raise ValueError(f"Action '{action_id}' not found")
        return self.reverse_graph.get(action_id, [])

    def get_dependents(self, action_id: str) -> List[str]:
        """
        Get all actions that depend on this action.

        Args:
            action_id: ID of the action

        Returns:
            List of action IDs that depend on this action
        """
        if action_id not in self.actions:
            raise ValueError(f"Action '{action_id}' not found")
        return self.graph.get(action_id, [])

    def get_execution_depth(self, action_id: str) -> int:
        """
        Get the execution depth (level) of an action.

        Depth represents how far from the root the action is in the
        dependency graph. Actions at the same depth can be executed in parallel.

        Args:
            action_id: ID of the action

        Returns:
            Depth level (0 for root actions)

        Raises:
            ValueError: If action not found or FSA not in COMPLETED state
        """
        if self.state != FSAState.COMPLETED:
            raise ValueError("Must resolve dependencies before getting execution depth")

        if action_id not in self.actions:
            raise ValueError(f"Action '{action_id}' not found")

        # Find which parallel group the action belongs to
        for depth, group in enumerate(self.execution_plan.parallel_groups):
            if action_id in group:
                return depth

        return 0


# ============================================================================
# TESTS
# ============================================================================

def test_simple_dag():
    """Test basic DAG building and topological sort."""
    print("Test 1: Simple DAG")

    actions = [
        Action(id="A", name="Task A", dependencies=[]),
        Action(id="B", name="Task B", dependencies=["A"]),
        Action(id="C", name="Task C", dependencies=["A"]),
        Action(id="D", name="Task D", dependencies=["B", "C"]),
    ]

    resolver = DependencyResolverFSA()
    plan = resolver.resolve(actions)

    print(f"  Execution order: {plan.execution_order}")
    print(f"  Parallel groups: {plan.parallel_groups}")

    # Verify execution order is valid
    order = plan.execution_order
    assert order.index("A") < order.index("B"), "A should come before B"
    assert order.index("A") < order.index("C"), "A should come before C"
    assert order.index("B") < order.index("D"), "B should come before D"
    assert order.index("C") < order.index("D"), "C should come before D"

    # Verify parallel groups
    assert ["A"] in plan.parallel_groups, "A should be in its own group"
    assert set(plan.parallel_groups[1]) == {"B", "C"}, "B and C should be parallel"
    assert ["D"] in plan.parallel_groups, "D should be in its own group"

    print("  ✓ Test passed\n")


def test_cycle_detection():
    """Test circular dependency detection."""
    print("Test 2: Cycle Detection")

    actions = [
        Action(id="A", name="Task A", dependencies=["B"]),
        Action(id="B", name="Task B", dependencies=["C"]),
        Action(id="C", name="Task C", dependencies=["A"]),
    ]

    resolver = DependencyResolverFSA()

    try:
        resolver.resolve(actions)
        assert False, "Should have raised CircularDependencyError"
    except CircularDependencyError as e:
        print(f"  ✓ Correctly detected cycle: {e}")
        assert resolver.state == FSAState.ERROR
        print("  ✓ Test passed\n")


def test_missing_dependency():
    """Test missing dependency detection."""
    print("Test 3: Missing Dependency Detection")

    actions = [
        Action(id="A", name="Task A", dependencies=["B"]),
        Action(id="C", name="Task C", dependencies=["A"]),
    ]

    resolver = DependencyResolverFSA()

    try:
        resolver.resolve(actions)
        assert False, "Should have raised MissingDependencyError"
    except MissingDependencyError as e:
        print(f"  ✓ Correctly detected missing dependency: {e}")
        print("  ✓ Test passed\n")


def test_self_dependency():
    """Test self-dependency detection."""
    print("Test 4: Self-Dependency Detection")

    actions = [
        Action(id="A", name="Task A", dependencies=["A"]),
    ]

    resolver = DependencyResolverFSA()

    try:
        resolver.resolve(actions)
        assert False, "Should have raised ConflictingDependencyError"
    except ConflictingDependencyError as e:
        print(f"  ✓ Correctly detected self-dependency: {e}")
        print("  ✓ Test passed\n")


def test_complex_parallel_execution():
    """Test complex scenario with multiple parallel execution opportunities."""
    print("Test 5: Complex Parallel Execution")

    # Create a diamond-shaped dependency graph
    #     A
    #    / \
    #   B   C
    #   |\ /|
    #   | X |
    #   |/ \|
    #   D   E
    #    \ /
    #     F

    actions = [
        Action(id="A", name="Task A", dependencies=[]),
        Action(id="B", name="Task B", dependencies=["A"]),
        Action(id="C", name="Task C", dependencies=["A"]),
        Action(id="D", name="Task D", dependencies=["B", "C"]),
        Action(id="E", name="Task E", dependencies=["B", "C"]),
        Action(id="F", name="Task F", dependencies=["D", "E"]),
    ]

    resolver = DependencyResolverFSA()
    plan = resolver.resolve(actions)

    print(f"  Execution order: {plan.execution_order}")
    print(f"  Parallel groups: {plan.parallel_groups}")

    # Verify parallel groups
    assert len(plan.parallel_groups) == 4, "Should have 4 depth levels"
    assert plan.parallel_groups[0] == ["A"], "Level 0: A"
    assert set(plan.parallel_groups[1]) == {"B", "C"}, "Level 1: B, C (parallel)"
    assert set(plan.parallel_groups[2]) == {"D", "E"}, "Level 2: D, E (parallel)"
    assert plan.parallel_groups[3] == ["F"], "Level 3: F"

    print("  ✓ Test passed\n")


def test_duplicate_actions():
    """Test duplicate action ID detection."""
    print("Test 6: Duplicate Action Detection")

    actions = [
        Action(id="A", name="Task A", dependencies=[]),
        Action(id="A", name="Task A Duplicate", dependencies=[]),
    ]

    resolver = DependencyResolverFSA()

    try:
        resolver.resolve(actions)
        assert False, "Should have raised ConflictingDependencyError"
    except ConflictingDependencyError as e:
        print(f"  ✓ Correctly detected duplicate: {e}")
        print("  ✓ Test passed\n")


def test_warnings():
    """Test warning generation for orphaned actions."""
    print("Test 7: Warning Generation")

    actions = [
        Action(id="A", name="Task A", dependencies=[]),
        Action(id="B", name="Task B", dependencies=[]),
        Action(id="C", name="Task C", dependencies=["A"]),
    ]

    resolver = DependencyResolverFSA()
    plan = resolver.resolve(actions)

    print(f"  Warnings: {len(plan.warnings)}")
    for warning in plan.warnings:
        print(f"    - {warning.action_id}: {warning.message}")

    # Both A and B are independent, so they should have warnings
    # (A is not an orphan as C depends on it, but B is)
    assert len(plan.warnings) > 0, "Should have warnings for orphaned actions"
    print("  ✓ Test passed\n")


def test_execution_depth():
    """Test execution depth calculation."""
    print("Test 8: Execution Depth")

    actions = [
        Action(id="A", name="Task A", dependencies=[]),
        Action(id="B", name="Task B", dependencies=["A"]),
        Action(id="C", name="Task C", dependencies=["B"]),
    ]

    resolver = DependencyResolverFSA()
    resolver.resolve(actions)

    assert resolver.get_execution_depth("A") == 0, "A should be at depth 0"
    assert resolver.get_execution_depth("B") == 1, "B should be at depth 1"
    assert resolver.get_execution_depth("C") == 2, "C should be at depth 2"

    print("  ✓ Execution depths correct")
    print("  ✓ Test passed\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running Dependency Resolver FSA Tests")
    print("=" * 60 + "\n")

    test_simple_dag()
    test_cycle_detection()
    test_missing_dependency()
    test_self_dependency()
    test_complex_parallel_execution()
    test_duplicate_actions()
    test_warnings()
    test_execution_depth()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

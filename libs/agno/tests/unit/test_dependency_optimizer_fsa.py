"""
Comprehensive unit tests for Dependency Optimizer FSA.

Tests cover:
- Graph construction
- Cycle detection
- Topological sorting
- Graph optimization
- Parallel execution identification
- Critical path analysis
- State machine transitions
- Error handling
"""

import pytest
from agno.fsa.dependency_optimizer import (
    DependencyOptimizerFSA,
    DependencyNode,
    DependencyEdge,
    FSAState,
)


class TestDependencyOptimizerFSA:
    """Test suite for Dependency Optimizer FSA."""

    def test_initialization(self):
        """Test FSA initializes in IDLE state."""
        fsa = DependencyOptimizerFSA()
        assert fsa.state == FSAState.IDLE
        assert fsa.error_message is None
        stats = fsa.get_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0

    def test_add_nodes_and_dependencies(self):
        """Test adding nodes and dependency relationships."""
        fsa = DependencyOptimizerFSA()

        # Add nodes
        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_node("C", "Task C")

        # FSA should transition to BUILDING
        assert fsa.state == FSAState.BUILDING

        # Add dependencies: C depends on B, B depends on A
        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "B")

        stats = fsa.get_stats()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2

    def test_simple_execution_order(self):
        """Test topological sorting for simple linear dependencies."""
        fsa = DependencyOptimizerFSA()

        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_node("C", "Task C")

        # C -> B -> A (execution order should be A, B, C)
        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "B")

        order = fsa.get_execution_order()
        assert order == ["A", "B", "C"]

    def test_complex_execution_order(self):
        """Test topological sorting for complex dependency graph."""
        fsa = DependencyOptimizerFSA()

        # Create a more complex graph
        #     A   B
        #     |\ /|
        #     | X |
        #     |/ \|
        #     C   D
        #      \ /
        #       E

        for node_id in ["A", "B", "C", "D", "E"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("C", "A")
        fsa.add_dependency("D", "A")
        fsa.add_dependency("C", "B")
        fsa.add_dependency("D", "B")
        fsa.add_dependency("E", "C")
        fsa.add_dependency("E", "D")

        order = fsa.get_execution_order()

        # Verify topological ordering constraints
        a_idx = order.index("A")
        b_idx = order.index("B")
        c_idx = order.index("C")
        d_idx = order.index("D")
        e_idx = order.index("E")

        assert a_idx < c_idx
        assert a_idx < d_idx
        assert b_idx < c_idx
        assert b_idx < d_idx
        assert c_idx < e_idx
        assert d_idx < e_idx

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        fsa = DependencyOptimizerFSA()

        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_node("C", "Task C")

        # Create a cycle: A -> B -> C -> A
        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "B")
        fsa.add_dependency("A", "C")

        # Validation should fail
        assert fsa.validate_graph() is False
        assert fsa.state == FSAState.ERROR
        assert "Circular dependency" in fsa.error_message

        # Should raise error when trying to get execution order
        with pytest.raises(ValueError, match="ERROR state"):
            fsa.get_execution_order()

    def test_self_loop_detection(self):
        """Test detection of self-referencing dependencies."""
        fsa = DependencyOptimizerFSA()

        fsa.add_node("A", "Task A")
        fsa.add_dependency("A", "A")

        assert fsa.validate_graph() is False
        assert fsa.state == FSAState.ERROR

    def test_graph_optimization_removes_transitive_edges(self):
        """Test that graph optimization removes redundant transitive edges."""
        fsa = DependencyOptimizerFSA()

        # Create graph with transitive edge
        #   A -> B -> C
        #   A ------> C  (redundant)

        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_node("C", "Task C")

        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "B")
        fsa.add_dependency("C", "A")  # Redundant edge

        assert fsa.get_stats()["edge_count"] == 3

        # Optimize should remove 1 edge
        removed = fsa.optimize_graph()
        assert removed == 1
        assert fsa.get_stats()["edge_count"] == 2

        # Execution order should remain valid
        order = fsa.get_execution_order()
        assert order == ["A", "B", "C"]

    def test_parallel_execution_groups(self):
        """Test identification of parallel execution groups."""
        fsa = DependencyOptimizerFSA()

        # Create graph:
        #       A
        #      /|\
        #     B C D
        #      \|/
        #       E

        for node_id in ["A", "B", "C", "D", "E"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "A")
        fsa.add_dependency("D", "A")
        fsa.add_dependency("E", "B")
        fsa.add_dependency("E", "C")
        fsa.add_dependency("E", "D")

        groups = fsa.find_parallel_groups()

        # Should have 3 groups: [A], [B, C, D], [E]
        assert len(groups) == 3
        assert groups[0] == ["A"]
        assert set(groups[1]) == {"B", "C", "D"}
        assert groups[2] == ["E"]

    def test_parallel_groups_independent_chains(self):
        """Test parallel groups with independent chains."""
        fsa = DependencyOptimizerFSA()

        # Two independent chains:
        # A -> B
        # C -> D

        for node_id in ["A", "B", "C", "D"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("B", "A")
        fsa.add_dependency("D", "C")

        groups = fsa.find_parallel_groups()

        # First group should have A and C (can run in parallel)
        # Second group should have B and D (can run in parallel)
        assert len(groups) == 2
        assert set(groups[0]) == {"A", "C"}
        assert set(groups[1]) == {"B", "D"}

    def test_critical_path_linear(self):
        """Test critical path calculation for linear chain."""
        fsa = DependencyOptimizerFSA()

        # A -> B -> C
        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_node("C", "Task C")

        fsa.add_dependency("B", "A", weight=2.0)
        fsa.add_dependency("C", "B", weight=3.0)

        critical_path = fsa.get_critical_path()
        assert critical_path == ["A", "B", "C"]

    def test_critical_path_complex(self):
        """Test critical path with multiple paths of different lengths."""
        fsa = DependencyOptimizerFSA()

        # Two paths:
        # A -> B -> E (weight 1 + 1 = 2)
        # A -> C -> D -> E (weight 1 + 1 + 1 = 3)

        for node_id in ["A", "B", "C", "D", "E"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("B", "A", weight=1.0)
        fsa.add_dependency("C", "A", weight=1.0)
        fsa.add_dependency("D", "C", weight=1.0)
        fsa.add_dependency("E", "B", weight=1.0)
        fsa.add_dependency("E", "D", weight=1.0)

        critical_path = fsa.get_critical_path()
        # Critical path should be A -> C -> D -> E
        assert critical_path == ["A", "C", "D", "E"]

    def test_stats_comprehensive(self):
        """Test comprehensive statistics calculation."""
        fsa = DependencyOptimizerFSA()

        # Create a small graph
        for node_id in ["A", "B", "C", "D"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "A")
        fsa.add_dependency("D", "B")
        fsa.add_dependency("D", "C")

        stats = fsa.get_stats()

        assert stats["node_count"] == 4
        assert stats["edge_count"] == 4
        assert stats["source_nodes"] == 1  # Only A has no dependencies
        assert stats["sink_nodes"] == 1  # Only D has no dependents
        assert "avg_in_degree" in stats
        assert "max_in_degree" in stats
        assert stats["max_in_degree"] == 2  # D has 2 incoming edges

    def test_metadata_preservation(self):
        """Test that node metadata is preserved."""
        fsa = DependencyOptimizerFSA()

        metadata = {"priority": "high", "owner": "team-A"}
        fsa.add_node("A", "Task A", metadata=metadata)

        stats = fsa.get_stats()
        assert stats["node_count"] == 1

    def test_reset_functionality(self):
        """Test that reset clears all data and returns to IDLE."""
        fsa = DependencyOptimizerFSA()

        # Build a graph
        fsa.add_node("A", "Task A")
        fsa.add_node("B", "Task B")
        fsa.add_dependency("B", "A")

        assert fsa.get_stats()["node_count"] == 2

        # Reset
        fsa.reset()

        assert fsa.state == FSAState.IDLE
        assert fsa.get_stats()["node_count"] == 0
        assert fsa.get_stats()["edge_count"] == 0
        assert fsa.error_message is None

    def test_invalid_dependency_nonexistent_node(self):
        """Test error handling when adding dependency with non-existent node."""
        fsa = DependencyOptimizerFSA()

        fsa.add_node("A", "Task A")

        # Try to add dependency to non-existent node
        with pytest.raises(ValueError, match="does not exist"):
            fsa.add_dependency("B", "A")

        with pytest.raises(ValueError, match="does not exist"):
            fsa.add_dependency("A", "C")

    def test_state_transitions(self):
        """Test FSA state transitions."""
        fsa = DependencyOptimizerFSA()

        # Start in IDLE
        assert fsa.state == FSAState.IDLE

        # Adding node transitions to BUILDING
        fsa.add_node("A", "Task A")
        assert fsa.state == FSAState.BUILDING

        # Validation transitions to VALIDATING then back to IDLE
        fsa.validate_graph()
        assert fsa.state == FSAState.IDLE

        # Optimization transitions through OPTIMIZING
        fsa.optimize_graph()
        assert fsa.state == FSAState.IDLE

        # Analysis operations transition through ANALYZING
        fsa.find_parallel_groups()
        assert fsa.state == FSAState.IDLE

    def test_large_graph_performance(self):
        """Test FSA with larger graph to ensure scalability."""
        fsa = DependencyOptimizerFSA()

        # Create a chain of 100 nodes
        num_nodes = 100
        for i in range(num_nodes):
            fsa.add_node(f"node_{i}", f"Task {i}")

        # Create linear dependencies
        for i in range(1, num_nodes):
            fsa.add_dependency(f"node_{i}", f"node_{i-1}")

        # Should handle large graph efficiently
        assert fsa.validate_graph() is True
        order = fsa.get_execution_order()
        assert len(order) == num_nodes
        assert order[0] == "node_0"
        assert order[-1] == f"node_{num_nodes-1}"

        # Test optimization
        removed = fsa.optimize_graph()
        assert removed == 0  # No transitive edges in linear chain

        # Test parallel groups (should all be sequential)
        groups = fsa.find_parallel_groups()
        assert len(groups) == num_nodes  # Each in its own group

    def test_diamond_dependency_pattern(self):
        """Test classic diamond dependency pattern."""
        fsa = DependencyOptimizerFSA()

        #     A
        #    / \
        #   B   C
        #    \ /
        #     D

        for node_id in ["A", "B", "C", "D"]:
            fsa.add_node(node_id, f"Task {node_id}")

        fsa.add_dependency("B", "A")
        fsa.add_dependency("C", "A")
        fsa.add_dependency("D", "B")
        fsa.add_dependency("D", "C")

        # Validate
        assert fsa.validate_graph() is True

        # Check execution order
        order = fsa.get_execution_order()
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

        # Check parallel groups
        groups = fsa.find_parallel_groups()
        assert len(groups) == 3
        assert groups[0] == ["A"]
        assert set(groups[1]) == {"B", "C"}
        assert groups[2] == ["D"]

        # Check critical path
        critical_path = fsa.get_critical_path()
        assert len(critical_path) == 3
        assert critical_path[0] == "A"
        assert critical_path[-1] == "D"


class TestDependencyNode:
    """Test DependencyNode dataclass."""

    def test_node_creation(self):
        """Test creating a dependency node."""
        node = DependencyNode(id="A", name="Task A", metadata={"key": "value"})
        assert node.id == "A"
        assert node.name == "Task A"
        assert node.metadata == {"key": "value"}

    def test_node_equality(self):
        """Test node equality based on ID."""
        node1 = DependencyNode(id="A", name="Task A")
        node2 = DependencyNode(id="A", name="Different Name")
        node3 = DependencyNode(id="B", name="Task B")

        assert node1 == node2  # Same ID
        assert node1 != node3  # Different ID

    def test_node_hashable(self):
        """Test that nodes can be used in sets and dicts."""
        node1 = DependencyNode(id="A", name="Task A")
        node2 = DependencyNode(id="B", name="Task B")

        node_set = {node1, node2}
        assert len(node_set) == 2
        assert node1 in node_set


class TestDependencyEdge:
    """Test DependencyEdge dataclass."""

    def test_edge_creation(self):
        """Test creating a dependency edge."""
        edge = DependencyEdge(from_node="A", to_node="B", weight=2.5)
        assert edge.from_node == "A"
        assert edge.to_node == "B"
        assert edge.weight == 2.5

    def test_edge_default_weight(self):
        """Test edge with default weight."""
        edge = DependencyEdge(from_node="A", to_node="B")
        assert edge.weight == 1.0

    def test_edge_equality(self):
        """Test edge equality based on from and to nodes."""
        edge1 = DependencyEdge(from_node="A", to_node="B", weight=1.0)
        edge2 = DependencyEdge(from_node="A", to_node="B", weight=2.0)
        edge3 = DependencyEdge(from_node="A", to_node="C", weight=1.0)

        assert edge1 == edge2  # Same nodes, different weight
        assert edge1 != edge3  # Different nodes

    def test_edge_hashable(self):
        """Test that edges can be used in sets."""
        edge1 = DependencyEdge(from_node="A", to_node="B")
        edge2 = DependencyEdge(from_node="B", to_node="C")

        edge_set = {edge1, edge2}
        assert len(edge_set) == 2
        assert edge1 in edge_set

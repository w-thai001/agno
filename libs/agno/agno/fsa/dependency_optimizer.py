"""
Dependency Optimizer FSA for analyzing and optimizing dependency graphs.

This module provides a Finite State Automaton implementation for managing
dependency graphs, detecting circular dependencies, optimizing execution order,
and identifying parallel execution opportunities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class FSAState(Enum):
    """States for the Dependency Optimizer FSA."""
    IDLE = "idle"
    BUILDING = "building"
    VALIDATING = "validating"
    OPTIMIZING = "optimizing"
    ANALYZING = "analyzing"
    ERROR = "error"


@dataclass
class DependencyNode:
    """
    Represents a node in the dependency graph.

    Attributes:
        id: Unique identifier for the node
        name: Human-readable name
        metadata: Additional data associated with the node
    """
    id: str
    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DependencyNode):
            return False
        return self.id == other.id


@dataclass
class DependencyEdge:
    """
    Represents a directed edge in the dependency graph.

    Attributes:
        from_node: Source node ID
        to_node: Target node ID (depends on from_node)
        weight: Optional weight for critical path analysis
    """
    from_node: str
    to_node: str
    weight: float = 1.0

    def __hash__(self) -> int:
        return hash((self.from_node, self.to_node))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DependencyEdge):
            return False
        return self.from_node == other.from_node and self.to_node == other.to_node


class DependencyOptimizerFSA:
    """
    Finite State Automaton for dependency graph optimization.

    This FSA manages dependency relationships, validates graphs for circular
    dependencies, optimizes execution order, and identifies opportunities
    for parallel execution.

    States:
        - IDLE: Ready to accept new operations
        - BUILDING: Adding nodes and edges to the graph
        - VALIDATING: Checking for circular dependencies and conflicts
        - OPTIMIZING: Pruning redundant dependencies
        - ANALYZING: Performing critical path and parallel execution analysis
        - ERROR: Invalid operation or graph state
    """

    def __init__(self):
        """Initialize the Dependency Optimizer FSA."""
        self._state: FSAState = FSAState.IDLE
        self._nodes: Dict[str, DependencyNode] = {}
        self._edges: Set[DependencyEdge] = set()
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._error_message: Optional[str] = None
        self._execution_order: Optional[List[str]] = None
        self._parallel_groups: Optional[List[List[str]]] = None
        self._critical_path: Optional[List[str]] = None

        logger.info("DependencyOptimizerFSA initialized in IDLE state")

    @property
    def state(self) -> FSAState:
        """Get the current FSA state."""
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        """Get the error message if in ERROR state."""
        return self._error_message

    def _transition_to(self, new_state: FSAState, error_msg: Optional[str] = None) -> None:
        """
        Transition to a new state.

        Args:
            new_state: The target state
            error_msg: Optional error message for ERROR state
        """
        old_state = self._state
        self._state = new_state
        if error_msg:
            self._error_message = error_msg
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    def add_node(self, node_id: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a node to the dependency graph.

        Args:
            node_id: Unique identifier for the node
            name: Human-readable name
            metadata: Optional additional data

        Raises:
            ValueError: If FSA is in ERROR state
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot add node in ERROR state: {self._error_message}")

        if self._state == FSAState.IDLE:
            self._transition_to(FSAState.BUILDING)

        node = DependencyNode(
            id=node_id,
            name=name,
            metadata=metadata or {}
        )
        self._nodes[node_id] = node

        # Invalidate cached results
        self._execution_order = None
        self._parallel_groups = None
        self._critical_path = None

        logger.debug(f"Added node: {node_id} ({name})")

    def add_dependency(self, node: str, depends_on: str, weight: float = 1.0) -> None:
        """
        Add a dependency relationship (node depends on depends_on).

        Args:
            node: The dependent node ID
            depends_on: The node that must execute first
            weight: Optional weight for critical path analysis

        Raises:
            ValueError: If nodes don't exist or FSA is in ERROR state
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot add dependency in ERROR state: {self._error_message}")

        if node not in self._nodes:
            raise ValueError(f"Node '{node}' does not exist. Add it first with add_node().")

        if depends_on not in self._nodes:
            raise ValueError(f"Node '{depends_on}' does not exist. Add it first with add_node().")

        if self._state == FSAState.IDLE:
            self._transition_to(FSAState.BUILDING)

        edge = DependencyEdge(from_node=depends_on, to_node=node, weight=weight)
        self._edges.add(edge)
        self._adjacency_list[depends_on].add(node)
        self._reverse_adjacency[node].add(depends_on)

        # Invalidate cached results
        self._execution_order = None
        self._parallel_groups = None
        self._critical_path = None

        logger.debug(f"Added dependency: {node} depends on {depends_on} (weight={weight})")

    def _detect_cycles(self) -> Optional[List[str]]:
        """
        Detect circular dependencies using DFS.

        Returns:
            List of node IDs forming a cycle, or None if no cycle exists
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self._nodes}
        parent = {node_id: None for node_id in self._nodes}

        def dfs(node: str) -> Optional[List[str]]:
            color[node] = GRAY

            for neighbor in self._adjacency_list[node]:
                if color[neighbor] == GRAY:
                    # Found a cycle, reconstruct it
                    cycle = [neighbor]
                    current = node
                    while current != neighbor:
                        cycle.append(current)
                        current = parent[current]
                    cycle.append(neighbor)
                    cycle.reverse()
                    return cycle

                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result

            color[node] = BLACK
            return None

        for node_id in self._nodes:
            if color[node_id] == WHITE:
                cycle = dfs(node_id)
                if cycle:
                    return cycle

        return None

    def validate_graph(self) -> bool:
        """
        Validate the dependency graph for circular dependencies and conflicts.

        Returns:
            True if graph is valid, False otherwise

        Raises:
            ValueError: If FSA is in ERROR state
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot validate in ERROR state: {self._error_message}")

        self._transition_to(FSAState.VALIDATING)

        # Check for circular dependencies
        cycle = self._detect_cycles()
        if cycle:
            cycle_str = " -> ".join(cycle)
            self._transition_to(
                FSAState.ERROR,
                f"Circular dependency detected: {cycle_str}"
            )
            logger.error(f"Validation failed: {self._error_message}")
            return False

        # Check for orphaned dependencies
        for node_id in self._nodes:
            for dep in self._reverse_adjacency[node_id]:
                if dep not in self._nodes:
                    self._transition_to(
                        FSAState.ERROR,
                        f"Node '{node_id}' depends on non-existent node '{dep}'"
                    )
                    logger.error(f"Validation failed: {self._error_message}")
                    return False

        self._transition_to(FSAState.IDLE)
        logger.info("Graph validation successful")
        return True

    def get_execution_order(self) -> List[str]:
        """
        Get topologically sorted execution order.

        Returns:
            List of node IDs in execution order

        Raises:
            ValueError: If graph is invalid or contains cycles
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot get execution order in ERROR state: {self._error_message}")

        if self._execution_order is not None:
            return self._execution_order.copy()

        # Validate first
        if not self.validate_graph():
            raise ValueError(f"Invalid graph: {self._error_message}")

        # Kahn's algorithm for topological sorting
        in_degree = {node_id: len(self._reverse_adjacency[node_id]) for node_id in self._nodes}
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in self._adjacency_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            self._transition_to(FSAState.ERROR, "Graph contains cycles")
            raise ValueError("Graph contains cycles")

        self._execution_order = result
        logger.info(f"Computed execution order: {len(result)} nodes")
        return result.copy()

    def optimize_graph(self) -> int:
        """
        Optimize the graph by removing redundant (transitive) edges.

        A redundant edge is one where there's already a longer path
        between the same two nodes.

        Returns:
            Number of edges removed

        Raises:
            ValueError: If graph is invalid
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot optimize in ERROR state: {self._error_message}")

        self._transition_to(FSAState.OPTIMIZING)

        # Validate first
        if not self.validate_graph():
            raise ValueError(f"Invalid graph: {self._error_message}")

        # Find transitive edges using reachability
        def can_reach(start: str, end: str, exclude_direct: bool = False) -> bool:
            """Check if end is reachable from start."""
            if start == end:
                return False

            visited = set()
            queue = deque([start])

            while queue:
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)

                for neighbor in self._adjacency_list[node]:
                    if exclude_direct and node == start and neighbor == end:
                        continue
                    if neighbor == end:
                        return True
                    queue.append(neighbor)

            return False

        edges_to_remove = set()
        for edge in self._edges:
            # Check if there's an alternate path
            if can_reach(edge.from_node, edge.to_node, exclude_direct=True):
                edges_to_remove.add(edge)

        # Remove redundant edges
        for edge in edges_to_remove:
            self._edges.remove(edge)
            self._adjacency_list[edge.from_node].discard(edge.to_node)
            self._reverse_adjacency[edge.to_node].discard(edge.from_node)

        # Invalidate cached results
        self._execution_order = None
        self._parallel_groups = None
        self._critical_path = None

        self._transition_to(FSAState.IDLE)
        logger.info(f"Optimization complete: removed {len(edges_to_remove)} redundant edges")
        return len(edges_to_remove)

    def find_parallel_groups(self) -> List[List[str]]:
        """
        Identify groups of nodes that can execute in parallel.

        Nodes in the same group have no dependencies on each other
        and all their dependencies are satisfied by previous groups.

        Returns:
            List of groups, where each group is a list of node IDs
            that can execute in parallel

        Raises:
            ValueError: If graph is invalid
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot find parallel groups in ERROR state: {self._error_message}")

        if self._parallel_groups is not None:
            return [group.copy() for group in self._parallel_groups]

        self._transition_to(FSAState.ANALYZING)

        # Validate first
        if not self.validate_graph():
            raise ValueError(f"Invalid graph: {self._error_message}")

        # Use level-order grouping based on in-degree
        in_degree = {node_id: len(self._reverse_adjacency[node_id]) for node_id in self._nodes}
        groups = []
        processed = set()

        while len(processed) < len(self._nodes):
            # Find all nodes with in-degree 0 (all dependencies satisfied)
            current_group = [
                node_id for node_id in self._nodes
                if node_id not in processed and in_degree[node_id] == 0
            ]

            if not current_group:
                self._transition_to(FSAState.ERROR, "Unable to find parallel groups")
                raise ValueError("Graph structure error")

            groups.append(current_group)
            processed.update(current_group)

            # Update in-degrees
            for node_id in current_group:
                for neighbor in self._adjacency_list[node_id]:
                    in_degree[neighbor] -= 1

        self._parallel_groups = groups
        self._transition_to(FSAState.IDLE)
        logger.info(f"Found {len(groups)} parallel execution groups")
        return [group.copy() for group in groups]

    def get_critical_path(self) -> List[str]:
        """
        Find the critical path (longest dependency chain) in the graph.

        The critical path represents the minimum time needed to execute
        all tasks if unlimited parallelism is available.

        Returns:
            List of node IDs forming the critical path

        Raises:
            ValueError: If graph is invalid
        """
        if self._state == FSAState.ERROR:
            raise ValueError(f"Cannot get critical path in ERROR state: {self._error_message}")

        if self._critical_path is not None:
            return self._critical_path.copy()

        self._transition_to(FSAState.ANALYZING)

        # Validate first
        if not self.validate_graph():
            raise ValueError(f"Invalid graph: {self._error_message}")

        # Use dynamic programming to find longest path
        execution_order = self.get_execution_order()

        # Calculate longest path to each node
        dist = {node_id: 0.0 for node_id in self._nodes}
        parent = {node_id: None for node_id in self._nodes}

        for node_id in execution_order:
            for neighbor in self._adjacency_list[node_id]:
                # Find edge weight
                edge_weight = 1.0
                for edge in self._edges:
                    if edge.from_node == node_id and edge.to_node == neighbor:
                        edge_weight = edge.weight
                        break

                if dist[node_id] + edge_weight > dist[neighbor]:
                    dist[neighbor] = dist[node_id] + edge_weight
                    parent[neighbor] = node_id

        # Find the node with maximum distance
        max_node = max(self._nodes.keys(), key=lambda n: dist[n])

        # Reconstruct the critical path
        path = []
        current = max_node
        while current is not None:
            path.append(current)
            current = parent[current]

        path.reverse()
        self._critical_path = path
        self._transition_to(FSAState.IDLE)
        logger.info(f"Critical path found: {len(path)} nodes, length={dist[max_node]}")
        return path.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the dependency graph.

        Returns:
            Dictionary containing various graph metrics
        """
        stats = {
            "state": self._state.value,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "error_message": self._error_message,
        }

        if self._state != FSAState.ERROR and len(self._nodes) > 0:
            try:
                # Calculate additional statistics
                in_degrees = [len(self._reverse_adjacency[n]) for n in self._nodes]
                out_degrees = [len(self._adjacency_list[n]) for n in self._nodes]

                stats.update({
                    "avg_in_degree": sum(in_degrees) / len(in_degrees) if in_degrees else 0,
                    "max_in_degree": max(in_degrees) if in_degrees else 0,
                    "avg_out_degree": sum(out_degrees) / len(out_degrees) if out_degrees else 0,
                    "max_out_degree": max(out_degrees) if out_degrees else 0,
                    "source_nodes": len([n for n in self._nodes if len(self._reverse_adjacency[n]) == 0]),
                    "sink_nodes": len([n for n in self._nodes if len(self._adjacency_list[n]) == 0]),
                })

                # Try to get execution order length
                try:
                    order = self.get_execution_order()
                    stats["execution_order_length"] = len(order)
                except Exception:
                    pass

                # Try to get parallel groups
                try:
                    groups = self.find_parallel_groups()
                    stats["parallel_groups_count"] = len(groups)
                    stats["max_parallelism"] = max(len(g) for g in groups) if groups else 0
                except Exception:
                    pass

                # Try to get critical path
                try:
                    path = self.get_critical_path()
                    stats["critical_path_length"] = len(path)
                except Exception:
                    pass

            except Exception as e:
                logger.warning(f"Error calculating stats: {e}")

        return stats

    def reset(self) -> None:
        """Reset the FSA to initial state, clearing all data."""
        self._state = FSAState.IDLE
        self._nodes.clear()
        self._edges.clear()
        self._adjacency_list.clear()
        self._reverse_adjacency.clear()
        self._error_message = None
        self._execution_order = None
        self._parallel_groups = None
        self._critical_path = None
        logger.info("FSA reset to IDLE state")

    def __repr__(self) -> str:
        return (
            f"DependencyOptimizerFSA(state={self._state.value}, "
            f"nodes={len(self._nodes)}, edges={len(self._edges)})"
        )

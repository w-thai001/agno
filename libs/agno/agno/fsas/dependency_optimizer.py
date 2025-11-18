"""
Dependency Optimizer FSA - Intelligent cascade orchestration and optimization

This FSA analyzes FSA dependencies, optimizes execution order, resolves conflicts,
minimizes redundancy, and ensures efficient cascade orchestration through graph-based
analysis and optimization strategies.

Author: Agno Team
License: MPL 2.0
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("networkx not available - using pure Python graph implementation")

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """Types of dependencies"""
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"
    RESOURCE = "resource"
    DATA = "data"


class ConflictType(str, Enum):
    """Types of dependency conflicts"""
    VERSION = "version"
    RESOURCE = "resource"
    DATA = "data"
    EXECUTION_ORDER = "execution_order"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts"""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    ISOLATE = "isolate"
    QUEUE = "queue"
    PRIORITIZE = "prioritize"
    MERGE = "merge"


@dataclass
class DependencyNode:
    """Node in dependency graph representing an FSA"""

    fsa_id: str
    fsa_name: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    depth: int = 0
    execution_order: int = -1
    dependency_types: Dict[str, DependencyType] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['dependency_types'] = {k: v.value for k, v in self.dependency_types.items()}
        return data


@dataclass
class DependencyGraph:
    """Graph representation of FSA dependencies"""

    nodes: Dict[str, DependencyNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: DependencyNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.fsa_id] = node

    def add_edge(self, from_id: str, to_id: str, dep_type: DependencyType = DependencyType.REQUIRED) -> None:
        """Add an edge (dependency) to the graph"""
        edge = (from_id, to_id)
        if edge not in self.edges:
            self.edges.append(edge)

        # Update node dependencies
        if from_id in self.nodes:
            if to_id not in self.nodes[from_id].dependencies:
                self.nodes[from_id].dependencies.append(to_id)
                self.nodes[from_id].dependency_types[to_id] = dep_type

        if to_id in self.nodes:
            if from_id not in self.nodes[to_id].dependents:
                self.nodes[to_id].dependents.append(from_id)

    def get_node(self, fsa_id: str) -> Optional[DependencyNode]:
        """Get a node by FSA ID"""
        return self.nodes.get(fsa_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'edges': self.edges,
            'metadata': self.metadata
        }


@dataclass
class Cycle:
    """Circular dependency cycle"""

    fsas_in_cycle: List[str]
    break_point_suggestions: List[Tuple[str, str]] = field(default_factory=list)
    severity: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Conflict:
    """Dependency conflict"""

    fsa1: str
    fsa2: str
    conflict_type: ConflictType
    priority: int = 0
    resolution_strategy: Optional[ResolutionStrategy] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['conflict_type'] = self.conflict_type.value
        if self.resolution_strategy:
            data['resolution_strategy'] = self.resolution_strategy.value
        return data


@dataclass
class Resolution:
    """Conflict resolution result"""

    resolved_order: List[str]
    modifications: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ExecutionPlan:
    """Optimized execution plan"""

    sequential_stages: List[List[str]] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    estimated_time: float = 0.0
    optimization_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class OptimizedGraph:
    """Optimized dependency graph"""

    original_graph: DependencyGraph
    optimized_graph: DependencyGraph
    optimizations_applied: List[str] = field(default_factory=list)
    performance_gain: float = 0.0
    redundancies_eliminated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'original_graph': self.original_graph.to_dict(),
            'optimized_graph': self.optimized_graph.to_dict(),
            'optimizations_applied': self.optimizations_applied,
            'performance_gain': self.performance_gain,
            'redundancies_eliminated': self.redundancies_eliminated
        }


@dataclass
class ValidationResult:
    """Dependency validation result"""

    is_valid: bool
    missing_dependencies: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DependencyOptimizerError(Exception):
    """Base exception for Dependency Optimizer"""
    pass


class CircularDependencyError(DependencyOptimizerError):
    """Raised when circular dependencies are detected"""
    pass


class ConflictResolutionError(DependencyOptimizerError):
    """Raised when conflicts cannot be resolved"""
    pass


class DependencyOptimizerFSA:
    """
    Dependency Optimizer FSA - Intelligent cascade orchestration

    Category: Meta

    Key Capabilities:
        - Graph-based dependency analysis
        - Topological sorting for optimal execution order
        - Circular dependency detection and resolution
        - Dependency conflict resolver
        - Redundancy elimination
        - Parallel execution planning
        - Dynamic dependency injection
        - Cache-aware dependency tracking
        - Version compatibility checking
        - Execution order optimization
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Dependency Optimizer FSA

        Args:
            config: Optional configuration dictionary
                - enable_parallel_execution: bool (default True)
                - max_parallel_fsas: int (default 4)
                - allow_circular_deps: bool (default False)
                - cache_resolved_deps: bool (default True)
        """
        self.name = "DependencyOptimizerFSA"
        self.config = config or {}
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()

        # Configuration
        self.enable_parallel_execution = self.config.get('enable_parallel_execution', True)
        self.max_parallel_fsas = self.config.get('max_parallel_fsas', 4)
        self.allow_circular_deps = self.config.get('allow_circular_deps', False)
        self.cache_resolved_deps = self.config.get('cache_resolved_deps', True)

        # Cache for resolved dependencies
        self._dependency_cache: Dict[str, Any] = {}

        logger.info(f"Initialized {self.name}")

    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the main FSA functionality

        Args:
            task: Task description or identifier
            params: Optional parameters for execution

        Returns:
            Execution result

        Raises:
            DependencyOptimizerError: If execution fails
        """
        if not task:
            raise DependencyOptimizerError("Task cannot be empty")

        logger.info(f"Executing task: {task}")
        params = params or {}

        if not self.validate_input(params):
            raise DependencyOptimizerError("Invalid input parameters")

        try:
            # Route to appropriate method based on task
            if task == "analyze_dependencies":
                return self.analyze_dependencies(params.get('fsas', []))
            elif task == "optimize_execution_order":
                return self.optimize_execution_order(params.get('graph'))
            elif task == "detect_circular_dependencies":
                return self.detect_circular_dependencies(params.get('graph'))
            elif task == "plan_parallel_execution":
                return self.plan_parallel_execution(params.get('graph'))
            else:
                return self._process_task(task, params)
        except Exception as e:
            return self.handle_error(e)

    def analyze_dependencies(self, fsas: List[Dict[str, Any]]) -> DependencyGraph:
        """
        Build dependency graph from FSA specifications

        Args:
            fsas: List of FSA specifications with dependencies

        Returns:
            DependencyGraph representing all dependencies
        """
        logger.info(f"Analyzing dependencies for {len(fsas)} FSAs")

        graph = DependencyGraph()

        # First pass: Create nodes
        for fsa_spec in fsas:
            fsa_id = fsa_spec.get('id', fsa_spec.get('name', 'unknown'))
            node = DependencyNode(
                fsa_id=fsa_id,
                fsa_name=fsa_spec.get('name', fsa_id),
                metadata=fsa_spec.get('metadata', {})
            )
            graph.add_node(node)

        # Second pass: Create edges
        for fsa_spec in fsas:
            fsa_id = fsa_spec.get('id', fsa_spec.get('name', 'unknown'))
            dependencies = fsa_spec.get('dependencies', [])

            for dep in dependencies:
                if isinstance(dep, str):
                    dep_id = dep
                    dep_type = DependencyType.REQUIRED
                elif isinstance(dep, dict):
                    dep_id = dep.get('id', dep.get('name'))
                    dep_type = DependencyType(dep.get('type', 'required'))
                else:
                    continue

                if dep_id in graph.nodes:
                    graph.add_edge(fsa_id, dep_id, dep_type)
                else:
                    logger.warning(f"Dependency {dep_id} not found for FSA {fsa_id}")

        # Calculate depths
        self._calculate_depths(graph)

        logger.info(f"Dependency graph created: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph

    def optimize_execution_order(self, graph: DependencyGraph) -> List[str]:
        """
        Determine optimal FSA execution order using topological sort

        Args:
            graph: Dependency graph

        Returns:
            List of FSA IDs in optimal execution order

        Raises:
            CircularDependencyError: If circular dependencies detected
        """
        logger.info("Computing optimal execution order")

        # Check for circular dependencies
        cycles = self.detect_circular_dependencies(graph)
        if cycles and not self.allow_circular_deps:
            raise CircularDependencyError(
                f"Circular dependencies detected: {[c.fsas_in_cycle for c in cycles]}"
            )

        # Perform topological sort
        order = self._topological_sort(graph)

        # Update execution order in nodes
        for idx, fsa_id in enumerate(order):
            if fsa_id in graph.nodes:
                graph.nodes[fsa_id].execution_order = idx

        logger.info(f"Execution order computed: {len(order)} FSAs")
        return order

    def detect_circular_dependencies(self, graph: DependencyGraph) -> List[Cycle]:
        """
        Detect circular dependencies in the graph

        Args:
            graph: Dependency graph

        Returns:
            List of detected cycles
        """
        logger.info("Detecting circular dependencies")

        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            """DFS to detect cycles"""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            node = graph.get_node(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # Cycle detected
                        cycle_start = path.index(dep_id)
                        cycle_nodes = path[cycle_start:] + [dep_id]

                        # Suggest break points (weakest dependencies)
                        break_points = []
                        for i in range(len(cycle_nodes) - 1):
                            from_id, to_id = cycle_nodes[i], cycle_nodes[i + 1]
                            from_node = graph.get_node(from_id)
                            if from_node and to_id in from_node.dependency_types:
                                if from_node.dependency_types[to_id] == DependencyType.OPTIONAL:
                                    break_points.append((from_id, to_id))

                        if not break_points:
                            # Suggest breaking the last edge
                            break_points.append((cycle_nodes[-2], cycle_nodes[-1]))

                        cycle = Cycle(
                            fsas_in_cycle=cycle_nodes,
                            break_point_suggestions=break_points
                        )
                        cycles.append(cycle)
                        return True

            path.pop()
            rec_stack.remove(node_id)
            return False

        # Check all nodes
        for node_id in graph.nodes:
            if node_id not in visited:
                dfs(node_id)

        logger.info(f"Detected {len(cycles)} circular dependencies")
        return cycles

    def resolve_conflicts(self, conflicts: List[Conflict]) -> Resolution:
        """
        Resolve dependency conflicts

        Args:
            conflicts: List of conflicts to resolve

        Returns:
            Resolution with resolved order and modifications
        """
        logger.info(f"Resolving {len(conflicts)} conflicts")

        resolved_order = []
        modifications = []
        warnings = []

        # Sort conflicts by priority
        sorted_conflicts = sorted(conflicts, key=lambda c: c.priority, reverse=True)

        for conflict in sorted_conflicts:
            strategy = conflict.resolution_strategy or self._suggest_resolution_strategy(conflict)

            if strategy == ResolutionStrategy.UPGRADE:
                modifications.append(f"Upgrade {conflict.fsa1} to resolve version conflict")
            elif strategy == ResolutionStrategy.DOWNGRADE:
                modifications.append(f"Downgrade {conflict.fsa2} to resolve version conflict")
            elif strategy == ResolutionStrategy.ISOLATE:
                modifications.append(f"Isolate {conflict.fsa1} and {conflict.fsa2}")
                warnings.append(f"Isolated execution may reduce performance")
            elif strategy == ResolutionStrategy.QUEUE:
                modifications.append(f"Queue {conflict.fsa2} after {conflict.fsa1}")
            elif strategy == ResolutionStrategy.PRIORITIZE:
                modifications.append(f"Prioritize {conflict.fsa1} over {conflict.fsa2}")
                resolved_order.extend([conflict.fsa1, conflict.fsa2])
            elif strategy == ResolutionStrategy.MERGE:
                modifications.append(f"Merge dependencies for {conflict.fsa1} and {conflict.fsa2}")

        resolution = Resolution(
            resolved_order=resolved_order,
            modifications=modifications,
            warnings=warnings
        )

        logger.info(f"Conflicts resolved with {len(modifications)} modifications")
        return resolution

    def eliminate_redundancy(self, graph: DependencyGraph) -> OptimizedGraph:
        """
        Eliminate redundant dependencies

        Args:
            graph: Original dependency graph

        Returns:
            OptimizedGraph with redundancies removed
        """
        logger.info("Eliminating redundant dependencies")

        optimized_graph = DependencyGraph()
        optimizations_applied = []
        redundancies_eliminated = 0

        # Copy nodes
        for node_id, node in graph.nodes.items():
            optimized_graph.add_node(DependencyNode(
                fsa_id=node.fsa_id,
                fsa_name=node.fsa_name,
                metadata=node.metadata.copy()
            ))

        # Eliminate transitive dependencies
        for node_id, node in graph.nodes.items():
            direct_deps = set(node.dependencies)
            transitive_deps = set()

            # Find all transitive dependencies
            for dep_id in node.dependencies:
                dep_node = graph.get_node(dep_id)
                if dep_node:
                    transitive_deps.update(dep_node.dependencies)

            # Remove transitive dependencies from direct dependencies
            necessary_deps = direct_deps - transitive_deps

            if len(necessary_deps) < len(direct_deps):
                eliminated = len(direct_deps) - len(necessary_deps)
                redundancies_eliminated += eliminated
                optimizations_applied.append(
                    f"Eliminated {eliminated} transitive dependencies from {node_id}"
                )

            # Add only necessary edges
            for dep_id in necessary_deps:
                dep_type = node.dependency_types.get(dep_id, DependencyType.REQUIRED)
                optimized_graph.add_edge(node_id, dep_id, dep_type)

        # Calculate performance gain (estimated)
        performance_gain = (redundancies_eliminated / max(len(graph.edges), 1)) * 100

        result = OptimizedGraph(
            original_graph=graph,
            optimized_graph=optimized_graph,
            optimizations_applied=optimizations_applied,
            performance_gain=performance_gain,
            redundancies_eliminated=redundancies_eliminated
        )

        logger.info(f"Eliminated {redundancies_eliminated} redundancies, "
                   f"estimated {performance_gain:.1f}% performance gain")
        return result

    def plan_parallel_execution(self, graph: DependencyGraph) -> ExecutionPlan:
        """
        Create parallel execution plan for independent FSAs

        Args:
            graph: Dependency graph

        Returns:
            ExecutionPlan with parallel groups
        """
        logger.info("Planning parallel execution")

        # Get execution order
        try:
            execution_order = self.optimize_execution_order(graph)
        except CircularDependencyError:
            logger.warning("Circular dependencies detected, using partial order")
            execution_order = list(graph.nodes.keys())

        # Group FSAs by depth level
        depth_groups: Dict[int, List[str]] = defaultdict(list)
        for fsa_id in execution_order:
            node = graph.get_node(fsa_id)
            if node:
                depth_groups[node.depth].append(fsa_id)

        # Create sequential stages and identify parallel opportunities
        sequential_stages = []
        parallel_groups = []

        for depth in sorted(depth_groups.keys()):
            fsas_at_depth = depth_groups[depth]

            if len(fsas_at_depth) > 1 and self.enable_parallel_execution:
                # Can execute in parallel
                # Split into groups based on max_parallel_fsas
                for i in range(0, len(fsas_at_depth), self.max_parallel_fsas):
                    parallel_group = fsas_at_depth[i:i + self.max_parallel_fsas]
                    parallel_groups.append(parallel_group)
                    sequential_stages.append(parallel_group)
            else:
                # Must execute sequentially
                sequential_stages.append(fsas_at_depth)

        optimization_notes = [
            f"Identified {len(parallel_groups)} parallel execution groups",
            f"Total stages: {len(sequential_stages)}",
            f"Max parallelism: {max(len(g) for g in parallel_groups) if parallel_groups else 1}"
        ]

        plan = ExecutionPlan(
            sequential_stages=sequential_stages,
            parallel_groups=parallel_groups,
            optimization_notes=optimization_notes
        )

        logger.info(f"Execution plan created: {len(sequential_stages)} stages, "
                   f"{len(parallel_groups)} parallel groups")
        return plan

    def inject_dependencies(self, fsa: Dict[str, Any], deps: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject dependencies into FSA at runtime

        Args:
            fsa: FSA specification
            deps: Dependencies to inject

        Returns:
            FSA with injected dependencies
        """
        logger.info(f"Injecting dependencies for FSA {fsa.get('id', 'unknown')}")

        fsa_with_deps = fsa.copy()
        fsa_with_deps['injected_dependencies'] = deps

        # Cache if enabled
        if self.cache_resolved_deps:
            fsa_id = fsa.get('id', fsa.get('name'))
            self._dependency_cache[fsa_id] = deps

        return fsa_with_deps

    def validate_dependencies(self, fsa: Dict[str, Any], available_fsas: List[str]) -> ValidationResult:
        """
        Validate that all required dependencies are available

        Args:
            fsa: FSA specification
            available_fsas: List of available FSA IDs

        Returns:
            ValidationResult with validation status
        """
        fsa_id = fsa.get('id', fsa.get('name', 'unknown'))
        logger.info(f"Validating dependencies for {fsa_id}")

        missing_dependencies = []
        errors = []
        warnings = []

        dependencies = fsa.get('dependencies', [])

        for dep in dependencies:
            if isinstance(dep, str):
                dep_id = dep
                dep_type = DependencyType.REQUIRED
            elif isinstance(dep, dict):
                dep_id = dep.get('id', dep.get('name'))
                dep_type = DependencyType(dep.get('type', 'required'))
            else:
                continue

            if dep_id not in available_fsas:
                if dep_type == DependencyType.REQUIRED:
                    missing_dependencies.append(dep_id)
                    errors.append(f"Required dependency {dep_id} not available")
                elif dep_type == DependencyType.OPTIONAL:
                    warnings.append(f"Optional dependency {dep_id} not available")

        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            missing_dependencies=missing_dependencies,
            errors=errors,
            warnings=warnings
        )

        logger.info(f"Validation result: {'valid' if is_valid else 'invalid'}")
        return result

    def compute_dependency_depth(self, graph: DependencyGraph) -> Dict[str, int]:
        """
        Calculate dependency depth for each FSA

        Args:
            graph: Dependency graph

        Returns:
            Dictionary mapping FSA IDs to depth levels
        """
        depths = {}

        # Initialize all depths to 0
        for node_id in graph.nodes:
            depths[node_id] = 0

        # Use BFS to calculate depths
        changed = True
        while changed:
            changed = False
            for node_id, node in graph.nodes.items():
                if node.dependencies:
                    max_dep_depth = max(
                        depths.get(dep_id, 0)
                        for dep_id in node.dependencies
                    )
                    new_depth = max_dep_depth + 1
                    if depths[node_id] != new_depth:
                        depths[node_id] = new_depth
                        changed = True

        # Update graph nodes
        for node_id, depth in depths.items():
            if node_id in graph.nodes:
                graph.nodes[node_id].depth = depth

        return depths

    def export_dependency_viz(self, graph: DependencyGraph, path: str) -> bool:
        """
        Export dependency graph visualization data

        Args:
            graph: Dependency graph
            path: Output file path

        Returns:
            True if export successful
        """
        try:
            # Export as DOT format for Graphviz
            dot_lines = ["digraph Dependencies {"]
            dot_lines.append("  rankdir=TB;")
            dot_lines.append("  node [shape=box];")

            # Add nodes
            for node_id, node in graph.nodes.items():
                label = f"{node.fsa_name}\\n(depth: {node.depth})"
                dot_lines.append(f'  "{node_id}" [label="{label}"];')

            # Add edges
            for from_id, to_id in graph.edges:
                from_node = graph.get_node(from_id)
                dep_type = "solid"
                if from_node and to_id in from_node.dependency_types:
                    if from_node.dependency_types[to_id] == DependencyType.OPTIONAL:
                        dep_type = "dashed"

                dot_lines.append(f'  "{from_id}" -> "{to_id}" [style={dep_type}];')

            dot_lines.append("}")

            # Write to file
            Path(path).write_text("\n".join(dot_lines))
            logger.info(f"Dependency visualization exported to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export visualization: {e}")
            return False

    def optimize_cascade_pipeline(self, cascade: Dict[str, Any]) -> Dict[str, Any]:
        """
        End-to-end cascade pipeline optimization

        Args:
            cascade: Cascade configuration with FSA specifications

        Returns:
            Optimized cascade configuration
        """
        logger.info("Optimizing cascade pipeline")

        fsas = cascade.get('fsas', [])

        # Analyze dependencies
        graph = self.analyze_dependencies(fsas)

        # Eliminate redundancy
        optimized = self.eliminate_redundancy(graph)

        # Plan parallel execution
        plan = self.plan_parallel_execution(optimized.optimized_graph)

        # Create optimized cascade
        optimized_cascade = cascade.copy()
        optimized_cascade['execution_plan'] = plan.to_dict()
        optimized_cascade['optimization_applied'] = optimized.optimizations_applied
        optimized_cascade['performance_gain'] = optimized.performance_gain

        logger.info(f"Cascade optimized: {optimized.performance_gain:.1f}% estimated gain")
        return optimized_cascade

    def resolve_runtime_dependencies(
        self,
        fsa: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve dependencies dynamically at runtime

        Args:
            fsa: FSA specification
            context: Runtime context

        Returns:
            Resolved dependencies
        """
        fsa_id = fsa.get('id', fsa.get('name', 'unknown'))
        logger.info(f"Resolving runtime dependencies for {fsa_id}")

        # Check cache first
        if self.cache_resolved_deps and fsa_id in self._dependency_cache:
            logger.info(f"Using cached dependencies for {fsa_id}")
            return self._dependency_cache[fsa_id]

        resolved = {}
        dependencies = fsa.get('dependencies', [])

        for dep in dependencies:
            if isinstance(dep, dict):
                dep_id = dep.get('id', dep.get('name'))
                dep_type = DependencyType(dep.get('type', 'required'))

                # Check if dependency is conditional
                if dep_type == DependencyType.CONDITIONAL:
                    condition = dep.get('condition')
                    if condition and not self._evaluate_condition(condition, context):
                        continue

                # Resolve from context
                if dep_id in context:
                    resolved[dep_id] = context[dep_id]

        # Cache resolved dependencies
        if self.cache_resolved_deps:
            self._dependency_cache[fsa_id] = resolved

        return resolved

    def validate_input(self, data: Any) -> bool:
        """Validate input data"""
        if data is None:
            raise DependencyOptimizerError("Input data cannot be None")
        return True

    def get_state(self) -> Dict[str, Any]:
        """Get current FSA state"""
        return self.state.copy()

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set FSA state"""
        self.state = state

    def handle_error(self, error: Exception) -> str:
        """Handle errors during execution"""
        error_msg = f"Error in {self.name}: {str(error)}"
        logger.error(error_msg)
        return error_msg

    def _process_task(self, task: str, params: Dict[str, Any]) -> Any:
        """Internal method to process task"""
        return {"status": "success", "task": task, "params": params}

    def initialize(self) -> None:
        """Initialize FSA for operation"""
        logger.info(f"Initializing {self.name}")
        self.state = {"initialized": True, "timestamp": datetime.now()}

    def cleanup(self) -> None:
        """Cleanup FSA resources"""
        logger.info(f"Cleaning up {self.name}")
        self._dependency_cache.clear()
        self.state = {}

    # Helper methods

    def _calculate_depths(self, graph: DependencyGraph) -> None:
        """Calculate and update depth for all nodes"""
        depths = self.compute_dependency_depth(graph)
        for node_id, depth in depths.items():
            if node_id in graph.nodes:
                graph.nodes[node_id].depth = depth

    def _topological_sort(self, graph: DependencyGraph) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm

        Returns:
            List of FSA IDs in topologically sorted order
        """
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in graph.nodes}
        for node_id, node in graph.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in in_degree:
                    in_degree[node_id] += 1

        # Queue of nodes with no incoming edges
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree for dependents
            node = graph.get_node(node_id)
            if node:
                for dependent_id in node.dependents:
                    if dependent_id in in_degree:
                        in_degree[dependent_id] -= 1
                        if in_degree[dependent_id] == 0:
                            queue.append(dependent_id)

        # If not all nodes are included, there's a cycle
        if len(result) != len(graph.nodes):
            logger.warning("Topological sort incomplete - possible circular dependencies")

        return result

    def _suggest_resolution_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        """Suggest a resolution strategy for a conflict"""
        if conflict.conflict_type == ConflictType.VERSION:
            return ResolutionStrategy.UPGRADE
        elif conflict.conflict_type == ConflictType.RESOURCE:
            return ResolutionStrategy.QUEUE
        elif conflict.conflict_type == ConflictType.DATA:
            return ResolutionStrategy.MERGE
        elif conflict.conflict_type == ConflictType.EXECUTION_ORDER:
            return ResolutionStrategy.PRIORITIZE
        return ResolutionStrategy.ISOLATE

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a conditional dependency"""
        # Simple evaluation - check if key exists in context
        # In production, this could use a more sophisticated expression evaluator
        return condition in context

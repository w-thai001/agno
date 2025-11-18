"""
Cascade Validator FSA - Validates FSA cascade integrity, dependencies, and execution flow.

This module provides comprehensive validation for FSA cascades in multi-agent workflows,
ensuring consistency, detecting conflicts, and optimizing execution order.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4


class FSAState(Enum):
    """FSA state enumeration."""

    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ConflictType(Enum):
    """Types of conflicts that can occur between FSAs."""

    RESOURCE = "resource"  # Resource contention
    DATA = "data"  # Data dependency conflict
    TIMING = "timing"  # Timing/ordering conflict
    STATE = "state"  # State machine conflict
    PRIORITY = "priority"  # Priority conflict


@dataclass
class FSA:
    """
    Finite State Automaton representation for workflow components.

    Attributes:
        id: Unique identifier for the FSA
        name: Human-readable name
        state: Current state of the FSA
        inputs: Expected input data types
        outputs: Produced output data types
        dependencies: List of FSA IDs this FSA depends on
        resources: Required resources (e.g., GPU, memory)
        priority: Execution priority (higher = more important)
        metadata: Additional metadata
        estimated_duration: Estimated execution time in seconds
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    state: FSAState = FSAState.IDLE
    inputs: Dict[str, str] = field(default_factory=dict)  # name -> type
    outputs: Dict[str, str] = field(default_factory=dict)  # name -> type
    dependencies: List[str] = field(default_factory=list)  # FSA IDs
    resources: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: float = 0.0

    def can_execute(self, completed_fsas: Set[str]) -> bool:
        """Check if this FSA can execute given completed FSAs."""
        return all(dep in completed_fsas for dep in self.dependencies)


@dataclass
class FSACascade:
    """
    A cascade of FSAs representing a multi-agent workflow.

    Attributes:
        id: Unique identifier for the cascade
        name: Cascade name
        fsas: List of FSAs in the cascade
        global_timeout: Maximum execution time for entire cascade
        metadata: Additional metadata
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    fsas: List[FSA] = field(default_factory=list)
    global_timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_fsa_by_id(self, fsa_id: str) -> Optional[FSA]:
        """Get FSA by ID."""
        for fsa in self.fsas:
            if fsa.id == fsa_id:
                return fsa
        return None


@dataclass
class DependencyGraph:
    """
    Dependency graph for FSA cascade.

    Attributes:
        nodes: Set of FSA IDs
        edges: Adjacency list (source -> [targets])
        reverse_edges: Reverse adjacency list (target -> [sources])
        levels: Topologically sorted levels
    """

    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    reverse_edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    levels: List[List[str]] = field(default_factory=list)


@dataclass
class Cycle:
    """Represents a circular dependency cycle."""

    nodes: List[str]  # FSA IDs in the cycle
    severity: str = "error"  # error, warning

    def __str__(self) -> str:
        return " -> ".join(self.nodes + [self.nodes[0]])


@dataclass
class Conflict:
    """Represents a conflict between FSAs."""

    type: ConflictType
    fsa_ids: List[str]
    description: str
    severity: str = "warning"  # error, warning, info
    resolution: Optional[str] = None


@dataclass
class FlowValidation:
    """Data flow validation result."""

    is_valid: bool
    issues: List[str] = field(default_factory=list)
    type_mismatches: List[Tuple[str, str, str, str]] = field(default_factory=list)  # (source_fsa, output, target_fsa, input)
    missing_inputs: List[Tuple[str, str]] = field(default_factory=list)  # (fsa_id, input_name)


@dataclass
class ExecutionPlan:
    """Optimized execution plan for FSA cascade."""

    stages: List[List[str]] = field(default_factory=list)  # Each stage = parallel executable FSAs
    total_estimated_time: float = 0.0
    critical_path: List[str] = field(default_factory=list)
    parallelism_opportunities: int = 0


@dataclass
class PerformanceReport:
    """Performance analysis report."""

    bottlenecks: List[str] = field(default_factory=list)  # FSA IDs
    total_estimated_duration: float = 0.0
    critical_path_duration: float = 0.0
    parallelism_score: float = 0.0  # 0-1 scale
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class IntegrityReport:
    """Cascade integrity check report."""

    is_consistent: bool
    issues: List[str] = field(default_factory=list)
    orphaned_fsas: List[str] = field(default_factory=list)
    unreachable_fsas: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Comprehensive validation result."""

    is_valid: bool
    dependency_graph: Optional[DependencyGraph] = None
    cycles: List[Cycle] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    flow_validation: Optional[FlowValidation] = None
    integrity_report: Optional[IntegrityReport] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation and analysis report."""

    validation_result: ValidationResult
    execution_plan: Optional[ExecutionPlan] = None
    performance_report: Optional[PerformanceReport] = None
    timestamp: Optional[str] = None


class CascadeValidatorFSA:
    """
    FSA for validating cascade integrity, dependencies, and execution flow.

    This validator ensures FSA cascades maintain consistency, detects conflicts,
    and optimizes cascade performance for multi-agent workflows.
    """

    def __init__(
        self,
        name: str = "CascadeValidator",
        strict_mode: bool = False,
        enable_optimization: bool = True
    ):
        """
        Initialize the Cascade Validator FSA.

        Args:
            name: Name of the validator
            strict_mode: If True, treat warnings as errors
            enable_optimization: Enable execution plan optimization
        """
        self.name = name
        self.strict_mode = strict_mode
        self.enable_optimization = enable_optimization
        self.state = FSAState.IDLE

    def execute(self, cascade: FSACascade) -> ValidationReport:
        """
        Main execution pipeline for cascade validation.

        Args:
            cascade: The FSA cascade to validate

        Returns:
            Complete validation report with all analysis results

        Raises:
            ValueError: If cascade is invalid
        """
        try:
            self.state = FSAState.RUNNING

            # Perform comprehensive validation
            validation_result = self.validate(cascade)

            # Generate execution plan if validation passed
            execution_plan = None
            if validation_result.is_valid and self.enable_optimization:
                execution_plan = self.optimize_execution_order(cascade)

            # Profile performance
            performance_report = None
            if validation_result.is_valid:
                performance_report = self.profile_performance(cascade)

            self.state = FSAState.COMPLETED

            return ValidationReport(
                validation_result=validation_result,
                execution_plan=execution_plan,
                performance_report=performance_report
            )

        except Exception as e:
            self.state = FSAState.FAILED
            raise ValueError(f"Cascade validation failed: {str(e)}") from e

    def validate(self, cascade: FSACascade) -> ValidationResult:
        """
        Comprehensive cascade validation.

        Args:
            cascade: The FSA cascade to validate

        Returns:
            Validation result with all detected issues
        """
        errors = []
        warnings = []

        # Basic validation
        if not cascade.fsas:
            errors.append("Cascade contains no FSAs")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Build and analyze dependency graph
        dependency_graph = self.analyze_dependencies(cascade.fsas)

        # Detect cycles
        cycles = self.detect_cycles(dependency_graph)
        if cycles:
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {str(cycle)}")

        # Check data flow
        flow_validation = self.check_data_flow(cascade)
        if not flow_validation.is_valid:
            errors.extend(flow_validation.issues)

        # Detect conflicts
        conflicts = self.detect_conflicts(cascade.fsas)
        for conflict in conflicts:
            if conflict.severity == "error":
                errors.append(f"{conflict.type.value} conflict: {conflict.description}")
            else:
                warnings.append(f"{conflict.type.value} conflict: {conflict.description}")

        # Verify integrity
        integrity_report = self.verify_integrity(cascade)
        if not integrity_report.is_consistent:
            errors.extend(integrity_report.issues)

        # Determine overall validity
        is_valid = len(errors) == 0
        if self.strict_mode and warnings:
            is_valid = False
            errors.extend(warnings)
            warnings = []

        return ValidationResult(
            is_valid=is_valid,
            dependency_graph=dependency_graph,
            cycles=cycles,
            conflicts=conflicts,
            flow_validation=flow_validation,
            integrity_report=integrity_report,
            errors=errors,
            warnings=warnings
        )

    def analyze_dependencies(self, fsas: List[FSA]) -> DependencyGraph:
        """
        Build and analyze FSA dependency graph.

        Args:
            fsas: List of FSAs to analyze

        Returns:
            Dependency graph with topological levels
        """
        graph = DependencyGraph()

        # Build graph
        for fsa in fsas:
            graph.nodes.add(fsa.id)
            for dep_id in fsa.dependencies:
                graph.edges[dep_id].append(fsa.id)
                graph.reverse_edges[fsa.id].append(dep_id)

        # Compute topological levels (if acyclic)
        graph.levels = self._compute_topological_levels(graph, fsas)

        return graph

    def _compute_topological_levels(
        self,
        graph: DependencyGraph,
        fsas: List[FSA]
    ) -> List[List[str]]:
        """Compute topological levels for parallel execution."""
        levels = []
        visited = set()

        # Create FSA lookup
        fsa_map = {fsa.id: fsa for fsa in fsas}

        # Find nodes with no dependencies (level 0)
        current_level = [
            fsa.id for fsa in fsas
            if not fsa.dependencies or fsa.id not in graph.nodes
        ]

        while current_level:
            levels.append(current_level)
            visited.update(current_level)

            # Find next level
            next_level = []
            for node in graph.nodes:
                if node in visited:
                    continue

                fsa = fsa_map.get(node)
                if fsa and fsa.can_execute(visited):
                    next_level.append(node)

            current_level = next_level

        return levels

    def check_data_flow(self, cascade: FSACascade) -> FlowValidation:
        """
        Verify input/output data type compatibility across cascade.

        Args:
            cascade: The FSA cascade to check

        Returns:
            Flow validation result with any issues found
        """
        issues = []
        type_mismatches = []
        missing_inputs = []

        # Build output registry
        available_outputs: Dict[str, Dict[str, str]] = {}  # fsa_id -> {output_name -> type}
        for fsa in cascade.fsas:
            available_outputs[fsa.id] = fsa.outputs.copy()

        # Check each FSA's inputs
        for fsa in cascade.fsas:
            for input_name, input_type in fsa.inputs.items():
                # Check if this input is satisfied by dependencies
                input_satisfied = False

                for dep_id in fsa.dependencies:
                    dep_fsa = cascade.get_fsa_by_id(dep_id)
                    if not dep_fsa:
                        continue

                    # Check if dependency provides this input
                    if input_name in dep_fsa.outputs:
                        output_type = dep_fsa.outputs[input_name]
                        if output_type == input_type or self._types_compatible(output_type, input_type):
                            input_satisfied = True
                            break
                        else:
                            type_mismatches.append((dep_id, input_name, fsa.id, input_name))
                            issues.append(
                                f"Type mismatch: {dep_fsa.name}.{input_name} ({output_type}) "
                                f"-> {fsa.name}.{input_name} ({input_type})"
                            )

                # If input not satisfied and FSA has dependencies, it's an issue
                if not input_satisfied and fsa.dependencies:
                    missing_inputs.append((fsa.id, input_name))
                    issues.append(
                        f"Missing input '{input_name}' for FSA '{fsa.name}' "
                        f"(required type: {input_type})"
                    )

        return FlowValidation(
            is_valid=len(issues) == 0,
            issues=issues,
            type_mismatches=type_mismatches,
            missing_inputs=missing_inputs
        )

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two data types are compatible."""
        # Simple compatibility check - can be extended
        if type1 == type2:
            return True

        # Handle Any type
        if type1 == "Any" or type2 == "Any":
            return True

        # Handle subtype relationships (simplified)
        compatible_pairs = [
            ("int", "float"),
            ("str", "text"),
            ("list", "array"),
        ]

        return (type1, type2) in compatible_pairs or (type2, type1) in compatible_pairs

    def detect_conflicts(self, fsas: List[FSA]) -> List[Conflict]:
        """
        Identify competing or incompatible FSAs.

        Args:
            fsas: List of FSAs to check for conflicts

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Check resource conflicts
        resource_usage: Dict[str, List[str]] = defaultdict(list)
        for fsa in fsas:
            for resource_name, resource_value in fsa.resources.items():
                resource_usage[resource_name].append(fsa.id)

        for resource_name, users in resource_usage.items():
            if len(users) > 1:
                # Check if FSAs using same resource can run in parallel
                parallel_users = self._find_parallel_execution(fsas, users)
                if parallel_users:
                    conflicts.append(Conflict(
                        type=ConflictType.RESOURCE,
                        fsa_ids=parallel_users,
                        description=f"Multiple FSAs may compete for resource '{resource_name}'"
                    ))

        # Check priority conflicts
        priority_groups: Dict[int, List[str]] = defaultdict(list)
        for fsa in fsas:
            priority_groups[fsa.priority].append(fsa.id)

        # Check state conflicts
        for i, fsa1 in enumerate(fsas):
            for fsa2 in fsas[i + 1:]:
                if self._have_state_conflict(fsa1, fsa2):
                    conflicts.append(Conflict(
                        type=ConflictType.STATE,
                        fsa_ids=[fsa1.id, fsa2.id],
                        description=f"State conflict between {fsa1.name} and {fsa2.name}",
                        severity="warning"
                    ))

        return conflicts

    def _find_parallel_execution(self, fsas: List[FSA], fsa_ids: List[str]) -> List[str]:
        """Find FSAs that might execute in parallel."""
        fsa_map = {fsa.id: fsa for fsa in fsas}
        parallel = []

        for i, id1 in enumerate(fsa_ids):
            for id2 in fsa_ids[i + 1:]:
                fsa1 = fsa_map.get(id1)
                fsa2 = fsa_map.get(id2)

                if fsa1 and fsa2:
                    # Check if neither depends on the other
                    if (id2 not in fsa1.dependencies and
                        id1 not in fsa2.dependencies):
                        if id1 not in parallel:
                            parallel.append(id1)
                        if id2 not in parallel:
                            parallel.append(id2)

        return parallel

    def _have_state_conflict(self, fsa1: FSA, fsa2: FSA) -> bool:
        """Check if two FSAs have conflicting state requirements."""
        # Check for metadata conflicts
        if "exclusive" in fsa1.metadata and "exclusive" in fsa2.metadata:
            if fsa1.metadata["exclusive"] == fsa2.metadata["exclusive"]:
                return True

        return False

    def optimize_execution_order(self, cascade: FSACascade) -> ExecutionPlan:
        """
        Generate optimal FSA execution sequence.

        Args:
            cascade: The FSA cascade to optimize

        Returns:
            Optimized execution plan with stages
        """
        graph = self.analyze_dependencies(cascade.fsas)

        # Use topological levels as execution stages
        stages = graph.levels

        # Calculate total estimated time (critical path)
        fsa_map = {fsa.id: fsa for fsa in cascade.fsas}
        critical_path, critical_duration = self._find_critical_path(cascade.fsas, graph)

        # Count parallelism opportunities
        parallelism = sum(1 for stage in stages if len(stage) > 1)

        return ExecutionPlan(
            stages=stages,
            total_estimated_time=critical_duration,
            critical_path=critical_path,
            parallelism_opportunities=parallelism
        )

    def _find_critical_path(
        self,
        fsas: List[FSA],
        graph: DependencyGraph
    ) -> Tuple[List[str], float]:
        """Find the critical path (longest path) through the dependency graph."""
        fsa_map = {fsa.id: fsa for fsa in fsas}

        # Calculate longest path to each node
        distances = {fsa.id: 0.0 for fsa in fsas}
        predecessors = {fsa.id: None for fsa in fsas}

        # Process in topological order
        for level in graph.levels:
            for node in level:
                fsa = fsa_map[node]

                # Check all dependencies
                for dep_id in fsa.dependencies:
                    dep_fsa = fsa_map.get(dep_id)
                    if dep_fsa:
                        new_distance = distances[dep_id] + dep_fsa.estimated_duration
                        if new_distance > distances[node]:
                            distances[node] = new_distance
                            predecessors[node] = dep_id

        # Find node with maximum distance
        max_node = max(distances.keys(), key=lambda k: distances[k])
        max_distance = distances[max_node] + fsa_map[max_node].estimated_duration

        # Reconstruct path
        path = []
        current = max_node
        while current is not None:
            path.append(current)
            current = predecessors[current]

        path.reverse()

        return path, max_distance

    def detect_cycles(self, dependency_graph: DependencyGraph) -> List[Cycle]:
        """
        Find circular dependencies in the dependency graph.

        Args:
            dependency_graph: The dependency graph to check

        Returns:
            List of detected cycles
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            """DFS to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependency_graph.edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle_nodes = path[cycle_start:]
                    cycles.append(Cycle(nodes=cycle_nodes))

            rec_stack.remove(node)

        for node in dependency_graph.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles

    def profile_performance(self, cascade: FSACascade) -> PerformanceReport:
        """
        Identify bottlenecks and inefficiencies in cascade.

        Args:
            cascade: The FSA cascade to profile

        Returns:
            Performance report with optimization suggestions
        """
        graph = self.analyze_dependencies(cascade.fsas)
        critical_path, critical_duration = self._find_critical_path(cascade.fsas, graph)

        # Find bottlenecks (FSAs on critical path with long duration)
        fsa_map = {fsa.id: fsa for fsa in cascade.fsas}
        bottlenecks = [
            fsa_id for fsa_id in critical_path
            if fsa_map[fsa_id].estimated_duration > critical_duration * 0.2
        ]

        # Calculate total duration (sum of all)
        total_duration = sum(fsa.estimated_duration for fsa in cascade.fsas)

        # Calculate parallelism score
        parallelism_score = 1.0 - (critical_duration / total_duration) if total_duration > 0 else 0.0

        # Generate optimization suggestions
        suggestions = []
        if parallelism_score < 0.5:
            suggestions.append("Consider breaking down long-running FSAs to increase parallelism")

        if bottlenecks:
            suggestions.append(f"Optimize bottleneck FSAs: {', '.join(fsa_map[b].name for b in bottlenecks)}")

        if len(graph.levels) == len(cascade.fsas):
            suggestions.append("Cascade is fully sequential - look for parallelization opportunities")

        return PerformanceReport(
            bottlenecks=bottlenecks,
            total_estimated_duration=total_duration,
            critical_path_duration=critical_duration,
            parallelism_score=parallelism_score,
            optimization_suggestions=suggestions
        )

    def verify_integrity(self, cascade: FSACascade) -> IntegrityReport:
        """
        Check cascade consistency and integrity.

        Args:
            cascade: The FSA cascade to verify

        Returns:
            Integrity report with any issues found
        """
        issues = []
        orphaned = []
        unreachable = []

        # Check for orphaned FSAs (dependencies not in cascade)
        fsa_ids = {fsa.id for fsa in cascade.fsas}
        for fsa in cascade.fsas:
            for dep_id in fsa.dependencies:
                if dep_id not in fsa_ids:
                    issues.append(f"FSA '{fsa.name}' depends on non-existent FSA '{dep_id}'")
                    if fsa.id not in orphaned:
                        orphaned.append(fsa.id)

        # Check for unreachable FSAs (no path from entry points)
        graph = self.analyze_dependencies(cascade.fsas)
        entry_points = [fsa.id for fsa in cascade.fsas if not fsa.dependencies]

        if entry_points:
            reachable = self._find_reachable(graph, entry_points)
            unreachable = [fsa.id for fsa in cascade.fsas if fsa.id not in reachable]

            if unreachable:
                issues.append(f"Found {len(unreachable)} unreachable FSAs")

        return IntegrityReport(
            is_consistent=len(issues) == 0,
            issues=issues,
            orphaned_fsas=orphaned,
            unreachable_fsas=unreachable
        )

    def _find_reachable(self, graph: DependencyGraph, entry_points: List[str]) -> Set[str]:
        """Find all FSAs reachable from entry points."""
        reachable = set()
        queue = deque(entry_points)

        while queue:
            node = queue.popleft()
            if node in reachable:
                continue

            reachable.add(node)

            # Add all nodes that depend on this one
            for neighbor in graph.edges.get(node, []):
                if neighbor not in reachable:
                    queue.append(neighbor)

        return reachable

    def error_handling(self, error: Exception) -> Dict[str, Any]:
        """
        Robust error recovery for validation failures.

        Args:
            error: The exception that occurred

        Returns:
            Error information and recovery suggestions
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "state": self.state.value,
            "recovery_suggestions": []
        }

        if isinstance(error, ValueError):
            error_info["recovery_suggestions"].append("Check cascade structure and FSA definitions")
        elif isinstance(error, KeyError):
            error_info["recovery_suggestions"].append("Verify all FSA IDs are correctly referenced")
        else:
            error_info["recovery_suggestions"].append("Review cascade configuration and try again")

        self.state = FSAState.FAILED

        return error_info

"""Cascade Validator FSA - Validates FSA cascade integrity and dependency flow."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    CRITICAL = "critical"  # Blocks execution
    WARNING = "warning"  # May cause issues
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the cascade."""

    severity: ValidationSeverity
    message: str
    fsa_id: Optional[str] = None
    affected_fsas: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class FSANode:
    """Represents an FSA node in the cascade."""

    fsa_id: str
    name: str
    dependencies: List[str] = field(default_factory=list)
    inputs: Dict[str, type] = field(default_factory=dict)
    outputs: Dict[str, type] = field(default_factory=dict)
    required_inputs: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.fsa_id)


@dataclass
class ValidationResult:
    """Result of cascade validation."""

    is_valid: bool
    health_score: float
    issues: List[ValidationIssue] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    repair_suggestions: List[str] = field(default_factory=list)

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        """Get all critical issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warnings."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class CascadeValidatorFSA:
    """
    Validates FSA cascade integrity, dependency flow, and execution order.

    Features:
    - Dependency graph validation (cycles, missing deps, orphaned FSAs)
    - Execution order verification (topological sort)
    - Input/output contract validation
    - Health scoring (0-100%)
    - Auto-repair suggestions
    """

    def __init__(self):
        """Initialize the cascade validator."""
        self.fsa_nodes: Dict[str, FSANode] = {}
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.issues: List[ValidationIssue] = []

    def validate_cascade(self, fsa_list: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate the entire FSA cascade.

        Args:
            fsa_list: List of FSA definitions with structure:
                {
                    'fsa_id': str,
                    'name': str,
                    'dependencies': List[str],
                    'inputs': Dict[str, type],
                    'outputs': Dict[str, type],
                    'required_inputs': Set[str],
                    'metadata': Dict[str, Any]
                }

        Returns:
            ValidationResult with complete validation details
        """
        # Reset state
        self.fsa_nodes = {}
        self.dependency_graph = defaultdict(list)
        self.reverse_graph = defaultdict(list)
        self.issues = []

        # Build FSA nodes
        self._build_nodes(fsa_list)

        # Run all validation checks
        self.check_dependencies()
        execution_order = self.verify_execution_order()
        self._validate_contracts()
        self._detect_orphaned_fsas()

        # Calculate health score
        health_score = self.calculate_health_score()

        # Generate repair suggestions
        repair_suggestions = self.suggest_repairs()

        # Determine if cascade is valid
        is_valid = len([i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]) == 0

        return ValidationResult(
            is_valid=is_valid,
            health_score=health_score,
            issues=self.issues.copy(),
            execution_order=execution_order,
            dependency_graph=dict(self.dependency_graph),
            repair_suggestions=repair_suggestions,
        )

    def _build_nodes(self, fsa_list: List[Dict[str, Any]]) -> None:
        """Build FSA nodes and dependency graph from input list."""
        for fsa_def in fsa_list:
            node = FSANode(
                fsa_id=fsa_def.get("fsa_id", ""),
                name=fsa_def.get("name", ""),
                dependencies=fsa_def.get("dependencies", []),
                inputs=fsa_def.get("inputs", {}),
                outputs=fsa_def.get("outputs", {}),
                required_inputs=set(fsa_def.get("required_inputs", [])),
                metadata=fsa_def.get("metadata", {}),
            )

            if not node.fsa_id:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        message="FSA missing required 'fsa_id' field",
                        suggestion="Ensure all FSAs have a unique 'fsa_id' field",
                    )
                )
                continue

            self.fsa_nodes[node.fsa_id] = node

            # Build dependency graphs
            for dep in node.dependencies:
                self.dependency_graph[node.fsa_id].append(dep)
                self.reverse_graph[dep].append(node.fsa_id)

    def check_dependencies(self) -> Dict[str, List[str]]:
        """
        Check for dependency issues: cycles, missing dependencies.

        Returns:
            Dictionary mapping FSA IDs to their dependencies
        """
        # Check for missing dependencies
        for fsa_id, deps in self.dependency_graph.items():
            for dep in deps:
                if dep not in self.fsa_nodes:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Missing dependency: {dep}",
                            fsa_id=fsa_id,
                            affected_fsas=[fsa_id],
                            suggestion=f"Add FSA '{dep}' to the cascade or remove dependency from '{fsa_id}'",
                        )
                    )

        # Check for cycles
        cycles = self._detect_cycles()
        for cycle in cycles:
            cycle_path = " -> ".join(cycle)
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Circular dependency detected: {cycle_path}",
                    affected_fsas=cycle,
                    suggestion=f"Break the cycle by removing one dependency in the chain: {cycle_path}",
                )
            )

        return dict(self.dependency_graph)

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the dependency graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependency_graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for fsa_id in self.fsa_nodes:
            if fsa_id not in visited:
                dfs(fsa_id)

        return cycles

    def verify_execution_order(self) -> List[str]:
        """
        Verify execution order using topological sort.

        Returns:
            List of FSA IDs in valid execution order, or empty list if invalid
        """
        # Check if there are cycles first
        if any(issue.message.startswith("Circular dependency") for issue in self.issues):
            return []

        # Kahn's algorithm for topological sort
        in_degree = {fsa_id: 0 for fsa_id in self.fsa_nodes}
        for fsa_id in self.fsa_nodes:
            for dep in self.dependency_graph.get(fsa_id, []):
                if dep in in_degree:  # Only count valid dependencies
                    in_degree[fsa_id] += 1

        queue = deque([fsa_id for fsa_id, degree in in_degree.items() if degree == 0])
        execution_order = []

        while queue:
            current = queue.popleft()
            execution_order.append(current)

            # Reduce in-degree for dependent FSAs
            for dependent in self.reverse_graph.get(current, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # If not all nodes are in execution order, there's an issue
        if len(execution_order) != len(self.fsa_nodes):
            missing = set(self.fsa_nodes.keys()) - set(execution_order)
            self.issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Unable to determine execution order for some FSAs: {missing}",
                    affected_fsas=list(missing),
                    suggestion="Check for unresolved dependency issues",
                )
            )

        return execution_order

    def _validate_contracts(self) -> None:
        """Validate input/output contracts between dependent FSAs."""
        for fsa_id, node in self.fsa_nodes.items():
            # Check if required inputs can be satisfied
            for required_input in node.required_inputs:
                if required_input not in node.inputs:
                    self.issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Required input '{required_input}' not defined in inputs",
                            fsa_id=fsa_id,
                            suggestion=f"Add '{required_input}' to the inputs definition of '{fsa_id}'",
                        )
                    )

            # Validate type compatibility with dependencies
            for dep_id in node.dependencies:
                if dep_id not in self.fsa_nodes:
                    continue  # Already flagged as missing dependency

                dep_node = self.fsa_nodes[dep_id]

                # Check if outputs from dependency match inputs needed
                for input_name, input_type in node.inputs.items():
                    if input_name in dep_node.outputs:
                        output_type = dep_node.outputs[input_name]
                        if output_type != input_type and output_type != Any and input_type != Any:
                            self.issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Type mismatch: {dep_id}.{input_name} ({output_type.__name__}) "
                                    f"-> {fsa_id}.{input_name} ({input_type.__name__})",
                                    fsa_id=fsa_id,
                                    affected_fsas=[dep_id, fsa_id],
                                    suggestion=f"Ensure type consistency or add type conversion between "
                                    f"'{dep_id}' and '{fsa_id}'",
                                )
                            )

    def _detect_orphaned_fsas(self) -> None:
        """Detect orphaned FSAs with no incoming or outgoing dependencies."""
        for fsa_id, node in self.fsa_nodes.items():
            has_dependencies = len(node.dependencies) > 0
            has_dependents = len(self.reverse_graph.get(fsa_id, [])) > 0

            if not has_dependencies and not has_dependents and len(self.fsa_nodes) > 1:
                self.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        message=f"Orphaned FSA detected: {fsa_id} (no dependencies or dependents)",
                        fsa_id=fsa_id,
                        suggestion=f"Consider connecting '{fsa_id}' to other FSAs or removing it from the cascade",
                    )
                )

    def calculate_health_score(self) -> float:
        """
        Calculate cascade health score (0-100%).

        Scoring:
        - Start at 100%
        - Deduct points for each issue based on severity
        - Critical: -20 points each
        - Warning: -10 points each
        - Info: -5 points each
        """
        if not self.fsa_nodes:
            return 0.0

        score = 100.0

        for issue in self.issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 20.0
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 10.0
            elif issue.severity == ValidationSeverity.INFO:
                score -= 5.0

        return max(0.0, min(100.0, score))

    def suggest_repairs(self) -> List[str]:
        """
        Generate auto-repair suggestions for broken cascades.

        Returns:
            List of actionable repair suggestions
        """
        suggestions = []

        # Collect unique suggestions from issues
        seen_suggestions = set()
        for issue in self.issues:
            if issue.suggestion and issue.suggestion not in seen_suggestions:
                suggestions.append(issue.suggestion)
                seen_suggestions.add(issue.suggestion)

        # Add general suggestions based on issue patterns
        if any(i.message.startswith("Circular dependency") for i in self.issues):
            suggestions.append("General: Review cascade architecture to eliminate circular dependencies")

        if any(i.message.startswith("Missing dependency") for i in self.issues):
            suggestions.append("General: Ensure all required FSAs are included in the cascade")

        if any(i.message.startswith("Type mismatch") for i in self.issues):
            suggestions.append("General: Add type conversion layers between incompatible FSAs")

        orphaned_count = len([i for i in self.issues if "Orphaned FSA" in i.message])
        if orphaned_count > 0:
            suggestions.append(f"General: Review {orphaned_count} orphaned FSA(s) for integration or removal")

        return suggestions

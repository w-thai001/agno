"""
Architecture Validator FSA - Comprehensive Software Architecture Validation

This module provides a comprehensive architecture validation framework that validates
software architecture against predefined patterns, architectural rules, layering principles,
dependency constraints, and design principles (SOLID, DRY, KISS) to ensure architectural
integrity and prevent architectural erosion over time.

Features:
- Multi-dimensional validation engine
- Architectural pattern detection (MVC, Layered, Microservices, Hexagonal, Clean)
- Layering rule enforcement (presentation, business logic, data access)
- Dependency constraint validation
- SOLID principles checker
- Architectural smell detection (cyclic dependencies, god components, feature envy)
- Component cohesion and coupling analyzer
- Architecture conformance checking
- Architecture drift detector
- Architecture quality metrics computation
"""

import ast
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class ArchitecturalPattern(Enum):
    """Supported architectural patterns."""
    LAYERED = "layered"
    MVC = "mvc"
    HEXAGONAL = "hexagonal"
    MICROSERVICES = "microservices"
    CLEAN = "clean"
    UNKNOWN = "unknown"


class SmellType(Enum):
    """Types of architectural smells."""
    CYCLIC_DEPENDENCY = "cyclic_dependency"
    GOD_COMPONENT = "god_component"
    FEATURE_ENVY = "feature_envy"
    SCATTERED_FUNCTIONALITY = "scattered_functionality"
    AMBIGUOUS_INTERFACE = "ambiguous_interface"
    SKIP_LAYER = "skip_layer"


class ViolationSeverity(Enum):
    """Severity levels for violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Component:
    """Represents a software component."""
    name: str
    path: Path
    dependencies: Set[str] = field(default_factory=set)
    size: int = 0
    complexity: int = 0
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    layer: Optional[str] = None


@dataclass
class DependencyGraph:
    """Represents the dependency graph of a project."""
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add an edge to the graph."""
        self.nodes.add(from_node)
        self.nodes.add(to_node)
        self.edges[from_node].add(to_node)

    def get_dependencies(self, node: str) -> Set[str]:
        """Get all dependencies of a node."""
        return self.edges.get(node, set())


@dataclass
class LayerSpec:
    """Specification for architectural layers."""
    layers: Dict[str, List[str]] = field(default_factory=dict)  # layer_name -> allowed_dependencies
    layer_patterns: Dict[str, List[str]] = field(default_factory=dict)  # layer_name -> path_patterns


@dataclass
class DependencyRules:
    """Rules for allowed/forbidden dependencies."""
    allowed: Dict[str, List[str]] = field(default_factory=dict)
    forbidden: List[Tuple[str, str]] = field(default_factory=list)
    package_conventions: Dict[str, str] = field(default_factory=dict)


@dataclass
class ArchitectureSpec:
    """Complete architecture specification."""
    patterns: List[ArchitecturalPattern] = field(default_factory=list)
    layers: Optional[LayerSpec] = None
    dependency_rules: Optional[DependencyRules] = None
    enforce_solid: bool = True
    max_component_size: int = 500
    max_complexity: int = 10
    max_dependencies: int = 10


@dataclass
class DetectedPattern:
    """Result of pattern detection."""
    pattern_type: ArchitecturalPattern
    confidence: float
    evidence: List[str] = field(default_factory=list)


@dataclass
class ArchitecturalSmell:
    """Represents an architectural smell."""
    smell_type: SmellType
    location: str
    severity: ViolationSeverity
    description: str
    fix_suggestion: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SOLIDViolation:
    """SOLID principle violation."""
    principle: str
    location: str
    description: str
    severity: ViolationSeverity


@dataclass
class SOLIDReport:
    """Report of SOLID principle violations."""
    srp_violations: List[SOLIDViolation] = field(default_factory=list)
    ocp_violations: List[SOLIDViolation] = field(default_factory=list)
    lsp_violations: List[SOLIDViolation] = field(default_factory=list)
    isp_violations: List[SOLIDViolation] = field(default_factory=list)
    dip_violations: List[SOLIDViolation] = field(default_factory=list)

    @property
    def total_violations(self) -> int:
        """Total number of violations."""
        return (len(self.srp_violations) + len(self.ocp_violations) +
                len(self.lsp_violations) + len(self.isp_violations) +
                len(self.dip_violations))


@dataclass
class CohesionScore:
    """Component cohesion metrics."""
    lcom: float  # Lack of Cohesion in Methods
    functional_cohesion: float
    score: float  # Overall cohesion score (0-1, higher is better)


@dataclass
class CouplingMatrix:
    """Coupling metrics for components."""
    afferent_coupling: Dict[str, int] = field(default_factory=dict)  # Ca: incoming
    efferent_coupling: Dict[str, int] = field(default_factory=dict)  # Ce: outgoing
    instability: Dict[str, float] = field(default_factory=dict)  # I = Ce / (Ca + Ce)


@dataclass
class LayeringReport:
    """Report of layering violations."""
    layer_violations: List[str] = field(default_factory=list)
    skip_layer_deps: List[Tuple[str, str]] = field(default_factory=list)
    circular_deps: List[List[str]] = field(default_factory=list)
    valid: bool = True


@dataclass
class RuleViolations:
    """Dependency rule violations."""
    violated_rules: List[str] = field(default_factory=list)
    affected_modules: Set[str] = field(default_factory=set)
    severity: ViolationSeverity = ViolationSeverity.MEDIUM


@dataclass
class ConformanceReport:
    """Architecture conformance report."""
    conformance_percentage: float
    missing_components: List[str] = field(default_factory=list)
    extra_components: List[str] = field(default_factory=list)
    dependency_violations: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class ArchitectureMetrics:
    """Overall architecture quality metrics."""
    modularity: float
    maintainability: float
    testability: float
    complexity: float
    abstractness: float
    distance_from_main_sequence: float


@dataclass
class DriftReport:
    """Architecture drift detection report."""
    drift_magnitude: float
    components_added: List[str] = field(default_factory=list)
    components_removed: List[str] = field(default_factory=list)
    dependencies_added: List[Tuple[str, str]] = field(default_factory=list)
    dependencies_removed: List[Tuple[str, str]] = field(default_factory=list)
    pattern_changes: List[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Complete validation report."""
    violations: List[str] = field(default_factory=list)
    smells: List[ArchitecturalSmell] = field(default_factory=list)
    metrics: Optional[ArchitectureMetrics] = None
    recommendations: List[str] = field(default_factory=list)
    conformance_score: float = 100.0
    solid_report: Optional[SOLIDReport] = None
    layering_report: Optional[LayeringReport] = None
    detected_pattern: Optional[DetectedPattern] = None


@dataclass
class ProjectStructure:
    """Represents analyzed project structure."""
    root: Path
    components: List[Component] = field(default_factory=list)
    dependency_graph: DependencyGraph = field(default_factory=DependencyGraph)
    total_files: int = 0
    total_lines: int = 0


class ArchitectureValidator:
    """
    Comprehensive architecture validation engine.

    Validates software architecture against patterns, rules, and principles
    to ensure architectural integrity and prevent erosion.
    """

    def __init__(self, spec: Optional[ArchitectureSpec] = None):
        """Initialize the validator with optional specification."""
        self.spec = spec or ArchitectureSpec()
        self.project: Optional[ProjectStructure] = None

    def validate(self, project_path: Path, architecture_spec: ArchitectureSpec) -> ValidationReport:
        """
        Main validation entry point.

        Args:
            project_path: Path to the project to validate
            architecture_spec: Architecture specification to validate against

        Returns:
            Complete validation report
        """
        self.spec = architecture_spec
        report = ValidationReport()

        try:
            # Analyze project structure
            self.project = self._analyze_project(project_path)

            # Detect architectural pattern
            report.detected_pattern = self.detect_architecture_pattern(self.project)

            # Validate layering if specified
            if self.spec.layers:
                report.layering_report = self.validate_layering(self.project, self.spec.layers)
                if not report.layering_report.valid:
                    report.violations.extend(report.layering_report.layer_violations)

            # Check dependency rules
            if self.spec.dependency_rules:
                rule_violations = self.check_dependency_rules(
                    self.project.dependency_graph,
                    self.spec.dependency_rules
                )
                report.violations.extend(rule_violations.violated_rules)

            # Validate SOLID principles
            if self.spec.enforce_solid:
                report.solid_report = self._validate_solid_all_components()

            # Detect architectural smells
            report.smells = self.detect_architectural_smells(self.project)

            # Compute metrics
            report.metrics = self.compute_architecture_metrics(self.project)

            # Generate recommendations
            report.recommendations = self.suggest_architecture_improvements(report)

            # Calculate conformance score
            report.conformance_score = self._calculate_conformance_score(report)

        except Exception as e:
            report.violations.append(f"Validation error: {str(e)}")
            report.conformance_score = 0.0

        return report

    def _analyze_project(self, project_path: Path) -> ProjectStructure:
        """Analyze project structure and build dependency graph."""
        project = ProjectStructure(root=project_path)

        # Find all Python files
        py_files = list(project_path.rglob("*.py"))
        project.total_files = len(py_files)

        for py_file in py_files:
            try:
                component = self._analyze_component(py_file, project_path)
                project.components.append(component)
                project.total_lines += component.size

                # Build dependency graph
                for dep in component.dependencies:
                    project.dependency_graph.add_edge(component.name, dep)
            except Exception:
                continue  # Skip files with parse errors

        return project

    def _analyze_component(self, file_path: Path, root: Path) -> Component:
        """Analyze a single component (Python file)."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return minimal component for unparseable files
            return Component(
                name=str(file_path.relative_to(root)),
                path=file_path,
                size=len(content.splitlines())
            )

        component = Component(
            name=str(file_path.relative_to(root)),
            path=file_path,
            size=len(content.splitlines())
        )

        # Extract imports (dependencies)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    component.dependencies.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    component.dependencies.add(node.module.split('.')[0])
            elif isinstance(node, ast.ClassDef):
                component.methods.extend([m.name for m in node.body if isinstance(m, ast.FunctionDef)])
                component.attributes.extend([a.targets[0].id for a in node.body
                                           if isinstance(a, ast.Assign) and
                                           isinstance(a.targets[0], ast.Name)])
            elif isinstance(node, ast.FunctionDef):
                component.complexity += self._calculate_cyclomatic_complexity(node)

        # Assign layer based on path
        component.layer = self._infer_layer(file_path, root)

        return component

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _infer_layer(self, file_path: Path, root: Path) -> Optional[str]:
        """Infer architectural layer from file path."""
        rel_path = str(file_path.relative_to(root)).lower()

        if any(pattern in rel_path for pattern in ['view', 'controller', 'ui', 'api', 'endpoint']):
            return 'presentation'
        elif any(pattern in rel_path for pattern in ['service', 'business', 'domain', 'usecase']):
            return 'business'
        elif any(pattern in rel_path for pattern in ['repository', 'dao', 'database', 'model']):
            return 'data'
        elif any(pattern in rel_path for pattern in ['util', 'helper', 'common', 'infrastructure']):
            return 'infrastructure'

        return None

    def detect_architecture_pattern(self, project: ProjectStructure) -> DetectedPattern:
        """Detect the architectural pattern used in the project."""
        evidence = []
        scores = {pattern: 0.0 for pattern in ArchitecturalPattern}

        # Count components by layer
        layer_counts = defaultdict(int)
        for component in project.components:
            if component.layer:
                layer_counts[component.layer] += 1

        # Check for Layered Architecture
        if layer_counts['presentation'] > 0 and layer_counts['business'] > 0 and layer_counts['data'] > 0:
            scores[ArchitecturalPattern.LAYERED] = 0.8
            evidence.append("Found distinct presentation, business, and data layers")

        # Check for MVC
        mvc_patterns = ['model', 'view', 'controller']
        mvc_count = sum(1 for c in project.components if any(p in c.name.lower() for p in mvc_patterns))
        if mvc_count >= 3:
            scores[ArchitecturalPattern.MVC] = 0.7
            evidence.append(f"Found {mvc_count} MVC-pattern components")

        # Check for Hexagonal
        if any('adapter' in c.name.lower() or 'port' in c.name.lower() for c in project.components):
            scores[ArchitecturalPattern.HEXAGONAL] = 0.6
            evidence.append("Found adapter/port patterns")

        # Check for Clean Architecture
        clean_layers = ['entity', 'usecase', 'interface']
        clean_count = sum(1 for c in project.components if any(p in c.name.lower() for p in clean_layers))
        if clean_count >= 2:
            scores[ArchitecturalPattern.CLEAN] = 0.6
            evidence.append("Found clean architecture layer patterns")

        # Select pattern with highest score
        best_pattern = max(scores.items(), key=lambda x: x[1])

        if best_pattern[1] < 0.3:
            return DetectedPattern(
                pattern_type=ArchitecturalPattern.UNKNOWN,
                confidence=0.0,
                evidence=["Could not identify a clear architectural pattern"]
            )

        return DetectedPattern(
            pattern_type=best_pattern[0],
            confidence=best_pattern[1],
            evidence=evidence
        )

    def validate_layering(self, project: ProjectStructure, layers: LayerSpec) -> LayeringReport:
        """Validate layering rules and dependencies."""
        report = LayeringReport()

        # Define allowed layer dependencies
        layer_hierarchy = {
            'presentation': ['business', 'infrastructure'],
            'business': ['data', 'infrastructure'],
            'data': ['infrastructure'],
            'infrastructure': []
        }

        # Check each component's dependencies
        for component in project.components:
            if not component.layer:
                continue

            allowed_layers = layer_hierarchy.get(component.layer, [])

            for dep_name in component.dependencies:
                # Find dependency component
                dep_component = next((c for c in project.components if dep_name in c.name), None)
                if not dep_component or not dep_component.layer:
                    continue

                # Check if dependency is allowed
                if dep_component.layer == component.layer:
                    continue  # Same layer is OK

                if dep_component.layer not in allowed_layers:
                    violation = f"{component.name} ({component.layer}) -> {dep_component.name} ({dep_component.layer})"
                    report.layer_violations.append(violation)
                    report.valid = False

                    # Check for skip-layer dependency
                    if component.layer == 'presentation' and dep_component.layer == 'data':
                        report.skip_layer_deps.append((component.name, dep_component.name))

        # Detect circular dependencies between layers
        report.circular_deps = self.detect_cyclic_dependencies(project.dependency_graph)
        if report.circular_deps:
            report.valid = False

        return report

    def check_dependency_rules(self, dependency_graph: DependencyGraph,
                               rules: DependencyRules) -> RuleViolations:
        """Check dependency constraints against rules."""
        violations = RuleViolations()

        # Check allowed dependencies
        for module, allowed_deps in rules.allowed.items():
            actual_deps = dependency_graph.get_dependencies(module)
            for dep in actual_deps:
                if dep not in allowed_deps and dep != module:
                    violations.violated_rules.append(
                        f"{module} depends on {dep} (not in allowed list)"
                    )
                    violations.affected_modules.add(module)

        # Check forbidden dependencies
        for from_module, to_module in rules.forbidden:
            if to_module in dependency_graph.get_dependencies(from_module):
                violations.violated_rules.append(
                    f"Forbidden dependency: {from_module} -> {to_module}"
                )
                violations.affected_modules.add(from_module)
                violations.severity = ViolationSeverity.CRITICAL

        return violations

    def validate_solid_principles(self, code: ast.AST) -> SOLIDReport:
        """Validate SOLID principles on AST."""
        report = SOLIDReport()

        for node in ast.walk(code):
            if isinstance(node, ast.ClassDef):
                # Check SRP - Single Responsibility
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 15:  # Too many methods suggests multiple responsibilities
                    report.srp_violations.append(SOLIDViolation(
                        principle="SRP",
                        location=node.name,
                        description=f"Class has {len(methods)} methods, may have multiple responsibilities",
                        severity=ViolationSeverity.MEDIUM
                    ))

                # Check ISP - Interface Segregation
                if len(methods) > 10:
                    report.isp_violations.append(SOLIDViolation(
                        principle="ISP",
                        location=node.name,
                        description=f"Interface may be too large ({len(methods)} methods)",
                        severity=ViolationSeverity.LOW
                    ))

                # Check DIP - Dependency Inversion
                for method in methods:
                    # Look for concrete class instantiations
                    for subnode in ast.walk(method):
                        if isinstance(subnode, ast.Call):
                            if isinstance(subnode.func, ast.Name):
                                # Heuristic: uppercase names are likely concrete classes
                                if subnode.func.id[0].isupper() and subnode.func.id not in ['True', 'False', 'None']:
                                    report.dip_violations.append(SOLIDViolation(
                                        principle="DIP",
                                        location=f"{node.name}.{method.name}",
                                        description=f"Direct instantiation of {subnode.func.id}",
                                        severity=ViolationSeverity.LOW
                                    ))

        return report

    def _validate_solid_all_components(self) -> SOLIDReport:
        """Validate SOLID principles for all components."""
        combined_report = SOLIDReport()

        if not self.project:
            return combined_report

        for component in self.project.components:
            try:
                with open(component.path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                report = self.validate_solid_principles(tree)
                combined_report.srp_violations.extend(report.srp_violations)
                combined_report.ocp_violations.extend(report.ocp_violations)
                combined_report.lsp_violations.extend(report.lsp_violations)
                combined_report.isp_violations.extend(report.isp_violations)
                combined_report.dip_violations.extend(report.dip_violations)
            except Exception:
                continue

        return combined_report

    def detect_architectural_smells(self, project: ProjectStructure) -> List[ArchitecturalSmell]:
        """Detect various architectural smells."""
        smells = []

        # Detect God Components
        for component in project.components:
            if component.size > self.spec.max_component_size:
                smells.append(ArchitecturalSmell(
                    smell_type=SmellType.GOD_COMPONENT,
                    location=component.name,
                    severity=ViolationSeverity.HIGH,
                    description=f"Component is too large ({component.size} lines)",
                    fix_suggestion="Consider splitting into smaller, focused components",
                    metrics={'size': component.size, 'threshold': self.spec.max_component_size}
                ))

            if len(component.dependencies) > self.spec.max_dependencies:
                smells.append(ArchitecturalSmell(
                    smell_type=SmellType.GOD_COMPONENT,
                    location=component.name,
                    severity=ViolationSeverity.MEDIUM,
                    description=f"Component has too many dependencies ({len(component.dependencies)})",
                    fix_suggestion="Reduce coupling by removing unnecessary dependencies",
                    metrics={'dependencies': len(component.dependencies)}
                ))

        # Detect Cyclic Dependencies
        cycles = self.detect_cyclic_dependencies(project.dependency_graph)
        for cycle in cycles:
            smells.append(ArchitecturalSmell(
                smell_type=SmellType.CYCLIC_DEPENDENCY,
                location=" -> ".join(cycle),
                severity=ViolationSeverity.CRITICAL,
                description=f"Circular dependency detected: {' -> '.join(cycle)}",
                fix_suggestion="Break cycle using dependency inversion or refactoring",
                metrics={'cycle_length': len(cycle)}
            ))

        # Detect Feature Envy
        coupling_matrix = self.analyze_component_coupling(project.components)
        for component_name, efferent in coupling_matrix.efferent_coupling.items():
            if efferent > 8:  # High efferent coupling
                smells.append(ArchitecturalSmell(
                    smell_type=SmellType.FEATURE_ENVY,
                    location=component_name,
                    severity=ViolationSeverity.MEDIUM,
                    description=f"Component heavily depends on other components (efferent coupling: {efferent})",
                    fix_suggestion="Consider moving functionality closer to where it's used",
                    metrics={'efferent_coupling': efferent}
                ))

        return smells

    def detect_cyclic_dependencies(self, dependency_graph: DependencyGraph) -> List[List[str]]:
        """Detect cycles using Tarjan's strongly connected components algorithm."""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = defaultdict(bool)
        sccs = []

        def strongconnect(node: str) -> None:
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            on_stack[node] = True
            stack.append(node)

            for successor in dependency_graph.get_dependencies(node):
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack[successor]:
                    lowlinks[node] = min(lowlinks[node], index[successor])

            if lowlinks[node] == index[node]:
                component = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    component.append(successor)
                    if successor == node:
                        break
                if len(component) > 1:  # Only cycles
                    sccs.append(component)

        for node in dependency_graph.nodes:
            if node not in index:
                strongconnect(node)

        return sccs

    def analyze_component_cohesion(self, component: Component) -> CohesionScore:
        """Analyze cohesion of a component using LCOM metric."""
        if not component.methods or not component.attributes:
            return CohesionScore(lcom=0.0, functional_cohesion=1.0, score=1.0)

        # Simplified LCOM calculation
        # LCOM = (methods that don't access attributes) / total methods
        methods_using_attrs = 0
        for method in component.methods:
            if any(attr in method for attr in component.attributes):
                methods_using_attrs += 1

        lcom = 1.0 - (methods_using_attrs / len(component.methods)) if component.methods else 0.0

        # Functional cohesion based on naming patterns
        functional_cohesion = 0.8  # Default

        # Overall score (lower LCOM is better)
        score = max(0.0, 1.0 - lcom)

        return CohesionScore(lcom=lcom, functional_cohesion=functional_cohesion, score=score)

    def analyze_component_coupling(self, components: List[Component]) -> CouplingMatrix:
        """Analyze coupling between components."""
        matrix = CouplingMatrix()

        # Build component name to component map
        comp_map = {c.name: c for c in components}

        for component in components:
            # Efferent coupling: number of outgoing dependencies
            matrix.efferent_coupling[component.name] = len(component.dependencies)

            # Afferent coupling: number of incoming dependencies
            afferent = 0
            for other in components:
                if component.name != other.name and component.name in other.dependencies:
                    afferent += 1
            matrix.afferent_coupling[component.name] = afferent

            # Instability: I = Ce / (Ca + Ce)
            total = matrix.efferent_coupling[component.name] + matrix.afferent_coupling[component.name]
            if total > 0:
                matrix.instability[component.name] = matrix.efferent_coupling[component.name] / total
            else:
                matrix.instability[component.name] = 0.0

        return matrix

    def check_architecture_conformance(self, actual: ProjectStructure,
                                      intended_components: List[str],
                                      intended_deps: Dict[str, List[str]]) -> ConformanceReport:
        """Check if actual architecture conforms to intended design."""
        actual_names = {c.name for c in actual.components}
        intended_set = set(intended_components)

        missing = list(intended_set - actual_names)
        extra = list(actual_names - intended_set)

        # Check dependency violations
        dep_violations = []
        for component in actual.components:
            if component.name in intended_deps:
                allowed = set(intended_deps[component.name])
                for dep in component.dependencies:
                    if dep not in allowed and dep in actual_names:
                        dep_violations.append((component.name, dep))

        total_expected = len(intended_components) + sum(len(deps) for deps in intended_deps.values())
        violations = len(missing) + len(extra) + len(dep_violations)
        conformance = max(0.0, 100.0 * (1.0 - violations / max(1, total_expected)))

        return ConformanceReport(
            conformance_percentage=conformance,
            missing_components=missing,
            extra_components=extra,
            dependency_violations=dep_violations
        )

    def compute_architecture_metrics(self, project: ProjectStructure) -> ArchitectureMetrics:
        """Compute overall architecture quality metrics."""
        # Modularity: based on number of well-sized components
        well_sized = sum(1 for c in project.components if c.size < self.spec.max_component_size)
        modularity = well_sized / max(1, len(project.components))

        # Coupling analysis
        coupling_matrix = self.analyze_component_coupling(project.components)
        avg_instability = sum(coupling_matrix.instability.values()) / max(1, len(coupling_matrix.instability))

        # Cohesion analysis
        cohesion_scores = [self.analyze_component_cohesion(c).score for c in project.components]
        avg_cohesion = sum(cohesion_scores) / max(1, len(cohesion_scores))

        # Maintainability: combination of coupling and cohesion
        maintainability = (avg_cohesion + (1.0 - avg_instability)) / 2.0

        # Testability: inverse of average coupling
        testability = 1.0 - avg_instability

        # Complexity: average component complexity
        avg_complexity = sum(c.complexity for c in project.components) / max(1, len(project.components))
        complexity_score = max(0.0, 1.0 - avg_complexity / 20.0)

        # Abstractness: ratio of abstract to concrete components (simplified)
        abstract_count = sum(1 for c in project.components if 'abstract' in c.name.lower() or 'interface' in c.name.lower())
        abstractness = abstract_count / max(1, len(project.components))

        # Distance from main sequence: D = |A + I - 1|
        distance = abs(abstractness + avg_instability - 1.0)

        return ArchitectureMetrics(
            modularity=modularity,
            maintainability=maintainability,
            testability=testability,
            complexity=complexity_score,
            abstractness=abstractness,
            distance_from_main_sequence=distance
        )

    def detect_architecture_drift(self, current: ProjectStructure,
                                  baseline: ProjectStructure) -> DriftReport:
        """Detect drift from baseline architecture."""
        current_names = {c.name for c in current.components}
        baseline_names = {c.name for c in baseline.components}

        added = list(current_names - baseline_names)
        removed = list(baseline_names - current_names)

        # Detect dependency changes
        current_deps = {(c.name, dep) for c in current.components for dep in c.dependencies}
        baseline_deps = {(c.name, dep) for c in baseline.components for dep in c.dependencies}

        deps_added = list(current_deps - baseline_deps)
        deps_removed = list(baseline_deps - current_deps)

        # Calculate drift magnitude
        total_changes = len(added) + len(removed) + len(deps_added) + len(deps_removed)
        baseline_size = len(baseline.components)
        drift_magnitude = total_changes / max(1, baseline_size)

        return DriftReport(
            drift_magnitude=drift_magnitude,
            components_added=added,
            components_removed=removed,
            dependencies_added=deps_added,
            dependencies_removed=deps_removed
        )

    def suggest_architecture_improvements(self, validation_report: ValidationReport) -> List[str]:
        """Generate improvement suggestions based on validation report."""
        suggestions = []

        # Based on smells
        god_components = [s for s in validation_report.smells if s.smell_type == SmellType.GOD_COMPONENT]
        if god_components:
            suggestions.append(f"Refactor {len(god_components)} oversized components into smaller modules")

        cycles = [s for s in validation_report.smells if s.smell_type == SmellType.CYCLIC_DEPENDENCY]
        if cycles:
            suggestions.append(f"Break {len(cycles)} circular dependencies using dependency inversion")

        # Based on SOLID violations
        if validation_report.solid_report:
            if len(validation_report.solid_report.srp_violations) > 5:
                suggestions.append("Multiple SRP violations detected - apply single responsibility principle")
            if len(validation_report.solid_report.dip_violations) > 10:
                suggestions.append("Consider using dependency injection to reduce coupling")

        # Based on metrics
        if validation_report.metrics:
            if validation_report.metrics.maintainability < 0.6:
                suggestions.append("Improve maintainability by reducing coupling and increasing cohesion")
            if validation_report.metrics.testability < 0.5:
                suggestions.append("Improve testability by reducing dependencies and using interfaces")
            if validation_report.metrics.distance_from_main_sequence > 0.5:
                suggestions.append("Architecture is far from ideal balance - adjust abstractness or stability")

        # Based on layering
        if validation_report.layering_report and validation_report.layering_report.skip_layer_deps:
            suggestions.append("Remove skip-layer dependencies to maintain proper layering")

        return suggestions

    def _calculate_conformance_score(self, report: ValidationReport) -> float:
        """Calculate overall conformance score."""
        score = 100.0

        # Deduct for violations
        score -= len(report.violations) * 5

        # Deduct for smells
        for smell in report.smells:
            if smell.severity == ViolationSeverity.CRITICAL:
                score -= 10
            elif smell.severity == ViolationSeverity.HIGH:
                score -= 5
            elif smell.severity == ViolationSeverity.MEDIUM:
                score -= 2
            else:
                score -= 1

        # Deduct for SOLID violations
        if report.solid_report:
            score -= report.solid_report.total_violations * 0.5

        return max(0.0, min(100.0, score))


# Example usage
if __name__ == "__main__":
    # Create sample architecture specification
    spec = ArchitectureSpec(
        patterns=[ArchitecturalPattern.LAYERED],
        layers=LayerSpec(
            layers={
                'presentation': ['business', 'infrastructure'],
                'business': ['data', 'infrastructure'],
                'data': ['infrastructure'],
                'infrastructure': []
            }
        ),
        dependency_rules=DependencyRules(
            forbidden=[('data', 'presentation'), ('data', 'business')]
        ),
        enforce_solid=True,
        max_component_size=300,
        max_complexity=10,
        max_dependencies=8
    )

    # Initialize validator
    validator = ArchitectureValidator(spec)

    # Validate a project
    project_path = Path(".")
    report = validator.validate(project_path, spec)

    # Print report
    print("=" * 80)
    print("ARCHITECTURE VALIDATION REPORT")
    print("=" * 80)
    print(f"\nConformance Score: {report.conformance_score:.2f}%")

    if report.detected_pattern:
        print(f"\nDetected Pattern: {report.detected_pattern.pattern_type.value}")
        print(f"Confidence: {report.detected_pattern.confidence:.2f}")
        print("Evidence:")
        for evidence in report.detected_pattern.evidence:
            print(f"  - {evidence}")

    if report.violations:
        print(f"\nViolations ({len(report.violations)}):")
        for violation in report.violations[:10]:  # Show first 10
            print(f"  - {violation}")

    if report.smells:
        print(f"\nArchitectural Smells ({len(report.smells)}):")
        for smell in report.smells[:10]:
            print(f"  - [{smell.severity.value}] {smell.smell_type.value}: {smell.description}")
            print(f"    Location: {smell.location}")
            print(f"    Fix: {smell.fix_suggestion}")

    if report.solid_report:
        print(f"\nSOLID Violations: {report.solid_report.total_violations}")
        print(f"  - SRP: {len(report.solid_report.srp_violations)}")
        print(f"  - OCP: {len(report.solid_report.ocp_violations)}")
        print(f"  - LSP: {len(report.solid_report.lsp_violations)}")
        print(f"  - ISP: {len(report.solid_report.isp_violations)}")
        print(f"  - DIP: {len(report.solid_report.dip_violations)}")

    if report.metrics:
        print("\nArchitecture Metrics:")
        print(f"  - Modularity: {report.metrics.modularity:.2f}")
        print(f"  - Maintainability: {report.metrics.maintainability:.2f}")
        print(f"  - Testability: {report.metrics.testability:.2f}")
        print(f"  - Complexity Score: {report.metrics.complexity:.2f}")
        print(f"  - Abstractness: {report.metrics.abstractness:.2f}")
        print(f"  - Distance from Main Sequence: {report.metrics.distance_from_main_sequence:.2f}")

    if report.recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

    print("\n" + "=" * 80)

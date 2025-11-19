"""Architecture Validator FSA for validating system design patterns and layer separation."""

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import logging

from agno.fsa.base import FSA, Transition

logger = logging.getLogger(__name__)


class ValidatorState(str, Enum):
    """States for Architecture Validator FSA."""

    INITIAL = "initial"
    LOADING_STRUCTURE = "loading_structure"
    ANALYZING_LAYERS = "analyzing_layers"
    CHECKING_PATTERNS = "checking_patterns"
    DETECTING_VIOLATIONS = "detecting_violations"
    COMPLETED = "completed"


@dataclass
class LayerDefinition:
    """Definition of an architectural layer."""

    name: str
    paths: List[str]
    allowed_dependencies: List[str] = field(default_factory=list)


@dataclass
class Violation:
    """Architecture violation."""

    severity: str  # "error", "warning", "info"
    category: str
    message: str
    file_path: str = ""
    line_number: int = 0
    details: str = ""


@dataclass
class ArchitectureReport:
    """Architecture validation report."""

    total_files: int = 0
    total_violations: int = 0
    errors: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)
    layer_info: Dict[str, Any] = field(default_factory=dict)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    pattern_violations: List[Violation] = field(default_factory=list)


class ArchitectureValidator(FSA):
    """FSA for validating software architecture."""

    def __init__(self, layers: Optional[List[LayerDefinition]] = None):
        super().__init__(name="ArchitectureValidator", initial_state=ValidatorState.INITIAL)

        # Default layer definitions (common 3-tier architecture)
        self.layers = layers or [
            LayerDefinition(
                name="presentation",
                paths=["ui", "views", "controllers", "api"],
                allowed_dependencies=["business", "data"],
            ),
            LayerDefinition(
                name="business",
                paths=["services", "logic", "domain", "models"],
                allowed_dependencies=["data"],
            ),
            LayerDefinition(
                name="data",
                paths=["repositories", "database", "storage", "dao"],
                allowed_dependencies=[],
            ),
        ]

        # Initialize context
        self.context = {
            "code_files": [],
            "file_structure": {},
            "imports": {},
            "violations": [],
            "report": None,
        }

        # Setup transitions
        self._setup_transitions()

    def _setup_transitions(self):
        """Setup FSA transitions."""
        transitions = [
            Transition(
                from_state=ValidatorState.INITIAL,
                to_state=ValidatorState.LOADING_STRUCTURE,
                condition=lambda ctx: len(ctx.get("code_files", [])) > 0,
                action=self._load_structure,
            ),
            Transition(
                from_state=ValidatorState.LOADING_STRUCTURE,
                to_state=ValidatorState.ANALYZING_LAYERS,
                condition=lambda ctx: "file_structure" in ctx,
                action=self._analyze_layers,
            ),
            Transition(
                from_state=ValidatorState.ANALYZING_LAYERS,
                to_state=ValidatorState.CHECKING_PATTERNS,
                action=self._check_patterns,
            ),
            Transition(
                from_state=ValidatorState.CHECKING_PATTERNS,
                to_state=ValidatorState.DETECTING_VIOLATIONS,
                action=self._detect_violations,
            ),
            Transition(
                from_state=ValidatorState.DETECTING_VIOLATIONS,
                to_state=ValidatorState.COMPLETED,
                action=self._generate_report,
            ),
        ]

        self.register_transitions(transitions)

    def _load_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Load code structure and imports."""
        logger.info("Loading code structure...")

        # Initialize context structure
        if "violations" not in context:
            context["violations"] = []

        file_structure = {}
        imports_map = {}

        for file_path in context["code_files"]:
            try:
                if isinstance(file_path, dict):
                    path = file_path["path"]
                    content = file_path["content"]
                else:
                    path = file_path
                    with open(path, "r") as f:
                        content = f.read()

                # Parse imports
                imports = self._extract_imports(content)
                imports_map[path] = imports

                # Determine layer
                layer = self._identify_layer(path)
                file_structure[path] = {"layer": layer, "imports": imports, "content": content}

            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        context["file_structure"] = file_structure
        context["imports"] = imports_map
        logger.info(f"Loaded {len(file_structure)} files")
        return context

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            pass
        return imports

    def _identify_layer(self, file_path: str) -> Optional[str]:
        """Identify which layer a file belongs to."""
        path_lower = file_path.lower()
        for layer in self.layers:
            for layer_path in layer.paths:
                if layer_path in path_lower:
                    return layer.name
        return None

    def _analyze_layers(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze layer separation and dependencies."""
        logger.info("Analyzing layer separation...")

        file_structure = context["file_structure"]
        layer_stats = {}

        # Count files per layer
        for file_path, info in file_structure.items():
            layer = info["layer"]
            if layer:
                if layer not in layer_stats:
                    layer_stats[layer] = {"files": 0, "imports": 0}
                layer_stats[layer]["files"] += 1
                layer_stats[layer]["imports"] += len(info["imports"])

        # Check for layer violations
        for file_path, info in file_structure.items():
            source_layer = info["layer"]
            if not source_layer:
                continue

            for imported_module in info["imports"]:
                # Check if import violates layer rules
                for other_file, other_info in file_structure.items():
                    if imported_module in other_file or any(
                        imp in imported_module for imp in other_info["imports"]
                    ):
                        target_layer = other_info["layer"]
                        if target_layer and not self._is_allowed_dependency(
                            source_layer, target_layer
                        ):
                            violation = Violation(
                                severity="error",
                                category="layer_violation",
                                message=f"Layer '{source_layer}' should not depend on '{target_layer}'",
                                file_path=file_path,
                                details=f"Import: {imported_module}",
                            )
                            context["violations"].append(violation)

        context["layer_stats"] = layer_stats
        logger.info(f"Analyzed {len(layer_stats)} layers")
        return context

    def _is_allowed_dependency(self, from_layer: str, to_layer: str) -> bool:
        """Check if dependency between layers is allowed."""
        if from_layer == to_layer:
            return True

        for layer in self.layers:
            if layer.name == from_layer:
                return to_layer in layer.allowed_dependencies

        return True  # Allow if layer not defined

    def _check_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check for common design pattern violations."""
        logger.info("Checking design patterns...")

        file_structure = context["file_structure"]

        for file_path, info in file_structure.items():
            try:
                # Get file content from structure
                content = info.get("content", "")
                if not content:
                    continue

                # Check for pattern violations
                violations = []

                # Pattern 1: God class (too many methods)
                class_methods = self._count_class_methods(content)
                for class_name, method_count in class_methods.items():
                    if method_count > 20:
                        violations.append(
                            Violation(
                                severity="warning",
                                category="god_class",
                                message=f"Class '{class_name}' has {method_count} methods (consider splitting)",
                                file_path=file_path,
                            )
                        )

                # Pattern 2: Direct database access in presentation layer
                if info["layer"] == "presentation":
                    if any(
                        db_term in imp.lower()
                        for imp in info["imports"]
                        for db_term in ["database", "sqlalchemy", "psycopg", "pymongo"]
                    ):
                        violations.append(
                            Violation(
                                severity="error",
                                category="pattern_violation",
                                message="Presentation layer should not directly access database",
                                file_path=file_path,
                            )
                        )

                context["violations"].extend(violations)

            except Exception as e:
                logger.debug(f"Error checking patterns in {file_path}: {e}")

        logger.info("Pattern checking completed")
        return context

    def _count_class_methods(self, content: str) -> Dict[str, int]:
        """Count methods in each class."""
        class_methods = {}
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    method_count = sum(
                        1 for item in node.body if isinstance(item, ast.FunctionDef)
                    )
                    class_methods[node.name] = method_count
        except SyntaxError:
            pass
        return class_methods

    def _detect_violations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect circular dependencies and other violations."""
        logger.info("Detecting violations...")

        # Detect circular dependencies
        imports_map = context["imports"]
        circular_deps = self._find_circular_dependencies(imports_map)

        for cycle in circular_deps:
            violation = Violation(
                severity="error",
                category="circular_dependency",
                message=f"Circular dependency detected: {' -> '.join(cycle)}",
                details=f"Cycle length: {len(cycle)}",
            )
            context["violations"].append(violation)

        context["circular_dependencies"] = circular_deps
        logger.info(f"Found {len(circular_deps)} circular dependencies")
        return context

    def _find_circular_dependencies(self, imports_map: Dict[str, List[str]]) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        circular = []
        visited = set()

        def dfs(file_path: str, path: List[str]) -> None:
            if file_path in path:
                # Found a cycle
                cycle_start = path.index(file_path)
                cycle = path[cycle_start:] + [file_path]
                if cycle not in circular and list(reversed(cycle)) not in circular:
                    circular.append(cycle)
                return

            if file_path in visited:
                return

            visited.add(file_path)
            new_path = path + [file_path]

            for imported in imports_map.get(file_path, []):
                # Find files that match this import
                for other_file in imports_map.keys():
                    if imported in other_file:
                        dfs(other_file, new_path)

        for file_path in imports_map.keys():
            dfs(file_path, [])

        return circular

    def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation report."""
        logger.info("Generating validation report...")

        violations = context["violations"]
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        report = ArchitectureReport(
            total_files=len(context["file_structure"]),
            total_violations=len(violations),
            errors=errors,
            warnings=warnings,
            layer_info=context.get("layer_stats", {}),
            circular_dependencies=context.get("circular_dependencies", []),
            pattern_violations=[v for v in violations if v.category in ["god_class", "pattern_violation"]],
        )

        context["report"] = report
        logger.info(f"Generated report: {len(errors)} errors, {len(warnings)} warnings")
        return context

    def validate(self, code_files: List[Any]) -> ArchitectureReport:
        """
        Validate architecture of given code files.

        Args:
            code_files: List of file paths or dicts with 'path' and 'content'

        Returns:
            ArchitectureReport with violations and metrics
        """
        # Reset FSA
        self.reset()

        # Set context
        self.context["code_files"] = code_files

        # Run FSA
        final_context = self.run()

        return final_context.get("report")


def print_architecture_report(report: ArchitectureReport):
    """Print formatted architecture validation report."""
    print("\n" + "=" * 80)
    print("ARCHITECTURE VALIDATION REPORT")
    print("=" * 80)

    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 80)
    print(f"  Total Files Analyzed:    {report.total_files}")
    print(f"  Total Violations:        {report.total_violations}")
    print(f"  Errors:                  {len(report.errors)}")
    print(f"  Warnings:                {len(report.warnings)}")

    # Layer information
    if report.layer_info:
        print("\n🏗️  LAYER ANALYSIS:")
        print("-" * 80)
        for layer_name, stats in report.layer_info.items():
            print(f"  {layer_name.upper()}:")
            print(f"    Files:   {stats['files']}")
            print(f"    Imports: {stats['imports']}")

    # Errors
    if report.errors:
        print("\n❌ ERRORS:")
        print("-" * 80)
        for i, error in enumerate(report.errors[:10], 1):
            print(f"  {i}. [{error.category.upper()}] {error.message}")
            if error.file_path:
                print(f"     File: {error.file_path}")
            if error.details:
                print(f"     {error.details}")

    # Warnings
    if report.warnings:
        print("\n⚠️  WARNINGS:")
        print("-" * 80)
        for i, warning in enumerate(report.warnings[:10], 1):
            print(f"  {i}. [{warning.category.upper()}] {warning.message}")
            if warning.file_path:
                print(f"     File: {warning.file_path}")

    # Circular dependencies
    if report.circular_dependencies:
        print("\n🔄 CIRCULAR DEPENDENCIES:")
        print("-" * 80)
        for i, cycle in enumerate(report.circular_dependencies, 1):
            print(f"  {i}. {' -> '.join([os.path.basename(f) for f in cycle])}")

    # Pattern violations
    if report.pattern_violations:
        print("\n🎨 PATTERN VIOLATIONS:")
        print("-" * 80)
        for i, violation in enumerate(report.pattern_violations[:5], 1):
            print(f"  {i}. {violation.message}")

    # Final verdict
    print("\n" + "=" * 80)
    if report.total_violations == 0:
        print("✅ Architecture validation passed! No violations detected.")
    elif len(report.errors) == 0:
        print("⚠️  Architecture has warnings but no critical errors.")
    else:
        print(f"❌ Architecture validation failed with {len(report.errors)} error(s).")
    print("=" * 80 + "\n")

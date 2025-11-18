"""
Code Smell Detector FSA - Comprehensive code smell detection and analysis.

This module provides AST-based code smell detection using Fowler's classification:
- Bloaters: Long methods, large classes, long parameter lists, data clumps, primitive obsession
- OOP Abusers: Switch statements, refused bequest
- Change Preventers: Divergent change, shotgun surgery
- Dispensables: Dead code, duplicate code, lazy class, excessive comments
- Couplers: Feature envy, inappropriate intimacy, message chains
- Python-specific: Mutable defaults, bare except, globals, magic numbers
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class Severity(Enum):
    """Smell severity levels."""

    CRITICAL = "critical"  # Fix immediately
    MAJOR = "major"  # Fix soon
    MINOR = "minor"  # Fix when convenient


class SmellCategory(Enum):
    """Fowler's code smell categories."""

    BLOATER = "bloater"
    OOP_ABUSER = "oop_abuser"
    CHANGE_PREVENTER = "change_preventer"
    DISPENSABLE = "dispensable"
    COUPLER = "coupler"
    PYTHON_SPECIFIC = "python_specific"


@dataclass
class Smell:
    """Represents a detected code smell."""

    smell_type: str
    category: SmellCategory
    severity: Severity
    location: str
    line_number: int
    description: str
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: str = ""


@dataclass
class RefactoringSuggestion:
    """Refactoring suggestion for a smell."""

    smell: Smell
    refactoring_type: str
    description: str
    estimated_effort: float  # hours
    benefit: str


@dataclass
class CodeFix:
    """Automated fix for a smell."""

    original_code: str
    fixed_code: str
    diff: str
    description: str


@dataclass
class TechnicalDebt:
    """Technical debt estimation."""

    total_hours: float
    cost_estimate: float
    interest_rate: float  # productivity impact percentage
    prioritized_fixes: list["PrioritizedSmell"] = field(default_factory=list)


@dataclass
class PrioritizedSmell:
    """Prioritized smell with impact analysis."""

    smell: Smell
    priority_score: float
    impact: float
    urgency: float


@dataclass
class SmellReport:
    """Comprehensive smell detection report."""

    smells: list[Smell]
    total_count: int
    severity_distribution: dict[str, int]
    category_distribution: dict[str, int]
    technical_debt: TechnicalDebt
    recommendations: list[RefactoringSuggestion]


class CodeSmellDetector:
    """Comprehensive code smell detector using AST analysis."""

    # Configuration thresholds
    LONG_METHOD_LINES = 50
    LONG_METHOD_COMPLEXITY = 10
    LARGE_CLASS_LINES = 500
    LARGE_CLASS_METHODS = 20
    LARGE_CLASS_FIELDS = 15
    LONG_PARAM_LIST_MINOR = 5
    LONG_PARAM_LIST_MAJOR = 7
    LAZY_CLASS_METHODS = 3
    LAZY_CLASS_LINES = 50
    MAGIC_NUMBER_THRESHOLD = 3
    MESSAGE_CHAIN_LENGTH = 3
    DUPLICATE_LINES_MIN = 5

    def __init__(self):
        """Initialize the code smell detector."""
        self.smells: list[Smell] = []

    def detect_smells(self, code: str | Path) -> SmellReport:
        """
        Detect all code smells in the given code.

        Args:
            code: Python code as string or Path to file

        Returns:
            SmellReport with all detected smells and analysis
        """
        if isinstance(code, Path):
            code = code.read_text()

        self.smells = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._create_error_report(f"Syntax error: {e}")

        # Detect all smell categories
        self._detect_bloaters(tree, code)
        self._detect_oop_abusers(tree, code)
        self._detect_change_preventers(tree, code)
        self._detect_dispensables(tree, code)
        self._detect_couplers(tree, code)
        self._detect_python_specific(tree, code)

        # Generate report with analysis
        return self._generate_report()

    def _detect_bloaters(self, tree: ast.AST, code: str) -> None:
        """Detect bloater smells (code that has grown too large)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._detect_long_method(node)
                self._detect_long_parameter_list(node)
            elif isinstance(node, ast.ClassDef):
                self._detect_large_class(node, code)
                self._detect_god_class(node, code)

        self._detect_primitive_obsession(tree)
        self._detect_data_clumps(tree)

    def _detect_long_method(self, func: ast.FunctionDef) -> None:
        """Detect long methods."""
        if not hasattr(func, "lineno") or not hasattr(func, "end_lineno"):
            return

        lines = func.end_lineno - func.lineno
        complexity = self._calculate_complexity(func)

        if lines > self.LONG_METHOD_LINES or complexity > self.LONG_METHOD_COMPLEXITY:
            severity = Severity.MAJOR if lines > 100 else Severity.MINOR

            smell = Smell(
                smell_type="long_method",
                category=SmellCategory.BLOATER,
                severity=severity,
                location=func.name,
                line_number=func.lineno,
                description=f"Method '{func.name}' is too long ({lines} lines, complexity {complexity})",
                metrics={"lines": lines, "complexity": complexity},
                evidence=f"Lines: {lines}, Cyclomatic Complexity: {complexity}",
            )
            self.smells.append(smell)

    def _detect_large_class(self, cls: ast.ClassDef, code: str) -> None:
        """Detect large classes."""
        if not hasattr(cls, "lineno") or not hasattr(cls, "end_lineno"):
            return

        lines = cls.end_lineno - cls.lineno
        methods = sum(1 for node in cls.body if isinstance(node, ast.FunctionDef))
        fields = self._count_class_fields(cls)

        if lines > self.LARGE_CLASS_LINES or methods > self.LARGE_CLASS_METHODS or fields > self.LARGE_CLASS_FIELDS:
            smell = Smell(
                smell_type="large_class",
                category=SmellCategory.BLOATER,
                severity=Severity.MAJOR,
                location=cls.name,
                line_number=cls.lineno,
                description=f"Class '{cls.name}' is too large ({lines} lines, {methods} methods, {fields} fields)",
                metrics={"lines": lines, "methods": methods, "fields": fields},
            )
            self.smells.append(smell)

    def _detect_god_class(self, cls: ast.ClassDef, code: str) -> None:
        """Detect god classes (classes that do too much)."""
        if not hasattr(cls, "lineno") or not hasattr(cls, "end_lineno"):
            return

        methods = sum(1 for node in cls.body if isinstance(node, ast.FunctionDef))
        fields = self._count_class_fields(cls)
        responsibilities = self._estimate_responsibilities(cls)

        # God class: > 30 methods, > 20 fields, or > 5 distinct responsibilities
        if methods > 30 or fields > 20 or responsibilities > 5:
            smell = Smell(
                smell_type="god_class",
                category=SmellCategory.BLOATER,
                severity=Severity.CRITICAL,
                location=cls.name,
                line_number=cls.lineno,
                description=f"Class '{cls.name}' has too many responsibilities (god class)",
                metrics={"methods": methods, "fields": fields, "responsibilities": responsibilities},
            )
            self.smells.append(smell)

    def _detect_long_parameter_list(self, func: ast.FunctionDef) -> None:
        """Detect long parameter lists."""
        param_count = len(func.args.args)

        # Subtract 1 for 'self' or 'cls' in methods
        if param_count > 0 and func.args.args[0].arg in ("self", "cls"):
            param_count -= 1

        if param_count >= self.LONG_PARAM_LIST_MINOR:
            severity = Severity.MAJOR if param_count >= self.LONG_PARAM_LIST_MAJOR else Severity.MINOR

            smell = Smell(
                smell_type="long_parameter_list",
                category=SmellCategory.BLOATER,
                severity=severity,
                location=func.name,
                line_number=func.lineno,
                description=f"Method '{func.name}' has too many parameters ({param_count})",
                metrics={"param_count": param_count},
            )
            self.smells.append(smell)

    def _detect_data_clumps(self, tree: ast.AST) -> None:
        """Detect data clumps (same group of parameters appearing together)."""
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        # Track parameter groups (sets of 3+ parameters)
        param_groups: dict[tuple, list[str]] = {}

        for func in functions:
            params = [arg.arg for arg in func.args.args if arg.arg not in ("self", "cls")]
            if len(params) >= 3:
                # Create all 3-param combinations
                for i in range(len(params) - 2):
                    group = tuple(sorted(params[i : i + 3]))
                    if group not in param_groups:
                        param_groups[group] = []
                    param_groups[group].append(func.name)

        # Find groups appearing in multiple functions
        for group, func_names in param_groups.items():
            if len(func_names) > 1:
                smell = Smell(
                    smell_type="data_clump",
                    category=SmellCategory.BLOATER,
                    severity=Severity.MINOR,
                    location=f"Functions: {', '.join(func_names[:3])}",
                    line_number=0,
                    description=f"Parameter group {group} appears in multiple functions",
                    metrics={"group": group, "occurrences": len(func_names)},
                )
                self.smells.append(smell)
                break  # Report one example

    def _detect_primitive_obsession(self, tree: ast.AST) -> None:
        """Detect primitive obsession (excessive use of primitives instead of objects)."""
        # Count string/int/float type annotations and isinstance checks
        primitive_checks = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    if len(node.args) >= 2:
                        if isinstance(node.args[1], ast.Name) and node.args[1].id in ("str", "int", "float", "bool"):
                            primitive_checks += 1

        if primitive_checks > 5:
            smell = Smell(
                smell_type="primitive_obsession",
                category=SmellCategory.BLOATER,
                severity=Severity.MINOR,
                location="Multiple locations",
                line_number=0,
                description=f"Excessive primitive type checking ({primitive_checks} occurrences)",
                metrics={"primitive_checks": primitive_checks},
            )
            self.smells.append(smell)

    def _detect_oop_abusers(self, tree: ast.AST, code: str) -> None:
        """Detect OOP abuser smells."""
        self._detect_switch_statements(tree)
        self._detect_refused_bequest(tree)

    def _detect_switch_statements(self, tree: ast.AST) -> None:
        """Detect switch statements (long if-elif chains with type checking)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                elif_count = self._count_elif_chain(node)
                has_type_checking = self._has_type_checking(node)

                if elif_count >= 3 and has_type_checking:
                    smell = Smell(
                        smell_type="switch_statement",
                        category=SmellCategory.OOP_ABUSER,
                        severity=Severity.MAJOR,
                        location="Multiple if-elif branches",
                        line_number=node.lineno,
                        description=f"Complex if-elif chain with type checking ({elif_count} branches)",
                        metrics={"elif_count": elif_count},
                    )
                    self.smells.append(smell)

    def _detect_refused_bequest(self, tree: ast.AST) -> None:
        """Detect refused bequest (subclass doesn't use inherited methods)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for NotImplementedError in methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Raise):
                                if isinstance(stmt.exc, ast.Call):
                                    if isinstance(stmt.exc.func, ast.Name):
                                        if stmt.exc.func.id == "NotImplementedError":
                                            smell = Smell(
                                                smell_type="refused_bequest",
                                                category=SmellCategory.OOP_ABUSER,
                                                severity=Severity.MAJOR,
                                                location=f"{node.name}.{item.name}",
                                                line_number=item.lineno,
                                                description=f"Method '{item.name}' raises NotImplementedError",
                                            )
                                            self.smells.append(smell)

    def _detect_change_preventers(self, tree: ast.AST, code: str) -> None:
        """Detect change preventer smells."""
        # These are harder to detect statically, so we use heuristics
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 25:  # High number of methods suggests multiple responsibilities
                    smell = Smell(
                        smell_type="divergent_change",
                        category=SmellCategory.CHANGE_PREVENTER,
                        severity=Severity.MAJOR,
                        location=node.name,
                        line_number=node.lineno,
                        description=f"Class '{node.name}' may have multiple reasons to change",
                        metrics={"methods": len(methods)},
                    )
                    self.smells.append(smell)

    def _detect_dispensables(self, tree: ast.AST, code: str) -> None:
        """Detect dispensable smells (unnecessary code)."""
        self._detect_dead_code(tree)
        self._detect_lazy_class(tree)
        self._detect_duplicate_code(code)
        self._detect_excessive_comments(tree, code)

    def _detect_dead_code(self, tree: ast.AST) -> None:
        """Detect dead code (unused variables, unreachable code)."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Detect unreachable code after return
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return):
                        if i < len(node.body) - 1:
                            smell = Smell(
                                smell_type="dead_code",
                                category=SmellCategory.DISPENSABLE,
                                severity=Severity.MINOR,
                                location=node.name,
                                line_number=node.body[i + 1].lineno,
                                description=f"Unreachable code after return in '{node.name}'",
                            )
                            self.smells.append(smell)
                            break

    def _detect_lazy_class(self, tree: ast.AST) -> None:
        """Detect lazy classes (classes that don't do enough)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
                    continue

                lines = node.end_lineno - node.lineno
                methods = sum(1 for item in node.body if isinstance(item, ast.FunctionDef))

                if methods < self.LAZY_CLASS_METHODS and lines < self.LAZY_CLASS_LINES:
                    smell = Smell(
                        smell_type="lazy_class",
                        category=SmellCategory.DISPENSABLE,
                        severity=Severity.MINOR,
                        location=node.name,
                        line_number=node.lineno,
                        description=f"Class '{node.name}' does too little ({methods} methods, {lines} lines)",
                        metrics={"methods": methods, "lines": lines},
                    )
                    self.smells.append(smell)

    def _detect_duplicate_code(self, code: str) -> None:
        """Detect duplicate code (simplified version)."""
        lines = code.split("\n")
        # Remove empty lines and comments
        non_empty_lines = [
            line.strip() for line in lines if line.strip() and not line.strip().startswith("#")
        ]

        # Look for repeated sequences
        seen_sequences: dict[tuple, int] = {}
        for i in range(len(non_empty_lines) - self.DUPLICATE_LINES_MIN):
            sequence = tuple(non_empty_lines[i : i + self.DUPLICATE_LINES_MIN])
            if sequence in seen_sequences:
                smell = Smell(
                    smell_type="duplicate_code",
                    category=SmellCategory.DISPENSABLE,
                    severity=Severity.MAJOR,
                    location=f"Lines {i + 1}-{i + self.DUPLICATE_LINES_MIN}",
                    line_number=i + 1,
                    description=f"Duplicate code sequence found ({self.DUPLICATE_LINES_MIN}+ lines)",
                )
                self.smells.append(smell)
                return  # Report one example
            seen_sequences[sequence] = i

    def _detect_excessive_comments(self, tree: ast.AST, code: str) -> None:
        """Detect excessive comments (high comment-to-code ratio)."""
        lines = code.split("\n")
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

        if code_lines > 0:
            comment_ratio = comment_lines / code_lines
            if comment_ratio > 0.4:  # More than 40% comments
                smell = Smell(
                    smell_type="excessive_comments",
                    category=SmellCategory.DISPENSABLE,
                    severity=Severity.MINOR,
                    location="Multiple locations",
                    line_number=0,
                    description=f"High comment-to-code ratio ({comment_ratio:.1%})",
                    metrics={"comment_ratio": comment_ratio},
                )
                self.smells.append(smell)

    def _detect_couplers(self, tree: ast.AST, code: str) -> None:
        """Detect coupler smells (excessive coupling)."""
        self._detect_feature_envy(tree)
        self._detect_message_chains(tree)

    def _detect_feature_envy(self, tree: ast.AST) -> None:
        """Detect feature envy (method uses more features of another class)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                external_calls = 0
                internal_calls = 0

                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Attribute):
                        if isinstance(stmt.value, ast.Name):
                            if stmt.value.id == "self":
                                internal_calls += 1
                            else:
                                external_calls += 1

                if external_calls > internal_calls and external_calls > 5:
                    smell = Smell(
                        smell_type="feature_envy",
                        category=SmellCategory.COUPLER,
                        severity=Severity.MAJOR,
                        location=node.name,
                        line_number=node.lineno,
                        description=f"Method '{node.name}' accesses external objects more than internal",
                        metrics={"external_calls": external_calls, "internal_calls": internal_calls},
                    )
                    self.smells.append(smell)

    def _detect_message_chains(self, tree: ast.AST) -> None:
        """Detect message chains (a.b.c.d - Law of Demeter violation)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                chain_length = self._count_attribute_chain(node)
                if chain_length >= self.MESSAGE_CHAIN_LENGTH:
                    smell = Smell(
                        smell_type="message_chain",
                        category=SmellCategory.COUPLER,
                        severity=Severity.MINOR,
                        location="Attribute access chain",
                        line_number=node.lineno,
                        description=f"Long message chain ({chain_length} levels)",
                        metrics={"chain_length": chain_length},
                    )
                    self.smells.append(smell)

    def _detect_python_specific(self, tree: ast.AST, code: str) -> None:
        """Detect Python-specific code smells."""
        self._detect_mutable_default_arguments(tree)
        self._detect_bare_except(tree)
        self._detect_global_variables(tree)
        self._detect_magic_numbers(tree)

    def _detect_mutable_default_arguments(self, tree: ast.AST) -> None:
        """Detect mutable default arguments (def func(arg=[]))."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        smell = Smell(
                            smell_type="mutable_default_argument",
                            category=SmellCategory.PYTHON_SPECIFIC,
                            severity=Severity.CRITICAL,
                            location=node.name,
                            line_number=node.lineno,
                            description=f"Function '{node.name}' has mutable default argument",
                        )
                        self.smells.append(smell)

    def _detect_bare_except(self, tree: ast.AST) -> None:
        """Detect bare except clauses."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    smell = Smell(
                        smell_type="bare_except",
                        category=SmellCategory.PYTHON_SPECIFIC,
                        severity=Severity.MAJOR,
                        location="Exception handler",
                        line_number=node.lineno,
                        description="Bare except clause catches all exceptions",
                    )
                    self.smells.append(smell)

    def _detect_global_variables(self, tree: ast.AST) -> None:
        """Detect global variable usage."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    smell = Smell(
                        smell_type="global_variable",
                        category=SmellCategory.PYTHON_SPECIFIC,
                        severity=Severity.MAJOR,
                        location=name,
                        line_number=node.lineno,
                        description=f"Global variable '{name}' used",
                    )
                    self.smells.append(smell)

    def _detect_magic_numbers(self, tree: ast.AST) -> None:
        """Detect magic numbers (hardcoded numeric literals)."""
        magic_numbers: dict[float, list[int]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and node.value not in (0, 1, -1):
                    if node.value not in magic_numbers:
                        magic_numbers[node.value] = []
                    if hasattr(node, "lineno"):
                        magic_numbers[node.value].append(node.lineno)

        for number, lines in magic_numbers.items():
            if len(lines) >= self.MAGIC_NUMBER_THRESHOLD:
                smell = Smell(
                    smell_type="magic_number",
                    category=SmellCategory.PYTHON_SPECIFIC,
                    severity=Severity.MINOR,
                    location=f"Number: {number}",
                    line_number=lines[0],
                    description=f"Magic number {number} used {len(lines)} times",
                    metrics={"number": number, "occurrences": len(lines)},
                )
                self.smells.append(smell)

    def suggest_refactoring(self, smell: Smell) -> RefactoringSuggestion:
        """Suggest refactoring for a given smell."""
        refactoring_map = {
            "long_method": ("Extract Method", "Break method into smaller, focused methods", 2.0),
            "large_class": ("Extract Class", "Split class into smaller, cohesive classes", 8.0),
            "god_class": ("Extract Class", "Decompose god class into multiple focused classes", 16.0),
            "long_parameter_list": ("Introduce Parameter Object", "Group parameters into an object", 1.0),
            "data_clump": ("Extract Class", "Create class to hold related data", 2.0),
            "primitive_obsession": ("Replace Data Value with Object", "Create value objects for primitives", 4.0),
            "switch_statement": ("Replace with Polymorphism", "Use polymorphism instead of type checking", 4.0),
            "refused_bequest": ("Replace Inheritance with Delegation", "Use composition over inheritance", 3.0),
            "dead_code": ("Remove Dead Code", "Delete unreachable code", 0.5),
            "lazy_class": ("Inline Class", "Merge class into using class", 1.0),
            "duplicate_code": ("Extract Method", "Extract common code into shared method", 2.0),
            "excessive_comments": ("Rename Method/Extract Method", "Make code self-documenting", 1.0),
            "feature_envy": ("Move Method", "Move method to the envied class", 2.0),
            "message_chain": ("Hide Delegate", "Add methods to hide chain", 1.5),
            "mutable_default_argument": ("Use None Default", "Replace with None and create inside", 0.5),
            "bare_except": ("Catch Specific Exceptions", "Catch only expected exceptions", 0.5),
            "global_variable": ("Encapsulate in Class", "Move to class or use dependency injection", 2.0),
            "magic_number": ("Replace with Named Constant", "Create named constant", 0.5),
        }

        refactoring_type, description, effort = refactoring_map.get(
            smell.smell_type, ("Refactor", "Improve code structure", 1.0)
        )

        benefit = self._calculate_benefit(smell)

        return RefactoringSuggestion(
            smell=smell,
            refactoring_type=refactoring_type,
            description=description,
            estimated_effort=effort,
            benefit=benefit,
        )

    def estimate_technical_debt(self, smells: list[Smell]) -> TechnicalDebt:
        """Estimate technical debt from smells."""
        total_hours = 0.0
        prioritized = []

        for smell in smells:
            suggestion = self.suggest_refactoring(smell)
            total_hours += suggestion.estimated_effort

            impact = self._calculate_impact(smell)
            urgency = self._calculate_urgency(smell)

            prioritized_smell = PrioritizedSmell(
                smell=smell,
                priority_score=(smell.severity.value == "critical" and 10 or smell.severity.value == "major" and 5 or 1)
                * impact
                * urgency
                / suggestion.estimated_effort,
                impact=impact,
                urgency=urgency,
            )
            prioritized.append(prioritized_smell)

        # Sort by priority
        prioritized.sort(key=lambda x: x.priority_score, reverse=True)

        # Calculate cost (assuming $100/hour developer rate)
        cost_estimate = total_hours * 100

        # Interest rate: percentage of productivity loss
        interest_rate = min(len(smells) * 0.5, 20.0)  # Cap at 20%

        return TechnicalDebt(
            total_hours=total_hours,
            cost_estimate=cost_estimate,
            interest_rate=interest_rate,
            prioritized_fixes=prioritized,
        )

    def generate_automated_fix(self, smell: Smell) -> Optional[CodeFix]:
        """Generate automated fix for simple smells."""
        if smell.smell_type == "mutable_default_argument":
            return CodeFix(
                original_code="def func(arg=[]):",
                fixed_code="def func(arg=None):\n    if arg is None:\n        arg = []",
                diff="- def func(arg=[]):\n+ def func(arg=None):\n+     if arg is None:\n+         arg = []",
                description="Replace mutable default with None",
            )

        if smell.smell_type == "bare_except":
            return CodeFix(
                original_code="except:",
                fixed_code="except Exception as e:",
                diff="- except:\n+ except Exception as e:",
                description="Catch specific exception",
            )

        if smell.smell_type == "magic_number":
            number = smell.metrics.get("number", 0)
            return CodeFix(
                original_code=f"value = {number}",
                fixed_code=f"CONSTANT_NAME = {number}\nvalue = CONSTANT_NAME",
                diff=f"+ CONSTANT_NAME = {number}\n- value = {number}\n+ value = CONSTANT_NAME",
                description="Replace with named constant",
            )

        return None

    # Helper methods
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _count_class_fields(self, cls: ast.ClassDef) -> int:
        """Count class fields."""
        fields = set()
        for node in ast.walk(cls):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == "self":
                            fields.add(target.attr)
        return len(fields)

    def _estimate_responsibilities(self, cls: ast.ClassDef) -> int:
        """Estimate number of responsibilities (simplified heuristic)."""
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)]
        # Group methods by prefix (get_, set_, handle_, process_, etc.)
        prefixes = set()
        for method in methods:
            parts = method.name.split("_")
            if len(parts) > 1:
                prefixes.add(parts[0])
        return max(len(prefixes), 1)

    def _count_elif_chain(self, node: ast.If) -> int:
        """Count the length of if-elif chain."""
        count = 1
        current = node
        while current.orelse:
            if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                count += 1
                current = current.orelse[0]
            else:
                break
        return count

    def _has_type_checking(self, node: ast.If) -> bool:
        """Check if if-elif chain has type checking (isinstance)."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == "isinstance":
                    return True
        return False

    def _count_attribute_chain(self, node: ast.Attribute) -> int:
        """Count the length of attribute chain (a.b.c)."""
        count = 1
        current = node.value
        while isinstance(current, ast.Attribute):
            count += 1
            current = current.value
        return count

    def _calculate_benefit(self, smell: Smell) -> str:
        """Calculate benefit of fixing a smell."""
        if smell.severity == Severity.CRITICAL:
            return "Prevents bugs, improves reliability"
        elif smell.severity == Severity.MAJOR:
            return "Improves maintainability, reduces complexity"
        else:
            return "Improves code quality, enhances readability"

    def _calculate_impact(self, smell: Smell) -> float:
        """Calculate impact of a smell (1-10)."""
        base_impact = {"critical": 10, "major": 5, "minor": 2}
        return base_impact.get(smell.severity.value, 1)

    def _calculate_urgency(self, smell: Smell) -> float:
        """Calculate urgency of fixing a smell (1-10)."""
        if smell.severity == Severity.CRITICAL:
            return 10
        elif smell.smell_type in ("god_class", "feature_envy", "switch_statement"):
            return 7
        else:
            return 3

    def _generate_report(self) -> SmellReport:
        """Generate comprehensive smell report."""
        severity_dist = {"critical": 0, "major": 0, "minor": 0}
        category_dist = {cat.value: 0 for cat in SmellCategory}

        for smell in self.smells:
            severity_dist[smell.severity.value] += 1
            category_dist[smell.category.value] += 1

        technical_debt = self.estimate_technical_debt(self.smells)
        recommendations = [self.suggest_refactoring(smell) for smell in self.smells[:10]]  # Top 10

        return SmellReport(
            smells=self.smells,
            total_count=len(self.smells),
            severity_distribution=severity_dist,
            category_distribution=category_dist,
            technical_debt=technical_debt,
            recommendations=recommendations,
        )

    def _create_error_report(self, error: str) -> SmellReport:
        """Create error report."""
        return SmellReport(
            smells=[],
            total_count=0,
            severity_distribution={"critical": 0, "major": 0, "minor": 0},
            category_distribution={cat.value: 0 for cat in SmellCategory},
            technical_debt=TechnicalDebt(total_hours=0, cost_estimate=0, interest_rate=0),
            recommendations=[],
        )


# Example usage
if __name__ == "__main__":
    # Sample code with multiple smells
    sample_code = '''
def process_data(a, b, c, d, e, f, g):  # Long parameter list
    """Process data with magic numbers and poor structure."""

    # Magic numbers
    if a > 100:  # Magic number
        result = a * 2.5  # Magic number
    elif b > 50:  # Magic number
        result = b * 1.5  # Magic number
    else:
        result = 0

    # Long method (simulated)
    for i in range(100):
        if i % 2 == 0:
            result += i
        else:
            result -= i

    return result

def another_function(items=[]):  # Mutable default argument - CRITICAL!
    """Dangerous mutable default."""
    items.append(1)
    return items

try:
    risky_operation()
except:  # Bare except - BAD!
    pass

global_var = 100  # Global variable

def use_global():
    global global_var  # Global usage
    global_var += 1
'''

    detector = CodeSmellDetector()
    report = detector.detect_smells(sample_code)

    print("=" * 80)
    print("CODE SMELL DETECTION REPORT")
    print("=" * 80)
    print(f"\nTotal Smells Detected: {report.total_count}\n")

    print("Severity Distribution:")
    for severity, count in report.severity_distribution.items():
        print(f"  {severity.upper()}: {count}")

    print("\nCategory Distribution:")
    for category, count in report.category_distribution.items():
        if count > 0:
            print(f"  {category}: {count}")

    print("\n" + "=" * 80)
    print("DETECTED SMELLS")
    print("=" * 80)

    for smell in report.smells:
        print(f"\n[{smell.severity.value.upper()}] {smell.smell_type}")
        print(f"  Location: {smell.location}:{smell.line_number}")
        print(f"  Category: {smell.category.value}")
        print(f"  Description: {smell.description}")
        if smell.metrics:
            print(f"  Metrics: {smell.metrics}")

    print("\n" + "=" * 80)
    print("TECHNICAL DEBT ANALYSIS")
    print("=" * 80)
    print(f"\nEstimated Effort: {report.technical_debt.total_hours:.1f} hours")
    print(f"Estimated Cost: ${report.technical_debt.cost_estimate:.2f}")
    print(f"Productivity Impact: {report.technical_debt.interest_rate:.1f}%")

    print("\n" + "=" * 80)
    print("TOP PRIORITY FIXES")
    print("=" * 80)

    for i, prioritized in enumerate(report.technical_debt.prioritized_fixes[:5], 1):
        print(f"\n{i}. {prioritized.smell.smell_type} (Priority: {prioritized.priority_score:.2f})")
        print(f"   Location: {prioritized.smell.location}:{prioritized.smell.line_number}")
        print(f"   Impact: {prioritized.impact}/10, Urgency: {prioritized.urgency}/10")

    print("\n" + "=" * 80)
    print("REFACTORING RECOMMENDATIONS")
    print("=" * 80)

    for i, rec in enumerate(report.recommendations[:5], 1):
        print(f"\n{i}. {rec.refactoring_type}")
        print(f"   Smell: {rec.smell.smell_type}")
        print(f"   Description: {rec.description}")
        print(f"   Estimated Effort: {rec.estimated_effort} hours")
        print(f"   Benefit: {rec.benefit}")

    print("\n" + "=" * 80)
    print("AUTOMATED FIXES (Examples)")
    print("=" * 80)

    for smell in report.smells:
        fix = detector.generate_automated_fix(smell)
        if fix:
            print(f"\nFix for {smell.smell_type}:")
            print(f"  {fix.description}")
            print(f"  Diff:\n{fix.diff}")
            break  # Show one example

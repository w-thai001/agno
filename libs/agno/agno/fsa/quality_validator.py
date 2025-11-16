"""
Code Quality Validator Tool

Comprehensive code quality validation system with multi-dimensional
quality checks, standards enforcement, and actionable feedback.

This module provides:
- Multi-level quality validation (syntax, style, security, performance)
- Configurable quality gates and thresholds
- Integration with static analysis tools
- Actionable violation reports
- Quality trend tracking
- CI/CD integration support

Key Features:
- Pluggable validation rules
- Severity-based reporting
- Auto-fix suggestions
- Quality scoring
- Historical tracking
- Standards compliance checking

Author: FSA Generation Sprint
Version: 1.0.0
"""

from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agno.utils.log import logger


class ViolationSeverity(Enum):
    """Severity levels for quality violations."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class QualityDimension(Enum):
    """Dimensions of code quality."""
    SYNTAX = "syntax"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    BEST_PRACTICES = "best_practices"


@dataclass
class QualityViolation:
    """
    A code quality violation.

    Represents a specific quality issue found in code.
    """
    # Unique ID
    id: str

    # Quality dimension
    dimension: QualityDimension

    # Severity level
    severity: ViolationSeverity

    # Rule ID that was violated
    rule_id: str

    # Description of the violation
    message: str

    # Location in code
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None

    # Code snippet
    code_snippet: Optional[str] = None

    # Suggested fix
    suggestion: Optional[str] = None

    # Auto-fix available
    auto_fixable: bool = False

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "dimension": self.dimension.value,
            "severity": self.severity.name,
            "rule_id": self.rule_id,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


class ValidationRule(ABC):
    """
    Abstract base class for validation rules.

    Rules check specific quality criteria and report violations.
    """

    def __init__(
        self,
        rule_id: str,
        dimension: QualityDimension,
        severity: ViolationSeverity,
        description: str,
    ):
        """
        Initialize rule.

        Args:
            rule_id: Unique rule identifier
            dimension: Quality dimension
            severity: Default severity
            description: Rule description
        """
        self.rule_id = rule_id
        self.dimension = dimension
        self.severity = severity
        self.description = description

    @abstractmethod
    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """
        Validate code against this rule.

        Args:
            code: Source code to validate
            file_path: Optional file path

        Returns:
            List of violations
        """
        pass


class PythonSyntaxRule(ValidationRule):
    """Validates Python syntax."""

    def __init__(self):
        super().__init__(
            rule_id="PY001",
            dimension=QualityDimension.SYNTAX,
            severity=ViolationSeverity.CRITICAL,
            description="Python syntax must be valid",
        )

    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """Validate Python syntax."""
        violations = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            violation = QualityViolation(
                id=f"{self.rule_id}_{hash(code)}",
                dimension=self.dimension,
                severity=self.severity,
                rule_id=self.rule_id,
                message=f"Syntax error: {e.msg}",
                file_path=file_path,
                line_number=e.lineno,
                column_number=e.offset,
                auto_fixable=False,
            )
            violations.append(violation)

        return violations


class LineLengthRule(ValidationRule):
    """Validates line length."""

    def __init__(self, max_length: int = 88):
        super().__init__(
            rule_id="STY001",
            dimension=QualityDimension.STYLE,
            severity=ViolationSeverity.WARNING,
            description=f"Lines should not exceed {max_length} characters",
        )
        self.max_length = max_length

    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """Validate line length."""
        violations = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            if len(line) > self.max_length:
                violation = QualityViolation(
                    id=f"{self.rule_id}_{i}",
                    dimension=self.dimension,
                    severity=self.severity,
                    rule_id=self.rule_id,
                    message=f"Line exceeds {self.max_length} characters (current: {len(line)})",
                    file_path=file_path,
                    line_number=i + 1,
                    code_snippet=line[:100] + "..." if len(line) > 100 else line,
                    suggestion="Break line into multiple lines or refactor",
                    auto_fixable=True,
                )
                violations.append(violation)

        return violations


class FunctionComplexityRule(ValidationRule):
    """Validates function complexity."""

    def __init__(self, max_complexity: int = 10):
        super().__init__(
            rule_id="MAINT001",
            dimension=QualityDimension.MAINTAINABILITY,
            severity=ViolationSeverity.WARNING,
            description=f"Functions should have complexity ≤ {max_complexity}",
        )
        self.max_complexity = max_complexity

    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """Validate function complexity."""
        violations = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_complexity(node)

                    if complexity > self.max_complexity:
                        violation = QualityViolation(
                            id=f"{self.rule_id}_{node.name}",
                            dimension=self.dimension,
                            severity=self.severity,
                            rule_id=self.rule_id,
                            message=f"Function '{node.name}' has complexity {complexity} (max: {self.max_complexity})",
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion="Break function into smaller functions",
                            auto_fixable=False,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error validating complexity: {e}")

        return violations

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
        return complexity


class SecurityRule(ValidationRule):
    """Validates security best practices."""

    def __init__(self):
        super().__init__(
            rule_id="SEC001",
            dimension=QualityDimension.SECURITY,
            severity=ViolationSeverity.ERROR,
            description="Avoid security vulnerabilities",
        )

    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """Validate security."""
        violations = []

        # Check for common security issues
        patterns = [
            (r"eval\(", "Use of eval() is dangerous"),
            (r"exec\(", "Use of exec() is dangerous"),
            (r"__import__\(", "Dynamic imports can be dangerous"),
            (r"pickle\.loads?\(", "Pickle deserialization can be dangerous"),
        ]

        lines = code.split("\n")

        for i, line in enumerate(lines):
            for pattern, message in patterns:
                if re.search(pattern, line):
                    violation = QualityViolation(
                        id=f"{self.rule_id}_{i}_{pattern}",
                        dimension=self.dimension,
                        severity=self.severity,
                        rule_id=self.rule_id,
                        message=message,
                        file_path=file_path,
                        line_number=i + 1,
                        code_snippet=line.strip(),
                        suggestion="Use safer alternatives",
                        auto_fixable=False,
                    )
                    violations.append(violation)

        return violations


class DocumentationRule(ValidationRule):
    """Validates documentation."""

    def __init__(self):
        super().__init__(
            rule_id="DOC001",
            dimension=QualityDimension.DOCUMENTATION,
            severity=ViolationSeverity.INFO,
            description="Functions and classes should have docstrings",
        )

    def validate(self, code: str, file_path: Optional[str] = None) -> List[QualityViolation]:
        """Validate documentation."""
        violations = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Check for docstring
                    has_docstring = (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    )

                    if not has_docstring:
                        entity_type = "Function" if isinstance(node, ast.FunctionDef) else "Class"
                        violation = QualityViolation(
                            id=f"{self.rule_id}_{node.name}",
                            dimension=self.dimension,
                            severity=self.severity,
                            rule_id=self.rule_id,
                            message=f"{entity_type} '{node.name}' is missing docstring",
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion=f"Add docstring explaining {entity_type.lower()} purpose and parameters",
                            auto_fixable=False,
                        )
                        violations.append(violation)

        except Exception as e:
            logger.error(f"Error validating documentation: {e}")

        return violations


@dataclass
class QualityGate:
    """
    Quality gate configuration.

    Defines thresholds that must be met for code to pass validation.
    """
    # Maximum allowed violations by severity
    max_critical: int = 0
    max_errors: int = 0
    max_warnings: int = 10
    max_info: int = 50

    # Minimum quality score (0-100)
    min_quality_score: float = 70.0

    # Required dimensions (all must have 0 critical/error violations)
    required_dimensions: Set[QualityDimension] = field(default_factory=set)

    def check(self, result: ValidationResult) -> Tuple[bool, List[str]]:
        """
        Check if validation result passes the quality gate.

        Args:
            result: Validation result

        Returns:
            Tuple of (passed, failure_reasons)
        """
        failures = []

        # Check violation counts
        if result.critical_count > self.max_critical:
            failures.append(
                f"Critical violations: {result.critical_count} > {self.max_critical}"
            )

        if result.error_count > self.max_errors:
            failures.append(
                f"Error violations: {result.error_count} > {self.max_errors}"
            )

        if result.warning_count > self.max_warnings:
            failures.append(
                f"Warning violations: {result.warning_count} > {self.max_warnings}"
            )

        if result.info_count > self.max_info:
            failures.append(
                f"Info violations: {result.info_count} > {self.max_info}"
            )

        # Check quality score
        if result.quality_score < self.min_quality_score:
            failures.append(
                f"Quality score: {result.quality_score:.1f} < {self.min_quality_score}"
            )

        # Check required dimensions
        for dimension in self.required_dimensions:
            dim_violations = [
                v for v in result.violations
                if v.dimension == dimension and v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.ERROR)
            ]
            if dim_violations:
                failures.append(
                    f"Required dimension '{dimension.value}' has {len(dim_violations)} critical/error violations"
                )

        return len(failures) == 0, failures


@dataclass
class ValidationResult:
    """
    Result of quality validation.

    Contains all violations and quality metrics.
    """
    # All violations
    violations: List[QualityViolation] = field(default_factory=list)

    # Quality score (0-100)
    quality_score: float = 100.0

    # Violation counts by severity
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    # Violations by dimension
    violations_by_dimension: Dict[QualityDimension, List[QualityViolation]] = field(
        default_factory=lambda: {dim: [] for dim in QualityDimension}
    )

    # Auto-fixable count
    auto_fixable_count: int = 0

    # Files checked
    files_checked: int = 0

    def add_violation(self, violation: QualityViolation) -> None:
        """Add a violation."""
        self.violations.append(violation)

        # Update counts
        if violation.severity == ViolationSeverity.CRITICAL:
            self.critical_count += 1
        elif violation.severity == ViolationSeverity.ERROR:
            self.error_count += 1
        elif violation.severity == ViolationSeverity.WARNING:
            self.warning_count += 1
        else:
            self.info_count += 1

        # Update by dimension
        if violation.dimension in self.violations_by_dimension:
            self.violations_by_dimension[violation.dimension].append(violation)

        # Update auto-fixable count
        if violation.auto_fixable:
            self.auto_fixable_count += 1

    def calculate_quality_score(self) -> float:
        """Calculate quality score based on violations."""
        # Start with perfect score
        score = 100.0

        # Deduct points based on violations
        score -= self.critical_count * 20
        score -= self.error_count * 10
        score -= self.warning_count * 2
        score -= self.info_count * 0.5

        self.quality_score = max(0.0, score)
        return self.quality_score

    def get_violations_by_severity(self, severity: ViolationSeverity) -> List[QualityViolation]:
        """Get violations filtered by severity."""
        return [v for v in self.violations if v.severity == severity]

    def get_violations_by_dimension(self, dimension: QualityDimension) -> List[QualityViolation]:
        """Get violations filtered by dimension."""
        return self.violations_by_dimension.get(dimension, [])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "quality_score": self.quality_score,
            "total_violations": len(self.violations),
            "critical": self.critical_count,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "info": self.info_count,
            "auto_fixable": self.auto_fixable_count,
            "files_checked": self.files_checked,
            "violations_by_dimension": {
                dim.value: len(viols)
                for dim, viols in self.violations_by_dimension.items()
            },
        }

    def print_summary(self) -> None:
        """Print validation summary."""
        print(f"\n{'=' * 60}")
        print("CODE QUALITY VALIDATION SUMMARY")
        print(f"{'=' * 60}")

        print(f"\n📊 Overall Score: {self.quality_score:.1f}/100")

        print(f"\n🔍 Violations by Severity:")
        print(f"  🔴 Critical: {self.critical_count}")
        print(f"  🟠 Error:    {self.error_count}")
        print(f"  🟡 Warning:  {self.warning_count}")
        print(f"  🔵 Info:     {self.info_count}")

        print(f"\n📋 Violations by Dimension:")
        for dim, viols in self.violations_by_dimension.items():
            if viols:
                print(f"  {dim.value}: {len(viols)}")

        if self.auto_fixable_count > 0:
            print(f"\n🔧 Auto-fixable: {self.auto_fixable_count}")

        # Show top violations
        if self.violations:
            print(f"\n⚠️  Top Violations:")
            sorted_violations = sorted(
                self.violations,
                key=lambda v: v.severity.value,
                reverse=True,
            )

            for violation in sorted_violations[:10]:
                severity_icon = {
                    ViolationSeverity.CRITICAL: "🔴",
                    ViolationSeverity.ERROR: "🟠",
                    ViolationSeverity.WARNING: "🟡",
                    ViolationSeverity.INFO: "🔵",
                }[violation.severity]

                location = f"{violation.file_path or 'code'}:{violation.line_number or '?'}"
                print(f"  {severity_icon} [{violation.rule_id}] {location}")
                print(f"     {violation.message}")


class QualityValidator:
    """
    Code Quality Validator Tool.

    Comprehensive validation system with configurable rules and quality gates.

    Features:
    - Multi-dimensional quality checks
    - Configurable validation rules
    - Quality gate enforcement
    - Auto-fix suggestions
    - Detailed reporting

    Example:
        ```python
        # Create validator
        validator = QualityValidator()

        # Add rules
        validator.add_rule(PythonSyntaxRule())
        validator.add_rule(LineLengthRule())
        validator.add_rule(SecurityRule())

        # Set quality gate
        gate = QualityGate(
            max_critical=0,
            max_errors=0,
            min_quality_score=80.0,
        )

        # Validate
        result = validator.validate(code, quality_gate=gate)

        result.print_summary()

        if not result.quality_score >= 80:
            print("Code does not meet quality standards!")
        ```
    """

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        """
        Initialize validator.

        Args:
            rules: Validation rules to use
        """
        self.rules = rules or [
            PythonSyntaxRule(),
            LineLengthRule(),
            FunctionComplexityRule(),
            SecurityRule(),
            DocumentationRule(),
        ]

    def add_rule(self, rule: ValidationRule) -> QualityValidator:
        """Add a validation rule."""
        self.rules.append(rule)
        return self

    def validate(
        self,
        code: str,
        file_path: Optional[str] = None,
        quality_gate: Optional[QualityGate] = None,
    ) -> ValidationResult:
        """
        Validate code quality.

        Args:
            code: Source code to validate
            file_path: Optional file path
            quality_gate: Optional quality gate to check

        Returns:
            Validation result
        """
        logger.info(f"Validating code quality{f' for {file_path}' if file_path else ''}")

        result = ValidationResult()
        result.files_checked = 1

        # Run all rules
        for rule in self.rules:
            try:
                violations = rule.validate(code, file_path)
                for violation in violations:
                    result.add_violation(violation)
            except Exception as e:
                logger.error(f"Rule {rule.rule_id} failed: {e}")

        # Calculate quality score
        result.calculate_quality_score()

        logger.info(
            f"Validation complete: "
            f"{len(result.violations)} violations, "
            f"quality score: {result.quality_score:.1f}"
        )

        # Check quality gate if provided
        if quality_gate:
            passed, failures = quality_gate.check(result)
            if not passed:
                logger.warning(f"Quality gate failed: {', '.join(failures)}")

        return result

    def validate_file(
        self,
        file_path: Path,
        quality_gate: Optional[QualityGate] = None,
    ) -> ValidationResult:
        """Validate a file."""
        code = file_path.read_text(encoding="utf-8")
        return self.validate(code, str(file_path), quality_gate)

    def validate_directory(
        self,
        directory: Path,
        pattern: str = "**/*.py",
        quality_gate: Optional[QualityGate] = None,
    ) -> ValidationResult:
        """
        Validate all files in a directory.

        Args:
            directory: Directory to validate
            pattern: File pattern to match
            quality_gate: Optional quality gate

        Returns:
            Combined validation result
        """
        combined_result = ValidationResult()

        files = list(directory.glob(pattern))
        logger.info(f"Validating {len(files)} files in {directory}")

        for file_path in files:
            try:
                result = self.validate_file(file_path, quality_gate=None)
                combined_result.violations.extend(result.violations)
                combined_result.files_checked += 1
            except Exception as e:
                logger.error(f"Error validating {file_path}: {e}")

        # Recalculate counts and score
        combined_result.critical_count = sum(
            1 for v in combined_result.violations
            if v.severity == ViolationSeverity.CRITICAL
        )
        combined_result.error_count = sum(
            1 for v in combined_result.violations
            if v.severity == ViolationSeverity.ERROR
        )
        combined_result.warning_count = sum(
            1 for v in combined_result.violations
            if v.severity == ViolationSeverity.WARNING
        )
        combined_result.info_count = sum(
            1 for v in combined_result.violations
            if v.severity == ViolationSeverity.INFO
        )

        combined_result.calculate_quality_score()

        # Check quality gate
        if quality_gate:
            passed, failures = quality_gate.check(combined_result)
            if not passed:
                logger.warning(f"Quality gate failed: {', '.join(failures)}")

        return combined_result

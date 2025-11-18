"""
Quality Assurance FSA (Finite State Automaton) for comprehensive code quality analysis.

This module provides automated quality assurance for FSA implementations, code quality,
test coverage, documentation completeness, and performance standards. It validates FSA
adherence to framework standards and best practices with detailed quality reports.

Author: Agno Team
License: MIT
"""

import ast
import inspect
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# ============================================================================
# State Management
# ============================================================================


class QAState(Enum):
    """Quality Assurance FSA states."""

    INITIALIZED = "initialized"
    ANALYZING_CODE = "analyzing_code"
    CHECKING_COVERAGE = "checking_coverage"
    VALIDATING_DOCS = "validating_docs"
    PROFILING_PERFORMANCE = "profiling_performance"
    CHECKING_COMPLIANCE = "checking_compliance"
    VALIDATING_PRACTICES = "validating_practices"
    AGGREGATING_METRICS = "aggregating_metrics"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    COMPLETED = "completed"
    ERROR = "error"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class CodeQualityMetrics:
    """Metrics for code quality assessment."""

    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    complexity: int = 0
    maintainability_index: float = 0.0
    functions_count: int = 0
    classes_count: int = 0
    average_function_length: float = 0.0
    max_function_length: int = 0
    duplicate_code_percentage: float = 0.0
    code_smells: List[str] = field(default_factory=list)
    naming_violations: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Test coverage analysis report."""

    total_statements: int = 0
    covered_statements: int = 0
    coverage_percentage: float = 0.0
    uncovered_lines: List[int] = field(default_factory=list)
    uncovered_functions: List[str] = field(default_factory=list)
    uncovered_branches: List[Tuple[int, int]] = field(default_factory=list)
    missing_test_cases: List[str] = field(default_factory=list)
    test_count: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0


@dataclass
class DocumentationReport:
    """Documentation completeness validation report."""

    has_module_docstring: bool = False
    module_docstring_length: int = 0
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    total_methods: int = 0
    documented_methods: int = 0
    documentation_coverage: float = 0.0
    missing_docstrings: List[str] = field(default_factory=list)
    incomplete_docstrings: List[str] = field(default_factory=list)
    has_readme: bool = False
    has_examples: bool = False
    has_api_docs: bool = False


@dataclass
class PerformanceMetrics:
    """Performance profiling metrics."""

    execution_time: float = 0.0
    memory_usage: float = 0.0
    peak_memory: float = 0.0
    cpu_usage: float = 0.0
    io_operations: int = 0
    network_calls: int = 0
    database_queries: int = 0
    bottlenecks: List[str] = field(default_factory=list)
    optimization_opportunities: List[str] = field(default_factory=list)
    performance_score: float = 0.0


@dataclass
class ComplianceReport:
    """Standards compliance validation report."""

    follows_pep8: bool = False
    pep8_violations: List[str] = field(default_factory=list)
    follows_type_hints: bool = False
    type_hint_coverage: float = 0.0
    follows_naming_conventions: bool = False
    naming_violations: List[str] = field(default_factory=list)
    has_proper_structure: bool = False
    structure_violations: List[str] = field(default_factory=list)
    dependency_issues: List[str] = field(default_factory=list)
    compliance_score: float = 0.0


@dataclass
class BestPracticesReport:
    """Best practices validation report."""

    uses_error_handling: bool = False
    error_handling_coverage: float = 0.0
    uses_logging: bool = False
    logging_coverage: float = 0.0
    uses_type_annotations: bool = False
    type_annotation_coverage: float = 0.0
    follows_solid_principles: bool = False
    solid_violations: List[str] = field(default_factory=list)
    follows_dry_principle: bool = False
    dry_violations: List[str] = field(default_factory=list)
    uses_design_patterns: List[str] = field(default_factory=list)
    best_practices_score: float = 0.0


@dataclass
class QualityScore:
    """Aggregated quality score."""

    overall_score: float = 0.0
    code_quality_score: float = 0.0
    test_coverage_score: float = 0.0
    documentation_score: float = 0.0
    performance_score: float = 0.0
    compliance_score: float = 0.0
    best_practices_score: float = 0.0
    grade: str = "F"
    passed_threshold: bool = False
    threshold: float = 70.0


@dataclass
class Improvement:
    """Improvement recommendation."""

    category: str
    priority: str  # "critical", "high", "medium", "low"
    title: str
    description: str
    estimated_impact: float  # 0.0 - 1.0
    estimated_effort: str  # "low", "medium", "high"
    code_examples: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Comprehensive validation result."""

    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    validation_info: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class QualityReport:
    """Comprehensive quality assurance report."""

    fsa_name: str
    fsa_version: str = "1.0.0"
    code_quality: Optional[CodeQualityMetrics] = None
    coverage: Optional[CoverageReport] = None
    documentation: Optional[DocumentationReport] = None
    performance: Optional[PerformanceMetrics] = None
    compliance: Optional[ComplianceReport] = None
    best_practices: Optional[BestPracticesReport] = None
    quality_score: Optional[QualityScore] = None
    improvements: List[Improvement] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    execution_time: float = 0.0


@dataclass
class DetailedQualityReport:
    """Detailed quality analysis report with full breakdown."""

    quality_report: QualityReport
    state_transitions: List[Tuple[QAState, float]] = field(default_factory=list)
    analysis_logs: List[str] = field(default_factory=list)
    raw_metrics: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# FSA Implementation
# ============================================================================


class FSAImplementation:
    """Mock FSA implementation for testing purposes."""

    def __init__(self, name: str, source_code: Optional[str] = None):
        self.name = name
        self.source_code = source_code
        self.module_path: Optional[str] = None
        self.test_module_path: Optional[str] = None

    def get_source_code(self) -> str:
        """Get source code of the FSA."""
        if self.source_code:
            return self.source_code
        if self.module_path and os.path.exists(self.module_path):
            with open(self.module_path, "r") as f:
                return f.read()
        return ""

    def execute(self, *args, **kwargs) -> Any:
        """Mock execute method."""
        return {"status": "success"}


class QualityAssuranceFSA:
    """
    Quality Assurance Finite State Automaton for comprehensive code quality analysis.

    This FSA provides automated quality assurance including code quality assessment,
    test coverage analysis, documentation validation, performance profiling, standards
    compliance checking, and best practices validation.

    Attributes:
        name: Name of the QA FSA instance
        state: Current state of the FSA
        config: Configuration parameters
        state_history: History of state transitions
        analysis_logs: Logs from analysis operations
    """

    def __init__(
        self,
        name: str = "QualityAssuranceFSA",
        quality_threshold: float = 70.0,
        coverage_threshold: float = 80.0,
        performance_threshold: float = 1.0,
        enable_strict_mode: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Quality Assurance FSA.

        Args:
            name: Name of the QA FSA instance
            quality_threshold: Minimum acceptable quality score (0-100)
            coverage_threshold: Minimum acceptable test coverage (0-100)
            performance_threshold: Maximum acceptable execution time in seconds
            enable_strict_mode: Enable strict validation mode
            config: Additional configuration parameters
        """
        self.name = name
        self.state = QAState.INITIALIZED
        self.quality_threshold = quality_threshold
        self.coverage_threshold = coverage_threshold
        self.performance_threshold = performance_threshold
        self.enable_strict_mode = enable_strict_mode
        self.config = config or {}

        # State tracking
        self.state_history: List[Tuple[QAState, float]] = [(QAState.INITIALIZED, time.time())]
        self.analysis_logs: List[str] = []

        # Metrics storage
        self._current_report: Optional[QualityReport] = None

        logger.info(f"Initialized {self.name} with threshold={quality_threshold}")

    def _transition_state(self, new_state: QAState) -> None:
        """
        Transition FSA to a new state.

        Args:
            new_state: Target state to transition to
        """
        old_state = self.state
        self.state = new_state
        timestamp = time.time()
        self.state_history.append((new_state, timestamp))
        self.analysis_logs.append(f"State transition: {old_state.value} -> {new_state.value}")
        logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    def _log_analysis(self, message: str) -> None:
        """Log analysis message."""
        self.analysis_logs.append(f"[{time.time()}] {message}")
        logger.info(message)

    def execute(self, fsa: FSAImplementation) -> QualityReport:
        """
        Main quality assurance pipeline.

        Executes the complete QA pipeline including code analysis, test coverage,
        documentation validation, performance profiling, compliance checking,
        best practices validation, and generates comprehensive quality report.

        Args:
            fsa: FSA implementation to analyze

        Returns:
            QualityReport: Comprehensive quality assurance report

        Raises:
            ValueError: If FSA is invalid or analysis fails
        """
        start_time = time.time()
        self._log_analysis(f"Starting QA analysis for: {fsa.name}")

        try:
            # Validate FSA
            self._log_analysis("Validating FSA implementation")
            validation_result = self.validate(fsa)
            if not validation_result.is_valid and self.enable_strict_mode:
                self._transition_state(QAState.ERROR)
                raise ValueError(f"FSA validation failed: {validation_result.validation_errors}")

            # Get source code
            source_code = fsa.get_source_code()
            if not source_code:
                raise ValueError("Unable to retrieve FSA source code")

            # Initialize report
            report = QualityReport(fsa_name=fsa.name)

            # Code quality analysis
            self._transition_state(QAState.ANALYZING_CODE)
            self._log_analysis("Analyzing code quality")
            report.code_quality = self.analyze_code_quality(source_code)

            # Test coverage analysis
            self._transition_state(QAState.CHECKING_COVERAGE)
            self._log_analysis("Checking test coverage")
            if fsa.module_path and fsa.test_module_path:
                report.coverage = self.check_test_coverage(fsa.module_path, fsa.test_module_path)
            else:
                report.coverage = CoverageReport()

            # Documentation validation
            self._transition_state(QAState.VALIDATING_DOCS)
            self._log_analysis("Validating documentation")
            report.documentation = self.validate_documentation(fsa)

            # Performance profiling
            self._transition_state(QAState.PROFILING_PERFORMANCE)
            self._log_analysis("Profiling performance")
            report.performance = self.profile_performance(fsa)

            # Standards compliance
            self._transition_state(QAState.CHECKING_COMPLIANCE)
            self._log_analysis("Checking standards compliance")
            report.compliance = self.check_standards_compliance(fsa)

            # Best practices validation
            self._transition_state(QAState.VALIDATING_PRACTICES)
            self._log_analysis("Validating best practices")
            report.best_practices = self.validate_best_practices(source_code)

            # Aggregate quality metrics
            self._transition_state(QAState.AGGREGATING_METRICS)
            self._log_analysis("Aggregating quality metrics")
            reports = [
                report.code_quality,
                report.coverage,
                report.documentation,
                report.performance,
                report.compliance,
                report.best_practices,
            ]
            report.quality_score = self.aggregate_quality_metrics(reports)

            # Generate improvement recommendations
            self._transition_state(QAState.GENERATING_RECOMMENDATIONS)
            self._log_analysis("Generating improvement recommendations")
            report.improvements = self.recommend_improvements(report)

            # Complete
            report.execution_time = time.time() - start_time
            self._current_report = report
            self._transition_state(QAState.COMPLETED)
            self._log_analysis(f"QA analysis completed in {report.execution_time:.2f}s")

            return report

        except Exception as e:
            self._transition_state(QAState.ERROR)
            self._log_analysis(f"Error during QA analysis: {str(e)}")
            logger.error(f"QA analysis failed: {str(e)}", exc_info=True)
            raise

    def validate(self, fsa: FSAImplementation) -> ValidationResult:
        """
        Comprehensive quality validation.

        Validates FSA implementation for basic requirements and structure.

        Args:
            fsa: FSA implementation to validate

        Returns:
            ValidationResult: Validation results with errors, warnings, and info
        """
        result = ValidationResult()
        errors = []
        warnings = []
        info = []

        # Check FSA has a name
        if not fsa.name:
            errors.append("FSA must have a name")
        else:
            info.append(f"FSA name: {fsa.name}")

        # Check FSA has source code or module path
        try:
            source_code = fsa.get_source_code()
            if not source_code:
                errors.append("FSA must have source code or valid module path")
            else:
                info.append(f"Source code length: {len(source_code)} characters")
        except Exception as e:
            errors.append(f"Failed to retrieve source code: {str(e)}")

        # Check FSA has execute method
        if not hasattr(fsa, "execute") or not callable(getattr(fsa, "execute")):
            errors.append("FSA must have an executable 'execute' method")
        else:
            info.append("FSA has execute method")

        # Check module path exists if provided
        if fsa.module_path and not os.path.exists(fsa.module_path):
            warnings.append(f"Module path does not exist: {fsa.module_path}")

        # Check test module path exists if provided
        if fsa.test_module_path and not os.path.exists(fsa.test_module_path):
            warnings.append(f"Test module path does not exist: {fsa.test_module_path}")

        result.validation_errors = errors
        result.validation_warnings = warnings
        result.validation_info = info
        result.is_valid = len(errors) == 0

        return result

    def analyze_code_quality(self, source: str) -> CodeQualityMetrics:
        """
        Assess code implementation quality.

        Analyzes source code for various quality metrics including complexity,
        maintainability, code smells, and security issues.

        Args:
            source: Source code to analyze

        Returns:
            CodeQualityMetrics: Code quality assessment metrics
        """
        metrics = CodeQualityMetrics()

        try:
            # Parse AST
            tree = ast.parse(source)

            # Line counting
            lines = source.split("\n")
            metrics.total_lines = len(lines)
            metrics.blank_lines = sum(1 for line in lines if not line.strip())
            metrics.comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
            metrics.code_lines = metrics.total_lines - metrics.blank_lines - metrics.comment_lines

            # Count functions and classes
            metrics.functions_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            metrics.classes_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

            # Calculate complexity
            metrics.complexity = self._calculate_complexity(tree)

            # Calculate maintainability index (simplified)
            if metrics.code_lines > 0:
                volume = metrics.code_lines * 2.5  # Simplified Halstead volume
                metrics.maintainability_index = max(
                    0, (171 - 5.2 * abs(volume) - 0.23 * metrics.complexity - 16.2 * 0) / 171 * 100
                )

            # Detect code smells
            metrics.code_smells = self._detect_code_smells(tree, source)

            # Check naming conventions
            metrics.naming_violations = self._check_naming_conventions(tree)

            # Basic security checks
            metrics.security_issues = self._check_security_issues(tree, source)

        except SyntaxError as e:
            logger.error(f"Syntax error in source code: {str(e)}")
            metrics.code_smells.append(f"Syntax error: {str(e)}")

        return metrics

    def check_test_coverage(self, fsa_module: str, test_module: str) -> CoverageReport:
        """
        Analyze test coverage.

        Analyzes test coverage for the FSA implementation by examining test files
        and identifying uncovered lines, functions, and branches.

        Args:
            fsa_module: Path to the FSA module
            test_module: Path to the test module

        Returns:
            CoverageReport: Test coverage analysis report
        """
        report = CoverageReport()

        try:
            # Check if files exist
            if not os.path.exists(fsa_module):
                logger.warning(f"FSA module not found: {fsa_module}")
                return report

            if not os.path.exists(test_module):
                logger.warning(f"Test module not found: {test_module}")
                return report

            # Read source code
            with open(fsa_module, "r") as f:
                source_code = f.read()

            with open(test_module, "r") as f:
                test_code = f.read()

            # Parse AST
            source_tree = ast.parse(source_code)
            test_tree = ast.parse(test_code)

            # Count statements
            report.total_statements = sum(1 for _ in ast.walk(source_tree) if isinstance(_, ast.stmt))

            # Count test functions
            test_functions = [node for node in ast.walk(test_tree) if isinstance(node, ast.FunctionDef)]
            report.test_count = len([f for f in test_functions if f.name.startswith("test_")])

            # Simple coverage estimation (would need actual execution for real coverage)
            # Estimate based on test function names matching source functions
            source_functions = [
                node.name for node in ast.walk(source_tree) if isinstance(node, ast.FunctionDef)
            ]
            tested_functions = set()

            for test_func in test_functions:
                test_name = test_func.name
                for source_func in source_functions:
                    if source_func.lower() in test_name.lower():
                        tested_functions.add(source_func)

            # Estimate coverage
            if source_functions:
                coverage_ratio = len(tested_functions) / len(source_functions)
                report.coverage_percentage = coverage_ratio * 100
                report.covered_statements = int(report.total_statements * coverage_ratio)

                # Identify uncovered functions
                report.uncovered_functions = [f for f in source_functions if f not in tested_functions]

            # Default to some test passing
            report.passed_tests = report.test_count

        except Exception as e:
            logger.error(f"Error analyzing test coverage: {str(e)}")

        return report

    def validate_documentation(self, fsa: FSAImplementation) -> DocumentationReport:
        """
        Check documentation completeness.

        Validates that FSA has proper documentation including docstrings for
        modules, classes, functions, and methods.

        Args:
            fsa: FSA implementation to validate

        Returns:
            DocumentationReport: Documentation completeness report
        """
        report = DocumentationReport()

        try:
            source_code = fsa.get_source_code()
            if not source_code:
                return report

            # Parse AST
            tree = ast.parse(source_code)

            # Check module docstring
            if ast.get_docstring(tree):
                report.has_module_docstring = True
                report.module_docstring_length = len(ast.get_docstring(tree))

            # Analyze functions
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            report.total_functions = len(functions)
            report.documented_functions = sum(1 for f in functions if ast.get_docstring(f))

            for func in functions:
                if not ast.get_docstring(func):
                    report.missing_docstrings.append(f"Function: {func.name}")
                elif len(ast.get_docstring(func)) < 20:
                    report.incomplete_docstrings.append(f"Function: {func.name} (too short)")

            # Analyze classes and methods
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            report.total_classes = len(classes)
            report.documented_classes = sum(1 for c in classes if ast.get_docstring(c))

            for cls in classes:
                if not ast.get_docstring(cls):
                    report.missing_docstrings.append(f"Class: {cls.name}")

                methods = [node for node in cls.body if isinstance(node, ast.FunctionDef)]
                report.total_methods += len(methods)
                report.documented_methods += sum(1 for m in methods if ast.get_docstring(m))

                for method in methods:
                    if not ast.get_docstring(method):
                        report.missing_docstrings.append(f"Method: {cls.name}.{method.name}")

            # Calculate documentation coverage
            total_items = report.total_functions + report.total_classes + report.total_methods
            documented_items = (
                report.documented_functions + report.documented_classes + report.documented_methods
            )
            if total_items > 0:
                report.documentation_coverage = (documented_items / total_items) * 100

            # Check for README
            if fsa.module_path:
                module_dir = os.path.dirname(fsa.module_path)
                readme_paths = [
                    os.path.join(module_dir, "README.md"),
                    os.path.join(module_dir, "README.rst"),
                    os.path.join(module_dir, "README.txt"),
                ]
                report.has_readme = any(os.path.exists(p) for p in readme_paths)

        except Exception as e:
            logger.error(f"Error validating documentation: {str(e)}")

        return report

    def profile_performance(self, fsa: FSAImplementation) -> PerformanceMetrics:
        """
        Measure execution efficiency.

        Profiles FSA execution to measure performance metrics including execution
        time, memory usage, and identify performance bottlenecks.

        Args:
            fsa: FSA implementation to profile

        Returns:
            PerformanceMetrics: Performance profiling metrics
        """
        metrics = PerformanceMetrics()

        try:
            import sys
            import tracemalloc

            # Start memory tracking
            tracemalloc.start()
            start_time = time.time()

            # Execute FSA
            try:
                result = fsa.execute()
            except Exception as e:
                logger.warning(f"FSA execution failed during profiling: {str(e)}")

            # Stop timing
            metrics.execution_time = time.time() - start_time

            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            metrics.memory_usage = current / 1024 / 1024  # Convert to MB
            metrics.peak_memory = peak / 1024 / 1024  # Convert to MB
            tracemalloc.stop()

            # Identify bottlenecks
            if metrics.execution_time > self.performance_threshold:
                metrics.bottlenecks.append(
                    f"Execution time ({metrics.execution_time:.2f}s) exceeds threshold ({self.performance_threshold}s)"
                )

            if metrics.peak_memory > 100:  # 100 MB threshold
                metrics.bottlenecks.append(
                    f"Peak memory usage ({metrics.peak_memory:.2f}MB) is high"
                )

            # Generate optimization opportunities
            if metrics.execution_time > 0.5:
                metrics.optimization_opportunities.append("Consider caching results for repeated operations")
            if metrics.peak_memory > 50:
                metrics.optimization_opportunities.append("Consider using generators for large data processing")

            # Calculate performance score
            time_score = max(0, 100 - (metrics.execution_time / self.performance_threshold) * 50)
            memory_score = max(0, 100 - (metrics.peak_memory / 100) * 50)
            metrics.performance_score = (time_score + memory_score) / 2

        except Exception as e:
            logger.error(f"Error profiling performance: {str(e)}")

        return metrics

    def check_standards_compliance(self, fsa: FSAImplementation) -> ComplianceReport:
        """
        Validate framework standards.

        Checks FSA implementation for compliance with Python standards (PEP 8),
        type hints, naming conventions, and structural requirements.

        Args:
            fsa: FSA implementation to check

        Returns:
            ComplianceReport: Standards compliance report
        """
        report = ComplianceReport()

        try:
            source_code = fsa.get_source_code()
            if not source_code:
                return report

            # Parse AST
            tree = ast.parse(source_code)

            # Check PEP 8 compliance (basic checks)
            lines = source_code.split("\n")
            for i, line in enumerate(lines, 1):
                # Line length check
                if len(line) > 120:
                    report.pep8_violations.append(f"Line {i}: Line too long ({len(line)} > 120)")

                # Multiple statements on one line
                if ";" in line and not line.strip().startswith("#"):
                    report.pep8_violations.append(f"Line {i}: Multiple statements on one line")

            report.follows_pep8 = len(report.pep8_violations) == 0

            # Check type hints
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            type_hinted_funcs = []

            for func in functions:
                has_return_type = func.returns is not None
                has_arg_types = all(arg.annotation is not None for arg in func.args.args if arg.arg != "self")
                if has_return_type or has_arg_types:
                    type_hinted_funcs.append(func)

            if functions:
                report.type_hint_coverage = (len(type_hinted_funcs) / len(functions)) * 100
                report.follows_type_hints = report.type_hint_coverage >= 80

            # Check naming conventions
            report.naming_violations = self._check_naming_conventions(tree)
            report.follows_naming_conventions = len(report.naming_violations) == 0

            # Check proper structure (has classes, proper imports, etc.)
            has_imports = any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
            has_classes = any(isinstance(node, ast.ClassDef) for node in tree.body)
            has_functions = any(isinstance(node, ast.FunctionDef) for node in tree.body)

            if not has_imports:
                report.structure_violations.append("No imports found - module should have imports")
            if not (has_classes or has_functions):
                report.structure_violations.append("No classes or functions found")

            report.has_proper_structure = len(report.structure_violations) == 0

            # Calculate compliance score
            scores = [
                100 if report.follows_pep8 else max(0, 100 - len(report.pep8_violations) * 10),
                report.type_hint_coverage,
                100 if report.follows_naming_conventions else max(0, 100 - len(report.naming_violations) * 10),
                100 if report.has_proper_structure else 50,
            ]
            report.compliance_score = sum(scores) / len(scores)

        except Exception as e:
            logger.error(f"Error checking standards compliance: {str(e)}")

        return report

    def validate_best_practices(self, code: str) -> BestPracticesReport:
        """
        Check design pattern adherence.

        Validates that code follows best practices including error handling,
        logging, SOLID principles, DRY principle, and common design patterns.

        Args:
            code: Source code to validate

        Returns:
            BestPracticesReport: Best practices validation report
        """
        report = BestPracticesReport()

        try:
            # Parse AST
            tree = ast.parse(code)

            # Check error handling
            try_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Try)]
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            if try_nodes:
                report.uses_error_handling = True
                report.error_handling_coverage = (len(try_nodes) / max(len(functions), 1)) * 100

            # Check logging usage
            has_logging_import = any(
                isinstance(node, (ast.Import, ast.ImportFrom))
                and any(
                    alias.name == "logging" or getattr(node, "module", None) == "logging"
                    for alias in (node.names if hasattr(node, "names") else [])
                )
                for node in ast.walk(tree)
            )

            if has_logging_import:
                report.uses_logging = True
                # Count logging calls
                logging_calls = sum(
                    1
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ["debug", "info", "warning", "error", "critical"]
                )
                report.logging_coverage = (logging_calls / max(len(functions), 1)) * 100

            # Check type annotations
            type_annotated_funcs = sum(
                1 for func in functions if func.returns or any(arg.annotation for arg in func.args.args)
            )
            if type_annotated_funcs > 0:
                report.uses_type_annotations = True
                report.type_annotation_coverage = (type_annotated_funcs / len(functions)) * 100

            # Check SOLID principles (simplified)
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            # Single Responsibility - check if classes are too large
            for cls in classes:
                method_count = sum(1 for node in cls.body if isinstance(node, ast.FunctionDef))
                if method_count > 15:
                    report.solid_violations.append(
                        f"Class {cls.name} may violate SRP (has {method_count} methods)"
                    )

            report.follows_solid_principles = len(report.solid_violations) == 0

            # Check DRY principle - look for duplicate code patterns
            function_bodies = []
            for func in functions:
                body_str = ast.unparse(func) if hasattr(ast, "unparse") else str(func)
                function_bodies.append(body_str)

            # Simple duplicate detection
            seen = set()
            for body in function_bodies:
                if body in seen and len(body) > 50:
                    report.dry_violations.append(f"Potential duplicate code detected")
                seen.add(body)

            report.follows_dry_principle = len(report.dry_violations) == 0

            # Identify design patterns
            if any("Factory" in cls.name for cls in classes):
                report.uses_design_patterns.append("Factory Pattern")
            if any("Singleton" in cls.name for cls in classes):
                report.uses_design_patterns.append("Singleton Pattern")
            if any("Observer" in cls.name for cls in classes):
                report.uses_design_patterns.append("Observer Pattern")
            if classes and any(isinstance(node, ast.ClassDef) for node in tree.body):
                report.uses_design_patterns.append("Object-Oriented Design")

            # Calculate best practices score
            scores = [
                report.error_handling_coverage,
                report.logging_coverage,
                report.type_annotation_coverage,
                100 if report.follows_solid_principles else 50,
                100 if report.follows_dry_principle else 50,
            ]
            report.best_practices_score = sum(scores) / len(scores)

        except Exception as e:
            logger.error(f"Error validating best practices: {str(e)}")

        return report

    def aggregate_quality_metrics(self, reports: List[Any]) -> QualityScore:
        """
        Calculate overall quality score.

        Aggregates quality metrics from all reports to compute an overall quality
        score with weighted metrics.

        Args:
            reports: List of quality reports to aggregate

        Returns:
            QualityScore: Aggregated quality score with grade
        """
        score = QualityScore(threshold=self.quality_threshold)

        try:
            # Extract individual scores
            code_quality_score = 0.0
            test_coverage_score = 0.0
            documentation_score = 0.0
            performance_score = 0.0
            compliance_score = 0.0
            best_practices_score = 0.0

            for report in reports:
                if isinstance(report, CodeQualityMetrics):
                    # Calculate code quality score based on maintainability
                    code_quality_score = report.maintainability_index
                    # Deduct for issues
                    code_quality_score -= len(report.code_smells) * 5
                    code_quality_score -= len(report.security_issues) * 10
                    code_quality_score = max(0, min(100, code_quality_score))

                elif isinstance(report, CoverageReport):
                    test_coverage_score = report.coverage_percentage

                elif isinstance(report, DocumentationReport):
                    documentation_score = report.documentation_coverage

                elif isinstance(report, PerformanceMetrics):
                    performance_score = report.performance_score

                elif isinstance(report, ComplianceReport):
                    compliance_score = report.compliance_score

                elif isinstance(report, BestPracticesReport):
                    best_practices_score = report.best_practices_score

            # Store individual scores
            score.code_quality_score = code_quality_score
            score.test_coverage_score = test_coverage_score
            score.documentation_score = documentation_score
            score.performance_score = performance_score
            score.compliance_score = compliance_score
            score.best_practices_score = best_practices_score

            # Calculate weighted overall score
            weights = {
                "code_quality": 0.20,
                "test_coverage": 0.25,
                "documentation": 0.15,
                "performance": 0.15,
                "compliance": 0.15,
                "best_practices": 0.10,
            }

            score.overall_score = (
                code_quality_score * weights["code_quality"]
                + test_coverage_score * weights["test_coverage"]
                + documentation_score * weights["documentation"]
                + performance_score * weights["performance"]
                + compliance_score * weights["compliance"]
                + best_practices_score * weights["best_practices"]
            )

            # Assign grade
            if score.overall_score >= 90:
                score.grade = "A"
            elif score.overall_score >= 80:
                score.grade = "B"
            elif score.overall_score >= 70:
                score.grade = "C"
            elif score.overall_score >= 60:
                score.grade = "D"
            else:
                score.grade = "F"

            # Check threshold
            score.passed_threshold = score.overall_score >= self.quality_threshold

        except Exception as e:
            logger.error(f"Error aggregating quality metrics: {str(e)}")

        return score

    def recommend_improvements(self, quality_report: QualityReport) -> List[Improvement]:
        """
        Generate enhancement suggestions.

        Analyzes quality report to generate prioritized improvement recommendations
        with estimated impact and effort.

        Args:
            quality_report: Quality report to analyze

        Returns:
            List[Improvement]: List of prioritized improvement recommendations
        """
        improvements = []

        try:
            # Test coverage improvements
            if quality_report.coverage and quality_report.coverage.coverage_percentage < 80:
                improvements.append(
                    Improvement(
                        category="Test Coverage",
                        priority="high",
                        title="Increase test coverage",
                        description=f"Current coverage is {quality_report.coverage.coverage_percentage:.1f}%. "
                        f"Add tests for uncovered functions: {', '.join(quality_report.coverage.uncovered_functions[:3])}",
                        estimated_impact=0.8,
                        estimated_effort="medium",
                        code_examples=[
                            "def test_uncovered_function():\n    result = function_to_test()\n    assert result == expected_value"
                        ],
                    )
                )

            # Documentation improvements
            if quality_report.documentation and quality_report.documentation.documentation_coverage < 80:
                improvements.append(
                    Improvement(
                        category="Documentation",
                        priority="medium",
                        title="Add missing docstrings",
                        description=f"Documentation coverage is {quality_report.documentation.documentation_coverage:.1f}%. "
                        f"Add docstrings to: {', '.join(quality_report.documentation.missing_docstrings[:3])}",
                        estimated_impact=0.6,
                        estimated_effort="low",
                        code_examples=[
                            '"""Brief description.\n\nArgs:\n    param: Description\n\nReturns:\n    Description\n"""'
                        ],
                    )
                )

            # Code quality improvements
            if quality_report.code_quality and quality_report.code_quality.code_smells:
                improvements.append(
                    Improvement(
                        category="Code Quality",
                        priority="high",
                        title="Address code smells",
                        description=f"Found {len(quality_report.code_quality.code_smells)} code smells. "
                        f"Examples: {', '.join(quality_report.code_quality.code_smells[:2])}",
                        estimated_impact=0.7,
                        estimated_effort="medium",
                    )
                )

            # Security improvements
            if quality_report.code_quality and quality_report.code_quality.security_issues:
                improvements.append(
                    Improvement(
                        category="Security",
                        priority="critical",
                        title="Fix security issues",
                        description=f"Found {len(quality_report.code_quality.security_issues)} security issues: "
                        f"{', '.join(quality_report.code_quality.security_issues)}",
                        estimated_impact=1.0,
                        estimated_effort="high",
                    )
                )

            # Performance improvements
            if quality_report.performance and quality_report.performance.bottlenecks:
                improvements.append(
                    Improvement(
                        category="Performance",
                        priority="medium",
                        title="Optimize performance bottlenecks",
                        description=f"Performance issues detected: {', '.join(quality_report.performance.bottlenecks)}",
                        estimated_impact=0.7,
                        estimated_effort="medium",
                    )
                )

            # Compliance improvements
            if quality_report.compliance and not quality_report.compliance.follows_pep8:
                improvements.append(
                    Improvement(
                        category="Compliance",
                        priority="low",
                        title="Fix PEP 8 violations",
                        description=f"Found {len(quality_report.compliance.pep8_violations)} PEP 8 violations",
                        estimated_impact=0.4,
                        estimated_effort="low",
                    )
                )

            # Best practices improvements
            if quality_report.best_practices and not quality_report.best_practices.uses_error_handling:
                improvements.append(
                    Improvement(
                        category="Best Practices",
                        priority="high",
                        title="Add error handling",
                        description="Implement proper error handling with try-except blocks",
                        estimated_impact=0.8,
                        estimated_effort="medium",
                        code_examples=[
                            "try:\n    risky_operation()\nexcept Exception as e:\n    logger.error(f'Error: {e}')\n    raise"
                        ],
                    )
                )

            # Sort by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            improvements.sort(key=lambda x: (priority_order.get(x.priority, 99), -x.estimated_impact))

        except Exception as e:
            logger.error(f"Error generating improvement recommendations: {str(e)}")

        return improvements

    def generate_detailed_report(self, fsa: FSAImplementation) -> DetailedQualityReport:
        """
        Comprehensive quality analysis.

        Generates a detailed quality report including full analysis, state transitions,
        logs, and raw metrics.

        Args:
            fsa: FSA implementation to analyze

        Returns:
            DetailedQualityReport: Comprehensive detailed quality report
        """
        # Execute full QA pipeline
        quality_report = self.execute(fsa)

        # Create detailed report
        detailed_report = DetailedQualityReport(
            quality_report=quality_report,
            state_transitions=self.state_history.copy(),
            analysis_logs=self.analysis_logs.copy(),
            raw_metrics={
                "state_count": len(self.state_history),
                "log_count": len(self.analysis_logs),
                "threshold": self.quality_threshold,
                "strict_mode": self.enable_strict_mode,
            },
        )

        return detailed_report

    def error_handling(self) -> None:
        """
        Robust error recovery for validation failures.

        Implements error recovery mechanisms to handle validation failures
        gracefully and transition to safe states.
        """
        if self.state == QAState.ERROR:
            self._log_analysis("Initiating error recovery")

            # Reset to initialized state
            self._transition_state(QAState.INITIALIZED)
            self._log_analysis("FSA reset to initialized state")

            # Clear any partial results
            self._current_report = None

            logger.info("Error recovery completed successfully")

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _detect_code_smells(self, tree: ast.AST, source: str) -> List[str]:
        """Detect code smells in AST."""
        smells = []

        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            # Long function
            func_lines = len([n for n in ast.walk(func) if isinstance(n, ast.stmt)])
            if func_lines > 50:
                smells.append(f"Long function: {func.name} ({func_lines} lines)")

            # Too many parameters
            if len(func.args.args) > 5:
                smells.append(f"Too many parameters: {func.name} ({len(func.args.args)} params)")

        return smells

    def _check_naming_conventions(self, tree: ast.AST) -> List[str]:
        """Check naming convention violations."""
        violations = []

        # Check function names (should be snake_case)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not re.match(r"^[a-z_][a-z0-9_]*$", node.name) and not node.name.startswith("__"):
                    violations.append(f"Function name should be snake_case: {node.name}")

            # Check class names (should be PascalCase)
            elif isinstance(node, ast.ClassDef):
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                    violations.append(f"Class name should be PascalCase: {node.name}")

        return violations

    def _check_security_issues(self, tree: ast.AST, source: str) -> List[str]:
        """Basic security issue detection."""
        issues = []

        # Check for eval/exec usage
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec"]:
                        issues.append(f"Dangerous function used: {node.func.id}")

        # Check for SQL injection patterns
        if "execute(" in source and ("%" in source or "format(" in source):
            issues.append("Potential SQL injection vulnerability")

        return issues

"""
Code Analyzer FSA - Deep static code analysis and quality metrics

This FSA provides comprehensive static code analysis including complexity metrics,
code smell detection, design pattern recognition, security vulnerability scanning,
and automated refactoring suggestions for FSA implementations.

Author: Agno Team
License: MPL 2.0
"""

from __future__ import annotations

import ast
import json
import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SmellSeverity(str, Enum):
    """Severity levels for code smells"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SecuritySeverity(str, Enum):
    """Severity levels for security issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplexityMetrics:
    """Code complexity metrics"""

    cyclomatic: int = 0
    cognitive: int = 0
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    halstead_effort: float = 0.0
    maintainability_index: float = 100.0
    loc: int = 0
    sloc: int = 0
    comment_ratio: float = 0.0
    nesting_depth: int = 0
    max_params: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CodeSmell:
    """Detected code smell"""

    type: str
    location: str
    severity: SmellSeverity
    description: str
    suggestion: str
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data


@dataclass
class DesignPattern:
    """Detected design pattern"""

    pattern_type: str
    confidence: float
    locations: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SecurityIssue:
    """Security vulnerability"""

    vulnerability_type: str
    severity: SecuritySeverity
    location: str
    recommendation: str
    cwe_id: Optional[str] = None
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data


@dataclass
class RefactoringSuggestion:
    """Refactoring suggestion"""

    type: str
    target: str
    description: str
    expected_benefit: str
    effort: str  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TypeCoverageReport:
    """Type annotation coverage report"""

    total_functions: int
    annotated_functions: int
    coverage_percent: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class DocQualityReport:
    """Documentation quality report"""

    total_items: int
    documented_items: int
    coverage_percent: float
    avg_quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CodeAnalysisReport:
    """Comprehensive code analysis report"""

    file_path: str
    complexity_metrics: ComplexityMetrics
    code_smells: List[CodeSmell] = field(default_factory=list)
    patterns: List[DesignPattern] = field(default_factory=list)
    security_issues: List[SecurityIssue] = field(default_factory=list)
    refactoring_suggestions: List[RefactoringSuggestion] = field(default_factory=list)
    type_coverage: Optional[TypeCoverageReport] = None
    doc_quality: Optional[DocQualityReport] = None
    quality_score: float = 0.0
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'file_path': self.file_path,
            'complexity_metrics': self.complexity_metrics.to_dict(),
            'code_smells': [s.to_dict() for s in self.code_smells],
            'patterns': [p.to_dict() for p in self.patterns],
            'security_issues': [s.to_dict() for s in self.security_issues],
            'refactoring_suggestions': [r.to_dict() for r in self.refactoring_suggestions],
            'type_coverage': self.type_coverage.to_dict() if self.type_coverage else None,
            'doc_quality': self.doc_quality.to_dict() if self.doc_quality else None,
            'quality_score': self.quality_score,
            'analyzed_at': self.analyzed_at.isoformat()
        }

    def to_json(self, path: Optional[str] = None) -> str:
        """Export to JSON"""
        json_str = json.dumps(self.to_dict(), indent=2)
        if path:
            Path(path).write_text(json_str)
        return json_str


class CodeAnalyzerError(Exception):
    """Base exception for Code Analyzer"""
    pass


class CodeAnalyzerFSA:
    """
    Code Analyzer FSA - Deep static analysis and quality metrics

    Category: Meta

    Key Capabilities:
        - AST-based Python code parsing
        - Complexity metrics (cyclomatic, cognitive, halstead)
        - Code smell detection
        - Design pattern recognition
        - Security vulnerability scanning
        - Dead code detection
        - Type annotation analysis
        - Documentation quality analysis
        - Quality scoring
        - Automated refactoring suggestions
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Code Analyzer FSA

        Args:
            config: Optional configuration dictionary
                - max_complexity: int (default 10)
                - max_method_lines: int (default 50)
                - max_class_lines: int (default 500)
                - max_params: int (default 5)
                - max_nesting: int (default 4)
        """
        self.name = "CodeAnalyzerFSA"
        self.config = config or {}
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()

        # Configuration thresholds
        self.max_complexity = self.config.get('max_complexity', 10)
        self.max_method_lines = self.config.get('max_method_lines', 50)
        self.max_class_lines = self.config.get('max_class_lines', 500)
        self.max_params = self.config.get('max_params', 5)
        self.max_nesting = self.config.get('max_nesting', 4)

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
            CodeAnalyzerError: If execution fails
        """
        if not task:
            raise CodeAnalyzerError("Task cannot be empty")

        logger.info(f"Executing task: {task}")
        params = params or {}

        if not self.validate_input(params):
            raise CodeAnalyzerError("Invalid input parameters")

        try:
            if task == "analyze_code":
                return self.analyze_code(params.get('code'))
            elif task == "calculate_complexity":
                return self.calculate_complexity(params.get('ast_node'))
            elif task == "detect_code_smells":
                return self.detect_code_smells(params.get('ast_node'))
            else:
                return self._process_task(task, params)
        except Exception as e:
            return self.handle_error(e)

    def analyze_code(self, code: Union[str, Path]) -> CodeAnalysisReport:
        """
        Main code analysis entry point

        Args:
            code: Python code as string or path to file

        Returns:
            Comprehensive CodeAnalysisReport

        Raises:
            CodeAnalyzerError: If analysis fails
        """
        # Load code
        if isinstance(code, (str, Path)) and Path(code).exists():
            file_path = str(code)
            code_str = Path(code).read_text()
        elif isinstance(code, str):
            file_path = "<string>"
            code_str = code
        else:
            raise CodeAnalyzerError("Invalid code input")

        logger.info(f"Analyzing code: {file_path}")

        # Parse AST
        try:
            tree = self.parse_ast(code_str)
        except SyntaxError as e:
            raise CodeAnalyzerError(f"Syntax error in code: {e}")

        # Calculate metrics
        complexity = self.calculate_complexity(tree)
        code_smells = self.detect_code_smells(tree)
        patterns = self.detect_patterns(tree)
        security_issues = self.analyze_security(tree)
        type_coverage = self.check_type_annotations(tree)
        doc_quality = self.analyze_documentation(tree)

        # Create report
        report = CodeAnalysisReport(
            file_path=file_path,
            complexity_metrics=complexity,
            code_smells=code_smells,
            patterns=patterns,
            security_issues=security_issues,
            type_coverage=type_coverage,
            doc_quality=doc_quality
        )

        # Calculate quality score
        report.quality_score = self.calculate_quality_score(report)

        # Generate refactoring suggestions
        report.refactoring_suggestions = self.suggest_refactorings(report)

        logger.info(f"Analysis complete: quality score = {report.quality_score:.1f}")
        return report

    def parse_ast(self, code: str) -> ast.Module:
        """
        Parse Python code to AST

        Args:
            code: Python code as string

        Returns:
            Parsed AST module

        Raises:
            SyntaxError: If code has syntax errors
        """
        return ast.parse(code)

    def calculate_complexity(self, ast_node: ast.AST) -> ComplexityMetrics:
        """
        Calculate comprehensive complexity metrics

        Args:
            ast_node: AST node to analyze

        Returns:
            ComplexityMetrics with all calculated metrics
        """
        metrics = ComplexityMetrics()

        # Calculate cyclomatic complexity
        metrics.cyclomatic = self._calculate_cyclomatic(ast_node)

        # Calculate cognitive complexity
        metrics.cognitive = self._calculate_cognitive(ast_node)

        # Calculate Halstead metrics
        halstead = self._calculate_halstead(ast_node)
        metrics.halstead_volume = halstead['volume']
        metrics.halstead_difficulty = halstead['difficulty']
        metrics.halstead_effort = halstead['effort']

        # Count lines of code
        if isinstance(ast_node, ast.Module):
            source_lines = ast.unparse(ast_node).split('\n')
            metrics.loc = len(source_lines)
            metrics.sloc = len([l for l in source_lines if l.strip() and not l.strip().startswith('#')])

            # Comment ratio
            comments = len([l for l in source_lines if l.strip().startswith('#')])
            metrics.comment_ratio = comments / max(metrics.loc, 1) * 100

        # Calculate nesting depth
        metrics.nesting_depth = self._calculate_nesting_depth(ast_node)

        # Find max parameters
        metrics.max_params = self._find_max_params(ast_node)

        # Calculate maintainability index
        metrics.maintainability_index = self._calculate_maintainability_index(metrics)

        return metrics

    def detect_code_smells(self, ast_node: ast.AST) -> List[CodeSmell]:
        """
        Detect code smells in AST

        Args:
            ast_node: AST node to analyze

        Returns:
            List of detected code smells
        """
        smells = []

        # Detect long methods
        for node in ast.walk(ast_node):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno + 1
                if func_lines > self.max_method_lines:
                    smells.append(CodeSmell(
                        type="Long Method",
                        location=f"Function '{node.name}'",
                        severity=SmellSeverity.MEDIUM,
                        description=f"Method has {func_lines} lines (threshold: {self.max_method_lines})",
                        suggestion="Break method into smaller, focused functions",
                        line_number=node.lineno
                    ))

        # Detect god classes
        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                class_lines = node.end_lineno - node.lineno + 1
                if class_lines > self.max_class_lines:
                    smells.append(CodeSmell(
                        type="God Class",
                        location=f"Class '{node.name}'",
                        severity=SmellSeverity.HIGH,
                        description=f"Class has {class_lines} lines (threshold: {self.max_class_lines})",
                        suggestion="Split class into smaller, cohesive classes with single responsibilities",
                        line_number=node.lineno
                    ))

        # Detect long parameter lists
        for node in ast.walk(ast_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_count = len(node.args.args)
                if param_count > self.max_params:
                    smells.append(CodeSmell(
                        type="Long Parameter List",
                        location=f"Function '{node.name}'",
                        severity=SmellSeverity.MEDIUM,
                        description=f"Function has {param_count} parameters (threshold: {self.max_params})",
                        suggestion="Consider using parameter objects or builder pattern",
                        line_number=node.lineno
                    ))

        # Detect deep nesting
        for node in ast.walk(ast_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                depth = self._calculate_nesting_depth(node)
                if depth > self.max_nesting:
                    smells.append(CodeSmell(
                        type="Deep Nesting",
                        location=f"Function '{node.name}'",
                        severity=SmellSeverity.MEDIUM,
                        description=f"Nesting depth is {depth} (threshold: {self.max_nesting})",
                        suggestion="Extract nested logic into separate functions",
                        line_number=node.lineno
                    ))

        # Detect magic numbers
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if node.value not in [0, 1, -1, 2, 10, 100, 1000] and not isinstance(node.value, bool):
                    smells.append(CodeSmell(
                        type="Magic Number",
                        location=f"Line {node.lineno}",
                        severity=SmellSeverity.LOW,
                        description=f"Magic number {node.value} found",
                        suggestion="Replace with named constant",
                        line_number=node.lineno
                    ))

        return smells

    def detect_patterns(self, ast_node: ast.AST) -> List[DesignPattern]:
        """
        Detect design patterns in code

        Args:
            ast_node: AST node to analyze

        Returns:
            List of detected design patterns
        """
        patterns = []

        # Detect Singleton pattern
        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                has_instance_attr = any(
                    isinstance(n, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == '_instance' for t in n.targets)
                    for n in node.body
                )
                has_new_method = any(
                    isinstance(n, ast.FunctionDef) and n.name == '__new__'
                    for n in node.body
                )

                if has_instance_attr and has_new_method:
                    patterns.append(DesignPattern(
                        pattern_type="Singleton",
                        confidence=0.8,
                        locations=[f"Class '{node.name}'"],
                        description="Singleton pattern detected through __new__ override"
                    ))

        # Detect Factory pattern
        for node in ast.walk(ast_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if 'create' in node.name.lower() or 'factory' in node.name.lower():
                    # Check if it returns class instances
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
                    if has_return:
                        patterns.append(DesignPattern(
                            pattern_type="Factory",
                            confidence=0.6,
                            locations=[f"Function '{node.name}'"],
                            description="Factory pattern suggested by naming convention"
                        ))

        # Detect Strategy pattern
        for node in ast.walk(ast_node):
            if isinstance(node, ast.ClassDef):
                # Look for classes with abstract methods or protocols
                has_abc = any(
                    isinstance(n, ast.FunctionDef) and
                    any(isinstance(d, ast.Name) and d.id in ['abstractmethod', 'abc'] for d in (n.decorator_list or []))
                    for n in node.body
                )
                if has_abc:
                    patterns.append(DesignPattern(
                        pattern_type="Strategy",
                        confidence=0.7,
                        locations=[f"Class '{node.name}'"],
                        description="Strategy pattern indicated by abstract methods"
                    ))

        return patterns

    def analyze_security(self, ast_node: ast.AST) -> List[SecurityIssue]:
        """
        Scan for security vulnerabilities

        Args:
            ast_node: AST node to analyze

        Returns:
            List of detected security issues
        """
        issues = []

        # Detect SQL injection risks
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['execute', 'executemany']:
                        # Check for string formatting in SQL
                        for arg in node.args:
                            if isinstance(arg, (ast.BinOp, ast.JoinedStr)):
                                issues.append(SecurityIssue(
                                    vulnerability_type="SQL Injection",
                                    severity=SecuritySeverity.HIGH,
                                    location=f"Line {node.lineno}",
                                    recommendation="Use parameterized queries instead of string formatting",
                                    cwe_id="CWE-89",
                                    line_number=node.lineno
                                ))

        # Detect command injection risks
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['system', 'popen']:
                        issues.append(SecurityIssue(
                            vulnerability_type="Command Injection",
                            severity=SecuritySeverity.CRITICAL,
                            location=f"Line {node.lineno}",
                            recommendation="Use subprocess with shell=False and validate inputs",
                            cwe_id="CWE-78",
                            line_number=node.lineno
                        ))

        # Detect eval/exec usage
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
                    issues.append(SecurityIssue(
                        vulnerability_type="Code Injection",
                        severity=SecuritySeverity.CRITICAL,
                        location=f"Line {node.lineno}",
                        recommendation="Avoid eval/exec or use ast.literal_eval for safe evaluation",
                        cwe_id="CWE-94",
                        line_number=node.lineno
                    ))

        # Detect hardcoded secrets
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(keyword in name_lower for keyword in ['password', 'secret', 'api_key', 'token']):
                            if isinstance(node.value, ast.Constant):
                                issues.append(SecurityIssue(
                                    vulnerability_type="Hardcoded Secret",
                                    severity=SecuritySeverity.HIGH,
                                    location=f"Variable '{target.id}' at line {node.lineno}",
                                    recommendation="Use environment variables or secure secret management",
                                    cwe_id="CWE-798",
                                    line_number=node.lineno
                                ))

        return issues

    def calculate_quality_score(self, report: CodeAnalysisReport) -> float:
        """
        Calculate overall quality score (0-100)

        Args:
            report: Code analysis report

        Returns:
            Quality score from 0 to 100
        """
        score = 100.0

        # Complexity penalty (30% weight)
        complexity_score = 100.0
        if report.complexity_metrics.cyclomatic > self.max_complexity:
            complexity_score -= min(50, (report.complexity_metrics.cyclomatic - self.max_complexity) * 5)
        if report.complexity_metrics.maintainability_index < 70:
            complexity_score -= (70 - report.complexity_metrics.maintainability_index) * 0.5

        score = score * 0.3 + complexity_score * 0.3

        # Code smells penalty (25% weight)
        smell_score = 100.0
        critical_smells = len([s for s in report.code_smells if s.severity == SmellSeverity.CRITICAL])
        high_smells = len([s for s in report.code_smells if s.severity == SmellSeverity.HIGH])
        medium_smells = len([s for s in report.code_smells if s.severity == SmellSeverity.MEDIUM])

        smell_score -= critical_smells * 20
        smell_score -= high_smells * 10
        smell_score -= medium_smells * 5

        score = score * 0.75 + max(0, smell_score) * 0.25

        # Security penalty (20% weight)
        security_score = 100.0
        critical_sec = len([s for s in report.security_issues if s.severity == SecuritySeverity.CRITICAL])
        high_sec = len([s for s in report.security_issues if s.severity == SecuritySeverity.HIGH])

        security_score -= critical_sec * 30
        security_score -= high_sec * 15

        score = score * 0.8 + max(0, security_score) * 0.2

        # Documentation bonus (15% weight)
        doc_score = 0.0
        if report.doc_quality:
            doc_score = report.doc_quality.coverage_percent

        score = score * 0.85 + doc_score * 0.15

        # Type annotation bonus (10% weight)
        type_score = 0.0
        if report.type_coverage:
            type_score = report.type_coverage.coverage_percent

        score = score * 0.9 + type_score * 0.1

        return max(0.0, min(100.0, score))

    def suggest_refactorings(self, report: CodeAnalysisReport) -> List[RefactoringSuggestion]:
        """
        Generate automated refactoring suggestions

        Args:
            report: Code analysis report

        Returns:
            List of refactoring suggestions
        """
        suggestions = []

        # Suggest refactoring for high complexity
        if report.complexity_metrics.cyclomatic > self.max_complexity:
            suggestions.append(RefactoringSuggestion(
                type="Extract Method",
                target="High complexity functions",
                description="Break down complex functions into smaller, focused methods",
                expected_benefit=f"Reduce cyclomatic complexity from {report.complexity_metrics.cyclomatic} to < {self.max_complexity}",
                effort="medium"
            ))

        # Suggest refactoring for code smells
        god_classes = [s for s in report.code_smells if s.type == "God Class"]
        if god_classes:
            suggestions.append(RefactoringSuggestion(
                type="Split Class",
                target=", ".join(s.location for s in god_classes[:3]),
                description="Decompose large classes into smaller, cohesive classes",
                expected_benefit="Improve maintainability and testability",
                effort="high"
            ))

        # Suggest refactoring for long parameter lists
        long_params = [s for s in report.code_smells if s.type == "Long Parameter List"]
        if long_params:
            suggestions.append(RefactoringSuggestion(
                type="Introduce Parameter Object",
                target=", ".join(s.location for s in long_params[:3]),
                description="Group related parameters into parameter objects",
                expected_benefit="Improve function signature clarity and reduce parameter count",
                effort="low"
            ))

        # Suggest security fixes
        if report.security_issues:
            critical = [s for s in report.security_issues if s.severity == SecuritySeverity.CRITICAL]
            if critical:
                suggestions.append(RefactoringSuggestion(
                    type="Security Fix",
                    target="Critical security vulnerabilities",
                    description="Address critical security issues immediately",
                    expected_benefit="Eliminate security vulnerabilities",
                    effort="high"
                ))

        return suggestions

    def check_type_annotations(self, ast_node: ast.AST) -> TypeCoverageReport:
        """
        Check type annotation coverage

        Args:
            ast_node: AST node to analyze

        Returns:
            Type coverage report
        """
        total_functions = 0
        annotated_functions = 0

        for node in ast.walk(ast_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1

                # Check for return annotation
                has_return_annotation = node.returns is not None

                # Check for parameter annotations
                has_param_annotations = any(arg.annotation is not None for arg in node.args.args)

                if has_return_annotation or has_param_annotations:
                    annotated_functions += 1

        coverage_percent = (annotated_functions / max(total_functions, 1)) * 100

        return TypeCoverageReport(
            total_functions=total_functions,
            annotated_functions=annotated_functions,
            coverage_percent=coverage_percent
        )

    def analyze_documentation(self, ast_node: ast.AST) -> DocQualityReport:
        """
        Analyze documentation quality

        Args:
            ast_node: AST node to analyze

        Returns:
            Documentation quality report
        """
        total_items = 0
        documented_items = 0
        quality_scores = []

        # Check module docstring
        if isinstance(ast_node, ast.Module):
            total_items += 1
            if ast.get_docstring(ast_node):
                documented_items += 1
                quality_scores.append(self._score_docstring(ast.get_docstring(ast_node)))

        # Check class and function docstrings
        for node in ast.walk(ast_node):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                total_items += 1
                docstring = ast.get_docstring(node)
                if docstring:
                    documented_items += 1
                    quality_scores.append(self._score_docstring(docstring))

        coverage_percent = (documented_items / max(total_items, 1)) * 100
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        return DocQualityReport(
            total_items=total_items,
            documented_items=documented_items,
            coverage_percent=coverage_percent,
            avg_quality_score=avg_quality
        )

    def detect_dead_code(self, ast_node: ast.AST) -> List[str]:
        """
        Detect dead code (unused variables, functions)

        Args:
            ast_node: AST node to analyze

        Returns:
            List of dead code locations
        """
        dead_code = []

        # Track defined and used names
        defined_names = set()
        used_names = set()

        for node in ast.walk(ast_node):
            # Track definitions
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)

            # Track usage
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        # Find unused definitions
        unused = defined_names - used_names
        dead_code.extend(f"Unused: {name}" for name in unused)

        return dead_code

    def compare_code_versions(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """
        Compare two versions of code

        Args:
            old_code: Old version of code
            new_code: New version of code

        Returns:
            Comparison analysis
        """
        old_report = self.analyze_code(old_code)
        new_report = self.analyze_code(new_code)

        return {
            'quality_score_change': new_report.quality_score - old_report.quality_score,
            'complexity_change': new_report.complexity_metrics.cyclomatic - old_report.complexity_metrics.cyclomatic,
            'smells_change': len(new_report.code_smells) - len(old_report.code_smells),
            'security_change': len(new_report.security_issues) - len(old_report.security_issues),
            'old_score': old_report.quality_score,
            'new_score': new_report.quality_score
        }

    def validate_input(self, data: Any) -> bool:
        """Validate input data"""
        if data is None:
            raise CodeAnalyzerError("Input data cannot be None")
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
        self.state = {}

    # Helper methods for complexity calculations

    def _calculate_cyclomatic(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity (McCabe)"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                complexity += 1

        return complexity

    def _calculate_cognitive(self, node: ast.AST) -> int:
        """Calculate cognitive complexity"""
        complexity = 0
        nesting_level = 0

        def visit(node, level):
            nonlocal complexity
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1 + level
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

            for child in ast.iter_child_nodes(node):
                new_level = level + 1 if isinstance(node, (ast.If, ast.While, ast.For, ast.FunctionDef)) else level
                visit(child, new_level)

        visit(node, 0)
        return complexity

    def _calculate_halstead(self, node: ast.AST) -> Dict[str, float]:
        """Calculate Halstead complexity metrics"""
        operators = set()
        operands = set()
        total_operators = 0
        total_operands = 0

        for child in ast.walk(node):
            # Count operators
            if isinstance(child, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
                                 ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
                                 ast.BitXor, ast.BitAnd, ast.FloorDiv)):
                operators.add(type(child).__name__)
                total_operators += 1
            elif isinstance(child, (ast.And, ast.Or, ast.Not)):
                operators.add(type(child).__name__)
                total_operators += 1
            # Count operands
            elif isinstance(child, (ast.Name, ast.Constant)):
                operands.add(str(child))
                total_operands += 1

        n1 = len(operators)  # Unique operators
        n2 = len(operands)   # Unique operands
        N1 = total_operators  # Total operators
        N2 = total_operands   # Total operands

        # Halstead metrics
        vocabulary = n1 + n2
        length = N1 + N2
        volume = length * math.log2(vocabulary) if vocabulary > 0 else 0
        difficulty = (n1 * N2) / (2 * n2) if n2 > 0 else 0
        effort = volume * difficulty

        return {
            'volume': volume,
            'difficulty': difficulty,
            'effort': effort
        }

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth"""
        def get_depth(node, current_depth=0):
            max_depth = current_depth
            for child in ast.iter_child_nodes(node):
                new_depth = current_depth + 1 if isinstance(child, (ast.If, ast.While, ast.For, ast.With)) else current_depth
                max_depth = max(max_depth, get_depth(child, new_depth))
            return max_depth

        return get_depth(node)

    def _find_max_params(self, node: ast.AST) -> int:
        """Find maximum parameter count"""
        max_params = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_count = len(child.args.args)
                max_params = max(max_params, param_count)
        return max_params

    def _calculate_maintainability_index(self, metrics: ComplexityMetrics) -> float:
        """Calculate maintainability index"""
        # Simplified MI calculation
        # MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        if metrics.halstead_volume == 0 or metrics.loc == 0:
            return 100.0

        mi = 171
        mi -= 5.2 * math.log(metrics.halstead_volume + 1)
        mi -= 0.23 * metrics.cyclomatic
        mi -= 16.2 * math.log(metrics.loc)

        # Normalize to 0-100
        mi = max(0, min(100, mi))
        return mi

    def _score_docstring(self, docstring: str) -> float:
        """Score docstring quality (0-100)"""
        if not docstring:
            return 0.0

        score = 50.0  # Base score for having a docstring

        # Length bonus
        if len(docstring) > 50:
            score += 10
        if len(docstring) > 100:
            score += 10

        # Contains Args/Returns
        if 'Args:' in docstring or 'Parameters:' in docstring:
            score += 15
        if 'Returns:' in docstring or 'Return:' in docstring:
            score += 15

        return min(100.0, score)

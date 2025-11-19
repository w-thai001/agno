"""Quality Metrics Calculator FSA for code analysis."""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import math
import logging

from agno.fsa.base import FSA, Transition

logger = logging.getLogger(__name__)


class QualityState(str, Enum):
    """States for Quality Metrics Calculator FSA."""

    INITIAL = "initial"
    LOADING_FILES = "loading_files"
    ANALYZING_COMPLEXITY = "analyzing_complexity"
    ANALYZING_COVERAGE = "analyzing_coverage"
    ANALYZING_DUPLICATION = "analyzing_duplication"
    COMPUTING_SCORES = "computing_scores"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class CodeMetrics:
    """Container for code metrics."""

    file_path: str
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    function_count: int = 0
    class_count: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    avg_function_complexity: float = 0.0


@dataclass
class TestResults:
    """Container for test results."""

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    coverage_percentage: float = 0.0
    lines_covered: int = 0
    lines_total: int = 0


@dataclass
class QualityScores:
    """Container for quality scores."""

    maintainability_index: float = 0.0
    technical_debt_ratio: float = 0.0
    code_coverage: float = 0.0
    complexity_score: float = 0.0
    duplication_score: float = 0.0
    overall_score: float = 0.0


class QualityMetricsCalculator(FSA):
    """FSA for calculating code quality metrics."""

    def __init__(self):
        super().__init__(name="QualityMetricsCalculator", initial_state=QualityState.INITIAL)

        # Initialize context structure
        self.context = {
            "code_files": [],
            "test_results": None,
            "execution_logs": [],
            "metrics": {},
            "duplication_data": {},
            "quality_scores": None,
            "recommendations": [],
            "errors": [],
        }

        # Register transitions
        self._setup_transitions()

    def _setup_transitions(self):
        """Setup FSA transitions."""
        transitions = [
            # INITIAL -> LOADING_FILES
            Transition(
                from_state=QualityState.INITIAL,
                to_state=QualityState.LOADING_FILES,
                condition=lambda ctx: len(ctx.get("code_files", [])) > 0,
                action=self._load_files,
            ),
            # LOADING_FILES -> ANALYZING_COMPLEXITY
            Transition(
                from_state=QualityState.LOADING_FILES,
                to_state=QualityState.ANALYZING_COMPLEXITY,
                condition=lambda ctx: "file_contents" in ctx,
                action=self._analyze_complexity,
            ),
            # ANALYZING_COMPLEXITY -> ANALYZING_COVERAGE
            Transition(
                from_state=QualityState.ANALYZING_COMPLEXITY,
                to_state=QualityState.ANALYZING_COVERAGE,
                condition=lambda ctx: "metrics" in ctx and len(ctx["metrics"]) > 0,
                action=self._analyze_coverage,
            ),
            # ANALYZING_COVERAGE -> ANALYZING_DUPLICATION
            Transition(
                from_state=QualityState.ANALYZING_COVERAGE,
                to_state=QualityState.ANALYZING_DUPLICATION,
                condition=lambda ctx: True,
                action=self._analyze_duplication,
            ),
            # ANALYZING_DUPLICATION -> COMPUTING_SCORES
            Transition(
                from_state=QualityState.ANALYZING_DUPLICATION,
                to_state=QualityState.COMPUTING_SCORES,
                condition=lambda ctx: "duplication_data" in ctx,
                action=self._compute_scores,
            ),
            # COMPUTING_SCORES -> GENERATING_RECOMMENDATIONS
            Transition(
                from_state=QualityState.COMPUTING_SCORES,
                to_state=QualityState.GENERATING_RECOMMENDATIONS,
                condition=lambda ctx: ctx.get("quality_scores") is not None,
                action=self._generate_recommendations,
            ),
            # GENERATING_RECOMMENDATIONS -> COMPLETED
            Transition(
                from_state=QualityState.GENERATING_RECOMMENDATIONS,
                to_state=QualityState.COMPLETED,
                condition=lambda ctx: len(ctx.get("recommendations", [])) > 0,
                action=lambda ctx: ctx,
            ),
            # Error transitions from any state
            Transition(
                from_state=QualityState.LOADING_FILES,
                to_state=QualityState.ERROR,
                condition=lambda ctx: len(ctx.get("errors", [])) > 0,
                action=lambda ctx: ctx,
            ),
        ]

        self.register_transitions(transitions)

    def _load_files(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Load and parse code files."""
        logger.info("Loading code files...")

        file_contents = {}
        for file_data in context["code_files"]:
            if isinstance(file_data, dict):
                path = file_data.get("path", "")
                content = file_data.get("content", "")
            else:
                # Assume it's a string path, read from file
                path = file_data
                try:
                    with open(path, "r") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Error reading file {path}: {e}")
                    context["errors"].append(f"Failed to read {path}: {e}")
                    continue

            file_contents[path] = content

        context["file_contents"] = file_contents
        logger.info(f"Loaded {len(file_contents)} files")
        return context

    def _analyze_complexity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cyclomatic complexity and other code metrics."""
        logger.info("Analyzing code complexity...")

        metrics = {}
        file_contents = context["file_contents"]

        for file_path, content in file_contents.items():
            try:
                file_metrics = self._calculate_file_metrics(file_path, content)
                metrics[file_path] = file_metrics
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                context["errors"].append(f"Failed to analyze {file_path}: {e}")

        context["metrics"] = metrics
        logger.info(f"Analyzed complexity for {len(metrics)} files")
        return context

    def _calculate_file_metrics(self, file_path: str, content: str) -> CodeMetrics:
        """Calculate metrics for a single file."""
        metrics = CodeMetrics(file_path=file_path)

        # Count lines
        lines = content.split("\n")
        metrics.lines_of_code = len(lines)

        # Count blank and comment lines
        for line in lines:
            stripped = line.strip()
            if not stripped:
                metrics.blank_lines += 1
            elif stripped.startswith("#"):
                metrics.comment_lines += 1

        # Parse AST for complexity
        try:
            tree = ast.parse(content)
            complexity_visitor = ComplexityVisitor()
            complexity_visitor.visit(tree)

            metrics.cyclomatic_complexity = complexity_visitor.complexity
            metrics.function_count = complexity_visitor.function_count
            metrics.class_count = complexity_visitor.class_count

            if metrics.function_count > 0:
                metrics.avg_function_complexity = (
                    metrics.cyclomatic_complexity / metrics.function_count
                )
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            metrics.cyclomatic_complexity = 0

        return metrics

    def _analyze_coverage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test coverage."""
        logger.info("Analyzing test coverage...")

        test_results = context.get("test_results")

        if test_results is None:
            # Create default test results
            total_lines = sum(m.lines_of_code for m in context["metrics"].values())
            test_results = TestResults(
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                coverage_percentage=0.0,
                lines_covered=0,
                lines_total=total_lines,
            )
        elif isinstance(test_results, dict):
            # Convert dict to TestResults object
            test_results = TestResults(**test_results)

        context["test_results"] = test_results
        logger.info(f"Coverage: {test_results.coverage_percentage:.1f}%")
        return context

    def _analyze_duplication(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code duplication."""
        logger.info("Analyzing code duplication...")

        file_contents = context["file_contents"]
        duplication_data = {
            "total_lines": 0,
            "duplicated_lines": 0,
            "duplication_percentage": 0.0,
            "duplicate_blocks": [],
        }

        # Simple duplication detection: find lines that appear multiple times
        line_occurrences = {}

        for file_path, content in file_contents.items():
            lines = content.split("\n")
            duplication_data["total_lines"] += len(lines)

            for line in lines:
                stripped = line.strip()
                if len(stripped) < 20:  # Ignore short lines
                    continue
                if stripped.startswith("#"):  # Ignore comments
                    continue

                if stripped not in line_occurrences:
                    line_occurrences[stripped] = []
                line_occurrences[stripped].append(file_path)

        # Count duplicates
        duplicated_lines = 0
        for line, occurrences in line_occurrences.items():
            if len(occurrences) > 1:
                duplicated_lines += len(occurrences)
                duplication_data["duplicate_blocks"].append(
                    {"line": line[:50], "count": len(occurrences), "files": occurrences}
                )

        duplication_data["duplicated_lines"] = duplicated_lines
        if duplication_data["total_lines"] > 0:
            duplication_data["duplication_percentage"] = (
                duplicated_lines / duplication_data["total_lines"]
            ) * 100

        context["duplication_data"] = duplication_data
        logger.info(
            f"Duplication: {duplication_data['duplication_percentage']:.1f}%"
        )
        return context

    def _compute_scores(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compute composite quality scores."""
        logger.info("Computing quality scores...")

        metrics = context["metrics"]
        test_results = context["test_results"]
        duplication_data = context["duplication_data"]

        # Calculate average complexity
        total_complexity = sum(m.cyclomatic_complexity for m in metrics.values())
        total_functions = sum(m.function_count for m in metrics.values())
        avg_complexity = total_complexity / max(total_functions, 1)

        # Calculate total lines of code
        total_loc = sum(m.lines_of_code for m in metrics.values())
        total_comment_lines = sum(m.comment_lines for m in metrics.values())

        # Complexity score (0-100, lower complexity = higher score)
        complexity_score = max(0, 100 - (avg_complexity * 10))

        # Coverage score
        coverage_score = test_results.coverage_percentage

        # Duplication score (0-100, less duplication = higher score)
        duplication_score = max(
            0, 100 - duplication_data["duplication_percentage"] * 2
        )

        # Maintainability Index (based on Microsoft's formula, simplified)
        # MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        # Simplified version without Halstead Volume
        if total_loc > 0:
            comment_ratio = total_comment_lines / total_loc
            mi = 100 - (avg_complexity * 2) - (math.log(total_loc) * 5)
            mi = mi + (comment_ratio * 20)  # Boost for comments
            maintainability_index = max(0, min(100, mi))
        else:
            maintainability_index = 0

        # Technical Debt Ratio (estimated)
        # Based on complexity, coverage, and duplication
        debt_factors = [
            (100 - complexity_score) * 0.3,
            (100 - coverage_score) * 0.4,
            (100 - duplication_score) * 0.3,
        ]
        technical_debt_ratio = sum(debt_factors) / 100

        # Overall score
        overall_score = (
            maintainability_index * 0.3
            + complexity_score * 0.2
            + coverage_score * 0.3
            + duplication_score * 0.2
        )

        scores = QualityScores(
            maintainability_index=round(maintainability_index, 2),
            technical_debt_ratio=round(technical_debt_ratio, 3),
            code_coverage=round(coverage_score, 2),
            complexity_score=round(complexity_score, 2),
            duplication_score=round(duplication_score, 2),
            overall_score=round(overall_score, 2),
        )

        context["quality_scores"] = scores
        logger.info(f"Overall quality score: {scores.overall_score:.2f}/100")
        return context

    def _generate_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations based on metrics."""
        logger.info("Generating recommendations...")

        scores = context["quality_scores"]
        metrics = context["metrics"]
        duplication_data = context["duplication_data"]
        recommendations = []

        # Complexity recommendations
        if scores.complexity_score < 60:
            high_complexity_files = [
                f"{path}: {m.avg_function_complexity:.1f}"
                for path, m in metrics.items()
                if m.avg_function_complexity > 10
            ]
            recommendations.append(
                {
                    "category": "Complexity",
                    "severity": "high",
                    "message": "High cyclomatic complexity detected. Consider refactoring complex functions.",
                    "details": high_complexity_files[:5],
                }
            )

        # Coverage recommendations
        if scores.code_coverage < 70:
            recommendations.append(
                {
                    "category": "Testing",
                    "severity": "high",
                    "message": f"Low test coverage ({scores.code_coverage:.1f}%). Aim for at least 80% coverage.",
                    "details": ["Add unit tests for core functionality"],
                }
            )

        # Duplication recommendations
        if scores.duplication_score < 70:
            recommendations.append(
                {
                    "category": "Duplication",
                    "severity": "medium",
                    "message": f"Code duplication detected ({duplication_data['duplication_percentage']:.1f}%). Consider extracting common logic.",
                    "details": [
                        f"{block['line']}... appears {block['count']} times"
                        for block in duplication_data["duplicate_blocks"][:3]
                    ],
                }
            )

        # Maintainability recommendations
        if scores.maintainability_index < 50:
            recommendations.append(
                {
                    "category": "Maintainability",
                    "severity": "high",
                    "message": "Low maintainability index. Focus on reducing complexity and improving documentation.",
                    "details": ["Add comments and docstrings", "Break down large functions"],
                }
            )

        # Positive feedback
        if scores.overall_score >= 80:
            recommendations.append(
                {
                    "category": "Overall",
                    "severity": "info",
                    "message": "Excellent code quality! Keep up the good work.",
                    "details": [],
                }
            )

        context["recommendations"] = recommendations
        logger.info(f"Generated {len(recommendations)} recommendations")
        return context

    def calculate(
        self,
        code_files: List[Any],
        test_results: Optional[Dict[str, Any]] = None,
        execution_logs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics for given code files.

        Args:
            code_files: List of file paths or dicts with 'path' and 'content'
            test_results: Optional test results dict
            execution_logs: Optional execution logs

        Returns:
            Dict containing quality_scores, metrics, and recommendations
        """
        # Reset FSA
        self.reset()

        # Set context
        self.context["code_files"] = code_files
        if test_results:
            self.context["test_results"] = test_results
        if execution_logs:
            self.context["execution_logs"] = execution_logs

        # Run FSA
        final_context = self.run()

        # Return results
        return {
            "quality_scores": final_context.get("quality_scores"),
            "maintainability_index": final_context.get("quality_scores").maintainability_index
            if final_context.get("quality_scores")
            else 0,
            "debt_ratio": final_context.get("quality_scores").technical_debt_ratio
            if final_context.get("quality_scores")
            else 0,
            "recommendations": final_context.get("recommendations", []),
            "metrics": final_context.get("metrics", {}),
            "duplication_data": final_context.get("duplication_data", {}),
            "current_state": self.current_state,
            "errors": final_context.get("errors", []),
        }


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1  # Base complexity
        self.function_count = 0
        self.class_count = 0

    def visit_FunctionDef(self, node):
        self.function_count += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.function_count += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.class_count += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

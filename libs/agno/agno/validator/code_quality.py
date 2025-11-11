"""
FSA-2.1: Code Quality Validator

Comprehensive code quality validation across multiple dimensions:
- Syntax correctness
- Style compliance
- Security vulnerabilities
- Performance optimization
- Best practices adherence

Integrates with:
- FSA-1.1: Prompt Optimizer for AI-assisted analysis
- FSA-1.2: Code Template Library for validation test cases
"""

import ast
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agno.optimizer import PromptOptimizer
from agno.optimizer.prompt_optimizer import AnalysisType
from agno.templates import CodeTemplateLibrary
from agno.utils.log import logger


class IssueSeverity(Enum):
    """Severity levels for code issues."""

    CRITICAL = "critical"  # Must fix immediately
    HIGH = "high"  # Should fix soon
    MEDIUM = "medium"  # Should address
    LOW = "low"  # Nice to fix
    INFO = "info"  # Informational only


@dataclass
class CodeIssue:
    """Represents a code quality issue."""

    severity: IssueSeverity
    category: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class DimensionScore:
    """Score for a specific quality dimension."""

    dimension: str
    score: int  # 0-100
    issues: List[CodeIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Comprehensive quality report for code."""

    overall_score: int  # 0-100
    language: str
    code_length: int
    dimensions: Dict[str, DimensionScore] = field(default_factory=dict)
    summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    report: QualityReport
    top_issues: List[CodeIssue] = field(default_factory=list)
    execution_time_ms: float = 0.0


class CodeQualityValidator:
    """
    Comprehensive code quality validator.

    Validates code across multiple dimensions and provides actionable feedback.
    Integrates with FSA-1.1 (Prompt Optimizer) and FSA-1.2 (Code Template Library).
    """

    # Supported languages
    SUPPORTED_LANGUAGES = ["python", "javascript"]

    # Quality score thresholds
    EXCELLENT_THRESHOLD = 90
    GOOD_THRESHOLD = 70
    FAIR_THRESHOLD = 50

    def __init__(
        self,
        use_ai_analysis: bool = False,
        prompt_optimizer: Optional[PromptOptimizer] = None,
        template_library: Optional[CodeTemplateLibrary] = None,
    ):
        """
        Initialize the Code Quality Validator.

        Args:
            use_ai_analysis: Enable AI-powered analysis (requires model integration)
            prompt_optimizer: FSA-1.1 Prompt Optimizer instance
            template_library: FSA-1.2 Code Template Library instance
        """
        self.use_ai_analysis = use_ai_analysis
        self.prompt_optimizer = prompt_optimizer or PromptOptimizer()
        self.template_library = template_library or CodeTemplateLibrary()

        logger.info("CodeQualityValidator initialized (AI analysis: %s)", use_ai_analysis)

    def validateCode(
        self, code: str, language: str, detailed: bool = True
    ) -> ValidationResult:
        """
        Validate code quality across all dimensions.

        Args:
            code: The source code to validate
            language: Programming language (python, javascript)
            detailed: Whether to include detailed analysis

        Returns:
            ValidationResult with comprehensive quality report

        Raises:
            ValueError: If language is not supported
        """
        start_time = datetime.now()

        # Validate language support
        if language.lower() not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}. Supported: {self.SUPPORTED_LANGUAGES}")

        logger.info("Validating %s code (%d characters)", language, len(code))

        # Create quality report
        report = QualityReport(
            overall_score=0, language=language, code_length=len(code), dimensions={}
        )

        # Run validations for each dimension
        try:
            # 1. Syntax validation
            syntax_score = self._validate_syntax(code, language)
            report.dimensions["syntax"] = syntax_score

            # 2. Style validation
            style_score = self._validate_style(code, language)
            report.dimensions["style"] = style_score

            # 3. Security validation
            security_score = self._validate_security(code, language)
            report.dimensions["security"] = security_score

            # 4. Performance validation
            performance_score = self._validate_performance(code, language)
            report.dimensions["performance"] = performance_score

            # 5. Best practices validation
            best_practices_score = self._validate_best_practices(code, language)
            report.dimensions["best_practices"] = best_practices_score

            # Calculate overall score (weighted average)
            weights = {
                "syntax": 0.25,
                "security": 0.25,
                "style": 0.15,
                "performance": 0.15,
                "best_practices": 0.20,
            }

            overall = sum(
                report.dimensions[dim].score * weights[dim] for dim in weights
            )
            report.overall_score = int(overall)

            # Generate summary
            report.summary = self._generate_summary(report)

            # Determine if code is valid (no critical issues)
            critical_issues = self._get_critical_issues(report)
            is_valid = len(critical_issues) == 0 and report.overall_score >= self.FAIR_THRESHOLD

            # Get top issues (prioritized)
            top_issues = self._prioritize_issues(report)

        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            # Return minimal valid report on error
            report.overall_score = 0
            report.summary = f"Validation failed: {str(e)}"
            is_valid = False
            top_issues = [
                CodeIssue(
                    severity=IssueSeverity.CRITICAL,
                    category="validation_error",
                    message=f"Validation failed: {str(e)}",
                )
            ]

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return ValidationResult(
            is_valid=is_valid,
            report=report,
            top_issues=top_issues[:10],  # Top 10 issues
            execution_time_ms=execution_time,
        )

    def _validate_syntax(self, code: str, language: str) -> DimensionScore:
        """
        Validate syntax correctness.

        Args:
            code: Source code to validate
            language: Programming language

        Returns:
            DimensionScore for syntax dimension
        """
        issues = []
        score = 100

        if language == "python":
            try:
                ast.parse(code)
                logger.debug("Python syntax validation passed")
            except SyntaxError as e:
                score = 0
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="syntax_error",
                        message=f"Syntax error: {e.msg}",
                        line=e.lineno,
                        suggestion="Fix the syntax error to make the code executable",
                    )
                )
                logger.warning("Python syntax error at line %s: %s", e.lineno, e.msg)

        elif language == "javascript":
            # Basic JavaScript syntax checks (regex-based)
            js_issues = self._check_javascript_syntax(code)
            issues.extend(js_issues)
            score = max(0, 100 - len(js_issues) * 20)

        return DimensionScore(dimension="syntax", score=score, issues=issues)

    def _check_javascript_syntax(self, code: str) -> List[CodeIssue]:
        """
        Perform basic JavaScript syntax checks.

        Args:
            code: JavaScript code

        Returns:
            List of syntax issues found
        """
        issues = []

        # Check for basic syntax patterns
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Check for unclosed strings
            if line_stripped.count('"') % 2 != 0 or line_stripped.count("'") % 2 != 0:
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.HIGH,
                        category="syntax_error",
                        message="Possible unclosed string",
                        line=i,
                        suggestion="Ensure all quotes are properly closed",
                    )
                )

            # Check for unmatched brackets
            if line_stripped.count("(") != line_stripped.count(")"):
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.HIGH,
                        category="syntax_error",
                        message="Unmatched parentheses",
                        line=i,
                        suggestion="Check for missing or extra parentheses",
                    )
                )

        return issues

    def _validate_style(self, code: str, language: str) -> DimensionScore:
        """
        Validate code style and readability.

        Args:
            code: Source code
            language: Programming language

        Returns:
            DimensionScore for style dimension
        """
        issues = []
        score = 100
        recommendations = []

        lines = code.split("\n")

        # Check line length
        long_lines = [(i + 1, line) for i, line in enumerate(lines) if len(line) > 120]
        if long_lines:
            score -= min(20, len(long_lines) * 2)
            for line_num, _ in long_lines[:5]:  # Report first 5
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.LOW,
                        category="style",
                        message="Line exceeds 120 characters",
                        line=line_num,
                        suggestion="Break long lines for better readability",
                    )
                )

        # Check for proper naming conventions
        if language == "python":
            # Check for snake_case in Python
            camelCase_pattern = re.compile(r'\bdef [a-z]+[A-Z]')
            if camelCase_pattern.search(code):
                score -= 10
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="naming_convention",
                        message="Use snake_case for Python function names",
                        suggestion="Rename functions to use snake_case (e.g., my_function)",
                    )
                )

        elif language == "javascript":
            # Check for camelCase in JavaScript
            snake_case_pattern = re.compile(r'\bfunction [a-z]+_[a-z]')
            if snake_case_pattern.search(code):
                score -= 10
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="naming_convention",
                        message="Use camelCase for JavaScript function names",
                        suggestion="Rename functions to use camelCase (e.g., myFunction)",
                    )
                )

        # Check for comments
        comment_lines = [line for line in lines if line.strip().startswith(("#", "//"))]
        comment_ratio = len(comment_lines) / max(len(lines), 1)

        if comment_ratio < 0.1:
            score -= 10
            recommendations.append("Add more comments to explain complex logic")

        # Check for proper indentation
        if language == "python":
            inconsistent_indent = self._check_python_indentation(lines)
            if inconsistent_indent:
                score -= 15
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="indentation",
                        message="Inconsistent indentation detected",
                        suggestion="Use consistent indentation (4 spaces recommended)",
                    )
                )

        score = max(0, score)
        return DimensionScore(
            dimension="style", score=score, issues=issues, recommendations=recommendations
        )

    def _check_python_indentation(self, lines: List[str]) -> bool:
        """Check for consistent Python indentation."""
        indents = []
        for line in lines:
            if line and not line.strip().startswith("#"):
                leading_spaces = len(line) - len(line.lstrip())
                if leading_spaces > 0:
                    indents.append(leading_spaces)

        # Check if indentation is consistent (multiples of 2 or 4)
        if indents:
            return not all(indent % 4 == 0 or indent % 2 == 0 for indent in indents)
        return False

    def _validate_security(self, code: str, language: str) -> DimensionScore:
        """
        Validate code for security vulnerabilities.

        Args:
            code: Source code
            language: Programming language

        Returns:
            DimensionScore for security dimension
        """
        issues = []
        score = 100

        # Common security patterns to check
        if language == "python":
            # Check for eval() usage
            if re.search(r'\beval\s*\(', code):
                score -= 40
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="code_injection",
                        message="Use of eval() detected - code injection vulnerability",
                        suggestion="Avoid eval(). Use ast.literal_eval() for safe evaluation or alternative approaches",
                    )
                )

            # Check for SQL injection patterns
            if re.search(r'execute\s*\(\s*["\'].*\+.*["\']', code) or re.search(
                r'execute\s*\(\s*f["\']', code
            ):
                score -= 35
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="sql_injection",
                        message="Possible SQL injection vulnerability",
                        suggestion="Use parameterized queries (e.g., cursor.execute(query, params))",
                    )
                )

            # Check for hardcoded secrets
            if re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
                score -= 25
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.HIGH,
                        category="hardcoded_secrets",
                        message="Possible hardcoded credentials detected",
                        suggestion="Use environment variables or secure configuration management",
                    )
                )

        elif language == "javascript":
            # Check for innerHTML usage
            if re.search(r'\.innerHTML\s*=', code):
                score -= 30
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.HIGH,
                        category="xss_vulnerability",
                        message="Use of innerHTML can lead to XSS attacks",
                        suggestion="Use textContent or sanitize input before using innerHTML",
                    )
                )

            # Check for eval() in JavaScript
            if re.search(r'\beval\s*\(', code):
                score -= 40
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="code_injection",
                        message="Use of eval() detected - code injection vulnerability",
                        suggestion="Avoid eval(). Use JSON.parse() for data or alternative approaches",
                    )
                )

        score = max(0, score)
        return DimensionScore(dimension="security", score=score, issues=issues)

    def _validate_performance(self, code: str, language: str) -> DimensionScore:
        """
        Validate code for performance optimization opportunities.

        Args:
            code: Source code
            language: Programming language

        Returns:
            DimensionScore for performance dimension
        """
        issues = []
        score = 100
        recommendations = []

        if language == "python":
            # Check for inefficient loops
            if re.search(r'for .+ in range\(len\(.+\)\):', code):
                score -= 10
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.LOW,
                        category="performance",
                        message="Inefficient iteration pattern",
                        suggestion="Use 'for item in collection:' instead of 'for i in range(len(collection)):'",
                    )
                )

            # Check for list concatenation in loops
            if re.search(r'for .+:\s*\n\s*.+\s*\+=\s*\[', code):
                score -= 15
                recommendations.append("Consider using list comprehension or append() instead of += in loops")

            # Check for global keyword overuse
            global_count = len(re.findall(r'\bglobal\b', code))
            if global_count > 3:
                score -= 10
                recommendations.append("Excessive use of global variables. Consider refactoring to use classes or pass parameters")

        elif language == "javascript":
            # Check for synchronous operations in async context
            if re.search(r'async\s+function', code) and not re.search(r'\bawait\b', code):
                score -= 10
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="performance",
                        message="Async function without await usage",
                        suggestion="Remove 'async' keyword if not using await, or ensure async operations use await",
                    )
                )

            # Check for DOM manipulation in loops
            if re.search(r'for\s*\(.*\)\s*\{[^}]*document\.(getElementById|querySelector)', code):
                score -= 15
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="performance",
                        message="DOM manipulation inside loop",
                        suggestion="Cache DOM references outside the loop to improve performance",
                    )
                )

        score = max(0, score)
        return DimensionScore(
            dimension="performance",
            score=score,
            issues=issues,
            recommendations=recommendations,
        )

    def _validate_best_practices(self, code: str, language: str) -> DimensionScore:
        """
        Validate adherence to best practices.

        Args:
            code: Source code
            language: Programming language

        Returns:
            DimensionScore for best practices dimension
        """
        issues = []
        score = 100
        recommendations = []

        # Check for proper error handling
        if language == "python":
            has_try_except = bool(re.search(r'\btry\s*:', code))
            has_functions = bool(re.search(r'\bdef\s+\w+', code))

            if has_functions and not has_try_except:
                score -= 15
                recommendations.append("Add error handling (try/except) for robust code")

            # Check for bare except
            if re.search(r'except\s*:', code):
                score -= 15
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category="error_handling",
                        message="Bare 'except:' clause catches all exceptions",
                        suggestion="Catch specific exceptions (e.g., 'except ValueError:') for better error handling",
                    )
                )

            # Check for docstrings
            if has_functions and not re.search(r'""".*?"""', code, re.DOTALL):
                score -= 10
                recommendations.append("Add docstrings to document functions and classes")

        elif language == "javascript":
            has_try_catch = bool(re.search(r'\btry\s*\{', code))
            has_functions = bool(re.search(r'function\s+\w+|=>\s*\{', code))

            if has_functions and not has_try_catch:
                score -= 15
                recommendations.append("Add error handling (try/catch) for robust code")

            # Check for console.log in production code
            console_logs = len(re.findall(r'\bconsole\.log\s*\(', code))
            if console_logs > 3:
                score -= 10
                issues.append(
                    CodeIssue(
                        severity=IssueSeverity.LOW,
                        category="debugging",
                        message="Multiple console.log statements found",
                        suggestion="Remove or replace with proper logging before production",
                    )
                )

        # Check for magic numbers
        magic_numbers = re.findall(r'\b\d{2,}\b', code)
        if len(magic_numbers) > 5:
            score -= 10
            recommendations.append("Replace magic numbers with named constants for better maintainability")

        score = max(0, score)
        return DimensionScore(
            dimension="best_practices",
            score=score,
            issues=issues,
            recommendations=recommendations,
        )

    def _get_critical_issues(self, report: QualityReport) -> List[CodeIssue]:
        """Get all critical issues from the report."""
        critical = []
        for dimension in report.dimensions.values():
            critical.extend([issue for issue in dimension.issues if issue.severity == IssueSeverity.CRITICAL])
        return critical

    def _prioritize_issues(self, report: QualityReport) -> List[CodeIssue]:
        """Prioritize and sort issues by severity."""
        all_issues = []
        for dimension in report.dimensions.values():
            all_issues.extend(dimension.issues)

        # Sort by severity (critical first)
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
            IssueSeverity.INFO: 4,
        }

        all_issues.sort(key=lambda issue: severity_order[issue.severity])
        return all_issues

    def _generate_summary(self, report: QualityReport) -> str:
        """Generate a human-readable summary of the quality report."""
        score = report.overall_score

        if score >= self.EXCELLENT_THRESHOLD:
            quality = "Excellent"
        elif score >= self.GOOD_THRESHOLD:
            quality = "Good"
        elif score >= self.FAIR_THRESHOLD:
            quality = "Fair"
        else:
            quality = "Poor"

        critical_count = len(self._get_critical_issues(report))
        total_issues = sum(len(dim.issues) for dim in report.dimensions.values())

        summary = f"{quality} code quality (score: {score}/100). "
        summary += f"Found {total_issues} issues"

        if critical_count > 0:
            summary += f" including {critical_count} critical"

        summary += ". "

        # Identify weakest dimension
        weakest_dim = min(report.dimensions.items(), key=lambda x: x[1].score)
        summary += f"Focus on improving {weakest_dim[0].replace('_', ' ')} (score: {weakest_dim[1].score})."

        return summary

    def getQualityScore(self, validation_result: ValidationResult) -> int:
        """
        Get the overall quality score from a validation result.

        Args:
            validation_result: ValidationResult from validateCode()

        Returns:
            Overall quality score (0-100)
        """
        return validation_result.report.overall_score

    def getSuggestions(self, validation_result: ValidationResult, limit: int = 10) -> List[str]:
        """
        Get actionable suggestions from a validation result.

        Args:
            validation_result: ValidationResult from validateCode()
            limit: Maximum number of suggestions to return

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Add suggestions from top issues
        for issue in validation_result.top_issues[:limit]:
            if issue.suggestion:
                suggestions.append(f"[{issue.severity.value.upper()}] {issue.message}: {issue.suggestion}")

        # Add recommendations from dimensions
        for dimension in validation_result.report.dimensions.values():
            for rec in dimension.recommendations:
                if len(suggestions) < limit:
                    suggestions.append(f"[RECOMMENDATION] {rec}")

        return suggestions[:limit]

    def compare_with_template(
        self, code: str, language: str, template_id: str
    ) -> Dict[str, Any]:
        """
        Compare code against a template from FSA-1.2 library.

        Args:
            code: Code to validate
            language: Programming language
            template_id: ID of template to compare against

        Returns:
            Comparison report with differences and quality comparison
        """
        template = self.template_library.get_template(template_id)

        if not template:
            raise ValueError(f"Template not found: {template_id}")

        if template.language.lower() != language.lower():
            raise ValueError(
                f"Language mismatch: template is {template.language}, code is {language}"
            )

        # Validate both code and template
        code_result = self.validateCode(code, language)
        template_result = self.validateCode(template.code, language)

        comparison = {
            "template": {
                "id": template.id,
                "name": template.name,
                "quality_level": template.quality_level.value,
                "score": template_result.report.overall_score,
            },
            "code": {"score": code_result.report.overall_score},
            "score_difference": code_result.report.overall_score
            - template_result.report.overall_score,
            "dimension_comparison": {},
            "lessons_learned": [],
        }

        # Compare dimensions
        for dim_name in code_result.report.dimensions:
            code_dim = code_result.report.dimensions[dim_name]
            template_dim = template_result.report.dimensions[dim_name]

            comparison["dimension_comparison"][dim_name] = {
                "code_score": code_dim.score,
                "template_score": template_dim.score,
                "difference": code_dim.score - template_dim.score,
            }

        # Extract lessons from template
        if template.best_practices:
            comparison["lessons_learned"].extend(template.best_practices)

        if template.security_notes:
            comparison["lessons_learned"].extend(
                [f"Security: {note}" for note in template.security_notes]
            )

        return comparison

    def get_optimized_prompt(self, code: str, language: str, analysis_type: str) -> str:
        """
        Get an optimized prompt for AI-assisted analysis using FSA-1.1.

        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis (syntax, style, security, etc.)

        Returns:
            Optimized prompt string
        """
        try:
            analysis_enum = AnalysisType(analysis_type.lower())
        except ValueError:
            raise ValueError(
                f"Invalid analysis type: {analysis_type}. "
                f"Valid types: {[t.value for t in AnalysisType]}"
            )

        optimized = self.prompt_optimizer.optimize_for_analysis(code, language, analysis_enum)
        return optimized.prompt

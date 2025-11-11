"""
FSA-2.1: Code Quality Validator

This module provides comprehensive code quality validation including:
- Syntax validation
- Style checking
- Security analysis
- Performance assessment
- Improvement suggestions with priority ranking

Integrates with:
- FSA-1.1 (Prompt Optimizer) - for optimizing validation prompts
- FSA-1.2 (Template Library) - for test case validation templates
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Language(str, Enum):
    """Supported programming languages."""

    JAVASCRIPT = "javascript"
    PYTHON = "python"


class Priority(str, Enum):
    """Priority levels for improvement suggestions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityMetrics:
    """Quality metrics for code validation."""

    syntax: float = 0.0  # 0-100
    style: float = 0.0  # 0-100
    security: float = 0.0  # 0-100
    performance: float = 0.0  # 0-100

    @property
    def overall(self) -> float:
        """Calculate overall quality score."""
        return (self.syntax + self.style + self.security + self.performance) / 4

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary."""
        return {
            "syntax": round(self.syntax, 2),
            "style": round(self.style, 2),
            "security": round(self.security, 2),
            "performance": round(self.performance, 2),
            "overall": round(self.overall, 2),
        }


@dataclass
class ImprovementSuggestion:
    """Represents a code improvement suggestion."""

    priority: Priority
    category: str
    issue: str
    suggestion: str
    line: Optional[int] = None
    code_snippet: Optional[str] = None
    fixed_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert suggestion to dictionary."""
        return {
            "priority": self.priority.value,
            "category": self.category,
            "issue": self.issue,
            "suggestion": self.suggestion,
            "line": self.line,
            "code_snippet": self.code_snippet,
            "fixed_code": self.fixed_code,
        }


@dataclass
class ValidationResult:
    """Result of code quality validation."""

    code: str
    language: Language
    metrics: QualityMetrics
    suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "language": self.language.value,
            "metrics": self.metrics.to_dict(),
            "suggestions": [s.to_dict() for s in self.suggestions],
            "errors": self.errors,
        }


class CodeQualityValidator:
    """
    FSA-2.1: Code Quality Validator

    Validates code quality across multiple dimensions and provides
    actionable improvement suggestions.
    """

    def __init__(
        self,
        prompt_optimizer: Optional[Any] = None,  # FSA-1.1 integration point
        template_library: Optional[Any] = None,  # FSA-1.2 integration point
    ):
        """
        Initialize the Code Quality Validator.

        Args:
            prompt_optimizer: Optional FSA-1.1 Prompt Optimizer instance
            template_library: Optional FSA-1.2 Template Library instance
        """
        self.prompt_optimizer = prompt_optimizer
        self.template_library = template_library
        self._current_code: Optional[str] = None
        self._current_language: Optional[Language] = None
        self._metrics: Optional[QualityMetrics] = None
        self._suggestions: List[ImprovementSuggestion] = []

    def validateCode(
        self, code: str, language: str
    ) -> ValidationResult:
        """
        Validate code quality for the given code and language.

        Args:
            code: Source code to validate
            language: Programming language (javascript or python)

        Returns:
            ValidationResult containing metrics and suggestions
        """
        try:
            lang = Language(language.lower())
        except ValueError:
            return ValidationResult(
                code=code,
                language=Language.JAVASCRIPT,
                metrics=QualityMetrics(),
                errors=[f"Unsupported language: {language}"],
            )

        self._current_code = code
        self._current_language = lang
        self._suggestions = []

        # Validate based on language
        if lang == Language.JAVASCRIPT:
            self._validate_javascript(code)
        elif lang == Language.PYTHON:
            self._validate_python(code)

        # Generate quality score
        self._metrics = self.generateQualityScore()

        # Generate improvement suggestions
        self.suggestImprovements()

        # Apply FSA-1.2 template validation if available
        if self.template_library:
            self._apply_template_validation()

        return ValidationResult(
            code=code,
            language=lang,
            metrics=self._metrics,
            suggestions=self._suggestions,
        )

    def generateQualityScore(self) -> QualityMetrics:
        """
        Generate quality scores based on validation results.

        Returns:
            QualityMetrics with scores for each dimension
        """
        if not self._current_code or not self._current_language:
            return QualityMetrics()

        metrics = QualityMetrics()

        if self._current_language == Language.JAVASCRIPT:
            metrics = self._score_javascript()
        elif self._current_language == Language.PYTHON:
            metrics = self._score_python()

        return metrics

    def suggestImprovements(self) -> List[ImprovementSuggestion]:
        """
        Generate prioritized improvement suggestions.

        Returns:
            List of ImprovementSuggestion objects sorted by priority
        """
        # Suggestions are already populated during validation
        # Sort by priority (critical -> high -> medium -> low)
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        self._suggestions.sort(key=lambda s: priority_order[s.priority])

        # Apply FSA-1.1 prompt optimization if available
        if self.prompt_optimizer:
            self._optimize_suggestion_prompts()

        return self._suggestions

    def _validate_javascript(self, code: str) -> None:
        """Validate JavaScript code."""
        lines = code.split("\n")

        # Syntax validation
        self._check_js_syntax(code)

        # Style validation
        self._check_js_style(code, lines)

        # Security validation
        self._check_js_security(code)

        # Performance validation
        self._check_js_performance(code)

    def _validate_python(self, code: str) -> None:
        """Validate Python code."""
        lines = code.split("\n")

        # Syntax validation
        self._check_py_syntax(code)

        # Style validation
        self._check_py_style(code, lines)

        # Security validation
        self._check_py_security(code)

        # Performance validation
        self._check_py_performance(code)

    # ==================== JavaScript Validators ====================

    def _check_js_syntax(self, code: str) -> None:
        """Check JavaScript syntax issues."""
        # Check for missing semicolons (optional in JS but good practice)
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.endswith((";", "{", "}", ",")):
                # Skip comments and specific control structures
                if not (
                    line.startswith("//")
                    or line.startswith("/*")
                    or line.startswith("*")
                    or re.match(r"^\s*(if|else|for|while|function|return|var|let|const)\s*\(", line)
                ):
                    pass  # Semicolons are optional in modern JS

        # Check for balanced braces
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="syntax",
                    issue="Unbalanced braces detected",
                    suggestion="Ensure all opening braces { have matching closing braces }",
                )
            )

    def _check_js_style(self, code: str, lines: List[str]) -> None:
        """Check JavaScript style issues."""
        # Check for 'var' usage (should use 'let' or 'const')
        if re.search(r"\bvar\s+\w+", code):
            matches = re.finditer(r"\bvar\s+(\w+)", code)
            for match in matches:
                line_num = code[: match.start()].count("\n") + 1
                var_name = match.group(1)
                self._suggestions.append(
                    ImprovementSuggestion(
                        priority=Priority.HIGH,
                        category="style",
                        issue=f"Use of 'var' keyword for variable '{var_name}'",
                        suggestion=f"Replace 'var' with 'const' or 'let' for better scoping",
                        line=line_num,
                        code_snippet=f"var {var_name}",
                        fixed_code=f"const {var_name}",
                    )
                )

        # Check for function spacing
        if re.search(r"function\s+\w+\s*\([^)]*\)\s*\{", code):
            # Good: has space before {
            pass
        elif re.search(r"function\s+\w+\s*\([^)]*\)\{", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.LOW,
                    category="style",
                    issue="Missing space before opening brace in function declaration",
                    suggestion="Add a space before { in function declarations: function name() {",
                )
            )

        # Check for missing function parameter spacing
        if re.search(r"function\s+\w+\(", code):
            # Check if parameters are poorly formatted
            func_match = re.search(r"function\s+(\w+)\(([^)]*)\)", code)
            if func_match:
                params = func_match.group(2)
                if params and "," in params and ", " not in params:
                    self._suggestions.append(
                        ImprovementSuggestion(
                            priority=Priority.LOW,
                            category="style",
                            issue="Missing space after comma in function parameters",
                            suggestion="Add space after commas in parameter lists: function(a, b, c)",
                        )
                    )

        # Check for inconsistent naming (camelCase is standard for JS)
        var_names = re.findall(r"(?:var|let|const)\s+([a-z_][a-z0-9_]*)", code, re.IGNORECASE)
        for var_name in var_names:
            if "_" in var_name and not var_name.isupper():
                self._suggestions.append(
                    ImprovementSuggestion(
                        priority=Priority.MEDIUM,
                        category="style",
                        issue=f"Variable '{var_name}' uses snake_case",
                        suggestion=f"Use camelCase for JavaScript variables: {self._to_camel_case(var_name)}",
                    )
                )

        # Check for missing documentation
        if re.search(r"function\s+\w+", code) and "/**" not in code and "//" not in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.MEDIUM,
                    category="style",
                    issue="Missing function documentation",
                    suggestion="Add JSDoc comments to document function purpose and parameters",
                )
            )

    def _check_js_security(self, code: str) -> None:
        """Check JavaScript security issues."""
        # Check for eval usage
        if "eval(" in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="security",
                    issue="Use of eval() function detected",
                    suggestion="Avoid eval() as it can execute arbitrary code. Use safer alternatives like JSON.parse()",
                )
            )

        # Check for innerHTML usage (XSS risk)
        if "innerHTML" in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.HIGH,
                    category="security",
                    issue="Use of innerHTML detected (potential XSS vulnerability)",
                    suggestion="Use textContent or sanitize HTML input to prevent XSS attacks",
                )
            )

        # Check for document.write
        if "document.write" in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.MEDIUM,
                    category="security",
                    issue="Use of document.write() detected",
                    suggestion="Avoid document.write() as it can be exploited. Use DOM manipulation methods instead",
                )
            )

    def _check_js_performance(self, code: str) -> None:
        """Check JavaScript performance issues."""
        # Check for inefficient operations
        if re.search(r"for\s*\([^)]*\)\s*\{[^}]*\.push\s*\(", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.MEDIUM,
                    category="performance",
                    issue="Array push in loop may be inefficient",
                    suggestion="Consider using array methods like map() or reduce() for better performance",
                )
            )

        # Check for synchronous operations
        if "XMLHttpRequest" in code and "async" not in code.lower():
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.HIGH,
                    category="performance",
                    issue="Synchronous XMLHttpRequest detected",
                    suggestion="Use async/await with fetch() API for better performance and user experience",
                )
            )

    def _score_javascript(self) -> QualityMetrics:
        """Calculate quality scores for JavaScript code."""
        metrics = QualityMetrics()

        # Count issues by category
        syntax_issues = [s for s in self._suggestions if s.category == "syntax"]
        style_issues = [s for s in self._suggestions if s.category == "style"]
        security_issues = [s for s in self._suggestions if s.category == "security"]
        performance_issues = [s for s in self._suggestions if s.category == "performance"]

        # Calculate scores (deduct points for each issue)
        metrics.syntax = max(0, 100 - len(syntax_issues) * 20)
        metrics.style = max(0, 100 - len(style_issues) * 10)
        metrics.security = max(0, 100 - len(security_issues) * 15)
        metrics.performance = max(0, 100 - len(performance_issues) * 12)

        return metrics

    # ==================== Python Validators ====================

    def _check_py_syntax(self, code: str) -> None:
        """Check Python syntax issues."""
        try:
            ast.parse(code)
        except SyntaxError as e:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="syntax",
                    issue=f"Syntax error: {str(e)}",
                    suggestion="Fix syntax error to make code executable",
                    line=e.lineno,
                )
            )

    def _check_py_style(self, code: str, lines: List[str]) -> None:
        """Check Python style issues (PEP 8)."""
        # Check for proper indentation (4 spaces)
        for i, line in enumerate(lines, 1):
            if line and line[0] == " ":
                leading_spaces = len(line) - len(line.lstrip())
                if leading_spaces % 4 != 0:
                    self._suggestions.append(
                        ImprovementSuggestion(
                            priority=Priority.MEDIUM,
                            category="style",
                            issue=f"Line {i}: Incorrect indentation (not multiple of 4)",
                            suggestion="Use 4 spaces per indentation level (PEP 8)",
                            line=i,
                        )
                    )
                    break  # Report only once

        # Check for function naming (snake_case)
        func_names = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code)
        for func_name in func_names:
            if not re.match(r"^[a-z_][a-z0-9_]*$", func_name):
                self._suggestions.append(
                    ImprovementSuggestion(
                        priority=Priority.MEDIUM,
                        category="style",
                        issue=f"Function '{func_name}' doesn't follow snake_case naming",
                        suggestion=f"Use snake_case for function names (PEP 8): {self._to_snake_case(func_name)}",
                    )
                )

        # Check for missing docstrings
        if re.search(r"def\s+\w+", code) and '"""' not in code and "'''" not in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.MEDIUM,
                    category="style",
                    issue="Missing function docstrings",
                    suggestion='Add docstrings using """...""" to document functions (PEP 257)',
                )
            )

        # Check line length (max 79 characters per PEP 8)
        for i, line in enumerate(lines, 1):
            if len(line.rstrip()) > 79:
                self._suggestions.append(
                    ImprovementSuggestion(
                        priority=Priority.LOW,
                        category="style",
                        issue=f"Line {i}: Line too long ({len(line)} > 79 characters)",
                        suggestion="Break long lines to stay within 79 characters (PEP 8)",
                        line=i,
                    )
                )

    def _check_py_security(self, code: str) -> None:
        """Check Python security issues."""
        # Check for eval/exec usage
        if re.search(r"\beval\s*\(", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="security",
                    issue="Use of eval() detected",
                    suggestion="Avoid eval() as it can execute arbitrary code. Use ast.literal_eval() for safe evaluation",
                )
            )

        if re.search(r"\bexec\s*\(", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="security",
                    issue="Use of exec() detected",
                    suggestion="Avoid exec() as it can execute arbitrary code",
                )
            )

        # Check for pickle usage
        if "pickle" in code:
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.HIGH,
                    category="security",
                    issue="Use of pickle detected",
                    suggestion="pickle can execute arbitrary code during deserialization. Use json for safer serialization",
                )
            )

        # Check for SQL string formatting
        if re.search(r"(execute|cursor)\s*\([^)]*%[^)]*\)", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.CRITICAL,
                    category="security",
                    issue="Potential SQL injection vulnerability",
                    suggestion="Use parameterized queries instead of string formatting for SQL",
                )
            )

    def _check_py_performance(self, code: str) -> None:
        """Check Python performance issues."""
        # Check for list concatenation in loops
        if re.search(r"for\s+\w+\s+in\s+.*:\s*\n\s*.*\+=\s*\[", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.MEDIUM,
                    category="performance",
                    issue="List concatenation in loop",
                    suggestion="Use list.append() or list comprehension instead of += for better performance",
                )
            )

        # Check for global variables
        if re.search(r"\bglobal\s+\w+", code):
            self._suggestions.append(
                ImprovementSuggestion(
                    priority=Priority.LOW,
                    category="performance",
                    issue="Use of global variables",
                    suggestion="Minimize global variable usage; pass as parameters for better performance and testability",
                )
            )

    def _score_python(self) -> QualityMetrics:
        """Calculate quality scores for Python code."""
        metrics = QualityMetrics()

        # Count issues by category
        syntax_issues = [s for s in self._suggestions if s.category == "syntax"]
        style_issues = [s for s in self._suggestions if s.category == "style"]
        security_issues = [s for s in self._suggestions if s.category == "security"]
        performance_issues = [s for s in self._suggestions if s.category == "performance"]

        # Calculate scores (deduct points for each issue)
        metrics.syntax = max(0, 100 - len(syntax_issues) * 20)
        metrics.style = max(0, 100 - len(style_issues) * 10)
        metrics.security = max(0, 100 - len(security_issues) * 15)
        metrics.performance = max(0, 100 - len(performance_issues) * 12)

        return metrics

    # ==================== Helper Methods ====================

    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    def _to_snake_case(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()

    def _apply_template_validation(self) -> None:
        """
        Apply FSA-1.2 template validation if available.

        This method will use the Template Library to validate code against
        standard templates and test cases.
        """
        # Placeholder for FSA-1.2 integration
        # When FSA-1.2 is available, this will:
        # 1. Load relevant templates from the library
        # 2. Compare code against templates
        # 3. Run template-based test cases
        # 4. Add suggestions based on template compliance
        pass

    def _optimize_suggestion_prompts(self) -> None:
        """
        Optimize suggestion messages using FSA-1.1 Prompt Optimizer.

        This method will use the Prompt Optimizer to generate more
        effective and clear improvement suggestions.
        """
        # Placeholder for FSA-1.1 integration
        # When FSA-1.1 is available, this will:
        # 1. Pass suggestion messages to the optimizer
        # 2. Receive optimized, clearer suggestions
        # 3. Update suggestions with improved wording
        pass

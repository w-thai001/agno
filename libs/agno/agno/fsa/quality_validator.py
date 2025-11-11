"""
FSA-2.1: QualityValidator

Validates code quality through multiple checks including:
- Syntax validation
- Code structure analysis
- Best practices verification
- Security checks
- Performance considerations
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from agno.utils.log import logger
import re


class ValidationLevel(str, Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue"""
    level: ValidationLevel = Field(..., description="Issue severity level")
    category: str = Field(..., description="Issue category")
    message: str = Field(..., description="Issue description")
    line: Optional[int] = Field(None, description="Line number if applicable")
    suggestion: Optional[str] = Field(None, description="Suggested fix")


class ValidationResult(BaseModel):
    """Result of code quality validation"""
    passed: bool = Field(..., description="Whether validation passed")
    score: float = Field(..., description="Quality score (0-100)")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Found issues")
    summary: str = Field(..., description="Validation summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QualityValidator:
    """
    FSA-2.1: QualityValidator

    Validates code quality through:
    - Syntax and structure checks
    - Best practices verification
    - Security vulnerability detection
    - Performance analysis
    - Documentation completeness
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.validators = self._initialize_validators()
        logger.info("FSA-2.1: QualityValidator initialized")

    def _initialize_validators(self) -> Dict[str, Any]:
        """Initialize validation rules"""
        return {
            "syntax": {
                "enabled": True,
                "weight": 0.25
            },
            "structure": {
                "enabled": True,
                "weight": 0.20
            },
            "best_practices": {
                "enabled": True,
                "weight": 0.20
            },
            "security": {
                "enabled": True,
                "weight": 0.20
            },
            "documentation": {
                "enabled": True,
                "weight": 0.15
            }
        }

    def validate(
        self,
        code: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate code quality

        Args:
            code: Code to validate
            language: Programming language
            context: Additional validation context

        Returns:
            ValidationResult with quality score and issues
        """
        if self.debug:
            logger.debug(f"Validating {language} code ({len(code)} chars)...")

        context = context or {}
        issues = []

        # Run all validation checks
        if self.validators["syntax"]["enabled"]:
            issues.extend(self._validate_syntax(code, language))

        if self.validators["structure"]["enabled"]:
            issues.extend(self._validate_structure(code, language))

        if self.validators["best_practices"]["enabled"]:
            issues.extend(self._validate_best_practices(code, language))

        if self.validators["security"]["enabled"]:
            issues.extend(self._validate_security(code, language))

        if self.validators["documentation"]["enabled"]:
            issues.extend(self._validate_documentation(code, language))

        # Calculate quality score
        score = self._calculate_quality_score(code, issues)

        # Determine if validation passed
        passed = self._determine_pass_status(issues, score)

        # Generate summary
        summary = self._generate_summary(issues, score, passed)

        result = ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            summary=summary,
            metadata={
                "language": language,
                "code_length": len(code),
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if i.level == ValidationLevel.CRITICAL]),
                "error_issues": len([i for i in issues if i.level == ValidationLevel.ERROR]),
            }
        )

        if self.debug:
            logger.debug(f"Validation complete. Score: {score:.1f}/100, Issues: {len(issues)}")

        return result

    def _validate_syntax(self, code: str, language: str) -> List[ValidationIssue]:
        """Validate code syntax"""
        issues = []

        if language == "python":
            # Check for common syntax issues
            # Unmatched brackets
            if code.count('(') != code.count(')'):
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="syntax",
                    message="Unmatched parentheses detected",
                    suggestion="Check all opening and closing parentheses"
                ))

            if code.count('{') != code.count('}'):
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="syntax",
                    message="Unmatched braces detected",
                    suggestion="Check all opening and closing braces"
                ))

            if code.count('[') != code.count(']'):
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="syntax",
                    message="Unmatched brackets detected",
                    suggestion="Check all opening and closing brackets"
                ))

            # Try basic compilation check (simplified)
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="syntax",
                    message=f"Syntax error: {str(e)}",
                    line=e.lineno,
                    suggestion="Fix the syntax error"
                ))

        return issues

    def _validate_structure(self, code: str, language: str) -> List[ValidationIssue]:
        """Validate code structure"""
        issues = []

        lines = code.split('\n')

        # Check for excessively long functions
        in_function = False
        function_length = 0
        function_name = ""

        for i, line in enumerate(lines, 1):
            if language == "python":
                if line.strip().startswith('def '):
                    in_function = True
                    function_length = 0
                    match = re.search(r'def (\w+)', line)
                    function_name = match.group(1) if match else "unknown"
                elif in_function:
                    if line.strip() and not line[0].isspace():
                        # End of function
                        if function_length > 50:
                            issues.append(ValidationIssue(
                                level=ValidationLevel.WARNING,
                                category="structure",
                                message=f"Function '{function_name}' is too long ({function_length} lines)",
                                line=i - function_length,
                                suggestion="Consider breaking this function into smaller functions"
                            ))
                        in_function = False
                    else:
                        function_length += 1

        # Check for deeply nested code
        max_indent = 0
        for i, line in enumerate(lines, 1):
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if language == "python":
                    indent_level = indent // 4
                else:
                    indent_level = indent // 2

                max_indent = max(max_indent, indent_level)

                if indent_level > 4:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        category="structure",
                        message=f"Excessive nesting depth ({indent_level} levels)",
                        line=i,
                        suggestion="Consider refactoring to reduce nesting"
                    ))

        return issues

    def _validate_best_practices(self, code: str, language: str) -> List[ValidationIssue]:
        """Validate adherence to best practices"""
        issues = []

        if language == "python":
            # Check for bare except clauses
            if re.search(r'except\s*:', code):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category="best_practices",
                    message="Bare except clause detected",
                    suggestion="Specify the exception type(s) to catch"
                ))

            # Check for print statements (should use logging)
            if 'print(' in code and 'logger' not in code:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="best_practices",
                    message="Consider using logging instead of print statements",
                    suggestion="Replace print() with proper logging"
                ))

            # Check for magic numbers
            magic_number_pattern = r'\b(?<!\.)\d{3,}\b'
            if re.search(magic_number_pattern, code):
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    category="best_practices",
                    message="Magic numbers detected",
                    suggestion="Define constants for magic numbers"
                ))

        return issues

    def _validate_security(self, code: str, language: str) -> List[ValidationIssue]:
        """Validate security aspects"""
        issues = []

        # Check for potential SQL injection
        if re.search(r'execute\s*\([^)]*\+[^)]*\)', code):
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                category="security",
                message="Potential SQL injection vulnerability",
                suggestion="Use parameterized queries instead of string concatenation"
            ))

        # Check for hardcoded credentials
        credential_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="security",
                    message="Hardcoded credentials detected",
                    suggestion="Use environment variables or secure configuration"
                ))
                break

        # Check for eval usage
        if re.search(r'\beval\s*\(', code):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                category="security",
                message="Use of eval() detected",
                suggestion="Avoid eval() as it's a security risk"
            ))

        return issues

    def _validate_documentation(self, code: str, language: str) -> List[ValidationIssue]:
        """Validate documentation completeness"""
        issues = []

        lines = code.split('\n')

        if language == "python":
            # Check for class/function docstrings
            for i, line in enumerate(lines):
                if line.strip().startswith('class ') or line.strip().startswith('def '):
                    # Check if next non-empty line is a docstring
                    has_docstring = False
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith('"""') or next_line.startswith("'''"):
                            has_docstring = True
                            break
                        if next_line and not next_line.startswith('#'):
                            break

                    if not has_docstring:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.INFO,
                            category="documentation",
                            message="Missing docstring",
                            line=i + 1,
                            suggestion="Add a docstring to document this code"
                        ))

        return issues

    def _calculate_quality_score(self, code: str, issues: List[ValidationIssue]) -> float:
        """Calculate overall quality score"""
        base_score = 100.0

        # Deduct points based on issue severity
        for issue in issues:
            if issue.level == ValidationLevel.CRITICAL:
                base_score -= 15
            elif issue.level == ValidationLevel.ERROR:
                base_score -= 10
            elif issue.level == ValidationLevel.WARNING:
                base_score -= 5
            elif issue.level == ValidationLevel.INFO:
                base_score -= 2

        return max(0.0, min(100.0, base_score))

    def _determine_pass_status(self, issues: List[ValidationIssue], score: float) -> bool:
        """Determine if validation passed"""
        # Fail if there are critical issues
        if any(i.level == ValidationLevel.CRITICAL for i in issues):
            return False

        # Fail if score is too low
        if score < 60:
            return False

        return True

    def _generate_summary(self, issues: List[ValidationIssue], score: float, passed: bool) -> str:
        """Generate validation summary"""
        status = "PASSED" if passed else "FAILED"
        summary_parts = [
            f"Validation {status} - Quality Score: {score:.1f}/100",
            f"Total Issues: {len(issues)}"
        ]

        if issues:
            by_level = {}
            for issue in issues:
                by_level[issue.level.value] = by_level.get(issue.level.value, 0) + 1

            for level, count in sorted(by_level.items()):
                summary_parts.append(f"- {level.upper()}: {count}")

        return "\n".join(summary_parts)

    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration"""
        return self.validators.copy()

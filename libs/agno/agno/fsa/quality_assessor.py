"""FSA-2.1: Code Quality Assessment

This module provides comprehensive code quality assessment using multiple metrics.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re


@dataclass
class QualityMetrics:
    """Quality metrics for code assessment"""

    # Overall quality score (0-100)
    overall_score: float = 0.0

    # Individual metric scores (0-100 each)
    readability: float = 0.0
    maintainability: float = 0.0
    efficiency: float = 0.0
    documentation: float = 0.0
    naming_quality: float = 0.0
    structure: float = 0.0
    best_practices: float = 0.0

    # Detailed feedback
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # Metadata
    code_length: int = 0
    language: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "overall_score": self.overall_score,
            "readability": self.readability,
            "maintainability": self.maintainability,
            "efficiency": self.efficiency,
            "documentation": self.documentation,
            "naming_quality": self.naming_quality,
            "structure": self.structure,
            "best_practices": self.best_practices,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "code_length": self.code_length,
            "language": self.language,
        }


class QualityAssessor:
    """FSA-2.1: Comprehensive code quality assessor

    Evaluates code quality across multiple dimensions:
    - Readability: How easy is the code to read and understand?
    - Maintainability: How easy is it to modify and extend?
    - Efficiency: How well does it perform?
    - Documentation: Are there comments and docs?
    - Naming: Are variables/functions well-named?
    - Structure: Is the code well-organized?
    - Best Practices: Does it follow language conventions?
    """

    def __init__(self):
        """Initialize the quality assessor"""
        self.weights = {
            "readability": 0.20,
            "maintainability": 0.15,
            "efficiency": 0.15,
            "documentation": 0.10,
            "naming_quality": 0.15,
            "structure": 0.15,
            "best_practices": 0.10,
        }

    def assess(self, code: str, language: Optional[str] = None) -> QualityMetrics:
        """Assess code quality and return detailed metrics

        Args:
            code: The code to assess
            language: Programming language (auto-detected if not provided)

        Returns:
            QualityMetrics object with detailed assessment
        """
        if not code or not code.strip():
            return QualityMetrics()

        # Detect language if not provided
        if language is None:
            language = self._detect_language(code)

        metrics = QualityMetrics(
            code_length=len(code),
            language=language
        )

        # Assess individual dimensions
        metrics.readability = self._assess_readability(code)
        metrics.maintainability = self._assess_maintainability(code)
        metrics.efficiency = self._assess_efficiency(code)
        metrics.documentation = self._assess_documentation(code)
        metrics.naming_quality = self._assess_naming(code)
        metrics.structure = self._assess_structure(code)
        metrics.best_practices = self._assess_best_practices(code, language)

        # Calculate overall score as weighted average
        metrics.overall_score = sum(
            getattr(metrics, key) * weight
            for key, weight in self.weights.items()
        )

        # Generate feedback
        self._generate_feedback(code, metrics)

        return metrics

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code"""
        code_lower = code.lower()

        if "function" in code_lower or "const" in code_lower or "let" in code_lower:
            return "javascript"
        elif "def" in code_lower and ":" in code:
            return "python"
        elif "public class" in code or "private" in code_lower:
            return "java"
        elif "#include" in code or "std::" in code:
            return "cpp"
        else:
            return "unknown"

    def _assess_readability(self, code: str) -> float:
        """Assess code readability (0-100)"""
        score = 100.0

        # Check line length
        lines = code.split('\n')
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 0:
            score -= min(20, long_lines * 5)

        # Check for proper spacing
        if '}{' in code or '){' in code:
            score -= 10

        # Check for single-line density
        avg_line_length = sum(len(line) for line in lines) / max(len(lines), 1)
        if avg_line_length > 60:
            score -= 15

        # Check for formatting consistency
        if code.count('  ') > 0 and code.count('\t') > 0:
            score -= 10  # Mixed tabs and spaces

        return max(0, score)

    def _assess_maintainability(self, code: str) -> float:
        """Assess code maintainability (0-100)"""
        score = 100.0

        # Check function/method length
        lines = code.split('\n')
        if len(lines) > 50:
            score -= 20
        elif len(lines) > 30:
            score -= 10

        # Check for magic numbers
        magic_numbers = re.findall(r'\b\d{2,}\b', code)
        if len(magic_numbers) > 0:
            score -= min(15, len(magic_numbers) * 5)

        # Check for single-letter variables (except i, j, k in loops)
        single_letters = re.findall(r'\b[a-h,l-z]\b', code)
        if len(single_letters) > 3:
            score -= 10

        return max(0, score)

    def _assess_efficiency(self, code: str) -> float:
        """Assess code efficiency (0-100)"""
        score = 100.0

        # Check for nested loops (potential O(n²) complexity)
        if code.count('for') > 1 or code.count('while') > 1:
            # Simple heuristic - could be improved
            nesting_level = max(
                code[:i].count('for') + code[:i].count('while')
                for i in range(len(code))
            )
            if nesting_level > 1:
                score -= 20

        # Check for repeated operations
        if '+=' in code or code.count('=') > 5:
            score -= 5

        # Check for string concatenation in loops (inefficient in many languages)
        if ('for' in code or 'while' in code) and ('+=' in code or '+ ' in code):
            score -= 15

        return max(0, score)

    def _assess_documentation(self, code: str) -> float:
        """Assess code documentation (0-100)"""
        score = 0.0

        # Check for comments
        comment_lines = code.count('//') + code.count('#') + code.count('/*')
        code_lines = len([line for line in code.split('\n') if line.strip()])

        if code_lines > 0:
            comment_ratio = comment_lines / code_lines
            score = min(100, comment_ratio * 300)

        # Bonus for JSDoc or docstrings
        if '/**' in code or '"""' in code or "'''" in code:
            score += 30

        return min(100, score)

    def _assess_naming(self, code: str) -> float:
        """Assess naming quality (0-100)"""
        score = 100.0

        # Check for descriptive function names
        functions = re.findall(r'function\s+(\w+)', code)
        functions += re.findall(r'def\s+(\w+)', code)

        short_names = [f for f in functions if len(f) < 3]
        if len(short_names) > 0:
            score -= min(20, len(short_names) * 10)

        # Check for camelCase/snake_case consistency
        has_camel = bool(re.search(r'[a-z][A-Z]', code))
        has_snake = bool(re.search(r'[a-z]_[a-z]', code))

        if has_camel and has_snake:
            score -= 10  # Inconsistent naming

        # Bonus for descriptive names
        descriptive = re.findall(r'\b[a-z]{4,}[A-Z][a-z]+', code)
        if len(descriptive) > 0:
            score += min(10, len(descriptive) * 2)

        return max(0, min(100, score))

    def _assess_structure(self, code: str) -> float:
        """Assess code structure (0-100)"""
        score = 100.0

        # Check for proper indentation
        lines = [line for line in code.split('\n') if line.strip()]
        if len(lines) > 0:
            indent_levels = [len(line) - len(line.lstrip()) for line in lines]
            if max(indent_levels) > 16:  # Too deeply nested
                score -= 20

        # Check for balanced braces/brackets
        if code.count('{') != code.count('}'):
            score -= 30
        if code.count('(') != code.count(')'):
            score -= 30

        # Check for separation of concerns (single function doing one thing)
        if code.count('function') > 1 or code.count('def') > 1:
            score += 10  # Good - multiple focused functions

        return max(0, score)

    def _assess_best_practices(self, code: str, language: str) -> float:
        """Assess adherence to best practices (0-100)"""
        score = 100.0

        if language == "javascript":
            # Check for var (should use let/const)
            if 'var ' in code:
                score -= 20

            # Check for === instead of ==
            if '==' in code and '===' not in code:
                score -= 10

            # Check for arrow functions
            if '=>' in code:
                score += 10

        elif language == "python":
            # Check for list comprehensions
            if '[' in code and 'for' in code and ']' in code:
                score += 10

            # Check for type hints
            if '->' in code or ':' in code:
                score += 10

        # General practices
        # Check for error handling
        if 'try' in code or 'catch' in code or 'except' in code:
            score += 15

        # Check for return statements
        if 'return' in code:
            score += 5

        return max(0, min(100, score))

    def _generate_feedback(self, code: str, metrics: QualityMetrics) -> None:
        """Generate human-readable feedback based on metrics"""

        # Identify strengths (scores > 80)
        if metrics.readability > 80:
            metrics.strengths.append("Code is highly readable with good formatting")
        if metrics.documentation > 80:
            metrics.strengths.append("Well-documented with helpful comments")
        if metrics.naming_quality > 80:
            metrics.strengths.append("Excellent naming conventions")
        if metrics.structure > 80:
            metrics.strengths.append("Well-structured and organized")

        # Identify weaknesses (scores < 50)
        if metrics.readability < 50:
            metrics.weaknesses.append("Poor readability - consider reformatting")
            metrics.suggestions.append("Break long lines, add spacing, use consistent indentation")

        if metrics.documentation < 50:
            metrics.weaknesses.append("Insufficient documentation")
            metrics.suggestions.append("Add comments explaining the logic and purpose")

        if metrics.naming_quality < 50:
            metrics.weaknesses.append("Poor naming - variables/functions are not descriptive")
            metrics.suggestions.append("Use descriptive names that explain purpose (e.g., 'calculateTotal' instead of 'calc')")

        if metrics.efficiency < 50:
            metrics.weaknesses.append("Potential efficiency issues")
            metrics.suggestions.append("Review algorithm complexity and optimize loops")

        if metrics.maintainability < 50:
            metrics.weaknesses.append("Difficult to maintain")
            metrics.suggestions.append("Refactor into smaller functions, avoid magic numbers")

        if metrics.structure < 50:
            metrics.weaknesses.append("Poor code structure")
            metrics.suggestions.append("Fix indentation, balance braces, reduce nesting")

        if metrics.best_practices < 50:
            metrics.weaknesses.append("Does not follow best practices")
            if metrics.language == "javascript":
                metrics.suggestions.append("Use const/let instead of var, use === for comparison")
            else:
                metrics.suggestions.append(f"Follow {metrics.language} best practices and conventions")

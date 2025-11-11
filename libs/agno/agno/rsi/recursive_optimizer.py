"""
FSA-3.2: RSI (Recursive Self-Improvement) Code Optimizer

Iteratively improves code through recursive self-improvement loops with:
- Quality assessment using FSA-2.1 (Code Quality Validator)
- Improvement generation (integrates with FSA-3.1 for complex improvements)
- Convergence detection and iteration tracking
- Rollback capability if quality degrades
- Comprehensive metrics and visualization
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from agno.utils.log import logger
from agno.validator import CodeQualityValidator


class ConvergenceReason(Enum):
    """Reason for RSI loop convergence."""

    MAX_ITERATIONS = "max_iterations"
    QUALITY_THRESHOLD = "quality_threshold"
    IMPROVEMENT_PLATEAU = "improvement_plateau"
    PERFECT_SCORE = "perfect_score"
    QUALITY_DEGRADATION = "quality_degradation"


class ImprovementType(Enum):
    """Types of code improvements."""

    SECURITY_FIX = "security_fix"
    STYLE_IMPROVEMENT = "style_improvement"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"
    BEST_PRACTICES = "best_practices"


@dataclass
class IterationMetrics:
    """Metrics for a single RSI iteration."""

    iteration: int
    quality_score: float
    quality_delta: float
    dimension_scores: Dict[str, int]
    improvements_applied: List[str]
    code_length: int
    validation_time_ms: float
    issues_fixed: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationResult:
    """Result of RSI optimization process."""

    original_code: str
    optimized_code: str
    original_quality: float
    final_quality: float
    total_improvement: float
    iterations: List[IterationMetrics]
    convergence_reason: ConvergenceReason
    total_time_ms: float
    success: bool
    language: str
    summary: str = ""


class RSICodeOptimizer:
    """
    Recursive Self-Improvement Code Optimizer.

    Iteratively improves code through multiple optimization cycles,
    integrating with FSA-2.1 for quality assessment and tracking
    improvement trajectories.
    """

    def __init__(
        self,
        validator: Optional[CodeQualityValidator] = None,
        convergence_threshold: float = 2.0,  # Minimum improvement per iteration
        quality_target: float = 95.0,  # Target quality score
        max_iterations: int = 10,
    ):
        """
        Initialize RSI Code Optimizer.

        Args:
            validator: FSA-2.1 Code Quality Validator instance
            convergence_threshold: Minimum quality improvement to continue (0-100)
            quality_target: Target quality score to achieve (0-100)
            max_iterations: Maximum number of iterations
        """
        self.validator = validator or CodeQualityValidator()
        self.convergence_threshold = convergence_threshold
        self.quality_target = quality_target
        self.max_iterations = max_iterations

        self.iteration_history: List[IterationMetrics] = []

        logger.info(
            "RSICodeOptimizer initialized (convergence=%.1f, target=%.1f, max_iter=%d)",
            convergence_threshold,
            quality_target,
            max_iterations,
        )

    def optimizeCode(
        self,
        code: str,
        language: str = "python",
        max_iterations: Optional[int] = None,
    ) -> OptimizationResult:
        """
        Optimize code through recursive self-improvement.

        Args:
            code: Source code to optimize
            language: Programming language
            max_iterations: Override default max iterations

        Returns:
            OptimizationResult with optimization trajectory and metrics
        """
        start_time = datetime.now()
        max_iter = max_iterations or self.max_iterations

        logger.info("Starting RSI optimization (max_iterations=%d)", max_iter)

        # Reset history
        self.iteration_history = []

        # Initial quality assessment
        original_quality = self.assessQuality(code, language)
        logger.info("Initial quality score: %.2f/100", original_quality)

        current_code = code
        current_quality = original_quality
        previous_quality = original_quality

        convergence_reason = ConvergenceReason.MAX_ITERATIONS

        # RSI Loop
        for iteration in range(1, max_iter + 1):
            logger.info("=" * 60)
            logger.info("RSI Iteration %d/%d", iteration, max_iter)
            logger.info("=" * 60)

            # Generate and apply improvements
            improved_code, improvements_applied = self.generateImprovements(
                current_code, language, iteration
            )

            # If no improvements possible, converge
            if not improvements_applied:
                logger.info("No further improvements possible")
                convergence_reason = ConvergenceReason.IMPROVEMENT_PLATEAU
                break

            # Assess improved code quality
            new_quality = self.assessQuality(improved_code, language)
            quality_delta = new_quality - current_quality

            logger.info("Quality: %.2f → %.2f (delta: %+.2f)", current_quality, new_quality, quality_delta)

            # Check for quality degradation
            if quality_delta < -1.0:  # Allow small fluctuations
                logger.warning("Quality degraded by %.2f points - rolling back", abs(quality_delta))
                convergence_reason = ConvergenceReason.QUALITY_DEGRADATION
                break

            # Track iteration metrics
            self.trackIteration(
                iteration=iteration,
                quality_score=new_quality,
                quality_delta=quality_delta,
                code=improved_code,
                improvements=improvements_applied,
                language=language,
            )

            # Update current state
            previous_quality = current_quality
            current_quality = new_quality
            current_code = improved_code

            # Check convergence conditions
            if current_quality >= self.quality_target:
                logger.info("Reached quality target: %.2f/100", current_quality)
                convergence_reason = ConvergenceReason.QUALITY_THRESHOLD
                break

            if current_quality >= 100:
                logger.info("Achieved perfect score: 100/100")
                convergence_reason = ConvergenceReason.PERFECT_SCORE
                break

            if quality_delta < self.convergence_threshold and iteration > 1:
                logger.info(
                    "Improvement plateau detected (delta: %.2f < threshold: %.2f)",
                    quality_delta,
                    self.convergence_threshold,
                )
                convergence_reason = ConvergenceReason.IMPROVEMENT_PLATEAU
                break

        # Calculate total time
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        # Determine final code (rollback if quality degraded)
        if convergence_reason == ConvergenceReason.QUALITY_DEGRADATION:
            final_code = code if not self.iteration_history else self.iteration_history[-1].code
            final_quality = self.iteration_history[-1].quality_score if self.iteration_history else original_quality
            success = False
        else:
            final_code = current_code
            final_quality = current_quality
            success = True

        total_improvement = final_quality - original_quality

        # Generate summary
        summary = self._generate_summary(
            original_quality,
            final_quality,
            total_improvement,
            len(self.iteration_history),
            convergence_reason,
        )

        result = OptimizationResult(
            original_code=code,
            optimized_code=final_code,
            original_quality=original_quality,
            final_quality=final_quality,
            total_improvement=total_improvement,
            iterations=self.iteration_history,
            convergence_reason=convergence_reason,
            total_time_ms=total_time,
            success=success,
            language=language,
            summary=summary,
        )

        logger.info(
            "RSI optimization complete: %.2f → %.2f (%+.2f) in %d iterations",
            original_quality,
            final_quality,
            total_improvement,
            len(self.iteration_history),
        )

        return result

    def assessQuality(self, code: str, language: str) -> float:
        """
        Assess code quality using FSA-2.1.

        Args:
            code: Source code to assess
            language: Programming language

        Returns:
            Quality score (0-100)
        """
        validation_result = self.validator.validateCode(code, language)
        return float(validation_result.report.overall_score)

    def generateImprovements(
        self, code: str, language: str, iteration: int
    ) -> Tuple[str, List[str]]:
        """
        Generate improvements for code.

        In production, this would use FSA-3.1 + LLM for intelligent improvements.
        For demo, uses rule-based transformations.

        Args:
            code: Source code to improve
            language: Programming language
            iteration: Current iteration number

        Returns:
            Tuple of (improved_code, list of improvements applied)
        """
        improved_code = code
        improvements_applied = []

        # Get current validation to identify issues
        validation = self.validator.validateCode(code, language)

        if language == "python":
            # Security improvements
            if "eval(" in improved_code:
                improved_code = self._fix_eval_usage(improved_code)
                improvements_applied.append("Replaced eval() with safer ast.literal_eval()")

            # SQL injection fixes
            if self._has_sql_injection(improved_code):
                improved_code = self._fix_sql_injection(improved_code)
                improvements_applied.append("Fixed SQL injection vulnerability with parameterized queries")

            # Style improvements
            if iteration <= 2:  # Early iterations focus on style
                # Add docstrings if missing
                if '"""' not in improved_code and "def " in improved_code:
                    improved_code = self._add_docstrings(improved_code)
                    improvements_applied.append("Added docstrings to functions")

                # Fix naming conventions
                if self._has_naming_issues(improved_code):
                    improved_code = self._fix_naming_conventions(improved_code)
                    improvements_applied.append("Fixed naming conventions (snake_case)")

            # Error handling improvements
            if iteration >= 2:  # Later iterations add error handling
                if "try:" not in improved_code and "def " in improved_code:
                    improved_code = self._add_error_handling(improved_code)
                    improvements_applied.append("Added comprehensive error handling")

            # Performance improvements
            if iteration >= 3:
                if "for i in range(len(" in improved_code:
                    improved_code = self._optimize_loops(improved_code)
                    improvements_applied.append("Optimized loop patterns")

        elif language == "javascript":
            # Security improvements
            if ".innerHTML =" in improved_code:
                improved_code = self._fix_xss_vulnerability(improved_code)
                improvements_applied.append("Fixed XSS vulnerability (innerHTML → textContent)")

            # Async improvements
            if "async " in improved_code and "await" not in improved_code:
                improvements_applied.append("Note: Async function should use await")

        return improved_code, improvements_applied

    def trackIteration(
        self,
        iteration: int,
        quality_score: float,
        quality_delta: float,
        code: str,
        improvements: List[str],
        language: str,
    ) -> None:
        """
        Track metrics for an iteration.

        Args:
            iteration: Iteration number
            quality_score: Quality score achieved
            quality_delta: Improvement from previous iteration
            code: Current code state
            improvements: List of improvements applied
            language: Programming language
        """
        # Get detailed validation
        validation = self.validator.validateCode(code, language)

        # Extract dimension scores
        dimension_scores = {
            dim: score.score for dim, score in validation.report.dimensions.items()
        }

        # Count issues fixed
        issues_fixed = len(improvements)

        metrics = IterationMetrics(
            iteration=iteration,
            quality_score=quality_score,
            quality_delta=quality_delta,
            dimension_scores=dimension_scores,
            improvements_applied=improvements,
            code_length=len(code),
            validation_time_ms=validation.execution_time_ms,
            issues_fixed=issues_fixed,
        )

        # Store code (not in dataclass to keep it light)
        metrics.code = code

        self.iteration_history.append(metrics)

        logger.info(
            "Iteration %d tracked: quality=%.2f, delta=%+.2f, improvements=%d",
            iteration,
            quality_score,
            quality_delta,
            issues_fixed,
        )

    # Rule-based improvement helpers (for demo)

    def _fix_eval_usage(self, code: str) -> str:
        """Replace eval() with ast.literal_eval()."""
        if "import ast" not in code:
            code = "import ast\n" + code
        code = re.sub(r'\beval\s*\(', 'ast.literal_eval(', code)
        return code

    def _has_sql_injection(self, code: str) -> bool:
        """Check for SQL injection patterns."""
        patterns = [
            r'execute\s*\(\s*["\'].*\+.*["\']',
            r'execute\s*\(\s*f["\']',
            r'execute\s*\(\s*["\'].*%.*["\']',
        ]
        return any(re.search(pattern, code) for pattern in patterns)

    def _fix_sql_injection(self, code: str) -> str:
        """Fix SQL injection with parameterized queries."""
        # Simple transformation for demo
        code = re.sub(
            r'execute\((["\'])(.+?)\+\s*str\((.+?)\)\s*\+\s*(["\'].*?)\1\)',
            r'execute("\2?\4", (\3,))',
            code
        )
        return code

    def _add_docstrings(self, code: str) -> str:
        """Add basic docstrings to functions."""
        lines = code.split('\n')
        new_lines = []

        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.strip().startswith('def ') and ':' in line:
                # Check if next line is not already a docstring
                if i + 1 < len(lines) and '"""' not in lines[i + 1]:
                    indent = len(line) - len(line.lstrip())
                    func_name = line.strip().split('(')[0].replace('def ', '')
                    docstring = ' ' * (indent + 4) + f'"""{func_name.replace("_", " ").title()}."""'
                    new_lines.append(docstring)

        return '\n'.join(new_lines)

    def _has_naming_issues(self, code: str) -> bool:
        """Check for naming convention issues."""
        # Check for camelCase in Python functions
        return bool(re.search(r'\bdef [a-z]+[A-Z]', code))

    def _fix_naming_conventions(self, code: str) -> str:
        """Fix naming conventions."""
        # Convert camelCase to snake_case for function names
        def camel_to_snake(match):
            name = match.group(1)
            snake = re.sub('([a-z])([A-Z])', r'\1_\2', name).lower()
            return f"def {snake}"

        code = re.sub(r'\bdef ([a-z]+[A-Z][a-zA-Z]*)', camel_to_snake, code)
        return code

    def _add_error_handling(self, code: str) -> str:
        """Add basic error handling."""
        # Wrap function body in try-except (simplified for demo)
        if "try:" in code:
            return code  # Already has error handling

        lines = code.split('\n')
        new_lines = []
        in_function = False
        function_indent = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and ':' in line:
                in_function = True
                function_indent = len(line) - len(line.lstrip())
                new_lines.append(line)

                # Skip docstring if present
                if i + 1 < len(lines) and '"""' in lines[i + 1]:
                    new_lines.append(lines[i + 1])
                    # Add try after docstring
                    new_lines.append(' ' * (function_indent + 4) + 'try:')
                else:
                    # Add try immediately
                    new_lines.append(' ' * (function_indent + 4) + 'try:')
            elif in_function and line.strip() and not line.strip().startswith('#'):
                # Indent function body
                new_lines.append(' ' * 4 + line)

                # Check if function ends
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line and not next_line[0].isspace():
                        # Function ends, add except
                        new_lines.append(' ' * (function_indent + 4) + 'except Exception as e:')
                        new_lines.append(' ' * (function_indent + 8) + 'raise')
                        in_function = False
            else:
                new_lines.append(line)

        return '\n'.join(new_lines)

    def _optimize_loops(self, code: str) -> str:
        """Optimize loop patterns."""
        # Replace range(len()) patterns
        code = re.sub(
            r'for (\w+) in range\(len\((\w+)\)\):\s*\n\s+(.+?)\[\\1\]',
            r'for item in \2:\n    \3item',
            code
        )
        return code

    def _fix_xss_vulnerability(self, code: str) -> str:
        """Fix XSS vulnerability in JavaScript."""
        code = code.replace('.innerHTML =', '.textContent =')
        return code

    def _generate_summary(
        self,
        original: float,
        final: float,
        improvement: float,
        iterations: int,
        reason: ConvergenceReason,
    ) -> str:
        """Generate optimization summary."""
        if improvement > 0:
            status = "SUCCESS"
        elif improvement == 0:
            status = "NO_CHANGE"
        else:
            status = "DEGRADED"

        summary = f"RSI Optimization {status}\n"
        summary += f"Quality: {original:.1f} → {final:.1f} ({improvement:+.1f})\n"
        summary += f"Iterations: {iterations}\n"
        summary += f"Convergence: {reason.value}"

        return summary

    def get_optimization_trajectory(self) -> List[float]:
        """Get quality scores across iterations."""
        return [m.quality_score for m in self.iteration_history]

    def get_dimension_trajectories(self) -> Dict[str, List[float]]:
        """Get dimension scores across iterations."""
        if not self.iteration_history:
            return {}

        dimensions = list(self.iteration_history[0].dimension_scores.keys())
        trajectories = {dim: [] for dim in dimensions}

        for metrics in self.iteration_history:
            for dim, score in metrics.dimension_scores.items():
                trajectories[dim].append(score)

        return trajectories

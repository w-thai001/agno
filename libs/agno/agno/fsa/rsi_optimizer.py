"""FSA-3.2: Recursive Self-Improvement (RSI) Code Optimizer

This module implements a recursive self-improvement loop for code optimization.
It uses FSA-2.1 for quality assessment and FSA-3.1 for multi-step improvements.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from agno.fsa.quality_assessor import QualityAssessor, QualityMetrics
from agno.fsa.code_improver import CodeImprover


@dataclass
class IterationResult:
    """Result of a single RSI iteration"""

    iteration: int
    code: str
    metrics: QualityMetrics
    quality_score: float
    improvement_delta: float
    focus_areas: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "iteration": self.iteration,
            "code": self.code,
            "metrics": self.metrics.to_dict(),
            "quality_score": self.quality_score,
            "improvement_delta": self.improvement_delta,
            "focus_areas": self.focus_areas,
            "timestamp": self.timestamp,
        }


@dataclass
class RSIResult:
    """Complete result of RSI optimization"""

    initial_code: str
    final_code: str
    iterations: List[IterationResult]
    total_iterations: int
    initial_quality: float
    final_quality: float
    total_improvement: float
    converged: bool
    convergence_reason: str
    avg_improvement_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "initial_code": self.initial_code,
            "final_code": self.final_code,
            "iterations": [it.to_dict() for it in self.iterations],
            "total_iterations": self.total_iterations,
            "initial_quality": self.initial_quality,
            "final_quality": self.final_quality,
            "total_improvement": self.total_improvement,
            "converged": self.converged,
            "convergence_reason": self.convergence_reason,
            "avg_improvement_rate": self.avg_improvement_rate,
        }

    def get_quality_trajectory(self) -> List[Tuple[int, float]]:
        """Get quality scores per iteration

        Returns:
            List of (iteration, quality_score) tuples
        """
        return [(it.iteration, it.quality_score) for it in self.iterations]

    def print_summary(self) -> None:
        """Print a human-readable summary of the optimization"""
        print("\n" + "=" * 70)
        print("RSI CODE OPTIMIZATION SUMMARY")
        print("=" * 70)
        print(f"\nInitial Quality Score: {self.initial_quality:.2f}/100")
        print(f"Final Quality Score:   {self.final_quality:.2f}/100")
        print(f"Total Improvement:     +{self.total_improvement:.2f} points")
        print(f"Iterations:            {self.total_iterations}")
        print(f"Avg Improvement Rate:  {self.avg_improvement_rate:.2f} points/iteration")
        print(f"Converged:             {self.converged}")
        print(f"Reason:                {self.convergence_reason}")

        print("\n" + "-" * 70)
        print("QUALITY TRAJECTORY (iteration -> score)")
        print("-" * 70)
        for iteration, score in self.get_quality_trajectory():
            bar_length = int(score / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            print(f"Iteration {iteration}: {score:5.2f} {bar}")

        print("\n" + "-" * 70)
        print("INITIAL CODE")
        print("-" * 70)
        print(self.initial_code)

        print("\n" + "-" * 70)
        print("FINAL CODE")
        print("-" * 70)
        print(self.final_code)
        print("\n" + "=" * 70 + "\n")


class RSICodeOptimizer:
    """FSA-3.2: Recursive Self-Improvement Code Optimizer

    Implements a recursive self-improvement loop:
    1. Assess current code quality (using FSA-2.1)
    2. Identify weaknesses and plan improvements
    3. Apply improvements (using FSA-3.1)
    4. Validate improvements
    5. Repeat until convergence

    Convergence detection:
    - Quality plateau (improvement < threshold for N iterations)
    - Maximum iterations reached
    - Quality target achieved
    """

    def __init__(
        self,
        convergence_threshold: float = 2.0,
        plateau_patience: int = 2,
        max_iterations: int = 10,
        target_quality: float = 90.0,
    ):
        """Initialize RSI Code Optimizer

        Args:
            convergence_threshold: Minimum improvement to continue (points)
            plateau_patience: Number of iterations to wait before declaring plateau
            max_iterations: Maximum number of improvement iterations
            target_quality: Target quality score (0-100)
        """
        self.convergence_threshold = convergence_threshold
        self.plateau_patience = plateau_patience
        self.max_iterations = max_iterations
        self.target_quality = target_quality

        # Initialize FSA-2.1 and FSA-3.1
        self.assessor = QualityAssessor()
        self.improver = CodeImprover()

    def improve_code(
        self,
        code: str,
        iterations: Optional[int] = None,
        language: Optional[str] = None,
        verbose: bool = True,
    ) -> RSIResult:
        """Execute RSI loop to improve code

        Args:
            code: Initial code to improve
            iterations: Number of iterations (uses max_iterations if None)
            language: Programming language (auto-detected if None)
            verbose: Print progress information

        Returns:
            RSIResult with complete optimization history
        """
        if iterations is None:
            iterations = self.max_iterations

        if verbose:
            print(f"\n{'='*70}")
            print("STARTING RSI CODE OPTIMIZATION")
            print(f"{'='*70}")
            print(f"Max iterations: {iterations}")
            print(f"Convergence threshold: {self.convergence_threshold} points")
            print(f"Target quality: {self.target_quality}/100")
            print(f"{'='*70}\n")

        # Store initial code
        initial_code = code
        current_code = code

        # Track iteration results
        iteration_results: List[IterationResult] = []

        # Assess initial quality
        initial_metrics = self.assess_quality(current_code)
        previous_score = initial_metrics.overall_score

        if verbose:
            print(f"Initial Quality Score: {previous_score:.2f}/100\n")

        # Track plateau
        plateau_count = 0
        converged = False
        convergence_reason = ""

        # RSI Loop: Assess → Improve → Validate → Repeat
        for i in range(iterations):
            iteration_num = i + 1

            if verbose:
                print(f"\n{'-'*70}")
                print(f"ITERATION {iteration_num}")
                print(f"{'-'*70}")

            # Step 1: Assess current quality
            current_metrics = self.assess_quality(current_code)
            current_score = current_metrics.overall_score

            if verbose:
                print(f"Current Quality Score: {current_score:.2f}/100")

            # Step 2: Calculate improvement delta
            improvement_delta = current_score - previous_score

            if verbose:
                print(f"Improvement Delta: {improvement_delta:+.2f} points")

            # Step 3: Identify focus areas for improvement
            focus_areas = self._identify_focus_areas(current_metrics)

            if verbose:
                print(f"Focus Areas: {', '.join(focus_areas)}")

            # Store iteration result
            iteration_results.append(
                IterationResult(
                    iteration=iteration_num,
                    code=current_code,
                    metrics=current_metrics,
                    quality_score=current_score,
                    improvement_delta=improvement_delta,
                    focus_areas=focus_areas,
                )
            )

            # Step 4: Check convergence conditions
            # Condition 1: Target quality achieved
            if current_score >= self.target_quality:
                converged = True
                convergence_reason = f"Target quality {self.target_quality:.2f} achieved"
                if verbose:
                    print(f"\n✓ {convergence_reason}")
                break

            # Condition 2: Quality plateau detected
            if improvement_delta < self.convergence_threshold:
                plateau_count += 1
                if verbose:
                    print(f"Plateau detected ({plateau_count}/{self.plateau_patience})")

                if plateau_count >= self.plateau_patience:
                    converged = True
                    convergence_reason = f"Quality plateau reached (improvement < {self.convergence_threshold} for {self.plateau_patience} iterations)"
                    if verbose:
                        print(f"\n✓ {convergence_reason}")
                    break
            else:
                plateau_count = 0  # Reset plateau counter

            # Condition 3: Maximum iterations (checked by loop)
            if iteration_num >= iterations:
                convergence_reason = f"Maximum iterations ({iterations}) reached"
                if verbose:
                    print(f"\n✓ {convergence_reason}")
                break

            # Step 5: Apply improvements
            if verbose:
                print(f"\nApplying improvements to: {focus_areas}")

            improved_code = self.improver.improve(
                current_code,
                focus_areas=focus_areas,
                language=language
            )

            # Step 6: Validate improvements
            improved_metrics = self.assess_quality(improved_code)
            improved_score = improved_metrics.overall_score

            if verbose:
                print(f"Post-improvement Score: {improved_score:.2f}/100")
                print(f"Net Improvement: {improved_score - current_score:+.2f} points")

            # Update for next iteration
            current_code = improved_code
            previous_score = current_score

        # Calculate final metrics
        final_metrics = self.assess_quality(current_code)
        final_score = final_metrics.overall_score
        total_improvement = final_score - initial_metrics.overall_score
        avg_improvement_rate = total_improvement / len(iteration_results) if iteration_results else 0

        # Create result
        result = RSIResult(
            initial_code=initial_code,
            final_code=current_code,
            iterations=iteration_results,
            total_iterations=len(iteration_results),
            initial_quality=initial_metrics.overall_score,
            final_quality=final_score,
            total_improvement=total_improvement,
            converged=converged,
            convergence_reason=convergence_reason,
            avg_improvement_rate=avg_improvement_rate,
        )

        if verbose:
            result.print_summary()

        return result

    def assess_quality(self, code: str) -> QualityMetrics:
        """Assess code quality using FSA-2.1

        Args:
            code: Code to assess

        Returns:
            QualityMetrics with detailed assessment
        """
        return self.assessor.assess(code)

    def track_progress(self, result: RSIResult) -> Dict[str, Any]:
        """Track and analyze optimization progress

        Args:
            result: RSIResult from improve_code()

        Returns:
            Dictionary with progress metrics
        """
        trajectory = result.get_quality_trajectory()

        progress = {
            "total_iterations": result.total_iterations,
            "initial_quality": result.initial_quality,
            "final_quality": result.final_quality,
            "total_improvement": result.total_improvement,
            "improvement_percentage": (
                (result.total_improvement / result.initial_quality * 100)
                if result.initial_quality > 0 else 0
            ),
            "avg_improvement_rate": result.avg_improvement_rate,
            "converged": result.converged,
            "convergence_reason": result.convergence_reason,
            "quality_trajectory": trajectory,
            "iteration_deltas": [
                it.improvement_delta for it in result.iterations
            ],
        }

        return progress

    def _identify_focus_areas(self, metrics: QualityMetrics) -> List[str]:
        """Identify areas that need improvement based on metrics

        Args:
            metrics: Quality metrics from assessment

        Returns:
            List of focus areas ordered by priority
        """
        # Score each dimension
        scores = {
            "naming": metrics.naming_quality,
            "documentation": metrics.documentation,
            "structure": metrics.structure,
            "readability": metrics.readability,
            "best_practices": metrics.best_practices,
            "efficiency": metrics.efficiency,
        }

        # Sort by score (lowest first = highest priority)
        sorted_areas = sorted(scores.items(), key=lambda x: x[1])

        # Return areas with score < 75 (needs improvement)
        focus_areas = [area for area, score in sorted_areas if score < 75]

        # If no areas need improvement, focus on the lowest scoring ones
        if not focus_areas:
            focus_areas = [sorted_areas[0][0], sorted_areas[1][0]]

        # Limit to top 3 areas to avoid too many changes at once
        return focus_areas[:3]

    def export_results(self, result: RSIResult, filename: str) -> None:
        """Export optimization results to JSON file

        Args:
            result: RSIResult to export
            filename: Output filename
        """
        with open(filename, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        print(f"\nResults exported to: {filename}")

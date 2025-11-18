"""
Prompt Optimizer FSA (Finite State Automaton)

This module provides a comprehensive prompt optimization system that analyzes and improves
AI prompts through token efficiency analysis, clarity enhancement, and pattern matching.

The PromptOptimizerFSA operates as a state machine that processes prompts through multiple
optimization stages to maximize output quality while minimizing token consumption.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field


class FSAState(str, Enum):
    """States in the prompt optimization finite state automaton."""

    INITIAL = "initial"
    VALIDATING = "validating"
    ANALYZING_TOKENS = "analyzing_tokens"
    ANALYZING_CLARITY = "analyzing_clarity"
    GENERATING_IMPROVEMENTS = "generating_improvements"
    APPLYING_OPTIMIZATIONS = "applying_optimizations"
    COMPLETED = "completed"
    ERROR = "error"


class ImprovementType(str, Enum):
    """Types of improvements that can be applied to prompts."""

    TOKEN_REDUCTION = "token_reduction"
    CLARITY_ENHANCEMENT = "clarity_enhancement"
    STRUCTURE_IMPROVEMENT = "structure_improvement"
    SPECIFICITY_BOOST = "specificity_boost"
    REDUNDANCY_REMOVAL = "redundancy_removal"
    INSTRUCTION_REFINEMENT = "instruction_refinement"


class ValidationResult(BaseModel):
    """Result of prompt validation."""

    is_valid: bool = Field(description="Whether the prompt is valid")
    issues: List[str] = Field(default_factory=list, description="List of validation issues")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    quality_score: float = Field(default=0.0, description="Overall quality score (0-100)")


class TokenAnalysis(BaseModel):
    """Detailed token analysis of a prompt."""

    token_count: int = Field(description="Estimated token count")
    efficiency_score: float = Field(description="Token efficiency score (0-100)")
    redundant_tokens: int = Field(default=0, description="Number of redundant tokens")
    optimal_token_count: int = Field(description="Optimal token count for this prompt")
    word_count: int = Field(description="Word count")
    avg_word_length: float = Field(description="Average word length")
    repetition_ratio: float = Field(default=0.0, description="Ratio of repeated phrases")


class Improvement(BaseModel):
    """A single improvement suggestion for a prompt."""

    type: ImprovementType = Field(description="Type of improvement")
    description: str = Field(description="Description of the improvement")
    original_text: Optional[str] = Field(default=None, description="Original text to replace")
    improved_text: Optional[str] = Field(default=None, description="Improved replacement text")
    impact_score: float = Field(description="Expected impact (0-100)")
    token_savings: int = Field(default=0, description="Expected token savings")


class PromptMetrics(BaseModel):
    """Metrics comparing original and optimized prompts."""

    original_tokens: int = Field(description="Original token count")
    optimized_tokens: int = Field(description="Optimized token count")
    token_reduction: int = Field(description="Number of tokens reduced")
    token_reduction_percentage: float = Field(description="Percentage of tokens reduced")
    clarity_improvement: float = Field(description="Clarity improvement score (0-100)")
    optimization_time_ms: float = Field(description="Time taken for optimization in milliseconds")


class OptimizedPrompt(BaseModel):
    """Result of prompt optimization."""

    optimization_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique optimization ID")
    original_prompt: str = Field(description="Original prompt text")
    optimized_prompt: str = Field(description="Optimized prompt text")
    improvements_applied: List[Improvement] = Field(
        default_factory=list, description="List of improvements applied"
    )
    metrics: PromptMetrics = Field(description="Optimization metrics")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of optimization")
    validation_result: Optional[ValidationResult] = Field(default=None, description="Validation result")


@dataclass
class OptimizationHistory:
    """Tracks history of optimizations performed."""

    optimizations: List[OptimizedPrompt] = field(default_factory=list)
    total_optimizations: int = 0
    total_tokens_saved: int = 0
    avg_improvement_score: float = 0.0

    def add_optimization(self, optimization: OptimizedPrompt) -> None:
        """Add an optimization to history."""
        self.optimizations.append(optimization)
        self.total_optimizations += 1
        self.total_tokens_saved += optimization.metrics.token_reduction
        if self.total_optimizations > 0:
            self.avg_improvement_score = (
                sum(opt.metrics.clarity_improvement for opt in self.optimizations) / self.total_optimizations
            )


@dataclass
class PromptOptimizerFSA:
    """
    Prompt Optimizer Finite State Automaton.

    A comprehensive prompt optimization system that uses state machine patterns to process
    prompts through multiple optimization stages including validation, token analysis,
    clarity enhancement, and improvement application.

    Attributes:
        state: Current state of the FSA
        optimization_history: History of all optimizations performed
        enable_aggressive_optimization: Enable more aggressive optimization strategies
        min_quality_threshold: Minimum quality threshold (0-100) for prompts
        max_iterations: Maximum optimization iterations
    """

    state: FSAState = FSAState.INITIAL
    optimization_history: OptimizationHistory = field(default_factory=OptimizationHistory)
    enable_aggressive_optimization: bool = False
    min_quality_threshold: float = 50.0
    max_iterations: int = 3

    # Common prompt anti-patterns to detect and fix
    ANTI_PATTERNS: Dict[str, str] = field(
        default_factory=lambda: {
            r"\b(very|really|just|basically|actually|literally)\b": "",  # Filler words
            r"\s+": " ",  # Multiple spaces
            r"\.{2,}": ".",  # Multiple periods
            r"\?{2,}": "?",  # Multiple question marks
            r"!{2,}": "!",  # Multiple exclamation marks
            r"\bplease\s+please\b": "please",  # Repeated please
            r"\b(\w+)\s+\1\b": r"\1",  # Repeated words
        }
    )

    # Optimization templates for common patterns
    OPTIMIZATION_TEMPLATES: Dict[str, Tuple[str, str]] = field(
        default_factory=lambda: {
            "be_specific": (
                r"\bcan you\b",
                "Define specifically what you want",
            ),
            "remove_politeness": (
                r"\b(please|kindly|if you (could|would|don't mind))\b",
                "",
            ),
            "direct_instruction": (
                r"\bI want you to\b",
                "",
            ),
            "eliminate_uncertainty": (
                r"\b(maybe|perhaps|possibly|might|could you)\b",
                "",
            ),
        }
    )

    def __post_init__(self) -> None:
        """Initialize the FSA with default settings."""
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the FSA to initial state."""
        self.state = FSAState.INITIAL

    def _transition_to(self, new_state: FSAState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: The state to transition to
        """
        self.state = new_state

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple heuristic: ~0.75 tokens per word for English text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        words = text.split()
        # More accurate estimation: count words, punctuation, and special characters
        word_count = len(words)
        punctuation_count = sum(1 for char in text if char in ".,!?;:\"'()[]{}—-")
        return int(word_count * 0.75 + punctuation_count * 0.3)

    def _calculate_word_stats(self, text: str) -> Tuple[int, float]:
        """
        Calculate word statistics.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (word_count, avg_word_length)
        """
        words = re.findall(r"\b\w+\b", text)
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / max(word_count, 1)
        return word_count, avg_word_length

    def _calculate_repetition_ratio(self, text: str) -> float:
        """
        Calculate the ratio of repeated phrases in text.

        Args:
            text: Text to analyze

        Returns:
            Repetition ratio (0.0-1.0)
        """
        # Find all 3-word phrases
        words = text.lower().split()
        if len(words) < 3:
            return 0.0

        phrases = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]
        if not phrases:
            return 0.0

        unique_phrases = set(phrases)
        repetition_ratio = 1.0 - (len(unique_phrases) / len(phrases))
        return repetition_ratio

    def _detect_redundancy(self, text: str) -> int:
        """
        Detect redundant tokens in text.

        Args:
            text: Text to analyze

        Returns:
            Number of redundant tokens
        """
        redundant_count = 0

        # Check for filler words
        filler_words = ["very", "really", "just", "basically", "actually", "literally", "quite"]
        for word in filler_words:
            redundant_count += len(re.findall(rf"\b{word}\b", text, re.IGNORECASE))

        # Check for repeated words
        words = text.lower().split()
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                redundant_count += 1

        return redundant_count

    def validate(self, prompt: str) -> ValidationResult:
        """
        Validate a prompt and check its quality.

        Args:
            prompt: The prompt to validate

        Returns:
            ValidationResult with validation details
        """
        self._transition_to(FSAState.VALIDATING)

        issues = []
        warnings = []
        quality_score = 100.0

        # Check if prompt is empty
        if not prompt or not prompt.strip():
            issues.append("Prompt is empty")
            quality_score = 0.0
            return ValidationResult(is_valid=False, issues=issues, warnings=warnings, quality_score=quality_score)

        # Check minimum length
        if len(prompt.strip()) < 10:
            issues.append("Prompt is too short (minimum 10 characters)")
            quality_score -= 30.0

        # Check maximum length
        if len(prompt) > 10000:
            warnings.append("Prompt is very long (>10000 characters), may be inefficient")
            quality_score -= 10.0

        # Check for excessive repetition
        repetition_ratio = self._calculate_repetition_ratio(prompt)
        if repetition_ratio > 0.3:
            warnings.append(f"High repetition detected ({repetition_ratio:.1%})")
            quality_score -= 15.0

        # Check for unclear instructions
        if not any(keyword in prompt.lower() for keyword in ["write", "create", "generate", "explain", "describe", "analyze", "summarize"]):
            warnings.append("Prompt lacks clear action verbs")
            quality_score -= 10.0

        # Check for excessive politeness (token waste)
        politeness_words = len(re.findall(r"\b(please|kindly|if you could|would you mind)\b", prompt, re.IGNORECASE))
        if politeness_words > 3:
            warnings.append("Excessive politeness may waste tokens")
            quality_score -= 5.0

        is_valid = len(issues) == 0
        quality_score = max(0.0, min(100.0, quality_score))

        return ValidationResult(is_valid=is_valid, issues=issues, warnings=warnings, quality_score=quality_score)

    def analyze_tokens(self, prompt: str) -> TokenAnalysis:
        """
        Perform detailed token analysis on a prompt.

        Args:
            prompt: The prompt to analyze

        Returns:
            TokenAnalysis with detailed token metrics
        """
        self._transition_to(FSAState.ANALYZING_TOKENS)

        token_count = self._estimate_tokens(prompt)
        word_count, avg_word_length = self._calculate_word_stats(prompt)
        redundant_tokens = self._detect_redundancy(prompt)
        repetition_ratio = self._calculate_repetition_ratio(prompt)

        # Calculate optimal token count (removing redundancy)
        optimal_token_count = token_count - redundant_tokens

        # Calculate efficiency score
        efficiency_score = 100.0
        if redundant_tokens > 0:
            efficiency_score -= (redundant_tokens / token_count) * 50.0
        if repetition_ratio > 0.2:
            efficiency_score -= repetition_ratio * 30.0
        efficiency_score = max(0.0, min(100.0, efficiency_score))

        return TokenAnalysis(
            token_count=token_count,
            efficiency_score=efficiency_score,
            redundant_tokens=redundant_tokens,
            optimal_token_count=optimal_token_count,
            word_count=word_count,
            avg_word_length=avg_word_length,
            repetition_ratio=repetition_ratio,
        )

    def suggest_improvements(self, prompt: str) -> List[Improvement]:
        """
        Generate optimization suggestions for a prompt.

        Args:
            prompt: The prompt to analyze

        Returns:
            List of Improvement suggestions
        """
        self._transition_to(FSAState.GENERATING_IMPROVEMENTS)

        improvements = []

        # Detect and suggest removal of filler words
        filler_words = ["very", "really", "just", "basically", "actually", "literally"]
        for word in filler_words:
            matches = re.findall(rf"\b{word}\b", prompt, re.IGNORECASE)
            if matches:
                token_savings = len(matches)
                improvements.append(
                    Improvement(
                        type=ImprovementType.TOKEN_REDUCTION,
                        description=f"Remove filler word '{word}' ({len(matches)} occurrences)",
                        original_text=word,
                        improved_text="",
                        impact_score=20.0 + (token_savings * 5),
                        token_savings=token_savings,
                    )
                )

        # Detect excessive politeness
        politeness_pattern = r"\b(please|kindly|if you could|would you mind)\b"
        politeness_matches = re.findall(politeness_pattern, prompt, re.IGNORECASE)
        if len(politeness_matches) > 2:
            improvements.append(
                Improvement(
                    type=ImprovementType.TOKEN_REDUCTION,
                    description="Reduce excessive politeness to save tokens",
                    original_text=None,
                    improved_text=None,
                    impact_score=30.0,
                    token_savings=len(politeness_matches) - 1,
                )
            )

        # Detect vague language
        vague_patterns = [
            (r"\bcan you\b", "Use direct instructions instead of questions"),
            (r"\btry to\b", "Use definitive language: 'do X' instead of 'try to do X'"),
            (r"\bmight|maybe|perhaps\b", "Remove uncertainty words for clearer instructions"),
        ]
        for pattern, description in vague_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                improvements.append(
                    Improvement(
                        type=ImprovementType.CLARITY_ENHANCEMENT,
                        description=description,
                        original_text=None,
                        improved_text=None,
                        impact_score=40.0,
                        token_savings=2,
                    )
                )

        # Detect repeated phrases
        repetition_ratio = self._calculate_repetition_ratio(prompt)
        if repetition_ratio > 0.2:
            improvements.append(
                Improvement(
                    type=ImprovementType.REDUNDANCY_REMOVAL,
                    description=f"High repetition detected ({repetition_ratio:.1%}). Consider consolidating repeated ideas.",
                    original_text=None,
                    improved_text=None,
                    impact_score=50.0,
                    token_savings=int(self._estimate_tokens(prompt) * repetition_ratio * 0.5),
                )
            )

        # Suggest structure improvements for long prompts
        if len(prompt) > 500:
            has_structure = any(marker in prompt for marker in ["1.", "2.", "-", "*", "\n\n"])
            if not has_structure:
                improvements.append(
                    Improvement(
                        type=ImprovementType.STRUCTURE_IMPROVEMENT,
                        description="Add bullet points or numbered lists to improve clarity",
                        original_text=None,
                        improved_text=None,
                        impact_score=60.0,
                        token_savings=0,
                    )
                )

        # Sort by impact score
        improvements.sort(key=lambda x: x.impact_score, reverse=True)

        return improvements

    def apply_optimizations(self, prompt: str, improvements: List[Improvement]) -> str:
        """
        Apply selected improvements to a prompt.

        Args:
            prompt: Original prompt
            improvements: List of improvements to apply

        Returns:
            Optimized prompt text
        """
        self._transition_to(FSAState.APPLYING_OPTIMIZATIONS)

        optimized = prompt

        for improvement in improvements:
            if improvement.type == ImprovementType.TOKEN_REDUCTION:
                # Remove filler words
                if improvement.original_text:
                    pattern = rf"\b{re.escape(improvement.original_text)}\b"
                    optimized = re.sub(pattern, improvement.improved_text or "", optimized, flags=re.IGNORECASE)

                # Remove excessive politeness
                if "politeness" in improvement.description.lower():
                    # Keep only one politeness marker
                    optimized = re.sub(r"\bplease\b", "", optimized, count=len(re.findall(r"\bplease\b", optimized, re.IGNORECASE)) - 1, flags=re.IGNORECASE)
                    optimized = re.sub(r"\bkindly\b", "", optimized, flags=re.IGNORECASE)

            elif improvement.type == ImprovementType.CLARITY_ENHANCEMENT:
                # Replace vague language
                optimized = re.sub(r"\bcan you\b", "", optimized, flags=re.IGNORECASE)
                optimized = re.sub(r"\btry to\b", "", optimized, flags=re.IGNORECASE)
                optimized = re.sub(r"\b(might|maybe|perhaps)\b", "", optimized, flags=re.IGNORECASE)
                optimized = re.sub(r"\bI want you to\b", "", optimized, flags=re.IGNORECASE)

        # Clean up multiple spaces
        optimized = re.sub(r"\s+", " ", optimized)
        optimized = optimized.strip()

        return optimized

    def track_metrics(self, original: str, optimized: str, start_time: float, end_time: float) -> PromptMetrics:
        """
        Track and compare optimization metrics.

        Args:
            original: Original prompt text
            optimized: Optimized prompt text
            start_time: Optimization start time (timestamp in seconds)
            end_time: Optimization end time (timestamp in seconds)

        Returns:
            PromptMetrics with comparison data
        """
        original_tokens = self._estimate_tokens(original)
        optimized_tokens = self._estimate_tokens(optimized)
        token_reduction = original_tokens - optimized_tokens
        token_reduction_percentage = (token_reduction / original_tokens * 100) if original_tokens > 0 else 0.0

        # Calculate clarity improvement based on various factors
        original_analysis = self.analyze_tokens(original)
        optimized_analysis = self.analyze_tokens(optimized)
        clarity_improvement = optimized_analysis.efficiency_score - original_analysis.efficiency_score

        optimization_time_ms = (end_time - start_time) * 1000

        return PromptMetrics(
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            token_reduction=token_reduction,
            token_reduction_percentage=token_reduction_percentage,
            clarity_improvement=clarity_improvement,
            optimization_time_ms=optimization_time_ms,
        )

    def execute(self, prompt: str) -> OptimizedPrompt:
        """
        Execute the complete optimization pipeline.

        This is the main entry point that processes a prompt through all optimization stages:
        1. Validation
        2. Token analysis
        3. Improvement generation
        4. Optimization application
        5. Metrics tracking

        Args:
            prompt: The prompt to optimize

        Returns:
            OptimizedPrompt with optimization results

        Raises:
            ValueError: If the prompt fails validation
        """
        import time

        start_time = time.time()

        try:
            # Step 1: Validate
            validation_result = self.validate(prompt)
            if not validation_result.is_valid:
                self._transition_to(FSAState.ERROR)
                raise ValueError(f"Prompt validation failed: {', '.join(validation_result.issues)}")

            if validation_result.quality_score < self.min_quality_threshold:
                self._transition_to(FSAState.ERROR)
                raise ValueError(
                    f"Prompt quality score ({validation_result.quality_score:.1f}) below minimum threshold ({self.min_quality_threshold})"
                )

            # Step 2: Analyze tokens
            token_analysis = self.analyze_tokens(prompt)

            # Step 3: Generate improvements
            improvements = self.suggest_improvements(prompt)

            # Step 4: Apply optimizations
            optimized_text = self.apply_optimizations(prompt, improvements)

            # Step 5: Track metrics
            end_time = time.time()
            metrics = self.track_metrics(prompt, optimized_text, start_time, end_time)

            # Create result
            result = OptimizedPrompt(
                original_prompt=prompt,
                optimized_prompt=optimized_text,
                improvements_applied=improvements,
                metrics=metrics,
                validation_result=validation_result,
            )

            # Add to history
            self.optimization_history.add_optimization(result)

            # Transition to completed state
            self._transition_to(FSAState.COMPLETED)

            return result

        except Exception as e:
            self._transition_to(FSAState.ERROR)
            raise

    def error_handling(self, error: Exception, prompt: str) -> OptimizedPrompt:
        """
        Handle errors during optimization with graceful fallback.

        Args:
            error: The exception that occurred
            prompt: The original prompt

        Returns:
            OptimizedPrompt with error information and original prompt preserved
        """
        self._transition_to(FSAState.ERROR)

        # Create a safe fallback result
        fallback_result = OptimizedPrompt(
            original_prompt=prompt,
            optimized_prompt=prompt,  # Return original if optimization fails
            improvements_applied=[],
            metrics=PromptMetrics(
                original_tokens=self._estimate_tokens(prompt),
                optimized_tokens=self._estimate_tokens(prompt),
                token_reduction=0,
                token_reduction_percentage=0.0,
                clarity_improvement=0.0,
                optimization_time_ms=0.0,
            ),
            validation_result=ValidationResult(
                is_valid=False,
                issues=[f"Optimization error: {str(error)}"],
                warnings=[],
                quality_score=0.0,
            ),
        )

        return fallback_result

    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all optimizations performed.

        Returns:
            Dictionary with optimization statistics
        """
        return {
            "total_optimizations": self.optimization_history.total_optimizations,
            "total_tokens_saved": self.optimization_history.total_tokens_saved,
            "avg_improvement_score": self.optimization_history.avg_improvement_score,
            "current_state": self.state.value,
        }

    def clear_history(self) -> None:
        """Clear optimization history."""
        self.optimization_history = OptimizationHistory()
        self._reset_state()

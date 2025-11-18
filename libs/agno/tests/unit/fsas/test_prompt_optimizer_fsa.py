"""
Unit tests for the Prompt Optimizer FSA.

Tests cover basic optimization, token efficiency, clarity enhancements,
edge cases, error handling, and metrics tracking.
"""

import pytest
import time

from agno.fsas.prompt_optimizer_fsa import (
    PromptOptimizerFSA,
    OptimizedPrompt,
    ValidationResult,
    TokenAnalysis,
    Improvement,
    ImprovementType,
    PromptMetrics,
    FSAState,
)


@pytest.fixture
def optimizer():
    """Create a PromptOptimizerFSA instance for testing."""
    return PromptOptimizerFSA()


@pytest.fixture
def sample_prompt():
    """Sample prompt with optimization opportunities."""
    return "Can you please write a very detailed story about a robot? I really want you to make it very interesting and actually quite engaging."


def test_basic_prompt_optimization(optimizer, sample_prompt):
    """Test basic prompt optimization pipeline."""
    result = optimizer.execute(sample_prompt)

    assert isinstance(result, OptimizedPrompt)
    assert result.original_prompt == sample_prompt
    assert len(result.optimized_prompt) > 0
    assert result.optimized_prompt != sample_prompt  # Should be different after optimization
    assert isinstance(result.improvements_applied, list)
    assert isinstance(result.metrics, PromptMetrics)
    assert result.metrics.token_reduction >= 0
    assert optimizer.state == FSAState.COMPLETED


def test_token_efficiency_improvements(optimizer):
    """Test that token-inefficient prompts are optimized."""
    inefficient_prompt = "Please please can you just really very basically write a simple simple story? I really really want it."

    result = optimizer.execute(inefficient_prompt)

    # Should reduce tokens
    assert result.metrics.token_reduction > 0
    assert result.metrics.token_reduction_percentage > 0

    # Should have token reduction improvements
    token_improvements = [imp for imp in result.improvements_applied if imp.type == ImprovementType.TOKEN_REDUCTION]
    assert len(token_improvements) > 0

    # Should remove filler words
    filler_words = ["very", "really", "just", "basically"]
    optimized_lower = result.optimized_prompt.lower()
    for word in filler_words:
        # Count should be reduced in optimized version
        original_count = inefficient_prompt.lower().count(word)
        optimized_count = optimized_lower.count(word)
        assert optimized_count <= original_count


def test_clarity_enhancements(optimizer):
    """Test clarity enhancement suggestions."""
    vague_prompt = "Can you maybe try to possibly write something? Perhaps you could do that if you don't mind."

    result = optimizer.execute(vague_prompt)

    # Should have clarity improvements
    clarity_improvements = [
        imp for imp in result.improvements_applied if imp.type == ImprovementType.CLARITY_ENHANCEMENT
    ]
    assert len(clarity_improvements) > 0

    # Optimized prompt should be more direct
    assert "can you" not in result.optimized_prompt.lower()
    assert "maybe" not in result.optimized_prompt.lower()
    assert "perhaps" not in result.optimized_prompt.lower()


def test_validation_empty_prompt(optimizer):
    """Test validation of empty prompts."""
    with pytest.raises(ValueError, match="Prompt validation failed"):
        optimizer.execute("")

    with pytest.raises(ValueError, match="Prompt validation failed"):
        optimizer.execute("   ")  # Whitespace only

    assert optimizer.state == FSAState.ERROR


def test_validation_short_prompt(optimizer):
    """Test validation of very short prompts."""
    short_prompt = "Hi"  # Too short

    with pytest.raises(ValueError, match="Prompt validation failed"):
        optimizer.execute(short_prompt)

    assert optimizer.state == FSAState.ERROR


def test_very_long_prompt(optimizer):
    """Test handling of very long prompts."""
    long_prompt = "Write a story. " * 1000  # Create a very long prompt

    result = optimizer.execute(long_prompt)

    # Should still process successfully
    assert isinstance(result, OptimizedPrompt)
    assert result.validation_result.is_valid

    # Should have warnings about length
    assert len(result.validation_result.warnings) > 0
    assert any("long" in warning.lower() for warning in result.validation_result.warnings)

    # Should detect high repetition
    assert result.metrics.token_reduction > 0


def test_token_analysis(optimizer, sample_prompt):
    """Test detailed token analysis functionality."""
    analysis = optimizer.analyze_tokens(sample_prompt)

    assert isinstance(analysis, TokenAnalysis)
    assert analysis.token_count > 0
    assert analysis.word_count > 0
    assert analysis.avg_word_length > 0
    assert 0 <= analysis.efficiency_score <= 100
    assert analysis.redundant_tokens >= 0
    assert analysis.optimal_token_count <= analysis.token_count
    assert 0 <= analysis.repetition_ratio <= 1.0


def test_suggest_improvements(optimizer):
    """Test improvement suggestion generation."""
    prompt_with_issues = "Please can you very really just basically write a simple story? Maybe try to make it interesting."

    improvements = optimizer.suggest_improvements(prompt_with_issues)

    assert isinstance(improvements, list)
    assert len(improvements) > 0

    # Check that improvements have required fields
    for improvement in improvements:
        assert isinstance(improvement, Improvement)
        assert isinstance(improvement.type, ImprovementType)
        assert len(improvement.description) > 0
        assert 0 <= improvement.impact_score <= 100
        assert improvement.token_savings >= 0

    # Improvements should be sorted by impact score
    impact_scores = [imp.impact_score for imp in improvements]
    assert impact_scores == sorted(impact_scores, reverse=True)


def test_metrics_tracking(optimizer, sample_prompt):
    """Test that metrics are properly tracked."""
    result = optimizer.execute(sample_prompt)
    metrics = result.metrics

    # Validate all metrics are present and reasonable
    assert metrics.original_tokens > 0
    assert metrics.optimized_tokens > 0
    assert metrics.token_reduction >= 0
    assert metrics.token_reduction_percentage >= 0
    assert metrics.optimization_time_ms >= 0

    # Token reduction percentage should match calculation
    expected_percentage = (
        (metrics.token_reduction / metrics.original_tokens * 100) if metrics.original_tokens > 0 else 0
    )
    assert abs(metrics.token_reduction_percentage - expected_percentage) < 0.01


def test_error_handling(optimizer):
    """Test error handling for malformed prompts."""
    # Test with None (will raise AttributeError internally)
    try:
        result = optimizer.error_handling(ValueError("Test error"), "test prompt")
        assert isinstance(result, OptimizedPrompt)
        assert result.original_prompt == "test prompt"
        assert result.optimized_prompt == "test prompt"  # Should return original on error
        assert len(result.improvements_applied) == 0
        assert not result.validation_result.is_valid
        assert optimizer.state == FSAState.ERROR
    except Exception as e:
        pytest.fail(f"Error handling should not raise exceptions: {e}")


def test_optimization_history(optimizer):
    """Test that optimization history is properly tracked."""
    prompts = [
        "Can you please write a very detailed story?",
        "Maybe you could try to create something interesting.",
        "I really want you to actually generate a poem.",
    ]

    for prompt in prompts:
        optimizer.execute(prompt)

    stats = optimizer.get_optimization_stats()

    assert stats["total_optimizations"] == len(prompts)
    assert stats["total_tokens_saved"] >= 0
    assert 0 <= stats["avg_improvement_score"] <= 100
    assert stats["current_state"] == FSAState.COMPLETED.value

    # Check history
    assert len(optimizer.optimization_history.optimizations) == len(prompts)


def test_clear_history(optimizer, sample_prompt):
    """Test clearing optimization history."""
    # Perform some optimizations
    optimizer.execute(sample_prompt)
    optimizer.execute(sample_prompt)

    assert optimizer.optimization_history.total_optimizations == 2

    # Clear history
    optimizer.clear_history()

    assert optimizer.optimization_history.total_optimizations == 0
    assert len(optimizer.optimization_history.optimizations) == 0
    assert optimizer.state == FSAState.INITIAL


def test_apply_optimizations(optimizer):
    """Test applying specific optimizations."""
    prompt = "Can you please very really write a story?"

    improvements = [
        Improvement(
            type=ImprovementType.TOKEN_REDUCTION,
            description="Remove filler word 'very'",
            original_text="very",
            improved_text="",
            impact_score=25.0,
            token_savings=1,
        ),
        Improvement(
            type=ImprovementType.CLARITY_ENHANCEMENT,
            description="Remove vague language",
            original_text=None,
            improved_text=None,
            impact_score=40.0,
            token_savings=2,
        ),
    ]

    optimized = optimizer.apply_optimizations(prompt, improvements)

    # Should have removed filler words and vague language
    assert "very" not in optimized.lower()
    assert "can you" not in optimized.lower()
    assert len(optimized) < len(prompt)


def test_validation_result_quality_score(optimizer):
    """Test validation quality scoring."""
    good_prompt = "Write a detailed story about a robot exploring Mars. Include character development and plot twists."
    validation = optimizer.validate(good_prompt)

    assert validation.is_valid
    assert validation.quality_score > 70.0
    assert len(validation.issues) == 0

    # Test prompt with issues
    bad_prompt = "very really just basically x"
    validation_bad = optimizer.validate(bad_prompt)

    assert validation_bad.quality_score < validation.quality_score


def test_state_transitions(optimizer, sample_prompt):
    """Test that FSA state transitions occur correctly."""
    assert optimizer.state == FSAState.INITIAL

    # Execute optimization and check state progression
    result = optimizer.execute(sample_prompt)

    # Should end in COMPLETED state
    assert optimizer.state == FSAState.COMPLETED

    # Reset and check initial state
    optimizer._reset_state()
    assert optimizer.state == FSAState.INITIAL


def test_redundancy_detection(optimizer):
    """Test detection and removal of redundant content."""
    redundant_prompt = "Write a story story about a robot robot. Make it very very interesting and really really engaging."

    result = optimizer.execute(redundant_prompt)

    # Should detect redundancy
    analysis = optimizer.analyze_tokens(redundant_prompt)
    assert analysis.redundant_tokens > 0

    # Should suggest redundancy removal
    redundancy_improvements = [
        imp for imp in result.improvements_applied if imp.type == ImprovementType.REDUNDANCY_REMOVAL
    ]

    # Should reduce tokens
    assert result.metrics.token_reduction > 0


def test_repetition_ratio_calculation(optimizer):
    """Test calculation of repetition ratio."""
    # Prompt with high repetition
    repetitive_prompt = "Write a story. Write a story. Write a story. Write a story."
    ratio = optimizer._calculate_repetition_ratio(repetitive_prompt)

    assert 0.0 <= ratio <= 1.0
    assert ratio > 0.5  # Should detect high repetition

    # Prompt with low repetition
    unique_prompt = "Create an engaging narrative about space exploration and discovery."
    ratio_unique = optimizer._calculate_repetition_ratio(unique_prompt)

    assert ratio_unique < ratio


def test_min_quality_threshold(optimizer):
    """Test minimum quality threshold enforcement."""
    optimizer.min_quality_threshold = 80.0

    # This prompt has low quality
    low_quality_prompt = "x y z"

    with pytest.raises(ValueError, match="quality score.*below minimum threshold"):
        optimizer.execute(low_quality_prompt)


def test_structure_improvement_suggestion(optimizer):
    """Test suggestions for structure improvements in long prompts."""
    # Long prompt without structure
    long_unstructured = "Write a story about " + "robots and AI " * 100

    improvements = optimizer.suggest_improvements(long_unstructured)

    # Should suggest structure improvements
    structure_improvements = [
        imp for imp in improvements if imp.type == ImprovementType.STRUCTURE_IMPROVEMENT
    ]

    assert len(structure_improvements) > 0
    assert "bullet" in structure_improvements[0].description.lower() or "list" in structure_improvements[0].description.lower()

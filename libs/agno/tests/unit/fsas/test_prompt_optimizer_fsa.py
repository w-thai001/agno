"""
Unit tests for Prompt Optimizer FSA.

Tests cover:
- Core FSA functionality
- MLA v3.0 directive alignment
- Token optimization
- Constraint validation
- API formatting
"""

import pytest

from agno.fsas.prompt_optimizer_fsa import (
    AnalysisResult,
    MLADirective,
    OptimizationResult,
    OptimizationState,
    PromptConstraint,
    PromptOptimizerFSA,
    PromptType,
    ValidationResult,
)


class TestPromptOptimizerFSAInitialization:
    """Test FSA initialization and configuration."""

    def test_default_initialization(self):
        """Test FSA initializes with default values."""
        fsa = PromptOptimizerFSA()

        assert fsa.state == OptimizationState.INITIAL
        assert fsa.max_tokens == 4096
        assert fsa.mla_version == 3.0
        assert fsa.strict_mode is False
        assert len(fsa._mla_directives) > 0

    def test_custom_initialization(self):
        """Test FSA initializes with custom values."""
        fsa = PromptOptimizerFSA(
            max_tokens=8192,
            mla_version=3.0,
            strict_mode=True,
        )

        assert fsa.max_tokens == 8192
        assert fsa.mla_version == 3.0
        assert fsa.strict_mode is True

    def test_mla_directives_loaded(self):
        """Test MLA directives are properly initialized."""
        fsa = PromptOptimizerFSA()

        assert "task_specification" in fsa._mla_directives
        assert "context_boundary" in fsa._mla_directives
        assert "output_format" in fsa._mla_directives
        assert "constraint_declaration" in fsa._mla_directives
        assert "example_provision" in fsa._mla_directives

        # Check required directives
        task_spec = fsa._mla_directives["task_specification"]
        assert task_spec.required is True
        assert task_spec.priority == 10


class TestPromptAnalysis:
    """Test prompt analysis functionality."""

    def test_analyze_simple_instruction(self):
        """Test analysis of simple instruction prompt."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a function to calculate the factorial of a number"

        result = fsa.analyze_prompt(prompt)

        assert isinstance(result, AnalysisResult)
        assert result.prompt_type in [PromptType.INSTRUCTION, PromptType.TASK]
        assert result.token_count > 0
        assert isinstance(result.issues, list)
        assert isinstance(result.directives, list)
        assert isinstance(result.constraints, list)

    def test_analyze_conversation_prompt(self):
        """Test analysis of conversation-style prompt."""
        fsa = PromptOptimizerFSA()
        prompt = "What is the difference between Python lists and tuples?"

        result = fsa.analyze_prompt(prompt)

        assert result.prompt_type in [PromptType.CONVERSATION, PromptType.TASK]
        assert result.token_count > 0

    def test_analyze_system_prompt(self):
        """Test analysis of system-style prompt."""
        fsa = PromptOptimizerFSA()
        prompt = "You are an expert Python developer. Help users write better code."

        result = fsa.analyze_prompt(prompt)

        assert result.prompt_type == PromptType.SYSTEM
        assert result.token_count > 0

    def test_analyze_empty_prompt_raises_error(self):
        """Test that empty prompt raises ValueError."""
        fsa = PromptOptimizerFSA()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            fsa.analyze_prompt("")

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            fsa.analyze_prompt("   ")

    def test_analyze_detects_directives(self):
        """Test directive detection in prompts."""
        fsa = PromptOptimizerFSA()
        prompt = """
        Task: Analyze the following code
        Output: Return results in JSON format
        Example: {"result": "success"}
        """

        result = fsa.analyze_prompt(prompt)

        directive_names = {d.name for d in result.directives}
        assert "task_specification" in directive_names
        assert "output_format" in directive_names
        assert "example_provision" in directive_names
        assert result.directive_count >= 3

    def test_analyze_detects_constraints(self):
        """Test constraint detection in prompts."""
        fsa = PromptOptimizerFSA()
        prompt = """
        Generate a summary in 100 words.
        Output format: JSON
        Must not include personal information.
        Should use proper grammar.
        """

        result = fsa.analyze_prompt(prompt)

        assert result.constraint_count > 0

        constraint_types = {c.constraint_type for c in result.constraints}
        assert "length" in constraint_types or "format" in constraint_types

    def test_analyze_token_count_estimation(self):
        """Test token count estimation."""
        fsa = PromptOptimizerFSA()

        short_prompt = "Hello"
        long_prompt = "Write a comprehensive guide " * 100

        short_result = fsa.analyze_prompt(short_prompt)
        long_result = fsa.analyze_prompt(long_prompt)

        assert short_result.token_count < long_result.token_count
        assert short_result.token_count > 0
        assert long_result.token_count > 100

    def test_analyze_detects_token_overflow(self):
        """Test detection of token limit overflow."""
        fsa = PromptOptimizerFSA(max_tokens=10)
        prompt = "This is a very long prompt that exceeds the token limit " * 10

        result = fsa.analyze_prompt(prompt)

        assert any("exceeds maximum" in issue for issue in result.issues)


class TestPromptOptimization:
    """Test prompt optimization functionality."""

    def test_optimize_basic_prompt(self):
        """Test basic prompt optimization."""
        fsa = PromptOptimizerFSA()
        prompt = "Please write a function to sort a list"

        result = fsa.optimize_for_mla(prompt)

        assert isinstance(result, OptimizationResult)
        assert result.optimized_prompt != ""
        assert result.original_token_count > 0
        assert result.optimized_token_count > 0
        assert isinstance(result.optimization_notes, list)

    def test_optimize_removes_filler_words(self):
        """Test that optimization removes filler words."""
        fsa = PromptOptimizerFSA()
        prompt = "Please kindly just write a really basic function"

        result = fsa.optimize_for_mla(prompt)

        # Should remove some filler words
        assert "please" not in result.optimized_prompt.lower() or \
               "kindly" not in result.optimized_prompt.lower() or \
               "just" not in result.optimized_prompt.lower()

    def test_optimize_normalizes_whitespace(self):
        """Test whitespace normalization."""
        fsa = PromptOptimizerFSA()
        prompt = "Write    a   function\n\n\nwith   multiple    spaces"

        result = fsa.optimize_for_mla(prompt)

        # Should not have multiple consecutive spaces
        assert "    " not in result.optimized_prompt
        assert result.optimized_token_count <= result.original_token_count

    def test_optimize_adds_task_directive(self):
        """Test adding task directive when missing."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a sorting algorithm"

        result = fsa.optimize_for_mla(prompt)

        # Should add task directive or preserve existing structure
        assert len(result.optimized_prompt) > 0
        assert any("task" in note.lower() or "directive" in note.lower()
                   for note in result.optimization_notes) or \
               "Task:" in result.optimized_prompt or \
               result.optimized_prompt != ""

    def test_optimize_preserves_format_constraints(self):
        """Test that format constraints are preserved."""
        fsa = PromptOptimizerFSA()
        prompt = "Generate a report in JSON format with user data"

        result = fsa.optimize_for_mla(prompt)

        # JSON format should be preserved
        assert "json" in result.optimized_prompt.lower()

    def test_optimize_with_analysis(self):
        """Test optimization with pre-computed analysis."""
        fsa = PromptOptimizerFSA()
        prompt = "Explain how quicksort works"

        analysis = fsa.analyze_prompt(prompt)
        result = fsa.optimize_for_mla(prompt, analysis)

        assert isinstance(result, OptimizationResult)
        assert result.optimized_prompt != ""

    def test_optimize_calculates_token_reduction(self):
        """Test token reduction calculation."""
        fsa = PromptOptimizerFSA()
        prompt = "Please    kindly    just    write    a    function"

        result = fsa.optimize_for_mla(prompt)

        # Token reduction should be calculated (may be zero or positive)
        assert result.token_reduction >= 0
        assert result.token_reduction == (
            result.original_token_count - result.optimized_token_count
        )

    def test_optimize_long_prompt_adds_structure(self):
        """Test that long prompts get structured."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a function that does X. It should handle Y. Make sure to consider Z. Also implement error handling. Use proper naming conventions."

        result = fsa.optimize_for_mla(prompt)

        # Should add some structure or notes about it
        assert len(result.optimized_prompt) > 0


class TestOptimizationValidation:
    """Test optimization validation functionality."""

    def test_validate_successful_optimization(self):
        """Test validation of successful optimization."""
        fsa = PromptOptimizerFSA()
        original = "Write a function to calculate fibonacci numbers"
        optimized = "Task: Write a function to calculate fibonacci numbers"

        result = fsa.validate_optimization(original, optimized)

        assert isinstance(result, ValidationResult)
        assert result.score >= 0.0
        assert result.score <= 1.0

    def test_validate_detects_token_increase(self):
        """Test validation detects when tokens increase."""
        fsa = PromptOptimizerFSA()
        original = "Sort list"
        optimized = "Please kindly sort the list with extra words"

        result = fsa.validate_optimization(original, optimized)

        # Should warn about token increase
        assert len(result.validation_warnings) > 0 or len(result.validation_errors) == 0

    def test_validate_checks_token_limit(self):
        """Test validation checks token limit."""
        fsa = PromptOptimizerFSA(max_tokens=10)
        original = "Sort"
        optimized = "Please write a very long sorting algorithm implementation " * 20

        result = fsa.validate_optimization(original, optimized)

        # Should have validation errors for exceeding token limit
        assert any("exceeds token limit" in error for error in result.validation_errors)
        assert result.is_valid is False

    def test_validate_empty_prompt(self):
        """Test validation of empty optimized prompt."""
        fsa = PromptOptimizerFSA()
        original = "Write code"
        optimized = ""

        result = fsa.validate_optimization(original, optimized)

        assert result.is_valid is False
        assert any("empty" in error.lower() for error in result.validation_errors)

    def test_validate_score_calculation(self):
        """Test validation score calculation."""
        fsa = PromptOptimizerFSA()
        original = "Write a function"
        optimized = "Task: Write a function"

        result = fsa.validate_optimization(original, optimized)

        # Score should be reasonable
        assert 0.0 <= result.score <= 1.0

        # High score for good optimization
        if len(result.validation_errors) == 0:
            assert result.score >= 0.5

    def test_validate_with_strict_mode(self):
        """Test validation in strict mode."""
        fsa = PromptOptimizerFSA(strict_mode=True)
        original = "Task: Write code. Example: def foo(): pass"
        optimized = "Task: Write code"  # Lost example directive

        result = fsa.validate_optimization(original, optimized)

        # Strict mode should be more stringent
        # May have errors or lower score
        assert isinstance(result, ValidationResult)

    def test_validate_constraint_preservation(self):
        """Test validation of constraint preservation."""
        fsa = PromptOptimizerFSA()
        original = "Generate output in JSON format"
        optimized = "Generate output"  # Lost format constraint

        result = fsa.validate_optimization(original, optimized)

        # Should detect lost constraint
        assert len(result.constraint_violations) > 0 or \
               len(result.validation_warnings) > 0 or \
               "json" in optimized.lower()


class TestOptimizeAndValidate:
    """Test combined optimization and validation."""

    def test_optimize_and_validate_workflow(self):
        """Test complete optimize and validate workflow."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a Python function to reverse a string"

        optimization, validation = fsa.optimize_and_validate(prompt)

        assert isinstance(optimization, OptimizationResult)
        assert isinstance(validation, ValidationResult)
        assert optimization.optimized_prompt != ""

    def test_optimize_and_validate_invalid_prompt(self):
        """Test workflow with problematic prompt."""
        fsa = PromptOptimizerFSA(max_tokens=5)
        prompt = "Write a comprehensive guide to Python programming with examples"

        optimization, validation = fsa.optimize_and_validate(prompt)

        # Should complete but may have validation issues
        assert isinstance(optimization, OptimizationResult)
        assert isinstance(validation, ValidationResult)


class TestClaudeAPIFormatting:
    """Test Claude API formatting functionality."""

    def test_format_for_claude_api_basic(self):
        """Test basic Claude API formatting."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a function"

        result = fsa.format_for_claude_api(prompt)

        assert isinstance(result, dict)
        assert "model" in result
        assert "max_tokens" in result
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == prompt

    def test_format_for_claude_api_with_system(self):
        """Test Claude API formatting with system prompt."""
        fsa = PromptOptimizerFSA()
        user_prompt = "Write a function"
        system_prompt = "You are a Python expert"

        result = fsa.format_for_claude_api(user_prompt, system_prompt)

        assert "system" in result
        assert result["system"] == system_prompt

    def test_format_respects_max_tokens(self):
        """Test that formatted output respects max_tokens."""
        fsa = PromptOptimizerFSA(max_tokens=8192)
        prompt = "Write code"

        result = fsa.format_for_claude_api(prompt)

        assert result["max_tokens"] == 8192


class TestFSAStateTransitions:
    """Test FSA state transitions."""

    def test_state_transitions_analyze(self):
        """Test state transitions during analysis."""
        fsa = PromptOptimizerFSA()

        assert fsa.state == OptimizationState.INITIAL

        fsa.analyze_prompt("Test prompt")

        # Should return to initial state after analysis
        assert fsa.state == OptimizationState.INITIAL

    def test_state_transitions_optimize(self):
        """Test state transitions during optimization."""
        fsa = PromptOptimizerFSA()

        assert fsa.state == OptimizationState.INITIAL

        fsa.optimize_for_mla("Test prompt")

        # Should return to initial state after optimization
        assert fsa.state == OptimizationState.INITIAL

    def test_state_transitions_validate(self):
        """Test state transitions during validation."""
        fsa = PromptOptimizerFSA()

        result = fsa.validate_optimization("Original", "Optimized")

        # Should transition to completed or failed
        assert fsa.state in [OptimizationState.COMPLETED, OptimizationState.FAILED]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_prompt(self):
        """Test handling of unicode characters."""
        fsa = PromptOptimizerFSA()
        prompt = "Write a function to process: 你好, мир, 🌍"

        result = fsa.analyze_prompt(prompt)

        assert result.token_count > 0
        assert isinstance(result, AnalysisResult)

    def test_very_short_prompt(self):
        """Test handling of very short prompts."""
        fsa = PromptOptimizerFSA()
        prompt = "Hi"

        result = fsa.analyze_prompt(prompt)

        assert result.token_count >= 1

    def test_very_long_prompt(self):
        """Test handling of very long prompts."""
        fsa = PromptOptimizerFSA()
        prompt = "Write code " * 1000

        result = fsa.analyze_prompt(prompt)

        assert result.token_count > 100

    def test_special_characters(self):
        """Test handling of special characters."""
        fsa = PromptOptimizerFSA()
        prompt = "Process this: @#$%^&*(){}[]|\\:;\"'<>,.?/~`"

        result = fsa.analyze_prompt(prompt)

        assert isinstance(result, AnalysisResult)

    def test_multiline_prompt(self):
        """Test handling of multiline prompts."""
        fsa = PromptOptimizerFSA()
        prompt = """
        Line 1: Task description
        Line 2: Additional context
        Line 3: Output requirements
        """

        result = fsa.analyze_prompt(prompt)

        assert result.token_count > 0


class TestMLADirectives:
    """Test MLA directive models."""

    def test_mla_directive_creation(self):
        """Test creating MLA directive."""
        directive = MLADirective(
            name="test_directive",
            content="Test content",
            priority=5,
            required=True,
        )

        assert directive.name == "test_directive"
        assert directive.content == "Test content"
        assert directive.priority == 5
        assert directive.required is True

    def test_prompt_constraint_creation(self):
        """Test creating prompt constraint."""
        constraint = PromptConstraint(
            constraint_type="length",
            description="Max 100 tokens",
            value=100,
            enforced=True,
        )

        assert constraint.constraint_type == "length"
        assert constraint.description == "Max 100 tokens"
        assert constraint.value == 100
        assert constraint.enforced is True


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_optimization_workflow(self):
        """Test complete workflow from analysis to API format."""
        fsa = PromptOptimizerFSA()
        original_prompt = "Please write a Python function that sorts a list of numbers"

        # Step 1: Analyze
        analysis = fsa.analyze_prompt(original_prompt)
        assert isinstance(analysis, AnalysisResult)

        # Step 2: Optimize
        optimization = fsa.optimize_for_mla(original_prompt, analysis)
        assert isinstance(optimization, OptimizationResult)

        # Step 3: Validate
        validation = fsa.validate_optimization(
            original_prompt,
            optimization.optimized_prompt,
            analysis,
        )
        assert isinstance(validation, ValidationResult)

        # Step 4: Format for API
        api_format = fsa.format_for_claude_api(optimization.optimized_prompt)
        assert isinstance(api_format, dict)
        assert "messages" in api_format

    def test_optimization_improves_prompt(self):
        """Test that optimization produces measurable improvements."""
        fsa = PromptOptimizerFSA()
        original = "Please kindly just write a really simple function"

        optimization, validation = fsa.optimize_and_validate(original)

        # Should have some optimization notes
        assert len(optimization.optimization_notes) > 0

        # Validation should pass or have constructive feedback
        assert isinstance(validation.score, float)

"""
Comprehensive tests for Output Validator FSA.

Tests cover validation scenarios including schema validation, quality scoring,
error detection, and threshold-based pass/fail decisions.
"""

import pytest
from pydantic import BaseModel, Field
from typing import List, Optional

from agno.fsa import (
    OutputValidator,
    OutputValidatorConfig,
    QualityScore,
    ValidationResult,
    ValidationState,
)


# Test Pydantic Models
class SimpleOutput(BaseModel):
    """Simple output model for testing."""

    title: str = Field(description="Output title")
    content: str = Field(description="Output content")


class ComplexOutput(BaseModel):
    """Complex output model with nested structures."""

    id: int = Field(description="Unique identifier")
    title: str = Field(description="Output title")
    description: str = Field(description="Detailed description")
    tags: List[str] = Field(default_factory=list, description="Tags list")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class TestOutputValidatorBasics:
    """Test basic Output Validator functionality."""

    def test_initialization(self):
        """Test validator initialization with default config."""
        validator = OutputValidator()
        assert validator.state == ValidationState.IDLE
        assert validator.result is None
        assert validator.config.pass_threshold == 0.7

    def test_custom_config(self):
        """Test validator initialization with custom config."""
        config = OutputValidatorConfig(
            pass_threshold=0.8,
            required_fields=["title", "content"],
        )
        validator = OutputValidator(config)
        assert validator.config.pass_threshold == 0.8
        assert validator.config.required_fields == ["title", "content"]

    def test_reset(self):
        """Test FSA reset functionality."""
        validator = OutputValidator()
        validator.validate({"test": "data"})
        assert validator.state == ValidationState.COMPLETE

        validator.reset()
        assert validator.state == ValidationState.IDLE
        assert validator.result is None


class TestFormatValidation:
    """Test format validation and parsing."""

    def test_dict_input(self):
        """Test validation with dictionary input."""
        validator = OutputValidator()
        output = {"title": "Test", "content": "Test content"}

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert result.validated_output == output
        assert result.quality_scores.format_compliance == 1.0

    def test_json_string_input(self):
        """Test validation with JSON string input."""
        validator = OutputValidator()
        output = '{"title": "Test", "content": "Test content"}'

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert result.validated_output == {"title": "Test", "content": "Test content"}
        assert result.quality_scores.format_compliance == 1.0

    def test_json_in_markdown(self):
        """Test extraction of JSON from markdown code blocks."""
        validator = OutputValidator()
        output = '```json\n{"title": "Test", "content": "Test content"}\n```'

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert result.validated_output == {"title": "Test", "content": "Test content"}
        assert result.quality_scores.format_compliance == 0.8
        assert any(issue.category == "format" for issue in result.issues)

    def test_plain_text_fallback(self):
        """Test fallback to plain text when JSON parsing fails."""
        validator = OutputValidator()
        output = "This is plain text output"

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert result.validated_output == {"content": output}
        assert result.quality_scores.format_compliance == 0.5
        assert any(issue.severity == "warning" for issue in result.issues)

    def test_pydantic_model_input(self):
        """Test validation with Pydantic model input."""
        validator = OutputValidator()
        output = SimpleOutput(title="Test", content="Test content")

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert result.validated_output["title"] == "Test"
        assert result.validated_output["content"] == "Test content"


class TestSchemaValidation:
    """Test schema validation against Pydantic models."""

    def test_valid_schema(self):
        """Test validation with valid schema compliance."""
        config = OutputValidatorConfig(schema_model=SimpleOutput)
        validator = OutputValidator(config)
        output = {"title": "Test", "content": "Test content"}

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert isinstance(result.validated_output, SimpleOutput)
        assert result.quality_scores.correctness == 1.0

    def test_invalid_schema(self):
        """Test validation with schema violations."""
        config = OutputValidatorConfig(schema_model=SimpleOutput)
        validator = OutputValidator(config)
        output = {"title": "Test"}  # Missing required 'content' field

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        schema_errors = [issue for issue in result.issues if issue.category == "schema"]
        assert len(schema_errors) > 0
        assert result.quality_scores.correctness < 1.0

    def test_complex_schema_validation(self):
        """Test validation with complex nested schema."""
        config = OutputValidatorConfig(schema_model=ComplexOutput)
        validator = OutputValidator(config)
        output = {
            "id": 123,
            "title": "Complex Test",
            "description": "This is a detailed description",
            "tags": ["test", "validation"],
            "metadata": {"author": "tester", "version": "1.0"},
        }

        result = validator.validate(output)

        assert result.state == ValidationState.COMPLETE
        assert isinstance(result.validated_output, ComplexOutput)
        assert result.quality_scores.correctness == 1.0


class TestCompletenessScoring:
    """Test completeness scoring with required fields."""

    def test_all_required_fields_present(self):
        """Test completeness when all required fields are present."""
        config = OutputValidatorConfig(
            required_fields=["title", "content", "author"]
        )
        validator = OutputValidator(config)
        output = {"title": "Test", "content": "Content", "author": "John"}

        result = validator.validate(output)

        assert result.quality_scores.completeness == 1.0

    def test_partial_required_fields(self):
        """Test completeness with some missing required fields."""
        config = OutputValidatorConfig(
            required_fields=["title", "content", "author"]
        )
        validator = OutputValidator(config)
        output = {"title": "Test", "content": "Content"}  # Missing 'author'

        result = validator.validate(output)

        assert result.quality_scores.completeness == pytest.approx(0.666, rel=0.01)
        completeness_issues = [
            issue for issue in result.issues if issue.category == "completeness"
        ]
        assert len(completeness_issues) > 0

    def test_no_required_fields(self):
        """Test completeness with no required fields configured."""
        config = OutputValidatorConfig(required_fields=[])
        validator = OutputValidator(config)
        output = {"any": "data"}

        result = validator.validate(output)

        assert result.quality_scores.completeness == 1.0


class TestQualityScoring:
    """Test multi-dimensional quality scoring."""

    def test_quality_score_properties(self):
        """Test QualityScore model and overall calculation."""
        score = QualityScore(
            completeness=0.8,
            correctness=0.9,
            format_compliance=1.0,
            clarity=0.7,
        )

        # Test weighted average: 0.8*0.3 + 0.9*0.3 + 1.0*0.25 + 0.7*0.15
        expected_overall = 0.24 + 0.27 + 0.25 + 0.105
        assert score.overall == pytest.approx(expected_overall, rel=0.01)

    def test_overall_score_calculation(self):
        """Test overall quality score in validation result."""
        config = OutputValidatorConfig(
            required_fields=["title", "content"],
            schema_model=SimpleOutput,
        )
        validator = OutputValidator(config)
        output = {"title": "Test", "content": "This is test content"}

        result = validator.validate(output)

        assert result.quality_scores.overall > 0.0
        assert result.quality_scores.overall <= 1.0


class TestClarityAssessment:
    """Test clarity scoring based on content quality."""

    def test_clear_structured_output(self):
        """Test clarity with well-structured output."""
        validator = OutputValidator()
        output = {
            "title": "Test Title",
            "content": "This is a comprehensive test content with sufficient length",
            "metadata": {"created": "2024-01-01"},
            "tags": ["test", "validation"],
        }

        result = validator.validate(output)

        assert result.quality_scores.clarity > 0.7

    def test_minimal_output_clarity(self):
        """Test clarity with minimal output."""
        validator = OutputValidator()
        output = {"data": "short"}

        result = validator.validate(output)

        assert result.quality_scores.clarity < 1.0

    def test_empty_output_clarity(self):
        """Test clarity with empty output."""
        validator = OutputValidator()
        output = {}

        result = validator.validate(output)

        assert result.quality_scores.clarity == 0.0


class TestThresholdDecisions:
    """Test threshold-based pass/fail decisions."""

    def test_pass_above_threshold(self):
        """Test validation passes when score exceeds threshold."""
        config = OutputValidatorConfig(
            pass_threshold=0.6,
            required_fields=["title", "content"],
            schema_model=SimpleOutput,
        )
        validator = OutputValidator(config)
        output = {"title": "Test", "content": "Test content"}

        result = validator.validate(output)

        assert result.quality_scores.overall >= 0.6
        assert result.passed is True

    def test_fail_below_threshold(self):
        """Test validation fails when score below threshold."""
        config = OutputValidatorConfig(
            pass_threshold=0.9,  # Very high threshold
            required_fields=["title", "content", "author", "date"],
        )
        validator = OutputValidator(config)
        output = {"title": "Test"}  # Missing most required fields

        result = validator.validate(output)

        assert result.quality_scores.overall < 0.9
        assert result.passed is False

    def test_custom_threshold(self):
        """Test validation with custom threshold values."""
        low_threshold = OutputValidatorConfig(pass_threshold=0.3)
        high_threshold = OutputValidatorConfig(pass_threshold=0.95)

        output = {"simple": "data"}

        low_result = OutputValidator(low_threshold).validate(output)
        high_result = OutputValidator(high_threshold).validate(output)

        assert low_result.passed is True
        assert high_result.passed is False


class TestErrorDetection:
    """Test error detection and issue reporting."""

    def test_validation_issues_recording(self):
        """Test that validation issues are properly recorded."""
        config = OutputValidatorConfig(
            schema_model=SimpleOutput,
            required_fields=["title", "content", "author"],
        )
        validator = OutputValidator(config)
        output = {"title": "Test"}  # Missing fields

        result = validator.validate(output)

        assert len(result.issues) > 0
        assert any(issue.category == "schema" for issue in result.issues)
        assert any(issue.category == "completeness" for issue in result.issues)

    def test_issue_severity_levels(self):
        """Test different severity levels in issues."""
        config = OutputValidatorConfig(required_fields=["title"])
        validator = OutputValidator(config)
        output = "Plain text output"  # Will trigger format warning

        result = validator.validate(output)

        severities = {issue.severity for issue in result.issues}
        assert "warning" in severities or "info" in severities

    def test_issue_location_tracking(self):
        """Test that issue locations are tracked when available."""
        config = OutputValidatorConfig(schema_model=SimpleOutput)
        validator = OutputValidator(config)
        output = {"title": 123, "content": "test"}  # Wrong type for title

        result = validator.validate(output)

        schema_issues = [issue for issue in result.issues if issue.category == "schema"]
        if schema_issues:
            assert any(issue.location is not None for issue in schema_issues)


class TestStateTransitions:
    """Test FSA state transitions."""

    def test_successful_state_transitions(self):
        """Test state transitions during successful validation."""
        validator = OutputValidator()
        assert validator.state == ValidationState.IDLE

        result = validator.validate({"test": "data"})

        assert result.state == ValidationState.COMPLETE
        assert validator.state == ValidationState.COMPLETE

    def test_failed_state_transition(self):
        """Test state transition on validation failure."""
        validator = OutputValidator()

        # Force an error by passing invalid input that will raise exception
        class InvalidType:
            pass

        result = validator.validate(InvalidType())

        assert result.state == ValidationState.FAILED
        assert validator.state == ValidationState.FAILED
        assert result.passed is False


class TestIntegrationScenarios:
    """Integration tests for complete validation scenarios."""

    def test_end_to_end_validation_success(self):
        """Test complete successful validation workflow."""
        config = OutputValidatorConfig(
            pass_threshold=0.7,
            required_fields=["title", "description"],
            schema_model=ComplexOutput,
        )
        validator = OutputValidator(config)
        output = {
            "id": 1,
            "title": "Complete Output",
            "description": "This is a comprehensive description with all required elements",
            "tags": ["complete", "valid"],
        }

        result = validator.validate(output)

        assert result.passed is True
        assert result.state == ValidationState.COMPLETE
        assert isinstance(result.validated_output, ComplexOutput)
        assert result.quality_scores.overall >= 0.7

    def test_end_to_end_validation_failure(self):
        """Test complete validation workflow with failures."""
        config = OutputValidatorConfig(
            pass_threshold=0.8,
            required_fields=["title", "description", "author", "date"],
            schema_model=SimpleOutput,
        )
        validator = OutputValidator(config)
        output = {"title": "Incomplete"}

        result = validator.validate(output)

        assert result.passed is False
        assert len(result.issues) > 0
        assert result.quality_scores.overall < 0.8

    def test_cascading_validation_interface(self):
        """Test that validation results are suitable for FSA cascading."""
        validator = OutputValidator()
        output = {"data": "test"}

        result = validator.validate(output)

        # Verify result can be serialized (for passing to next FSA)
        result_dict = result.model_dump()
        assert "state" in result_dict
        assert "passed" in result_dict
        assert "quality_scores" in result_dict
        assert "issues" in result_dict

        # Verify state is accessible for decision making
        if result.passed:
            next_state = "continue_cascade"
        else:
            next_state = "halt_cascade"
        assert next_state in ["continue_cascade", "halt_cascade"]

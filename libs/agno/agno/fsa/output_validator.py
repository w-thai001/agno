"""
Output Validator FSA - Validates deliverable quality using finite state machine.

This module implements a comprehensive validation system with multi-dimensional
quality scoring, schema validation, and error detection capabilities.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ConfigDict, Field, ValidationError
import json
import re


class ValidationState(str, Enum):
    """States of the Output Validator FSA."""

    IDLE = "idle"
    VALIDATING = "validating"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


class QualityScore(BaseModel):
    """Multi-dimensional quality scoring for output validation."""

    completeness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score for output completeness (0-1)",
    )
    correctness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score for output correctness (0-1)",
    )
    format_compliance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score for format/schema compliance (0-1)",
    )
    clarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score for output clarity and structure (0-1)",
    )

    @property
    def overall(self) -> float:
        """Calculate overall quality score as weighted average."""
        return (
            self.completeness * 0.3 +
            self.correctness * 0.3 +
            self.format_compliance * 0.25 +
            self.clarity * 0.15
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert scores to dictionary including overall score."""
        return {
            "completeness": self.completeness,
            "correctness": self.correctness,
            "format_compliance": self.format_compliance,
            "clarity": self.clarity,
            "overall": self.overall,
        }


class ValidationIssue(BaseModel):
    """Represents a quality or validation issue detected in output."""

    severity: str = Field(description="Issue severity: error, warning, info")
    category: str = Field(description="Issue category: schema, format, content, etc.")
    message: str = Field(description="Human-readable issue description")
    location: Optional[str] = Field(default=None, description="Location of issue in output")


class ValidationResult(BaseModel):
    """Complete validation result with scores, issues, and pass/fail status."""

    state: ValidationState = Field(description="Current FSA state")
    passed: bool = Field(description="Whether validation passed threshold")
    quality_scores: QualityScore = Field(description="Multi-dimensional quality scores")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Detected issues")
    validated_output: Optional[Any] = Field(default=None, description="Validated/parsed output")
    raw_output: Optional[str] = Field(default=None, description="Original raw output")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def add_issue(self, severity: str, category: str, message: str, location: Optional[str] = None) -> None:
        """Add a validation issue to the result."""
        self.issues.append(
            ValidationIssue(
                severity=severity,
                category=category,
                message=message,
                location=location,
            )
        )


class OutputValidatorConfig(BaseModel):
    """Configuration for Output Validator FSA."""

    pass_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum overall quality score to pass (0-1)",
    )
    required_fields: List[str] = Field(
        default_factory=list,
        description="Required fields for completeness check",
    )
    schema_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model for schema validation",
    )
    enable_format_validation: bool = Field(
        default=True,
        description="Enable JSON/format validation",
    )
    enable_content_validation: bool = Field(
        default=True,
        description="Enable content quality validation",
    )
    min_clarity_length: int = Field(
        default=10,
        description="Minimum length for clarity assessment",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutputValidator:
    """
    Finite State Automaton for validating output deliverables.

    Implements multi-dimensional quality scoring, schema validation,
    error detection, and threshold-based pass/fail decisions.
    """

    def __init__(self, config: Optional[OutputValidatorConfig] = None):
        """
        Initialize the Output Validator FSA.

        Args:
            config: Configuration object for the validator
        """
        self.config = config or OutputValidatorConfig()
        self.state = ValidationState.IDLE
        self.result: Optional[ValidationResult] = None

    def validate(self, output: Union[str, Dict, BaseModel]) -> ValidationResult:
        """
        Main validation entry point. Runs complete validation pipeline.

        Args:
            output: Output to validate (string, dict, or Pydantic model)

        Returns:
            ValidationResult with scores, issues, and pass/fail status
        """
        # Transition to VALIDATING state
        self.state = ValidationState.VALIDATING

        # Initialize result
        self.result = ValidationResult(
            state=self.state,
            passed=False,
            quality_scores=QualityScore(),
            raw_output=str(output) if not isinstance(output, BaseModel) else None,
        )

        try:
            # Parse and validate format
            parsed_output = self._validate_format(output)

            # Validate against schema if provided
            if self.config.schema_model:
                parsed_output = self._validate_schema(parsed_output)

            self.result.validated_output = parsed_output

            # Transition to SCORING state
            self.state = ValidationState.SCORING
            self.result.state = self.state

            # Calculate quality scores
            self._calculate_quality_scores(parsed_output)

            # Determine pass/fail based on threshold
            overall_score = self.result.quality_scores.overall
            self.result.passed = overall_score >= self.config.pass_threshold

            # Transition to COMPLETE state
            self.state = ValidationState.COMPLETE
            self.result.state = self.state

        except Exception as e:
            # Transition to FAILED state on error
            self.state = ValidationState.FAILED
            self.result.state = self.state
            self.result.passed = False
            self.result.add_issue(
                severity="error",
                category="validation",
                message=f"Validation failed: {str(e)}",
            )

        return self.result

    def _validate_format(self, output: Union[str, Dict, BaseModel]) -> Dict[str, Any]:
        """
        Validate and parse output format.

        Args:
            output: Raw output to parse

        Returns:
            Parsed output as dictionary

        Raises:
            ValueError: If format is invalid
        """
        if not self.config.enable_format_validation:
            return output if isinstance(output, dict) else {"content": str(output)}

        # Handle Pydantic models
        if isinstance(output, BaseModel):
            return output.model_dump()

        # Handle dictionaries
        if isinstance(output, dict):
            self.result.quality_scores.format_compliance = 1.0
            return output

        # Handle string input - try to parse as JSON
        if isinstance(output, str):
            try:
                # Try direct JSON parse
                parsed = json.loads(output)
                self.result.quality_scores.format_compliance = 1.0
                return parsed
            except json.JSONDecodeError:
                # Try extracting JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                        self.result.quality_scores.format_compliance = 0.8
                        self.result.add_issue(
                            severity="info",
                            category="format",
                            message="JSON extracted from markdown code block",
                        )
                        return parsed
                    except json.JSONDecodeError:
                        pass

                # Fallback: treat as plain text
                self.result.quality_scores.format_compliance = 0.5
                self.result.add_issue(
                    severity="warning",
                    category="format",
                    message="Output is not valid JSON, treating as plain text",
                )
                return {"content": output}

        raise ValueError(f"Unsupported output type: {type(output)}")

    def _validate_schema(self, parsed_output: Dict[str, Any]) -> Union[Dict[str, Any], BaseModel]:
        """
        Validate output against Pydantic schema model.

        Args:
            parsed_output: Parsed output dictionary

        Returns:
            Validated Pydantic model instance or original dict
        """
        if not self.config.schema_model:
            return parsed_output

        try:
            validated = self.config.schema_model(**parsed_output)
            # Schema validation passed
            return validated
        except ValidationError as e:
            # Schema validation failed - record errors
            for error in e.errors():
                self.result.add_issue(
                    severity="error",
                    category="schema",
                    message=f"{error['loc']}: {error['msg']}",
                    location=".".join(str(loc) for loc in error['loc']),
                )
            # Return original dict but mark as failed
            return parsed_output

    def _calculate_quality_scores(self, parsed_output: Union[Dict, BaseModel]) -> None:
        """
        Calculate multi-dimensional quality scores.

        Args:
            parsed_output: Validated output to score
        """
        output_dict = parsed_output.model_dump() if isinstance(parsed_output, BaseModel) else parsed_output

        # Calculate completeness score
        if self.config.required_fields:
            present_fields = sum(1 for field in self.config.required_fields if field in output_dict)
            self.result.quality_scores.completeness = present_fields / len(self.config.required_fields)

            # Add issues for missing fields
            missing_fields = [f for f in self.config.required_fields if f not in output_dict]
            if missing_fields:
                self.result.add_issue(
                    severity="warning",
                    category="completeness",
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                )
        else:
            # No required fields specified - score based on content presence
            self.result.quality_scores.completeness = 1.0 if output_dict else 0.0

        # Calculate correctness score based on schema validation
        if self.config.schema_model:
            # Count schema errors
            schema_errors = [issue for issue in self.result.issues if issue.category == "schema"]
            if schema_errors:
                # Penalize based on number of schema errors
                self.result.quality_scores.correctness = max(0.0, 1.0 - len(schema_errors) * 0.2)
            else:
                self.result.quality_scores.correctness = 1.0
        else:
            # No schema - assume correct if parseable
            self.result.quality_scores.correctness = 0.8

        # Calculate clarity score based on structure and content
        if self.config.enable_content_validation:
            clarity_score = self._assess_clarity(output_dict)
            self.result.quality_scores.clarity = clarity_score
        else:
            self.result.quality_scores.clarity = 1.0

    def _assess_clarity(self, output_dict: Dict[str, Any]) -> float:
        """
        Assess output clarity based on structure and content quality.

        Args:
            output_dict: Output dictionary to assess

        Returns:
            Clarity score (0-1)
        """
        score = 0.0

        # Check for non-empty content
        if not output_dict:
            return 0.0

        # Award points for having multiple fields (structure)
        num_fields = len(output_dict)
        score += min(0.3, num_fields * 0.1)

        # Award points for content length and quality
        total_content_length = 0
        for value in output_dict.values():
            if isinstance(value, str):
                total_content_length += len(value)
            elif isinstance(value, (list, dict)):
                total_content_length += len(str(value))

        if total_content_length >= self.config.min_clarity_length:
            score += 0.4
        else:
            score += 0.2
            self.result.add_issue(
                severity="info",
                category="clarity",
                message=f"Content length ({total_content_length}) below recommended minimum",
            )

        # Award points for proper nesting (indicates structure)
        has_nested = any(isinstance(v, (dict, list)) for v in output_dict.values())
        if has_nested:
            score += 0.3

        return min(1.0, score)

    def reset(self) -> None:
        """Reset the FSA to initial IDLE state."""
        self.state = ValidationState.IDLE
        self.result = None

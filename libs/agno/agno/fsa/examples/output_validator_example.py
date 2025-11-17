"""
Example usage of the Output Validator FSA.

This example demonstrates various validation scenarios including:
- Basic JSON validation
- Schema validation with Pydantic models
- Multi-dimensional quality scoring
- Threshold-based pass/fail decisions
- Error detection and reporting
"""

from pydantic import BaseModel, Field
from typing import List
from agno.fsa import OutputValidator, OutputValidatorConfig, ValidationState


# Define a schema model for structured output
class BlogPost(BaseModel):
    """Schema for a blog post."""

    title: str = Field(description="Post title")
    content: str = Field(description="Post content")
    author: str = Field(description="Post author")
    tags: List[str] = Field(default_factory=list, description="Post tags")


def example_1_basic_validation():
    """Example 1: Basic validation with default configuration."""
    print("\n=== Example 1: Basic Validation ===")

    validator = OutputValidator()

    # Validate a simple dictionary
    output = {
        "title": "Introduction to FSA",
        "content": "Finite State Automata are powerful tools for modeling state-based systems.",
    }

    result = validator.validate(output)

    print(f"Validation State: {result.state}")
    print(f"Passed: {result.passed}")
    print(f"Overall Score: {result.quality_scores.overall:.2f}")
    print(f"Quality Scores: {result.quality_scores.to_dict()}")


def example_2_schema_validation():
    """Example 2: Validation with Pydantic schema model."""
    print("\n=== Example 2: Schema Validation ===")

    config = OutputValidatorConfig(
        schema_model=BlogPost,
        pass_threshold=0.75,
    )
    validator = OutputValidator(config)

    # Valid output matching schema
    valid_output = {
        "title": "Understanding FSA",
        "content": "This post explains FSA concepts in detail with practical examples.",
        "author": "Jane Doe",
        "tags": ["fsa", "programming", "tutorial"],
    }

    result = validator.validate(valid_output)

    print(f"Validation State: {result.state}")
    print(f"Passed: {result.passed}")
    print(f"Correctness Score: {result.quality_scores.correctness:.2f}")
    print(f"Number of Issues: {len(result.issues)}")


def example_3_incomplete_output():
    """Example 3: Handling incomplete output with missing required fields."""
    print("\n=== Example 3: Incomplete Output ===")

    config = OutputValidatorConfig(
        required_fields=["title", "content", "author", "summary"],
        pass_threshold=0.7,
    )
    validator = OutputValidator(config)

    # Incomplete output
    incomplete_output = {
        "title": "Partial Post",
        "content": "This post is missing some fields.",
        # Missing: author, summary
    }

    result = validator.validate(incomplete_output)

    print(f"Validation State: {result.state}")
    print(f"Passed: {result.passed}")
    print(f"Completeness Score: {result.quality_scores.completeness:.2f}")
    print(f"\nIssues detected:")
    for issue in result.issues:
        print(f"  - [{issue.severity}] {issue.category}: {issue.message}")


def example_4_format_validation():
    """Example 4: Format validation with JSON extraction."""
    print("\n=== Example 4: Format Validation ===")

    validator = OutputValidator()

    # JSON embedded in markdown
    markdown_output = """
    Here's the result:
    ```json
    {
        "title": "Extracted JSON",
        "content": "This JSON was extracted from markdown"
    }
    ```
    """

    result = validator.validate(markdown_output)

    print(f"Validation State: {result.state}")
    print(f"Format Compliance: {result.quality_scores.format_compliance:.2f}")
    print(f"Validated Output: {result.validated_output}")
    print(f"\nIssues detected:")
    for issue in result.issues:
        print(f"  - [{issue.severity}] {issue.category}: {issue.message}")


def example_5_threshold_tuning():
    """Example 5: Threshold-based pass/fail decisions."""
    print("\n=== Example 5: Threshold Tuning ===")

    output = {
        "title": "Test Output",
        "content": "Short content",
    }

    # Test with different thresholds
    thresholds = [0.5, 0.7, 0.9]

    for threshold in thresholds:
        config = OutputValidatorConfig(pass_threshold=threshold)
        validator = OutputValidator(config)
        result = validator.validate(output)

        print(f"\nThreshold: {threshold:.1f}")
        print(f"  Overall Score: {result.quality_scores.overall:.2f}")
        print(f"  Passed: {result.passed}")


def example_6_schema_validation_failure():
    """Example 6: Handling schema validation failures."""
    print("\n=== Example 6: Schema Validation Failure ===")

    config = OutputValidatorConfig(
        schema_model=BlogPost,
        pass_threshold=0.8,
    )
    validator = OutputValidator(config)

    # Invalid output with wrong types and missing fields
    invalid_output = {
        "title": 12345,  # Should be string
        "content": "Some content",
        # Missing: author (required field)
    }

    result = validator.validate(invalid_output)

    print(f"Validation State: {result.state}")
    print(f"Passed: {result.passed}")
    print(f"Correctness Score: {result.quality_scores.correctness:.2f}")
    print(f"\nSchema validation errors:")
    for issue in result.issues:
        if issue.category == "schema":
            print(f"  - {issue.location}: {issue.message}")


def example_7_cascading_validators():
    """Example 7: Simulating FSA cascade pattern."""
    print("\n=== Example 7: Cascading Validators ===")

    # First validator: Check basic format
    format_config = OutputValidatorConfig(
        enable_format_validation=True,
        pass_threshold=0.6,
    )
    format_validator = OutputValidator(format_config)

    # Second validator: Check completeness and quality
    quality_config = OutputValidatorConfig(
        required_fields=["title", "content", "author"],
        pass_threshold=0.8,
    )
    quality_validator = OutputValidator(quality_config)

    output = {
        "title": "Cascading Validation Example",
        "content": "This demonstrates how validators can be chained together in a cascade.",
        "author": "System",
    }

    # Stage 1: Format validation
    format_result = format_validator.validate(output)
    print(f"Stage 1 - Format Validation:")
    print(f"  State: {format_result.state}")
    print(f"  Passed: {format_result.passed}")

    # Stage 2: Quality validation (only if format passed)
    if format_result.passed:
        quality_result = quality_validator.validate(format_result.validated_output)
        print(f"\nStage 2 - Quality Validation:")
        print(f"  State: {quality_result.state}")
        print(f"  Passed: {quality_result.passed}")
        print(f"  Overall Score: {quality_result.quality_scores.overall:.2f}")

        if quality_result.passed:
            print("\n✓ Output passed all validation stages!")
        else:
            print("\n✗ Output failed quality validation")
    else:
        print("\n✗ Output failed format validation - skipping quality check")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Output Validator FSA - Usage Examples")
    print("=" * 60)

    example_1_basic_validation()
    example_2_schema_validation()
    example_3_incomplete_output()
    example_4_format_validation()
    example_5_threshold_tuning()
    example_6_schema_validation_failure()
    example_7_cascading_validators()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

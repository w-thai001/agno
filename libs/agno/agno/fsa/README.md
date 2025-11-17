# FSA (Finite State Automaton) Implementations

This module provides Finite State Automaton implementations for the Agno framework, enabling sophisticated state-based validation and processing pipelines.

## Output Validator FSA

The Output Validator FSA provides comprehensive validation of deliverables with multi-dimensional quality scoring.

### Features

- **Multi-dimensional Quality Scoring**: Evaluates outputs across four dimensions:
  - **Completeness** (30% weight): Checks for presence of required fields
  - **Correctness** (30% weight): Validates against schema and data types
  - **Format Compliance** (25% weight): Ensures proper JSON/structure formatting
  - **Clarity** (15% weight): Assesses content quality and structure

- **Schema Validation**: Uses Pydantic models for strict type checking and field validation

- **Flexible Input Formats**:
  - Python dictionaries
  - JSON strings
  - JSON embedded in markdown code blocks
  - Pydantic model instances

- **Error Detection & Reporting**: Tracks issues with severity levels (error, warning, info) and categorization

- **Threshold-based Pass/Fail**: Configurable quality thresholds for automated decision making

- **FSA State Management**: Clear state transitions (IDLE → VALIDATING → SCORING → COMPLETE/FAILED)

- **Cascade-compatible**: Results designed for chaining with other FSAs

### Installation

The FSA module is part of the Agno library:

```python
from agno.fsa import (
    OutputValidator,
    OutputValidatorConfig,
    ValidationResult,
    ValidationState,
)
```

### Quick Start

#### Basic Usage

```python
from agno.fsa import OutputValidator

# Create validator with default configuration
validator = OutputValidator()

# Validate output
output = {"title": "My Output", "content": "Some content here"}
result = validator.validate(output)

print(f"Passed: {result.passed}")
print(f"Overall Score: {result.quality_scores.overall}")
```

#### Schema Validation

```python
from pydantic import BaseModel, Field
from agno.fsa import OutputValidator, OutputValidatorConfig

# Define schema
class BlogPost(BaseModel):
    title: str
    content: str
    author: str

# Configure validator
config = OutputValidatorConfig(
    schema_model=BlogPost,
    pass_threshold=0.75,
)
validator = OutputValidator(config)

# Validate against schema
output = {
    "title": "My Post",
    "content": "Post content",
    "author": "John Doe",
}
result = validator.validate(output)
```

#### Required Fields Checking

```python
from agno.fsa import OutputValidator, OutputValidatorConfig

config = OutputValidatorConfig(
    required_fields=["title", "content", "author"],
    pass_threshold=0.7,
)
validator = OutputValidator(config)

result = validator.validate(output)
print(f"Completeness: {result.quality_scores.completeness}")
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pass_threshold` | float | 0.7 | Minimum overall score to pass (0-1) |
| `required_fields` | List[str] | [] | Fields required for completeness |
| `schema_model` | Type[BaseModel] | None | Pydantic model for schema validation |
| `enable_format_validation` | bool | True | Enable JSON/format validation |
| `enable_content_validation` | bool | True | Enable content quality checks |
| `min_clarity_length` | int | 10 | Minimum content length for clarity |

### Validation Result Structure

```python
class ValidationResult(BaseModel):
    state: ValidationState           # Current FSA state
    passed: bool                     # Pass/fail status
    quality_scores: QualityScore     # Multi-dimensional scores
    issues: List[ValidationIssue]    # Detected issues
    validated_output: Any            # Parsed/validated output
    raw_output: str                  # Original input
    metadata: Dict[str, Any]         # Additional data
```

### Quality Scores

```python
class QualityScore(BaseModel):
    completeness: float       # 0-1: Required fields present
    correctness: float        # 0-1: Schema compliance
    format_compliance: float  # 0-1: JSON/format validity
    clarity: float           # 0-1: Content structure quality

    @property
    def overall(self) -> float:
        # Weighted average of all scores
        return (completeness * 0.3 + correctness * 0.3 +
                format_compliance * 0.25 + clarity * 0.15)
```

### FSA States

- **IDLE**: Initial state, ready for validation
- **VALIDATING**: Parsing and format validation in progress
- **SCORING**: Calculating quality scores
- **COMPLETE**: Validation completed successfully
- **FAILED**: Validation failed due to error

### Error Detection

Issues are categorized and tracked with severity levels:

```python
class ValidationIssue(BaseModel):
    severity: str    # "error", "warning", "info"
    category: str    # "schema", "format", "content", "completeness", etc.
    message: str     # Human-readable description
    location: str    # Optional location in output (e.g., "field.nested")
```

### Cascading Validators

Validators can be chained together for multi-stage validation:

```python
# Stage 1: Format validation
format_validator = OutputValidator(
    OutputValidatorConfig(pass_threshold=0.6)
)
format_result = format_validator.validate(raw_output)

# Stage 2: Quality validation (only if format passed)
if format_result.passed:
    quality_validator = OutputValidator(
        OutputValidatorConfig(
            required_fields=["title", "content"],
            pass_threshold=0.8,
        )
    )
    quality_result = quality_validator.validate(format_result.validated_output)

    if quality_result.passed:
        # Continue to next stage
        pass
```

### Examples

See `agno/fsa/examples/output_validator_example.py` for comprehensive usage examples including:

1. Basic validation with default config
2. Schema validation with Pydantic models
3. Handling incomplete outputs
4. Format validation and JSON extraction
5. Threshold tuning
6. Schema validation failures
7. Cascading validators

Run the examples:

```bash
python -m agno.fsa.examples.output_validator_example
```

### Testing

Run the test suite:

```bash
pytest tests/fsa/test_output_validator.py -v
```

The test suite includes 30 comprehensive tests covering:
- Basic functionality and initialization
- Format validation (JSON, markdown, plain text)
- Schema validation
- Quality scoring (completeness, correctness, clarity)
- Threshold-based decisions
- Error detection and reporting
- State transitions
- Integration scenarios

### Architecture

The Output Validator FSA follows clean architecture principles:

```
User Input
    ↓
[IDLE → VALIDATING]
    ↓
Format Parsing (JSON/dict/Pydantic)
    ↓
Schema Validation (if configured)
    ↓
[VALIDATING → SCORING]
    ↓
Multi-dimensional Scoring:
  - Completeness
  - Correctness
  - Format Compliance
  - Clarity
    ↓
Threshold Evaluation
    ↓
[SCORING → COMPLETE/FAILED]
    ↓
ValidationResult
```

### Error Handling

The validator handles errors gracefully:

- **Parse errors**: Falls back to plain text with format warnings
- **Schema errors**: Records validation issues but continues scoring
- **Invalid input**: Transitions to FAILED state with error details
- **Exceptions**: Caught and reported as validation errors

### Performance

- Lightweight: ~400 lines of production code
- Fast: Typical validation < 1ms
- Memory efficient: Minimal object allocation
- No external dependencies beyond Pydantic

### Extending

To create custom validators:

1. Follow the FSA state pattern (IDLE → processing states → COMPLETE/FAILED)
2. Use Pydantic models for configuration and results
3. Implement reset() for reusability
4. Design results to be cascade-compatible (serializable, with state info)

### License

Part of the Agno framework. See LICENSE file for details.

### Contributing

Contributions welcome! Please ensure:
- All tests pass
- New features include tests
- Code follows existing style
- Documentation is updated

---

For more information about Agno, visit: https://github.com/agno-agi/agno

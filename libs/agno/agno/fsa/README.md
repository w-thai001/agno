# FSA: Framework for Structured Automation

## FSA-2.1: Code Quality Validator

A comprehensive code quality validation system that analyzes code across multiple dimensions and provides actionable improvement suggestions.

### Features

- **Multi-Language Support**: Currently supports JavaScript and Python
- **Comprehensive Analysis**: Validates syntax, style, security, and performance
- **Quality Scoring**: Generates scores (0-100) for each quality dimension
- **Prioritized Suggestions**: Provides improvement suggestions ranked by priority (Critical, High, Medium, Low)
- **Integration Ready**: Designed to integrate with FSA-1.1 (Prompt Optimizer) and FSA-1.2 (Template Library)

### Quality Metrics

The validator assesses code across four key dimensions:

1. **Syntax (0-100)**: Checks for syntax errors and structural issues
2. **Style (0-100)**: Validates code style and formatting conventions
3. **Security (0-100)**: Identifies potential security vulnerabilities
4. **Performance (0-100)**: Detects performance anti-patterns

### Installation

```python
from agno.fsa import CodeQualityValidator

# Initialize the validator
validator = CodeQualityValidator()
```

### Usage

#### Basic Validation

```python
from agno.fsa import CodeQualityValidator

# Initialize validator
validator = CodeQualityValidator()

# Validate JavaScript code
code = """function badCode(x){var y=x*2;return y}"""
result = validator.validateCode(code, "javascript")

# Access quality metrics
print(f"Overall Score: {result.metrics.overall}")
print(f"Syntax Score: {result.metrics.syntax}")
print(f"Style Score: {result.metrics.style}")
print(f"Security Score: {result.metrics.security}")
print(f"Performance Score: {result.metrics.performance}")

# Get improvement suggestions
for suggestion in result.suggestions:
    print(f"[{suggestion.priority.value}] {suggestion.issue}")
    print(f"Suggestion: {suggestion.suggestion}")
```

#### With FSA-1.1 and FSA-1.2 Integration

```python
from agno.fsa import CodeQualityValidator
# from agno.fsa import PromptOptimizer  # FSA-1.1 (coming soon)
# from agno.fsa import TemplateLibrary  # FSA-1.2 (coming soon)

# Initialize with integrations
# prompt_optimizer = PromptOptimizer()
# template_library = TemplateLibrary()

validator = CodeQualityValidator(
    # prompt_optimizer=prompt_optimizer,
    # template_library=template_library,
)

result = validator.validateCode(code, "javascript")
```

### Language-Specific Validation

#### JavaScript Validation

The JavaScript validator checks for:

**Syntax:**
- Balanced braces
- Proper function structure

**Style:**
- Use of `const`/`let` instead of `var`
- Proper function spacing
- camelCase naming conventions
- Function documentation (JSDoc)

**Security:**
- `eval()` usage (XSS risk)
- `innerHTML` usage (XSS risk)
- `document.write()` usage

**Performance:**
- Array operations in loops
- Synchronous XMLHttpRequest

#### Python Validation

The Python validator checks for:

**Syntax:**
- Valid Python syntax (using AST parsing)

**Style (PEP 8):**
- 4-space indentation
- snake_case function naming
- Function docstrings (PEP 257)
- Line length (79 characters)

**Security:**
- `eval()` and `exec()` usage
- `pickle` module usage
- SQL injection patterns

**Performance:**
- List concatenation in loops
- Global variable usage

### API Reference

#### CodeQualityValidator

**Methods:**

- `validateCode(code: str, language: str) -> ValidationResult`
  - Validates code and returns comprehensive results
  - Parameters:
    - `code`: Source code to validate
    - `language`: Programming language ("javascript" or "python")
  - Returns: `ValidationResult` object

- `generateQualityScore() -> QualityMetrics`
  - Generates quality scores based on validation results
  - Returns: `QualityMetrics` object with scores

- `suggestImprovements() -> List[ImprovementSuggestion]`
  - Generates prioritized improvement suggestions
  - Returns: List of `ImprovementSuggestion` objects

#### QualityMetrics

**Properties:**
- `syntax: float` - Syntax quality score (0-100)
- `style: float` - Style quality score (0-100)
- `security: float` - Security quality score (0-100)
- `performance: float` - Performance quality score (0-100)
- `overall: float` - Overall quality score (0-100)

**Methods:**
- `to_dict() -> Dict[str, float]` - Convert metrics to dictionary

#### ImprovementSuggestion

**Properties:**
- `priority: Priority` - Priority level (CRITICAL, HIGH, MEDIUM, LOW)
- `category: str` - Category (syntax, style, security, performance)
- `issue: str` - Description of the issue
- `suggestion: str` - Recommended improvement
- `line: Optional[int]` - Line number where issue occurs
- `code_snippet: Optional[str]` - Current code snippet
- `fixed_code: Optional[str]` - Suggested fixed code

#### ValidationResult

**Properties:**
- `code: str` - Original code that was validated
- `language: Language` - Programming language
- `metrics: QualityMetrics` - Quality metrics
- `suggestions: List[ImprovementSuggestion]` - Improvement suggestions
- `errors: List[str]` - Validation errors

### Example Output

For the code `function badCode(x){var y=x*2;return y}`:

```
Quality Metrics:
- Syntax: 100/100 ✅ Excellent
- Style: 80/100 🟢 Good
- Security: 100/100 ✅ Excellent
- Performance: 100/100 ✅ Excellent
- Overall: 95/100 ✅ Excellent

Improvement Suggestions:
🟠 HIGH Priority
  [1] STYLE
      Issue: Use of 'var' keyword for variable 'y'
      Suggestion: Replace 'var' with 'const' or 'let' for better scoping
      Current: var y
      Improved: const y

🟡 MEDIUM Priority
  [1] STYLE
      Issue: Missing function documentation
      Suggestion: Add JSDoc comments to document function purpose and parameters
```

### Demo

Run the demo script to see the validator in action:

```bash
python3 demo_fsa_2_1.py
```

### Future Integrations

#### FSA-1.1: Prompt Optimizer (Coming Soon)
- Will optimize improvement suggestion messages for better clarity
- Integration point: `_optimize_suggestion_prompts()` method

#### FSA-1.2: Template Library (Coming Soon)
- Will validate code against standard templates
- Will run template-based test cases
- Integration point: `_apply_template_validation()` method

### Contributing

When extending the validator:

1. Add language support by implementing `_validate_{language}()` methods
2. Add new validation rules in the appropriate category methods
3. Update scoring algorithms in `_score_{language}()` methods
4. Ensure suggestions include priority, category, issue, and recommendation

### License

Part of the Agno framework.

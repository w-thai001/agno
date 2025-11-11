# FSA-2.1: Code Quality Validator

Comprehensive code quality validation system with multi-dimensional analysis, integrated with FSA-1.1 (Prompt Optimizer) and FSA-1.2 (Code Template Library).

## Features

### Multi-Dimensional Analysis
- **Syntax Correctness**: Validates code syntax and identifies errors
- **Style Compliance**: Checks naming conventions, formatting, documentation
- **Security Vulnerabilities**: Detects SQL injection, XSS, code injection, hardcoded secrets
- **Performance Optimization**: Identifies inefficient patterns and bottlenecks
- **Best Practices**: Validates error handling, design patterns, maintainability

### Integration
- **FSA-1.1 Prompt Optimizer**: Generates optimized prompts for AI-assisted code analysis
- **FSA-1.2 Code Template Library**: Compare code against quality templates and learn from examples

### Multi-Language Support
- Python
- JavaScript

## Installation

```bash
pip install agno
```

## Quick Start

```python
from agno.validator import CodeQualityValidator

# Initialize validator
validator = CodeQualityValidator()

# Validate code
code = '''
def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    return sum(numbers) / len(numbers)
'''

result = validator.validateCode(code, "python")

print(f"Overall Score: {result.report.overall_score}/100")
print(f"Valid: {result.is_valid}")
print(f"Summary: {result.report.summary}")
```

## Core Methods

### `validateCode(code, language, detailed=True)`

Validates code across all quality dimensions.

**Parameters:**
- `code` (str): Source code to validate
- `language` (str): Programming language (python, javascript)
- `detailed` (bool): Include detailed analysis

**Returns:** `ValidationResult` with comprehensive quality report

```python
result = validator.validateCode(code, "python")

# Access overall score
print(result.report.overall_score)  # 0-100

# Check if valid
print(result.is_valid)  # True/False

# Get dimension scores
for dim_name, dim_score in result.report.dimensions.items():
    print(f"{dim_name}: {dim_score.score}/100")

# Get top issues
for issue in result.top_issues:
    print(f"{issue.severity.value}: {issue.message}")
```

### `getQualityScore(validation_result)`

Extract overall quality score from validation result.

```python
score = validator.getQualityScore(result)  # Returns 0-100
```

### `getSuggestions(validation_result, limit=10)`

Get actionable suggestions for improving code quality.

```python
suggestions = validator.getSuggestions(result, limit=10)

for suggestion in suggestions:
    print(suggestion)
```

## Quality Dimensions

### 1. Syntax (25% weight)

Validates code can be parsed and executed.

**Checks:**
- Python: AST parsing
- JavaScript: Basic syntax patterns
- Unclosed strings/brackets
- Invalid syntax structures

**Example Issues:**
- `SyntaxError: invalid syntax`
- `Unmatched parentheses`

### 2. Security (25% weight)

Detects security vulnerabilities.

**Checks:**
- SQL injection patterns
- XSS vulnerabilities (innerHTML usage)
- Code injection (eval() usage)
- Hardcoded secrets
- Insecure data handling

**Example Issues:**
```python
# CRITICAL: SQL injection
query = "SELECT * FROM users WHERE id='" + user_id + "'"

# CRITICAL: Code injection
result = eval(user_input)

# HIGH: Hardcoded secret
password = "admin123"
```

### 3. Style (15% weight)

Checks code readability and conventions.

**Checks:**
- Line length (>120 chars)
- Naming conventions (snake_case/camelCase)
- Comment coverage
- Indentation consistency

**Example Issues:**
- `Line exceeds 120 characters`
- `Use snake_case for Python functions`
- `Inconsistent indentation`

### 4. Performance (15% weight)

Identifies optimization opportunities.

**Checks:**
- Inefficient loop patterns
- DOM manipulation in loops (JS)
- Async/await usage
- Global variable overuse

**Example Issues:**
```python
# Inefficient
for i in range(len(items)):
    process(items[i])

# Better
for item in items:
    process(item)
```

### 5. Best Practices (20% weight)

Validates adherence to best practices.

**Checks:**
- Error handling (try/except, try/catch)
- Docstrings/documentation
- Bare except clauses
- Magic numbers
- Console.log in production

**Example Issues:**
- `Add error handling (try/except)`
- `Bare 'except:' catches all exceptions`
- `Missing docstrings`

## FSA-1.1 Integration: Prompt Optimizer

Generate optimized prompts for AI-assisted code analysis.

```python
# Get optimized prompt for security analysis
prompt = validator.get_optimized_prompt(
    code,
    "python",
    "security"
)

# Use prompt with your LLM for deep analysis
# result = llm.analyze(prompt)
```

**Available Analysis Types:**
- `syntax` - Syntax validation
- `style` - Style compliance
- `security` - Security vulnerabilities
- `performance` - Performance optimization
- `best_practices` - Best practices
- `overall` - Comprehensive analysis

## FSA-1.2 Integration: Template Library

Compare code against quality templates and learn from examples.

### Get Templates

```python
from agno.templates import CodeTemplateLibrary, QualityLevel

library = CodeTemplateLibrary()

# Get all templates
templates = library.get_all_templates()

# Get templates by language
python_templates = library.get_templates_by_language("python")

# Get templates by quality level
good_examples = library.get_templates_by_quality(QualityLevel.EXCELLENT)

# Search templates
api_templates = library.search_templates("api", language="python")
```

### Compare with Templates

```python
# Compare your code against a template
comparison = validator.compare_with_template(
    code=my_code,
    language="python",
    template_id="py_api_good"
)

print(f"Your score: {comparison['code']['score']}")
print(f"Template score: {comparison['template']['score']}")
print(f"Difference: {comparison['score_difference']}")

# Learn from template
for lesson in comparison['lessons_learned']:
    print(f"  • {lesson}")
```

### Built-in Templates

**Python Templates:**
- `py_api_good` - Well-structured Flask API endpoint (GOOD)
- `py_api_poor` - Poorly written API endpoint (POOR)
- `py_db_query_good` - Secure database query with parameterization (EXCELLENT)
- `py_db_query_poor` - Insecure SQL injection vulnerable query (POOR)
- `py_error_handling_good` - Comprehensive error handling (EXCELLENT)

**JavaScript Templates:**
- `js_async_good` - Proper async/await with error handling (EXCELLENT)
- `js_async_poor` - Callback hell pattern (POOR)
- `js_xss_vulnerable` - XSS vulnerability example (POOR)

## Quality Scoring

### Score Ranges
- **90-100**: Excellent - Production-ready code
- **70-89**: Good - Minor improvements needed
- **50-69**: Fair - Needs attention
- **0-49**: Poor - Significant issues

### Weighted Scoring
```
Overall Score = (Syntax × 0.25) + (Security × 0.25) +
                (Style × 0.15) + (Performance × 0.15) +
                (Best Practices × 0.20)
```

## Issue Severity

- **CRITICAL**: Must fix immediately (security vulnerabilities, syntax errors)
- **HIGH**: Should fix soon (security concerns, major issues)
- **MEDIUM**: Should address (style violations, minor bugs)
- **LOW**: Nice to fix (minor style issues, optimizations)
- **INFO**: Informational only

## Advanced Usage

### Custom Validation

```python
# Validate with detailed analysis
result = validator.validateCode(code, "python", detailed=True)

# Get specific dimension score
security_score = result.report.dimensions['security']
print(f"Security: {security_score.score}/100")

# Check for critical issues
for issue in security_score.issues:
    if issue.severity == IssueSeverity.CRITICAL:
        print(f"CRITICAL: {issue.message}")
        print(f"Fix: {issue.suggestion}")
```

### Batch Validation

```python
codes = [
    ("file1.py", python_code1),
    ("file2.py", python_code2),
    ("file3.js", javascript_code),
]

results = []
for filename, code in codes:
    language = "python" if filename.endswith(".py") else "javascript"
    result = validator.validateCode(code, language)
    results.append((filename, result))

# Report
for filename, result in results:
    print(f"{filename}: {result.report.overall_score}/100")
```

### Integration with CI/CD

```python
import sys

def check_code_quality(code, language, min_score=70):
    """Check code quality and exit with error if below threshold."""
    validator = CodeQualityValidator()
    result = validator.validateCode(code, language)

    if result.report.overall_score < min_score:
        print(f"❌ Code quality too low: {result.report.overall_score}/100")
        print(f"   Minimum required: {min_score}/100")

        for issue in result.top_issues[:5]:
            print(f"   • {issue.message}")

        sys.exit(1)

    print(f"✓ Code quality passed: {result.report.overall_score}/100")
    return result

# Use in CI
check_code_quality(my_code, "python", min_score=80)
```

## Running the Demo

```bash
python cookbook/validator/quality_demo.py
```

**Demo Scenarios:**
1. **Basic Validation** - Good vs poor code examples
2. **FSA-1.2 Template Validation** - Validate all library templates
3. **Template Comparison** - Compare code against templates
4. **Security Detection** - Find vulnerabilities
5. **Dimension Analysis** - Detailed scoring breakdown
6. **Actionable Suggestions** - Get improvement recommendations
7. **FSA-1.1 Prompt Generation** - Optimized AI prompts
8. **Multi-Language Support** - Python and JavaScript examples

## Example Output

```
Code: calculate_average function
Language: python
Length: 435 characters

Overall Score: 98/100
Status: ✓ VALID
Execution Time: 1.57ms

Dimension Scores:
  ✓ Syntax: 100/100
  ✓ Style: 90/100
  ✓ Security: 100/100
  ✓ Performance: 100/100
  ✓ Best Practices: 100/100

Summary:
  Excellent code quality (score: 98/100). Found 0 issues.
```

## Architecture

```
CodeQualityValidator
├── validateCode()
│   ├── _validate_syntax()
│   ├── _validate_style()
│   ├── _validate_security()
│   ├── _validate_performance()
│   └── _validate_best_practices()
├── getQualityScore()
├── getSuggestions()
├── compare_with_template() → FSA-1.2
└── get_optimized_prompt() → FSA-1.1
```

## Best Practices

1. **Always validate before deployment** - Catch issues early
2. **Set minimum quality thresholds** - Enforce standards
3. **Review top issues first** - Prioritize critical problems
4. **Learn from templates** - Compare against good examples
5. **Use AI analysis for complex issues** - Leverage FSA-1.1 prompts
6. **Track quality over time** - Monitor improvements

## Error Handling

The validator includes comprehensive error handling:

```python
try:
    result = validator.validateCode(code, "python")
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Common errors:
- `ValueError`: Unsupported language
- `SyntaxError`: Invalid Python syntax (captured in report)

## Performance

- **Average validation time**: 1-5ms per file
- **Supports large files**: Up to 10,000 lines
- **Minimal dependencies**: Uses standard library for core validation

## License

Same as the parent Agno project.

## Contributing

To add new templates to FSA-1.2:

```python
from agno.templates import CodeTemplate, TemplateCategory, QualityLevel

template = CodeTemplate(
    id="my_template",
    name="My Template",
    description="Description",
    language="python",
    category=TemplateCategory.API_ENDPOINT,
    quality_level=QualityLevel.EXCELLENT,
    code="...",
    best_practices=["..."],
    security_notes=["..."]
)

library.add_template(template)
```

## Support

For issues or questions, refer to the Agno project documentation.

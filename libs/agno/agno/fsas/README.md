# FSA Generator - Meta-FSA for Automated FSA Creation

The FSA Generator is a comprehensive meta-FSA (Functional Specialist Agent) that automatically generates other FSAs based on specifications. It provides a complete code generation pipeline including template management, code synthesis, automated test generation, validation, and git integration.

## Features

- **Specification-Driven Generation**: Define FSAs using simple JSON/YAML specifications
- **Template Engine**: Built-in templates for different FSA categories (Core, Integration, Meta, Domain)
- **Automated Test Generation**: Automatically generates comprehensive pytest test suites
- **Code Validation**: Validates generated code for syntax and required components
- **Git Integration**: Optional automatic commits with descriptive messages
- **Error Recovery**: Graceful error handling with helpful recovery suggestions

## Installation

The FSA Generator is part of the agno package:

```python
from agno.fsas import FSAGenerator
```

## Quick Start

### Basic Usage

```python
from agno.fsas import FSAGenerator

# Create generator
generator = FSAGenerator()

# Define FSA specification
spec = {
    "name": "DataProcessor",
    "category": "Domain",
    "purpose": "Process and transform data from various sources",
    "key_capabilities": [
        "Read data from multiple formats",
        "Transform and validate data",
        "Export to different formats"
    ],
    "dependencies": ["pandas", "numpy"],
    "complexity_target": "400-600 LOC"
}

# Generate FSA
implementation = generator.generate_fsa(spec)
print(f"Generated: {implementation.file_path}")
```

### Using JSON/YAML Specifications

```python
# From JSON file
implementation = generator.generate_fsa("specs/my_fsa.json")

# From YAML file
implementation = generator.generate_fsa("specs/my_fsa.yaml")
```

### With Git Integration

```python
# Enable automatic commits
generator = FSAGenerator(auto_commit=True)

# Generate and auto-commit
implementation = generator.generate_fsa(spec)
# FSA is automatically committed to git repository
```

## Specification Format

### Required Fields

- **name** (str): PascalCase name for the FSA
- **category** (str): One of "Core", "Integration", "Meta", "Domain"
- **purpose** (str): Brief description of what the FSA does

### Optional Fields

- **key_capabilities** (list): List of key capabilities
- **dependencies** (list): List of Python package dependencies
- **complexity_target** (str): Target LOC range (e.g., "300-500 LOC")
- **custom_methods** (dict): Custom method signatures and descriptions

### Example Specification

```json
{
  "name": "APIIntegrator",
  "category": "Integration",
  "purpose": "Integrate with external REST APIs",
  "key_capabilities": [
    "Send HTTP requests",
    "Handle authentication",
    "Parse JSON responses",
    "Implement retry logic"
  ],
  "dependencies": ["requests", "urllib3"],
  "complexity_target": "500-700 LOC",
  "custom_methods": {
    "authenticate": "Authenticate with API using OAuth2",
    "fetch_data": "Fetch data from API endpoint",
    "handle_rate_limit": "Handle API rate limiting"
  }
}
```

## FSA Categories

### Core Infrastructure FSAs
Foundation FSAs that provide basic functionality used by other FSAs.

```python
spec = {
    "name": "Logger",
    "category": "Core",
    "purpose": "Centralized logging and monitoring"
}
```

### Integration FSAs
FSAs that integrate with external services and APIs.

```python
spec = {
    "name": "SlackNotifier",
    "category": "Integration",
    "purpose": "Send notifications to Slack channels"
}
```

### Meta FSAs
FSAs that operate on other FSAs (like the Generator itself).

```python
spec = {
    "name": "FSAOptimizer",
    "category": "Meta",
    "purpose": "Optimize FSA performance and resource usage"
}
```

### Domain-Specific FSAs
FSAs for specific business domains or use cases.

```python
spec = {
    "name": "InvoiceProcessor",
    "category": "Domain",
    "purpose": "Process and validate invoices"
}
```

## Advanced Usage

### Custom Output Directories

```python
generator = FSAGenerator(
    repo_path="/path/to/repo",
    output_dir="/path/to/fsas",
    test_dir="/path/to/tests"
)
```

### Validation Only

```python
# Generate without writing files
spec = FSASpecification(**spec_dict)
parsed = generator.parse_specification(spec)
templates = generator.select_templates(parsed)
code = generator.synthesize_code(templates, parsed)

# Validate
if generator.validate_fsa(implementation):
    print("✓ FSA is valid")
```

### Error Handling

```python
try:
    implementation = generator.generate_fsa(spec)
except InvalidSpecificationError as e:
    recovery = generator.error_recovery(e)
    print(recovery)
except CodeValidationError as e:
    print(f"Generated code has errors: {e}")
except GitOperationError as e:
    print(f"Git operation failed: {e}")
```

## Generated FSA Structure

Each generated FSA includes:

### Main FSA Class
- `__init__()`: Initialize FSA with configuration
- `execute()`: Main execution method
- `validate_input()`: Input validation
- `get_state()` / `set_state()`: State management
- `handle_error()`: Error handling
- `initialize()` / `cleanup()`: Lifecycle methods
- Custom methods (if specified)

### Exception Class
- Custom exception class for FSA-specific errors

### Comprehensive Tests
- Initialization tests
- Core functionality tests
- Error handling tests
- State management tests
- Integration tests

## Example: Complete Workflow

```python
from agno.fsas import FSAGenerator, FSACategory

# Initialize generator with git integration
generator = FSAGenerator(auto_commit=True)

# Define a data processing FSA
spec = {
    "name": "CSVProcessor",
    "category": "Domain",
    "purpose": "Process and analyze CSV files",
    "key_capabilities": [
        "Read CSV files with various encodings",
        "Validate data types and ranges",
        "Clean and transform data",
        "Export to multiple formats"
    ],
    "dependencies": ["pandas", "chardet"],
    "complexity_target": "500-700 LOC",
    "custom_methods": {
        "detect_encoding": "Auto-detect CSV file encoding",
        "infer_types": "Infer column data types",
        "clean_missing": "Handle missing values",
        "export_json": "Export to JSON format"
    }
}

# Generate the FSA
try:
    implementation = generator.generate_fsa(spec)

    print(f"✓ Generated {implementation.spec.class_name}")
    print(f"  Location: {implementation.file_path}")
    print(f"  Tests: {implementation.test_file_path}")
    print(f"  Lines of Code: {len(implementation.code.splitlines())}")
    print(f"  Test Cases: {implementation.tests.count('def test_')}")

    # The FSA is now ready to use
    from agno.fsas.csv_processor import CSVProcessorFSA

    processor = CSVProcessorFSA()
    result = processor.execute(task="process_file", params={"file": "data.csv"})

except Exception as e:
    print(f"✗ Generation failed: {e}")
    recovery_msg = generator.error_recovery(e)
    print(recovery_msg)
```

## API Reference

### FSAGenerator

**Methods:**
- `generate_fsa(spec)` → FSAImplementation - Main generation method
- `parse_specification(spec)` → ParsedSpec - Parse and validate specification
- `select_templates(parsed_spec)` → List[Template] - Select appropriate templates
- `synthesize_code(templates, spec)` → str - Generate Python code
- `generate_tests(code, spec)` → str - Auto-generate pytest tests
- `validate_fsa(implementation)` → bool - Validate generated code
- `commit_to_repo(implementation)` → bool - Commit to git repository
- `error_recovery(error)` → str - Handle generation failures

### FSASpecification

Pydantic model for FSA specifications with validation.

### ParsedSpec

Processed specification with additional computed properties:
- `file_name` → str - Snake_case filename
- `class_name` → str - PascalCase class name with FSA suffix

### FSAImplementation

Container for generated FSA with methods:
- `validate_syntax()` → bool - Validate Python syntax
- `validate_tests()` → bool - Validate test syntax

## Best Practices

1. **Start Simple**: Begin with basic specifications and add complexity incrementally
2. **Use Categories**: Choose the appropriate FSA category for better template selection
3. **Custom Methods**: Define custom methods for domain-specific functionality
4. **Validate Early**: Use specification validation to catch errors early
5. **Test Generated Code**: Run pytest on generated tests to ensure quality
6. **Version Control**: Use git integration to track FSA evolution

## Troubleshooting

### Common Issues

**Invalid Specification**
- Ensure name is PascalCase without spaces
- Verify category is one of: Core, Integration, Meta, Domain
- Check complexity_target format: "XXX-YYY LOC"

**Code Validation Failures**
- Review custom method specifications for syntax errors
- Simplify dependencies if conflicts arise
- Check that generated code compiles with `python -m py_compile`

**Git Operation Errors**
- Verify git repository is initialized
- Check file permissions
- Ensure working directory is clean

## License

MPL 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

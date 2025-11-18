"""
Comprehensive test suite for DocumentationGeneratorFSA.

Tests cover all major functionality including:
- API documentation generation
- Docstring generation
- README creation
- Architecture diagrams
- Tutorial generation
- Changelog generation
- OpenAPI spec generation
- Code example extraction
- Cross-reference generation
- Multi-format output
- Version tracking
- Error handling
- Type hint documentation
- Multi-language support
- Performance optimization
"""

import ast
import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, List, Any

from agno.fsas.documentation.documentation_generator_fsa import (
    DocumentationGeneratorFSA,
    DocumentationConfig,
    FunctionDocumentation,
    ClassDocumentation,
    ModuleDocumentation,
)


@pytest.fixture
def default_fsa():
    """Create a default DocumentationGeneratorFSA instance."""
    return DocumentationGeneratorFSA()


@pytest.fixture
def configured_fsa():
    """Create a configured DocumentationGeneratorFSA instance."""
    config = DocumentationConfig(
        project_name="Test Project",
        project_version="1.2.3",
        author="Test Author",
        description="A test project for documentation generation",
        include_private=False,
        include_magic=False,
        supported_languages=["en", "es"],
        default_language="en",
        output_formats=["markdown", "html"],
    )
    return DocumentationGeneratorFSA(config)


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''
"""Sample module for testing documentation generation."""

import os
from typing import List, Optional


CONSTANT_VALUE = 42


class SampleClass:
    """
    A sample class for testing.

    Attributes:
        name: The name of the instance
        value: A numeric value
    """

    name: str
    value: int

    def __init__(self, name: str, value: int = 0):
        """
        Initialize the SampleClass.

        Args:
            name: The name to assign
            value: The initial value (default: 0)
        """
        self.name = name
        self.value = value

    def process(self, data: List[str]) -> Optional[str]:
        """
        Process a list of data.

        Args:
            data: List of strings to process

        Returns:
            Processed result or None if empty

        Raises:
            ValueError: If data is invalid
        """
        if not data:
            raise ValueError("Data cannot be empty")
        return " ".join(data)


def helper_function(x: int, y: int) -> int:
    """
    A helper function for calculations.

    Args:
        x: First integer
        y: Second integer

    Returns:
        Sum of x and y

    Example:
        >>> helper_function(2, 3)
        5
    """
    return x + y


async def async_operation(timeout: float = 1.0) -> bool:
    """
    An async operation.

    Args:
        timeout: Operation timeout in seconds

    Returns:
        True if successful
    """
    return True
'''


@pytest.fixture
def sample_api_routes():
    """Sample API routes for OpenAPI spec testing."""
    return [
        {
            "path": "/users",
            "method": "GET",
            "summary": "List all users",
            "description": "Retrieve a list of all registered users",
            "operation_id": "listUsers",
            "tags": ["users"],
            "parameters": [
                {
                    "name": "limit",
                    "in": "query",
                    "schema": {"type": "integer"},
                    "description": "Maximum number of users to return"
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        }
                    }
                }
            }
        },
        {
            "path": "/users/{user_id}",
            "method": "GET",
            "summary": "Get user by ID",
            "description": "Retrieve a specific user by their ID",
            "operation_id": "getUserById",
            "tags": ["users"],
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"}
                }
            ],
            "responses": {
                "200": {
                    "description": "User found",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                },
                "404": {
                    "description": "User not found"
                }
            }
        }
    ]


@pytest.fixture
def sample_commits():
    """Sample commit history for changelog testing."""
    return [
        {
            "hash": "abc123",
            "message": "feat: Add user authentication",
            "author": "Developer 1",
            "date": "2024-01-01"
        },
        {
            "hash": "def456",
            "message": "fix: Resolve login issue",
            "author": "Developer 2",
            "date": "2024-01-02"
        },
        {
            "hash": "ghi789",
            "message": "docs: Update README",
            "author": "Developer 1",
            "date": "2024-01-03"
        },
        {
            "hash": "jkl012",
            "message": "feat: Add password reset functionality",
            "author": "Developer 3",
            "date": "2024-01-04"
        }
    ]


class TestAPIDocumentationGeneration:
    """Test suite for API documentation generation."""

    def test_generate_api_docs_basic(self, default_fsa, sample_python_code):
        """Test basic API documentation generation from AST."""
        tree = ast.parse(sample_python_code)
        result = default_fsa.generate_api_docs(tree)

        assert "module" in result
        assert "statistics" in result
        assert "cross_references" in result

        module = result["module"]
        assert len(module.classes) == 1
        assert module.classes[0].name == "SampleClass"
        assert len(module.functions) == 2  # helper_function and async_operation

    def test_api_docs_class_methods(self, default_fsa, sample_python_code):
        """Test that class methods are properly documented."""
        tree = ast.parse(sample_python_code)
        result = default_fsa.generate_api_docs(tree)

        sample_class = result["module"].classes[0]
        assert len(sample_class.methods) >= 2  # __init__ and process

        # Find the process method
        process_method = next(
            (m for m in sample_class.methods if m.name == "process"),
            None
        )
        assert process_method is not None
        assert "List[str]" in process_method.signature
        assert "Optional[str]" in process_method.signature

    def test_api_docs_statistics(self, default_fsa, sample_python_code):
        """Test statistics generation for API docs."""
        tree = ast.parse(sample_python_code)
        result = default_fsa.generate_api_docs(tree)

        stats = result["statistics"]
        assert stats["num_classes"] == 1
        assert stats["num_functions"] == 2
        assert stats["num_constants"] >= 1  # CONSTANT_VALUE


class TestDocstringGeneration:
    """Test suite for docstring generation and enhancement."""

    def test_generate_docstring_with_params(self, default_fsa):
        """Test docstring generation for function with parameters."""
        code = '''
def calculate(x: int, y: int, multiply: bool = False) -> int:
    """Calculate result."""
    return x * y if multiply else x + y
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = default_fsa.generate_docstrings(func_node)

        assert "Args:" in docstring
        assert "x" in docstring
        assert "y" in docstring
        assert "multiply" in docstring
        assert "Returns:" in docstring
        assert "int" in docstring

    def test_generate_docstring_with_raises(self, default_fsa):
        """Test docstring generation includes raises section."""
        code = '''
def validate(value: str) -> bool:
    if not value:
        raise ValueError("Value cannot be empty")
    return True
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = default_fsa.generate_docstrings(func_node)

        assert "Raises:" in docstring
        assert "ValueError" in docstring

    def test_enhance_existing_docstring(self, default_fsa):
        """Test enhancement of existing docstring."""
        code = '''
def process(data: List[str]) -> str:
    """Process data and return result."""
    return "".join(data)
'''
        tree = ast.parse(code)
        func_node = tree.body[0]

        docstring = default_fsa.generate_docstrings(func_node)

        # Should preserve original summary
        assert "Process data" in docstring or "process" in docstring.lower()
        # Should add Args and Returns
        assert "Args:" in docstring
        assert "Returns:" in docstring


class TestREADMEGeneration:
    """Test suite for README generation."""

    def test_create_readme_basic(self, configured_fsa):
        """Test basic README generation."""
        project_structure = {
            "features": [
                "Fast and efficient",
                "Easy to use",
                "Well documented"
            ]
        }

        readme = configured_fsa.create_readme(project_structure)

        assert "Test Project" in readme
        assert "Installation" in readme
        assert "Quick Start" in readme
        assert "Features" in readme

    def test_readme_includes_badges(self, configured_fsa):
        """Test that README includes version and other badges."""
        readme = configured_fsa.create_readme({})

        assert "1.2.3" in readme
        assert "badge" in readme.lower()
        assert "Python" in readme

    def test_readme_table_of_contents(self, configured_fsa):
        """Test README includes table of contents."""
        readme = configured_fsa.create_readme({})

        assert "Table of Contents" in readme
        assert "#installation" in readme.lower()
        assert "#usage" in readme.lower()


class TestArchitectureDiagramGeneration:
    """Test suite for architecture diagram generation."""

    def test_generate_mermaid_diagram(self, default_fsa):
        """Test Mermaid diagram generation."""
        dependencies = {
            "module_a": ["module_b", "module_c"],
            "module_b": ["module_d"],
            "module_c": ["module_d"],
            "module_d": []
        }

        diagram = default_fsa.generate_architecture_diagram(dependencies)

        assert "graph TD" in diagram
        assert "module_a" in diagram
        assert "-->" in diagram

    def test_diagram_handles_complex_dependencies(self, default_fsa):
        """Test diagram with complex dependency graph."""
        dependencies = {
            "core.utils": ["core.base", "external.lib"],
            "core.models": ["core.base"],
            "api.routes": ["core.models", "core.utils"],
            "core.base": []
        }

        diagram = default_fsa.generate_architecture_diagram(dependencies)

        assert all(module.replace(".", "_") in diagram for module in dependencies.keys())


class TestTutorialGeneration:
    """Test suite for tutorial generation."""

    def test_create_tutorial_basic(self, configured_fsa):
        """Test basic tutorial creation."""
        code_examples = [
            "from test_project import Agent\nagent = Agent()\nresult = agent.run()",
            "from test_project import DataProcessor\nprocessor = DataProcessor()\ndata = processor.load('file.csv')"
        ]

        tutorial = configured_fsa.create_tutorial(code_examples)

        assert "Tutorial" in tutorial
        assert "Prerequisites" in tutorial
        assert "Example 1" in tutorial
        assert "Example 2" in tutorial

    def test_tutorial_includes_code_blocks(self, configured_fsa):
        """Test tutorial includes properly formatted code blocks."""
        code_examples = ["print('Hello, World!')"]

        tutorial = configured_fsa.create_tutorial(code_examples)

        assert "```python" in tutorial
        assert "Hello, World!" in tutorial


class TestChangelogGeneration:
    """Test suite for changelog generation."""

    def test_generate_changelog_structure(self, default_fsa, sample_commits):
        """Test changelog structure and format."""
        changelog = default_fsa.generate_changelog(sample_commits)

        assert "# Changelog" in changelog
        assert "Keep a Changelog" in changelog
        assert "Semantic Versioning" in changelog

    def test_changelog_categorizes_commits(self, default_fsa, sample_commits):
        """Test that commits are properly categorized."""
        changelog = default_fsa.generate_changelog(sample_commits)

        assert "### Added" in changelog
        assert "### Fixed" in changelog
        assert "user authentication" in changelog.lower()

    def test_changelog_version_grouping(self, configured_fsa, sample_commits):
        """Test commits are grouped by version."""
        changelog = configured_fsa.generate_changelog(sample_commits)

        assert "1.2.3" in changelog


class TestOpenAPISpecGeneration:
    """Test suite for OpenAPI specification generation."""

    def test_create_openapi_spec_structure(self, configured_fsa, sample_api_routes):
        """Test OpenAPI spec has correct structure."""
        spec = configured_fsa.create_openapi_spec(sample_api_routes)

        assert spec["openapi"] == "3.0.0"
        assert "info" in spec
        assert "paths" in spec
        assert "components" in spec

    def test_openapi_spec_info_section(self, configured_fsa, sample_api_routes):
        """Test OpenAPI info section contains correct data."""
        spec = configured_fsa.create_openapi_spec(sample_api_routes)

        info = spec["info"]
        assert info["title"] == "Test Project"
        assert info["version"] == "1.2.3"
        assert info["description"] == "A test project for documentation generation"

    def test_openapi_spec_paths(self, configured_fsa, sample_api_routes):
        """Test OpenAPI paths are correctly generated."""
        spec = configured_fsa.create_openapi_spec(sample_api_routes)

        paths = spec["paths"]
        assert "/users" in paths
        assert "/users/{user_id}" in paths
        assert "get" in paths["/users"]


class TestCodeExampleExtraction:
    """Test suite for code example extraction."""

    def test_extract_from_docstring(self, default_fsa):
        """Test extraction of code examples from docstrings."""
        code = '''
def example():
    """
    Example function.

    ```python
    result = example()
    print(result)
    ```
    """
    pass
'''
        examples = default_fsa.extract_code_examples(code)

        assert len(examples) >= 1
        assert "example()" in examples[0]

    def test_extract_doctest_examples(self, default_fsa, sample_python_code):
        """Test extraction of doctest-style examples."""
        examples = default_fsa.extract_code_examples(sample_python_code)

        # Should find the >>> example in helper_function
        assert len(examples) >= 1

    def test_extract_multiple_examples(self, default_fsa):
        """Test extraction of multiple code examples."""
        code = '''
"""
Example 1:
    from module import func
    func()

Example 2:
    from module import other
    other.run()
"""
'''
        examples = default_fsa.extract_code_examples(code)

        assert len(examples) >= 2


class TestCrossReferenceGeneration:
    """Test suite for cross-reference generation."""

    def test_generate_cross_references(self, default_fsa, sample_python_code):
        """Test cross-reference generation."""
        tree = ast.parse(sample_python_code)
        result = default_fsa.generate_api_docs(tree)

        cross_refs = result["cross_references"]

        assert isinstance(cross_refs, dict)

    def test_cross_ref_detects_references(self, default_fsa):
        """Test that cross-references detect mentions in docstrings."""
        code = '''
class Manager:
    """Manager uses Worker to process tasks."""
    pass

class Worker:
    """Worker processes tasks."""
    pass
'''
        tree = ast.parse(code)
        result = default_fsa.generate_api_docs(tree)

        cross_refs = result["cross_references"]

        # Manager should reference Worker
        if "Manager" in cross_refs:
            assert any("Worker" in ref for ref in cross_refs["Manager"])


class TestMultiFormatOutput:
    """Test suite for multi-format output generation."""

    def test_format_markdown(self, default_fsa):
        """Test Markdown output formatting."""
        content = "# Test\n\nThis is **bold** text."
        result = default_fsa.format_output(content, "markdown")

        assert result == content

    def test_format_html(self, default_fsa):
        """Test HTML output formatting."""
        content = "# Test Heading\n\nParagraph text."
        result = default_fsa.format_output(content, "html")

        assert "<h1>" in result or "<h2>" in result
        assert "<!DOCTYPE html>" in result

    def test_format_rst(self, default_fsa):
        """Test reStructuredText output formatting."""
        content = "# Test\n\nParagraph."
        result = default_fsa.format_output(content, "rst")

        assert "===" in result or "---" in result

    def test_format_json(self, default_fsa):
        """Test JSON output formatting."""
        content = "Test content"
        result = default_fsa.format_output(content, "json")

        parsed = json.loads(result)
        assert "content" in parsed
        assert parsed["content"] == content


class TestVersionTracking:
    """Test suite for version-aware documentation."""

    def test_version_in_config(self, configured_fsa):
        """Test version tracking in configuration."""
        assert configured_fsa.config.project_version == "1.2.3"

    def test_version_validation(self, default_fsa):
        """Test semantic version validation."""
        default_fsa.config.project_version = "1.2.3"
        assert default_fsa.validate()

        default_fsa.config.project_version = "invalid"
        assert not default_fsa.validate()

    def test_version_in_openapi(self, configured_fsa, sample_api_routes):
        """Test version appears in OpenAPI spec."""
        spec = configured_fsa.create_openapi_spec(sample_api_routes)

        assert spec["info"]["version"] == "1.2.3"


class TestErrorHandling:
    """Test suite for error handling."""

    def test_error_handling_structure(self, default_fsa):
        """Test error handling returns proper structure."""
        exception = ValueError("Test error")
        error_info = default_fsa.error_handling(exception)

        assert "error_type" in error_info
        assert "error_message" in error_info
        assert "timestamp" in error_info
        assert error_info["error_type"] == "ValueError"

    def test_execute_invalid_path(self, default_fsa):
        """Test execution with invalid source path."""
        with pytest.raises(FileNotFoundError):
            default_fsa.execute("/nonexistent/path.py")

    def test_execute_invalid_format(self, default_fsa):
        """Test execution with invalid output format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Empty file")
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                default_fsa.execute(temp_path, "invalid_format")
        finally:
            Path(temp_path).unlink()


class TestTypeHintDocumentation:
    """Test suite for type hint documentation."""

    def test_type_hints_in_parameters(self, default_fsa):
        """Test type hints are documented in parameters."""
        code = '''
def typed_func(name: str, count: int, optional: Optional[bool] = None) -> List[str]:
    """Function with type hints."""
    return [name] * count
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        result = default_fsa._document_function(func_node)

        assert len(result.parameters) == 3
        assert any("str" in param["type"] for param in result.parameters)
        assert any("int" in param["type"] for param in result.parameters)

    def test_return_type_documented(self, default_fsa):
        """Test return type hints are documented."""
        code = '''
def returns_dict() -> Dict[str, Any]:
    """Returns a dictionary."""
    return {}
'''
        tree = ast.parse(code)
        func_node = tree.body[0]
        result = default_fsa._document_function(func_node)

        assert result.returns is not None
        assert "Dict" in result.returns["type"]


class TestMultiLanguageSupport:
    """Test suite for multi-language documentation support."""

    def test_language_configuration(self, configured_fsa):
        """Test multi-language configuration."""
        assert "en" in configured_fsa.config.supported_languages
        assert "es" in configured_fsa.config.supported_languages
        assert configured_fsa.config.default_language == "en"

    def test_html_lang_attribute(self, configured_fsa):
        """Test HTML output includes language attribute."""
        content = "# Test"
        result = configured_fsa.format_output(content, "html")

        assert f'lang="{configured_fsa.config.default_language}"' in result


class TestValidation:
    """Test suite for FSA validation."""

    def test_validate_success(self, configured_fsa):
        """Test validation passes with valid config."""
        assert configured_fsa.validate()

    def test_validate_invalid_version(self, default_fsa):
        """Test validation fails with invalid version."""
        default_fsa.config.project_version = "not-a-version"
        assert not default_fsa.validate()

    def test_validate_missing_project_name(self, default_fsa):
        """Test validation fails without project name."""
        default_fsa.config.project_name = ""
        assert not default_fsa.validate()

    def test_validate_invalid_output_format(self, default_fsa):
        """Test validation fails with invalid output format."""
        default_fsa.config.output_formats = ["invalid_format"]
        assert not default_fsa.validate()


class TestPerformanceOptimization:
    """Test suite for performance optimization features."""

    def test_ast_caching(self, default_fsa):
        """Test AST modules are cached for performance."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_path = f.name

        try:
            # Parse once
            module1 = default_fsa._parse_python_file(temp_path)

            # Should hit cache on second parse
            module2 = default_fsa._parse_python_file(temp_path)

            assert temp_path in default_fsa.ast_cache
            assert module1 is module2  # Same object from cache

        finally:
            Path(temp_path).unlink()

    def test_execute_complete_workflow(self, configured_fsa, sample_python_code):
        """Test complete execution workflow for performance."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(sample_python_code)
            temp_path = f.name

        try:
            # Execute complete documentation generation
            result = configured_fsa.execute(temp_path, "markdown")

            assert len(result) > 0
            assert "Module Documentation" in result

        finally:
            Path(temp_path).unlink()

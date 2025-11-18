"""
Comprehensive unit tests for TestGeneratorFSA.

This test module provides thorough coverage of the Test Generator FSA,
testing all major functionality including unit test generation, integration
test scaffolding, property-based test creation, mock generation, and more.
"""

import ast
import pytest
from unittest.mock import Mock, patch, MagicMock

from agno.fsas.testing.test_generator_fsa import (
    TestGeneratorFSA,
    TestType,
    AssertionStyle,
    FunctionMetadata,
    TestCase,
)


class TestTestGeneratorFSAInitialization:
    """Test TestGeneratorFSA initialization and configuration."""

    def test_default_initialization(self):
        """Test FSA initializes with default parameters."""
        fsa = TestGeneratorFSA()

        assert fsa.assertion_style == AssertionStyle.PYTEST
        assert fsa.framework == "pytest"
        assert fsa.coverage_threshold == 80.0
        assert fsa.max_test_cases_per_function == 10
        assert fsa.include_edge_cases is True
        assert fsa.use_hypothesis is True
        assert fsa.use_faker is True
        assert fsa.optimize_suite is True

    def test_custom_initialization(self):
        """Test FSA initializes with custom parameters."""
        fsa = TestGeneratorFSA(
            assertion_style=AssertionStyle.UNITTEST,
            framework="unittest",
            coverage_threshold=90.0,
            max_test_cases_per_function=5,
            include_edge_cases=False,
            use_hypothesis=False,
            use_faker=False,
            optimize_suite=False
        )

        assert fsa.assertion_style == AssertionStyle.UNITTEST
        assert fsa.framework == "unittest"
        assert fsa.coverage_threshold == 90.0
        assert fsa.max_test_cases_per_function == 5
        assert fsa.include_edge_cases is False
        assert fsa.use_hypothesis is False
        assert fsa.use_faker is False
        assert fsa.optimize_suite is False

    def test_validation_success(self):
        """Test validation succeeds with valid configuration."""
        fsa = TestGeneratorFSA()
        assert fsa.validate() is True

    def test_validation_failure_invalid_coverage(self):
        """Test validation fails with invalid coverage threshold."""
        fsa = TestGeneratorFSA(coverage_threshold=150.0)
        assert fsa.validate() is False

        fsa2 = TestGeneratorFSA(coverage_threshold=-10.0)
        assert fsa2.validate() is False

    def test_validation_failure_invalid_max_tests(self):
        """Test validation fails with invalid max test cases."""
        fsa = TestGeneratorFSA(max_test_cases_per_function=0)
        assert fsa.validate() is False


class TestUnitTestGeneration:
    """Test unit test generation functionality."""

    def test_generate_unit_tests_simple_function(self):
        """Test unit test generation for simple function."""
        source_code = """
def add(a, b):
    '''Add two numbers.'''
    return a + b
"""
        fsa = TestGeneratorFSA()
        result = fsa.execute(source_code, "unit")

        assert "import pytest" in result
        assert "class TestGeneratedSuite" in result
        assert "test_add" in result

    def test_generate_unit_tests_with_edge_cases(self):
        """Test unit test generation includes edge cases."""
        source_code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        fsa = TestGeneratorFSA(include_edge_cases=True)
        result = fsa.execute(source_code, "unit")

        assert "test_divide_edge_cases" in result
        assert "test_divide_error_conditions" in result

    def test_generate_unit_tests_multiple_functions(self):
        """Test unit test generation for multiple functions."""
        source_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
"""
        fsa = TestGeneratorFSA()
        result = fsa.execute(source_code, "unit")

        assert "test_add" in result
        assert "test_subtract" in result
        assert "test_multiply" in result

    def test_generate_unit_tests_class_methods(self):
        """Test unit test generation for class methods."""
        source_code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        fsa = TestGeneratorFSA()
        module = ast.parse(source_code)
        test_methods = fsa.generate_unit_tests(module)

        assert len(test_methods) > 0
        assert any("test_add" in test for test in test_methods)
        assert any("test_subtract" in test for test in test_methods)


class TestIntegrationTestGeneration:
    """Test integration test scaffolding generation."""

    def test_generate_integration_tests_basic(self):
        """Test basic integration test generation."""
        api_spec = {
            "endpoints": [
                {"method": "GET", "path": "/users", "name": "get_users"},
                {"method": "POST", "path": "/users", "name": "create_user"}
            ],
            "has_database": True
        }

        fsa = TestGeneratorFSA()
        result = fsa.generate_integration_tests(api_spec)

        assert "class TestIntegration" in result
        assert "test_get_get_users" in result
        assert "test_post_create_user" in result
        assert "test_database_connection" in result

    def test_generate_integration_tests_no_database(self):
        """Test integration test generation without database."""
        api_spec = {
            "endpoints": [
                {"method": "GET", "path": "/health", "name": "health_check"}
            ],
            "has_database": False
        }

        fsa = TestGeneratorFSA()
        result = fsa.generate_integration_tests(api_spec)

        assert "class TestIntegration" in result
        assert "test_database_connection" not in result

    def test_integration_test_from_source_code(self):
        """Test integration test generation from source code."""
        source_code = """
def api_handler():
    pass
"""
        fsa = TestGeneratorFSA()
        result = fsa.execute(source_code, "integration")

        assert "class TestIntegration" in result


class TestPropertyBasedTestGeneration:
    """Test property-based test generation."""

    def test_generate_property_tests_enabled(self):
        """Test property-based test generation when enabled."""
        function_signature = "def add(a: int, b: int) -> int:"

        fsa = TestGeneratorFSA(use_hypothesis=True)
        result = fsa.generate_property_tests(function_signature)

        assert "from hypothesis import given" in result
        assert "strategies as st" in result
        assert "test_add_properties" in result
        assert "test_add_idempotency" in result

    def test_generate_property_tests_disabled(self):
        """Test property-based test generation when disabled."""
        function_signature = "def add(a: int, b: int) -> int:"

        fsa = TestGeneratorFSA(use_hypothesis=False)
        result = fsa.generate_property_tests(function_signature)

        assert "Property-based testing disabled" in result

    def test_generate_property_tests_complex_types(self):
        """Test property-based test generation with complex types."""
        function_signature = "def process_list(items: list, threshold: float) -> bool:"

        fsa = TestGeneratorFSA(use_hypothesis=True)
        result = fsa.generate_property_tests(function_signature)

        assert "TestProperties_process_list" in result
        assert "@given" in result


class TestMockObjectGeneration:
    """Test mock object generation functionality."""

    def test_create_mock_objects_single_dependency(self):
        """Test mock generation for single dependency."""
        dependencies = ["DatabaseConnection"]

        fsa = TestGeneratorFSA()
        result = fsa.create_mock_objects(dependencies)

        assert "class MockDatabaseConnection" in result
        assert "@pytest.fixture" in result
        assert "def mock_databaseconnection()" in result

    def test_create_mock_objects_multiple_dependencies(self):
        """Test mock generation for multiple dependencies."""
        dependencies = ["Database", "APIClient", "CacheService"]

        fsa = TestGeneratorFSA()
        result = fsa.create_mock_objects(dependencies)

        assert "class MockDatabase" in result
        assert "class MockAPIClient" in result
        assert "class MockCacheService" in result
        assert result.count("@pytest.fixture") == 3

    def test_mock_objects_cached(self):
        """Test that generated mocks are cached."""
        dependencies = ["Service"]

        fsa = TestGeneratorFSA()
        fsa.create_mock_objects(dependencies)

        assert "Service" in fsa._mocks_generated


class TestFixtureGeneration:
    """Test fixture and test data generation."""

    def test_generate_test_fixtures_simple_schema(self):
        """Test fixture generation with simple schema."""
        data_schema = {
            "User": {
                "name": "str",
                "email": "str",
                "age": "int"
            }
        }

        fsa = TestGeneratorFSA(use_faker=True)
        result = fsa.generate_test_fixtures(data_schema)

        assert "class DataFactory" in result
        assert "def create_User" in result
        assert "@pytest.fixture" in result
        assert "def user_data()" in result

    def test_generate_test_fixtures_faker_disabled(self):
        """Test fixture generation without Faker."""
        data_schema = {
            "Product": {
                "name": "str",
                "price": "float"
            }
        }

        fsa = TestGeneratorFSA(use_faker=False)
        result = fsa.generate_test_fixtures(data_schema)

        assert "class DataFactory" in result
        assert "from faker import Faker" not in result

    def test_generate_test_fixtures_multiple_entities(self):
        """Test fixture generation for multiple entities."""
        data_schema = {
            "User": {"name": "str"},
            "Product": {"title": "str"},
            "Order": {"id": "int"}
        }

        fsa = TestGeneratorFSA()
        result = fsa.generate_test_fixtures(data_schema)

        assert "create_User" in result
        assert "create_Product" in result
        assert "create_Order" in result


class TestParametricTestGeneration:
    """Test parameterized test generation."""

    def test_generate_parametric_tests_basic(self):
        """Test parametric test generation with basic test cases."""
        test_cases = [
            {
                "function": "add",
                "inputs": {"a": 1, "b": 2},
                "expected_output": 3
            },
            {
                "function": "add",
                "inputs": {"a": 5, "b": 3},
                "expected_output": 8
            }
        ]

        fsa = TestGeneratorFSA()
        result = fsa.generate_parametric_tests(test_cases)

        assert "@pytest.mark.parametrize" in result
        assert "test_add_parametric" in result
        assert "(1, 2, 3)" in result
        assert "(5, 3, 8)" in result

    def test_generate_parametric_tests_empty_list(self):
        """Test parametric test generation with empty test cases."""
        test_cases = []

        fsa = TestGeneratorFSA()
        result = fsa.generate_parametric_tests(test_cases)

        assert "No test cases provided" in result

    def test_generate_parametric_tests_multiple_functions(self):
        """Test parametric test generation for multiple functions."""
        test_cases = [
            {
                "function": "add",
                "inputs": {"a": 1, "b": 2},
                "expected_output": 3
            },
            {
                "function": "multiply",
                "inputs": {"x": 2, "y": 3},
                "expected_output": 6
            }
        ]

        fsa = TestGeneratorFSA()
        result = fsa.generate_parametric_tests(test_cases)

        assert "test_add_parametric" in result
        assert "test_multiply_parametric" in result


class TestCoverageAnalysis:
    """Test coverage gap analysis functionality."""

    def test_analyze_coverage_gaps_below_threshold(self):
        """Test coverage analysis identifies gaps below threshold."""
        coverage_report = {
            "files": {
                "module.py": {
                    "coverage_percent": 65.0,
                    "missing_lines": [10, 11, 12, 15],
                    "missing_branches": [("20", "21")]
                }
            },
            "functions": {
                "uncovered_function": False,
                "covered_function": True
            }
        }

        fsa = TestGeneratorFSA(coverage_threshold=80.0)
        recommendations = fsa.analyze_coverage_gaps(coverage_report)

        assert len(recommendations) > 0
        assert any("module.py" in rec for rec in recommendations)
        assert any("65.0%" in rec for rec in recommendations)
        assert any("Uncovered lines" in rec for rec in recommendations)

    def test_analyze_coverage_gaps_uncovered_functions(self):
        """Test coverage analysis identifies uncovered functions."""
        coverage_report = {
            "files": {},
            "functions": {
                "function1": False,
                "function2": False,
                "function3": True
            }
        }

        fsa = TestGeneratorFSA()
        recommendations = fsa.analyze_coverage_gaps(coverage_report)

        assert any("Uncovered functions" in rec for rec in recommendations)
        assert any("function1" in rec or "function2" in rec for rec in recommendations)

    def test_analyze_coverage_gaps_suggestions(self):
        """Test coverage analysis provides actionable suggestions."""
        coverage_report = {
            "files": {
                "test_module.py": {
                    "coverage_percent": 70.0,
                    "missing_lines": [5, 6],
                    "missing_branches": []
                }
            },
            "functions": {}
        }

        fsa = TestGeneratorFSA()
        recommendations = fsa.analyze_coverage_gaps(coverage_report)

        assert any("Suggested actions" in rec for rec in recommendations)
        assert any("unit tests" in rec for rec in recommendations)


class TestMutationTestGeneration:
    """Test mutation testing generation."""

    def test_generate_mutation_tests_basic(self):
        """Test mutation test generation for basic code."""
        source_code = """
def add(a, b):
    return a + b

def compare(x, y):
    return x > y
"""
        fsa = TestGeneratorFSA()
        result = fsa.generate_mutation_tests(source_code)

        assert "Mutation Testing Configuration" in result
        assert "MUTATION_CONFIG" in result
        assert "Mutation Points Identified" in result

    def test_generate_mutation_tests_identifies_operators(self):
        """Test mutation testing identifies different operator types."""
        source_code = """
def complex_function(a, b, c):
    if a > b:
        return a + c
    elif a == b:
        return a * c
    else:
        return b - c
"""
        fsa = TestGeneratorFSA()
        result = fsa.generate_mutation_tests(source_code)

        # Should identify various mutation points
        assert "AOR" in result or "ROR" in result or "LOR" in result

    def test_generate_mutation_tests_invalid_code(self):
        """Test mutation test generation with invalid code."""
        source_code = "def broken( syntax error"

        fsa = TestGeneratorFSA()
        result = fsa.generate_mutation_tests(source_code)

        assert "Cannot parse source code" in result


class TestSuiteOptimization:
    """Test test suite optimization functionality."""

    def test_optimize_test_suite_basic(self):
        """Test basic test suite optimization."""
        test_files = ["test_module1.py", "test_module2.py"]

        fsa = TestGeneratorFSA(optimize_suite=True)
        report = fsa.optimize_test_suite(test_files)

        assert "total_tests" in report
        assert "redundant_tests" in report
        assert "recommendations" in report
        assert "estimated_savings" in report

    def test_optimize_test_suite_disabled(self):
        """Test optimization when disabled."""
        test_files = ["test_module.py"]

        fsa = TestGeneratorFSA(optimize_suite=False)
        report = fsa.optimize_test_suite(test_files)

        assert "optimization is disabled" in report["recommendations"][0]

    def test_optimize_test_suite_provides_recommendations(self):
        """Test that optimization provides actionable recommendations."""
        test_files = ["test_a.py", "test_b.py", "test_c.py"]

        fsa = TestGeneratorFSA(optimize_suite=True)
        report = fsa.optimize_test_suite(test_files)

        assert len(report["recommendations"]) > 0
        # Should have performance recommendations
        assert any("fixture" in rec or "parallel" in rec for rec in report["recommendations"])


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_execute_with_empty_source_code(self):
        """Test execution with empty source code raises error."""
        fsa = TestGeneratorFSA()

        with pytest.raises(ValueError, match="Source code cannot be empty"):
            fsa.execute("", "unit")

    def test_execute_with_invalid_test_type(self):
        """Test execution with invalid test type raises error."""
        fsa = TestGeneratorFSA()
        source_code = "def foo(): pass"

        with pytest.raises(ValueError):
            fsa.execute(source_code, "invalid_type")

    def test_error_handling_syntax_error(self):
        """Test error handling for syntax errors."""
        fsa = TestGeneratorFSA()
        error = SyntaxError("invalid syntax")
        error.lineno = 5

        error_info = fsa.error_handling(error)

        assert error_info["type"] == "SyntaxError"
        assert len(error_info["suggestions"]) > 0
        assert "syntax" in error_info["suggestions"][0].lower()

    def test_error_handling_value_error(self):
        """Test error handling for value errors."""
        fsa = TestGeneratorFSA()
        error = ValueError("Invalid parameter")

        error_info = fsa.error_handling(error)

        assert error_info["type"] == "ValueError"
        assert error_info["recoverable"] is True
        assert any("parameter" in s.lower() for s in error_info["suggestions"])

    def test_error_handling_unexpected_error(self):
        """Test error handling for unexpected errors."""
        fsa = TestGeneratorFSA()
        error = RuntimeError("Unexpected error")

        error_info = fsa.error_handling(error)

        assert error_info["type"] == "RuntimeError"
        assert error_info["recoverable"] is False


class TestMultiFrameworkSupport:
    """Test support for multiple testing frameworks."""

    def test_pytest_framework_support(self):
        """Test pytest framework support."""
        source_code = "def add(a, b): return a + b"

        fsa = TestGeneratorFSA(framework="pytest", assertion_style=AssertionStyle.PYTEST)
        result = fsa.execute(source_code, "unit")

        assert "import pytest" in result
        assert "class TestGeneratedSuite" in result

    def test_unittest_framework_support(self):
        """Test unittest framework support."""
        fsa = TestGeneratorFSA(
            framework="unittest",
            assertion_style=AssertionStyle.UNITTEST
        )

        assert fsa.framework == "unittest"
        assert fsa.assertion_style == AssertionStyle.UNITTEST
        assert fsa.validate() is True


class TestTestQualityMetrics:
    """Test quality metrics and validation."""

    def test_function_metadata_extraction(self):
        """Test extraction of function metadata."""
        source_code = '''
def process_data(items: list, threshold: float = 0.5) -> dict:
    """Process items based on threshold."""
    return {"processed": len(items)}
'''
        fsa = TestGeneratorFSA()
        module = ast.parse(source_code)
        fsa._extract_metadata(module)

        assert "process_data" in fsa._function_metadata
        metadata = fsa._function_metadata["process_data"]
        assert metadata.name == "process_data"
        assert "items" in metadata.args
        assert "threshold" in metadata.args
        assert metadata.docstring is not None

    def test_test_naming_conventions(self):
        """Test that generated tests follow naming conventions."""
        source_code = "def calculate_total(prices): return sum(prices)"

        fsa = TestGeneratorFSA()
        result = fsa.execute(source_code, "unit")

        # Test names should follow pattern: test_<function_name>_<scenario>
        assert "test_calculate_total_normal_case" in result
        assert "test_calculate_total_edge_cases" in result or "test_calculate_total" in result

    def test_test_documentation_generation(self):
        """Test that generated tests include documentation."""
        source_code = "def validate_email(email): return '@' in email"

        fsa = TestGeneratorFSA()
        result = fsa.execute(source_code, "unit")

        # Tests should have docstrings
        assert '"""' in result
        # Should describe what is being tested
        assert "validate_email" in result.lower()

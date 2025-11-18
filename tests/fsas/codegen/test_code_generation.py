"""
Comprehensive unit tests for Code Generation FSA.

Tests cover:
- Class generation validation
- Function generation accuracy
- Design pattern application
- Code refactoring correctness
- Test stub generation
- Documentation generation
- Multi-language support
- Error handling for invalid templates
"""

import pytest
from agno.fsas.codegen.code_generation_fsa import (
    CodeGenerationFSA,
    Language,
    DesignPattern,
    RefactoringType,
    GenerationResult,
    ValidationResult
)


class TestClassGeneration:
    """Test suite for class generation functionality."""

    def test_generate_python_class_basic(self):
        """Test basic Python class generation with attributes and methods."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_class(
            name="User",
            attributes=["name", "email", "age"],
            methods=["save", "delete", "update"]
        )

        # Verify class definition
        assert "class User:" in result
        assert "def __init__(self, name, email, age):" in result

        # Verify attributes are assigned
        assert "self.name = name" in result
        assert "self.email = email" in result
        assert "self.age = age" in result

        # Verify methods are defined
        assert "def save(self):" in result
        assert "def delete(self):" in result
        assert "def update(self):" in result

        # Verify docstrings
        assert '"""' in result

    def test_generate_python_class_with_inheritance(self):
        """Test Python class generation with base classes."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_class(
            name="Admin",
            attributes=["permissions"],
            methods=["grant_access"],
            base_classes=["User", "Authenticatable"]
        )

        # Verify inheritance
        assert "class Admin(User, Authenticatable):" in result
        assert "self.permissions = permissions" in result

    def test_generate_javascript_class(self):
        """Test JavaScript class generation."""
        fsa = CodeGenerationFSA(language=Language.JAVASCRIPT)

        result = fsa.generate_class(
            name="Product",
            attributes=["name", "price"],
            methods=["display", "purchase"]
        )

        # Verify JavaScript syntax
        assert "class Product {" in result
        assert "constructor(name, price) {" in result
        assert "this.name = name;" in result
        assert "this.price = price;" in result
        assert "display() {" in result
        assert "purchase() {" in result

    def test_generate_typescript_class(self):
        """Test TypeScript class generation."""
        fsa = CodeGenerationFSA(language=Language.TYPESCRIPT)

        result = fsa.generate_class(
            name="Service",
            attributes=["endpoint", "timeout"],
            methods=["connect", "disconnect"]
        )

        # Verify TypeScript syntax
        assert "class Service {" in result
        assert "private endpoint: any;" in result
        assert "private timeout: any;" in result
        assert "connect(): void {" in result

    def test_generate_java_class(self):
        """Test Java class generation."""
        fsa = CodeGenerationFSA(language=Language.JAVA)

        result = fsa.generate_class(
            name="Customer",
            attributes=["customerId", "name"],
            methods=["register", "unregister"]
        )

        # Verify Java syntax
        assert "public class Customer {" in result
        assert "private Object customerId;" in result
        assert "public Customer(Object customerId, Object name) {" in result
        assert "this.customerId = customerId;" in result
        assert "public void register() {" in result


class TestFunctionGeneration:
    """Test suite for function generation accuracy."""

    def test_generate_python_function_basic(self):
        """Test basic Python function generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_function(
            name="calculate_total",
            params=["items", "tax_rate"],
            return_type="float",
            body="return sum(items) * (1 + tax_rate)"
        )

        # Verify function signature
        assert "def calculate_total(items, tax_rate) -> float:" in result
        assert "return sum(items) * (1 + tax_rate)" in result

    def test_generate_function_with_decorators(self):
        """Test function generation with decorators."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_function(
            name="cached_compute",
            params=["data"],
            return_type="Any",
            body="return process(data)",
            decorators=["lru_cache", "timer"]
        )

        # Verify decorators
        assert "@lru_cache" in result
        assert "@timer" in result
        assert "def cached_compute(data) -> Any:" in result

    def test_generate_async_function(self):
        """Test async function generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_function(
            name="fetch_data",
            params=["url"],
            return_type="dict",
            body="response = await client.get(url)\nreturn response.json()",
            async_func=True
        )

        # Verify async keyword
        assert "async def fetch_data(url) -> dict:" in result
        assert "await client.get(url)" in result

    def test_generate_javascript_function(self):
        """Test JavaScript function generation."""
        fsa = CodeGenerationFSA(language=Language.JAVASCRIPT)

        result = fsa.generate_function(
            name="processData",
            params=["data", "callback"],
            return_type="",
            body="callback(data.map(x => x * 2));"
        )

        # Verify JavaScript syntax
        assert "function processData(data, callback) {" in result
        assert "callback(data.map(x => x * 2));" in result

    def test_generate_typescript_function(self):
        """Test TypeScript function generation with type annotations."""
        fsa = CodeGenerationFSA(language=Language.TYPESCRIPT)

        result = fsa.generate_function(
            name="transform",
            params=["input"],
            return_type="string",
            body="return input.toString();"
        )

        # Verify TypeScript type annotation
        assert "function transform(input): string {" in result
        assert "return input.toString();" in result


class TestDesignPatterns:
    """Test suite for design pattern application."""

    def test_apply_singleton_pattern(self):
        """Test Singleton pattern generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.apply_design_pattern(
            "singleton",
            {"class_name": "DatabaseConnection"}
        )

        # Verify Singleton pattern elements
        assert "class DatabaseConnection:" in result
        assert "_instance = None" in result
        assert "def __new__(cls):" in result
        assert "cls._instance = super().__new__(cls)" in result

    def test_apply_factory_pattern(self):
        """Test Factory pattern generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.apply_design_pattern(
            "factory",
            {
                "factory_name": "VehicleFactory",
                "products": ["Car", "Truck", "Motorcycle"]
            }
        )

        # Verify Factory pattern elements
        assert "class Product(ABC):" in result
        assert "class Car(Product):" in result
        assert "class Truck(Product):" in result
        assert "class Motorcycle(Product):" in result
        assert "class VehicleFactory:" in result
        assert "def create_product(product_type: str) -> Product:" in result

    def test_apply_observer_pattern(self):
        """Test Observer pattern generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.apply_design_pattern(
            "observer",
            {"subject_name": "WeatherStation"}
        )

        # Verify Observer pattern elements
        assert "class Observer(ABC):" in result
        assert "def update(self, subject: 'WeatherStation') -> None:" in result
        assert "class WeatherStation:" in result
        assert "def attach(self, observer: Observer) -> None:" in result
        assert "def detach(self, observer: Observer) -> None:" in result
        assert "def notify(self) -> None:" in result

    def test_apply_strategy_pattern(self):
        """Test Strategy pattern generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.apply_design_pattern(
            "strategy",
            {"strategies": ["QuickSort", "MergeSort", "BubbleSort"]}
        )

        # Verify Strategy pattern elements
        assert "class Strategy(ABC):" in result
        assert "class QuickSort(Strategy):" in result
        assert "class MergeSort(Strategy):" in result
        assert "class Context:" in result
        assert "def set_strategy(self, strategy: Strategy):" in result

    def test_apply_builder_pattern(self):
        """Test Builder pattern generation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.apply_design_pattern(
            "builder",
            {"product_name": "House"}
        )

        # Verify Builder pattern elements
        assert "class House:" in result
        assert "class Builder:" in result
        assert "def build_part_a(self) -> 'Builder':" in result
        assert "def get_product(self) -> House:" in result

    def test_unsupported_pattern_raises_error(self):
        """Test that unsupported pattern raises ValueError."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        with pytest.raises(ValueError, match="Unsupported design pattern"):
            fsa.apply_design_pattern("invalid_pattern", {})


class TestCodeRefactoring:
    """Test suite for code refactoring correctness."""

    def test_refactor_rename_variable(self):
        """Test variable renaming refactoring."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
x = 10
y = x + 5
print(x)
result = x * 2
"""

        result = fsa.refactor_code(
            source,
            "rename_variable",
            old_name="x",
            new_name="value"
        )

        # Verify variable is renamed
        assert "value = 10" in result
        assert "y = value + 5" in result
        assert "print(value)" in result
        assert "result = value * 2" in result
        # Ensure y is not renamed
        assert "y = " in result

    def test_refactor_extract_method(self):
        """Test method extraction refactoring."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """class Calculator:
    def complex_operation(self):
        result = 0
        result += 10
        result *= 2
        return result
"""

        result = fsa.refactor_code(
            source,
            "extract_method",
            method_name="calculate",
            start_line=3,
            end_line=5
        )

        # Verify method extraction
        assert "def calculate(self):" in result
        assert "self.calculate()" in result

    def test_refactor_inline_variable(self):
        """Test variable inlining refactoring."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
temp = 10 * 2
result = temp + 5
print(temp)
"""

        result = fsa.refactor_code(
            source,
            "inline_variable",
            variable_name="temp"
        )

        # Verify variable is inlined
        assert "result = 10 * 2 + 5" in result or "10 * 2" in result
        assert "print(10 * 2)" in result

    def test_unsupported_refactoring_type(self):
        """Test unsupported refactoring type raises error."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        with pytest.raises(ValueError, match="Unsupported refactoring type"):
            fsa.refactor_code("code", "invalid_refactoring")


class TestTestGeneration:
    """Test suite for test stub generation."""

    def test_generate_tests_for_functions(self):
        """Test generation of test stubs for functions."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b
"""

        result = fsa.generate_tests(source, test_framework="pytest")

        # Verify test structure
        assert "import pytest" in result
        assert "def test_add():" in result
        assert "def test_subtract():" in result
        assert "def test_multiply():" in result
        assert "# Arrange" in result
        assert "# Act" in result
        assert "# Assert" in result

    def test_generate_tests_for_classes(self):
        """Test generation of test stubs for classes."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
class Calculator:
    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        return a / b
"""

        result = fsa.generate_tests(source, test_framework="pytest")

        # Verify test class structure
        assert "class TestCalculator:" in result
        assert "def test_add(self):" in result
        assert "def test_divide(self):" in result

    def test_generate_tests_empty_source(self):
        """Test test generation with no testable code."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = "# Just a comment"
        result = fsa.generate_tests(source)

        # Should return import statement with no tests or a message
        assert "pytest" in result or "No testable" in result


class TestDocumentationGeneration:
    """Test suite for documentation generation."""

    def test_generate_docs_for_function(self):
        """Test documentation generation for functions."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
def calculate(x, y):
    return x + y
"""

        result = fsa.generate_docs(source, style="google")

        # Verify docstring is added
        assert '"""' in result
        assert "calculate function" in result

    def test_generate_docs_for_class(self):
        """Test documentation generation for classes."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = """
class DataProcessor:
    def process(self, data):
        return data
"""

        result = fsa.generate_docs(source)

        # Verify docstrings are present
        assert '"""' in result

    def test_generate_docs_preserves_existing(self):
        """Test that existing docstrings are preserved."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        source = '''
def documented():
    """Already documented."""
    pass
'''

        result = fsa.generate_docs(source)

        # Should keep existing docstring
        assert "Already documented." in result


class TestTemplateExecution:
    """Test suite for template-based code generation."""

    def test_execute_simple_template(self):
        """Test execution of simple template."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        template = "def {{ name }}(): pass"
        result = fsa.execute(template, {"name": "hello_world"})

        assert result == "def hello_world(): pass"

    def test_execute_complex_template(self):
        """Test execution of complex template with loops."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        template = """
class {{ class_name }}:
    {% for attr in attributes %}
    {{ attr }} = None
    {% endfor %}
"""

        result = fsa.execute(template, {
            "class_name": "Config",
            "attributes": ["host", "port", "debug"]
        })

        assert "class Config:" in result
        assert "host = None" in result
        assert "port = None" in result
        assert "debug = None" in result

    def test_execute_template_with_undefined_variable(self):
        """Test template execution with undefined variable."""
        fsa = CodeGenerationFSA(language=Language.PYTHON, strict_mode=False)

        template = "def {{ undefined_var }}(): pass"
        result = fsa.execute(template, {})

        # Should render with empty string for undefined vars in sandboxed mode
        # or return error message
        assert "def " in result  # Basic validation that template was processed

    def test_execute_template_syntax_error(self):
        """Test template execution with syntax error."""
        fsa = CodeGenerationFSA(language=Language.PYTHON, strict_mode=False)

        template = "def {{ name }(): pass"  # Missing closing brace
        result = fsa.execute(template, {"name": "test"})

        # Should handle syntax error gracefully
        assert "Error" in result or "syntax" in result.lower()


class TestErrorHandling:
    """Test suite for error handling."""

    def test_error_handling_template_syntax_error(self):
        """Test error handling for template syntax errors."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        from jinja2 import TemplateSyntaxError
        error = TemplateSyntaxError("Invalid syntax", lineno=5)

        result = fsa.error_handling(error)

        assert result['error_type'] == 'TemplateSyntaxError'
        assert len(result['suggestions']) > 0
        assert 'template syntax' in result['suggestions'][0].lower()

    def test_error_handling_value_error(self):
        """Test error handling for value errors."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        error = ValueError("Invalid parameter")

        result = fsa.error_handling(error)

        assert result['error_type'] == 'ValueError'
        assert 'input parameters' in result['suggestions'][0].lower()

    def test_error_handling_syntax_error(self):
        """Test error handling for Python syntax errors."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        try:
            compile("def invalid syntax", "<string>", "exec")
        except SyntaxError as error:
            result = fsa.error_handling(error)

            assert result['error_type'] == 'SyntaxError'
            assert 'syntax errors' in result['suggestions'][0].lower()
            assert 'line' in result['context']


class TestValidation:
    """Test suite for FSA validation."""

    def test_validate_success(self):
        """Test successful validation."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        assert fsa.validate() is True

    def test_validate_checks_templates(self):
        """Test validation checks templates."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)
        fsa.templates = {}  # Clear templates

        assert fsa.validate() is False

    def test_validate_checks_environment(self):
        """Test validation checks environment."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)
        fsa.env = None

        assert fsa.validate() is False


class TestMultiLanguageSupport:
    """Test suite for multi-language support."""

    def test_python_language_support(self):
        """Test Python language support."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        result = fsa.generate_function(
            "test_func",
            ["arg1"],
            "str",
            "return str(arg1)"
        )

        assert "def test_func(arg1) -> str:" in result

    def test_javascript_language_support(self):
        """Test JavaScript language support."""
        fsa = CodeGenerationFSA(language=Language.JAVASCRIPT)

        result = fsa.generate_function(
            "testFunc",
            ["arg1"],
            "",
            "return arg1.toString();"
        )

        assert "function testFunc(arg1)" in result

    def test_typescript_language_support(self):
        """Test TypeScript language support."""
        fsa = CodeGenerationFSA(language=Language.TYPESCRIPT)

        result = fsa.generate_function(
            "testFunc",
            ["arg1"],
            "string",
            "return arg1.toString();"
        )

        assert "function testFunc(arg1): string" in result

    def test_java_language_support(self):
        """Test Java language support."""
        fsa = CodeGenerationFSA(language=Language.JAVA)

        result = fsa.generate_function(
            "testMethod",
            ["arg1"],
            "String",
            "return arg1.toString();"
        )

        assert "public String testMethod(Object arg1)" in result

    def test_language_switching(self):
        """Test switching between languages."""
        fsa = CodeGenerationFSA(language=Language.PYTHON)

        # Generate Python code
        py_result = fsa.generate_class(
            "TestClass",
            ["attr1"],
            ["method1"],
            language=Language.PYTHON
        )
        assert "class TestClass:" in py_result

        # Generate JavaScript code
        js_result = fsa.generate_class(
            "TestClass",
            ["attr1"],
            ["method1"],
            language=Language.JAVASCRIPT
        )
        assert "class TestClass {" in js_result

        # Verify they're different
        assert py_result != js_result

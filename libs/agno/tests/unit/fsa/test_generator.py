"""Tests for FSA Generator."""

import ast
import tempfile
from pathlib import Path

import pytest
from agno.fsa.generator import FSAGeneratorFSA, FSASpecification


class TestFSASpecification:
    """Tests for FSASpecification."""

    def test_specification_initialization(self):
        """Test FSASpecification initialization."""
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test FSA for testing"
        )
        assert spec.name == "TestFSA"
        assert spec.purpose == "Test FSA for testing"
        assert "initial" in spec.states
        assert spec.stateful is True
        assert spec.cascade_aware is False

    def test_specification_with_custom_states(self):
        """Test FSASpecification with custom states."""
        states = {"start", "middle", "end"}
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            states=states
        )
        assert spec.states == states

    def test_specification_with_methods(self):
        """Test FSASpecification with methods."""
        methods = [
            {"name": "process_data", "params": [], "return_type": "str"}
        ]
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            methods=methods
        )
        assert len(spec.methods) == 1
        assert spec.methods[0]["name"] == "process_data"

    def test_specification_with_dependencies(self):
        """Test FSASpecification with dependencies."""
        deps = ["json", "requests"]
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            dependencies=deps
        )
        assert spec.dependencies == deps

    def test_specification_with_transitions(self):
        """Test FSASpecification with custom transitions."""
        transitions = [
            {"from_state": "initial", "to_state": "processing"}
        ]
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            custom_transitions=transitions
        )
        assert len(spec.custom_transitions) == 1


class TestFSAGeneratorFSA:
    """Tests for FSAGeneratorFSA."""

    def test_generator_initialization(self):
        """Test FSAGeneratorFSA initialization."""
        generator = FSAGeneratorFSA()
        assert generator.name == "FSAGeneratorFSA"
        assert generator.current_state == "initial"
        assert "validating" in generator.states
        assert "generating" in generator.states
        assert "writing" in generator.states

    def test_generator_has_correct_states(self):
        """Test generator has correct states."""
        generator = FSAGeneratorFSA()
        expected_states = {
            "initial", "validating", "generating",
            "writing", "completed", "error"
        }
        assert generator.states == expected_states

    def test_generator_transitions_defined(self):
        """Test generator has transitions defined."""
        generator = FSAGeneratorFSA()
        assert len(generator.transitions) > 0

    def test_validate_fsa_valid_specification(self):
        """Test validate_fsa with valid specification."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test FSA"
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is True

    def test_validate_fsa_missing_name(self):
        """Test validate_fsa with missing name."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="", purpose="Test")
        result = generator.validate_fsa(spec)
        assert result["valid"] is False
        assert "name is required" in result["error"]

    def test_validate_fsa_invalid_name_format(self):
        """Test validate_fsa with invalid name format."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="test_fsa", purpose="Test")
        result = generator.validate_fsa(spec)
        assert result["valid"] is False

    def test_validate_fsa_name_without_fsa_suffix(self):
        """Test validate_fsa with name not ending in FSA."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestAgent", purpose="Test")
        result = generator.validate_fsa(spec)
        assert result["valid"] is False
        assert "must end with 'FSA'" in result["error"]

    def test_validate_fsa_missing_purpose(self):
        """Test validate_fsa with missing purpose."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="")
        result = generator.validate_fsa(spec)
        assert result["valid"] is False

    def test_validate_fsa_no_states(self):
        """Test validate_fsa with no states."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            states=set()
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is False

    def test_validate_fsa_missing_initial_state(self):
        """Test validate_fsa with missing initial state."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            states={"processing", "completed"}
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is False
        assert "initial" in result["error"]

    def test_validate_fsa_invalid_method_name(self):
        """Test validate_fsa with invalid method name."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            methods=[{"name": "ProcessData"}]  # Should be snake_case
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is False
        assert "snake_case" in result["error"]

    def test_validate_fsa_method_without_name(self):
        """Test validate_fsa with method without name."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            methods=[{"params": []}]
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is False

    def test_validate_fsa_invalid_transition(self):
        """Test validate_fsa with invalid transition."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            custom_transitions=[{"from_state": "nonexistent", "to_state": "initial"}]
        )
        result = generator.validate_fsa(spec)
        assert result["valid"] is False

    def test_create_template(self):
        """Test create_template method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test FSA"
        )
        template = generator.create_template(spec)
        assert "TestFSA" in template
        assert "from agno.fsa.base import FSA" in template
        assert "def run(self" in template

    def test_create_template_with_methods(self):
        """Test create_template with custom methods."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            methods=[
                {
                    "name": "process_data",
                    "params": [{"name": "data", "type": "str"}],
                    "return_type": "str",
                    "docstring": "Process data"
                }
            ]
        )
        template = generator.create_template(spec)
        assert "def process_data" in template
        assert "data: str" in template

    def test_create_template_with_dependencies(self):
        """Test create_template with dependencies."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            dependencies=["json", "os"]
        )
        template = generator.create_template(spec)
        assert "import json" in template
        assert "import os" in template

    def test_customize_code(self):
        """Test customize_code method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test")
        template = generator.create_template(spec)
        customized = generator.customize_code(template, spec)
        assert isinstance(customized, str)
        assert len(customized) > 0

    def test_validate_generated_code(self):
        """Test _validate_generated_code with valid code."""
        generator = FSAGeneratorFSA()
        valid_code = "def foo():\n    pass"
        generator._validate_generated_code(valid_code)  # Should not raise

    def test_validate_generated_code_invalid(self):
        """Test _validate_generated_code with invalid code."""
        generator = FSAGeneratorFSA()
        invalid_code = "def foo(\n    pass"  # Missing closing parenthesis
        with pytest.raises(SyntaxError):
            generator._validate_generated_code(invalid_code)

    def test_generate_fsa(self):
        """Test generate_fsa method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test FSA")
        code = generator.generate_fsa(spec)
        assert isinstance(code, str)
        assert "TestFSA" in code
        # Validate syntax
        ast.parse(code)

    def test_generate_tests(self):
        """Test generate_tests method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test FSA")
        tests = generator.generate_tests(spec)
        assert isinstance(tests, str)
        assert "TestTestFSA" in tests
        assert "import pytest" in tests
        assert "def test_" in tests

    def test_generate_tests_with_custom_methods(self):
        """Test generate_tests with custom methods."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="TestFSA",
            purpose="Test",
            methods=[{"name": "custom_method"}]
        )
        tests = generator.generate_tests(spec)
        assert "test_custom_method_exists" in tests

    def test_to_snake_case(self):
        """Test _to_snake_case conversion."""
        generator = FSAGeneratorFSA()
        assert generator._to_snake_case("TestFSA") == "test_fsa"
        assert generator._to_snake_case("MyCustomFSA") == "my_custom_fsa"
        assert generator._to_snake_case("FSA") == "fsa"

    def test_write_files(self):
        """Test write_files method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = FSAGeneratorFSA(
                output_dir=Path(tmpdir) / "fsa",
                test_output_dir=Path(tmpdir) / "tests"
            )
            spec = FSASpecification(name="TestFSA", purpose="Test")
            code = generator.generate_fsa(spec)
            tests = generator.generate_tests(spec)

            files = generator.write_files(spec, code, tests)

            assert len(files) > 0
            assert any("test_fsa.py" in f for f in files)
            assert any("test_test_fsa.py" in f for f in files)

    def test_run_full_generation(self):
        """Test full FSA generation run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = FSAGeneratorFSA(
                output_dir=Path(tmpdir) / "fsa",
                test_output_dir=Path(tmpdir) / "tests"
            )
            spec = FSASpecification(
                name="CustomFSA",
                purpose="Custom test FSA",
                states={"initial", "processing", "completed", "error"}
            )

            result = generator.run(spec)

            assert result["success"] is True
            assert result["fsa_name"] == "CustomFSA"
            assert len(result["generated_files"]) > 0
            assert "code" in result
            assert "tests" in result
            assert generator.current_state == "completed"

    def test_run_with_invalid_specification(self):
        """Test run with invalid specification."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="InvalidName", purpose="Test")
        result = generator.run(spec)

        assert result["success"] is False
        assert "error" in result
        assert generator.current_state == "error"

    def test_run_state_transitions(self):
        """Test run method state transitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = FSAGeneratorFSA(
                output_dir=Path(tmpdir) / "fsa",
                test_output_dir=Path(tmpdir) / "tests"
            )
            spec = FSASpecification(name="TestFSA", purpose="Test")

            assert generator.current_state == "initial"
            generator.run(spec)
            assert generator.current_state == "completed"
            assert len(generator.transition_history) > 0

    def test_format_code(self):
        """Test _format_code method."""
        generator = FSAGeneratorFSA()
        code_with_blanks = "line1\n\n\n\n\nline2"
        formatted = generator._format_code(code_with_blanks)
        # Should reduce excessive blank lines
        assert formatted.count("\n\n\n") == 0

    def test_build_class_definition(self):
        """Test _build_class_definition method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test FSA")
        class_def = generator._build_class_definition(spec)
        assert "class TestFSA(FSA):" in class_def
        assert "@dataclass" in class_def

    def test_build_post_init(self):
        """Test _build_post_init method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test")
        post_init = generator._build_post_init(spec)
        assert "def __post_init__" in post_init
        assert "self.add_transition" in post_init

    def test_build_run_method(self):
        """Test _build_run_method method."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test")
        run_method = generator._build_run_method(spec)
        assert "def run(self" in run_method
        assert "self.transition" in run_method

    def test_generated_code_syntax_valid(self):
        """Test generated code has valid Python syntax."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(
            name="SyntaxTestFSA",
            purpose="Test syntax validation",
            methods=[
                {
                    "name": "test_method",
                    "params": [{"name": "arg1", "type": "str"}],
                    "return_type": "bool"
                }
            ]
        )
        code = generator.generate_fsa(spec)
        # This should not raise SyntaxError
        ast.parse(code)

    def test_generated_tests_syntax_valid(self):
        """Test generated tests have valid Python syntax."""
        generator = FSAGeneratorFSA()
        spec = FSASpecification(name="TestFSA", purpose="Test")
        tests = generator.generate_tests(spec)
        # This should not raise SyntaxError
        ast.parse(tests)

    def test_multiple_generations(self):
        """Test generating multiple FSAs sequentially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = FSAGeneratorFSA(
                output_dir=Path(tmpdir) / "fsa",
                test_output_dir=Path(tmpdir) / "tests"
            )

            spec1 = FSASpecification(name="FirstFSA", purpose="First")
            spec2 = FSASpecification(name="SecondFSA", purpose="Second")

            result1 = generator.run(spec1)
            generator.reset()  # Reset for next generation

            result2 = generator.run(spec2)

            assert result1["success"] is True
            assert result2["success"] is True
            assert result1["fsa_name"] != result2["fsa_name"]

"""
Comprehensive tests for FSA Generator

Tests cover specification parsing, template selection, code generation,
validation, and git integration.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from agno.fsas.generator import (
    CodeValidationError,
    FSACategory,
    FSAGenerator,
    FSAImplementation,
    FSASpecification,
    GitOperationError,
    InvalidSpecificationError,
    ParsedSpec,
    Template,
    TemplateRenderError,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_spec_dict():
    """Sample FSA specification as dictionary"""
    return {
        "name": "TestProcessor",
        "category": "Core",
        "purpose": "Test FSA for unit testing",
        "key_capabilities": [
            "Process test data",
            "Validate test inputs",
            "Generate test outputs"
        ],
        "dependencies": ["pytest", "mock"],
        "complexity_target": "300-500 LOC",
        "custom_methods": {
            "process_data": "Process data for testing",
            "validate_result": "Validate processing result"
        }
    }


@pytest.fixture
def sample_spec_object(sample_spec_dict):
    """Sample FSA specification as FSASpecification object"""
    return FSASpecification(**sample_spec_dict)


@pytest.fixture
def generator(temp_dir):
    """Create FSA Generator instance"""
    return FSAGenerator(
        repo_path=temp_dir,
        output_dir=temp_dir / "fsas",
        test_dir=temp_dir / "tests",
        auto_commit=False
    )


class TestFSASpecification:
    """Test FSASpecification validation and parsing"""

    def test_valid_specification(self, sample_spec_dict):
        """Test creation of valid FSA specification"""
        spec = FSASpecification(**sample_spec_dict)
        assert spec.name == "TestProcessor"
        assert spec.category == FSACategory.CORE
        assert spec.purpose == "Test FSA for unit testing"
        assert len(spec.key_capabilities) == 3
        assert len(spec.dependencies) == 2

    def test_invalid_name_empty(self):
        """Test that empty name raises validation error"""
        with pytest.raises(ValueError, match="FSA name cannot be empty"):
            FSASpecification(
                name="",
                category="Core",
                purpose="Test"
            )

    def test_invalid_name_lowercase(self):
        """Test that lowercase name raises validation error"""
        with pytest.raises(ValueError, match="must start with uppercase"):
            FSASpecification(
                name="testProcessor",
                category="Core",
                purpose="Test"
            )

    def test_invalid_name_with_spaces(self):
        """Test that name with spaces raises validation error"""
        with pytest.raises(ValueError, match="cannot contain spaces"):
            FSASpecification(
                name="Test Processor",
                category="Core",
                purpose="Test"
            )

    def test_invalid_complexity_target(self):
        """Test that invalid complexity target raises validation error"""
        with pytest.raises(ValueError, match="Complexity target must be"):
            FSASpecification(
                name="TestProcessor",
                category="Core",
                purpose="Test",
                complexity_target="invalid"
            )

    def test_default_values(self):
        """Test that default values are set correctly"""
        spec = FSASpecification(
            name="TestProcessor",
            category="Core",
            purpose="Test"
        )
        assert spec.key_capabilities == []
        assert spec.dependencies == []
        assert spec.complexity_target == "300-500 LOC"
        assert spec.custom_methods is None


class TestParsedSpec:
    """Test ParsedSpec functionality"""

    def test_file_name_generation(self):
        """Test snake_case filename generation from PascalCase"""
        spec = ParsedSpec(
            name="DataProcessor",
            category=FSACategory.DOMAIN,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        assert spec.file_name == "data_processor"

    def test_class_name_without_fsa_suffix(self):
        """Test class name generation when name doesn't end with FSA"""
        spec = ParsedSpec(
            name="DataProcessor",
            category=FSACategory.DOMAIN,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        assert spec.class_name == "DataProcessorFSA"

    def test_class_name_with_fsa_suffix(self):
        """Test class name generation when name already ends with FSA"""
        spec = ParsedSpec(
            name="DataProcessorFSA",
            category=FSACategory.DOMAIN,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        assert spec.class_name == "DataProcessorFSA"


class TestFSAGeneratorInitialization:
    """Test FSA Generator initialization"""

    def test_init_default(self, temp_dir):
        """Test initialization with default parameters"""
        generator = FSAGenerator(repo_path=temp_dir)
        assert generator.repo_path == temp_dir
        assert generator.auto_commit is False
        assert generator.templates is not None
        assert len(generator.templates) == 4  # Four categories

    def test_init_with_auto_commit(self, temp_dir):
        """Test initialization with auto_commit enabled"""
        generator = FSAGenerator(repo_path=temp_dir, auto_commit=True)
        assert generator.auto_commit is True

    def test_directories_created(self, temp_dir):
        """Test that output directories are created"""
        output_dir = temp_dir / "fsas"
        test_dir = temp_dir / "tests"

        generator = FSAGenerator(
            repo_path=temp_dir,
            output_dir=output_dir,
            test_dir=test_dir
        )

        assert output_dir.exists()
        assert test_dir.exists()

    def test_templates_initialized(self, generator):
        """Test that templates are initialized for all categories"""
        assert FSACategory.CORE in generator.templates
        assert FSACategory.INTEGRATION in generator.templates
        assert FSACategory.META in generator.templates
        assert FSACategory.DOMAIN in generator.templates


class TestParseSpecification:
    """Test specification parsing functionality"""

    def test_parse_dict_specification(self, generator, sample_spec_dict):
        """Test parsing specification from dictionary"""
        parsed = generator.parse_specification(sample_spec_dict)

        assert isinstance(parsed, ParsedSpec)
        assert parsed.name == "TestProcessor"
        assert parsed.category == FSACategory.CORE
        assert parsed.complexity_range == (300, 500)
        assert len(parsed.key_capabilities) == 3

    def test_parse_object_specification(self, generator, sample_spec_object):
        """Test parsing specification from FSASpecification object"""
        parsed = generator.parse_specification(sample_spec_object)

        assert isinstance(parsed, ParsedSpec)
        assert parsed.name == "TestProcessor"
        assert parsed.class_name == "TestProcessorFSA"

    def test_parse_json_file(self, generator, temp_dir, sample_spec_dict):
        """Test parsing specification from JSON file"""
        json_file = temp_dir / "spec.json"
        with open(json_file, 'w') as f:
            json.dump(sample_spec_dict, f)

        parsed = generator.parse_specification(json_file)
        assert isinstance(parsed, ParsedSpec)
        assert parsed.name == "TestProcessor"

    def test_parse_yaml_file(self, generator, temp_dir, sample_spec_dict):
        """Test parsing specification from YAML file"""
        yaml_file = temp_dir / "spec.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(sample_spec_dict, f)

        parsed = generator.parse_specification(yaml_file)
        assert isinstance(parsed, ParsedSpec)
        assert parsed.name == "TestProcessor"

    def test_parse_nonexistent_file(self, generator):
        """Test that parsing nonexistent file raises error"""
        with pytest.raises(InvalidSpecificationError, match="not found"):
            generator.parse_specification("/nonexistent/spec.json")

    def test_parse_unsupported_format(self, generator, temp_dir):
        """Test that unsupported file format raises error"""
        txt_file = temp_dir / "spec.txt"
        txt_file.write_text("some text")

        with pytest.raises(InvalidSpecificationError, match="Unsupported file format"):
            generator.parse_specification(txt_file)

    def test_parse_invalid_type(self, generator):
        """Test that invalid specification type raises error"""
        with pytest.raises(InvalidSpecificationError, match="Unsupported specification type"):
            generator.parse_specification(12345)


class TestTemplateSelection:
    """Test template selection logic"""

    def test_select_core_templates(self, generator):
        """Test selecting templates for Core category"""
        spec = ParsedSpec(
            name="TestCore",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        templates = generator.select_templates(spec)
        assert len(templates) > 0
        assert templates[0].category == FSACategory.CORE

    def test_select_integration_templates(self, generator):
        """Test selecting templates for Integration category"""
        spec = ParsedSpec(
            name="TestIntegration",
            category=FSACategory.INTEGRATION,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        templates = generator.select_templates(spec)
        assert len(templates) > 0
        assert templates[0].category == FSACategory.INTEGRATION

    def test_select_meta_templates(self, generator):
        """Test selecting templates for Meta category"""
        spec = ParsedSpec(
            name="TestMeta",
            category=FSACategory.META,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        templates = generator.select_templates(spec)
        assert len(templates) > 0
        assert templates[0].category == FSACategory.META


class TestCodeSynthesis:
    """Test code synthesis and generation"""

    def test_synthesize_basic_code(self, generator):
        """Test basic code synthesis"""
        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test FSA",
            key_capabilities=["Test capability"],
            dependencies=[],
            complexity_range=(300, 500)
        )
        templates = generator.select_templates(spec)
        code = generator.synthesize_code(templates, spec)

        assert "class TestFSAFSA:" in code
        assert "def __init__" in code
        assert "def execute" in code
        assert "Test FSA" in code

    def test_synthesize_with_imports(self, generator):
        """Test code synthesis includes imports"""
        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=["pandas", "numpy"],
            complexity_range=(300, 500)
        )
        templates = generator.select_templates(spec)
        code = generator.synthesize_code(templates, spec)

        assert "import pandas" in code
        assert "import numpy" in code

    def test_synthesize_with_custom_methods(self, generator):
        """Test code synthesis includes custom methods"""
        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500),
            custom_methods={
                "custom_method": "Custom method description",
                "another_method": "Another method"
            }
        )
        templates = generator.select_templates(spec)
        code = generator.synthesize_code(templates, spec)

        assert "def custom_method" in code
        assert "def another_method" in code


class TestTestGeneration:
    """Test automatic test generation"""

    def test_generate_tests(self, generator):
        """Test generation of test suite"""
        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        code = "class TestFSAFSA:\n    pass"
        tests = generator.generate_tests(code, spec)

        assert "import pytest" in tests
        assert "class Test" in tests
        assert "def test_" in tests
        assert "TestFSAFSA" in tests

    def test_generated_tests_structure(self, generator):
        """Test that generated tests have proper structure"""
        spec = ParsedSpec(
            name="DataProcessor",
            category=FSACategory.DOMAIN,
            purpose="Process data",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        code = "class DataProcessorFSA:\n    pass"
        tests = generator.generate_tests(code, spec)

        # Check for test classes
        assert "TestDataProcessorFSAInitialization" in tests
        assert "TestDataProcessorFSACoreFunctionality" in tests
        assert "TestDataProcessorFSAErrorHandling" in tests
        assert "TestDataProcessorFSAStateManagement" in tests


class TestValidation:
    """Test FSA validation functionality"""

    def test_validate_valid_code(self, generator):
        """Test validation of syntactically correct code"""
        spec = ParsedSpec(
            name="ValidFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        valid_code = '''
class ValidFSAFSA:
    def __init__(self):
        pass

    def execute(self, task):
        return task
'''
        valid_tests = '''
import pytest

def test_valid():
    assert True
'''
        impl = FSAImplementation(
            spec=spec,
            code=valid_code,
            tests=valid_tests,
            file_path=Path("/tmp/valid.py"),
            test_file_path=Path("/tmp/test_valid.py")
        )

        assert generator.validate_fsa(impl) is True

    def test_validate_invalid_syntax(self, generator):
        """Test validation rejects code with syntax errors"""
        spec = ParsedSpec(
            name="InvalidFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        invalid_code = '''
class InvalidFSAFSA:
    def __init__(self)  # Missing colon
        pass
'''
        valid_tests = "import pytest\n"

        impl = FSAImplementation(
            spec=spec,
            code=invalid_code,
            tests=valid_tests,
            file_path=Path("/tmp/invalid.py"),
            test_file_path=Path("/tmp/test_invalid.py")
        )

        assert generator.validate_fsa(impl) is False

    def test_validate_missing_required_components(self, generator):
        """Test validation checks for required components"""
        spec = ParsedSpec(
            name="IncompleteFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        incomplete_code = '''
class IncompleteFSAFSA:
    pass
'''
        valid_tests = "import pytest\n"

        impl = FSAImplementation(
            spec=spec,
            code=incomplete_code,
            tests=valid_tests,
            file_path=Path("/tmp/incomplete.py"),
            test_file_path=Path("/tmp/test_incomplete.py")
        )

        # Should fail because missing __init__ and execute methods
        assert generator.validate_fsa(impl) is False


class TestEndToEndGeneration:
    """Test complete end-to-end FSA generation"""

    def test_full_generation_workflow(self, generator, sample_spec_dict):
        """Test complete FSA generation workflow"""
        # Generate FSA
        implementation = generator.generate_fsa(sample_spec_dict)

        # Verify implementation
        assert isinstance(implementation, FSAImplementation)
        assert implementation.spec.name == "TestProcessor"
        assert implementation.code is not None
        assert implementation.tests is not None

        # Verify files were created
        assert implementation.file_path.exists()
        assert implementation.test_file_path.exists()

        # Verify code content
        code_content = implementation.file_path.read_text()
        assert "class TestProcessorFSA:" in code_content
        assert "def __init__" in code_content
        assert "def execute" in code_content

        # Verify test content
        test_content = implementation.test_file_path.read_text()
        assert "import pytest" in test_content
        assert "TestTestProcessorFSA" in test_content

    def test_generation_with_json_file(self, generator, temp_dir, sample_spec_dict):
        """Test generation from JSON specification file"""
        spec_file = temp_dir / "spec.json"
        with open(spec_file, 'w') as f:
            json.dump(sample_spec_dict, f)

        implementation = generator.generate_fsa(spec_file)
        assert implementation.file_path.exists()
        assert implementation.test_file_path.exists()


class TestGitIntegration:
    """Test git integration functionality"""

    def test_commit_to_repo_without_git(self, generator):
        """Test commit when no git repo is initialized"""
        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test",
            key_capabilities=[],
            dependencies=[],
            complexity_range=(300, 500)
        )
        impl = FSAImplementation(
            spec=spec,
            code="test",
            tests="test",
            file_path=Path("/tmp/test.py"),
            test_file_path=Path("/tmp/test_test.py")
        )

        # Should return False when no repo
        result = generator.commit_to_repo(impl)
        assert result is False

    @patch('agno.fsas.generator.Repo')
    def test_commit_to_repo_with_git(self, mock_repo_class, generator):
        """Test commit when git repo is available"""
        # Setup mock
        mock_repo = MagicMock()
        mock_index = MagicMock()
        mock_repo.index = mock_index
        generator.repo = mock_repo

        spec = ParsedSpec(
            name="TestFSA",
            category=FSACategory.CORE,
            purpose="Test FSA",
            key_capabilities=["Test"],
            dependencies=[],
            complexity_range=(300, 500)
        )

        # Create actual files for the test
        test_file = generator.output_dir / "test_fsa.py"
        test_test_file = generator.test_dir / "test_test_fsa.py"
        test_file.write_text("test")
        test_test_file.write_text("test")

        impl = FSAImplementation(
            spec=spec,
            code="test",
            tests="test",
            file_path=test_file,
            test_file_path=test_test_file
        )

        # Execute commit
        result = generator.commit_to_repo(impl)

        # Verify
        assert result is True
        mock_index.add.assert_called_once()
        mock_index.commit.assert_called_once()


class TestErrorHandling:
    """Test error handling and recovery"""

    def test_error_recovery_invalid_spec(self, generator):
        """Test error recovery for invalid specification"""
        error = InvalidSpecificationError("Test error")
        recovery_msg = generator.error_recovery(error)

        assert "InvalidSpecificationError" in recovery_msg
        assert "Test error" in recovery_msg
        assert "Recovery suggestions" in recovery_msg

    def test_error_recovery_template_render(self, generator):
        """Test error recovery for template render errors"""
        error = TemplateRenderError("Template error")
        recovery_msg = generator.error_recovery(error)

        assert "TemplateRenderError" in recovery_msg
        assert "Template error" in recovery_msg

    def test_error_recovery_code_validation(self, generator):
        """Test error recovery for code validation errors"""
        error = CodeValidationError("Validation error")
        recovery_msg = generator.error_recovery(error)

        assert "CodeValidationError" in recovery_msg
        assert "Validation error" in recovery_msg

    def test_error_recovery_git_operation(self, generator):
        """Test error recovery for git operation errors"""
        error = GitOperationError("Git error")
        recovery_msg = generator.error_recovery(error)

        assert "GitOperationError" in recovery_msg
        assert "Git error" in recovery_msg


class TestTemplateRendering:
    """Test template rendering functionality"""

    def test_template_render_basic(self):
        """Test basic template rendering"""
        template = Template(
            name="test",
            category=FSACategory.CORE,
            template_content="Hello {{name}}!",
            placeholders=["name"]
        )

        result = template.render({"name": "World"})
        assert result == "Hello World!"

    def test_template_render_multiple_placeholders(self):
        """Test rendering with multiple placeholders"""
        template = Template(
            name="test",
            category=FSACategory.CORE,
            template_content="{{greeting}} {{name}}! Age: {{age}}",
            placeholders=["greeting", "name", "age"]
        )

        result = template.render({
            "greeting": "Hello",
            "name": "Alice",
            "age": "30"
        })
        assert result == "Hello Alice! Age: 30"

    def test_template_render_unused_placeholders(self):
        """Test rendering with unused placeholders"""
        template = Template(
            name="test",
            category=FSACategory.CORE,
            template_content="Hello {{name}}!",
            placeholders=["name"]
        )

        # Extra context values should be ignored
        result = template.render({"name": "World", "unused": "value"})
        assert result == "Hello World!"

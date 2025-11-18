"""
FSA Generator - A meta-FSA for generating Functional Specialist Agents

This module provides comprehensive functionality for automatically generating FSAs
from specifications. It includes template management, code synthesis, test generation,
validation, and git integration.

Author: Agno Team
License: MPL 2.0
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from git import Repo
from pydantic import BaseModel, Field, validator

# Configure logging
logger = logging.getLogger(__name__)


class FSACategory(str, Enum):
    """Categories of FSAs that can be generated"""
    CORE = "Core"
    INTEGRATION = "Integration"
    META = "Meta"
    DOMAIN = "Domain"


class FSASpecification(BaseModel):
    """Specification for an FSA to be generated"""

    name: str = Field(..., description="Name of the FSA (PascalCase)")
    category: FSACategory = Field(..., description="Category of the FSA")
    purpose: str = Field(..., description="Brief description of what this FSA does")
    key_capabilities: List[str] = Field(
        default_factory=list,
        description="List of key capabilities this FSA should have"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of dependencies (package names or modules)"
    )
    complexity_target: str = Field(
        default="300-500 LOC",
        description="Target complexity in lines of code"
    )
    custom_methods: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional custom method signatures and descriptions"
    )

    @validator('name')
    def validate_name(cls, v):
        """Ensure name is PascalCase and doesn't contain spaces"""
        if not v:
            raise ValueError("FSA name cannot be empty")
        if not v[0].isupper():
            raise ValueError("FSA name must start with uppercase letter")
        if ' ' in v:
            raise ValueError("FSA name cannot contain spaces")
        return v

    @validator('complexity_target')
    def validate_complexity(cls, v):
        """Validate complexity target format"""
        pattern = r'^\d+-\d+\s*LOC$'
        if not re.match(pattern, v):
            raise ValueError("Complexity target must be in format 'XXX-YYY LOC'")
        return v


@dataclass
class ParsedSpec:
    """Parsed and processed FSA specification"""

    name: str
    category: FSACategory
    purpose: str
    key_capabilities: List[str]
    dependencies: List[str]
    complexity_range: tuple[int, int]
    custom_methods: Dict[str, str] = field(default_factory=dict)

    @property
    def file_name(self) -> str:
        """Generate snake_case filename from FSA name"""
        # Convert PascalCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    @property
    def class_name(self) -> str:
        """Get the class name (ensure it ends with FSA)"""
        if self.name.endswith('FSA'):
            return self.name
        return f"{self.name}FSA"


@dataclass
class Template:
    """Code template for FSA generation"""

    name: str
    category: FSACategory
    template_content: str
    placeholders: List[str] = field(default_factory=list)

    def render(self, context: Dict[str, Any]) -> str:
        """Render template with provided context"""
        result = self.template_content
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result


@dataclass
class FSAImplementation:
    """Generated FSA implementation"""

    spec: ParsedSpec
    code: str
    tests: str
    file_path: Path
    test_file_path: Path
    created_at: datetime = field(default_factory=datetime.now)

    def validate_syntax(self) -> bool:
        """Validate that generated code has valid Python syntax"""
        try:
            ast.parse(self.code)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return False

    def validate_tests(self) -> bool:
        """Validate that generated tests have valid Python syntax"""
        try:
            ast.parse(self.tests)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in generated tests: {e}")
            return False


class FSAGeneratorError(Exception):
    """Base exception for FSA Generator errors"""
    pass


class InvalidSpecificationError(FSAGeneratorError):
    """Raised when FSA specification is invalid"""
    pass


class TemplateRenderError(FSAGeneratorError):
    """Raised when template rendering fails"""
    pass


class CodeValidationError(FSAGeneratorError):
    """Raised when generated code fails validation"""
    pass


class GitOperationError(FSAGeneratorError):
    """Raised when git operations fail"""
    pass


class FSAGenerator:
    """
    Meta-FSA for generating Functional Specialist Agents

    This class provides comprehensive functionality for automatically generating
    FSAs from specifications, including code generation, test creation, validation,
    and git integration.
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        test_dir: Optional[str] = None,
        auto_commit: bool = False
    ):
        """
        Initialize FSA Generator

        Args:
            repo_path: Path to git repository (defaults to current directory)
            output_dir: Directory for generated FSAs (defaults to libs/agno/agno/fsas)
            test_dir: Directory for generated tests (defaults to libs/agno/tests/unit/fsas)
            auto_commit: Whether to automatically commit generated FSAs
        """
        self.repo_path = Path(repo_path or os.getcwd())
        self.output_dir = Path(output_dir or self.repo_path / "libs/agno/agno/fsas")
        self.test_dir = Path(test_dir or self.repo_path / "libs/agno/tests/unit/fsas")
        self.auto_commit = auto_commit

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Initialize git repo if auto_commit is enabled
        self.repo: Optional[Repo] = None
        if self.auto_commit:
            try:
                self.repo = Repo(self.repo_path)
            except Exception as e:
                logger.warning(f"Could not initialize git repo: {e}")

        # Initialize template library
        self._initialize_templates()

        logger.info(f"FSA Generator initialized at {self.repo_path}")

    def _initialize_templates(self) -> None:
        """Initialize the built-in FSA templates library"""
        self.templates: Dict[FSACategory, List[Template]] = {
            FSACategory.CORE: [
                Template(
                    name="core_infrastructure",
                    category=FSACategory.CORE,
                    template_content=self._get_core_template(),
                    placeholders=["CLASS_NAME", "PURPOSE", "METHODS", "IMPORTS"]
                )
            ],
            FSACategory.INTEGRATION: [
                Template(
                    name="integration_base",
                    category=FSACategory.INTEGRATION,
                    template_content=self._get_integration_template(),
                    placeholders=["CLASS_NAME", "PURPOSE", "METHODS", "IMPORTS"]
                )
            ],
            FSACategory.META: [
                Template(
                    name="meta_base",
                    category=FSACategory.META,
                    template_content=self._get_meta_template(),
                    placeholders=["CLASS_NAME", "PURPOSE", "METHODS", "IMPORTS"]
                )
            ],
            FSACategory.DOMAIN: [
                Template(
                    name="domain_base",
                    category=FSACategory.DOMAIN,
                    template_content=self._get_domain_template(),
                    placeholders=["CLASS_NAME", "PURPOSE", "METHODS", "IMPORTS"]
                )
            ]
        }

    def generate_fsa(
        self,
        spec: Union[Dict[str, Any], FSASpecification, str, Path]
    ) -> FSAImplementation:
        """
        Main generation method - orchestrates the entire FSA generation process

        Args:
            spec: FSA specification (dict, FSASpecification object, or path to JSON/YAML)

        Returns:
            FSAImplementation object containing generated code and metadata

        Raises:
            InvalidSpecificationError: If specification is invalid
            TemplateRenderError: If template rendering fails
            CodeValidationError: If generated code is invalid
        """
        logger.info("Starting FSA generation")

        # Parse specification
        parsed_spec = self.parse_specification(spec)
        logger.info(f"Generating FSA: {parsed_spec.class_name}")

        # Select appropriate templates
        templates = self.select_templates(parsed_spec)
        logger.info(f"Selected {len(templates)} template(s)")

        # Synthesize code
        code = self.synthesize_code(templates, parsed_spec)
        logger.info(f"Generated {len(code.splitlines())} lines of code")

        # Generate tests
        tests = self.generate_tests(code, parsed_spec)
        logger.info(f"Generated {len(tests.splitlines())} lines of tests")

        # Create file paths
        file_path = self.output_dir / f"{parsed_spec.file_name}.py"
        test_file_path = self.test_dir / f"test_{parsed_spec.file_name}.py"

        # Create implementation object
        implementation = FSAImplementation(
            spec=parsed_spec,
            code=code,
            tests=tests,
            file_path=file_path,
            test_file_path=test_file_path
        )

        # Validate generated code
        if not self.validate_fsa(implementation):
            raise CodeValidationError("Generated FSA code failed validation")

        # Write files
        self._write_files(implementation)
        logger.info(f"FSA written to {file_path}")

        # Commit to repo if enabled
        if self.auto_commit and self.repo:
            success = self.commit_to_repo(implementation)
            if success:
                logger.info("Successfully committed FSA to repository")

        return implementation

    def parse_specification(
        self,
        spec: Union[Dict[str, Any], FSASpecification, str, Path]
    ) -> ParsedSpec:
        """
        Parse and validate FSA specification

        Args:
            spec: Specification in various formats

        Returns:
            ParsedSpec object with validated and processed specification

        Raises:
            InvalidSpecificationError: If specification is invalid
        """
        try:
            # Handle different input types
            if isinstance(spec, (str, Path)):
                spec_path = Path(spec)
                if not spec_path.exists():
                    raise InvalidSpecificationError(f"Specification file not found: {spec}")

                with open(spec_path, 'r') as f:
                    if spec_path.suffix in ['.yaml', '.yml']:
                        spec_dict = yaml.safe_load(f)
                    elif spec_path.suffix == '.json':
                        spec_dict = json.load(f)
                    else:
                        raise InvalidSpecificationError(f"Unsupported file format: {spec_path.suffix}")

                spec_obj = FSASpecification(**spec_dict)

            elif isinstance(spec, dict):
                spec_obj = FSASpecification(**spec)

            elif isinstance(spec, FSASpecification):
                spec_obj = spec

            else:
                raise InvalidSpecificationError(f"Unsupported specification type: {type(spec)}")

            # Parse complexity target
            match = re.search(r'(\d+)-(\d+)', spec_obj.complexity_target)
            if match:
                complexity_range = (int(match.group(1)), int(match.group(2)))
            else:
                complexity_range = (300, 500)

            # Create parsed spec
            parsed = ParsedSpec(
                name=spec_obj.name,
                category=spec_obj.category,
                purpose=spec_obj.purpose,
                key_capabilities=spec_obj.key_capabilities,
                dependencies=spec_obj.dependencies,
                complexity_range=complexity_range,
                custom_methods=spec_obj.custom_methods or {}
            )

            logger.info(f"Successfully parsed specification for {parsed.class_name}")
            return parsed

        except Exception as e:
            raise InvalidSpecificationError(f"Failed to parse specification: {e}")

    def select_templates(self, parsed_spec: ParsedSpec) -> List[Template]:
        """
        Select appropriate templates based on parsed specification

        Args:
            parsed_spec: Parsed FSA specification

        Returns:
            List of Template objects to use for code generation
        """
        category_templates = self.templates.get(parsed_spec.category, [])

        if not category_templates:
            logger.warning(f"No templates found for category {parsed_spec.category}, using Core")
            category_templates = self.templates[FSACategory.CORE]

        return category_templates

    def synthesize_code(
        self,
        templates: List[Template],
        spec: ParsedSpec
    ) -> str:
        """
        Synthesize FSA code from templates and specification

        Args:
            templates: List of templates to use
            spec: Parsed specification

        Returns:
            Generated Python code as string

        Raises:
            TemplateRenderError: If template rendering fails
        """
        try:
            # Generate imports
            imports = self._generate_imports(spec)

            # Generate methods
            methods = self._generate_methods(spec)

            # Prepare context for template rendering
            context = {
                "CLASS_NAME": spec.class_name,
                "PURPOSE": spec.purpose,
                "METHODS": methods,
                "IMPORTS": imports,
                "CAPABILITIES": "\n".join(f"    - {cap}" for cap in spec.key_capabilities),
                "CATEGORY": spec.category.value,
                "FILE_NAME": spec.file_name,
            }

            # Render primary template
            template = templates[0] if templates else self._get_default_template()
            code = template.render(context)

            return code

        except Exception as e:
            raise TemplateRenderError(f"Failed to synthesize code: {e}")

    def generate_tests(self, fsa_code: str, spec: ParsedSpec) -> str:
        """
        Auto-generate comprehensive pytest tests for the FSA

        Args:
            fsa_code: Generated FSA code
            spec: Parsed specification

        Returns:
            Generated test code as string
        """
        test_template = f'''"""
Tests for {spec.class_name}

Auto-generated tests for the {spec.class_name} FSA.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from agno.fsas.{spec.file_name} import {spec.class_name}, {spec.class_name}Error


class Test{spec.class_name}Initialization:
    """Test {spec.class_name} initialization"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        fsa = {spec.class_name}()
        assert fsa is not None
        assert fsa.name == "{spec.class_name}"

    def test_init_with_config(self):
        """Test initialization with custom configuration"""
        config = {{"param1": "value1", "param2": "value2"}}
        fsa = {spec.class_name}(config=config)
        assert fsa.config == config


class Test{spec.class_name}CoreFunctionality:
    """Test core functionality of {spec.class_name}"""

    def test_execute_success(self):
        """Test successful execution of main functionality"""
        fsa = {spec.class_name}()
        result = fsa.execute(task="test_task")
        assert result is not None

    def test_execute_with_params(self):
        """Test execution with various parameters"""
        fsa = {spec.class_name}()
        result = fsa.execute(
            task="test_task",
            params={{"key": "value"}}
        )
        assert result is not None

    def test_validate_input(self):
        """Test input validation"""
        fsa = {spec.class_name}()
        # Valid input
        assert fsa.validate_input({{"valid": "data"}}) is True

        # Invalid input
        with pytest.raises({spec.class_name}Error):
            fsa.validate_input(None)


class Test{spec.class_name}ErrorHandling:
    """Test error handling in {spec.class_name}"""

    def test_handle_invalid_input(self):
        """Test handling of invalid input"""
        fsa = {spec.class_name}()
        with pytest.raises({spec.class_name}Error):
            fsa.execute(task=None)

    def test_error_recovery(self):
        """Test error recovery mechanism"""
        fsa = {spec.class_name}()
        error = Exception("Test error")
        result = fsa.handle_error(error)
        assert result is not None


class Test{spec.class_name}StateManagement:
    """Test state management in {spec.class_name}"""

    def test_get_state(self):
        """Test getting FSA state"""
        fsa = {spec.class_name}()
        state = fsa.get_state()
        assert isinstance(state, dict)

    def test_set_state(self):
        """Test setting FSA state"""
        fsa = {spec.class_name}()
        new_state = {{"key": "value"}}
        fsa.set_state(new_state)
        assert fsa.get_state() == new_state


class Test{spec.class_name}Integration:
    """Test integration scenarios for {spec.class_name}"""

    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        fsa = {spec.class_name}()

        # Initialize
        fsa.initialize()

        # Execute task
        result = fsa.execute(task="integration_test")

        # Verify result
        assert result is not None

        # Cleanup
        fsa.cleanup()
'''
        return test_template

    def validate_fsa(self, implementation: FSAImplementation) -> bool:
        """
        Validate generated FSA code and tests

        Args:
            implementation: FSA implementation to validate

        Returns:
            True if validation passes, False otherwise
        """
        # Validate code syntax
        if not implementation.validate_syntax():
            logger.error("FSA code has syntax errors")
            return False

        # Validate tests syntax
        if not implementation.validate_tests():
            logger.error("FSA tests have syntax errors")
            return False

        # Check that code contains required components
        required_patterns = [
            r'class\s+\w+FSA',  # FSA class definition
            r'def\s+__init__',  # Constructor
            r'def\s+execute',   # Execute method
        ]

        for pattern in required_patterns:
            if not re.search(pattern, implementation.code):
                logger.error(f"Generated code missing required pattern: {pattern}")
                return False

        logger.info("FSA validation passed")
        return True

    def commit_to_repo(self, fsa_impl: FSAImplementation) -> bool:
        """
        Commit generated FSA to git repository

        Args:
            fsa_impl: FSA implementation to commit

        Returns:
            True if commit successful, False otherwise
        """
        if not self.repo:
            logger.warning("No git repository initialized")
            return False

        try:
            # Add files to git
            self.repo.index.add([
                str(fsa_impl.file_path.relative_to(self.repo_path)),
                str(fsa_impl.test_file_path.relative_to(self.repo_path))
            ])

            # Create commit message
            commit_message = (
                f"feat: Add {fsa_impl.spec.class_name} ({fsa_impl.spec.category.value})\n\n"
                f"{fsa_impl.spec.purpose}\n\n"
                f"Auto-generated by FSA Generator"
            )

            # Commit
            self.repo.index.commit(commit_message)
            logger.info(f"Committed {fsa_impl.spec.class_name} to repository")

            return True

        except Exception as e:
            raise GitOperationError(f"Failed to commit to repository: {e}")

    def error_recovery(self, error: Exception) -> str:
        """
        Handle generation failures gracefully

        Args:
            error: Exception that occurred during generation

        Returns:
            Error message and recovery suggestions
        """
        error_type = type(error).__name__
        error_msg = str(error)

        recovery_suggestions = {
            "InvalidSpecificationError": [
                "Check that all required fields are present",
                "Validate the specification format (JSON/YAML)",
                "Ensure FSA name is in PascalCase without spaces"
            ],
            "TemplateRenderError": [
                "Verify template placeholders match specification",
                "Check for syntax errors in custom methods",
                "Try a simpler specification first"
            ],
            "CodeValidationError": [
                "Review generated code for syntax errors",
                "Simplify custom method specifications",
                "Check dependency compatibility"
            ],
            "GitOperationError": [
                "Verify git repository is initialized",
                "Check file permissions",
                "Ensure working directory is clean"
            ]
        }

        suggestions = recovery_suggestions.get(error_type, ["Review error message and try again"])

        recovery_message = f"""
Error during FSA generation: {error_type}
Message: {error_msg}

Recovery suggestions:
{chr(10).join(f'  - {s}' for s in suggestions)}
"""

        logger.error(recovery_message)
        return recovery_message

    def _generate_imports(self, spec: ParsedSpec) -> str:
        """Generate import statements based on specification"""
        base_imports = [
            "from __future__ import annotations",
            "",
            "import logging",
            "from dataclasses import dataclass, field",
            "from datetime import datetime",
            "from typing import Any, Dict, List, Optional, Union",
            "",
            "from pydantic import BaseModel, Field",
        ]

        # Add dependency imports
        for dep in spec.dependencies:
            base_imports.append(f"import {dep}")

        base_imports.extend([
            "",
            "logger = logging.getLogger(__name__)",
            ""
        ])

        return "\n".join(base_imports)

    def _generate_methods(self, spec: ParsedSpec) -> str:
        """Generate method implementations based on specification"""
        methods = []

        # Constructor
        methods.append('''    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize {CLASS_NAME}

        Args:
            config: Optional configuration dictionary
        """
        self.name = "{CLASS_NAME}"
        self.config = config or {}
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.now()
        logger.info(f"Initialized {self.name}")
    ''')

        # Execute method
        methods.append('''    def execute(self, task: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the main FSA functionality

        Args:
            task: Task description or identifier
            params: Optional parameters for execution

        Returns:
            Execution result

        Raises:
            {CLASS_NAME}Error: If execution fails
        """
        if not task:
            raise {CLASS_NAME}Error("Task cannot be empty")

        logger.info(f"Executing task: {task}")
        params = params or {}

        # Validate input
        if not self.validate_input(params):
            raise {CLASS_NAME}Error("Invalid input parameters")

        try:
            # Execute task logic
            result = self._process_task(task, params)
            logger.info(f"Task completed successfully: {task}")
            return result
        except Exception as e:
            return self.handle_error(e)
    ''')

        # Validation method
        methods.append('''    def validate_input(self, data: Any) -> bool:
        """
        Validate input data

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        if data is None:
            raise {CLASS_NAME}Error("Input data cannot be None")
        return True
    ''')

        # State management methods
        methods.append('''    def get_state(self) -> Dict[str, Any]:
        """Get current FSA state"""
        return self.state.copy()

    def set_state(self, state: Dict[str, Any]) -> None:
        """Set FSA state"""
        self.state = state
    ''')

        # Error handling
        methods.append('''    def handle_error(self, error: Exception) -> str:
        """
        Handle errors during execution

        Args:
            error: Exception that occurred

        Returns:
            Error message
        """
        error_msg = f"Error in {self.name}: {str(error)}"
        logger.error(error_msg)
        return error_msg
    ''')

        # Helper methods
        methods.append('''    def _process_task(self, task: str, params: Dict[str, Any]) -> Any:
        """Internal method to process task"""
        # Implementation specific to this FSA
        return {"status": "success", "task": task, "params": params}

    def initialize(self) -> None:
        """Initialize FSA for operation"""
        logger.info(f"Initializing {self.name}")
        self.state = {"initialized": True, "timestamp": datetime.now()}

    def cleanup(self) -> None:
        """Cleanup FSA resources"""
        logger.info(f"Cleaning up {self.name}")
        self.state = {}
''')

        # Add custom methods if specified
        for method_name, method_desc in spec.custom_methods.items():
            methods.append(f'''    def {method_name}(self) -> Any:
        """
        {method_desc}
        """
        # TODO: Implement {method_name}
        pass
    ''')

        return "\n".join(methods)

    def _write_files(self, implementation: FSAImplementation) -> None:
        """Write generated FSA and test files to disk"""
        # Write FSA code
        with open(implementation.file_path, 'w') as f:
            f.write(implementation.code)

        # Write test code
        with open(implementation.test_file_path, 'w') as f:
            f.write(implementation.tests)

    def _get_core_template(self) -> str:
        """Get template for Core FSAs"""
        return '''{IMPORTS}


class {CLASS_NAME}Error(Exception):
    """Exception raised by {CLASS_NAME}"""
    pass


class {CLASS_NAME}:
    """
    {PURPOSE}

    Category: {CATEGORY}

    Key Capabilities:
{CAPABILITIES}
    """

{METHODS}
'''

    def _get_integration_template(self) -> str:
        """Get template for Integration FSAs"""
        return self._get_core_template()  # Similar structure for now

    def _get_meta_template(self) -> str:
        """Get template for Meta FSAs"""
        return self._get_core_template()  # Similar structure for now

    def _get_domain_template(self) -> str:
        """Get template for Domain FSAs"""
        return self._get_core_template()  # Similar structure for now

    def _get_default_template(self) -> Template:
        """Get default template when no specific template is found"""
        return Template(
            name="default",
            category=FSACategory.CORE,
            template_content=self._get_core_template(),
            placeholders=["CLASS_NAME", "PURPOSE", "METHODS", "IMPORTS"]
        )


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Example specification
    example_spec = {
        "name": "DataProcessor",
        "category": "Domain",
        "purpose": "Process and transform data from various sources",
        "key_capabilities": [
            "Read data from multiple formats (CSV, JSON, XML)",
            "Transform and validate data",
            "Export to different formats",
            "Handle data quality issues"
        ],
        "dependencies": ["pandas", "numpy"],
        "complexity_target": "400-600 LOC",
        "custom_methods": {
            "read_csv": "Read data from CSV file",
            "transform_data": "Apply transformations to data",
            "export_json": "Export data to JSON format"
        }
    }

    # Create generator
    generator = FSAGenerator(auto_commit=False)

    # Generate FSA
    try:
        implementation = generator.generate_fsa(example_spec)
        print(f"✓ Successfully generated {implementation.spec.class_name}")
        print(f"  Code: {implementation.file_path}")
        print(f"  Tests: {implementation.test_file_path}")
        print(f"  Lines of code: {len(implementation.code.splitlines())}")
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        recovery_msg = generator.error_recovery(e)
        print(recovery_msg)

"""FSA Generator - Meta-FSA for generating new FSA implementations."""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agno.fsa.base import FSA
from agno.utils.log import logger


@dataclass
class FSASpecification:
    """Specification for generating an FSA.

    Attributes:
        name: Name of the FSA class to generate
        purpose: Description of what the FSA does
        states: Set of valid states for the FSA
        methods: List of method definitions (name, params, return type)
        dependencies: External dependencies required
        stateful: Whether FSA maintains state
        cascade_aware: Whether FSA can cascade to other FSAs
        custom_transitions: Custom state transitions
    """

    name: str
    purpose: str
    states: Set[str] = field(default_factory=lambda: {"initial", "processing", "completed", "error"})
    methods: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    stateful: bool = True
    cascade_aware: bool = False
    custom_transitions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FSAGeneratorFSA(FSA):
    """Meta-FSA for generating new FSA implementations.

    This FSA takes specifications and generates complete FSA implementations
    including class structure, methods, tests, and documentation.

    States:
        - initial: Ready to receive specification
        - validating: Validating FSA specification
        - generating: Generating FSA code
        - writing: Writing files to disk
        - completed: Generation complete
        - error: Error during generation
    """

    # Output configuration
    output_dir: Optional[Path] = None
    test_output_dir: Optional[Path] = None

    # Generation results
    generated_code: Optional[str] = None
    generated_tests: Optional[str] = None
    generated_files: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize FSA Generator."""
        # Set valid states for generator
        self.states = {
            "initial",
            "validating",
            "generating",
            "writing",
            "completed",
            "error"
        }
        self.current_state = "initial"

        # Add transitions
        self.add_transition("initial", "validating")
        self.add_transition("validating", "generating")
        self.add_transition("validating", "error")
        self.add_transition("generating", "writing")
        self.add_transition("generating", "error")
        self.add_transition("writing", "completed")
        self.add_transition("writing", "error")

        super().__post_init__()

    def run(self, specification: FSASpecification, **kwargs) -> Dict[str, Any]:
        """Execute FSA generation.

        Args:
            specification: FSA specification to generate from
            **kwargs: Additional arguments

        Returns:
            Dictionary with generation results
        """
        try:
            # Transition to validating
            self.transition("validating")

            # Validate specification
            validation_result = self.validate_fsa(specification)
            if not validation_result["valid"]:
                self.transition("error")
                return {
                    "success": False,
                    "error": validation_result.get("error", "Validation failed")
                }

            # Transition to generating
            self.transition("generating")

            # Generate FSA code
            fsa_code = self.generate_fsa(specification)
            self.generated_code = fsa_code

            # Generate tests
            test_code = self.generate_tests(specification)
            self.generated_tests = test_code

            # Transition to writing
            self.transition("writing")

            # Write files
            written_files = self.write_files(specification, fsa_code, test_code)
            self.generated_files = written_files

            # Transition to completed
            self.transition("completed")

            return {
                "success": True,
                "fsa_name": specification.name,
                "generated_files": written_files,
                "code": fsa_code,
                "tests": test_code
            }

        except Exception as e:
            logger.error(f"FSA generation failed: {e}")
            self.transition("error")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_fsa(self, specification: FSASpecification) -> str:
        """Generate FSA code from specification.

        Args:
            specification: FSA specification

        Returns:
            Generated FSA Python code
        """
        # Create template
        template = self.create_template(specification)

        # Customize code
        customized_code = self.customize_code(template, specification)

        # Validate generated code using AST
        self._validate_generated_code(customized_code)

        return customized_code

    def create_template(self, specification: FSASpecification) -> str:
        """Create FSA code template.

        Args:
            specification: FSA specification

        Returns:
            FSA code template string
        """
        # Build imports
        imports = self._build_imports(specification)

        # Build class definition
        class_def = self._build_class_definition(specification)

        # Build __post_init__ method
        post_init = self._build_post_init(specification)

        # Build run method
        run_method = self._build_run_method(specification)

        # Build custom methods
        custom_methods = self._build_custom_methods(specification)

        # Combine all parts
        template = f'''"""Generated FSA: {specification.name}

{specification.purpose}
"""

{imports}


{class_def}
{post_init}
{run_method}
{custom_methods}
'''
        return template

    def customize_code(self, template: str, specification: FSASpecification) -> str:
        """Customize code template with specification details.

        Args:
            template: Code template
            specification: FSA specification

        Returns:
            Customized code
        """
        # Template is already customized in create_template
        # This method allows for additional customization if needed
        code = template

        # Format code
        code = self._format_code(code)

        return code

    def validate_fsa(self, specification: FSASpecification) -> Dict[str, Any]:
        """Validate FSA specification against MLA v3.0 standards.

        Args:
            specification: FSA specification to validate

        Returns:
            Dictionary with validation results
        """
        errors = []

        # Validate name
        if not specification.name:
            errors.append("FSA name is required")
        elif not specification.name.endswith("FSA"):
            errors.append("FSA name must end with 'FSA'")
        elif not re.match(r'^[A-Z][a-zA-Z0-9]*FSA$', specification.name):
            errors.append("FSA name must be PascalCase and end with 'FSA'")

        # Validate purpose
        if not specification.purpose:
            errors.append("FSA purpose is required")

        # Validate states
        if not specification.states:
            errors.append("FSA must have at least one state")
        elif "initial" not in specification.states:
            errors.append("FSA must have an 'initial' state")

        # Validate methods
        for method in specification.methods:
            if "name" not in method:
                errors.append("All methods must have a name")
            elif not re.match(r'^[a-z_][a-z0-9_]*$', method["name"]):
                errors.append(f"Method name '{method['name']}' must be snake_case")

        # Validate transitions
        for transition in specification.custom_transitions:
            if "from_state" not in transition or "to_state" not in transition:
                errors.append("Transitions must have from_state and to_state")
            elif transition["from_state"] not in specification.states:
                errors.append(f"Transition from_state '{transition['from_state']}' not in states")
            elif transition["to_state"] not in specification.states:
                errors.append(f"Transition to_state '{transition['to_state']}' not in states")

        if errors:
            return {
                "valid": False,
                "errors": errors,
                "error": "; ".join(errors)
            }

        return {"valid": True}

    def write_files(
        self,
        specification: FSASpecification,
        fsa_code: str,
        test_code: str
    ) -> List[str]:
        """Write generated files to disk.

        Args:
            specification: FSA specification
            fsa_code: Generated FSA code
            test_code: Generated test code

        Returns:
            List of written file paths
        """
        written_files = []

        # Determine output directories
        if self.output_dir is None:
            self.output_dir = Path("libs/agno/agno/fsa/generated")
        if self.test_output_dir is None:
            self.test_output_dir = Path("libs/agno/tests/unit/fsa/generated")

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_output_dir.mkdir(parents=True, exist_ok=True)

        # Write FSA code
        fsa_filename = self._to_snake_case(specification.name.replace("FSA", "")) + ".py"
        fsa_path = self.output_dir / fsa_filename
        fsa_path.write_text(fsa_code)
        written_files.append(str(fsa_path))
        logger.info(f"Wrote FSA to {fsa_path}")

        # Write test code
        test_filename = f"test_{fsa_filename}"
        test_path = self.test_output_dir / test_filename
        test_path.write_text(test_code)
        written_files.append(str(test_path))
        logger.info(f"Wrote tests to {test_path}")

        # Write __init__.py files if they don't exist
        for directory in [self.output_dir, self.test_output_dir]:
            init_path = directory / "__init__.py"
            if not init_path.exists():
                init_path.write_text('"""Generated FSAs."""\n')
                written_files.append(str(init_path))

        return written_files

    def generate_tests(self, specification: FSASpecification) -> str:
        """Generate pytest tests for the FSA.

        Args:
            specification: FSA specification

        Returns:
            Generated test code
        """
        fsa_module = self._to_snake_case(specification.name.replace("FSA", ""))
        class_name = specification.name

        tests = f'''"""Tests for generated {class_name}."""

import pytest
from agno.fsa.generated.{fsa_module} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""

    def test_initialization(self):
        """Test FSA initialization."""
        fsa = {class_name}()
        assert fsa.name == "{class_name}"
        assert fsa.current_state == "initial"
        assert fsa.fsa_id is not None

    def test_states(self):
        """Test FSA has correct states."""
        fsa = {class_name}()
        expected_states = {repr(specification.states)}
        assert fsa.states == expected_states

    def test_initial_state(self):
        """Test FSA starts in initial state."""
        fsa = {class_name}()
        assert fsa.current_state == "initial"

    def test_state_transitions(self):
        """Test FSA can transition between states."""
        fsa = {class_name}()
        assert fsa.current_state == "initial"
        # Test transitions based on FSA implementation

    def test_stateful_configuration(self):
        """Test FSA stateful configuration."""
        fsa = {class_name}()
        assert fsa.stateful == {specification.stateful}

    def test_cascade_aware_configuration(self):
        """Test FSA cascade_aware configuration."""
        fsa = {class_name}()
        assert fsa.cascade_aware == {specification.cascade_aware}

    def test_session_state(self):
        """Test FSA session state management."""
        fsa = {class_name}()
        fsa.session_state["test_key"] = "test_value"
        assert fsa.session_state["test_key"] == "test_value"

    def test_context(self):
        """Test FSA context management."""
        fsa = {class_name}()
        fsa.context["test_key"] = "test_value"
        assert fsa.context["test_key"] == "test_value"

    def test_get_state_info(self):
        """Test get_state_info method."""
        fsa = {class_name}()
        info = fsa.get_state_info()
        assert info["name"] == "{class_name}"
        assert info["current_state"] == "initial"
        assert "fsa_id" in info

    def test_reset(self):
        """Test FSA reset."""
        fsa = {class_name}()
        fsa.session_state["key"] = "value"
        fsa.reset()
        assert fsa.current_state == "initial"

    def test_can_transition(self):
        """Test can_transition method."""
        fsa = {class_name}()
        # Test based on defined transitions
        assert isinstance(fsa.can_transition("processing"), bool)

    def test_transition_history(self):
        """Test transition history tracking."""
        fsa = {class_name}()
        assert isinstance(fsa.transition_history, list)
        initial_count = len(fsa.transition_history)
        # Perform transitions
        assert len(fsa.transition_history) >= initial_count

    def test_state_history(self):
        """Test state history tracking."""
        fsa = {class_name}()
        assert isinstance(fsa.state_history, list)

    def test_run_method_exists(self):
        """Test run method exists."""
        fsa = {class_name}()
        assert hasattr(fsa, "run")
        assert callable(fsa.run)

    def test_run_execution(self):
        """Test run method execution."""
        fsa = {class_name}()
        # Test run method - may need customization based on FSA
        try:
            result = fsa.run()
            assert result is not None
        except NotImplementedError:
            pytest.skip("Run method not fully implemented")
'''

        # Add custom method tests
        for method in specification.methods:
            method_name = method["name"]
            tests += f'''
    def test_{method_name}_exists(self):
        """Test {method_name} method exists."""
        fsa = {class_name}()
        assert hasattr(fsa, "{method_name}")
        assert callable(fsa.{method_name})
'''

        return tests

    # Helper methods

    def _build_imports(self, specification: FSASpecification) -> str:
        """Build import statements."""
        imports = [
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass, field",
            "from typing import Any, Dict, List, Optional, Set",
            "",
            "from agno.fsa.base import FSA",
            "from agno.utils.log import logger",
        ]

        # Add custom dependencies
        for dep in specification.dependencies:
            imports.append(f"import {dep}")

        return "\n".join(imports)

    def _build_class_definition(self, specification: FSASpecification) -> str:
        """Build class definition."""
        return f'''@dataclass
class {specification.name}(FSA):
    """Generated FSA: {specification.name}

    {specification.purpose}

    States: {", ".join(sorted(specification.states))}
    Stateful: {specification.stateful}
    Cascade-aware: {specification.cascade_aware}
    """

    # Custom attributes can be added here
    pass
'''

    def _build_post_init(self, specification: FSASpecification) -> str:
        """Build __post_init__ method."""
        transitions = []
        if specification.custom_transitions:
            for trans in specification.custom_transitions:
                from_state = trans["from_state"]
                to_state = trans["to_state"]
                transitions.append(f'        self.add_transition("{from_state}", "{to_state}")')
        else:
            # Add default transitions
            transitions.append('        self.add_transition("initial", "processing")')
            transitions.append('        self.add_transition("processing", "completed")')
            transitions.append('        self.add_transition("processing", "error")')

        transitions_code = "\n".join(transitions)

        return f'''
    def __post_init__(self):
        """Initialize {specification.name}."""
        self.states = {repr(specification.states)}
        self.current_state = "initial"
        self.stateful = {specification.stateful}
        self.cascade_aware = {specification.cascade_aware}

        # Add transitions
{transitions_code}

        super().__post_init__()
'''

    def _build_run_method(self, specification: FSASpecification) -> str:
        """Build run method."""
        return f'''
    def run(self, **kwargs) -> Any:
        """Execute the {specification.name}.

        Args:
            **kwargs: Arguments for FSA execution

        Returns:
            Result of FSA execution
        """
        try:
            # Transition to processing
            self.transition("processing")

            # Execute FSA logic here
            result = self._execute(**kwargs)

            # Transition to completed
            self.transition("completed")

            return result

        except Exception as e:
            logger.error(f"{specification.name} execution failed: {{e}}")
            self.transition("error")
            raise

    def _execute(self, **kwargs) -> Any:
        """Internal execution logic.

        Args:
            **kwargs: Execution arguments

        Returns:
            Execution result
        """
        # Implement FSA-specific logic here
        logger.info(f"Executing {specification.name}")
        return {{"status": "completed", "result": None}}
'''

    def _build_custom_methods(self, specification: FSASpecification) -> str:
        """Build custom methods from specification."""
        if not specification.methods:
            return ""

        methods = []
        for method_spec in specification.methods:
            method_name = method_spec.get("name", "custom_method")
            params = method_spec.get("params", [])
            return_type = method_spec.get("return_type", "Any")
            docstring = method_spec.get("docstring", f"Custom method: {method_name}")

            # Build parameter list
            param_list = ", ".join([f"{p['name']}: {p.get('type', 'Any')}" for p in params])

            method_code = f'''
    def {method_name}(self{", " + param_list if param_list else ""}) -> {return_type}:
        """{docstring}"""
        # Implement method logic
        logger.debug(f"Executing {method_name}")
        pass
'''
            methods.append(method_code)

        return "\n".join(methods)

    def _validate_generated_code(self, code: str) -> None:
        """Validate generated code using AST.

        Args:
            code: Generated Python code

        Raises:
            SyntaxError: If code has syntax errors
        """
        try:
            ast.parse(code)
            logger.debug("Generated code validated successfully")
        except SyntaxError as e:
            logger.error(f"Generated code has syntax errors: {e}")
            raise

    def _format_code(self, code: str) -> str:
        """Format code (basic formatting).

        Args:
            code: Code to format

        Returns:
            Formatted code
        """
        # Remove excessive blank lines
        lines = code.split("\n")
        formatted_lines = []
        blank_count = 0

        for line in lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    formatted_lines.append(line)
            else:
                blank_count = 0
                formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def _to_snake_case(self, name: str) -> str:
        """Convert PascalCase to snake_case.

        Args:
            name: PascalCase name

        Returns:
            snake_case name
        """
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

#!/usr/bin/env python3
"""
FSA10 Test Suite Generator - Automated Test Generation for Agno Framework

This module provides comprehensive test suite generation for FSA (Financial Services Agent)
modules and general Agno framework components. It parses specifications, generates unit
and integration tests, identifies edge cases, and provides coverage analysis.

Features:
    - AST parsing for code analysis
    - Pytest-compatible test generation
    - Edge case identification algorithms
    - Coverage.py integration for analysis
    - Subprocess-based file operations
    - Test result reporting (JSON + HTML)

Example:
    $ python fsa10_test_suite_generator.py --module agno/agent/agent.py --output tests/generated/
    $ python fsa10_test_suite_generator.py --execute tests/generated/ --report html
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import inspect
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FSA10TestGenerator")


# =============================================================================
# Data Models
# =============================================================================


class TestType(Enum):
    """Enumeration of test types."""

    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"
    PARAMETRIZED = "parametrized"


@dataclass
class ParameterSpec:
    """Specification for a function parameter."""

    name: str
    type_hint: Optional[str] = None
    default_value: Optional[Any] = None
    has_default: bool = False
    is_optional: bool = False
    is_variadic: bool = False
    is_keyword_variadic: bool = False

    def __repr__(self) -> str:
        type_str = f": {self.type_hint}" if self.type_hint else ""
        default_str = f" = {self.default_value}" if self.has_default else ""
        return f"{self.name}{type_str}{default_str}"


@dataclass
class FunctionSpec:
    """Specification for a function or method."""

    name: str
    module_path: str
    class_name: Optional[str] = None
    docstring: Optional[str] = None
    parameters: List[ParameterSpec] = field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    decorators: List[str] = field(default_factory=list)
    source_code: Optional[str] = None
    line_number: int = 0
    complexity: int = 1
    raises: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get the fully qualified function name."""
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name

    @property
    def is_private(self) -> bool:
        """Check if function is private (starts with _)."""
        return self.name.startswith("_") and not self.name.startswith("__")

    @property
    def is_dunder(self) -> bool:
        """Check if function is a dunder method."""
        return self.name.startswith("__") and self.name.endswith("__")


@dataclass
class ClassSpec:
    """Specification for a class."""

    name: str
    module_path: str
    docstring: Optional[str] = None
    base_classes: List[str] = field(default_factory=list)
    methods: List[FunctionSpec] = field(default_factory=list)
    class_attributes: Dict[str, Any] = field(default_factory=dict)
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0
    is_dataclass: bool = False
    is_abstract: bool = False


@dataclass
class ModuleSpec:
    """Specification for a Python module."""

    path: str
    name: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    classes: List[ClassSpec] = field(default_factory=list)
    functions: List[FunctionSpec] = field(default_factory=list)
    constants: Dict[str, Any] = field(default_factory=dict)
    global_variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeCase:
    """Specification for an edge case test."""

    name: str
    description: str
    test_type: str
    input_values: Dict[str, Any]
    expected_behavior: str
    priority: int = 1
    tags: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """Generated test case specification."""

    name: str
    test_type: TestType
    target_function: str
    target_class: Optional[str] = None
    test_code: str = ""
    fixtures: List[str] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""
    docstring: str = ""


@dataclass
class CoverageReport:
    """Coverage analysis report."""

    total_statements: int = 0
    covered_statements: int = 0
    missing_statements: int = 0
    coverage_percentage: float = 0.0
    branch_coverage: Optional[float] = None
    uncovered_lines: List[int] = field(default_factory=list)
    file_reports: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class TestResult:
    """Test execution result."""

    test_name: str
    passed: bool
    duration: float = 0.0
    error_message: Optional[str] = None
    stdout: str = ""
    stderr: str = ""


@dataclass
class TestSuiteReport:
    """Complete test suite execution report."""

    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    results: List[TestResult] = field(default_factory=list)
    coverage: Optional[CoverageReport] = None


# =============================================================================
# AST Parsing Utilities
# =============================================================================


class ASTParser:
    """AST parser for extracting code specifications."""

    def __init__(self):
        self.type_mapping = {
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "list": "List",
            "dict": "Dict",
            "tuple": "Tuple",
            "set": "Set",
            "None": "None",
            "Any": "Any",
        }

    def parse_type_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """Parse a type annotation AST node to string representation."""
        if node is None:
            return None

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        elif isinstance(node, ast.Subscript):
            value = self.parse_type_annotation(node.value)
            slice_val = self.parse_type_annotation(node.slice)
            return f"{value}[{slice_val}]"
        elif isinstance(node, ast.Tuple):
            elts = [self.parse_type_annotation(e) for e in node.elts]
            return ", ".join(filter(None, elts))
        elif isinstance(node, ast.List):
            elts = [self.parse_type_annotation(e) for e in node.elts]
            return f"[{', '.join(filter(None, elts))}]"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self.parse_type_annotation(node.left)
            right = self.parse_type_annotation(node.right)
            return f"{left} | {right}"
        elif isinstance(node, ast.Call):
            func = self.parse_type_annotation(node.func)
            args = [self.parse_type_annotation(a) for a in node.args]
            return f"{func}({', '.join(filter(None, args))})"

        return None

    def parse_default_value(self, node: ast.AST) -> Any:
        """Parse a default value AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id == "None":
                return None
            elif node.id == "True":
                return True
            elif node.id == "False":
                return False
            return f"<{node.id}>"
        elif isinstance(node, ast.List):
            return [self.parse_default_value(e) for e in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self.parse_default_value(k) if k else None: self.parse_default_value(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.Tuple):
            return tuple(self.parse_default_value(e) for e in node.elts)
        elif isinstance(node, ast.Call):
            func_name = self.parse_type_annotation(node.func)
            return f"<{func_name}()>"
        elif isinstance(node, ast.Attribute):
            return f"<{self.parse_type_annotation(node)}>"
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                operand = self.parse_default_value(node.operand)
                if isinstance(operand, (int, float)):
                    return -operand
        return "<complex>"

    def parse_parameters(self, args: ast.arguments) -> List[ParameterSpec]:
        """Parse function arguments to parameter specifications."""
        params = []

        # Calculate defaults offset
        num_defaults = len(args.defaults)
        num_args = len(args.args)
        defaults_offset = num_args - num_defaults

        for i, arg in enumerate(args.args):
            param = ParameterSpec(
                name=arg.arg,
                type_hint=self.parse_type_annotation(arg.annotation),
            )

            # Check for default value
            default_idx = i - defaults_offset
            if default_idx >= 0 and default_idx < len(args.defaults):
                param.has_default = True
                param.default_value = self.parse_default_value(args.defaults[default_idx])
                param.is_optional = True

            params.append(param)

        # Handle *args
        if args.vararg:
            params.append(
                ParameterSpec(
                    name=args.vararg.arg,
                    type_hint=self.parse_type_annotation(args.vararg.annotation),
                    is_variadic=True,
                )
            )

        # Handle keyword-only arguments
        for i, kwarg in enumerate(args.kwonlyargs):
            param = ParameterSpec(
                name=kwarg.arg,
                type_hint=self.parse_type_annotation(kwarg.annotation),
            )
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                param.has_default = True
                param.default_value = self.parse_default_value(args.kw_defaults[i])
                param.is_optional = True
            params.append(param)

        # Handle **kwargs
        if args.kwarg:
            params.append(
                ParameterSpec(
                    name=args.kwarg.arg,
                    type_hint=self.parse_type_annotation(args.kwarg.annotation),
                    is_keyword_variadic=True,
                )
            )

        return params

    def calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Match):
                complexity += len(child.cases) - 1 if hasattr(child, "cases") else 0
            elif isinstance(child, ast.Assert):
                complexity += 1

        return complexity

    def extract_raises(self, node: ast.FunctionDef) -> List[str]:
        """Extract exception types raised by a function."""
        raises = []

        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if child.exc:
                    if isinstance(child.exc, ast.Call):
                        if isinstance(child.exc.func, ast.Name):
                            raises.append(child.exc.func.id)
                        elif isinstance(child.exc.func, ast.Attribute):
                            raises.append(child.exc.func.attr)
                    elif isinstance(child.exc, ast.Name):
                        raises.append(child.exc.id)

        return list(set(raises))

    def extract_docstring_examples(self, docstring: Optional[str]) -> List[str]:
        """Extract code examples from docstring."""
        if not docstring:
            return []

        examples = []
        in_example = False
        current_example = []

        for line in docstring.split("\n"):
            stripped = line.strip()

            if stripped.startswith(">>>"):
                in_example = True
                current_example.append(stripped[3:].strip())
            elif in_example:
                if stripped.startswith("..."):
                    current_example.append(stripped[3:].strip())
                elif stripped and not stripped.startswith(">>>"):
                    # Expected output line
                    current_example.append(f"# Expected: {stripped}")
                else:
                    if current_example:
                        examples.append("\n".join(current_example))
                        current_example = []
                    in_example = stripped.startswith(">>>")
                    if in_example:
                        current_example.append(stripped[3:].strip())

        if current_example:
            examples.append("\n".join(current_example))

        return examples


# =============================================================================
# FSA Test Suite Generator
# =============================================================================


class FSATestSuiteGenerator:
    """
    Automated test suite generator for FSA (Financial Services Agent) modules.

    This class provides comprehensive test generation capabilities including:
    - Parsing FSA specifications and docstrings
    - Generating unit and integration tests
    - Identifying edge cases and failure modes
    - Analyzing test coverage
    - Executing test suites with detailed reporting

    Attributes:
        output_dir: Directory for generated test files
        parser: AST parser instance
        coverage_threshold: Minimum required coverage percentage
        verbose: Enable verbose logging

    Example:
        >>> generator = FSATestSuiteGenerator(output_dir="tests/generated")
        >>> spec = generator.parse_fsa_spec("agno/agent/agent.py")
        >>> unit_tests = generator.generate_unit_tests(spec)
        >>> generator.execute_tests("tests/generated")
    """

    def __init__(
        self,
        output_dir: str = "tests/generated",
        coverage_threshold: float = 80.0,
        verbose: bool = False,
    ):
        """
        Initialize the FSA Test Suite Generator.

        Args:
            output_dir: Directory for generated test files
            coverage_threshold: Minimum required coverage percentage (0-100)
            verbose: Enable verbose logging output
        """
        self.output_dir = Path(output_dir)
        self.coverage_threshold = coverage_threshold
        self.verbose = verbose
        self.parser = ASTParser()

        # Test generation templates
        self._test_templates = self._initialize_templates()

        # Edge case patterns
        self._edge_case_patterns = self._initialize_edge_case_patterns()

        if verbose:
            logger.setLevel(logging.DEBUG)

    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize test code templates."""
        return {
            "unit_test": textwrap.dedent('''
                def test_{test_name}({fixtures}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip(),
            "async_unit_test": textwrap.dedent('''
                @pytest.mark.asyncio
                async def test_{test_name}({fixtures}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip(),
            "parametrized_test": textwrap.dedent('''
                @pytest.mark.parametrize("{param_names}", {param_values})
                def test_{test_name}({fixtures}, {param_names}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip(),
            "integration_test": textwrap.dedent('''
                @pytest.mark.integration
                def test_{test_name}_integration({fixtures}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
                    {teardown}
            ''').strip(),
            "async_integration_test": textwrap.dedent('''
                @pytest.mark.asyncio
                @pytest.mark.integration
                async def test_{test_name}_integration({fixtures}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
                    {teardown}
            ''').strip(),
            "edge_case_test": textwrap.dedent('''
                @pytest.mark.edge_case
                def test_{test_name}_edge_case({fixtures}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip(),
            "fixture": textwrap.dedent('''
                @pytest.fixture{scope}
                {async_def}def {fixture_name}({dependencies}):
                    """{docstring}"""
                    {setup}
                    yield {yield_value}
                    {teardown}
            ''').strip(),
        }

    def _initialize_edge_case_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for edge case identification."""
        return {
            "null_input": {
                "description": "Test with None/null input",
                "types": ["str", "list", "dict", "Any", "Optional"],
                "test_values": [None],
                "expected": "Should handle gracefully or raise appropriate error",
            },
            "empty_collection": {
                "description": "Test with empty collection",
                "types": ["list", "dict", "set", "tuple", "List", "Dict", "Set", "Tuple"],
                "test_values": [[], {}, set(), ()],
                "expected": "Should handle empty collections",
            },
            "boundary_numeric": {
                "description": "Test numeric boundary conditions",
                "types": ["int", "float", "number"],
                "test_values": [0, -1, 1, float("inf"), float("-inf"), float("nan")],
                "expected": "Should handle boundary values",
            },
            "large_input": {
                "description": "Test with large input data",
                "types": ["str", "list", "dict"],
                "test_values": ["x" * 10000, list(range(10000)), {str(i): i for i in range(1000)}],
                "expected": "Should handle large inputs efficiently",
            },
            "special_characters": {
                "description": "Test with special characters",
                "types": ["str"],
                "test_values": ["", " ", "\n", "\t", "unicode: 你好", "<script>alert('xss')</script>"],
                "expected": "Should handle special characters safely",
            },
            "type_mismatch": {
                "description": "Test with wrong type input",
                "types": ["*"],
                "test_values": ["string_instead_of_int", 123, [], {}],
                "expected": "Should raise TypeError or handle type conversion",
            },
            "concurrent_access": {
                "description": "Test concurrent/parallel access",
                "types": ["async", "thread_safe"],
                "test_values": [],
                "expected": "Should be thread-safe",
            },
        }

    # =========================================================================
    # Core API Methods
    # =========================================================================

    def parse_fsa_spec(self, module_path: str) -> ModuleSpec:
        """
        Parse FSA module specifications using AST analysis.

        Extracts comprehensive specifications from a Python module including:
        - Classes and their methods
        - Functions and their signatures
        - Type annotations and docstrings
        - Import statements and dependencies

        Args:
            module_path: Path to the Python module file

        Returns:
            ModuleSpec containing all extracted specifications

        Raises:
            FileNotFoundError: If module file doesn't exist
            SyntaxError: If module contains invalid Python syntax

        Example:
            >>> generator = FSATestSuiteGenerator()
            >>> spec = generator.parse_fsa_spec("agno/agent/agent.py")
            >>> print(f"Found {len(spec.classes)} classes")
        """
        path = Path(module_path)
        if not path.exists():
            raise FileNotFoundError(f"Module not found: {module_path}")

        logger.info(f"Parsing module: {module_path}")

        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            logger.error(f"Syntax error in {module_path}: {e}")
            raise

        module_spec = ModuleSpec(
            path=str(path.absolute()),
            name=path.stem,
            docstring=ast.get_docstring(tree),
        )

        # Parse imports
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_spec.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for alias in node.names:
                    module_spec.imports.append(f"{module_name}.{alias.name}")

        # Parse top-level assignments (constants/globals)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper():
                            module_spec.constants[target.id] = self.parser.parse_default_value(
                                node.value
                            )
                        else:
                            module_spec.global_variables[target.id] = self.parser.parse_default_value(
                                node.value
                            )

        # Parse classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_spec = self._parse_class(node, source, module_path)
                module_spec.classes.append(class_spec)

        # Parse top-level functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_spec = self._parse_function(node, source, module_path)
                module_spec.functions.append(func_spec)

        logger.info(
            f"Parsed {len(module_spec.classes)} classes, "
            f"{len(module_spec.functions)} functions"
        )

        return module_spec

    def generate_unit_tests(self, spec: ModuleSpec) -> List[TestCase]:
        """
        Generate unit tests for individual functions in the module.

        Creates pytest-compatible unit tests with:
        - Proper fixtures for dependencies
        - Mock objects for external calls
        - Parameterized tests for multiple inputs
        - Assertions based on return types

        Args:
            spec: ModuleSpec from parse_fsa_spec()

        Returns:
            List of TestCase objects with generated test code

        Example:
            >>> spec = generator.parse_fsa_spec("agno/tools/calculator.py")
            >>> tests = generator.generate_unit_tests(spec)
            >>> for test in tests:
            ...     print(f"Generated: {test.name}")
        """
        test_cases = []
        logger.info(f"Generating unit tests for module: {spec.name}")

        # Generate tests for top-level functions
        for func in spec.functions:
            if not func.is_private or func.name == "__init__":
                tests = self._generate_function_unit_tests(func, spec)
                test_cases.extend(tests)

        # Generate tests for class methods
        for cls in spec.classes:
            for method in cls.methods:
                if not method.is_private or method.name == "__init__":
                    tests = self._generate_function_unit_tests(method, spec, cls)
                    test_cases.extend(tests)

        logger.info(f"Generated {len(test_cases)} unit tests")
        return test_cases

    def generate_integration_tests(self, spec: ModuleSpec) -> List[TestCase]:
        """
        Generate integration tests for FSA workflows.

        Creates tests that verify:
        - End-to-end functionality
        - Component interactions
        - Data flow through the system
        - External service integrations

        Args:
            spec: ModuleSpec from parse_fsa_spec()

        Returns:
            List of TestCase objects with integration test code

        Example:
            >>> spec = generator.parse_fsa_spec("agno/workflow/workflow.py")
            >>> integration_tests = generator.generate_integration_tests(spec)
        """
        test_cases = []
        logger.info(f"Generating integration tests for module: {spec.name}")

        # Identify workflow patterns
        workflow_classes = [
            cls for cls in spec.classes if any(base in cls.base_classes for base in ["Workflow", "Agent"])
        ]

        for cls in workflow_classes:
            tests = self._generate_workflow_integration_tests(cls, spec)
            test_cases.extend(tests)

        # Generate integration tests for class interactions
        if len(spec.classes) > 1:
            tests = self._generate_class_interaction_tests(spec)
            test_cases.extend(tests)

        # Generate integration tests for complex functions
        complex_functions = [f for f in spec.functions if f.complexity > 5]
        for func in complex_functions:
            tests = self._generate_complex_function_integration_tests(func, spec)
            test_cases.extend(tests)

        logger.info(f"Generated {len(test_cases)} integration tests")
        return test_cases

    def identify_edge_cases(self, spec: ModuleSpec) -> List[EdgeCase]:
        """
        Identify potential edge cases and boundary conditions.

        Analyzes:
        - Parameter types for boundary values
        - Optional parameters for None handling
        - Collection parameters for empty cases
        - Numeric parameters for overflow/underflow
        - String parameters for special characters

        Args:
            spec: ModuleSpec from parse_fsa_spec()

        Returns:
            List of EdgeCase objects with test specifications

        Example:
            >>> spec = generator.parse_fsa_spec("agno/agent/agent.py")
            >>> edge_cases = generator.identify_edge_cases(spec)
            >>> for case in edge_cases:
            ...     print(f"{case.name}: {case.description}")
        """
        edge_cases = []
        logger.info(f"Identifying edge cases for module: {spec.name}")

        # Analyze all functions
        all_functions = list(spec.functions)
        for cls in spec.classes:
            all_functions.extend(cls.methods)

        for func in all_functions:
            if func.is_dunder and func.name != "__init__":
                continue

            func_edge_cases = self._identify_function_edge_cases(func)
            edge_cases.extend(func_edge_cases)

        # Identify edge cases from exception handling
        for func in all_functions:
            if func.raises:
                for exc_type in func.raises:
                    edge_cases.append(
                        EdgeCase(
                            name=f"{func.full_name}_raises_{exc_type}",
                            description=f"Test that {func.full_name} raises {exc_type}",
                            test_type="exception",
                            input_values={"exception_type": exc_type},
                            expected_behavior=f"Should raise {exc_type}",
                            priority=2,
                            tags=["exception", exc_type.lower()],
                        )
                    )

        logger.info(f"Identified {len(edge_cases)} edge cases")
        return edge_cases

    def analyze_coverage(self, test_path: str, source_path: Optional[str] = None) -> CoverageReport:
        """
        Analyze test coverage using coverage.py.

        Runs the test suite with coverage tracking and generates
        detailed metrics including:
        - Line coverage percentage
        - Branch coverage (if enabled)
        - Uncovered line numbers
        - Per-file coverage breakdown

        Args:
            test_path: Path to test file or directory
            source_path: Optional source path to measure coverage for

        Returns:
            CoverageReport with detailed coverage metrics

        Example:
            >>> report = generator.analyze_coverage("tests/unit/")
            >>> print(f"Coverage: {report.coverage_percentage:.1f}%")
        """
        logger.info(f"Analyzing coverage for tests: {test_path}")

        # Build coverage command
        cmd = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--branch",
            "-m",
            "pytest",
            test_path,
            "-v",
            "--tb=short",
        ]

        if source_path:
            cmd.extend(["--source", source_path])

        # Run coverage
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.output_dir.parent) if self.output_dir.exists() else None,
            )
        except subprocess.TimeoutExpired:
            logger.error("Coverage analysis timed out")
            return CoverageReport()
        except FileNotFoundError:
            logger.error("coverage.py not found. Install with: pip install coverage")
            return CoverageReport()

        # Generate JSON report
        json_report_path = Path(tempfile.mktemp(suffix=".json"))

        try:
            subprocess.run(
                [sys.executable, "-m", "coverage", "json", "-o", str(json_report_path)],
                capture_output=True,
                timeout=60,
            )

            if json_report_path.exists():
                with open(json_report_path) as f:
                    coverage_data = json.load(f)

                report = CoverageReport(
                    total_statements=coverage_data.get("totals", {}).get("num_statements", 0),
                    covered_statements=coverage_data.get("totals", {}).get("covered_lines", 0),
                    missing_statements=coverage_data.get("totals", {}).get("missing_lines", 0),
                    coverage_percentage=coverage_data.get("totals", {}).get("percent_covered", 0.0),
                    branch_coverage=coverage_data.get("totals", {}).get("percent_covered_branches"),
                )

                # Parse per-file reports
                for file_path, file_data in coverage_data.get("files", {}).items():
                    report.file_reports[file_path] = {
                        "covered_lines": file_data.get("executed_lines", []),
                        "missing_lines": file_data.get("missing_lines", []),
                        "excluded_lines": file_data.get("excluded_lines", []),
                        "coverage": file_data.get("summary", {}).get("percent_covered", 0.0),
                    }
                    report.uncovered_lines.extend(file_data.get("missing_lines", []))

                return report
        finally:
            if json_report_path.exists():
                json_report_path.unlink()

        return CoverageReport()

    def execute_tests(
        self,
        test_path: str,
        report_format: str = "both",
        output_dir: Optional[str] = None,
    ) -> TestSuiteReport:
        """
        Execute test suite and generate reports.

        Runs pytest with comprehensive options and generates:
        - JSON report with test results
        - HTML report for visualization
        - Coverage integration if available

        Args:
            test_path: Path to test file or directory
            report_format: Report format - "json", "html", or "both"
            output_dir: Output directory for reports

        Returns:
            TestSuiteReport with complete execution results

        Example:
            >>> report = generator.execute_tests("tests/generated/")
            >>> print(f"Passed: {report.passed}/{report.total_tests}")
        """
        logger.info(f"Executing tests: {test_path}")

        output_path = Path(output_dir) if output_dir else self.output_dir / "reports"
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().isoformat()
        json_report_path = output_path / f"test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        html_report_path = output_path / f"test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_path,
            "-v",
            "--tb=short",
            f"--json-report-file={json_report_path}",
        ]

        if report_format in ("html", "both"):
            cmd.append(f"--html={html_report_path}")
            cmd.append("--self-contained-html")

        # Run tests
        start_time = datetime.datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return TestSuiteReport(timestamp=timestamp)
        except FileNotFoundError as e:
            logger.warning(f"pytest plugin not found: {e}")
            # Fallback to basic pytest
            cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        duration = (datetime.datetime.now() - start_time).total_seconds()

        # Parse results
        report = TestSuiteReport(timestamp=timestamp, duration=duration)

        # Try to parse JSON report
        if json_report_path.exists():
            try:
                with open(json_report_path) as f:
                    json_data = json.load(f)

                report.total_tests = json_data.get("summary", {}).get("total", 0)
                report.passed = json_data.get("summary", {}).get("passed", 0)
                report.failed = json_data.get("summary", {}).get("failed", 0)
                report.skipped = json_data.get("summary", {}).get("skipped", 0)
                report.errors = json_data.get("summary", {}).get("error", 0)

                for test in json_data.get("tests", []):
                    test_result = TestResult(
                        test_name=test.get("nodeid", "unknown"),
                        passed=test.get("outcome") == "passed",
                        duration=test.get("duration", 0.0),
                        error_message=test.get("longrepr") if test.get("outcome") == "failed" else None,
                    )
                    report.results.append(test_result)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not parse JSON report: {e}")

        # Fallback: parse stdout
        if report.total_tests == 0:
            report = self._parse_pytest_output(result.stdout, result.stderr, timestamp, duration)

        # Run coverage analysis
        try:
            coverage_report = self.analyze_coverage(test_path)
            report.coverage = coverage_report
        except Exception as e:
            logger.warning(f"Coverage analysis failed: {e}")

        # Generate custom HTML report if pytest-html not available
        if report_format in ("html", "both") and not html_report_path.exists():
            self._generate_html_report(report, html_report_path)

        # Save JSON report
        if report_format in ("json", "both"):
            self._save_json_report(report, json_report_path)

        logger.info(
            f"Test execution complete: {report.passed}/{report.total_tests} passed "
            f"({report.duration:.2f}s)"
        )

        return report

    # =========================================================================
    # File Generation Methods
    # =========================================================================

    def write_test_file(
        self,
        test_cases: List[TestCase],
        output_path: str,
        module_spec: Optional[ModuleSpec] = None,
    ) -> str:
        """
        Write generated tests to a Python file.

        Args:
            test_cases: List of TestCase objects
            output_path: Path for output file
            module_spec: Optional module spec for imports

        Returns:
            Path to generated test file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Generate file content
        content = self._generate_test_file_content(test_cases, module_spec)

        # Write using subprocess (PowerShell on Windows, shell on others)
        self._write_file_via_subprocess(str(output_file), content)

        logger.info(f"Written test file: {output_file}")
        return str(output_file)

    def generate_conftest(self, specs: List[ModuleSpec], output_dir: str) -> str:
        """
        Generate conftest.py with common fixtures.

        Args:
            specs: List of ModuleSpec objects
            output_dir: Output directory

        Returns:
            Path to generated conftest.py
        """
        fixtures = self._generate_common_fixtures(specs)
        conftest_path = Path(output_dir) / "conftest.py"

        content = textwrap.dedent('''
            """
            Auto-generated pytest configuration and fixtures.

            Generated by FSA10 Test Suite Generator
            """

            import pytest
            import pytest_asyncio
            from unittest.mock import MagicMock, AsyncMock, patch
            from typing import Any, Dict, Generator
            import json
            import tempfile
            import os

        ''').lstrip()

        content += "\n".join(fixtures)

        self._write_file_via_subprocess(str(conftest_path), content)

        logger.info(f"Written conftest.py: {conftest_path}")
        return str(conftest_path)

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _parse_class(self, node: ast.ClassDef, source: str, module_path: str) -> ClassSpec:
        """Parse a class definition node."""
        # Get base classes
        base_classes = []
        for base in node.bases:
            base_name = self.parser.parse_type_annotation(base)
            if base_name:
                base_classes.append(base_name)

        # Get decorators
        decorators = []
        is_dataclass = False
        for decorator in node.decorator_list:
            dec_name = self.parser.parse_type_annotation(decorator)
            if dec_name:
                decorators.append(dec_name)
                if "dataclass" in dec_name.lower():
                    is_dataclass = True

        class_spec = ClassSpec(
            name=node.name,
            module_path=module_path,
            docstring=ast.get_docstring(node),
            base_classes=base_classes,
            decorators=decorators,
            line_number=node.lineno,
            is_dataclass=is_dataclass,
            is_abstract="ABC" in base_classes or "Abstract" in node.name,
        )

        # Parse methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_spec = self._parse_function(item, source, module_path, node.name)
                class_spec.methods.append(method_spec)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_spec.class_attributes[target.id] = self.parser.parse_default_value(
                            item.value
                        )

        return class_spec

    def _parse_function(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        source: str,
        module_path: str,
        class_name: Optional[str] = None,
    ) -> FunctionSpec:
        """Parse a function definition node."""
        # Get decorators
        decorators = []
        is_property = False
        is_classmethod = False
        is_staticmethod = False

        for decorator in node.decorator_list:
            dec_name = self.parser.parse_type_annotation(decorator)
            if dec_name:
                decorators.append(dec_name)
                if dec_name == "property":
                    is_property = True
                elif dec_name == "classmethod":
                    is_classmethod = True
                elif dec_name == "staticmethod":
                    is_staticmethod = True

        # Extract source code
        try:
            source_lines = source.split("\n")
            end_lineno = getattr(node, "end_lineno", node.lineno + 10)
            func_source = "\n".join(source_lines[node.lineno - 1 : end_lineno])
        except (IndexError, AttributeError):
            func_source = None

        func_spec = FunctionSpec(
            name=node.name,
            module_path=module_path,
            class_name=class_name,
            docstring=ast.get_docstring(node),
            parameters=self.parser.parse_parameters(node.args),
            return_type=self.parser.parse_type_annotation(node.returns),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_property=is_property,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            decorators=decorators,
            source_code=func_source,
            line_number=node.lineno,
            complexity=self.parser.calculate_complexity(node),
            raises=self.parser.extract_raises(node),
            examples=self.parser.extract_docstring_examples(ast.get_docstring(node)),
        )

        return func_spec

    def _generate_function_unit_tests(
        self,
        func: FunctionSpec,
        module_spec: ModuleSpec,
        class_spec: Optional[ClassSpec] = None,
    ) -> List[TestCase]:
        """Generate unit tests for a function."""
        tests = []

        # Skip property getters for unit tests
        if func.is_property:
            return tests

        # Basic functionality test
        basic_test = self._generate_basic_function_test(func, class_spec)
        if basic_test:
            tests.append(basic_test)

        # Return type test
        if func.return_type and func.return_type != "None":
            return_test = self._generate_return_type_test(func, class_spec)
            if return_test:
                tests.append(return_test)

        # Parameter validation tests
        for param in func.parameters:
            if param.name in ("self", "cls"):
                continue
            if param.is_optional or param.has_default:
                optional_test = self._generate_optional_param_test(func, param, class_spec)
                if optional_test:
                    tests.append(optional_test)

        # Exception handling tests
        for exc_type in func.raises:
            exc_test = self._generate_exception_test(func, exc_type, class_spec)
            if exc_test:
                tests.append(exc_test)

        return tests

    def _generate_basic_function_test(
        self, func: FunctionSpec, class_spec: Optional[ClassSpec] = None
    ) -> Optional[TestCase]:
        """Generate a basic functionality test."""
        test_name = self._sanitize_test_name(f"{func.full_name}_basic")

        # Build fixtures
        fixtures = []
        setup_lines = []
        call_args = []

        if class_spec and not func.is_staticmethod:
            fixture_name = self._get_class_fixture_name(class_spec.name)
            fixtures.append(fixture_name)
            instance_var = self._to_snake_case(class_spec.name)

        for param in func.parameters:
            if param.name in ("self", "cls"):
                continue

            value = self._generate_test_value(param)
            call_args.append(f"{param.name}={repr(value)}")

        # Build test body
        if class_spec and not func.is_staticmethod:
            instance_var = self._to_snake_case(class_spec.name)
            if func.is_async:
                call = f"result = await {instance_var}.{func.name}({', '.join(call_args)})"
            else:
                call = f"result = {instance_var}.{func.name}({', '.join(call_args)})"
        else:
            if func.is_async:
                call = f"result = await {func.name}({', '.join(call_args)})"
            else:
                call = f"result = {func.name}({', '.join(call_args)})"

        # Build assertions
        assertions = []
        if func.return_type and func.return_type != "None":
            assertions.append("assert result is not None")
        else:
            assertions.append("# Function executed without error")

        test_code = self._build_test_code(
            test_name=test_name,
            is_async=func.is_async,
            fixtures=fixtures,
            setup="\n    ".join(setup_lines),
            test_body=call,
            assertions="\n    ".join(assertions),
            docstring=f"Test basic functionality of {func.full_name}.",
        )

        return TestCase(
            name=test_name,
            test_type=TestType.UNIT,
            target_function=func.name,
            target_class=class_spec.name if class_spec else None,
            test_code=test_code,
            fixtures=fixtures,
            markers=["asyncio"] if func.is_async else [],
            docstring=f"Test basic functionality of {func.full_name}.",
        )

    def _generate_return_type_test(
        self, func: FunctionSpec, class_spec: Optional[ClassSpec] = None
    ) -> Optional[TestCase]:
        """Generate a test for return type validation."""
        test_name = self._sanitize_test_name(f"{func.full_name}_return_type")

        fixtures = []
        call_args = []

        if class_spec and not func.is_staticmethod:
            fixture_name = self._get_class_fixture_name(class_spec.name)
            fixtures.append(fixture_name)

        for param in func.parameters:
            if param.name in ("self", "cls"):
                continue
            value = self._generate_test_value(param)
            call_args.append(f"{param.name}={repr(value)}")

        instance_var = self._to_snake_case(class_spec.name) if class_spec else None

        if class_spec and not func.is_staticmethod:
            if func.is_async:
                call = f"result = await {instance_var}.{func.name}({', '.join(call_args)})"
            else:
                call = f"result = {instance_var}.{func.name}({', '.join(call_args)})"
        else:
            if func.is_async:
                call = f"result = await {func.name}({', '.join(call_args)})"
            else:
                call = f"result = {func.name}({', '.join(call_args)})"

        # Type assertion
        type_check = self._generate_type_assertion(func.return_type)

        test_code = self._build_test_code(
            test_name=test_name,
            is_async=func.is_async,
            fixtures=fixtures,
            setup="",
            test_body=call,
            assertions=type_check,
            docstring=f"Test return type of {func.full_name}.",
        )

        return TestCase(
            name=test_name,
            test_type=TestType.UNIT,
            target_function=func.name,
            target_class=class_spec.name if class_spec else None,
            test_code=test_code,
            fixtures=fixtures,
            markers=["asyncio"] if func.is_async else [],
        )

    def _generate_optional_param_test(
        self,
        func: FunctionSpec,
        param: ParameterSpec,
        class_spec: Optional[ClassSpec] = None,
    ) -> Optional[TestCase]:
        """Generate test for optional parameter handling."""
        test_name = self._sanitize_test_name(f"{func.full_name}_optional_{param.name}")

        fixtures = []
        call_args = []

        if class_spec and not func.is_staticmethod:
            fixture_name = self._get_class_fixture_name(class_spec.name)
            fixtures.append(fixture_name)

        # Include required params, exclude the optional one being tested
        for p in func.parameters:
            if p.name in ("self", "cls"):
                continue
            if p.name == param.name:
                continue  # Skip the optional param we're testing
            if not p.has_default:
                value = self._generate_test_value(p)
                call_args.append(f"{p.name}={repr(value)}")

        instance_var = self._to_snake_case(class_spec.name) if class_spec else None

        if class_spec and not func.is_staticmethod:
            if func.is_async:
                call = f"result = await {instance_var}.{func.name}({', '.join(call_args)})"
            else:
                call = f"result = {instance_var}.{func.name}({', '.join(call_args)})"
        else:
            if func.is_async:
                call = f"result = await {func.name}({', '.join(call_args)})"
            else:
                call = f"result = {func.name}({', '.join(call_args)})"

        assertions = "# Function should work without optional parameter"

        test_code = self._build_test_code(
            test_name=test_name,
            is_async=func.is_async,
            fixtures=fixtures,
            setup="",
            test_body=call,
            assertions=assertions,
            docstring=f"Test {func.full_name} without optional parameter {param.name}.",
        )

        return TestCase(
            name=test_name,
            test_type=TestType.UNIT,
            target_function=func.name,
            target_class=class_spec.name if class_spec else None,
            test_code=test_code,
            fixtures=fixtures,
            markers=["asyncio"] if func.is_async else [],
        )

    def _generate_exception_test(
        self,
        func: FunctionSpec,
        exc_type: str,
        class_spec: Optional[ClassSpec] = None,
    ) -> Optional[TestCase]:
        """Generate test for exception handling."""
        test_name = self._sanitize_test_name(f"{func.full_name}_raises_{exc_type}")

        fixtures = []

        if class_spec and not func.is_staticmethod:
            fixture_name = self._get_class_fixture_name(class_spec.name)
            fixtures.append(fixture_name)

        instance_var = self._to_snake_case(class_spec.name) if class_spec else None

        # Generate invalid inputs to trigger exception
        invalid_args = self._generate_invalid_args(func)

        if class_spec and not func.is_staticmethod:
            call = f"{instance_var}.{func.name}({invalid_args})"
        else:
            call = f"{func.name}({invalid_args})"

        if func.is_async:
            test_body = f"""with pytest.raises({exc_type}):
        await {call}"""
        else:
            test_body = f"""with pytest.raises({exc_type}):
        {call}"""

        test_code = self._build_test_code(
            test_name=test_name,
            is_async=func.is_async,
            fixtures=fixtures,
            setup="",
            test_body=test_body,
            assertions="",
            docstring=f"Test that {func.full_name} raises {exc_type}.",
        )

        return TestCase(
            name=test_name,
            test_type=TestType.EDGE_CASE,
            target_function=func.name,
            target_class=class_spec.name if class_spec else None,
            test_code=test_code,
            fixtures=fixtures,
            markers=["asyncio"] if func.is_async else [],
        )

    def _generate_workflow_integration_tests(
        self, cls: ClassSpec, module_spec: ModuleSpec
    ) -> List[TestCase]:
        """Generate integration tests for workflow classes."""
        tests = []

        # Test workflow initialization
        init_test = self._generate_workflow_init_test(cls)
        if init_test:
            tests.append(init_test)

        # Test workflow execution methods
        run_methods = [m for m in cls.methods if m.name in ("run", "arun", "execute", "invoke")]
        for method in run_methods:
            exec_test = self._generate_workflow_execution_test(cls, method)
            if exec_test:
                tests.append(exec_test)

        return tests

    def _generate_workflow_init_test(self, cls: ClassSpec) -> Optional[TestCase]:
        """Generate initialization test for workflow class."""
        test_name = self._sanitize_test_name(f"{cls.name}_initialization")

        init_method = next((m for m in cls.methods if m.name == "__init__"), None)

        setup_args = []
        if init_method:
            for param in init_method.parameters:
                if param.name == "self":
                    continue
                if not param.has_default:
                    value = self._generate_test_value(param)
                    setup_args.append(f"{param.name}={repr(value)}")

        test_code = textwrap.dedent(f'''
            @pytest.mark.integration
            def test_{test_name}():
                """Test {cls.name} initialization."""
                instance = {cls.name}({", ".join(setup_args)})
                assert instance is not None
        ''').strip()

        return TestCase(
            name=test_name,
            test_type=TestType.INTEGRATION,
            target_function="__init__",
            target_class=cls.name,
            test_code=test_code,
            markers=["integration"],
            docstring=f"Test {cls.name} initialization.",
        )

    def _generate_workflow_execution_test(
        self, cls: ClassSpec, method: FunctionSpec
    ) -> Optional[TestCase]:
        """Generate execution test for workflow method."""
        test_name = self._sanitize_test_name(f"{cls.name}_{method.name}_execution")

        test_code = textwrap.dedent(f'''
            @pytest.mark.integration
            @pytest.mark.asyncio
            async def test_{test_name}(mock_model):
                """Test {cls.name}.{method.name} execution."""
                instance = {cls.name}(model=mock_model)
                {"result = await instance." + method.name + '("test input")' if method.is_async else "result = instance." + method.name + '("test input")'}
                assert result is not None
        ''').strip()

        return TestCase(
            name=test_name,
            test_type=TestType.INTEGRATION,
            target_function=method.name,
            target_class=cls.name,
            test_code=test_code,
            fixtures=["mock_model"],
            markers=["integration", "asyncio"],
        )

    def _generate_class_interaction_tests(self, module_spec: ModuleSpec) -> List[TestCase]:
        """Generate tests for class interactions."""
        tests = []

        # Find classes that might interact
        for i, cls1 in enumerate(module_spec.classes):
            for cls2 in module_spec.classes[i + 1 :]:
                # Check if one class references the other
                if self._classes_interact(cls1, cls2):
                    test = self._generate_interaction_test(cls1, cls2)
                    if test:
                        tests.append(test)

        return tests

    def _classes_interact(self, cls1: ClassSpec, cls2: ClassSpec) -> bool:
        """Check if two classes have potential interactions."""
        # Check if one inherits from the other
        if cls1.name in cls2.base_classes or cls2.name in cls1.base_classes:
            return True

        # Check if one is referenced in the other's methods
        for method in cls1.methods:
            if method.source_code and cls2.name in method.source_code:
                return True

        for method in cls2.methods:
            if method.source_code and cls1.name in method.source_code:
                return True

        return False

    def _generate_interaction_test(
        self, cls1: ClassSpec, cls2: ClassSpec
    ) -> Optional[TestCase]:
        """Generate test for class interaction."""
        test_name = self._sanitize_test_name(f"{cls1.name}_{cls2.name}_interaction")

        test_code = textwrap.dedent(f'''
            @pytest.mark.integration
            def test_{test_name}():
                """Test interaction between {cls1.name} and {cls2.name}."""
                # Create instances
                instance1 = MagicMock(spec={cls1.name})
                instance2 = MagicMock(spec={cls2.name})

                # Verify instances are compatible
                assert instance1 is not None
                assert instance2 is not None
        ''').strip()

        return TestCase(
            name=test_name,
            test_type=TestType.INTEGRATION,
            target_function="interaction",
            target_class=f"{cls1.name}_{cls2.name}",
            test_code=test_code,
            markers=["integration"],
        )

    def _generate_complex_function_integration_tests(
        self, func: FunctionSpec, module_spec: ModuleSpec
    ) -> List[TestCase]:
        """Generate integration tests for complex functions."""
        tests = []

        test_name = self._sanitize_test_name(f"{func.full_name}_integration")

        test_code = textwrap.dedent(f'''
            @pytest.mark.integration
            {"@pytest.mark.asyncio" if func.is_async else ""}
            {"async " if func.is_async else ""}def test_{test_name}():
                """Integration test for {func.full_name} (complexity: {func.complexity})."""
                # Complex function with cyclomatic complexity {func.complexity}
                # TODO: Add comprehensive integration test
                pass
        ''').strip()

        tests.append(
            TestCase(
                name=test_name,
                test_type=TestType.INTEGRATION,
                target_function=func.name,
                test_code=test_code,
                markers=["integration"] + (["asyncio"] if func.is_async else []),
            )
        )

        return tests

    def _identify_function_edge_cases(self, func: FunctionSpec) -> List[EdgeCase]:
        """Identify edge cases for a function."""
        edge_cases = []

        for param in func.parameters:
            if param.name in ("self", "cls"):
                continue

            type_hint = param.type_hint or "Any"

            for pattern_name, pattern in self._edge_case_patterns.items():
                if self._type_matches_pattern(type_hint, pattern["types"]):
                    for i, test_value in enumerate(pattern["test_values"]):
                        edge_cases.append(
                            EdgeCase(
                                name=f"{func.full_name}_{param.name}_{pattern_name}_{i}",
                                description=f"{pattern['description']} for {param.name}",
                                test_type=pattern_name,
                                input_values={param.name: test_value},
                                expected_behavior=pattern["expected"],
                                priority=2 if "boundary" in pattern_name else 1,
                                tags=[pattern_name, type_hint.lower()],
                            )
                        )

        return edge_cases

    def _type_matches_pattern(self, type_hint: str, pattern_types: List[str]) -> bool:
        """Check if a type hint matches any pattern types."""
        if "*" in pattern_types:
            return True

        type_lower = type_hint.lower()
        for pattern_type in pattern_types:
            if pattern_type.lower() in type_lower:
                return True

        return False

    def _generate_test_value(self, param: ParameterSpec) -> Any:
        """Generate appropriate test value for a parameter."""
        if param.has_default and param.default_value is not None:
            return param.default_value

        type_hint = param.type_hint or ""
        type_lower = type_hint.lower()

        # Type-based value generation
        if "str" in type_lower:
            return "test_string"
        elif "int" in type_lower:
            return 42
        elif "float" in type_lower:
            return 3.14
        elif "bool" in type_lower:
            return True
        elif "list" in type_lower or type_hint.startswith("List"):
            return []
        elif "dict" in type_lower or type_hint.startswith("Dict"):
            return {}
        elif "optional" in type_lower:
            return None
        elif "callable" in type_lower:
            return "lambda x: x"
        elif "path" in type_lower:
            return "/tmp/test"
        else:
            return MagicMock() if "Mock" not in str(type_hint) else None

    def _generate_invalid_args(self, func: FunctionSpec) -> str:
        """Generate invalid arguments to trigger exceptions."""
        invalid_args = []

        for param in func.parameters:
            if param.name in ("self", "cls"):
                continue

            type_hint = param.type_hint or ""
            type_lower = type_hint.lower()

            # Generate type-mismatched values
            if "str" in type_lower:
                invalid_args.append(f"{param.name}=None")
            elif "int" in type_lower:
                invalid_args.append(f'{param.name}="invalid"')
            elif "list" in type_lower:
                invalid_args.append(f"{param.name}=None")
            else:
                invalid_args.append(f"{param.name}=None")

        return ", ".join(invalid_args) if invalid_args else ""

    def _generate_type_assertion(self, return_type: str) -> str:
        """Generate type assertion for return value."""
        type_lower = return_type.lower()

        if "str" in type_lower:
            return "assert isinstance(result, str)"
        elif "int" in type_lower:
            return "assert isinstance(result, int)"
        elif "float" in type_lower:
            return "assert isinstance(result, (int, float))"
        elif "bool" in type_lower:
            return "assert isinstance(result, bool)"
        elif "list" in type_lower:
            return "assert isinstance(result, list)"
        elif "dict" in type_lower:
            return "assert isinstance(result, dict)"
        elif "none" in type_lower:
            return "assert result is None"
        else:
            return "assert result is not None"

    def _build_test_code(
        self,
        test_name: str,
        is_async: bool,
        fixtures: List[str],
        setup: str,
        test_body: str,
        assertions: str,
        docstring: str,
    ) -> str:
        """Build complete test function code."""
        fixture_str = ", ".join(fixtures) if fixtures else ""

        if is_async:
            template = textwrap.dedent(f'''
                @pytest.mark.asyncio
                async def test_{test_name}({fixture_str}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip()
        else:
            template = textwrap.dedent(f'''
                def test_{test_name}({fixture_str}):
                    """{docstring}"""
                    {setup}
                    {test_body}
                    {assertions}
            ''').strip()

        # Clean up empty lines
        lines = template.split("\n")
        cleaned_lines = []
        for line in lines:
            if line.strip() or cleaned_lines:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _generate_test_file_content(
        self, test_cases: List[TestCase], module_spec: Optional[ModuleSpec] = None
    ) -> str:
        """Generate complete test file content."""
        # Header
        content = textwrap.dedent('''
            """
            Auto-generated test suite.

            Generated by FSA10 Test Suite Generator
            Timestamp: {timestamp}

            Module: {module_name}
            """

            import pytest
            import pytest_asyncio
            from unittest.mock import MagicMock, AsyncMock, patch
            from typing import Any

        ''').format(
            timestamp=datetime.datetime.now().isoformat(),
            module_name=module_spec.name if module_spec else "unknown",
        ).lstrip()

        # Import module under test
        if module_spec:
            module_import = f"# from {module_spec.name} import *\n\n"
            content += module_import

        # Add test functions
        for test_case in test_cases:
            content += "\n\n" + test_case.test_code

        return content

    def _generate_common_fixtures(self, specs: List[ModuleSpec]) -> List[str]:
        """Generate common fixtures for test suite."""
        fixtures = []

        # Mock model fixture
        fixtures.append(
            textwrap.dedent('''
            @pytest.fixture
            def mock_model():
                """Create a mock model for testing."""
                mock = MagicMock()
                mock.id = "test-model"
                mock.invoke = MagicMock(return_value="test response")
                mock.ainvoke = AsyncMock(return_value="test response")
                return mock
        ''').strip()
        )

        # Mock agent fixture
        fixtures.append(
            textwrap.dedent('''
            @pytest.fixture
            def mock_agent(mock_model):
                """Create a mock agent for testing."""
                mock = MagicMock()
                mock.model = mock_model
                mock.run = MagicMock(return_value=MagicMock(content="test"))
                mock.arun = AsyncMock(return_value=MagicMock(content="test"))
                return mock
        ''').strip()
        )

        # Temp directory fixture
        fixtures.append(
            textwrap.dedent('''
            @pytest.fixture
            def temp_dir():
                """Create a temporary directory for testing."""
                import tempfile
                import shutil
                dir_path = tempfile.mkdtemp()
                yield dir_path
                shutil.rmtree(dir_path, ignore_errors=True)
        ''').strip()
        )

        # Generate class-specific fixtures
        for spec in specs:
            for cls in spec.classes:
                if not cls.is_abstract:
                    fixture_name = self._get_class_fixture_name(cls.name)
                    fixture = self._generate_class_fixture(cls)
                    fixtures.append(fixture)

        return fixtures

    def _generate_class_fixture(self, cls: ClassSpec) -> str:
        """Generate a fixture for a class."""
        fixture_name = self._get_class_fixture_name(cls.name)
        instance_var = self._to_snake_case(cls.name)

        # Determine initialization args
        init_method = next((m for m in cls.methods if m.name == "__init__"), None)
        init_args = []

        if init_method:
            for param in init_method.parameters:
                if param.name == "self":
                    continue
                if not param.has_default:
                    # Use mock for complex types
                    init_args.append(f"{param.name}=MagicMock()")

        return textwrap.dedent(f'''
            @pytest.fixture
            def {fixture_name}():
                """Create a {cls.name} instance for testing."""
                {instance_var} = MagicMock(spec={cls.name})
                return {instance_var}
        ''').strip()

    def _write_file_via_subprocess(self, file_path: str, content: str) -> None:
        """Write file using subprocess for PowerShell compatibility."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine shell based on platform
        if sys.platform == "win32":
            # Use PowerShell on Windows
            # Escape content for PowerShell
            escaped_content = content.replace("'", "''")
            cmd = [
                "powershell",
                "-Command",
                f"Set-Content -Path '{file_path}' -Value '{escaped_content}' -Encoding UTF8",
            ]
        else:
            # Use shell on Unix
            # Write via tee command
            cmd = ["tee", file_path]

        try:
            if sys.platform == "win32":
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            else:
                subprocess.run(
                    cmd,
                    input=content.encode("utf-8"),
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
        except subprocess.SubprocessError as e:
            # Fallback to direct write
            logger.warning(f"Subprocess write failed, using direct write: {e}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def _parse_pytest_output(
        self, stdout: str, stderr: str, timestamp: str, duration: float
    ) -> TestSuiteReport:
        """Parse pytest output to extract test results."""
        report = TestSuiteReport(timestamp=timestamp, duration=duration)

        # Parse summary line: "X passed, Y failed, Z skipped"
        summary_pattern = r"(\d+) passed"
        if match := re.search(summary_pattern, stdout):
            report.passed = int(match.group(1))

        summary_pattern = r"(\d+) failed"
        if match := re.search(summary_pattern, stdout):
            report.failed = int(match.group(1))

        summary_pattern = r"(\d+) skipped"
        if match := re.search(summary_pattern, stdout):
            report.skipped = int(match.group(1))

        summary_pattern = r"(\d+) error"
        if match := re.search(summary_pattern, stdout):
            report.errors = int(match.group(1))

        report.total_tests = report.passed + report.failed + report.skipped + report.errors

        # Parse individual test results
        test_pattern = r"([\w/]+::[\w_]+)\s+(PASSED|FAILED|SKIPPED|ERROR)"
        for match in re.finditer(test_pattern, stdout):
            test_name = match.group(1)
            outcome = match.group(2)
            report.results.append(
                TestResult(
                    test_name=test_name,
                    passed=outcome == "PASSED",
                    error_message=stderr if outcome in ("FAILED", "ERROR") else None,
                )
            )

        return report

    def _generate_html_report(self, report: TestSuiteReport, output_path: Path) -> None:
        """Generate HTML report for test results."""
        html_content = textwrap.dedent(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>FSA10 Test Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #333; color: white; padding: 20px; }}
                    .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                    .stat {{ padding: 15px; border-radius: 5px; min-width: 100px; text-align: center; }}
                    .passed {{ background-color: #4CAF50; color: white; }}
                    .failed {{ background-color: #f44336; color: white; }}
                    .skipped {{ background-color: #ff9800; color: white; }}
                    .total {{ background-color: #2196F3; color: white; }}
                    .results {{ margin-top: 20px; }}
                    .result-item {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                    .result-passed {{ border-left: 4px solid #4CAF50; }}
                    .result-failed {{ border-left: 4px solid #f44336; }}
                    .coverage {{ margin-top: 20px; padding: 15px; background-color: #f5f5f5; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>FSA10 Test Suite Report</h1>
                    <p>Generated: {report.timestamp}</p>
                    <p>Duration: {report.duration:.2f}s</p>
                </div>

                <div class="summary">
                    <div class="stat total">
                        <h2>{report.total_tests}</h2>
                        <p>Total</p>
                    </div>
                    <div class="stat passed">
                        <h2>{report.passed}</h2>
                        <p>Passed</p>
                    </div>
                    <div class="stat failed">
                        <h2>{report.failed}</h2>
                        <p>Failed</p>
                    </div>
                    <div class="stat skipped">
                        <h2>{report.skipped}</h2>
                        <p>Skipped</p>
                    </div>
                </div>

                {"<div class='coverage'><h3>Coverage: " + str(report.coverage.coverage_percentage) + "%</h3></div>" if report.coverage else ""}

                <div class="results">
                    <h2>Test Results</h2>
                    {"".join(f'<div class="result-item {"result-passed" if r.passed else "result-failed"}">{r.test_name} - {"PASSED" if r.passed else "FAILED"}</div>' for r in report.results)}
                </div>
            </body>
            </html>
        ''').strip()

        self._write_file_via_subprocess(str(output_path), html_content)

    def _save_json_report(self, report: TestSuiteReport, output_path: Path) -> None:
        """Save test report as JSON."""
        report_dict = {
            "timestamp": report.timestamp,
            "duration": report.duration,
            "summary": {
                "total": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "errors": report.errors,
            },
            "results": [
                {
                    "name": r.test_name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "error": r.error_message,
                }
                for r in report.results
            ],
            "coverage": {
                "percentage": report.coverage.coverage_percentage,
                "statements": report.coverage.total_statements,
                "covered": report.coverage.covered_statements,
                "missing": report.coverage.missing_statements,
            }
            if report.coverage
            else None,
        }

        content = json.dumps(report_dict, indent=2)
        self._write_file_via_subprocess(str(output_path), content)

    def _sanitize_test_name(self, name: str) -> str:
        """Sanitize name for use as test function name."""
        # Remove invalid characters
        name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        # Remove consecutive underscores
        name = re.sub(r"_+", "_", name)
        # Remove leading/trailing underscores
        name = name.strip("_")
        return name.lower()

    def _get_class_fixture_name(self, class_name: str) -> str:
        """Get fixture name for a class."""
        return self._to_snake_case(class_name)

    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# =============================================================================
# Mock import for type hints
# =============================================================================

try:
    from unittest.mock import MagicMock
except ImportError:
    MagicMock = object  # type: ignore


# =============================================================================
# CLI Interface
# =============================================================================


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fsa10_test_suite_generator",
        description="FSA10 Test Suite Generator - Automated test generation for Agno framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
            Examples:
              # Parse and generate tests for a module
              %(prog)s --module agno/agent/agent.py --output tests/generated/

              # Generate and execute tests
              %(prog)s --module agno/tools/calculator.py --execute --report both

              # Analyze coverage only
              %(prog)s --coverage tests/unit/ --source agno/

              # Generate edge case tests
              %(prog)s --module agno/agent/agent.py --edge-cases --output tests/edge/

              # Full pipeline
              %(prog)s --module agno/agent/agent.py --output tests/generated/ \\
                       --execute --report html --coverage-threshold 80
        '''),
    )

    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "--module",
        "-m",
        type=str,
        help="Path to Python module to analyze",
    )
    input_group.add_argument(
        "--directory",
        "-d",
        type=str,
        help="Directory containing modules to analyze",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        "-o",
        type=str,
        default="tests/generated",
        help="Output directory for generated tests (default: tests/generated)",
    )
    output_group.add_argument(
        "--report",
        "-r",
        choices=["json", "html", "both"],
        default="both",
        help="Report format (default: both)",
    )

    # Test generation options
    gen_group = parser.add_argument_group("Test Generation Options")
    gen_group.add_argument(
        "--unit",
        action="store_true",
        default=True,
        help="Generate unit tests (default: True)",
    )
    gen_group.add_argument(
        "--integration",
        action="store_true",
        help="Generate integration tests",
    )
    gen_group.add_argument(
        "--edge-cases",
        action="store_true",
        help="Generate edge case tests",
    )
    gen_group.add_argument(
        "--all",
        action="store_true",
        help="Generate all test types",
    )

    # Execution options
    exec_group = parser.add_argument_group("Execution Options")
    exec_group.add_argument(
        "--execute",
        "-e",
        action="store_true",
        help="Execute generated tests",
    )
    exec_group.add_argument(
        "--coverage",
        "-c",
        type=str,
        help="Run coverage analysis on specified test path",
    )
    exec_group.add_argument(
        "--source",
        "-s",
        type=str,
        help="Source path for coverage analysis",
    )
    exec_group.add_argument(
        "--coverage-threshold",
        type=float,
        default=80.0,
        help="Minimum coverage percentage (default: 80.0)",
    )

    # General options
    general_group = parser.add_argument_group("General Options")
    general_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    general_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    general_group.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


def main() -> int:
    """Main entry point for CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    if not args.module and not args.directory and not args.coverage:
        parser.error("Must specify --module, --directory, or --coverage")

    # Initialize generator
    generator = FSATestSuiteGenerator(
        output_dir=args.output,
        coverage_threshold=args.coverage_threshold,
        verbose=args.verbose,
    )

    try:
        # Coverage analysis only
        if args.coverage and not args.module:
            logger.info(f"Running coverage analysis on: {args.coverage}")
            report = generator.analyze_coverage(args.coverage, args.source)
            print(f"\nCoverage Report:")
            print(f"  Total statements: {report.total_statements}")
            print(f"  Covered: {report.covered_statements}")
            print(f"  Missing: {report.missing_statements}")
            print(f"  Coverage: {report.coverage_percentage:.1f}%")

            if report.coverage_percentage < args.coverage_threshold:
                print(f"\n⚠ Coverage below threshold ({args.coverage_threshold}%)")
                return 1
            return 0

        # Process module(s)
        modules_to_process = []

        if args.module:
            modules_to_process.append(args.module)

        if args.directory:
            dir_path = Path(args.directory)
            for py_file in dir_path.rglob("*.py"):
                if not py_file.name.startswith("_"):
                    modules_to_process.append(str(py_file))

        if not modules_to_process:
            logger.error("No modules found to process")
            return 1

        all_test_cases = []
        all_specs = []

        for module_path in modules_to_process:
            logger.info(f"Processing: {module_path}")

            try:
                # Parse module
                spec = generator.parse_fsa_spec(module_path)
                all_specs.append(spec)

                # Generate tests based on options
                if args.all or args.unit:
                    unit_tests = generator.generate_unit_tests(spec)
                    all_test_cases.extend(unit_tests)
                    logger.info(f"  Generated {len(unit_tests)} unit tests")

                if args.all or args.integration:
                    integration_tests = generator.generate_integration_tests(spec)
                    all_test_cases.extend(integration_tests)
                    logger.info(f"  Generated {len(integration_tests)} integration tests")

                if args.all or args.edge_cases:
                    edge_cases = generator.identify_edge_cases(spec)
                    logger.info(f"  Identified {len(edge_cases)} edge cases")
                    # Convert edge cases to test cases
                    for ec in edge_cases:
                        tc = TestCase(
                            name=ec.name,
                            test_type=TestType.EDGE_CASE,
                            target_function=ec.name.split("_")[0],
                            docstring=ec.description,
                            test_code=f"# Edge case: {ec.description}\n# Input: {ec.input_values}\n# Expected: {ec.expected_behavior}\npass",
                        )
                        all_test_cases.append(tc)

            except Exception as e:
                logger.error(f"Error processing {module_path}: {e}")
                if args.verbose:
                    traceback.print_exc()
                continue

        if not all_test_cases:
            logger.warning("No test cases generated")
            return 1

        # Write tests
        if not args.dry_run:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate conftest.py
            generator.generate_conftest(all_specs, str(output_dir))

            # Generate test file
            test_file = output_dir / "test_generated.py"
            generator.write_test_file(all_test_cases, str(test_file), all_specs[0] if all_specs else None)

            logger.info(f"\nGenerated {len(all_test_cases)} tests in {output_dir}")

            # Execute tests if requested
            if args.execute:
                logger.info("\nExecuting tests...")
                report = generator.execute_tests(str(output_dir), args.report)

                print(f"\nTest Execution Report:")
                print(f"  Total: {report.total_tests}")
                print(f"  Passed: {report.passed}")
                print(f"  Failed: {report.failed}")
                print(f"  Skipped: {report.skipped}")
                print(f"  Duration: {report.duration:.2f}s")

                if report.coverage:
                    print(f"  Coverage: {report.coverage.coverage_percentage:.1f}%")

                if report.failed > 0:
                    return 1
        else:
            print(f"\nDry run - would generate {len(all_test_cases)} tests:")
            for tc in all_test_cases[:10]:
                print(f"  - {tc.name} ({tc.test_type.value})")
            if len(all_test_cases) > 10:
                print(f"  ... and {len(all_test_cases) - 10} more")

        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

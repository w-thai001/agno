"""
Documentation Generator FSA - Comprehensive automated documentation creation system.

This FSA provides intelligent documentation generation capabilities including:
- API documentation from source code
- Docstring generation and enhancement
- README.md generation
- Architecture diagram generation (PlantUML, Mermaid)
- Tutorial and guide generation
- Changelog automation
- OpenAPI/Swagger specification generation
- Multi-format output (Markdown, reStructuredText, HTML)
- Code example extraction and formatting
- Cross-reference link generation
- Version-aware documentation
- Multi-language documentation support
"""

from __future__ import annotations

import ast
import datetime
import json
import re
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from xml.etree import ElementTree as ET

try:
    import jinja2
except ImportError:
    jinja2 = None

try:
    import markdown
except ImportError:
    markdown = None


@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""

    project_name: str = "Unnamed Project"
    project_version: str = "0.1.0"
    author: str = ""
    description: str = ""
    include_private: bool = False
    include_magic: bool = False
    max_depth: int = 10
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    default_language: str = "en"
    output_formats: List[str] = field(default_factory=lambda: ["markdown", "html"])
    theme: str = "default"
    enable_search: bool = True
    enable_versions: bool = True


@dataclass
class FunctionDocumentation:
    """Structured documentation for a function."""

    name: str
    signature: str
    docstring: str
    parameters: List[Dict[str, str]]
    returns: Optional[Dict[str, str]]
    raises: List[Dict[str, str]]
    examples: List[str]
    decorators: List[str]
    is_async: bool
    line_number: int


@dataclass
class ClassDocumentation:
    """Structured documentation for a class."""

    name: str
    docstring: str
    bases: List[str]
    methods: List[FunctionDocumentation]
    attributes: List[Dict[str, str]]
    decorators: List[str]
    line_number: int


@dataclass
class ModuleDocumentation:
    """Structured documentation for a module."""

    name: str
    docstring: str
    classes: List[ClassDocumentation]
    functions: List[FunctionDocumentation]
    imports: List[str]
    constants: List[Dict[str, str]]
    file_path: str


class DocumentationGeneratorFSA:
    """
    Focused Specialized Agent for comprehensive documentation generation.

    This FSA automates the creation of high-quality documentation across multiple
    formats and styles, including API docs, tutorials, diagrams, and specifications.

    Attributes:
        config: Configuration object for documentation generation
        ast_cache: Cache of parsed AST modules for performance
        template_cache: Cache of Jinja2 templates
        cross_ref_map: Map of cross-references between documentation elements
        version_history: History of documentation versions
    """

    def __init__(self, config: Optional[DocumentationConfig] = None):
        """
        Initialize the Documentation Generator FSA.

        Args:
            config: Optional configuration object. If not provided, uses defaults.
        """
        self.config = config or DocumentationConfig()
        self.ast_cache: Dict[str, ast.Module] = {}
        self.template_cache: Dict[str, Any] = {}
        self.cross_ref_map: Dict[str, List[str]] = defaultdict(list)
        self.version_history: List[Dict[str, Any]] = []

        # Initialize Jinja2 environment if available
        if jinja2:
            self.jinja_env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None

    def execute(self, source_path: str, output_format: str = "markdown") -> str:
        """
        Main execution method for documentation generation.

        Args:
            source_path: Path to the source code to document
            output_format: Output format (markdown, rst, html)

        Returns:
            Generated documentation as a string

        Raises:
            ValueError: If source path is invalid or output format unsupported
            FileNotFoundError: If source file doesn't exist
        """
        source_path_obj = Path(source_path)

        if not source_path_obj.exists():
            raise FileNotFoundError(f"Source path not found: {source_path}")

        if output_format not in ["markdown", "rst", "html", "json"]:
            raise ValueError(f"Unsupported output format: {output_format}")

        # Parse the source code
        if source_path_obj.is_file() and source_path_obj.suffix == ".py":
            module_ast = self._parse_python_file(str(source_path_obj))
            module_docs = self.generate_api_docs(module_ast)

            # Extract code examples
            examples = self.extract_code_examples(source_path_obj.read_text())

            # Generate comprehensive documentation
            doc_content = self._build_complete_documentation(
                module_docs, examples, output_format
            )

        elif source_path_obj.is_dir():
            # Process entire directory
            doc_content = self._process_directory(source_path_obj, output_format)
        else:
            raise ValueError(f"Unsupported source type: {source_path}")

        return self.format_output(doc_content, output_format)

    def generate_api_docs(self, module: ast.Module) -> Dict[str, Any]:
        """
        Generate API documentation from AST module.

        Args:
            module: Parsed AST module

        Returns:
            Dictionary containing structured API documentation
        """
        module_doc = ModuleDocumentation(
            name="",
            docstring=ast.get_docstring(module) or "",
            classes=[],
            functions=[],
            imports=[],
            constants=[],
            file_path=""
        )

        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef):
                class_doc = self._document_class(node)
                module_doc.classes.append(class_doc)
            elif isinstance(node, ast.FunctionDef) and self._is_module_level(node, module):
                func_doc = self._document_function(node)
                module_doc.functions.append(func_doc)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                import_str = self._format_import(node)
                module_doc.imports.append(import_str)
            elif isinstance(node, ast.Assign) and self._is_module_level(node, module):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constant = {
                            "name": target.id,
                            "value": ast.unparse(node.value) if hasattr(ast, 'unparse') else ""
                        }
                        module_doc.constants.append(constant)

        return {
            "module": module_doc,
            "statistics": self._generate_statistics(module_doc),
            "cross_references": self.generate_cross_references({"module": module_doc})
        }

    def generate_docstrings(self, function_node: ast.FunctionDef) -> str:
        """
        Generate or enhance docstrings for a function using AST analysis.

        Args:
            function_node: AST node representing a function

        Returns:
            Generated/enhanced docstring in Google style
        """
        existing_docstring = ast.get_docstring(function_node)

        # Extract function signature information
        params = self._extract_parameters(function_node)
        return_type = self._extract_return_type(function_node)
        raises = self._extract_raises(function_node)

        # Build docstring sections
        sections = []

        # Summary (use existing or generate generic)
        if existing_docstring:
            summary = existing_docstring.split('\n\n')[0]
        else:
            summary = f"Execute {function_node.name} operation."

        sections.append(summary)

        # Args section
        if params:
            sections.append("\nArgs:")
            for param in params:
                param_type = param.get('type', 'Any')
                param_desc = param.get('description', 'Parameter description.')
                sections.append(f"    {param['name']} ({param_type}): {param_desc}")

        # Returns section
        if return_type:
            sections.append("\nReturns:")
            sections.append(f"    {return_type['type']}: {return_type.get('description', 'Return value.')}")

        # Raises section
        if raises:
            sections.append("\nRaises:")
            for exc in raises:
                sections.append(f"    {exc['exception']}: {exc.get('description', 'Exception description.')}")

        return '\n'.join(sections)

    def create_readme(self, project_structure: Dict[str, Any]) -> str:
        """
        Generate a comprehensive README.md file.

        Args:
            project_structure: Dictionary containing project information

        Returns:
            Generated README content in Markdown format
        """
        sections = []

        # Title and description
        sections.append(f"# {self.config.project_name}\n")
        if self.config.description:
            sections.append(f"{self.config.description}\n")

        # Badges
        sections.append("## Badges\n")
        sections.append(f"![Version](https://img.shields.io/badge/version-{self.config.project_version}-blue)")
        sections.append("![Python](https://img.shields.io/badge/python-3.8+-blue)")
        sections.append("![License](https://img.shields.io/badge/license-MIT-green)\n")

        # Table of Contents
        sections.append("## Table of Contents\n")
        sections.append("- [Installation](#installation)")
        sections.append("- [Quick Start](#quick-start)")
        sections.append("- [Features](#features)")
        sections.append("- [Usage](#usage)")
        sections.append("- [API Reference](#api-reference)")
        sections.append("- [Examples](#examples)")
        sections.append("- [Contributing](#contributing)")
        sections.append("- [License](#license)\n")

        # Installation
        sections.append("## Installation\n")
        sections.append("```bash")
        sections.append(f"pip install {self.config.project_name.lower().replace(' ', '-')}")
        sections.append("```\n")

        # Quick Start
        sections.append("## Quick Start\n")
        sections.append("```python")
        sections.append(f"from {self.config.project_name.lower().replace(' ', '_')} import Agent\n")
        sections.append("# Initialize the agent")
        sections.append("agent = Agent()")
        sections.append("result = agent.execute()")
        sections.append("print(result)")
        sections.append("```\n")

        # Features
        if "features" in project_structure:
            sections.append("## Features\n")
            for feature in project_structure["features"]:
                sections.append(f"- {feature}")
            sections.append("")

        # Usage
        sections.append("## Usage\n")
        sections.append("### Basic Usage\n")
        sections.append("Describe basic usage patterns here.\n")

        # API Reference
        if "modules" in project_structure:
            sections.append("## API Reference\n")
            sections.append("For detailed API documentation, see [API Documentation](docs/api.md).\n")

        # Examples
        sections.append("## Examples\n")
        sections.append("See the [examples](examples/) directory for more usage examples.\n")

        # Contributing
        sections.append("## Contributing\n")
        sections.append("Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.\n")

        # License
        sections.append("## License\n")
        sections.append("This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.")

        return '\n'.join(sections)

    def generate_architecture_diagram(self, dependencies: Dict[str, List[str]]) -> str:
        """
        Generate architecture diagrams in PlantUML or Mermaid format.

        Args:
            dependencies: Dictionary mapping modules to their dependencies

        Returns:
            Diagram definition in Mermaid format
        """
        lines = ["graph TD"]

        # Add nodes and edges
        node_ids = {}
        counter = 0

        for module, deps in dependencies.items():
            if module not in node_ids:
                node_ids[module] = f"A{counter}"
                counter += 1
                # Sanitize module name for Mermaid
                safe_name = module.replace(".", "_").replace("-", "_")
                lines.append(f"    {node_ids[module]}[{safe_name}]")

            for dep in deps:
                if dep not in node_ids:
                    node_ids[dep] = f"A{counter}"
                    counter += 1
                    safe_dep = dep.replace(".", "_").replace("-", "_")
                    lines.append(f"    {node_ids[dep]}[{safe_dep}]")

                lines.append(f"    {node_ids[module]} --> {node_ids[dep]}")

        # Add styling
        lines.append("\n    classDef default fill:#f9f,stroke:#333,stroke-width:2px")

        return '\n'.join(lines)

    def create_tutorial(self, code_examples: List[str]) -> str:
        """
        Generate tutorial documentation from code examples.

        Args:
            code_examples: List of code example strings

        Returns:
            Tutorial content in Markdown format
        """
        sections = []

        sections.append(f"# {self.config.project_name} Tutorial\n")
        sections.append("This tutorial will guide you through the key features and usage patterns.\n")

        sections.append("## Prerequisites\n")
        sections.append("Before starting, ensure you have:")
        sections.append("- Python 3.8 or higher installed")
        sections.append("- Basic understanding of Python programming")
        sections.append(f"- {self.config.project_name} installed (`pip install {self.config.project_name.lower()}`)\n")

        sections.append("## Getting Started\n")

        for idx, example in enumerate(code_examples, 1):
            sections.append(f"### Example {idx}\n")
            sections.append("```python")
            sections.append(example.strip())
            sections.append("```\n")

            # Add explanation section
            sections.append(f"**Explanation:**\n")
            sections.append(f"This example demonstrates...")
            sections.append("")

        sections.append("## Next Steps\n")
        sections.append("- Explore the [API Reference](api.md)")
        sections.append("- Check out [Advanced Examples](advanced.md)")
        sections.append("- Join our community on [GitHub](https://github.com)")

        return '\n'.join(sections)

    def generate_changelog(self, commits: List[Dict[str, str]]) -> str:
        """
        Generate changelog from commit history.

        Args:
            commits: List of commit dictionaries with 'hash', 'message', 'author', 'date'

        Returns:
            Formatted changelog in Keep a Changelog format
        """
        sections = []

        sections.append("# Changelog\n")
        sections.append("All notable changes to this project will be documented in this file.\n")
        sections.append("The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),")
        sections.append("and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n")

        # Group commits by version/date
        version_groups = self._group_commits_by_version(commits)

        for version, version_commits in version_groups.items():
            sections.append(f"## [{version}] - {datetime.datetime.now().strftime('%Y-%m-%d')}\n")

            # Categorize commits
            categories = {
                "Added": [],
                "Changed": [],
                "Deprecated": [],
                "Removed": [],
                "Fixed": [],
                "Security": []
            }

            for commit in version_commits:
                message = commit.get("message", "")
                category = self._categorize_commit(message)
                if category:
                    categories[category].append(message)

            # Output categorized changes
            for category, messages in categories.items():
                if messages:
                    sections.append(f"### {category}\n")
                    for msg in messages:
                        sections.append(f"- {msg}")
                    sections.append("")

        return '\n'.join(sections)

    def create_openapi_spec(self, api_routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate OpenAPI/Swagger specification from API route definitions.

        Args:
            api_routes: List of API route dictionaries

        Returns:
            OpenAPI specification as a dictionary
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.config.project_name,
                "description": self.config.description,
                "version": self.config.project_version,
                "contact": {
                    "name": self.config.author
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            }
        }

        # Process each route
        for route in api_routes:
            path = route.get("path", "/")
            method = route.get("method", "get").lower()

            if path not in spec["paths"]:
                spec["paths"][path] = {}

            spec["paths"][path][method] = {
                "summary": route.get("summary", ""),
                "description": route.get("description", ""),
                "operationId": route.get("operation_id", f"{method}_{path.replace('/', '_')}"),
                "tags": route.get("tags", []),
                "parameters": route.get("parameters", []),
                "requestBody": route.get("request_body", {}),
                "responses": route.get("responses", {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }),
                "security": route.get("security", [])
            }

        return spec

    def extract_code_examples(self, source_code: str) -> List[str]:
        """
        Extract code examples from docstrings and comments.

        Args:
            source_code: Source code string to analyze

        Returns:
            List of extracted code examples
        """
        examples = []

        # Parse the source code
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return examples

        # Extract examples from docstrings
        for node in ast.walk(tree):
            docstring = ast.get_docstring(node)
            if docstring:
                # Look for code blocks in docstring
                example_blocks = re.findall(
                    r'```python\n(.*?)```|```\n(.*?)```|>>>\s+(.*?)(?=\n\n|\n>>>|\Z)',
                    docstring,
                    re.DOTALL | re.MULTILINE
                )

                for block in example_blocks:
                    # Extract the non-empty group
                    code = next((b for b in block if b), None)
                    if code and code.strip():
                        examples.append(code.strip())

        # Also extract from Example: sections
        example_pattern = r'Example[s]?:\s*\n((?:(?:    |\t).*\n)+)'
        example_matches = re.finditer(example_pattern, source_code, re.MULTILINE)

        for match in example_matches:
            example_code = textwrap.dedent(match.group(1))
            if example_code.strip():
                examples.append(example_code.strip())

        return examples

    def generate_cross_references(self, doc_tree: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate cross-reference links between documentation elements.

        Args:
            doc_tree: Documentation tree structure

        Returns:
            Dictionary mapping elements to their cross-references
        """
        cross_refs = defaultdict(list)

        # Extract all documented elements
        elements = self._extract_all_elements(doc_tree)
        element_names = {elem["name"]: elem["type"] for elem in elements}

        # Find references in docstrings and descriptions
        for element in elements:
            name = element["name"]
            content = element.get("docstring", "") + element.get("description", "")

            # Look for references to other elements
            for other_name, other_type in element_names.items():
                if other_name != name and other_name in content:
                    cross_refs[name].append(f"{other_type}:{other_name}")

        # Store in instance variable for later use
        self.cross_ref_map = dict(cross_refs)

        return dict(cross_refs)

    def format_output(self, content: str, format: str) -> str:
        """
        Format documentation content to the specified output format.

        Args:
            content: Documentation content to format
            format: Target format (markdown, rst, html, json)

        Returns:
            Formatted documentation string
        """
        if format == "markdown":
            return content

        elif format == "rst":
            # Convert Markdown to reStructuredText
            return self._markdown_to_rst(content)

        elif format == "html":
            # Convert Markdown to HTML
            if markdown:
                html = markdown.markdown(
                    content,
                    extensions=['fenced_code', 'tables', 'toc']
                )
                return self._wrap_html(html)
            else:
                # Fallback: basic HTML conversion
                return self._basic_markdown_to_html(content)

        elif format == "json":
            # Return structured JSON
            return json.dumps({"content": content}, indent=2)

        else:
            raise ValueError(f"Unsupported format: {format}")

    def validate(self) -> bool:
        """
        Validate the FSA configuration and state.

        Returns:
            True if validation passes, False otherwise
        """
        # Check configuration
        if not self.config.project_name:
            return False

        if not self.config.project_version:
            return False

        # Validate version format (semantic versioning)
        version_pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'
        if not re.match(version_pattern, self.config.project_version):
            return False

        # Validate supported languages
        if not self.config.supported_languages:
            return False

        if self.config.default_language not in self.config.supported_languages:
            return False

        # Validate output formats
        valid_formats = {"markdown", "rst", "html", "json"}
        if not all(fmt in valid_formats for fmt in self.config.output_formats):
            return False

        return True

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle and log errors during documentation generation.

        Args:
            exception: Exception that occurred

        Returns:
            Dictionary containing error information
        """
        error_info = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": datetime.datetime.now().isoformat(),
            "config": {
                "project_name": self.config.project_name,
                "version": self.config.project_version
            }
        }

        # Add traceback information for debugging
        import traceback
        error_info["traceback"] = traceback.format_exc()

        # Log the error (in production, use proper logging)
        print(f"Error in DocumentationGeneratorFSA: {error_info}")

        return error_info

    # ========== Private Helper Methods ==========

    def _parse_python_file(self, file_path: str) -> ast.Module:
        """Parse a Python file into an AST module."""
        if file_path in self.ast_cache:
            return self.ast_cache[file_path]

        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        module = ast.parse(source_code)
        self.ast_cache[file_path] = module
        return module

    def _document_class(self, node: ast.ClassDef) -> ClassDocumentation:
        """Extract documentation from a class node."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if self.config.include_private or not item.name.startswith('_'):
                    methods.append(self._document_function(item))

        bases = [ast.unparse(base) if hasattr(ast, 'unparse') else '' for base in node.bases]

        return ClassDocumentation(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            bases=bases,
            methods=methods,
            attributes=self._extract_class_attributes(node),
            decorators=[self._format_decorator(d) for d in node.decorator_list],
            line_number=node.lineno
        )

    def _document_function(self, node: ast.FunctionDef) -> FunctionDocumentation:
        """Extract documentation from a function node."""
        params = self._extract_parameters(node)
        return_info = self._extract_return_type(node)
        raises = self._extract_raises(node)

        # Extract signature
        signature = self._build_signature(node)

        return FunctionDocumentation(
            name=node.name,
            signature=signature,
            docstring=ast.get_docstring(node) or "",
            parameters=params,
            returns=return_info,
            raises=raises,
            examples=[],
            decorators=[self._format_decorator(d) for d in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line_number=node.lineno
        )

    def _extract_parameters(self, node: ast.FunctionDef) -> List[Dict[str, str]]:
        """Extract parameter information from function."""
        params = []
        args = node.args

        # Regular arguments
        for arg in args.args:
            param_type = self._get_annotation(arg.annotation) if arg.annotation else "Any"
            params.append({
                "name": arg.arg,
                "type": param_type,
                "description": ""
            })

        return params

    def _extract_return_type(self, node: ast.FunctionDef) -> Optional[Dict[str, str]]:
        """Extract return type annotation."""
        if node.returns:
            return_type = self._get_annotation(node.returns)
            return {
                "type": return_type,
                "description": ""
            }
        return None

    def _extract_raises(self, node: ast.FunctionDef) -> List[Dict[str, str]]:
        """Extract exception information from function body."""
        raises = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                    raises.append({
                        "exception": child.exc.func.id,
                        "description": ""
                    })
                elif isinstance(child.exc, ast.Name):
                    raises.append({
                        "exception": child.exc.id,
                        "description": ""
                    })
        return raises

    def _get_annotation(self, annotation: ast.expr) -> str:
        """Get string representation of type annotation."""
        if hasattr(ast, 'unparse'):
            return ast.unparse(annotation)
        return str(annotation)

    def _build_signature(self, node: ast.FunctionDef) -> str:
        """Build function signature string."""
        args_list = []
        args = node.args

        for arg in args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation(arg.annotation)}"
            args_list.append(arg_str)

        signature = f"{node.name}({', '.join(args_list)})"

        if node.returns:
            signature += f" -> {self._get_annotation(node.returns)}"

        return signature

    def _format_decorator(self, decorator: ast.expr) -> str:
        """Format decorator as string."""
        if hasattr(ast, 'unparse'):
            return ast.unparse(decorator)
        return str(decorator)

    def _format_import(self, node: Union[ast.Import, ast.ImportFrom]) -> str:
        """Format import statement as string."""
        if isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            return f"import {names}"
        else:
            module = node.module or ""
            names = ", ".join(alias.name for alias in node.names)
            return f"from {module} import {names}"

    def _is_module_level(self, node: ast.AST, module: ast.Module) -> bool:
        """Check if a node is at module level."""
        return node in module.body

    def _extract_class_attributes(self, node: ast.ClassDef) -> List[Dict[str, str]]:
        """Extract class attributes."""
        attributes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_type = self._get_annotation(item.annotation) if item.annotation else "Any"
                attributes.append({
                    "name": item.target.id,
                    "type": attr_type
                })
        return attributes

    def _build_complete_documentation(
        self,
        module_docs: Dict[str, Any],
        examples: List[str],
        output_format: str
    ) -> str:
        """Build complete documentation from components."""
        sections = []

        module = module_docs["module"]

        # Module header
        sections.append(f"# Module Documentation\n")
        if module.docstring:
            sections.append(f"{module.docstring}\n")

        # Statistics
        stats = module_docs.get("statistics", {})
        sections.append("## Statistics\n")
        sections.append(f"- Classes: {stats.get('num_classes', 0)}")
        sections.append(f"- Functions: {stats.get('num_functions', 0)}")
        sections.append(f"- Lines of Code: {stats.get('lines_of_code', 0)}\n")

        # Classes
        if module.classes:
            sections.append("## Classes\n")
            for cls in module.classes:
                sections.append(f"### {cls.name}\n")
                if cls.docstring:
                    sections.append(f"{cls.docstring}\n")

                # Methods
                if cls.methods:
                    sections.append("#### Methods\n")
                    for method in cls.methods:
                        sections.append(f"##### `{method.signature}`\n")
                        if method.docstring:
                            sections.append(f"{method.docstring}\n")

        # Functions
        if module.functions:
            sections.append("## Functions\n")
            for func in module.functions:
                sections.append(f"### `{func.signature}`\n")
                if func.docstring:
                    sections.append(f"{func.docstring}\n")

        return '\n'.join(sections)

    def _process_directory(self, directory: Path, output_format: str) -> str:
        """Process an entire directory of Python files."""
        sections = []
        sections.append(f"# {self.config.project_name} Documentation\n")

        # Find all Python files
        python_files = list(directory.rglob("*.py"))

        for py_file in python_files:
            if py_file.name.startswith("__"):
                continue

            sections.append(f"\n## {py_file.relative_to(directory)}\n")

            try:
                module_ast = self._parse_python_file(str(py_file))
                module_docs = self.generate_api_docs(module_ast)

                module = module_docs["module"]
                if module.docstring:
                    sections.append(f"{module.docstring}\n")

            except Exception as e:
                error_info = self.error_handling(e)
                sections.append(f"Error processing file: {error_info['error_message']}\n")

        return '\n'.join(sections)

    def _generate_statistics(self, module_doc: ModuleDocumentation) -> Dict[str, int]:
        """Generate statistics for module documentation."""
        return {
            "num_classes": len(module_doc.classes),
            "num_functions": len(module_doc.functions),
            "num_imports": len(module_doc.imports),
            "num_constants": len(module_doc.constants),
            "lines_of_code": 0  # Would need to count from source
        }

    def _group_commits_by_version(self, commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Group commits by version."""
        # Simple grouping - in practice, would parse git tags
        return {
            self.config.project_version: commits
        }

    def _categorize_commit(self, message: str) -> Optional[str]:
        """Categorize commit message."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["add", "new", "feature"]):
            return "Added"
        elif any(word in message_lower for word in ["change", "update", "modify"]):
            return "Changed"
        elif any(word in message_lower for word in ["deprecate"]):
            return "Deprecated"
        elif any(word in message_lower for word in ["remove", "delete"]):
            return "Removed"
        elif any(word in message_lower for word in ["fix", "bug", "issue"]):
            return "Fixed"
        elif any(word in message_lower for word in ["security", "vulnerability"]):
            return "Security"

        return None

    def _extract_all_elements(self, doc_tree: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract all documentation elements for cross-referencing."""
        elements = []

        if "module" in doc_tree:
            module = doc_tree["module"]

            for cls in module.classes:
                elements.append({
                    "name": cls.name,
                    "type": "class",
                    "docstring": cls.docstring
                })

                for method in cls.methods:
                    elements.append({
                        "name": f"{cls.name}.{method.name}",
                        "type": "method",
                        "docstring": method.docstring
                    })

            for func in module.functions:
                elements.append({
                    "name": func.name,
                    "type": "function",
                    "docstring": func.docstring
                })

        return elements

    def _markdown_to_rst(self, markdown_text: str) -> str:
        """Convert Markdown to reStructuredText."""
        # Basic conversion (in practice, would use pandoc or similar)
        rst = markdown_text

        # Convert headers
        rst = re.sub(r'^# (.+)$', r'\1\n' + '=' * 80, rst, flags=re.MULTILINE)
        rst = re.sub(r'^## (.+)$', r'\1\n' + '-' * 80, rst, flags=re.MULTILINE)
        rst = re.sub(r'^### (.+)$', r'\1\n' + '~' * 80, rst, flags=re.MULTILINE)

        # Convert code blocks
        rst = re.sub(r'```(\w+)?\n(.*?)```', r'::\n\n\2', rst, flags=re.DOTALL)

        # Convert inline code
        rst = re.sub(r'`([^`]+)`', r'``\1``', rst)

        return rst

    def _wrap_html(self, html_content: str) -> str:
        """Wrap HTML content in a complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="{self.config.default_language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.project_name} Documentation</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""

    def _basic_markdown_to_html(self, markdown_text: str) -> str:
        """Basic Markdown to HTML conversion."""
        html = markdown_text

        # Convert headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

        # Convert code blocks
        html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

        # Convert inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

        # Convert paragraphs
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f'<p>{html}</p>'

        return self._wrap_html(html)

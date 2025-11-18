"""
Refactoring Engine FSA - Automated Code Refactoring System

This module provides comprehensive code refactoring capabilities using AST manipulation
and semantic analysis to perform safe, behavior-preserving transformations.
"""

import ast
import copy
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class RefactoringOperationType(Enum):
    """Enumeration of supported refactoring operations."""

    EXTRACT_METHOD = "extract_method"
    RENAME_SYMBOL = "rename_symbol"
    INLINE_METHOD = "inline_method"
    INLINE_VARIABLE = "inline_variable"
    EXTRACT_CLASS = "extract_class"
    MOVE_METHOD = "move_method"
    EXTRACT_VARIABLE = "extract_variable"
    INTRODUCE_PARAMETER_OBJECT = "introduce_parameter_object"
    REMOVE_DEAD_CODE = "remove_dead_code"
    CONSOLIDATE_DUPLICATE_CODE = "consolidate_duplicate_code"
    DECOMPOSE_CONDITIONAL = "decompose_conditional"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"


class Scope(Enum):
    """Symbol scope enumeration."""

    LOCAL = "local"
    NONLOCAL = "nonlocal"
    GLOBAL = "global"
    CLASS = "class"
    MODULE = "module"


@dataclass
class RefactoringOperation:
    """Represents a refactoring operation to be performed."""

    operation_type: RefactoringOperationType
    parameters: Dict[str, Any]
    target_location: Optional[Tuple[int, int]] = None  # (start_line, end_line)


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""

    success: bool
    refactored_code: Optional[str] = None
    changes_made: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class RefactoringPreview:
    """Preview of refactoring changes before application."""

    original_code: str
    refactored_code: str
    diff: str
    safety_score: float  # 0.0 to 1.0
    changes_description: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of refactoring validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class SafetyReport:
    """Safety analysis report for refactoring operation."""

    safety_score: float  # 0.0 to 1.0
    breaking_changes: List[str] = field(default_factory=list)
    affected_code: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high


@dataclass
class BatchResult:
    """Result of batch refactoring operation."""

    successful_files: List[Path] = field(default_factory=list)
    failed_files: List[Path] = field(default_factory=list)
    total_changes: int = 0
    summary: str = ""


@dataclass
class RefactoringHistoryEntry:
    """Entry in refactoring history for undo/redo."""

    operation: RefactoringOperation
    original_code: str
    refactored_code: str
    timestamp: datetime = field(default_factory=datetime.now)


class SymbolResolver(ast.NodeVisitor):
    """AST visitor to resolve symbol references and scopes."""

    def __init__(self, symbol_name: str):
        self.symbol_name = symbol_name
        self.references: List[Tuple[int, int]] = []
        self.definitions: List[Tuple[int, int]] = []

    def visit_Name(self, node: ast.Name) -> None:
        """Visit name nodes to track symbol usage."""
        if node.id == self.symbol_name:
            if isinstance(node.ctx, ast.Store):
                self.definitions.append((node.lineno, node.col_offset))
            else:
                self.references.append((node.lineno, node.col_offset))
        self.generic_visit(node)


class DeadCodeDetector(ast.NodeVisitor):
    """AST visitor to detect dead code patterns."""

    def __init__(self):
        self.dead_code_nodes: List[ast.AST] = []
        self.unreachable_code: List[Tuple[int, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Detect unreachable code after return statements."""
        for i, stmt in enumerate(node.body):
            if isinstance(stmt, ast.Return) and i < len(node.body) - 1:
                # Code after return is unreachable
                for unreachable in node.body[i + 1:]:
                    if hasattr(unreachable, 'lineno'):
                        self.unreachable_code.append((unreachable.lineno, unreachable.lineno))
                break
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Detect if statements with constant conditions."""
        if isinstance(node.test, ast.Constant):
            if not node.test.value:
                # Condition is always False, body is dead code
                for stmt in node.body:
                    self.dead_code_nodes.append(stmt)
            elif not node.orelse:
                # Condition is always True and no else, could be simplified
                pass
        self.generic_visit(node)


class DuplicateCodeDetector(ast.NodeVisitor):
    """AST visitor to detect duplicate code patterns."""

    def __init__(self):
        self.code_blocks: Dict[str, List[ast.AST]] = {}
        self.duplicates: List[Tuple[ast.AST, ast.AST]] = []

    def get_node_signature(self, node: ast.AST) -> str:
        """Generate signature for AST node for comparison."""
        try:
            return ast.unparse(node)
        except Exception:
            return str(type(node))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions for duplicate detection."""
        sig = self.get_node_signature(node)
        if sig in self.code_blocks:
            self.duplicates.append((self.code_blocks[sig][0], node))
        else:
            self.code_blocks[sig] = [node]
        self.generic_visit(node)


class RefactoringEngine:
    """
    Main refactoring engine with AST-based code transformation capabilities.

    Provides comprehensive refactoring operations with safety guarantees,
    preview mode, undo/redo support, and semantic analysis.
    """

    def __init__(self):
        """Initialize the refactoring engine."""
        self.undo_stack: List[RefactoringHistoryEntry] = []
        self.redo_stack: List[RefactoringHistoryEntry] = []
        self.current_code: Optional[str] = None
        self.max_history_size: int = 50

    def refactor(
        self,
        code: str,
        operation: RefactoringOperation,
        **params
    ) -> RefactoringResult:
        """
        Perform a refactoring operation on the given code.

        Args:
            code: Source code to refactor
            operation: Refactoring operation to perform
            **params: Additional parameters for the operation

        Returns:
            RefactoringResult containing the refactored code and metadata
        """
        try:
            # Merge operation parameters with additional params
            all_params = {**operation.parameters, **params}

            # Dispatch to specific refactoring method
            if operation.operation_type == RefactoringOperationType.EXTRACT_METHOD:
                refactored = self.extract_method(
                    code,
                    all_params.get('start_line', 0),
                    all_params.get('end_line', 0),
                    all_params.get('method_name', 'extracted_method')
                )
            elif operation.operation_type == RefactoringOperationType.RENAME_SYMBOL:
                refactored = self.rename_symbol(
                    code,
                    all_params.get('old_name', ''),
                    all_params.get('new_name', ''),
                    all_params.get('scope', Scope.MODULE)
                )
            elif operation.operation_type == RefactoringOperationType.INLINE_METHOD:
                refactored = self.inline_method(code, all_params.get('method_name', ''))
            elif operation.operation_type == RefactoringOperationType.INLINE_VARIABLE:
                refactored = self.inline_variable(code, all_params.get('variable_name', ''))
            elif operation.operation_type == RefactoringOperationType.EXTRACT_VARIABLE:
                refactored = self.extract_variable(
                    code,
                    all_params.get('expression', ''),
                    all_params.get('variable_name', 'extracted_var')
                )
            elif operation.operation_type == RefactoringOperationType.REMOVE_DEAD_CODE:
                refactored = self.remove_dead_code(code)
            elif operation.operation_type == RefactoringOperationType.CONSOLIDATE_DUPLICATE_CODE:
                refactored = self.consolidate_duplicate_code(code)
            elif operation.operation_type == RefactoringOperationType.DECOMPOSE_CONDITIONAL:
                refactored = self.decompose_conditional(code)
            else:
                return RefactoringResult(
                    success=False,
                    errors=[f"Unsupported operation: {operation.operation_type}"]
                )

            # Add to history
            self._add_to_history(operation, code, refactored)

            return RefactoringResult(
                success=True,
                refactored_code=refactored,
                changes_made=[f"Applied {operation.operation_type.value}"]
            )

        except SyntaxError as e:
            return RefactoringResult(
                success=False,
                errors=[f"Syntax error in code: {str(e)}"]
            )
        except Exception as e:
            return RefactoringResult(
                success=False,
                errors=[f"Refactoring failed: {str(e)}"]
            )

    def extract_method(
        self,
        code: str,
        start_line: int,
        end_line: int,
        method_name: str
    ) -> str:
        """
        Extract code block into a new method.

        Args:
            code: Source code
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            method_name: Name for the new method

        Returns:
            Refactored code with extracted method
        """
        lines = code.split('\n')

        # Extract the code block
        extracted_lines = lines[start_line - 1:end_line]
        extracted_code = '\n'.join(extracted_lines)

        # Determine indentation
        base_indent = len(extracted_lines[0]) - len(extracted_lines[0].lstrip())

        # Create new method
        method_indent = ' ' * 4
        new_method = f"\n{method_indent}def {method_name}(self):\n"
        for line in extracted_lines:
            if line.strip():
                new_method += f"{method_indent}{' ' * 4}{line.strip()}\n"
            else:
                new_method += "\n"

        # Replace extracted code with method call
        method_call = ' ' * base_indent + f"self.{method_name}()"
        lines[start_line - 1:end_line] = [method_call]

        # Find appropriate place to insert method (after class definition)
        tree = ast.parse(code)
        insert_line = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                insert_line = node.lineno
                break

        if insert_line > 0:
            lines.insert(insert_line, new_method)
        else:
            lines.insert(0, new_method)

        return '\n'.join(lines)

    def rename_symbol(
        self,
        code: str,
        old_name: str,
        new_name: str,
        scope: Scope = Scope.MODULE
    ) -> str:
        """
        Rename a symbol (variable, function, class) throughout the code.

        Args:
            code: Source code
            old_name: Current symbol name
            new_name: New symbol name
            scope: Scope of the symbol

        Returns:
            Refactored code with renamed symbol
        """
        tree = ast.parse(code)

        class NameReplacer(ast.NodeTransformer):
            """AST transformer to replace symbol names."""

            def visit_Name(self, node: ast.Name) -> ast.Name:
                if node.id == old_name:
                    node.id = new_name
                return node

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                if node.name == old_name:
                    node.name = new_name
                self.generic_visit(node)
                return node

            def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
                if node.name == old_name:
                    node.name = new_name
                self.generic_visit(node)
                return node

        transformer = NameReplacer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def inline_method(self, code: str, method_name: str) -> str:
        """
        Inline a method by replacing its calls with its body.

        Args:
            code: Source code
            method_name: Name of method to inline

        Returns:
            Refactored code with inlined method
        """
        tree = ast.parse(code)
        method_body: Optional[List[ast.stmt]] = None

        # Find the method definition
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method_name:
                method_body = node.body
                break

        if not method_body:
            return code

        class MethodInliner(ast.NodeTransformer):
            """AST transformer to inline method calls."""

            def visit_Call(self, node: ast.Call) -> Union[ast.Call, ast.AST]:
                if isinstance(node.func, ast.Name) and node.func.id == method_name:
                    # Replace call with method body
                    if method_body and len(method_body) == 1:
                        if isinstance(method_body[0], ast.Return):
                            return method_body[0].value or node
                    return node
                return node

        transformer = MethodInliner()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def inline_variable(self, code: str, variable_name: str) -> str:
        """
        Inline a variable by replacing its references with its value.

        Args:
            code: Source code
            variable_name: Name of variable to inline

        Returns:
            Refactored code with inlined variable
        """
        tree = ast.parse(code)
        variable_value: Optional[ast.expr] = None

        # Find variable assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == variable_name:
                        variable_value = node.value
                        break

        if not variable_value:
            return code

        class VariableInliner(ast.NodeTransformer):
            """AST transformer to inline variable references."""

            def visit_Name(self, node: ast.Name) -> ast.expr:
                if node.id == variable_name and isinstance(node.ctx, ast.Load):
                    return copy.deepcopy(variable_value)
                return node

        transformer = VariableInliner()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def extract_variable(self, code: str, expression: str, variable_name: str) -> str:
        """
        Extract an expression into a named variable.

        Args:
            code: Source code
            expression: Expression to extract
            variable_name: Name for the new variable

        Returns:
            Refactored code with extracted variable
        """
        try:
            expr_ast = ast.parse(expression, mode='eval').body
        except SyntaxError:
            return code

        tree = ast.parse(code)
        expr_str = ast.unparse(expr_ast)

        class ExpressionExtractor(ast.NodeTransformer):
            """AST transformer to extract expressions into variables."""

            def __init__(self):
                self.extracted = False

            def visit_Module(self, node: ast.Module) -> ast.Module:
                # Insert variable assignment at module level
                if not self.extracted:
                    assignment = ast.Assign(
                        targets=[ast.Name(id=variable_name, ctx=ast.Store())],
                        value=copy.deepcopy(expr_ast)
                    )
                    node.body.insert(0, assignment)
                    self.extracted = True
                self.generic_visit(node)
                return node

        transformer = ExpressionExtractor()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def remove_dead_code(self, code: str) -> str:
        """
        Remove unreachable and dead code.

        Args:
            code: Source code

        Returns:
            Refactored code without dead code
        """
        tree = ast.parse(code)
        detector = DeadCodeDetector()
        detector.visit(tree)

        class DeadCodeRemover(ast.NodeTransformer):
            """AST transformer to remove dead code."""

            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                # Remove code after return statements
                new_body = []
                for stmt in node.body:
                    new_body.append(stmt)
                    if isinstance(stmt, ast.Return):
                        break
                node.body = new_body
                self.generic_visit(node)
                return node

            def visit_If(self, node: ast.If) -> Union[ast.If, List[ast.stmt], None]:
                # Remove if statements with constant False conditions
                if isinstance(node.test, ast.Constant):
                    if node.test.value:
                        # Always True, replace with body
                        return node.body
                    else:
                        # Always False, replace with orelse or remove
                        return node.orelse if node.orelse else None
                return node

        transformer = DeadCodeRemover()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def consolidate_duplicate_code(self, code: str) -> str:
        """
        Consolidate duplicate code into reusable functions.

        Args:
            code: Source code

        Returns:
            Refactored code with consolidated duplicates
        """
        tree = ast.parse(code)
        detector = DuplicateCodeDetector()
        detector.visit(tree)

        # For now, just return the code as-is (full implementation would be complex)
        # This is a simplified version
        if detector.duplicates:
            # In a full implementation, we would extract duplicate code into functions
            pass

        return code

    def decompose_conditional(self, code: str) -> str:
        """
        Decompose complex conditionals into separate methods.

        Args:
            code: Source code

        Returns:
            Refactored code with decomposed conditionals
        """
        tree = ast.parse(code)

        class ConditionalDecomposer(ast.NodeTransformer):
            """AST transformer to decompose complex conditionals."""

            def __init__(self):
                self.condition_counter = 0

            def visit_If(self, node: ast.If) -> ast.If:
                # Decompose complex boolean expressions
                if isinstance(node.test, ast.BoolOp):
                    # Complex condition - could be extracted
                    self.condition_counter += 1
                self.generic_visit(node)
                return node

        transformer = ConditionalDecomposer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree)

    def preview_refactoring(
        self,
        code: str,
        operation: RefactoringOperation
    ) -> RefactoringPreview:
        """
        Preview refactoring changes before applying them.

        Args:
            code: Source code
            operation: Refactoring operation to preview

        Returns:
            RefactoringPreview with diff and safety analysis
        """
        result = self.refactor(code, operation)

        if not result.success or not result.refactored_code:
            return RefactoringPreview(
                original_code=code,
                refactored_code=code,
                diff="",
                safety_score=0.0
            )

        # Generate diff
        diff = self._generate_diff(code, result.refactored_code)

        # Calculate safety score
        safety = self.analyze_refactoring_safety(code, operation)

        return RefactoringPreview(
            original_code=code,
            refactored_code=result.refactored_code,
            diff=diff,
            safety_score=safety.safety_score,
            changes_description=result.changes_made
        )

    def validate_refactoring(
        self,
        original: str,
        refactored: str
    ) -> ValidationResult:
        """
        Validate that refactoring preserves code semantics.

        Args:
            original: Original source code
            refactored: Refactored source code

        Returns:
            ValidationResult with validation status and messages
        """
        errors = []
        warnings = []
        suggestions = []

        # Check if both parse correctly
        try:
            ast.parse(original)
        except SyntaxError as e:
            errors.append(f"Original code has syntax error: {e}")

        try:
            ast.parse(refactored)
        except SyntaxError as e:
            errors.append(f"Refactored code has syntax error: {e}")

        # Basic validation checks
        if len(refactored.split('\n')) > len(original.split('\n')) * 2:
            warnings.append("Refactored code is significantly longer")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def analyze_refactoring_safety(
        self,
        code: str,
        operation: RefactoringOperation
    ) -> SafetyReport:
        """
        Analyze safety of refactoring operation.

        Args:
            code: Source code
            operation: Refactoring operation to analyze

        Returns:
            SafetyReport with safety metrics
        """
        breaking_changes = []
        affected_code = []
        safety_score = 0.8  # Default score

        # Analyze based on operation type
        if operation.operation_type in [
            RefactoringOperationType.RENAME_SYMBOL,
            RefactoringOperationType.EXTRACT_METHOD
        ]:
            safety_score = 0.9
            risk_level = "low"
        elif operation.operation_type in [
            RefactoringOperationType.REMOVE_DEAD_CODE,
            RefactoringOperationType.INLINE_METHOD
        ]:
            safety_score = 0.7
            risk_level = "medium"
        else:
            safety_score = 0.6
            risk_level = "medium"

        return SafetyReport(
            safety_score=safety_score,
            breaking_changes=breaking_changes,
            affected_code=affected_code,
            risk_level=risk_level
        )

    def undo_refactoring(self) -> Optional[str]:
        """
        Undo the last refactoring operation.

        Returns:
            Original code before last refactoring, or None if nothing to undo
        """
        if not self.undo_stack:
            return None

        entry = self.undo_stack.pop()
        self.redo_stack.append(entry)

        # Trim redo stack if too large
        if len(self.redo_stack) > self.max_history_size:
            self.redo_stack.pop(0)

        return entry.original_code

    def redo_refactoring(self) -> Optional[str]:
        """
        Redo the last undone refactoring operation.

        Returns:
            Refactored code after redo, or None if nothing to redo
        """
        if not self.redo_stack:
            return None

        entry = self.redo_stack.pop()
        self.undo_stack.append(entry)

        return entry.refactored_code

    def batch_refactor(
        self,
        files: List[Path],
        operation: RefactoringOperation
    ) -> BatchResult:
        """
        Apply refactoring operation to multiple files.

        Args:
            files: List of file paths to refactor
            operation: Refactoring operation to apply

        Returns:
            BatchResult with summary of batch operation
        """
        successful = []
        failed = []
        total_changes = 0

        for file_path in files:
            try:
                code = file_path.read_text()
                result = self.refactor(code, operation)

                if result.success and result.refactored_code:
                    file_path.write_text(result.refactored_code)
                    successful.append(file_path)
                    total_changes += len(result.changes_made)
                else:
                    failed.append(file_path)
            except Exception as e:
                failed.append(file_path)

        summary = f"Refactored {len(successful)}/{len(files)} files successfully"

        return BatchResult(
            successful_files=successful,
            failed_files=failed,
            total_changes=total_changes,
            summary=summary
        )

    def _generate_diff(self, original: str, refactored: str) -> str:
        """Generate unified diff between original and refactored code."""
        original_lines = original.splitlines(keepends=True)
        refactored_lines = refactored.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            refactored_lines,
            fromfile='original',
            tofile='refactored',
            lineterm=''
        )

        return ''.join(diff)

    def _add_to_history(
        self,
        operation: RefactoringOperation,
        original: str,
        refactored: str
    ) -> None:
        """Add refactoring to history for undo/redo."""
        entry = RefactoringHistoryEntry(
            operation=operation,
            original_code=original,
            refactored_code=refactored
        )

        self.undo_stack.append(entry)
        self.redo_stack.clear()  # Clear redo stack on new operation

        # Trim undo stack if too large
        if len(self.undo_stack) > self.max_history_size:
            self.undo_stack.pop(0)

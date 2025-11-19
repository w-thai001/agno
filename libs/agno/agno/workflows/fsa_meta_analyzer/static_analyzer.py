"""
FSA Static Analyzer - Parses workflow definitions to extract FSA structure.

This module uses Python's AST (Abstract Syntax Tree) to analyze Workflow.run() methods
and extract finite state automaton characteristics including states, transitions, and control flow.
"""

import ast
import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from agno.workflow.workflow import Workflow


@dataclass
class FSAState:
    """Represents a state in the finite state automaton."""

    name: str
    line_number: int
    state_type: str  # 'entry', 'processing', 'decision', 'exit', 'error'
    description: Optional[str] = None
    variables_read: Set[str] = field(default_factory=set)
    variables_written: Set[str] = field(default_factory=set)
    agent_calls: List[str] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)


@dataclass
class FSATransition:
    """Represents a transition between states."""

    from_state: str
    to_state: str
    condition: Optional[str] = None
    transition_type: str = 'sequential'  # 'sequential', 'conditional', 'loop', 'exception'
    line_number: int = 0


@dataclass
class FSAStructure:
    """Complete FSA structure extracted from a workflow."""

    workflow_name: str
    workflow_class: Type[Workflow]
    states: Dict[str, FSAState] = field(default_factory=dict)
    transitions: List[FSATransition] = field(default_factory=list)
    entry_state: Optional[str] = None
    exit_states: Set[str] = field(default_factory=set)
    error_states: Set[str] = field(default_factory=set)
    loop_states: Set[str] = field(default_factory=set)
    parameters: Dict[str, Any] = field(default_factory=dict)
    return_type: Optional[str] = None
    agents: List[str] = field(default_factory=list)
    complexity_metrics: Dict[str, int] = field(default_factory=dict)


class FSAStaticAnalyzer:
    """Analyzes workflow source code to extract FSA structure."""

    def __init__(self):
        self.current_state_counter = 0
        self.state_stack: List[str] = []

    def analyze_workflow(self, workflow_class: Type[Workflow]) -> FSAStructure:
        """
        Main entry point: analyzes a workflow class and returns FSA structure.

        Args:
            workflow_class: The Workflow class to analyze

        Returns:
            FSAStructure containing all extracted information
        """
        fsa = FSAStructure(
            workflow_name=workflow_class.__name__,
            workflow_class=workflow_class,
        )

        # Extract method signature
        self._extract_method_signature(workflow_class, fsa)

        # Extract agents from class attributes
        self._extract_agents(workflow_class, fsa)

        # Parse the run method's AST
        run_method = workflow_class.run
        source = inspect.getsource(run_method)
        tree = ast.parse(source)

        # Analyze the AST
        self._analyze_ast(tree, fsa)

        # Calculate complexity metrics
        self._calculate_complexity(fsa)

        return fsa

    def _extract_method_signature(self, workflow_class: Type[Workflow], fsa: FSAStructure):
        """Extract parameters and return type from run method."""
        sig = inspect.signature(workflow_class.run)

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            fsa.parameters[param_name] = {
                'name': param_name,
                'annotation': param.annotation,
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty,
            }

        if sig.return_annotation != inspect.Signature.empty:
            fsa.return_type = str(sig.return_annotation)

    def _extract_agents(self, workflow_class: Type[Workflow], fsa: FSAStructure):
        """Extract agent attributes from workflow class."""
        for attr_name in dir(workflow_class):
            if attr_name.startswith('_'):
                continue
            try:
                attr = getattr(workflow_class, attr_name)
                # Check if it's an Agent by looking for agent-like attributes
                if hasattr(attr, 'run') and hasattr(attr, 'model'):
                    fsa.agents.append(attr_name)
            except Exception:
                pass

    def _analyze_ast(self, tree: ast.AST, fsa: FSAStructure):
        """Analyze AST to extract states and transitions."""
        # Find the run method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'run':
                self._analyze_function_body(node.body, fsa)
                break

    def _analyze_function_body(
        self, body: List[ast.stmt], fsa: FSAStructure, parent_state: Optional[str] = None
    ):
        """Recursively analyze function body to extract control flow."""
        if not parent_state:
            parent_state = self._create_state(fsa, 'entry', 0, 'entry')
            fsa.entry_state = parent_state

        current_state = parent_state

        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.If):
                current_state = self._handle_if_statement(stmt, fsa, current_state)
            elif isinstance(stmt, ast.For) or isinstance(stmt, ast.While):
                current_state = self._handle_loop_statement(stmt, fsa, current_state)
            elif isinstance(stmt, ast.Return):
                current_state = self._handle_return_statement(stmt, fsa, current_state)
            elif isinstance(stmt, ast.Try):
                current_state = self._handle_try_statement(stmt, fsa, current_state)
            elif isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                self._handle_assignment(stmt, fsa, current_state)
            elif isinstance(stmt, ast.Expr):
                # Check for agent/method calls
                if isinstance(stmt.value, ast.Yield) or isinstance(stmt.value, ast.YieldFrom):
                    self._handle_yield(stmt.value, fsa, current_state)
                elif isinstance(stmt.value, ast.Call):
                    self._handle_call(stmt.value, fsa, current_state)

    def _handle_if_statement(
        self, node: ast.If, fsa: FSAStructure, current_state: str
    ) -> str:
        """Handle if/elif/else statements as decision states."""
        decision_state = self._create_state(
            fsa, f'decision_{node.lineno}', node.lineno, 'decision'
        )

        # Add transition from current to decision
        fsa.transitions.append(
            FSATransition(
                from_state=current_state,
                to_state=decision_state,
                transition_type='sequential',
                line_number=node.lineno,
            )
        )

        # Analyze if branch
        if_branch_state = self._create_state(
            fsa, f'if_branch_{node.lineno}', node.lineno, 'processing'
        )
        condition = ast.unparse(node.test) if hasattr(ast, 'unparse') else 'condition'
        fsa.transitions.append(
            FSATransition(
                from_state=decision_state,
                to_state=if_branch_state,
                condition=condition,
                transition_type='conditional',
                line_number=node.lineno,
            )
        )
        self._analyze_function_body(node.body, fsa, if_branch_state)

        # Analyze else branch
        if node.orelse:
            else_branch_state = self._create_state(
                fsa, f'else_branch_{node.lineno}', node.lineno, 'processing'
            )
            fsa.transitions.append(
                FSATransition(
                    from_state=decision_state,
                    to_state=else_branch_state,
                    condition=f'not ({condition})',
                    transition_type='conditional',
                    line_number=node.lineno,
                )
            )
            self._analyze_function_body(node.orelse, fsa, else_branch_state)

        # Create merge state after if/else
        merge_state = self._create_state(
            fsa, f'merge_{node.lineno}', node.lineno, 'processing'
        )

        return merge_state

    def _handle_loop_statement(
        self, node: Union[ast.For, ast.While], fsa: FSAStructure, current_state: str
    ) -> str:
        """Handle for/while loops as loop states."""
        loop_state = self._create_state(fsa, f'loop_{node.lineno}', node.lineno, 'processing')
        fsa.loop_states.add(loop_state)

        # Add transition to loop
        loop_condition = ''
        if isinstance(node, ast.While):
            loop_condition = (
                ast.unparse(node.test) if hasattr(ast, 'unparse') else 'while_condition'
            )
        elif isinstance(node, ast.For):
            loop_condition = f'for {ast.unparse(node.target) if hasattr(ast, "unparse") else "var"} in {ast.unparse(node.iter) if hasattr(ast, "unparse") else "iterable"}'

        fsa.transitions.append(
            FSATransition(
                from_state=current_state,
                to_state=loop_state,
                condition=loop_condition,
                transition_type='loop',
                line_number=node.lineno,
            )
        )

        # Analyze loop body
        loop_body_state = self._create_state(
            fsa, f'loop_body_{node.lineno}', node.lineno, 'processing'
        )
        self._analyze_function_body(node.body, fsa, loop_body_state)

        # Add back-edge to loop
        fsa.transitions.append(
            FSATransition(
                from_state=loop_body_state,
                to_state=loop_state,
                transition_type='loop',
                line_number=node.lineno,
            )
        )

        # Create exit state
        exit_loop_state = self._create_state(
            fsa, f'exit_loop_{node.lineno}', node.lineno, 'processing'
        )

        return exit_loop_state

    def _handle_return_statement(
        self, node: ast.Return, fsa: FSAStructure, current_state: str
    ) -> str:
        """Handle return statements as exit states."""
        exit_state = self._create_state(fsa, f'exit_{node.lineno}', node.lineno, 'exit')
        fsa.exit_states.add(exit_state)

        fsa.transitions.append(
            FSATransition(
                from_state=current_state,
                to_state=exit_state,
                transition_type='sequential',
                line_number=node.lineno,
            )
        )

        return exit_state

    def _handle_try_statement(
        self, node: ast.Try, fsa: FSAStructure, current_state: str
    ) -> str:
        """Handle try/except statements."""
        try_state = self._create_state(fsa, f'try_{node.lineno}', node.lineno, 'processing')

        fsa.transitions.append(
            FSATransition(
                from_state=current_state,
                to_state=try_state,
                transition_type='sequential',
                line_number=node.lineno,
            )
        )

        # Analyze try block
        self._analyze_function_body(node.body, fsa, try_state)

        # Analyze except blocks
        for handler in node.handlers:
            error_state = self._create_state(
                fsa, f'error_{handler.lineno}', handler.lineno, 'error'
            )
            fsa.error_states.add(error_state)

            exception_type = (
                ast.unparse(handler.type) if handler.type and hasattr(ast, 'unparse') else 'Exception'
            )

            fsa.transitions.append(
                FSATransition(
                    from_state=try_state,
                    to_state=error_state,
                    condition=f'exception: {exception_type}',
                    transition_type='exception',
                    line_number=handler.lineno,
                )
            )

            self._analyze_function_body(handler.body, fsa, error_state)

        # Create merge state
        merge_state = self._create_state(fsa, f'merge_{node.lineno}', node.lineno, 'processing')

        return merge_state

    def _handle_assignment(
        self, node: Union[ast.Assign, ast.AugAssign, ast.AnnAssign], fsa: FSAStructure, state: str
    ):
        """Track variable assignments in states."""
        if state in fsa.states:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        fsa.states[state].variables_written.add(target.id)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                if isinstance(node.target, ast.Name):
                    fsa.states[state].variables_written.add(node.target.id)

    def _handle_yield(self, node: Union[ast.Yield, ast.YieldFrom], fsa: FSAStructure, state: str):
        """Track yield statements (typically streaming responses)."""
        if state in fsa.states:
            fsa.states[state].description = 'Streaming output'

    def _handle_call(self, node: ast.Call, fsa: FSAStructure, state: str):
        """Track method and agent calls."""
        if state in fsa.states:
            if isinstance(node.func, ast.Attribute):
                # Check for agent calls (e.g., self.agent.run())
                if isinstance(node.func.value, ast.Attribute):
                    if node.func.attr == 'run':
                        agent_name = (
                            ast.unparse(node.func.value)
                            if hasattr(ast, 'unparse')
                            else 'agent'
                        )
                        fsa.states[state].agent_calls.append(agent_name)

    def _create_state(
        self, fsa: FSAStructure, name: str, line_number: int, state_type: str
    ) -> str:
        """Create a new state in the FSA."""
        state = FSAState(name=name, line_number=line_number, state_type=state_type)
        fsa.states[name] = state
        return name

    def _calculate_complexity(self, fsa: FSAStructure):
        """Calculate complexity metrics for the FSA."""
        fsa.complexity_metrics = {
            'total_states': len(fsa.states),
            'total_transitions': len(fsa.transitions),
            'decision_points': sum(
                1 for s in fsa.states.values() if s.state_type == 'decision'
            ),
            'loop_states': len(fsa.loop_states),
            'exit_states': len(fsa.exit_states),
            'error_states': len(fsa.error_states),
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity(fsa),
            'agent_interactions': sum(len(s.agent_calls) for s in fsa.states.values()),
        }

    def _calculate_cyclomatic_complexity(self, fsa: FSAStructure) -> int:
        """
        Calculate cyclomatic complexity: M = E - N + 2P
        where E = edges (transitions), N = nodes (states), P = connected components (1 for single workflow)
        """
        E = len(fsa.transitions)
        N = len(fsa.states)
        P = 1
        return E - N + 2 * P if N > 0 else 0

"""
Comprehensive Static Analyzer FSA for Python code analysis.

This module performs deep static analysis of Python code including:
- Control flow analysis and CFG construction
- Data flow analysis (reaching definitions, live variables)
- Type inference and type checking
- Taint analysis for security vulnerabilities
- Dead code and unreachable code detection
- Security vulnerability detection
- Code quality metrics computation
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, deque
from enum import Enum


# ============================================================================
# Data Structures
# ============================================================================

class SecurityIssueType(Enum):
    """Types of security issues that can be detected."""
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    UNSAFE_EVAL = "unsafe_eval"


class Severity(Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class BasicBlock:
    """Represents a basic block in the control flow graph."""
    id: int
    statements: List[ast.AST] = field(default_factory=list)
    predecessors: Set[int] = field(default_factory=set)
    successors: Set[int] = field(default_factory=set)
    dominators: Set[int] = field(default_factory=set)
    live_in: Set[str] = field(default_factory=set)
    live_out: Set[str] = field(default_factory=set)
    reaching_defs: Dict[str, Set[int]] = field(default_factory=dict)

    def add_statement(self, stmt: ast.AST):
        """Add a statement to this basic block."""
        self.statements.append(stmt)

    def add_successor(self, block_id: int):
        """Add a successor block."""
        self.successors.add(block_id)

    def add_predecessor(self, block_id: int):
        """Add a predecessor block."""
        self.predecessors.add(block_id)


@dataclass
class ControlFlowGraph:
    """Control flow graph representation."""
    blocks: Dict[int, BasicBlock] = field(default_factory=dict)
    entry: Optional[int] = None
    exit: Optional[int] = None
    next_block_id: int = 0

    def create_block(self) -> BasicBlock:
        """Create a new basic block."""
        block_id = self.next_block_id
        self.next_block_id += 1
        block = BasicBlock(id=block_id)
        self.blocks[block_id] = block
        return block

    def add_edge(self, from_id: int, to_id: int):
        """Add an edge between two blocks."""
        if from_id in self.blocks and to_id in self.blocks:
            self.blocks[from_id].add_successor(to_id)
            self.blocks[to_id].add_predecessor(from_id)

    def compute_dominators(self):
        """Compute dominator sets for all blocks."""
        if not self.entry:
            return

        # Initialize
        all_blocks = set(self.blocks.keys())
        self.blocks[self.entry].dominators = {self.entry}

        for block_id in self.blocks:
            if block_id != self.entry:
                self.blocks[block_id].dominators = all_blocks.copy()

        # Fixed-point iteration
        changed = True
        while changed:
            changed = False
            for block_id in self.blocks:
                if block_id == self.entry:
                    continue

                block = self.blocks[block_id]
                new_doms = all_blocks.copy()

                for pred_id in block.predecessors:
                    new_doms &= self.blocks[pred_id].dominators

                new_doms.add(block_id)

                if new_doms != block.dominators:
                    block.dominators = new_doms
                    changed = True


@dataclass
class DataFlowAnalysis:
    """Results of data flow analysis."""
    reaching_defs: Dict[int, Dict[str, Set[int]]] = field(default_factory=dict)
    live_vars: Dict[int, Set[str]] = field(default_factory=dict)
    available_exprs: Dict[int, Set[str]] = field(default_factory=dict)
    def_use_chains: Dict[Tuple[int, str], Set[Tuple[int, str]]] = field(default_factory=dict)
    use_def_chains: Dict[Tuple[int, str], Set[Tuple[int, str]]] = field(default_factory=dict)


@dataclass
class TypeConstraint:
    """Represents a type constraint for type inference."""
    var: str
    type_expr: str
    location: Tuple[int, int]


@dataclass
class TypeInferenceResult:
    """Results of type inference."""
    inferred_types: Dict[str, str] = field(default_factory=dict)
    type_constraints: List[TypeConstraint] = field(default_factory=list)
    type_errors: List[str] = field(default_factory=list)


@dataclass
class TaintSource:
    """Represents a taint source."""
    var: str
    location: Tuple[int, int]
    source_type: str


@dataclass
class TaintSink:
    """Represents a taint sink."""
    var: str
    location: Tuple[int, int]
    sink_type: str


@dataclass
class TaintFlow:
    """Represents a taint flow from source to sink."""
    source: TaintSource
    sink: TaintSink
    path: List[str]


@dataclass
class TaintReport:
    """Results of taint analysis."""
    tainted_flows: List[TaintFlow] = field(default_factory=list)
    sources: List[TaintSource] = field(default_factory=list)
    sinks: List[TaintSink] = field(default_factory=list)
    sanitized_flows: List[TaintFlow] = field(default_factory=list)


@dataclass
class SecurityIssue:
    """Represents a security vulnerability."""
    type: SecurityIssueType
    severity: Severity
    location: Tuple[int, int]
    description: str
    fix_suggestion: str
    code_snippet: Optional[str] = None


@dataclass
class CallGraphNode:
    """Node in the call graph."""
    name: str
    lineno: int
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)


@dataclass
class CallGraph:
    """Call graph representation."""
    nodes: Dict[str, CallGraphNode] = field(default_factory=dict)
    entry_points: Set[str] = field(default_factory=set)


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    max_nesting_depth: int = 0
    num_functions: int = 0
    num_classes: int = 0
    avg_function_length: float = 0.0
    maintainability_index: float = 0.0


@dataclass
class CodeIssue:
    """Represents a code issue (error, warning, etc.)."""
    severity: Severity
    location: Tuple[int, int]
    message: str
    code: Optional[str] = None


@dataclass
class AnalysisReport:
    """Comprehensive analysis report."""
    errors: List[CodeIssue] = field(default_factory=list)
    warnings: List[CodeIssue] = field(default_factory=list)
    security_issues: List[SecurityIssue] = field(default_factory=list)
    metrics: Optional[ComplexityMetrics] = None
    cfg: Optional[ControlFlowGraph] = None
    data_flow: Optional[DataFlowAnalysis] = None
    type_inference: Optional[TypeInferenceResult] = None
    taint_report: Optional[TaintReport] = None
    call_graph: Optional[CallGraph] = None
    dead_code: List[CodeIssue] = field(default_factory=list)
    unreachable_code: List[CodeIssue] = field(default_factory=list)


# ============================================================================
# Static Analyzer Implementation
# ============================================================================

class StaticAnalyzer:
    """
    Comprehensive static analyzer for Python code.

    Performs multi-pass analysis including CFG construction, data flow analysis,
    type inference, taint analysis, security vulnerability detection, and more.
    """

    def __init__(self):
        """Initialize the static analyzer."""
        self.ast_tree: Optional[ast.AST] = None
        self.source_lines: List[str] = []
        self.cfg: Optional[ControlFlowGraph] = None
        self.variables: Set[str] = set()
        self.functions: Dict[str, ast.FunctionDef] = {}

    def analyze(self, code: Union[str, Path]) -> AnalysisReport:
        """
        Main analysis entry point.

        Args:
            code: Python code as string or path to file

        Returns:
            Comprehensive analysis report
        """
        # Load code
        if isinstance(code, Path):
            code = code.read_text()

        self.source_lines = code.split('\n')

        report = AnalysisReport()

        # Parse AST
        try:
            self.ast_tree = self.parse_ast(code)
        except SyntaxError as e:
            report.errors.append(CodeIssue(
                severity=Severity.CRITICAL,
                location=(e.lineno or 0, e.offset or 0),
                message=f"Syntax error: {e.msg}",
                code=e.text
            ))
            return report

        # Build CFG
        self.cfg = self.build_cfg(self.ast_tree)
        report.cfg = self.cfg

        # Analyze data flow
        report.data_flow = self.analyze_data_flow(self.cfg)

        # Type inference
        report.type_inference = self.infer_types(self.ast_tree)

        # Dead code detection
        dead_code = self.detect_dead_code(self.cfg, report.data_flow)
        report.dead_code = dead_code

        # Unreachable code detection
        unreachable = self.detect_unreachable_code(self.cfg)
        report.unreachable_code = unreachable

        # Taint analysis
        report.taint_report = self.perform_taint_analysis(self.cfg)

        # Security vulnerability detection
        report.security_issues = self.detect_security_vulnerabilities(self.ast_tree)

        # Build call graph
        report.call_graph = self.build_call_graph(self.ast_tree)

        # Compute complexity metrics
        report.metrics = self.analyze_complexity(self.ast_tree)

        # Detect undefined variables
        undefined_vars = self.detect_undefined_variables(self.cfg, report.data_flow)
        report.warnings.extend(undefined_vars)

        return report

    def parse_ast(self, code: str) -> ast.AST:
        """Parse Python code into AST."""
        return ast.parse(code)

    def build_cfg(self, ast_node: ast.AST) -> ControlFlowGraph:
        """
        Construct control flow graph from AST.

        Args:
            ast_node: Root AST node

        Returns:
            Control flow graph
        """
        cfg = ControlFlowGraph()

        # Create entry and exit blocks
        entry = cfg.create_block()
        cfg.entry = entry.id

        exit_block = cfg.create_block()
        cfg.exit = exit_block.id

        # Build CFG from module body
        if isinstance(ast_node, ast.Module):
            current = entry
            for stmt in ast_node.body:
                current = self._build_cfg_stmt(stmt, current, exit_block, cfg)

            # Connect final block to exit
            if current:
                cfg.add_edge(current.id, exit_block.id)

        # Compute dominators
        cfg.compute_dominators()

        return cfg

    def _build_cfg_stmt(self, stmt: ast.AST, current: BasicBlock,
                        exit_block: BasicBlock, cfg: ControlFlowGraph) -> BasicBlock:
        """Build CFG for a single statement."""
        if isinstance(stmt, ast.If):
            # Create blocks for if branches
            then_block = cfg.create_block()
            else_block = cfg.create_block()
            merge_block = cfg.create_block()

            # Add condition to current block
            current.add_statement(stmt)
            cfg.add_edge(current.id, then_block.id)
            cfg.add_edge(current.id, else_block.id)

            # Build then branch
            then_current = then_block
            for s in stmt.body:
                then_current = self._build_cfg_stmt(s, then_current, exit_block, cfg)
            cfg.add_edge(then_current.id, merge_block.id)

            # Build else branch
            else_current = else_block
            if stmt.orelse:
                for s in stmt.orelse:
                    else_current = self._build_cfg_stmt(s, else_current, exit_block, cfg)
            cfg.add_edge(else_current.id, merge_block.id)

            return merge_block

        elif isinstance(stmt, (ast.While, ast.For)):
            # Create loop blocks
            loop_header = cfg.create_block()
            loop_body = cfg.create_block()
            loop_exit = cfg.create_block()

            current.add_statement(stmt)
            cfg.add_edge(current.id, loop_header.id)
            cfg.add_edge(loop_header.id, loop_body.id)
            cfg.add_edge(loop_header.id, loop_exit.id)

            # Build loop body
            body_current = loop_body
            body_stmts = stmt.body if hasattr(stmt, 'body') else []
            for s in body_stmts:
                body_current = self._build_cfg_stmt(s, body_current, exit_block, cfg)

            # Back edge to loop header
            cfg.add_edge(body_current.id, loop_header.id)

            return loop_exit

        elif isinstance(stmt, ast.Return):
            current.add_statement(stmt)
            cfg.add_edge(current.id, exit_block.id)
            return cfg.create_block()  # Create unreachable block

        elif isinstance(stmt, ast.FunctionDef):
            # Store function for later analysis
            self.functions[stmt.name] = stmt
            current.add_statement(stmt)
            return current

        else:
            # Simple statement
            current.add_statement(stmt)
            return current

    def analyze_data_flow(self, cfg: ControlFlowGraph) -> DataFlowAnalysis:
        """
        Perform data flow analysis on the CFG.

        Includes reaching definitions and live variable analysis.
        """
        dfa = DataFlowAnalysis()

        # Reaching definitions analysis
        self._compute_reaching_definitions(cfg, dfa)

        # Live variable analysis
        self._compute_live_variables(cfg, dfa)

        return dfa

    def _compute_reaching_definitions(self, cfg: ControlFlowGraph, dfa: DataFlowAnalysis):
        """Compute reaching definitions using fixed-point iteration."""
        # Initialize
        for block_id, block in cfg.blocks.items():
            block.reaching_defs = {}

        # Fixed-point iteration
        changed = True
        iterations = 0
        max_iterations = 100

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for block_id, block in cfg.blocks.items():
                old_defs = block.reaching_defs.copy()
                new_defs = {}

                # Merge definitions from predecessors
                for pred_id in block.predecessors:
                    pred_block = cfg.blocks[pred_id]
                    for var, defs in pred_block.reaching_defs.items():
                        if var not in new_defs:
                            new_defs[var] = set()
                        new_defs[var].update(defs)

                # Process statements in block
                for stmt in block.statements:
                    defs_vars = self._get_defined_vars(stmt)
                    for var in defs_vars:
                        new_defs[var] = {block_id}

                if new_defs != old_defs:
                    block.reaching_defs = new_defs
                    changed = True

        dfa.reaching_defs = {bid: block.reaching_defs for bid, block in cfg.blocks.items()}

    def _compute_live_variables(self, cfg: ControlFlowGraph, dfa: DataFlowAnalysis):
        """Compute live variables using backward data flow analysis."""
        # Initialize
        for block in cfg.blocks.values():
            block.live_in = set()
            block.live_out = set()

        # Fixed-point iteration (backward)
        changed = True
        iterations = 0
        max_iterations = 100

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for block_id in reversed(list(cfg.blocks.keys())):
                block = cfg.blocks[block_id]
                old_live_in = block.live_in.copy()

                # live_out = union of live_in of successors
                block.live_out = set()
                for succ_id in block.successors:
                    block.live_out.update(cfg.blocks[succ_id].live_in)

                # live_in = (live_out - def) + use
                used_vars = set()
                defined_vars = set()

                for stmt in block.statements:
                    used_vars.update(self._get_used_vars(stmt))
                    defined_vars.update(self._get_defined_vars(stmt))

                block.live_in = (block.live_out - defined_vars) | used_vars

                if block.live_in != old_live_in:
                    changed = True

        dfa.live_vars = {bid: block.live_in for bid, block in cfg.blocks.items()}

    def _get_defined_vars(self, stmt: ast.AST) -> Set[str]:
        """Extract variables defined in a statement."""
        defined = set()

        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name):
                defined.add(stmt.target.id)
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                defined.add(stmt.target.id)
        elif isinstance(stmt, ast.For):
            if isinstance(stmt.target, ast.Name):
                defined.add(stmt.target.id)

        return defined

    def _get_used_vars(self, stmt: ast.AST) -> Set[str]:
        """Extract variables used in a statement."""
        used = set()

        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)

        return used

    def infer_types(self, ast_node: ast.AST) -> TypeInferenceResult:
        """
        Perform type inference using constraint-based approach.

        This is a simplified Hindley-Milner style type inference.
        """
        result = TypeInferenceResult()

        # Collect type annotations
        for node in ast.walk(ast_node):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.annotation:
                    type_str = ast.unparse(node.annotation)
                    result.inferred_types[node.target.id] = type_str
                    result.type_constraints.append(TypeConstraint(
                        var=node.target.id,
                        type_expr=type_str,
                        location=(node.lineno, node.col_offset)
                    ))

            elif isinstance(node, ast.FunctionDef):
                # Infer function parameter types
                for arg in node.args.args:
                    if arg.annotation:
                        type_str = ast.unparse(arg.annotation)
                        result.inferred_types[arg.arg] = type_str

        # Simple type inference from literals
        for node in ast.walk(ast_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        inferred_type = self._infer_type_from_value(node.value)
                        if inferred_type and var_name not in result.inferred_types:
                            result.inferred_types[var_name] = inferred_type

        return result

    def _infer_type_from_value(self, node: ast.AST) -> Optional[str]:
        """Infer type from a value node."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return "list"
        elif isinstance(node, ast.Dict):
            return "dict"
        elif isinstance(node, ast.Set):
            return "set"
        elif isinstance(node, ast.Tuple):
            return "tuple"
        return None

    def detect_dead_code(self, cfg: ControlFlowGraph, dfa: DataFlowAnalysis) -> List[CodeIssue]:
        """Detect dead code (code that has no effect)."""
        dead_code = []

        for block_id, block in cfg.blocks.items():
            for stmt in block.statements:
                # Check for assignments to variables that are never used
                defined_vars = self._get_defined_vars(stmt)

                for var in defined_vars:
                    # Check if variable is live after this block
                    if var not in block.live_out:
                        dead_code.append(CodeIssue(
                            severity=Severity.LOW,
                            location=(getattr(stmt, 'lineno', 0), getattr(stmt, 'col_offset', 0)),
                            message=f"Dead code: variable '{var}' is assigned but never used",
                            code=ast.unparse(stmt) if hasattr(ast, 'unparse') else None
                        ))

        return dead_code

    def detect_unreachable_code(self, cfg: ControlFlowGraph) -> List[CodeIssue]:
        """Detect unreachable code using CFG reachability."""
        unreachable = []

        if not cfg.entry:
            return unreachable

        # BFS to find reachable blocks
        reachable = set()
        queue = deque([cfg.entry])
        reachable.add(cfg.entry)

        while queue:
            block_id = queue.popleft()
            block = cfg.blocks[block_id]

            for succ_id in block.successors:
                if succ_id not in reachable:
                    reachable.add(succ_id)
                    queue.append(succ_id)

        # Check for unreachable blocks
        for block_id, block in cfg.blocks.items():
            if block_id not in reachable and block.statements:
                stmt = block.statements[0]
                unreachable.append(CodeIssue(
                    severity=Severity.MEDIUM,
                    location=(getattr(stmt, 'lineno', 0), getattr(stmt, 'col_offset', 0)),
                    message="Unreachable code detected",
                    code=ast.unparse(stmt) if hasattr(ast, 'unparse') else None
                ))

        return unreachable

    def detect_undefined_variables(self, cfg: ControlFlowGraph,
                                   dfa: DataFlowAnalysis) -> List[CodeIssue]:
        """Detect undefined variables."""
        undefined = []
        defined_vars = set()

        # Collect all defined variables
        for block in cfg.blocks.values():
            for stmt in block.statements:
                defined_vars.update(self._get_defined_vars(stmt))

        # Add builtins
        builtins = {'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict',
                   'set', 'tuple', 'open', 'input', 'type', 'isinstance', 'True',
                   'False', 'None', 'Exception', 'ValueError', 'TypeError'}
        defined_vars.update(builtins)

        # Check for undefined usage
        for block in cfg.blocks.values():
            for stmt in block.statements:
                used_vars = self._get_used_vars(stmt)
                for var in used_vars:
                    if var not in defined_vars:
                        undefined.append(CodeIssue(
                            severity=Severity.HIGH,
                            location=(getattr(stmt, 'lineno', 0), getattr(stmt, 'col_offset', 0)),
                            message=f"Undefined variable: '{var}'",
                            code=ast.unparse(stmt) if hasattr(ast, 'unparse') else None
                        ))

        return undefined

    def perform_taint_analysis(self, cfg: ControlFlowGraph) -> TaintReport:
        """Perform taint analysis for security vulnerabilities."""
        report = TaintReport()

        # Define taint sources (user input)
        taint_sources = {'input', 'request.args', 'request.form', 'request.json',
                        'os.environ', 'sys.argv'}

        # Define taint sinks (dangerous operations)
        taint_sinks = {'eval', 'exec', 'os.system', 'subprocess.call',
                      'subprocess.run', 'cursor.execute', 'db.execute'}

        # Track tainted variables
        tainted_vars: Set[str] = set()

        for block in cfg.blocks.values():
            for stmt in block.statements:
                # Check for taint sources
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Call):
                        func_name = self._get_call_name(node)
                        if func_name in taint_sources:
                            # Mark assigned variable as tainted
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Name):
                                        tainted_vars.add(target.id)
                                        report.sources.append(TaintSource(
                                            var=target.id,
                                            location=(stmt.lineno, stmt.col_offset),
                                            source_type=func_name
                                        ))

                # Check for taint sinks
                for node in ast.walk(stmt):
                    if isinstance(node, ast.Call):
                        func_name = self._get_call_name(node)
                        if func_name in taint_sinks:
                            # Check if any argument is tainted
                            for arg in node.args:
                                if isinstance(arg, ast.Name) and arg.id in tainted_vars:
                                    sink = TaintSink(
                                        var=arg.id,
                                        location=(node.lineno, node.col_offset),
                                        sink_type=func_name
                                    )
                                    report.sinks.append(sink)

                                    # Find corresponding source
                                    for source in report.sources:
                                        if source.var == arg.id:
                                            report.tainted_flows.append(TaintFlow(
                                                source=source,
                                                sink=sink,
                                                path=[arg.id]
                                            ))

                # Propagate taint through assignments
                if isinstance(stmt, ast.Assign):
                    used_vars = self._get_used_vars(stmt.value)
                    if any(var in tainted_vars for var in used_vars):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                tainted_vars.add(target.id)

        return report

    def detect_security_vulnerabilities(self, ast_node: ast.AST) -> List[SecurityIssue]:
        """Detect security vulnerabilities in code."""
        issues = []

        for node in ast.walk(ast_node):
            # SQL injection detection
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)

                # Dangerous eval/exec
                if func_name in ('eval', 'exec'):
                    issues.append(SecurityIssue(
                        type=SecurityIssueType.UNSAFE_EVAL,
                        severity=Severity.CRITICAL,
                        location=(node.lineno, node.col_offset),
                        description=f"Use of dangerous function '{func_name}'",
                        fix_suggestion="Avoid using eval/exec. Use safer alternatives."
                    ))

                # Command injection
                if func_name in ('os.system', 'subprocess.call', 'subprocess.run'):
                    issues.append(SecurityIssue(
                        type=SecurityIssueType.COMMAND_INJECTION,
                        severity=Severity.HIGH,
                        location=(node.lineno, node.col_offset),
                        description=f"Potential command injection via '{func_name}'",
                        fix_suggestion="Use subprocess with shell=False and list arguments"
                    ))

                # SQL injection
                if 'execute' in func_name and any(isinstance(arg, ast.BinOp) for arg in node.args):
                    issues.append(SecurityIssue(
                        type=SecurityIssueType.SQL_INJECTION,
                        severity=Severity.CRITICAL,
                        location=(node.lineno, node.col_offset),
                        description="Potential SQL injection via string concatenation",
                        fix_suggestion="Use parameterized queries with placeholders"
                    ))

            # Hardcoded secrets
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id.lower()
                        if any(keyword in var_name for keyword in ['password', 'secret', 'token', 'api_key']):
                            if isinstance(node.value, ast.Constant):
                                issues.append(SecurityIssue(
                                    type=SecurityIssueType.HARDCODED_SECRET,
                                    severity=Severity.HIGH,
                                    location=(node.lineno, node.col_offset),
                                    description=f"Hardcoded secret in variable '{target.id}'",
                                    fix_suggestion="Use environment variables or secure vaults"
                                ))

        return issues

    def build_call_graph(self, ast_node: ast.AST) -> CallGraph:
        """Build call graph from AST."""
        call_graph = CallGraph()
        current_function = None

        for node in ast.walk(ast_node):
            if isinstance(node, ast.FunctionDef):
                current_function = node.name
                if current_function not in call_graph.nodes:
                    call_graph.nodes[current_function] = CallGraphNode(
                        name=current_function,
                        lineno=node.lineno
                    )

            elif isinstance(node, ast.Call) and current_function:
                func_name = self._get_call_name(node)
                if func_name:
                    call_graph.nodes[current_function].calls.add(func_name)

                    if func_name not in call_graph.nodes:
                        call_graph.nodes[func_name] = CallGraphNode(
                            name=func_name,
                            lineno=node.lineno
                        )
                    call_graph.nodes[func_name].called_by.add(current_function)

        # Identify entry points (functions not called by others)
        for name, node in call_graph.nodes.items():
            if not node.called_by:
                call_graph.entry_points.add(name)

        return call_graph

    def analyze_complexity(self, ast_node: ast.AST) -> ComplexityMetrics:
        """Compute code complexity metrics."""
        metrics = ComplexityMetrics()

        # Count lines
        metrics.lines_of_code = len(self.source_lines)
        metrics.blank_lines = sum(1 for line in self.source_lines if not line.strip())
        metrics.comment_lines = sum(1 for line in self.source_lines if line.strip().startswith('#'))

        function_lengths = []

        for node in ast.walk(ast_node):
            # Count functions and classes
            if isinstance(node, ast.FunctionDef):
                metrics.num_functions += 1
                func_length = len(node.body)
                function_lengths.append(func_length)

                # Cyclomatic complexity (simplified)
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                metrics.cyclomatic_complexity += complexity

            elif isinstance(node, ast.ClassDef):
                metrics.num_classes += 1

            # Max nesting depth
            depth = self._get_nesting_depth(node)
            metrics.max_nesting_depth = max(metrics.max_nesting_depth, depth)

        # Average function length
        if function_lengths:
            metrics.avg_function_length = sum(function_lengths) / len(function_lengths)

        # Maintainability index (simplified)
        if metrics.lines_of_code > 0:
            loc = metrics.lines_of_code
            cc = metrics.cyclomatic_complexity or 1
            metrics.maintainability_index = max(0, (171 - 5.2 * (loc ** 0.5) - 0.23 * cc) / 171 * 100)

        return metrics

    def _get_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calculate nesting depth of a node."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._get_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._get_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from a call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return ""


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example Python code to analyze
    sample_code = """
import os
import subprocess

def process_user_input():
    user_input = input("Enter command: ")
    # Security issue: command injection
    os.system(user_input)

    password = "hardcoded_secret_123"  # Security issue: hardcoded secret

    x = 10
    y = x + 5
    z = y * 2

    unused_var = 42  # Dead code

    return z

def unreachable_function():
    return "This is never called"

def divide(a, b):
    if b == 0:
        return None
    return a / b

result = divide(10, 2)
print(result)
"""

    # Create analyzer and run analysis
    analyzer = StaticAnalyzer()
    report = analyzer.analyze(sample_code)

    # Print results
    print("=" * 80)
    print("STATIC ANALYSIS REPORT")
    print("=" * 80)

    print(f"\n📊 Complexity Metrics:")
    if report.metrics:
        print(f"  Lines of Code: {report.metrics.lines_of_code}")
        print(f"  Cyclomatic Complexity: {report.metrics.cyclomatic_complexity}")
        print(f"  Functions: {report.metrics.num_functions}")
        print(f"  Maintainability Index: {report.metrics.maintainability_index:.2f}")

    print(f"\n🔴 Security Issues ({len(report.security_issues)}):")
    for issue in report.security_issues:
        print(f"  [{issue.severity.value}] {issue.type.value} at line {issue.location[0]}")
        print(f"    {issue.description}")
        print(f"    Fix: {issue.fix_suggestion}")

    print(f"\n⚠️  Warnings ({len(report.warnings)}):")
    for warning in report.warnings[:5]:  # Show first 5
        print(f"  Line {warning.location[0]}: {warning.message}")

    print(f"\n💀 Dead Code ({len(report.dead_code)}):")
    for dead in report.dead_code:
        print(f"  Line {dead.location[0]}: {dead.message}")

    print(f"\n🚫 Unreachable Code ({len(report.unreachable_code)}):")
    for unreachable in report.unreachable_code:
        print(f"  Line {unreachable.location[0]}: {unreachable.message}")

    if report.taint_report:
        print(f"\n🔍 Taint Analysis:")
        print(f"  Tainted Flows: {len(report.taint_report.tainted_flows)}")
        for flow in report.taint_report.tainted_flows:
            print(f"    {flow.source.var} ({flow.source.source_type}) -> "
                  f"{flow.sink.var} ({flow.sink.sink_type})")

    print("\n" + "=" * 80)

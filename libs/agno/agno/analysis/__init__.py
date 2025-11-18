"""
Static analysis module for Python code.

Provides comprehensive static analysis capabilities including:
- Control flow analysis
- Data flow analysis
- Type inference
- Taint analysis
- Security vulnerability detection
- Code quality metrics
"""

from agno.analysis.static_analyzer import (
    StaticAnalyzer,
    AnalysisReport,
    BasicBlock,
    ControlFlowGraph,
    DataFlowAnalysis,
    TypeInferenceResult,
    TaintReport,
    SecurityIssue,
    SecurityIssueType,
    CallGraph,
    ComplexityMetrics,
    CodeIssue,
    Severity,
)

__all__ = [
    "StaticAnalyzer",
    "AnalysisReport",
    "BasicBlock",
    "ControlFlowGraph",
    "DataFlowAnalysis",
    "TypeInferenceResult",
    "TaintReport",
    "SecurityIssue",
    "SecurityIssueType",
    "CallGraph",
    "ComplexityMetrics",
    "CodeIssue",
    "Severity",
]

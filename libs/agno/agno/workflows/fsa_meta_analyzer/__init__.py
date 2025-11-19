"""
FSA Meta-Analyzer - A specialized FSA for analyzing, validating, and improving other FSAs.

This package provides comprehensive tools for analyzing workflow FSAs including:
- Static structure analysis
- Validation and error detection
- Performance profiling
- Quality metrics calculation
- Pattern detection
- Dependency analysis
- Optimization recommendations
"""

from agno.workflows.fsa_meta_analyzer.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyAnalysisReport,
    DependencyGraph,
)
from agno.workflows.fsa_meta_analyzer.meta_analyzer import FSAMetaAnalyzer, MetaAnalysisReport
from agno.workflows.fsa_meta_analyzer.optimizer import FSAOptimizer, OptimizationPlan
from agno.workflows.fsa_meta_analyzer.pattern_analyzer import (
    FSAPatternDetector,
    PatternAnalysisReport,
)
from agno.workflows.fsa_meta_analyzer.profiler import (
    FSAPerformanceProfiler,
    PerformanceAnalysis,
)
from agno.workflows.fsa_meta_analyzer.quality_metrics import QualityMetrics, QualityMetricsCalculator
from agno.workflows.fsa_meta_analyzer.static_analyzer import FSAStaticAnalyzer, FSAStructure
from agno.workflows.fsa_meta_analyzer.validator import FSAValidator, ValidationReport

__all__ = [
    # Main workflow
    'FSAMetaAnalyzer',
    'MetaAnalysisReport',
    # Analyzers
    'FSAStaticAnalyzer',
    'FSAValidator',
    'FSAPerformanceProfiler',
    'QualityMetricsCalculator',
    'FSAPatternDetector',
    'DependencyAnalyzer',
    'FSAOptimizer',
    # Data structures
    'FSAStructure',
    'ValidationReport',
    'PerformanceAnalysis',
    'QualityMetrics',
    'PatternAnalysisReport',
    'DependencyAnalysisReport',
    'DependencyGraph',
    'OptimizationPlan',
]

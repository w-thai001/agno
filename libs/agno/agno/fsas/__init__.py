"""
Functional Specialist Agents (FSAs)

This package contains FSA implementations and the FSA Generator meta-FSA.
"""

from agno.fsas.generator import (
    FSACategory,
    FSAGenerator,
    FSAGeneratorError,
    FSAImplementation,
    FSASpecification,
    InvalidSpecificationError,
    ParsedSpec,
    Template,
    TemplateRenderError,
    CodeValidationError,
    GitOperationError,
)

from agno.fsas.performance_profiler import (
    PerformanceProfilerFSA,
    PerformanceProfilerError,
    ProfileResult,
    ProfileReport,
    MemoryProfile,
    CPUProfile,
    Bottleneck,
    AnalysisReport,
    ComparisonReport,
    CascadeProfile,
    ProfilingSeverity,
    ProfileType,
)

from agno.fsas.dependency_optimizer import (
    DependencyOptimizerFSA,
    DependencyOptimizerError,
    CircularDependencyError,
    ConflictResolutionError,
    DependencyGraph,
    DependencyNode,
    Cycle,
    Conflict,
    Resolution,
    ExecutionPlan,
    OptimizedGraph,
    ValidationResult,
    DependencyType,
    ConflictType,
    ResolutionStrategy,
)

from agno.fsas.code_analyzer import (
    CodeAnalyzerFSA,
    CodeAnalyzerError,
    CodeAnalysisReport,
    ComplexityMetrics,
    CodeSmell,
    DesignPattern,
    SecurityIssue,
    RefactoringSuggestion,
    TypeCoverageReport,
    DocQualityReport,
    SmellSeverity,
    SecuritySeverity,
)

__all__ = [
    # Generator
    "FSACategory",
    "FSAGenerator",
    "FSAGeneratorError",
    "FSAImplementation",
    "FSASpecification",
    "InvalidSpecificationError",
    "ParsedSpec",
    "Template",
    "TemplateRenderError",
    "CodeValidationError",
    "GitOperationError",
    # Performance Profiler
    "PerformanceProfilerFSA",
    "PerformanceProfilerError",
    "ProfileResult",
    "ProfileReport",
    "MemoryProfile",
    "CPUProfile",
    "Bottleneck",
    "AnalysisReport",
    "ComparisonReport",
    "CascadeProfile",
    "ProfilingSeverity",
    "ProfileType",
    # Dependency Optimizer
    "DependencyOptimizerFSA",
    "DependencyOptimizerError",
    "CircularDependencyError",
    "ConflictResolutionError",
    "DependencyGraph",
    "DependencyNode",
    "Cycle",
    "Conflict",
    "Resolution",
    "ExecutionPlan",
    "OptimizedGraph",
    "ValidationResult",
    "DependencyType",
    "ConflictType",
    "ResolutionStrategy",
    # Code Analyzer
    "CodeAnalyzerFSA",
    "CodeAnalyzerError",
    "CodeAnalysisReport",
    "ComplexityMetrics",
    "CodeSmell",
    "DesignPattern",
    "SecurityIssue",
    "RefactoringSuggestion",
    "TypeCoverageReport",
    "DocQualityReport",
    "SmellSeverity",
    "SecuritySeverity",
]

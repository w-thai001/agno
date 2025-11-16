"""
Fundamentally Sequenced Actions (FSA) Framework

A meta-orchestration system for coordinating complex multi-step workflows,
code generation, optimization, and quality validation processes.

This module provides:
- Meta-FSA Orchestrator: Master coordinator for FSA workflows
- Multi-Step Code Builder: Incremental code construction with validation
- MLA Task Deconstructor: Maximum Leverage Analysis for task prioritization
- RSI Code Optimizer: Recursive Self-Improvement for code optimization
- Code Quality Validator: Comprehensive quality assurance and validation

Quick Start:
    ```python
    from agno.fsa import FSAOrchestrator, FSA, FSAExecutor, FSAContext

    # Create custom FSA executor
    class MyExecutor(FSAExecutor):
        async def execute(self, context: FSAContext):
            return "Hello from FSA!"

    # Create and run FSA
    orchestrator = FSAOrchestrator()
    orchestrator.add_fsa(FSA(
        id="my_task",
        name="My Task",
        executor=MyExecutor()
    ))

    results = await orchestrator.execute()
    ```

For detailed examples, see the examples modules for each component.
"""

# Orchestrator
from agno.fsa.orchestrator import (
    FSA,
    FSAContext,
    FSAExecutor,
    FSAOrchestrator,
    FSAResult,
    FSAStatus,
)

# Code Builder
from agno.fsa.code_builder import (
    BuildPlan,
    BuildStep,
    CodeArtifact,
    CodeBuildContext,
    CodeGenerator,
    CodeLanguage,
    CodeValidator,
    MultiStepCodeBuilder,
    PythonSyntaxValidator,
    TemplateCodeGenerator,
)

# MLA Task Deconstructor
from agno.fsa.mla_deconstructor import (
    DeconstructionResult,
    Goal,
    ImpactMetrics,
    MLATaskDeconstructor,
    Task,
    TaskCategory,
    TaskComplexity,
)

# RSI Optimizer
from agno.fsa.rsi_optimizer import (
    CodeAnalyzer,
    CodeMetrics,
    Optimization,
    OptimizationApplicator,
    OptimizationResult,
    OptimizationType,
    RSICodeOptimizer,
)

# Quality Validator
from agno.fsa.quality_validator import (
    QualityDimension,
    QualityGate,
    QualityValidator,
    QualityViolation,
    ValidationResult,
    ValidationRule,
    ViolationSeverity,
)

__all__ = [
    # Orchestrator
    "FSA",
    "FSAContext",
    "FSAExecutor",
    "FSAOrchestrator",
    "FSAResult",
    "FSAStatus",
    # Code Builder
    "BuildPlan",
    "BuildStep",
    "CodeArtifact",
    "CodeBuildContext",
    "CodeGenerator",
    "CodeLanguage",
    "CodeValidator",
    "MultiStepCodeBuilder",
    "PythonSyntaxValidator",
    "TemplateCodeGenerator",
    # MLA Task Deconstructor
    "DeconstructionResult",
    "Goal",
    "ImpactMetrics",
    "MLATaskDeconstructor",
    "Task",
    "TaskCategory",
    "TaskComplexity",
    # RSI Optimizer
    "CodeAnalyzer",
    "CodeMetrics",
    "Optimization",
    "OptimizationApplicator",
    "OptimizationResult",
    "OptimizationType",
    "RSICodeOptimizer",
    # Quality Validator
    "QualityDimension",
    "QualityGate",
    "QualityValidator",
    "QualityViolation",
    "ValidationResult",
    "ValidationRule",
    "ViolationSeverity",
]

__version__ = "1.0.0"

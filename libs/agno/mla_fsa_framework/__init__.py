"""
MLA-FSA Framework
=================

Meta-Learning Architecture Financial Services Agent Framework

A comprehensive framework for building, testing, orchestrating, and deploying
intelligent Financial Services Agents (FSAs) with production-ready features.

Features:
    - Parallel execution engine with asyncio
    - Fault tolerance with circuit breaker pattern
    - Real-time monitoring with WebSocket support
    - Hot-swapping of FSA implementations
    - Performance optimization and profiling
    - Automated test suite generation

Quick Start:
    >>> from mla_fsa_framework import FSAIntegrationLayer, FSAConfig
    >>> layer = FSAIntegrationLayer()
    >>> await layer.initialize()
    >>> await layer.execute("my_fsa", {"input": "data"})

For more information, see:
    - Documentation: https://docs.agno.dev/fsa-framework
    - GitHub: https://github.com/agno-agi/agno
"""

__version__ = "1.0.0"
__author__ = "Agno Team"
__license__ = "MIT"
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core classes
    "FSAIntegrationLayer",
    "FSATestSuiteGenerator",
    # Configuration
    "FSAConfig",
    "WorkflowDefinition",
    "WorkflowStep",
    "ExecutionContext",
    # Components
    "ParallelExecutor",
    "ErrorRecoveryManager",
    "CircuitBreaker",
    "HotSwapManager",
    "PerformanceOptimizer",
    "MonitoringDashboard",
    "WorkflowOrchestrator",
    # Base classes
    "AbstractFSA",
    "BaseFSA",
    # Enums
    "ExecutionState",
    "CircuitState",
    "Priority",
    "MetricType",
    "TestType",
    # Data models
    "ParameterSpec",
    "FunctionSpec",
    "ClassSpec",
    "ModuleSpec",
    "EdgeCase",
    "TestCase",
    "CoverageReport",
    "TestSuiteReport",
    "PerformanceMetric",
    "MonitoringEvent",
]

# Lazy imports to avoid circular dependencies and improve import time
def __getattr__(name: str):
    """Lazy import attributes on first access."""

    # Integration layer components
    if name in (
        "FSAIntegrationLayer",
        "FSAConfig",
        "WorkflowDefinition",
        "WorkflowStep",
        "ExecutionContext",
        "ParallelExecutor",
        "ErrorRecoveryManager",
        "CircuitBreaker",
        "HotSwapManager",
        "PerformanceOptimizer",
        "MonitoringDashboard",
        "WorkflowOrchestrator",
        "AbstractFSA",
        "BaseFSA",
        "ExecutionState",
        "CircuitState",
        "Priority",
        "MetricType",
        "PerformanceMetric",
        "MonitoringEvent",
        "CircuitBreakerState",
    ):
        try:
            from agno.fsa_integration_layer import (
                FSAIntegrationLayer,
                FSAConfig,
                WorkflowDefinition,
                WorkflowStep,
                ExecutionContext,
                ParallelExecutor,
                ErrorRecoveryManager,
                CircuitBreaker,
                HotSwapManager,
                PerformanceOptimizer,
                MonitoringDashboard,
                WorkflowOrchestrator,
                AbstractFSA,
                BaseFSA,
                ExecutionState,
                CircuitState,
                Priority,
                MetricType,
                PerformanceMetric,
                MonitoringEvent,
                CircuitBreakerState,
            )
            return locals()[name]
        except ImportError:
            pass

    # Test generator components
    if name in (
        "FSATestSuiteGenerator",
        "TestType",
        "ParameterSpec",
        "FunctionSpec",
        "ClassSpec",
        "ModuleSpec",
        "EdgeCase",
        "TestCase",
        "CoverageReport",
        "TestSuiteReport",
        "TestResult",
    ):
        try:
            from agno.fsa10_test_suite_generator import (
                FSATestSuiteGenerator,
                TestType,
                ParameterSpec,
                FunctionSpec,
                ClassSpec,
                ModuleSpec,
                EdgeCase,
                TestCase,
                CoverageReport,
                TestSuiteReport,
                TestResult,
            )
            return locals()[name]
        except ImportError:
            pass

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_version() -> str:
    """Return the package version."""
    return __version__


def get_config_path() -> str:
    """Return the path to the default configuration file."""
    import os
    return os.path.join(os.path.dirname(__file__), "config.json")


def load_default_config() -> dict:
    """Load and return the default configuration."""
    import json
    config_path = get_config_path()
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

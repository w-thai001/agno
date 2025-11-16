"""
FSA (Finite State Automaton) Framework for Agno

This module provides a production-ready FSA framework with specialized agents:

**Core FSAs (Phase 1 & 2):**
- Meta-FSA Orchestrator: Coordinates and manages multiple FSAs
- Multi-Step Code Builder: Builds code through structured state transitions
- MLA Task Deconstructor: Analyzes and decomposes tasks using Maximum Leverage Analysis
- RSI Code Optimizer: Self-improving code optimizer with recursive self-improvement
- Code Quality Validator: Validates code quality and standards

**Tooling FSAs (Phase 3A):**
- FSA Validator: Validates FSA definitions for correctness and completeness
- FSA Documentation Generator: Auto-generates comprehensive documentation
- FSA Testing Framework: Comprehensive testing suite for FSAs
- FSA Pattern Library: Reusable FSA patterns and templates

**Advanced Tooling FSAs (Phase 3B):**
- FSA Monitoring Dashboard: Real-time monitoring and health tracking
- FSA Workflow Designer: Visual FSA builder without code
- FSA Serialization: Save/load FSAs and checkpoint management
- FSA Performance Profiler: Performance analysis and bottleneck detection

**Resilience FSAs (Phase 3C):**
- FSA Circuit Breaker: Fault tolerance and cascading failure prevention
- FSA Debugger: Interactive debugging with breakpoints and inspection
- FSA Auto-Healer: Automatic error recovery and self-healing

**Integration FSAs (Phase 3D):**
- FSA Rate Limiter: Resource control and request throttling
- FSA Event Bus: Pub/sub messaging for decoupled communication
"""

from agno.fsa.base import FSA, FSAState, FSATransition
from agno.fsa.meta_orchestrator import MetaFSAOrchestrator
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.task_deconstructor import MLATaskDeconstructor
from agno.fsa.code_optimizer import RSICodeOptimizer
from agno.fsa.quality_validator import CodeQualityValidator
from agno.fsa.fsa_validator import FSAValidator
from agno.fsa.doc_generator import FSADocGenerator
from agno.fsa.testing_framework import FSATestingFramework
from agno.fsa.pattern_library import FSAPatternLibrary
from agno.fsa.monitoring_dashboard import FSAMonitoringDashboard
from agno.fsa.workflow_designer import FSAWorkflowDesigner
from agno.fsa.serialization import FSASerialization
from agno.fsa.performance_profiler import FSAPerformanceProfiler
from agno.fsa.circuit_breaker import FSACircuitBreaker
from agno.fsa.debugger import FSADebugger
from agno.fsa.auto_healer import FSAAutoHealer
from agno.fsa.rate_limiter import FSARateLimiter
from agno.fsa.event_bus import FSAEventBus

__all__ = [
    # Base
    "FSA",
    "FSAState",
    "FSATransition",
    # Core FSAs
    "MetaFSAOrchestrator",
    "MultiStepCodeBuilder",
    "MLATaskDeconstructor",
    "RSICodeOptimizer",
    "CodeQualityValidator",
    # Tooling FSAs (Phase 3A)
    "FSAValidator",
    "FSADocGenerator",
    "FSATestingFramework",
    "FSAPatternLibrary",
    # Advanced Tooling FSAs (Phase 3B)
    "FSAMonitoringDashboard",
    "FSAWorkflowDesigner",
    "FSASerialization",
    "FSAPerformanceProfiler",
    # Resilience FSAs (Phase 3C)
    "FSACircuitBreaker",
    "FSADebugger",
    "FSAAutoHealer",
    # Integration FSAs (Phase 3D)
    "FSARateLimiter",
    "FSAEventBus",
]

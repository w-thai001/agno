"""
FSA (Finite State Automaton) Framework for Agno

This module provides a production-ready FSA framework with specialized agents:

**Core FSAs (Phase 1 & 2):**
- Meta-FSA Orchestrator: Coordinates and manages multiple FSAs
- Multi-Step Code Builder: Builds code through structured state transitions
- MLA Task Deconstructor: Analyzes and decomposes tasks using Maximum Leverage Analysis
- RSI Code Optimizer: Self-improving code optimizer with recursive self-improvement
- Code Quality Validator: Validates code quality and standards

**Tooling FSAs (Phase 3):**
- FSA Validator: Validates FSA definitions for correctness and completeness
- FSA Documentation Generator: Auto-generates comprehensive documentation
- FSA Testing Framework: Comprehensive testing suite for FSAs
- FSA Pattern Library: Reusable FSA patterns and templates
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
    # Tooling FSAs
    "FSAValidator",
    "FSADocGenerator",
    "FSATestingFramework",
    "FSAPatternLibrary",
]

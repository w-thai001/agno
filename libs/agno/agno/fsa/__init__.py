"""
Agno FSA Framework - Production-ready Finite State Agent Framework

This module provides a comprehensive framework for building, managing, and orchestrating
Finite State Agents (FSAs) with support for dependency injection, pipeline management,
and production-grade features.
"""

from agno.fsa.registry import FSARegistry, FSAModule, FSAHealth
from agno.fsa.pipeline_manager import (
    FSAPipeline,
    FSAPipelineManager,
    PipelineExecutionResult,
)
from agno.fsa.cli import FSACLIHandler

__all__ = [
    "FSARegistry",
    "FSAModule",
    "FSAHealth",
    "FSAPipeline",
    "FSAPipelineManager",
    "PipelineExecutionResult",
    "FSACLIHandler",
]

__version__ = "1.0.0"

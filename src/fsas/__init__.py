"""
Error Recovery FSA Module

This module provides a production-ready Finite State Automaton (FSA) for handling
error detection, classification, and recovery in distributed systems.
"""

from .error_recovery_fsa import (
    ErrorRecoveryFSA,
    ErrorType,
    RecoveryState,
    ErrorContext,
    RecoveryStrategy,
)

__all__ = [
    "ErrorRecoveryFSA",
    "ErrorType",
    "RecoveryState",
    "ErrorContext",
    "RecoveryStrategy",
]

__version__ = "1.0.0"

"""
FSA (Finite State Automaton) state definitions for Progress Tracker.

This module defines the states and valid transitions for the progress tracking
state machine, ensuring proper state management throughout task execution.
"""

from enum import Enum
from typing import Dict, List, Set


class ProgressState(str, Enum):
    """
    FSA States for workflow/task progress tracking.

    State transitions follow a strict finite state machine model to ensure
    consistent and predictable progress tracking behavior.
    """

    IDLE = "idle"  # Initial state, no tracking active
    QUEUED = "queued"  # Task queued for execution
    RUNNING = "running"  # Actively executing
    PAUSED = "paused"  # Temporarily paused by user/system
    WAITING = "waiting"  # Waiting for external input/dependency
    REVIEWING = "reviewing"  # In review/validation phase
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with errors
    CANCELLED = "cancelled"  # Cancelled by user
    BLOCKED = "blocked"  # Blocked by dependency or resource


# FSA Transition Rules: Maps each state to its valid next states
STATE_TRANSITIONS: Dict[ProgressState, List[ProgressState]] = {
    ProgressState.IDLE: [ProgressState.QUEUED],
    ProgressState.QUEUED: [
        ProgressState.RUNNING,
        ProgressState.CANCELLED,
    ],
    ProgressState.RUNNING: [
        ProgressState.PAUSED,
        ProgressState.WAITING,
        ProgressState.REVIEWING,
        ProgressState.COMPLETED,
        ProgressState.FAILED,
        ProgressState.BLOCKED,
    ],
    ProgressState.PAUSED: [
        ProgressState.RUNNING,
        ProgressState.CANCELLED,
    ],
    ProgressState.WAITING: [
        ProgressState.RUNNING,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    ],
    ProgressState.REVIEWING: [
        ProgressState.RUNNING,
        ProgressState.COMPLETED,
        ProgressState.FAILED,
    ],
    ProgressState.BLOCKED: [
        ProgressState.RUNNING,
        ProgressState.FAILED,
        ProgressState.CANCELLED,
    ],
    ProgressState.FAILED: [
        ProgressState.RUNNING,  # Allow retry
        ProgressState.CANCELLED,
    ],
    ProgressState.COMPLETED: [],  # Terminal state
    ProgressState.CANCELLED: [],  # Terminal state
}


# Terminal states that cannot transition further
TERMINAL_STATES: Set[ProgressState] = {
    ProgressState.COMPLETED,
    ProgressState.CANCELLED,
}


# Active states where progress is being made
ACTIVE_STATES: Set[ProgressState] = {
    ProgressState.RUNNING,
    ProgressState.REVIEWING,
}


# States that indicate the task is not actively progressing
INACTIVE_STATES: Set[ProgressState] = {
    ProgressState.IDLE,
    ProgressState.QUEUED,
    ProgressState.PAUSED,
    ProgressState.WAITING,
    ProgressState.BLOCKED,
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ProgressState, to_state: ProgressState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition from {from_state.value} to {to_state.value}. "
            f"Valid transitions from {from_state.value}: "
            f"{[s.value for s in STATE_TRANSITIONS[from_state]]}"
        )


def validate_transition(from_state: ProgressState, to_state: ProgressState) -> bool:
    """
    Validate if a state transition is allowed by the FSA.

    Args:
        from_state: Current state
        to_state: Desired next state

    Returns:
        True if transition is valid, False otherwise
    """
    return to_state in STATE_TRANSITIONS.get(from_state, [])


def get_valid_transitions(state: ProgressState) -> List[ProgressState]:
    """
    Get all valid transition states from the current state.

    Args:
        state: Current state

    Returns:
        List of valid next states
    """
    return STATE_TRANSITIONS.get(state, [])


def is_terminal_state(state: ProgressState) -> bool:
    """
    Check if the given state is a terminal state.

    Args:
        state: State to check

    Returns:
        True if state is terminal, False otherwise
    """
    return state in TERMINAL_STATES


def is_active_state(state: ProgressState) -> bool:
    """
    Check if the given state is an active execution state.

    Args:
        state: State to check

    Returns:
        True if state is active, False otherwise
    """
    return state in ACTIVE_STATES

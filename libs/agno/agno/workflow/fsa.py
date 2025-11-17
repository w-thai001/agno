"""
Base Finite State Automaton (FSA) classes for workflow orchestration.

This module provides the foundational infrastructure for building FSA-based
workflows that coordinate multiple agents and manage complex state transitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import logging

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class FSAState(str, Enum):
    """
    Base state enumeration for FSAs.

    Extend this class to define custom states for specific FSA implementations.
    States should be descriptive and represent meaningful workflow phases.
    """
    pass


class TransitionCondition(BaseModel):
    """
    Defines a condition that must be met for a state transition.

    Conditions can be simple boolean checks or complex logic evaluating
    the current context, previous states, or external data.
    """

    name: str = Field(..., description="Descriptive name for this condition")
    check: Optional[Callable[[Dict[str, Any]], bool]] = Field(
        None,
        description="Function that evaluates if transition should occur",
        exclude=True
    )
    required_data: List[str] = Field(
        default_factory=list,
        description="Keys required in context for condition to evaluate"
    )

    class Config:
        arbitrary_types_allowed = True

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate if this condition is satisfied.

        Args:
            context: Current execution context with state data

        Returns:
            True if condition is met, False otherwise
        """
        # Check required data is present
        for key in self.required_data:
            if key not in context:
                logger.warning(f"Required data '{key}' missing for condition '{self.name}'")
                return False

        # Evaluate condition function if provided
        if self.check:
            try:
                return self.check(context)
            except Exception as e:
                logger.error(f"Error evaluating condition '{self.name}': {e}")
                return False

        # Default to True if no check function provided
        return True


class TransitionAction(BaseModel):
    """
    Defines an action to execute during a state transition.

    Actions modify context, trigger external systems, or perform
    side effects necessary for the workflow.
    """

    name: str = Field(..., description="Descriptive name for this action")
    execute: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = Field(
        None,
        description="Function that performs the action and returns updated context",
        exclude=True
    )
    is_async: bool = Field(False, description="Whether this action should run asynchronously")
    timeout_seconds: Optional[int] = Field(None, description="Maximum execution time")

    class Config:
        arbitrary_types_allowed = True

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute this action and return updated context.

        Args:
            context: Current execution context

        Returns:
            Updated context after action execution
        """
        if not self.execute:
            return context

        try:
            result = self.execute(context)
            logger.debug(f"Action '{self.name}' completed successfully")
            return result if result is not None else context
        except Exception as e:
            logger.error(f"Error executing action '{self.name}': {e}")
            context["_error"] = str(e)
            context["_failed_action"] = self.name
            return context


@dataclass
class StateTransition:
    """
    Defines a transition between two states in an FSA.

    Transitions specify source and target states, conditions that must be met,
    actions to execute, and priority for conflict resolution.
    """

    from_state: FSAState
    to_state: FSAState
    conditions: List[TransitionCondition] = field(default_factory=list)
    actions: List[TransitionAction] = field(default_factory=list)
    priority: int = 0  # Higher priority transitions evaluated first
    description: str = ""

    def can_transition(self, context: Dict[str, Any]) -> bool:
        """
        Check if all conditions for this transition are satisfied.

        Args:
            context: Current execution context

        Returns:
            True if transition can occur, False otherwise
        """
        if not self.conditions:
            return True

        return all(condition.evaluate(context) for condition in self.conditions)

    def execute_actions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all actions associated with this transition.

        Args:
            context: Current execution context

        Returns:
            Updated context after all actions
        """
        for action in self.actions:
            context = action.run(context)

            # Stop if action failed
            if "_error" in context and context.get("_failed_action") == action.name:
                logger.error(f"Action '{action.name}' failed, halting transition actions")
                break

        return context


class FSADependency(BaseModel):
    """
    Defines dependencies between FSA states or sub-FSAs.

    Used for coordinating execution order and managing data flow
    between dependent components.
    """

    name: str = Field(..., description="Identifier for this dependency")
    depends_on: List[str] = Field(..., description="List of FSA/state names this depends on")
    dependency_type: str = Field("sequential", description="Type: sequential, parallel, optional")
    data_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Map output keys from dependencies to input keys"
    )

    def is_satisfied(self, completed: Set[str]) -> bool:
        """
        Check if all dependencies are satisfied.

        Args:
            completed: Set of completed FSA/state names

        Returns:
            True if dependencies are met, False otherwise
        """
        if self.dependency_type == "optional":
            return True

        return all(dep in completed for dep in self.depends_on)

    def can_execute_parallel(self) -> bool:
        """Check if this dependency allows parallel execution."""
        return self.dependency_type == "parallel"


class FSAConfig(BaseModel):
    """
    Configuration for an FSA instance.

    Defines the complete state machine structure including states,
    transitions, dependencies, and execution parameters.
    """

    name: str = Field(..., description="Unique identifier for this FSA")
    initial_state: FSAState = Field(..., description="Starting state")
    final_states: List[FSAState] = Field(..., description="Terminal states")
    error_states: List[FSAState] = Field(
        default_factory=list,
        description="States representing error conditions"
    )
    transitions: List[StateTransition] = Field(
        default_factory=list,
        description="All possible state transitions"
    )
    dependencies: List[FSADependency] = Field(
        default_factory=list,
        description="Dependencies on other FSAs or states"
    )
    max_transitions: int = Field(
        100,
        description="Maximum transitions before forcing termination"
    )
    enable_history: bool = Field(True, description="Track state transition history")
    enable_monitoring: bool = Field(True, description="Enable progress monitoring")

    class Config:
        arbitrary_types_allowed = True


@dataclass
class FSAExecutionContext:
    """
    Runtime execution context for an FSA.

    Maintains current state, history, data, and execution metadata.
    """

    current_state: FSAState
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    transition_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_history_entry(self, from_state: FSAState, to_state: FSAState,
                         transition: StateTransition, success: bool = True):
        """Add a state transition to history."""
        entry = {
            "from_state": from_state.value,
            "to_state": to_state.value,
            "transition_description": transition.description,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "transition_count": self.transition_count
        }
        self.history.append(entry)

    def is_final(self, final_states: List[FSAState]) -> bool:
        """Check if current state is a final state."""
        return self.current_state in final_states

    def is_error(self, error_states: List[FSAState]) -> bool:
        """Check if current state is an error state."""
        return self.current_state in error_states


class FSA(ABC):
    """
    Abstract base class for Finite State Automaton implementations.

    Provides core FSA functionality including state management,
    transition execution, and execution control flow.
    """

    def __init__(self, config: FSAConfig, session_state: Optional[Dict[str, Any]] = None):
        """
        Initialize FSA with configuration and optional session state.

        Args:
            config: FSA configuration defining structure and behavior
            session_state: Optional persistent state storage
        """
        self.config = config
        self.session_state = session_state or {}

        # Initialize execution context
        context_key = f"fsa_context_{config.name}"
        if context_key not in self.session_state:
            self.context = FSAExecutionContext(
                current_state=config.initial_state,
                start_time=datetime.now()
            )
            self.session_state[context_key] = self.context
        else:
            self.context = self.session_state[context_key]

        logger.info(f"FSA '{config.name}' initialized in state '{config.initial_state.value}'")

    def get_available_transitions(self) -> List[StateTransition]:
        """
        Get all transitions available from current state.

        Returns:
            List of possible transitions, sorted by priority
        """
        transitions = [
            t for t in self.config.transitions
            if t.from_state == self.context.current_state
        ]
        return sorted(transitions, key=lambda t: t.priority, reverse=True)

    def find_transition(self) -> Optional[StateTransition]:
        """
        Find the first valid transition from current state.

        Evaluates transitions in priority order and returns the first
        whose conditions are satisfied.

        Returns:
            Valid transition or None if no transition possible
        """
        available = self.get_available_transitions()

        for transition in available:
            if transition.can_transition(self.context.data):
                logger.debug(
                    f"Found valid transition: {transition.from_state.value} -> "
                    f"{transition.to_state.value}"
                )
                return transition

        return None

    def execute_transition(self, transition: StateTransition) -> bool:
        """
        Execute a state transition.

        Args:
            transition: The transition to execute

        Returns:
            True if transition succeeded, False otherwise
        """
        old_state = self.context.current_state

        try:
            # Execute transition actions
            self.context.data = transition.execute_actions(self.context.data)

            # Check if actions failed
            if "_error" in self.context.data:
                logger.error(f"Transition actions failed: {self.context.data['_error']}")
                self.context.error = self.context.data["_error"]
                return False

            # Update state
            self.context.current_state = transition.to_state
            self.context.transition_count += 1

            # Record in history
            if self.config.enable_history:
                self.context.add_history_entry(old_state, transition.to_state, transition)

            logger.info(
                f"FSA '{self.config.name}' transitioned: {old_state.value} -> "
                f"{transition.to_state.value}"
            )

            return True

        except Exception as e:
            logger.error(f"Error executing transition: {e}")
            self.context.error = str(e)
            if self.config.enable_history:
                self.context.add_history_entry(old_state, transition.to_state, transition, success=False)
            return False

    def is_complete(self) -> bool:
        """Check if FSA has reached a final state."""
        return self.context.is_final(self.config.final_states)

    def is_error_state(self) -> bool:
        """Check if FSA is in an error state."""
        return self.context.is_error(self.config.error_states)

    def has_exceeded_max_transitions(self) -> bool:
        """Check if maximum transition count exceeded."""
        return self.context.transition_count >= self.config.max_transitions

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Execute the FSA. Must be implemented by subclasses.

        Args:
            **kwargs: Implementation-specific parameters

        Returns:
            Implementation-specific result
        """
        pass

    def get_progress(self) -> Dict[str, Any]:
        """
        Get current execution progress information.

        Returns:
            Dictionary with progress metrics
        """
        return {
            "fsa_name": self.config.name,
            "current_state": self.context.current_state.value,
            "transition_count": self.context.transition_count,
            "max_transitions": self.config.max_transitions,
            "is_complete": self.is_complete(),
            "is_error": self.is_error_state(),
            "start_time": self.context.start_time.isoformat() if self.context.start_time else None,
            "error": self.context.error
        }

    def reset(self):
        """Reset FSA to initial state."""
        self.context = FSAExecutionContext(
            current_state=self.config.initial_state,
            start_time=datetime.now()
        )
        context_key = f"fsa_context_{self.config.name}"
        self.session_state[context_key] = self.context
        logger.info(f"FSA '{self.config.name}' reset to initial state")

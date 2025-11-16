"""
Base FSA (Finite State Automaton) Framework

Provides core FSA functionality for building stateful agentic systems with:
- State management and transitions
- Event-driven execution
- Error handling and recovery
- Progress tracking
- Extensible state machine architecture
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from pydantic import BaseModel

from agno.agent import Agent
from agno.utils.log import logger


class FSAState(str, Enum):
    """Base FSA states - extend in subclasses"""
    INITIAL = "initial"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class FSATransition:
    """Represents a state transition in the FSA"""
    from_state: FSAState
    to_state: FSAState
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    description: str = ""

    def can_transition(self, context: Dict[str, Any]) -> bool:
        """Check if transition is allowed given current context"""
        if self.condition is None:
            return True
        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Transition condition failed: {e}")
            return False

    def execute_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute transition action and return updated context"""
        if self.action is None:
            return context
        try:
            return self.action(context)
        except Exception as e:
            logger.error(f"Transition action failed: {e}")
            raise


class FSAExecutionResult(BaseModel):
    """Result of FSA execution"""
    fsa_id: str
    fsa_name: str
    final_state: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    state_history: List[str] = []
    execution_time: float = 0.0


@dataclass
class FSA:
    """
    Base Finite State Automaton class

    Provides a foundation for building stateful agentic systems with:
    - State management and transitions
    - Event-driven execution
    - Error handling and recovery
    - Progress tracking

    Example:
        ```python
        class MyFSA(FSA):
            def __init__(self):
                super().__init__(name="MyFSA", initial_state=FSAState.INITIAL)
                self.add_transition(FSAState.INITIAL, FSAState.RUNNING,
                                   action=self.start_execution)
                self.add_transition(FSAState.RUNNING, FSAState.SUCCESS,
                                   condition=lambda ctx: ctx.get("done", False))

            def start_execution(self, context):
                # Custom logic
                return context
        ```
    """

    # FSA Identity
    name: str
    fsa_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""

    # State Management
    current_state: FSAState = FSAState.INITIAL
    initial_state: FSAState = FSAState.INITIAL
    final_states: Set[FSAState] = field(default_factory=lambda: {FSAState.SUCCESS, FSAState.FAILED})

    # Transitions
    transitions: Dict[FSAState, List[FSATransition]] = field(default_factory=dict)

    # Execution Context
    context: Dict[str, Any] = field(default_factory=dict)
    state_history: List[FSAState] = field(default_factory=list)

    # Agents (optional - for agentic FSAs)
    agent: Optional[Agent] = None

    # Configuration
    max_transitions: int = 1000  # Prevent infinite loops
    debug_mode: bool = False

    def __post_init__(self):
        """Initialize FSA after dataclass initialization"""
        self.current_state = self.initial_state
        self.state_history.append(self.current_state)
        if self.debug_mode:
            logger.debug(f"FSA {self.name} initialized in state {self.current_state}")

    def add_transition(
        self,
        from_state: FSAState,
        to_state: FSAState,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        action: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        description: str = ""
    ) -> None:
        """
        Add a transition to the FSA

        Args:
            from_state: Source state
            to_state: Destination state
            condition: Optional callable that returns True if transition is allowed
            action: Optional callable to execute during transition
            description: Human-readable description of the transition
        """
        if from_state not in self.transitions:
            self.transitions[from_state] = []

        transition = FSATransition(
            from_state=from_state,
            to_state=to_state,
            condition=condition,
            action=action,
            description=description
        )
        self.transitions[from_state].append(transition)

        if self.debug_mode:
            logger.debug(f"Added transition: {from_state} -> {to_state}")

    def transition_to(self, new_state: FSAState, force: bool = False) -> bool:
        """
        Transition to a new state

        Args:
            new_state: Target state
            force: If True, bypass transition validation

        Returns:
            True if transition successful, False otherwise
        """
        if force:
            self._execute_transition(new_state)
            return True

        # Find valid transition
        if self.current_state not in self.transitions:
            logger.error(f"No transitions defined from state {self.current_state}")
            return False

        for transition in self.transitions[self.current_state]:
            if transition.to_state == new_state and transition.can_transition(self.context):
                # Execute transition action
                if transition.action:
                    self.context = transition.execute_action(self.context)

                self._execute_transition(new_state)
                return True

        logger.error(f"No valid transition from {self.current_state} to {new_state}")
        return False

    def _execute_transition(self, new_state: FSAState) -> None:
        """Internal method to execute state transition"""
        old_state = self.current_state
        self.current_state = new_state
        self.state_history.append(new_state)

        if self.debug_mode:
            logger.debug(f"FSA {self.name}: {old_state} -> {new_state}")

        # Call state entry hook
        self.on_state_enter(new_state)

    def on_state_enter(self, state: FSAState) -> None:
        """
        Hook called when entering a new state
        Override in subclasses for custom behavior
        """
        pass

    def on_state_exit(self, state: FSAState) -> None:
        """
        Hook called when exiting a state
        Override in subclasses for custom behavior
        """
        pass

    def step(self) -> bool:
        """
        Execute one step of the FSA (find and execute next valid transition)

        Returns:
            True if a transition was executed, False if no valid transition found
        """
        if self.is_final():
            return False

        if self.current_state not in self.transitions:
            logger.warning(f"No transitions from state {self.current_state}")
            return False

        # Try each transition in order
        for transition in self.transitions[self.current_state]:
            if transition.can_transition(self.context):
                # Execute action
                if transition.action:
                    self.context = transition.execute_action(self.context)

                self._execute_transition(transition.to_state)
                return True

        # No valid transition found
        logger.warning(f"No valid transition from {self.current_state} with current context")
        return False

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> FSAExecutionResult:
        """
        Run the FSA until it reaches a final state

        Args:
            initial_context: Initial context data

        Returns:
            FSAExecutionResult with execution details
        """
        import time
        start_time = time.time()

        # Initialize context
        if initial_context:
            self.context.update(initial_context)

        transitions_executed = 0
        success = False
        error = None

        try:
            while not self.is_final() and transitions_executed < self.max_transitions:
                if not self.step():
                    # No valid transition - might be stuck
                    logger.warning(f"FSA {self.name} stuck in state {self.current_state}")
                    break
                transitions_executed += 1

            if transitions_executed >= self.max_transitions:
                error = f"Max transitions ({self.max_transitions}) exceeded"
                logger.error(error)

            success = self.current_state == FSAState.SUCCESS

        except Exception as e:
            error = str(e)
            logger.error(f"FSA execution failed: {e}")
            self.current_state = FSAState.FAILED

        execution_time = time.time() - start_time

        return FSAExecutionResult(
            fsa_id=self.fsa_id,
            fsa_name=self.name,
            final_state=self.current_state.value,
            success=success,
            output=self.context.get("output"),
            error=error,
            metadata={
                "transitions_executed": transitions_executed,
                "context": self.context,
            },
            state_history=[s.value for s in self.state_history],
            execution_time=execution_time
        )

    def is_final(self) -> bool:
        """Check if current state is a final state"""
        return self.current_state in self.final_states

    def reset(self) -> None:
        """Reset FSA to initial state"""
        self.current_state = self.initial_state
        self.state_history = [self.initial_state]
        self.context = {}

        if self.debug_mode:
            logger.debug(f"FSA {self.name} reset to {self.initial_state}")

    def get_state_diagram(self) -> str:
        """
        Generate a text representation of the FSA state diagram

        Returns:
            String representation of states and transitions
        """
        diagram = f"FSA: {self.name}\n"
        diagram += f"Current State: {self.current_state}\n"
        diagram += "\nTransitions:\n"

        for from_state, transitions in self.transitions.items():
            for trans in transitions:
                diagram += f"  {from_state.value} -> {trans.to_state.value}"
                if trans.description:
                    diagram += f" ({trans.description})"
                diagram += "\n"

        return diagram

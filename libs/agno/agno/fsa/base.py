"""
Base classes for Finite State Automaton (FSA) implementation in Agno Framework.

FSAs provide a state-driven approach to agent orchestration where execution flows
through defined states with explicit transitions based on conditions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Union
from enum import Enum
import logging

from agno.workflow.workflow import Workflow
from agno.agent.agent import Agent
from agno.run.response import RunResponse, RunEvent
from agno.utils.log import logger


class StateStatus(str, Enum):
    """Status of a state execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StateContext:
    """
    Context object that carries data and metadata through FSA state transitions.

    Attributes:
        data: Main data payload passed between states
        metadata: Additional metadata about execution
        error: Error information if state failed
        retry_count: Number of retries attempted
        state_history: List of states visited during execution
    """
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    retry_count: int = 0
    state_history: List[str] = field(default_factory=list)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the context data"""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context data"""
        return self.data.get(key, default)

    def update(self, **kwargs: Any) -> None:
        """Update multiple values in the context data"""
        self.data.update(kwargs)

    def clear_error(self) -> None:
        """Clear error state"""
        self.error = None

    def set_error(self, error: Exception) -> None:
        """Set error state"""
        self.error = error

    def increment_retry(self) -> int:
        """Increment retry count and return new value"""
        self.retry_count += 1
        return self.retry_count

    def reset_retry(self) -> None:
        """Reset retry counter"""
        self.retry_count = 0

    def add_to_history(self, state_name: str) -> None:
        """Add state to execution history"""
        self.state_history.append(state_name)


@dataclass
class Transition:
    """
    Defines a transition from one state to another.

    Attributes:
        from_state: Name of the source state
        to_state: Name of the target state
        condition: Callable that determines if transition should occur
        priority: Priority for evaluating multiple transitions (higher = earlier)
    """
    from_state: str
    to_state: str
    condition: Callable[[StateContext], bool]
    priority: int = 0

    def should_transition(self, context: StateContext) -> bool:
        """Evaluate if transition condition is met"""
        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Error evaluating transition condition: {e}")
            return False


@dataclass
class State:
    """
    Represents a state in the FSA.

    A state can optionally have an agent that executes when the state is entered.
    States can also have custom entry/exit handlers for setup and cleanup.

    Attributes:
        name: Unique identifier for the state
        agent: Optional agent to execute in this state
        on_enter: Optional callback executed when entering state
        on_exit: Optional callback executed when leaving state
        execute_func: Optional custom execution function instead of agent
        is_terminal: Whether this is a final state (no outgoing transitions)
        max_retries: Maximum number of retries allowed for this state
        status: Current execution status of the state
    """
    name: str
    agent: Optional[Agent] = None
    on_enter: Optional[Callable[[StateContext], None]] = None
    on_exit: Optional[Callable[[StateContext], None]] = None
    execute_func: Optional[Callable[[StateContext], StateContext]] = None
    is_terminal: bool = False
    max_retries: int = 3
    status: StateStatus = StateStatus.PENDING

    def enter(self, context: StateContext) -> None:
        """Execute state entry logic"""
        logger.info(f"Entering state: {self.name}")
        context.add_to_history(self.name)
        self.status = StateStatus.IN_PROGRESS

        if self.on_enter:
            try:
                self.on_enter(context)
            except Exception as e:
                logger.error(f"Error in on_enter for state {self.name}: {e}")
                raise

    def exit(self, context: StateContext) -> None:
        """Execute state exit logic"""
        logger.info(f"Exiting state: {self.name}")

        if self.on_exit:
            try:
                self.on_exit(context)
            except Exception as e:
                logger.error(f"Error in on_exit for state {self.name}: {e}")
                raise

    def execute(self, context: StateContext) -> Iterator[RunResponse]:
        """
        Execute state logic.

        If state has an agent, run the agent with context data.
        If state has execute_func, call it directly.
        Otherwise, state is a pass-through.
        """
        try:
            if self.execute_func:
                # Custom execution function
                logger.debug(f"Executing custom function for state: {self.name}")
                updated_context = self.execute_func(context)
                if updated_context:
                    context.data.update(updated_context.data)
                    context.metadata.update(updated_context.metadata)

                yield RunResponse(
                    content=f"State {self.name} completed",
                    event=RunEvent.run_response.value,
                )
                self.status = StateStatus.COMPLETED

            elif self.agent:
                # Execute agent
                logger.debug(f"Executing agent for state: {self.name}")

                # Prepare agent input from context
                agent_input = context.get("agent_input", context.data)

                # Run agent and yield responses
                for response in self.agent.run(agent_input, stream=True):
                    # Store agent response in context
                    if response.content:
                        context.set("last_agent_response", response.content)
                    if response.messages:
                        context.set("last_agent_messages", response.messages)

                    yield response

                self.status = StateStatus.COMPLETED
            else:
                # Pass-through state
                logger.debug(f"Pass-through state: {self.name}")
                yield RunResponse(
                    content=f"State {self.name} (pass-through)",
                    event=RunEvent.run_response.value,
                )
                self.status = StateStatus.COMPLETED

        except Exception as e:
            logger.error(f"Error executing state {self.name}: {e}")
            context.set_error(e)
            self.status = StateStatus.FAILED
            raise


@dataclass(init=False)
class FSA(Workflow):
    """
    Finite State Automaton (FSA) implementation.

    FSA extends Workflow to provide state-machine based orchestration of agents.
    Execution flows through defined states with explicit transitions based on conditions.

    Features:
    - State-driven execution flow
    - Conditional transitions between states
    - Context passing between states
    - Built-in error handling and retry logic
    - State execution history tracking
    - Terminal state detection

    Example:
        >>> fsa = FSA(name="my_fsa", initial_state="start")
        >>> fsa.add_state(State(name="start", agent=my_agent))
        >>> fsa.add_state(State(name="end", is_terminal=True))
        >>> fsa.add_transition(Transition(
        ...     from_state="start",
        ...     to_state="end",
        ...     condition=lambda ctx: ctx.get("success") == True
        ... ))
        >>> for response in fsa.run():
        ...     print(response.content)
    """

    # FSA-specific attributes
    states: Dict[str, State] = field(default_factory=dict)
    transitions: List[Transition] = field(default_factory=list)
    initial_state: Optional[str] = None
    current_state: Optional[str] = None
    context: Optional[StateContext] = None
    max_iterations: int = 100  # Prevent infinite loops

    def __init__(
        self,
        name: Optional[str] = None,
        initial_state: Optional[str] = None,
        max_iterations: int = 100,
        **kwargs: Any,
    ):
        """
        Initialize FSA.

        Args:
            name: Name of the FSA
            initial_state: Name of the starting state
            max_iterations: Maximum number of state transitions to prevent infinite loops
            **kwargs: Additional arguments passed to Workflow
        """
        super().__init__(name=name, **kwargs)
        self.states = {}
        self.transitions = []
        self.initial_state = initial_state
        self.current_state = None
        self.context = StateContext()
        self.max_iterations = max_iterations

    def add_state(self, state: State) -> "FSA":
        """
        Add a state to the FSA.

        Args:
            state: State to add

        Returns:
            Self for method chaining
        """
        if state.name in self.states:
            logger.warning(f"State {state.name} already exists, overwriting")

        self.states[state.name] = state
        logger.debug(f"Added state: {state.name}")
        return self

    def add_transition(self, transition: Transition) -> "FSA":
        """
        Add a transition between states.

        Args:
            transition: Transition to add

        Returns:
            Self for method chaining
        """
        # Validate states exist
        if transition.from_state not in self.states:
            raise ValueError(f"From state '{transition.from_state}' does not exist")
        if transition.to_state not in self.states:
            raise ValueError(f"To state '{transition.to_state}' does not exist")

        self.transitions.append(transition)
        logger.debug(f"Added transition: {transition.from_state} -> {transition.to_state}")
        return self

    def get_next_state(self, context: StateContext) -> Optional[str]:
        """
        Determine next state based on transitions.

        Args:
            context: Current state context

        Returns:
            Name of next state or None if no transition condition is met
        """
        if not self.current_state:
            return None

        # Get current state
        current = self.states.get(self.current_state)
        if current and current.is_terminal:
            logger.info(f"Current state {self.current_state} is terminal")
            return None

        # Find applicable transitions from current state
        applicable_transitions = [
            t for t in self.transitions
            if t.from_state == self.current_state
        ]

        # Sort by priority (higher priority first)
        applicable_transitions.sort(key=lambda t: t.priority, reverse=True)

        # Find first transition whose condition is met
        for transition in applicable_transitions:
            if transition.should_transition(context):
                logger.info(f"Transition condition met: {transition.from_state} -> {transition.to_state}")
                return transition.to_state

        # No transition condition met
        logger.debug(f"No transition condition met from state {self.current_state}")
        return None

    def run(self, initial_context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Iterator[RunResponse]:
        """
        Execute the FSA.

        Args:
            initial_context: Initial data to populate the context
            **kwargs: Additional context data

        Yields:
            RunResponse objects for each state execution
        """
        # Initialize context
        self.context = StateContext()
        if initial_context:
            self.context.data.update(initial_context)
        if kwargs:
            self.context.data.update(kwargs)

        # Set initial state
        if not self.initial_state:
            raise ValueError("Initial state not set")

        if self.initial_state not in self.states:
            raise ValueError(f"Initial state '{self.initial_state}' does not exist")

        self.current_state = self.initial_state

        # Emit workflow started event
        yield RunResponse(
            content=f"FSA {self.name} started",
            event=RunEvent.workflow_started.value,
            workflow_id=self.workflow_id,
        )

        iteration = 0

        # Execute state machine
        while self.current_state and iteration < self.max_iterations:
            iteration += 1

            # Get current state
            state = self.states.get(self.current_state)
            if not state:
                raise ValueError(f"State '{self.current_state}' not found")

            logger.info(f"Executing state: {self.current_state} (iteration {iteration})")

            try:
                # Enter state
                state.enter(self.context)

                # Execute state
                for response in state.execute(self.context):
                    yield response

                # Exit state
                state.exit(self.context)

                # Clear error state if execution succeeded
                self.context.clear_error()
                self.context.reset_retry()

            except Exception as e:
                logger.error(f"Error in state {self.current_state}: {e}")
                self.context.set_error(e)

                # Emit error event
                yield RunResponse(
                    content=f"Error in state {self.current_state}: {str(e)}",
                    event=RunEvent.run_error.value,
                    workflow_id=self.workflow_id,
                )

                # Check if we should retry or transition to error state
                if self.context.retry_count < state.max_retries:
                    self.context.increment_retry()
                    logger.info(f"Retrying state {self.current_state} (attempt {self.context.retry_count})")
                    continue
                else:
                    # Max retries exceeded, try to find error transition
                    logger.error(f"Max retries exceeded for state {self.current_state}")
                    break

            # Determine next state
            next_state = self.get_next_state(self.context)

            if next_state:
                logger.info(f"Transitioning: {self.current_state} -> {next_state}")
                self.current_state = next_state
            else:
                # No valid transition, end execution
                logger.info("No valid transition found, ending FSA execution")
                break

        if iteration >= self.max_iterations:
            logger.warning(f"FSA reached max iterations ({self.max_iterations})")
            yield RunResponse(
                content=f"FSA reached max iterations ({self.max_iterations})",
                event=RunEvent.run_error.value,
                workflow_id=self.workflow_id,
            )

        # Emit workflow completed event
        yield RunResponse(
            content=f"FSA {self.name} completed",
            event=RunEvent.workflow_completed.value,
            workflow_id=self.workflow_id,
        )

    def visualize(self) -> str:
        """
        Generate a text representation of the FSA structure.

        Returns:
            String representation of states and transitions
        """
        lines = [f"FSA: {self.name}"]
        lines.append(f"Initial State: {self.initial_state}")
        lines.append("\nStates:")
        for name, state in self.states.items():
            terminal = " (terminal)" if state.is_terminal else ""
            agent_info = f" [agent: {state.agent.name}]" if state.agent else ""
            lines.append(f"  - {name}{terminal}{agent_info}")

        lines.append("\nTransitions:")
        for transition in self.transitions:
            lines.append(f"  - {transition.from_state} -> {transition.to_state} (priority: {transition.priority})")

        return "\n".join(lines)

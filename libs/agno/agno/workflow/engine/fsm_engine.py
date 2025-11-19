"""
Finite State Machine Workflow Engine.

Production-ready workflow orchestration engine with FSA-based execution,
conditional branching, parallel execution, error handling, and progress tracking.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field

from agno.run.response import RunEvent, RunResponse
from agno.utils.log import logger
from agno.workflow.engine.context import ExecutionContext
from agno.workflow.engine.state import State, StateGraph, StateStatus
from agno.workflow.workflow import Workflow


class WorkflowEngineConfig(BaseModel):
    """Configuration for workflow engine."""

    name: str = Field("workflow_engine", description="Engine name")
    max_parallel_tasks: int = Field(
        5, description="Maximum parallel task executions", ge=1, le=20
    )
    default_timeout_seconds: int = Field(
        300, description="Default state timeout in seconds", ge=1
    )
    enable_progress_tracking: bool = Field(
        True, description="Enable progress event emission"
    )
    enable_state_caching: bool = Field(
        False, description="Cache state execution results"
    )
    retry_delay_seconds: float = Field(
        1.0, description="Delay between retries in seconds", ge=0
    )
    max_execution_time_seconds: int = Field(
        3600, description="Maximum total execution time", ge=1
    )


@dataclass(init=False)
class WorkflowEngine(Workflow):
    """
    Finite State Machine based workflow engine.

    Provides production-ready workflow orchestration with:
    - FSA-based state management
    - Conditional branching
    - Parallel execution support
    - Comprehensive error handling
    - Progress tracking
    - State persistence via existing Workflow infrastructure

    Example:
        ```python
        engine = WorkflowEngine(name="order_processing")

        # Define states
        validate = State(name="validate", is_initial=True)
        process = State(name="process")
        complete = State(name="complete", is_final=True)

        # Add transitions
        validate.add_transition("process")
        process.add_transition("complete")

        # Add states to engine
        engine.add_state(validate)
        engine.add_state(process)
        engine.add_state(complete)

        # Execute workflow
        result = engine.run(order_id="12345")
        ```
    """

    config: WorkflowEngineConfig
    state_graph: StateGraph
    state_handlers: Dict[str, Callable]
    _execution_context: Optional[ExecutionContext]

    def __init__(
        self,
        name: str = "workflow_engine",
        config: Optional[WorkflowEngineConfig] = None,
        **kwargs,
    ):
        """
        Initialize workflow engine.

        Args:
            name: Engine name
            config: Engine configuration
            **kwargs: Additional Workflow parameters
        """
        # Initialize parent Workflow
        super().__init__(name=name, **kwargs)

        # Initialize engine-specific attributes
        self.config = config or WorkflowEngineConfig(name=name)
        self.state_graph = StateGraph()
        self.state_handlers = {}
        self._execution_context = None

    def add_state(
        self,
        state: State,
        handler: Optional[Callable] = None,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
    ) -> State:
        """
        Add a state to the workflow.

        Args:
            state: State to add
            handler: Function to execute in this state
            on_enter: Callback when entering state
            on_exit: Callback when exiting state

        Returns:
            The added state
        """
        # Update state with callbacks
        if handler:
            state.handler = handler
        if on_enter:
            state.on_enter = on_enter
        if on_exit:
            state.on_exit = on_exit

        # Add to graph
        self.state_graph.add_state(state)

        # Register handler
        if state.handler:
            self.state_handlers[state.name] = state.handler

        logger.debug(f"Added state '{state.name}' to workflow engine '{self.name}'")
        return state

    def validate(self) -> List[str]:
        """
        Validate the workflow configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = self.state_graph.validate_graph()

        # Check handlers exist for non-final states
        for state in self.state_graph.states.values():
            if not state.is_final and not state.handler:
                errors.append(f"State '{state.name}' has no handler function")

        return errors

    def run(self, **kwargs) -> Iterator[RunResponse]:
        """
        Execute the workflow.

        Args:
            **kwargs: Input parameters for the workflow

        Yields:
            RunResponse objects tracking execution progress
        """
        # Validate workflow
        validation_errors = self.validate()
        if validation_errors:
            error_msg = f"Workflow validation failed: {'; '.join(validation_errors)}"
            logger.error(error_msg)
            yield RunResponse(
                content=None,
                event=RunEvent.run_error.value,
                workflow_id=self.workflow_id,
                messages=[{"role": "system", "content": error_msg}],
            )
            return

        # Initialize execution context
        self._execution_context = ExecutionContext(
            workflow_id=self.workflow_id or self.name
        )
        self._execution_context.update(kwargs)

        # Emit start event
        yield RunResponse(
            content={"status": "started", "workflow": self.name},
            event=RunEvent.run_started.value,
            workflow_id=self.workflow_id,
        )

        # Execute workflow
        try:
            start_time = time.time()
            max_time = self.config.max_execution_time_seconds

            # Execute state machine
            for response in self._execute_fsm():
                yield response

                # Check timeout
                if time.time() - start_time > max_time:
                    raise TimeoutError(
                        f"Workflow execution exceeded {max_time} seconds"
                    )

            # Workflow completed successfully
            self._execution_context.complete()

            yield RunResponse(
                content={
                    "status": "completed",
                    "result": self._execution_context.variables,
                    "execution_path": self._execution_context.get_execution_path(),
                    "duration_ms": self._execution_context.get_total_duration_ms(),
                    "statistics": self._execution_context.get_state_statistics(),
                },
                event=RunEvent.run_completed.value,
                workflow_id=self.workflow_id,
            )

        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._execution_context.complete(error=error_msg)

            yield RunResponse(
                content={"status": "failed", "error": error_msg},
                event=RunEvent.run_error.value,
                workflow_id=self.workflow_id,
            )

    def _execute_fsm(self) -> Iterator[RunResponse]:
        """
        Execute the finite state machine.

        Yields:
            RunResponse objects for each state transition
        """
        if not self.state_graph.initial_state:
            raise ValueError("No initial state defined")

        current_state_name = self.state_graph.initial_state
        context = self._execution_context

        while current_state_name:
            state = self.state_graph.get_state(current_state_name)
            if not state:
                raise ValueError(f"State '{current_state_name}' not found")

            # Execute state
            for response in self._execute_state(state):
                yield response

            # Check if final state
            if state.is_final:
                logger.info(f"Reached final state '{state.name}'")
                break

            # Determine next state
            next_state_name = state.get_next_state(context.to_dict())

            if not next_state_name:
                # No valid transition found
                if state.transitions:
                    error_msg = f"No valid transition from state '{state.name}' with current context"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                else:
                    # No transitions defined - must be a final state
                    logger.warning(
                        f"State '{state.name}' has no transitions but is not marked as final"
                    )
                    break

            # Emit transition event
            if self.config.enable_progress_tracking:
                yield RunResponse(
                    content={
                        "status": "transition",
                        "from_state": current_state_name,
                        "to_state": next_state_name,
                    },
                    event=RunEvent.run_response.value,
                    workflow_id=self.workflow_id,
                )

            current_state_name = next_state_name

    def _execute_state(self, state: State) -> Iterator[RunResponse]:
        """
        Execute a single state with retries and error handling.

        Args:
            state: State to execute

        Yields:
            RunResponse objects for state execution
        """
        context = self._execution_context
        max_attempts = state.retry_count + 1

        for attempt in range(1, max_attempts + 1):
            try:
                # Start execution tracking
                execution = context.start_state_execution(state.name, attempt=attempt)
                state.status = StateStatus.RUNNING
                state.attempt = attempt

                # Emit progress event
                if self.config.enable_progress_tracking:
                    yield RunResponse(
                        content={
                            "status": "state_started",
                            "state": state.name,
                            "attempt": attempt,
                        },
                        event=RunEvent.run_response.value,
                        workflow_id=self.workflow_id,
                    )

                # Execute on_enter callback
                if state.on_enter:
                    state.on_enter(context)

                # Execute state handler
                result = None
                if state.handler:
                    # Set timeout if specified
                    timeout = state.timeout_seconds or self.config.default_timeout_seconds

                    result = self._execute_with_timeout(
                        state.handler, context, timeout
                    )

                # Execute on_exit callback
                if state.on_exit:
                    state.on_exit(context)

                # Mark as completed
                state.status = StateStatus.COMPLETED
                state.result = result
                context.complete_state_execution(result=result)

                # Emit completion event
                if self.config.enable_progress_tracking:
                    yield RunResponse(
                        content={
                            "status": "state_completed",
                            "state": state.name,
                            "result": result,
                            "duration_ms": execution.duration_ms,
                        },
                        event=RunEvent.run_response.value,
                        workflow_id=self.workflow_id,
                    )

                # Success - exit retry loop
                break

            except Exception as e:
                error_msg = f"State '{state.name}' failed (attempt {attempt}/{max_attempts}): {str(e)}"
                logger.error(error_msg, exc_info=True)

                state.status = StateStatus.FAILED
                state.error = error_msg
                context.complete_state_execution(error=error_msg)

                # Check if we should retry
                if attempt < max_attempts:
                    logger.info(
                        f"Retrying state '{state.name}' after {self.config.retry_delay_seconds}s"
                    )
                    time.sleep(self.config.retry_delay_seconds)
                    continue
                else:
                    # All retries exhausted
                    yield RunResponse(
                        content={
                            "status": "state_failed",
                            "state": state.name,
                            "error": error_msg,
                        },
                        event=RunEvent.run_error.value,
                        workflow_id=self.workflow_id,
                    )
                    raise

    def _execute_with_timeout(
        self, handler: Callable, context: ExecutionContext, timeout: int
    ) -> Any:
        """
        Execute a handler with timeout.

        Args:
            handler: Handler function to execute
            context: Execution context
            timeout: Timeout in seconds

        Returns:
            Handler result

        Raises:
            TimeoutError: If handler exceeds timeout
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(handler, context)
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                raise TimeoutError(
                    f"Handler execution exceeded timeout of {timeout}s"
                )

    def execute_parallel(
        self, tasks: List[Callable], context: ExecutionContext
    ) -> List[Any]:
        """
        Execute multiple tasks in parallel.

        Args:
            tasks: List of task functions to execute
            context: Execution context

        Returns:
            List of task results in order

        Raises:
            Exception: If any task fails
        """
        results = [None] * len(tasks)
        max_workers = min(self.config.max_parallel_tasks, len(tasks))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(task, context): i for i, task in enumerate(tasks)
            }

            # Collect results
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    logger.error(f"Parallel task {index} failed: {e}", exc_info=True)
                    raise

        return results

    def get_execution_context(self) -> Optional[ExecutionContext]:
        """Get the current execution context."""
        return self._execution_context

    def reset(self) -> None:
        """Reset all states and execution context."""
        for state in self.state_graph.states.values():
            state.reset()
        self._execution_context = None
        logger.debug(f"Reset workflow engine '{self.name}'")

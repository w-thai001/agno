"""
Execution context for workflow engine.

Manages the runtime state, variables, and execution history during workflow execution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agno.workflow.engine.state import StateStatus


class StateExecution(BaseModel):
    """Tracks execution of a single state."""

    state_name: str = Field(..., description="Name of the state")
    status: StateStatus = Field(..., description="Execution status")
    started_at: datetime = Field(
        default_factory=datetime.now, description="Start timestamp"
    )
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[Any] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    attempt: int = Field(1, description="Attempt number")
    duration_ms: Optional[float] = Field(None, description="Execution duration in ms")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )

    def complete(self, result: Any = None, error: Optional[str] = None) -> None:
        """Mark execution as completed."""
        self.completed_at = datetime.now()
        self.result = result
        self.error = error
        self.status = StateStatus.FAILED if error else StateStatus.COMPLETED

        if self.completed_at and self.started_at:
            self.duration_ms = (
                self.completed_at - self.started_at
            ).total_seconds() * 1000


class ExecutionContext(BaseModel):
    """
    Manages workflow execution context and state.

    This class tracks variables, execution history, and provides
    a scoped environment for state handlers and transitions.
    """

    workflow_id: str = Field(..., description="Unique workflow execution ID")
    variables: Dict[str, Any] = Field(
        default_factory=dict, description="Execution variables"
    )
    execution_history: List[StateExecution] = Field(
        default_factory=list, description="History of state executions"
    )
    current_state: Optional[str] = Field(None, description="Current state name")
    started_at: datetime = Field(
        default_factory=datetime.now, description="Workflow start time"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Workflow completion time"
    )
    error: Optional[str] = Field(None, description="Workflow-level error")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )

    def set(self, key: str, value: Any) -> None:
        """
        Set a variable in the execution context.

        Args:
            key: Variable name
            value: Variable value
        """
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a variable from the execution context.

        Args:
            key: Variable name
            default: Default value if key not found

        Returns:
            Variable value or default
        """
        return self.variables.get(key, default)

    def has(self, key: str) -> bool:
        """Check if variable exists in context."""
        return key in self.variables

    def delete(self, key: str) -> None:
        """Remove a variable from context."""
        self.variables.pop(key, None)

    def update(self, variables: Dict[str, Any]) -> None:
        """
        Update multiple variables at once.

        Args:
            variables: Dictionary of variables to update
        """
        self.variables.update(variables)

    def start_state_execution(self, state_name: str, attempt: int = 1) -> StateExecution:
        """
        Record the start of a state execution.

        Args:
            state_name: Name of the state
            attempt: Attempt number

        Returns:
            StateExecution tracking object
        """
        execution = StateExecution(
            state_name=state_name, status=StateStatus.RUNNING, attempt=attempt
        )
        self.execution_history.append(execution)
        self.current_state = state_name
        return execution

    def complete_state_execution(
        self, result: Any = None, error: Optional[str] = None
    ) -> None:
        """
        Complete the current state execution.

        Args:
            result: Execution result
            error: Error message if failed
        """
        if self.execution_history:
            self.execution_history[-1].complete(result=result, error=error)

    def get_state_executions(self, state_name: str) -> List[StateExecution]:
        """
        Get all executions of a specific state.

        Args:
            state_name: Name of the state

        Returns:
            List of executions for that state
        """
        return [ex for ex in self.execution_history if ex.state_name == state_name]

    def get_last_execution(self, state_name: str) -> Optional[StateExecution]:
        """
        Get the most recent execution of a state.

        Args:
            state_name: Name of the state

        Returns:
            Most recent execution or None
        """
        executions = self.get_state_executions(state_name)
        return executions[-1] if executions else None

    def has_visited_state(self, state_name: str) -> bool:
        """Check if a state has been visited."""
        return any(ex.state_name == state_name for ex in self.execution_history)

    def get_execution_path(self) -> List[str]:
        """
        Get the path of executed states.

        Returns:
            List of state names in execution order
        """
        return [ex.state_name for ex in self.execution_history]

    def get_total_duration_ms(self) -> float:
        """
        Get total workflow duration in milliseconds.

        Returns:
            Duration in milliseconds
        """
        if not self.started_at:
            return 0.0

        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds() * 1000

    def get_state_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get execution statistics per state.

        Returns:
            Dictionary mapping state names to their statistics
        """
        stats: Dict[str, Dict[str, Any]] = {}

        for execution in self.execution_history:
            state_name = execution.state_name
            if state_name not in stats:
                stats[state_name] = {
                    "total_executions": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration_ms": 0.0,
                    "avg_duration_ms": 0.0,
                }

            stats[state_name]["total_executions"] += 1

            if execution.status == StateStatus.COMPLETED:
                stats[state_name]["successful"] += 1
            elif execution.status == StateStatus.FAILED:
                stats[state_name]["failed"] += 1

            if execution.duration_ms:
                stats[state_name]["total_duration_ms"] += execution.duration_ms

        # Calculate averages
        for state_stats in stats.values():
            if state_stats["total_executions"] > 0:
                state_stats["avg_duration_ms"] = (
                    state_stats["total_duration_ms"] / state_stats["total_executions"]
                )

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary for condition evaluation.

        Returns:
            Dictionary representation
        """
        return {
            **self.variables,
            "_context": {
                "workflow_id": self.workflow_id,
                "current_state": self.current_state,
                "execution_path": self.get_execution_path(),
                "total_duration_ms": self.get_total_duration_ms(),
            },
        }

    def complete(self, error: Optional[str] = None) -> None:
        """
        Mark the workflow execution as completed.

        Args:
            error: Error message if workflow failed
        """
        self.completed_at = datetime.now()
        self.error = error

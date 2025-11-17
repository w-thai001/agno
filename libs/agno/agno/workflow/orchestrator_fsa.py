"""
Orchestrator FSA - Master coordinator for FSA cascade execution.

This module provides a sophisticated orchestration layer that coordinates
multiple FSA executions with dependency management, parallel processing,
error recovery, and comprehensive monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
import logging

from pydantic import BaseModel, Field

from agno.agent import Agent
from agno.run.response import RunEvent, RunResponse
from agno.workflow.fsa import (
    FSA,
    FSAConfig,
    FSADependency,
    FSAExecutionContext,
    FSAState,
    StateTransition,
    TransitionAction,
    TransitionCondition
)
from agno.workflow.workflow import Workflow


logger = logging.getLogger(__name__)


class OrchestratorState(str, Enum):
    """States for the orchestrator FSA lifecycle."""

    IDLE = "idle"
    VALIDATING = "validating"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    RECOVERING = "recovering"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class ExecutionStrategy(str, Enum):
    """Execution strategies for FSA coordination."""

    SEQUENTIAL = "sequential"  # Execute FSAs one after another
    PARALLEL = "parallel"  # Execute independent FSAs concurrently
    ADAPTIVE = "adaptive"  # Dynamically choose based on dependencies


class RecoveryStrategy(str, Enum):
    """Error recovery strategies."""

    FAIL_FAST = "fail_fast"  # Stop on first error
    CONTINUE = "continue"  # Skip failed FSA, continue with others
    RETRY = "retry"  # Retry failed FSA up to max attempts
    ROLLBACK = "rollback"  # Revert to last known good state


@dataclass
class FSATask:
    """
    Represents a task/FSA to be executed by the orchestrator.

    Encapsulates FSA configuration, execution state, dependencies,
    and results for coordination.
    """

    name: str
    fsa: Optional[FSA] = None
    agent: Optional[Agent] = None
    dependencies: List[str] = field(default_factory=list)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    can_run_parallel: bool = False

    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep in completed_tasks for dep in self.dependencies)

    def mark_running(self):
        """Mark task as running."""
        self.status = "running"
        self.start_time = datetime.now()

    def mark_completed(self, result: Any):
        """Mark task as successfully completed."""
        self.status = "completed"
        self.result = result
        self.end_time = datetime.now()

    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = "failed"
        self.error = error
        self.end_time = datetime.now()

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries

    def reset_for_retry(self):
        """Reset task state for retry."""
        self.status = "pending"
        self.error = None
        self.start_time = None
        self.end_time = None
        self.retry_count += 1


class OrchestratorConfig(BaseModel):
    """Configuration for orchestrator FSA behavior."""

    execution_strategy: ExecutionStrategy = Field(
        ExecutionStrategy.ADAPTIVE,
        description="Strategy for executing FSA cascade"
    )
    recovery_strategy: RecoveryStrategy = Field(
        RecoveryStrategy.RETRY,
        description="Strategy for handling errors"
    )
    max_parallel_tasks: int = Field(
        4,
        description="Maximum number of tasks to run in parallel"
    )
    enable_monitoring: bool = Field(
        True,
        description="Enable progress monitoring and callbacks"
    )
    enable_checkpointing: bool = Field(
        True,
        description="Save state at each major transition"
    )
    global_timeout_seconds: Optional[int] = Field(
        None,
        description="Maximum time for entire orchestration"
    )
    task_timeout_seconds: int = Field(
        300,
        description="Default timeout for individual tasks"
    )
    enable_data_validation: bool = Field(
        True,
        description="Validate data flow between FSAs"
    )

    class Config:
        use_enum_values = True


@dataclass
class OrchestrationResult:
    """Result of orchestrator execution."""

    success: bool
    completed_tasks: List[str]
    failed_tasks: List[str]
    outputs: Dict[str, Any]
    execution_time_seconds: float
    total_transitions: int
    error_summary: Optional[str] = None
    task_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class OrchestratorFSA(Workflow, FSA):
    """
    Master orchestrator FSA for coordinating FSA cascade execution.

    This orchestrator manages the complete lifecycle of multi-FSA workflows,
    including dependency resolution, parallel execution, error recovery,
    data flow orchestration, and comprehensive monitoring.

    Features:
    - Dependency-based task scheduling
    - Parallel execution of independent tasks
    - Multiple error recovery strategies
    - Progress monitoring with callbacks
    - State checkpointing for resume capability
    - Data validation and transformation
    - Comprehensive execution reporting
    """

    description: str = "FSA Orchestrator for coordinating complex multi-agent workflows"

    def __init__(
        self,
        tasks: Optional[List[FSATask]] = None,
        config: Optional[OrchestratorConfig] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs
    ):
        """
        Initialize Orchestrator FSA.

        Args:
            tasks: List of FSA tasks to coordinate
            config: Orchestrator configuration
            progress_callback: Optional callback for progress updates
            **kwargs: Additional arguments passed to Workflow
        """
        # Initialize Workflow
        Workflow.__init__(self, **kwargs)

        # Initialize orchestrator-specific attributes
        self.tasks: List[FSATask] = tasks or []
        self.orchestrator_config = config or OrchestratorConfig()
        self.progress_callback = progress_callback

        # Build FSA configuration
        fsa_config = self._build_fsa_config()

        # Initialize FSA base class
        FSA.__init__(self, config=fsa_config, session_state=self.session_state)

        # Execution tracking
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.task_outputs: Dict[str, Any] = {}
        self.execution_start_time: Optional[datetime] = None

        logger.info(f"OrchestratorFSA initialized with {len(self.tasks)} tasks")

    def _build_fsa_config(self) -> FSAConfig:
        """Build FSA configuration with state transitions."""

        # Define state transitions
        transitions = [
            # IDLE -> VALIDATING
            StateTransition(
                from_state=OrchestratorState.IDLE,
                to_state=OrchestratorState.VALIDATING,
                description="Start orchestration by validating tasks",
                priority=100
            ),
            # VALIDATING -> PLANNING (success)
            StateTransition(
                from_state=OrchestratorState.VALIDATING,
                to_state=OrchestratorState.PLANNING,
                conditions=[
                    TransitionCondition(
                        name="validation_successful",
                        check=lambda ctx: ctx.get("validation_passed", False)
                    )
                ],
                description="Proceed to planning after successful validation",
                priority=100
            ),
            # VALIDATING -> ERROR (failure)
            StateTransition(
                from_state=OrchestratorState.VALIDATING,
                to_state=OrchestratorState.ERROR,
                conditions=[
                    TransitionCondition(
                        name="validation_failed",
                        check=lambda ctx: not ctx.get("validation_passed", False)
                    )
                ],
                description="Enter error state on validation failure",
                priority=90
            ),
            # PLANNING -> EXECUTING
            StateTransition(
                from_state=OrchestratorState.PLANNING,
                to_state=OrchestratorState.EXECUTING,
                conditions=[
                    TransitionCondition(
                        name="plan_ready",
                        check=lambda ctx: ctx.get("execution_plan") is not None
                    )
                ],
                description="Start executing tasks",
                priority=100
            ),
            # EXECUTING -> MONITORING
            StateTransition(
                from_state=OrchestratorState.EXECUTING,
                to_state=OrchestratorState.MONITORING,
                conditions=[
                    TransitionCondition(
                        name="tasks_running",
                        check=lambda ctx: len(ctx.get("running_tasks", [])) > 0
                    )
                ],
                description="Monitor running tasks",
                priority=100
            ),
            # MONITORING -> EXECUTING (more tasks to run)
            StateTransition(
                from_state=OrchestratorState.MONITORING,
                to_state=OrchestratorState.EXECUTING,
                conditions=[
                    TransitionCondition(
                        name="has_pending_tasks",
                        check=lambda ctx: len(ctx.get("pending_tasks", [])) > 0
                    )
                ],
                description="Return to executing for next batch of tasks",
                priority=100
            ),
            # MONITORING -> RECOVERING (errors detected)
            StateTransition(
                from_state=OrchestratorState.MONITORING,
                to_state=OrchestratorState.RECOVERING,
                conditions=[
                    TransitionCondition(
                        name="has_failures",
                        check=lambda ctx: len(ctx.get("failed_tasks", [])) > 0
                    )
                ],
                description="Handle task failures",
                priority=90
            ),
            # MONITORING -> FINALIZING (all done)
            StateTransition(
                from_state=OrchestratorState.MONITORING,
                to_state=OrchestratorState.FINALIZING,
                conditions=[
                    TransitionCondition(
                        name="all_tasks_done",
                        check=lambda ctx: (
                            len(ctx.get("pending_tasks", [])) == 0 and
                            len(ctx.get("running_tasks", [])) == 0
                        )
                    )
                ],
                description="Finalize orchestration",
                priority=80
            ),
            # RECOVERING -> EXECUTING (retry)
            StateTransition(
                from_state=OrchestratorState.RECOVERING,
                to_state=OrchestratorState.EXECUTING,
                conditions=[
                    TransitionCondition(
                        name="can_recover",
                        check=lambda ctx: ctx.get("recovery_action") == "retry"
                    )
                ],
                description="Retry failed tasks",
                priority=100
            ),
            # RECOVERING -> ERROR (fail fast)
            StateTransition(
                from_state=OrchestratorState.RECOVERING,
                to_state=OrchestratorState.ERROR,
                conditions=[
                    TransitionCondition(
                        name="should_fail",
                        check=lambda ctx: ctx.get("recovery_action") == "fail"
                    )
                ],
                description="Fail orchestration",
                priority=90
            ),
            # RECOVERING -> FINALIZING (continue)
            StateTransition(
                from_state=OrchestratorState.RECOVERING,
                to_state=OrchestratorState.FINALIZING,
                conditions=[
                    TransitionCondition(
                        name="should_continue",
                        check=lambda ctx: ctx.get("recovery_action") == "continue"
                    )
                ],
                description="Continue with successful tasks",
                priority=80
            ),
            # FINALIZING -> COMPLETED
            StateTransition(
                from_state=OrchestratorState.FINALIZING,
                to_state=OrchestratorState.COMPLETED,
                description="Complete orchestration",
                priority=100
            )
        ]

        return FSAConfig(
            name="orchestrator",
            initial_state=OrchestratorState.IDLE,
            final_states=[OrchestratorState.COMPLETED, OrchestratorState.ERROR],
            error_states=[OrchestratorState.ERROR],
            transitions=transitions,
            max_transitions=1000,
            enable_history=True,
            enable_monitoring=self.orchestrator_config.enable_monitoring
        )

    def add_task(self, task: FSATask):
        """Add a task to the orchestration."""
        self.tasks.append(task)
        logger.info(f"Added task '{task.name}' to orchestration")

    def validate_tasks(self) -> bool:
        """
        Validate task configuration and dependencies.

        Returns:
            True if validation passes, False otherwise
        """
        task_names = {task.name for task in self.tasks}

        # Check for duplicate task names
        if len(task_names) != len(self.tasks):
            logger.error("Duplicate task names detected")
            return False

        # Validate dependencies
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_names:
                    logger.error(f"Task '{task.name}' has invalid dependency '{dep}'")
                    return False

        # Check for circular dependencies
        if self._has_circular_dependencies():
            logger.error("Circular dependencies detected")
            return False

        logger.info("Task validation passed")
        return True

    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies using DFS."""
        graph = {task.name: task.dependencies for task in self.tasks}

        def visit(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if visit(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited: Set[str] = set()
        for task in self.tasks:
            if task.name not in visited:
                if visit(task.name, visited, set()):
                    return True

        return False

    def create_execution_plan(self) -> List[List[str]]:
        """
        Create execution plan based on dependencies.

        Returns:
            List of task batches (each batch can run in parallel)
        """
        plan: List[List[str]] = []
        remaining_tasks = {task.name: task for task in self.tasks}
        completed: Set[str] = set()

        while remaining_tasks:
            # Find tasks ready to execute
            ready_tasks = [
                name for name, task in remaining_tasks.items()
                if task.is_ready(completed)
            ]

            if not ready_tasks:
                logger.error("Execution plan stuck - possible circular dependency")
                break

            # Determine which tasks can run in parallel
            if self.orchestrator_config.execution_strategy == ExecutionStrategy.PARALLEL:
                batch = ready_tasks[:self.orchestrator_config.max_parallel_tasks]
            elif self.orchestrator_config.execution_strategy == ExecutionStrategy.SEQUENTIAL:
                batch = [ready_tasks[0]]
            else:  # ADAPTIVE
                # Group tasks that can run in parallel
                parallel_batch = [
                    name for name in ready_tasks
                    if remaining_tasks[name].can_run_parallel
                ][:self.orchestrator_config.max_parallel_tasks]
                batch = parallel_batch if parallel_batch else [ready_tasks[0]]

            plan.append(batch)

            # Mark batch as completed for dependency resolution
            for task_name in batch:
                completed.add(task_name)
                del remaining_tasks[task_name]

        logger.info(f"Created execution plan with {len(plan)} batches")
        return plan

    def execute_task(self, task: FSATask) -> Any:
        """
        Execute a single task (FSA or Agent).

        Args:
            task: Task to execute

        Returns:
            Task execution result
        """
        task.mark_running()
        logger.info(f"Executing task '{task.name}'")

        try:
            # Prepare input data from dependencies
            input_data = self._prepare_task_input(task)

            # Execute FSA or Agent
            if task.fsa:
                result = task.fsa.run(**input_data)
            elif task.agent:
                result = task.agent.run(**input_data)
            else:
                raise ValueError(f"Task '{task.name}' has no FSA or Agent configured")

            # Store output
            output_data = self._extract_task_output(task, result)
            task.mark_completed(result)
            self.task_outputs[task.name] = output_data

            logger.info(f"Task '{task.name}' completed successfully")
            return result

        except Exception as e:
            error_msg = f"Task '{task.name}' failed: {str(e)}"
            logger.error(error_msg)
            task.mark_failed(error_msg)
            raise

    def _prepare_task_input(self, task: FSATask) -> Dict[str, Any]:
        """Prepare input data for task from dependency outputs."""
        input_data = {}

        for dep_name in task.dependencies:
            dep_output = self.task_outputs.get(dep_name, {})

            # Apply input mapping
            for source_key, target_key in task.input_mapping.items():
                if source_key in dep_output:
                    input_data[target_key] = dep_output[source_key]

        return input_data

    def _extract_task_output(self, task: FSATask, result: Any) -> Dict[str, Any]:
        """Extract and map output data from task result."""
        output_data = {}

        # Handle different result types
        if isinstance(result, dict):
            output_data = result
        elif isinstance(result, RunResponse):
            output_data = {"content": result.content, "run_response": result}
        else:
            output_data = {"result": result}

        # Apply output mapping
        if task.output_mapping:
            mapped_output = {}
            for source_key, target_key in task.output_mapping.items():
                if source_key in output_data:
                    mapped_output[target_key] = output_data[source_key]
            return mapped_output

        return output_data

    def execute_batch_parallel(self, task_names: List[str]) -> Dict[str, Any]:
        """
        Execute a batch of tasks in parallel.

        Args:
            task_names: Names of tasks to execute

        Returns:
            Dictionary mapping task names to results
        """
        results = {}
        task_map = {task.name: task for task in self.tasks}

        with ThreadPoolExecutor(max_workers=len(task_names)) as executor:
            # Submit all tasks
            futures: Dict[Future, str] = {}
            for task_name in task_names:
                task = task_map[task_name]
                future = executor.submit(self.execute_task, task)
                futures[future] = task_name

            # Collect results
            for future in as_completed(futures):
                task_name = futures[future]
                try:
                    result = future.result()
                    results[task_name] = result
                    self.completed_tasks.add(task_name)
                except Exception as e:
                    logger.error(f"Parallel task '{task_name}' failed: {e}")
                    self.failed_tasks.add(task_name)
                    results[task_name] = None

        return results

    def execute_batch_sequential(self, task_names: List[str]) -> Dict[str, Any]:
        """
        Execute a batch of tasks sequentially.

        Args:
            task_names: Names of tasks to execute

        Returns:
            Dictionary mapping task names to results
        """
        results = {}
        task_map = {task.name: task for task in self.tasks}

        for task_name in task_names:
            task = task_map[task_name]
            try:
                result = self.execute_task(task)
                results[task_name] = result
                self.completed_tasks.add(task_name)
            except Exception as e:
                logger.error(f"Sequential task '{task_name}' failed: {e}")
                self.failed_tasks.add(task_name)
                results[task_name] = None

                # Stop on first error if fail-fast
                if self.orchestrator_config.recovery_strategy == RecoveryStrategy.FAIL_FAST:
                    break

        return results

    def handle_recovery(self) -> str:
        """
        Handle recovery from failed tasks.

        Returns:
            Recovery action: "retry", "continue", or "fail"
        """
        strategy = self.orchestrator_config.recovery_strategy

        if strategy == RecoveryStrategy.FAIL_FAST:
            return "fail"

        elif strategy == RecoveryStrategy.RETRY:
            # Check if any failed tasks can be retried
            task_map = {task.name: task for task in self.tasks}
            can_retry_any = any(
                task_map[name].can_retry()
                for name in self.failed_tasks
            )

            if can_retry_any:
                # Reset retryable tasks
                for name in list(self.failed_tasks):
                    task = task_map[name]
                    if task.can_retry():
                        task.reset_for_retry()
                        self.failed_tasks.remove(name)
                        logger.info(f"Task '{name}' queued for retry")
                return "retry"
            else:
                return "continue"

        elif strategy == RecoveryStrategy.CONTINUE:
            return "continue"

        elif strategy == RecoveryStrategy.ROLLBACK:
            # TODO: Implement rollback logic
            logger.warning("Rollback not yet implemented, continuing")
            return "continue"

        return "fail"

    def report_progress(self):
        """Report current progress to callback if configured."""
        if not self.progress_callback or not self.orchestrator_config.enable_monitoring:
            return

        progress = {
            "current_state": self.context.current_state.value,
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "pending_tasks": len(self.tasks) - len(self.completed_tasks) - len(self.failed_tasks),
            "completion_percentage": (len(self.completed_tasks) / len(self.tasks) * 100) if self.tasks else 0
        }

        try:
            self.progress_callback(progress)
        except Exception as e:
            logger.error(f"Progress callback failed: {e}")

    def run(self, **kwargs) -> Iterator[RunResponse]:
        """
        Execute the orchestrated FSA cascade.

        Args:
            **kwargs: Additional parameters (not used, for Workflow compatibility)

        Yields:
            RunResponse objects for progress updates
        """
        self.execution_start_time = datetime.now()

        yield RunResponse(
            event=RunEvent.workflow_started.value,
            content="Starting FSA orchestration",
            workflow_id=self.workflow_id,
            session_id=self.session_id
        )

        # Main orchestration loop
        while not self.is_complete() and not self.has_exceeded_max_transitions():
            current_state = self.context.current_state

            # Handle current state
            if current_state == OrchestratorState.IDLE:
                # Transition to validating
                self.context.data["validation_passed"] = False
                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.VALIDATING:
                # Validate tasks
                validation_passed = self.validate_tasks()
                self.context.data["validation_passed"] = validation_passed

                yield RunResponse(
                    event="validation_completed",
                    content=f"Validation {'passed' if validation_passed else 'failed'}",
                    workflow_id=self.workflow_id
                )

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.PLANNING:
                # Create execution plan
                plan = self.create_execution_plan()
                self.context.data["execution_plan"] = plan
                self.context.data["current_batch"] = 0

                yield RunResponse(
                    event="planning_completed",
                    content=f"Created execution plan with {len(plan)} batches",
                    workflow_id=self.workflow_id
                )

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.EXECUTING:
                # Execute next batch of tasks
                plan = self.context.data.get("execution_plan", [])
                batch_idx = self.context.data.get("current_batch", 0)

                if batch_idx < len(plan):
                    batch = plan[batch_idx]
                    self.context.data["running_tasks"] = batch

                    yield RunResponse(
                        event="batch_started",
                        content=f"Executing batch {batch_idx + 1}/{len(plan)}: {batch}",
                        workflow_id=self.workflow_id
                    )

                    # Execute batch
                    if len(batch) > 1 and self.orchestrator_config.execution_strategy != ExecutionStrategy.SEQUENTIAL:
                        results = self.execute_batch_parallel(batch)
                    else:
                        results = self.execute_batch_sequential(batch)

                    self.context.data["current_batch"] = batch_idx + 1

                    yield RunResponse(
                        event="batch_completed",
                        content=f"Batch {batch_idx + 1} completed",
                        workflow_id=self.workflow_id
                    )

                # Get pending tasks
                self.context.data["pending_tasks"] = [
                    task.name for task in self.tasks
                    if task.status == "pending"
                ]

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.MONITORING:
                # Update monitoring data
                self.context.data["running_tasks"] = [
                    task.name for task in self.tasks
                    if task.status == "running"
                ]
                self.context.data["failed_tasks"] = list(self.failed_tasks)

                self.report_progress()

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.RECOVERING:
                # Handle recovery
                recovery_action = self.handle_recovery()
                self.context.data["recovery_action"] = recovery_action

                yield RunResponse(
                    event="recovery_action",
                    content=f"Recovery action: {recovery_action}",
                    workflow_id=self.workflow_id
                )

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.FINALIZING:
                # Finalize orchestration
                execution_time = (datetime.now() - self.execution_start_time).total_seconds()

                result = OrchestrationResult(
                    success=len(self.failed_tasks) == 0,
                    completed_tasks=list(self.completed_tasks),
                    failed_tasks=list(self.failed_tasks),
                    outputs=self.task_outputs,
                    execution_time_seconds=execution_time,
                    total_transitions=self.context.transition_count,
                    task_details={
                        task.name: {
                            "status": task.status,
                            "start_time": task.start_time.isoformat() if task.start_time else None,
                            "end_time": task.end_time.isoformat() if task.end_time else None,
                            "retry_count": task.retry_count,
                            "error": task.error
                        }
                        for task in self.tasks
                    }
                )

                self.session_state["orchestration_result"] = result
                self.context.data["final_result"] = result

                yield RunResponse(
                    event="orchestration_finalized",
                    content=result,
                    workflow_id=self.workflow_id
                )

                transition = self.find_transition()
                if transition:
                    self.execute_transition(transition)

            elif current_state == OrchestratorState.ERROR:
                # Handle error state
                error_summary = self._create_error_summary()

                yield RunResponse(
                    event=RunEvent.run_error.value,
                    content=error_summary,
                    workflow_id=self.workflow_id
                )
                break

            else:
                # Unknown state
                logger.error(f"Unknown state: {current_state}")
                break

        # Final response
        final_state = self.context.current_state
        final_result = self.context.data.get("final_result")

        yield RunResponse(
            event=RunEvent.workflow_completed.value,
            content=f"Orchestration completed in state: {final_state.value}",
            workflow_id=self.workflow_id,
            session_id=self.session_id,
            extra_data={"result": final_result} if final_result else None
        )

    def _create_error_summary(self) -> str:
        """Create a summary of errors that occurred."""
        error_lines = ["Orchestration failed with the following errors:"]

        for task in self.tasks:
            if task.error:
                error_lines.append(f"- Task '{task.name}': {task.error}")

        return "\n".join(error_lines)

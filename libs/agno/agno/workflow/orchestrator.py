"""
Workflow Orchestrator FSA - Complete orchestration engine with DAG execution,
parallel task support, dependency resolution, error recovery, state persistence,
and execution monitoring.
"""

from __future__ import annotations

import asyncio
import json
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from agno.utils.log import logger


# ==================== FSA States ====================


class TaskState(str, Enum):
    """Finite State Automaton states for task execution"""

    PENDING = "pending"
    WAITING = "waiting"  # Waiting for dependencies
    READY = "ready"  # Dependencies satisfied, ready to run
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class WorkflowState(str, Enum):
    """Workflow execution states"""

    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== Task Definition ====================


@dataclass
class TaskResult:
    """Result of a task execution"""

    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "retry_count": self.retry_count,
        }


@dataclass
class Task:
    """
    Represents a single task in the workflow DAG.

    Attributes:
        task_id: Unique identifier for the task
        name: Human-readable task name
        func: Callable function to execute
        dependencies: List of task_ids this task depends on
        retry_count: Number of times to retry on failure
        retry_delay: Delay in seconds between retries
        timeout: Maximum execution time in seconds
        on_failure: Callback function when task fails
        on_success: Callback function when task succeeds
        metadata: Additional task metadata
    """

    task_id: str
    name: str
    func: Callable
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    on_failure: Optional[Callable] = None
    on_success: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Runtime state
    state: TaskState = TaskState.PENDING
    result: Optional[TaskResult] = None
    attempts: int = 0

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid4())

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are satisfied"""
        return all(dep in completed_tasks for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task to dictionary"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "dependencies": self.dependencies,
            "state": self.state.value,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "metadata": self.metadata,
            "attempts": self.attempts,
            "result": self.result.to_dict() if self.result else None,
        }


# ==================== DAG Management ====================


class DAG:
    """
    Directed Acyclic Graph for managing task dependencies and execution order.

    Provides topological sorting, cycle detection, and dependency resolution.
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.adjacency_list: Dict[str, List[str]] = {}
        self.reverse_adjacency: Dict[str, List[str]] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to the DAG"""
        if task.task_id in self.tasks:
            raise ValueError(f"Task {task.task_id} already exists in DAG")

        self.tasks[task.task_id] = task
        self.adjacency_list[task.task_id] = task.dependencies.copy()

        # Build reverse adjacency for finding dependents
        for dep in task.dependencies:
            if dep not in self.reverse_adjacency:
                self.reverse_adjacency[dep] = []
            self.reverse_adjacency[dep].append(task.task_id)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def has_cycle(self) -> bool:
        """Check if DAG contains cycles using DFS"""
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for neighbor in self.adjacency_list.get(task_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        """
        Return tasks in topological order using Kahn's algorithm.
        Raises ValueError if cycle is detected.
        """
        if self.has_cycle():
            raise ValueError("DAG contains cycles - cannot perform topological sort")

        in_degree = {task_id: len(deps) for task_id, deps in self.adjacency_list.items()}
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            # Reduce in-degree for dependent tasks
            for dependent in self.reverse_adjacency.get(task_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.tasks):
            raise ValueError("DAG contains cycles or disconnected components")

        return result

    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[Task]:
        """Get all tasks that are ready to execute"""
        ready_tasks = []
        for task_id, task in self.tasks.items():
            if (
                task.state in [TaskState.PENDING, TaskState.WAITING]
                and task.can_execute(completed_tasks)
            ):
                ready_tasks.append(task)
        return ready_tasks

    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get all tasks that depend on the given task"""
        return self.reverse_adjacency.get(task_id, [])

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the DAG structure.
        Returns (is_valid, error_message)
        """
        # Check for cycles
        if self.has_cycle():
            return False, "DAG contains cycles"

        # Check that all dependencies exist
        for task_id, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    return False, f"Task {task_id} depends on non-existent task {dep}"

        return True, None


# ==================== State Persistence ====================


class StateManager:
    """
    Manages workflow state persistence to disk.
    Enables recovery from failures and execution monitoring.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or Path(".workflow_state")
        self.state_dir.mkdir(exist_ok=True)

    def save_state(self, workflow_id: str, state_data: Dict[str, Any]) -> None:
        """Save workflow state to disk"""
        state_file = self.state_dir / f"{workflow_id}.json"
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2, default=str)
        logger.debug(f"Saved state for workflow {workflow_id}")

    def load_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state from disk"""
        state_file = self.state_dir / f"{workflow_id}.json"
        if not state_file.exists():
            return None

        with open(state_file, "r") as f:
            state_data = json.load(f)
        logger.debug(f"Loaded state for workflow {workflow_id}")
        return state_data

    def delete_state(self, workflow_id: str) -> None:
        """Delete workflow state from disk"""
        state_file = self.state_dir / f"{workflow_id}.json"
        if state_file.exists():
            state_file.unlink()
            logger.debug(f"Deleted state for workflow {workflow_id}")

    def list_workflows(self) -> List[str]:
        """List all workflow IDs with saved state"""
        return [f.stem for f in self.state_dir.glob("*.json")]


# ==================== Execution Monitoring ====================


@dataclass
class ExecutionMetrics:
    """Metrics for workflow execution monitoring"""

    workflow_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    running_tasks: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

    def update_from_dag(self, dag: DAG) -> None:
        """Update metrics from DAG state"""
        state_counts = {state: 0 for state in TaskState}
        for task in dag.tasks.values():
            state_counts[task.state] += 1

        self.total_tasks = len(dag.tasks)
        self.completed_tasks = state_counts[TaskState.COMPLETED]
        self.failed_tasks = state_counts[TaskState.FAILED]
        self.skipped_tasks = state_counts[TaskState.SKIPPED]
        self.running_tasks = state_counts[TaskState.RUNNING]

    def get_progress_percentage(self) -> float:
        """Calculate execution progress percentage"""
        if self.total_tasks == 0:
            return 0.0
        completed = self.completed_tasks + self.failed_tasks + self.skipped_tasks
        return (completed / self.total_tasks) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "running_tasks": self.running_tasks,
            "progress_percentage": self.get_progress_percentage(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
        }


# ==================== Workflow Orchestrator ====================


class WorkflowOrchestrator:
    """
    Complete workflow orchestration engine with FSA-based task execution.

    Features:
    - DAG-based task dependency management
    - Parallel task execution
    - Automatic dependency resolution
    - Error recovery with retry mechanisms
    - State persistence and recovery
    - Real-time execution monitoring
    - Conditional task execution
    - Task cancellation and workflow pause/resume

    Example:
        >>> orchestrator = WorkflowOrchestrator(workflow_id="data_pipeline")
        >>>
        >>> # Define tasks
        >>> task1 = Task(task_id="extract", name="Extract Data", func=extract_data)
        >>> task2 = Task(task_id="transform", name="Transform Data",
        ...              func=transform_data, dependencies=["extract"])
        >>> task3 = Task(task_id="load", name="Load Data",
        ...              func=load_data, dependencies=["transform"])
        >>>
        >>> # Add tasks to orchestrator
        >>> orchestrator.add_task(task1)
        >>> orchestrator.add_task(task2)
        >>> orchestrator.add_task(task3)
        >>>
        >>> # Execute workflow
        >>> results = orchestrator.execute()
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        max_parallel_tasks: int = 4,
        state_dir: Optional[Path] = None,
        auto_persist: bool = True,
    ):
        """
        Initialize the Workflow Orchestrator.

        Args:
            workflow_id: Unique identifier for the workflow
            max_parallel_tasks: Maximum number of tasks to run in parallel
            state_dir: Directory for state persistence
            auto_persist: Automatically persist state after each task
        """
        self.workflow_id = workflow_id or str(uuid4())
        self.max_parallel_tasks = max_parallel_tasks
        self.auto_persist = auto_persist

        self.dag = DAG()
        self.state_manager = StateManager(state_dir)
        self.metrics = ExecutionMetrics(workflow_id=self.workflow_id)

        self.workflow_state = WorkflowState.INITIALIZED
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.task_results: Dict[str, TaskResult] = {}

        self._execution_lock = asyncio.Lock()
        self._should_stop = False

    # ==================== Task Management ====================

    def add_task(self, task: Task) -> None:
        """Add a task to the workflow"""
        self.dag.add_task(task)
        logger.debug(f"Added task {task.task_id} ({task.name})")

    def add_tasks(self, tasks: List[Task]) -> None:
        """Add multiple tasks to the workflow"""
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.dag.get_task(task_id)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the workflow"""
        if task_id in self.dag.tasks:
            # Check if any tasks depend on this one
            dependents = self.dag.get_dependent_tasks(task_id)
            if dependents:
                raise ValueError(
                    f"Cannot remove task {task_id}: tasks {dependents} depend on it"
                )
            del self.dag.tasks[task_id]
            logger.debug(f"Removed task {task_id}")

    # ==================== Workflow Execution ====================

    def execute(
        self, context: Optional[Dict[str, Any]] = None, resume: bool = False
    ) -> Dict[str, TaskResult]:
        """
        Execute the workflow synchronously.

        Args:
            context: Context data passed to all tasks
            resume: Resume from previous state if available

        Returns:
            Dictionary mapping task_id to TaskResult
        """
        return asyncio.run(self.execute_async(context=context, resume=resume))

    async def execute_async(
        self, context: Optional[Dict[str, Any]] = None, resume: bool = False
    ) -> Dict[str, TaskResult]:
        """
        Execute the workflow asynchronously with parallel task support.

        Args:
            context: Context data passed to all tasks
            resume: Resume from previous state if available

        Returns:
            Dictionary mapping task_id to TaskResult
        """
        async with self._execution_lock:
            # Resume from previous state if requested
            if resume:
                self._resume_from_state()

            # Validate DAG structure
            is_valid, error = self.dag.validate()
            if not is_valid:
                raise ValueError(f"Invalid workflow DAG: {error}")

            # Initialize execution
            self.workflow_state = WorkflowState.RUNNING
            self.metrics.start_time = datetime.now()
            self.metrics.update_from_dag(self.dag)
            self._should_stop = False

            context = context or {}
            logger.info(f"Starting workflow execution: {self.workflow_id}")
            logger.info(f"Total tasks: {len(self.dag.tasks)}")

            try:
                # Execute tasks in parallel where possible
                await self._execute_dag(context)

                # Determine final workflow state
                if self.failed_tasks:
                    self.workflow_state = WorkflowState.FAILED
                elif self._should_stop:
                    self.workflow_state = WorkflowState.CANCELLED
                else:
                    self.workflow_state = WorkflowState.COMPLETED

            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                self.workflow_state = WorkflowState.FAILED
                raise
            finally:
                # Finalize metrics
                self.metrics.end_time = datetime.now()
                if self.metrics.start_time:
                    self.metrics.duration = (
                        self.metrics.end_time - self.metrics.start_time
                    ).total_seconds()
                self.metrics.update_from_dag(self.dag)

                # Persist final state
                if self.auto_persist:
                    self.persist_state()

                logger.info(f"Workflow execution completed: {self.workflow_state.value}")
                logger.info(
                    f"Completed: {self.metrics.completed_tasks}, "
                    f"Failed: {self.metrics.failed_tasks}, "
                    f"Skipped: {self.metrics.skipped_tasks}"
                )

            return self.task_results

    async def _execute_dag(self, context: Dict[str, Any]) -> None:
        """Execute DAG with parallel task execution"""
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)
        pending_tasks: Set[asyncio.Task] = set()

        while not self._should_stop:
            # Get ready tasks
            ready_tasks = self.dag.get_ready_tasks(self.completed_tasks)

            # Update task states to READY
            for task in ready_tasks:
                if task.state in [TaskState.PENDING, TaskState.WAITING]:
                    task.state = TaskState.READY

            # Start new tasks up to parallel limit
            for task in ready_tasks:
                if len(pending_tasks) >= self.max_parallel_tasks:
                    break

                if task.state == TaskState.READY:
                    task.state = TaskState.RUNNING
                    coroutine = self._execute_task_with_semaphore(
                        task, context, semaphore
                    )
                    pending_tasks.add(asyncio.create_task(coroutine))

            # Wait for at least one task to complete
            if pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks, return_when=asyncio.FIRST_COMPLETED
                )

                # Process completed tasks
                for task_future in done:
                    await task_future  # Ensure exceptions are raised

                # Persist state after each batch
                if self.auto_persist:
                    self.persist_state()
            else:
                # No tasks running and no ready tasks - we're done
                break

        # Wait for any remaining tasks
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

    async def _execute_task_with_semaphore(
        self, task: Task, context: Dict[str, Any], semaphore: asyncio.Semaphore
    ) -> None:
        """Execute a single task with semaphore for concurrency control"""
        async with semaphore:
            await self._execute_task(task, context)

    async def _execute_task(self, task: Task, context: Dict[str, Any]) -> None:
        """
        Execute a single task with retry logic and error handling.

        Args:
            task: Task to execute
            context: Execution context
        """
        logger.info(f"Executing task: {task.name} ({task.task_id})")
        start_time = datetime.now()

        for attempt in range(task.retry_count + 1):
            task.attempts = attempt + 1

            try:
                # Execute with timeout if specified
                if task.timeout:
                    output = await asyncio.wait_for(
                        self._run_task_func(task, context), timeout=task.timeout
                    )
                else:
                    output = await self._run_task_func(task, context)

                # Task succeeded
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                task.result = TaskResult(
                    task_id=task.task_id,
                    success=True,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    retry_count=attempt,
                )
                task.state = TaskState.COMPLETED
                self.completed_tasks.add(task.task_id)
                self.task_results[task.task_id] = task.result

                logger.info(
                    f"Task completed: {task.name} ({task.task_id}) "
                    f"in {duration:.2f}s"
                )

                # Call success callback
                if task.on_success:
                    try:
                        await self._call_callback(task.on_success, task, output)
                    except Exception as e:
                        logger.warning(f"Success callback failed: {e}")

                return

            except asyncio.TimeoutError:
                error_msg = f"Task timed out after {task.timeout}s"
                logger.warning(f"{error_msg}: {task.name} ({task.task_id})")

            except Exception as e:
                error_msg = f"Task failed with error: {str(e)}"
                logger.warning(
                    f"{error_msg}: {task.name} ({task.task_id}) "
                    f"(attempt {attempt + 1}/{task.retry_count + 1})"
                )

            # Retry logic
            if attempt < task.retry_count:
                task.state = TaskState.RETRYING
                await asyncio.sleep(task.retry_delay)
                continue

        # All retries exhausted - task failed
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        task.result = TaskResult(
            task_id=task.task_id,
            success=False,
            error=error_msg,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            retry_count=task.retry_count,
        )
        task.state = TaskState.FAILED
        self.failed_tasks.add(task.task_id)
        self.task_results[task.task_id] = task.result

        logger.error(f"Task failed: {task.name} ({task.task_id})")

        # Call failure callback
        if task.on_failure:
            try:
                await self._call_callback(task.on_failure, task, error_msg)
            except Exception as e:
                logger.warning(f"Failure callback failed: {e}")

        # Mark dependent tasks as skipped
        self._skip_dependent_tasks(task.task_id)

    async def _run_task_func(self, task: Task, context: Dict[str, Any]) -> Any:
        """Run task function, handling both sync and async functions"""
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(context)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, task.func, context)

    async def _call_callback(
        self, callback: Callable, task: Task, result: Any
    ) -> None:
        """Call a callback function, handling both sync and async"""
        if asyncio.iscoroutinefunction(callback):
            await callback(task, result)
        else:
            callback(task, result)

    def _skip_dependent_tasks(self, failed_task_id: str) -> None:
        """Mark all tasks dependent on a failed task as skipped"""
        to_skip = set(self.dag.get_dependent_tasks(failed_task_id))
        visited = set()

        while to_skip:
            task_id = to_skip.pop()
            if task_id in visited:
                continue

            visited.add(task_id)
            task = self.dag.get_task(task_id)
            if task and task.state not in [TaskState.COMPLETED, TaskState.SKIPPED]:
                task.state = TaskState.SKIPPED
                logger.info(f"Skipping task {task.name} ({task_id}) due to failed dependency")

                # Add dependents of this task to skip list
                to_skip.update(self.dag.get_dependent_tasks(task_id))

    # ==================== State Persistence ====================

    def persist_state(self) -> None:
        """Persist current workflow state to disk"""
        state_data = {
            "workflow_id": self.workflow_id,
            "workflow_state": self.workflow_state.value,
            "completed_tasks": list(self.completed_tasks),
            "failed_tasks": list(self.failed_tasks),
            "tasks": {
                task_id: task.to_dict() for task_id, task in self.dag.tasks.items()
            },
            "task_results": {
                task_id: result.to_dict()
                for task_id, result in self.task_results.items()
            },
            "metrics": self.metrics.to_dict(),
        }
        self.state_manager.save_state(self.workflow_id, state_data)

    def _resume_from_state(self) -> None:
        """Resume workflow from persisted state"""
        state_data = self.state_manager.load_state(self.workflow_id)
        if not state_data:
            logger.info("No previous state found, starting fresh")
            return

        logger.info(f"Resuming workflow from saved state")
        self.completed_tasks = set(state_data.get("completed_tasks", []))
        self.failed_tasks = set(state_data.get("failed_tasks", []))

        # Restore task states (but not functions - those must be re-registered)
        tasks_data = state_data.get("tasks", {})
        for task_id, task_data in tasks_data.items():
            task = self.dag.get_task(task_id)
            if task:
                task.state = TaskState(task_data["state"])
                task.attempts = task_data.get("attempts", 0)

        logger.info(
            f"Resumed: {len(self.completed_tasks)} completed, "
            f"{len(self.failed_tasks)} failed"
        )

    # ==================== Monitoring & Control ====================

    def get_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics"""
        self.metrics.update_from_dag(self.dag)
        return self.metrics

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status"""
        self.metrics.update_from_dag(self.dag)
        return {
            "workflow_id": self.workflow_id,
            "state": self.workflow_state.value,
            "metrics": self.metrics.to_dict(),
            "task_states": {
                task_id: task.state.value for task_id, task in self.dag.tasks.items()
            },
        }

    def pause(self) -> None:
        """Pause workflow execution"""
        self._should_stop = True
        self.workflow_state = WorkflowState.PAUSED
        logger.info("Workflow paused")

    def cancel(self) -> None:
        """Cancel workflow execution"""
        self._should_stop = True
        self.workflow_state = WorkflowState.CANCELLED
        logger.info("Workflow cancelled")

    def reset(self) -> None:
        """Reset workflow to initial state"""
        for task in self.dag.tasks.values():
            task.state = TaskState.PENDING
            task.result = None
            task.attempts = 0

        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self.task_results.clear()
        self.workflow_state = WorkflowState.INITIALIZED
        self.metrics = ExecutionMetrics(workflow_id=self.workflow_id)
        logger.info("Workflow reset")

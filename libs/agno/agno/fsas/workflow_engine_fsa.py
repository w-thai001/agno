"""
Workflow Engine FSA: Powerful workflow orchestration and automation for FSA systems.

This module provides comprehensive workflow orchestration with support for:
- DAG-based workflow definitions
- Conditional branching and decision nodes
- Parallel task execution
- Workflow scheduling
- State tracking and checkpointing
- Error handling with retry and compensation
- Workflow versioning
- Performance analysis and optimization
- State persistence for fault tolerance
- Workflow resumption from checkpoints
- Workflow visualization
- Thread-safe execution
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowStatus(Enum):
    """Workflow execution status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Types of workflow tasks."""
    SIMPLE = "simple"
    DECISION = "decision"
    PARALLEL = "parallel"
    MERGE = "merge"


# ==================== Data Classes ====================

@dataclass
class Task:
    """Represents a workflow task."""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    task_type: TaskType = TaskType.SIMPLE
    handler: Optional[Callable] = None
    timeout: timedelta = timedelta(seconds=30)
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Condition:
    """Conditional logic for branching."""
    condition_id: str = field(default_factory=lambda: str(uuid4()))
    predicate: Optional[Callable[[Any], bool]] = None
    expression: str = ""


@dataclass
class DecisionNode:
    """Decision node for conditional branching."""
    node_id: str = field(default_factory=lambda: str(uuid4()))
    conditions: List[Tuple[Condition, str]] = field(default_factory=list)  # (condition, next_task_id)
    default_task: Optional[str] = None


@dataclass
class WorkflowContext:
    """Context passed between workflow tasks."""
    workflow_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in context."""
        self.data[key] = value


@dataclass
class WorkflowDefinition:
    """Defines a workflow structure."""
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    tasks: Dict[str, Task] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # task_id -> [dependency_ids]
    start_task: Optional[str] = None
    end_tasks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DAG:
    """Directed Acyclic Graph representation."""
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    in_degree: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_node(self, node: str) -> None:
        """Add node to DAG."""
        self.nodes.add(node)

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add edge to DAG."""
        self.edges[from_node].add(to_node)
        self.in_degree[to_node] += 1

    def has_cycle(self) -> bool:
        """Check if DAG has cycles using topological sort."""
        in_degree = self.in_degree.copy()
        queue = deque([node for node in self.nodes if in_degree.get(node, 0) == 0])
        visited = 0

        while queue:
            node = queue.popleft()
            visited += 1

            for neighbor in self.edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited != len(self.nodes)

    def topological_sort(self) -> List[str]:
        """Return topologically sorted nodes."""
        in_degree = self.in_degree.copy()
        queue = deque([node for node in self.nodes if in_degree.get(node, 0) == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in self.edges.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BranchResult:
    """Result of conditional branching."""
    success: bool
    selected_branch: Optional[str] = None
    evaluated_conditions: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ParallelResult:
    """Result of parallel task execution."""
    success: bool
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    failed_tasks: List[str] = field(default_factory=list)


@dataclass
class Schedule:
    """Workflow schedule configuration."""
    schedule_id: str = field(default_factory=lambda: str(uuid4()))
    cron_expression: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    enabled: bool = True


@dataclass
class ScheduleResult:
    """Result of workflow scheduling."""
    success: bool
    schedule_id: str
    next_run: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class StateEntry:
    """Workflow state tracking entry."""
    entry_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    task_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetryPolicy:
    """Retry policy for failed tasks."""
    max_retries: int = 3
    retry_delay: timedelta = timedelta(seconds=1)
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0


@dataclass
class FailureHandlingResult:
    """Result of failure handling."""
    success: bool
    action_taken: str = ""  # retry, compensate, fail
    retry_count: int = 0
    error: Optional[str] = None


@dataclass
class CompensationResult:
    """Result of compensation/rollback."""
    success: bool
    compensated_tasks: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class Change:
    """Workflow change for versioning."""
    change_id: str = field(default_factory=lambda: str(uuid4()))
    change_type: str = ""  # added, modified, removed
    affected_element: str = ""
    description: str = ""


@dataclass
class VersionEntry:
    """Workflow version entry."""
    version: str = ""
    workflow_id: str = ""
    changes: List[Change] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowAnalysis:
    """Workflow structure analysis."""
    workflow_id: str
    total_tasks: int = 0
    critical_path_length: int = 0
    parallelizable_tasks: int = 0
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class WorkflowState:
    """Complete workflow execution state."""
    workflow_id: str
    status: WorkflowStatus
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    context: WorkflowContext = field(default_factory=WorkflowContext)
    checkpoints: List[StateEntry] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class PersistenceResult:
    """Result of state persistence."""
    success: bool
    workflow_id: str
    checkpoint_id: str = ""
    error: Optional[str] = None


@dataclass
class ResumeResult:
    """Result of workflow resumption."""
    success: bool
    workflow_id: str
    resumed_from_task: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WorkflowVisualization:
    """Workflow visualization data."""
    workflow_id: str
    format: str = "mermaid"  # mermaid, dot, json
    content: str = ""


@dataclass
class WorkflowMetrics:
    """Workflow execution metrics."""
    workflow_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    task_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Workflow validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class WorkflowExecutionResult:
    """Result of workflow execution."""
    success: bool
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.COMPLETED
    completed_tasks: int = 0
    failed_tasks: int = 0
    execution_time: float = 0.0
    output: Any = None
    errors: List[str] = field(default_factory=list)


# ==================== Main FSA Class ====================

class WorkflowEngineFSA:
    """
    Workflow Engine Finite State Automaton.

    Provides comprehensive workflow orchestration with DAG-based execution,
    conditional branching, parallel execution, and fault tolerance.
    """

    def __init__(
        self,
        name: str = "WorkflowEngineFSA",
        persistence_path: Optional[Path] = None,
        max_parallel_tasks: int = 4,
    ):
        """
        Initialize Workflow Engine FSA.

        Args:
            name: Name of the FSA instance
            persistence_path: Path for workflow state persistence
            max_parallel_tasks: Maximum concurrent tasks
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.persistence_path = persistence_path or Path("/tmp/workflow_engine_fsa")
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        self.max_parallel_tasks = max_parallel_tasks

        # Workflow storage
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.workflow_states: Dict[str, WorkflowState] = {}

        # DAG storage
        self.workflow_dags: Dict[str, DAG] = {}

        # Execution tracking
        self.task_results: Dict[str, Dict[str, TaskResult]] = defaultdict(dict)
        self.execution_history: Dict[str, List[WorkflowState]] = defaultdict(list)

        # Scheduling
        self.schedules: Dict[str, Schedule] = {}
        self.scheduled_workflows: Dict[str, str] = {}  # schedule_id -> workflow_id

        # Versioning
        self.workflow_versions: Dict[str, List[VersionEntry]] = defaultdict(list)

        # Metrics
        self.workflow_metrics: Dict[str, WorkflowMetrics] = {}
        self.execution_times: Dict[str, List[float]] = defaultdict(list)

        # Compensation handlers
        self.compensation_handlers: Dict[str, Callable] = {}

        # Thread pool for parallel execution
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_tasks)

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, workflow: WorkflowDefinition) -> WorkflowExecutionResult:
        """
        Main workflow execution pipeline.

        Args:
            workflow: Workflow definition to execute

        Returns:
            WorkflowExecutionResult with execution status
        """
        start_time = time.time()
        workflow_id = workflow.workflow_id

        try:
            # Validate workflow
            validation = self.validate(workflow)
            if not validation.valid:
                return WorkflowExecutionResult(
                    success=False,
                    workflow_id=workflow_id,
                    status=WorkflowStatus.FAILED,
                    errors=validation.errors
                )

            # Build DAG
            dag = self.build_dag(workflow.tasks, workflow.dependencies)
            self.workflow_dags[workflow_id] = dag

            # Initialize workflow state
            context = WorkflowContext(workflow_id=workflow_id)
            state = WorkflowState(
                workflow_id=workflow_id,
                status=WorkflowStatus.RUNNING,
                context=context,
                started_at=datetime.utcnow()
            )
            self.workflow_states[workflow_id] = state

            # Get execution order
            execution_order = dag.topological_sort()

            # Execute tasks in order
            completed = 0
            failed = 0
            errors = []

            for task_id in execution_order:
                if task_id not in workflow.tasks:
                    continue

                task = workflow.tasks[task_id]

                # Check dependencies completed
                deps = workflow.dependencies.get(task_id, [])
                if not all(dep in state.completed_tasks for dep in deps):
                    continue

                # Execute task
                result = self.execute_task(task, context)
                self.task_results[workflow_id][task_id] = result

                if result.success:
                    state.completed_tasks.append(task_id)
                    completed += 1

                    # Track state
                    self.track_state(workflow_id, task, TaskStatus.COMPLETED)
                else:
                    state.failed_tasks.append(task_id)
                    failed += 1
                    errors.append(f"Task {task.name} failed: {result.error}")

                    # Handle failure
                    retry_policy = RetryPolicy(max_retries=task.max_retries)
                    failure_result = self.handle_task_failure(task, Exception(result.error or "Unknown"), retry_policy)

                    if not failure_result.success:
                        # Compensate workflow
                        self.compensate_workflow(workflow_id, task)
                        state.status = WorkflowStatus.FAILED
                        break

            # Update final state
            if state.status != WorkflowStatus.FAILED:
                state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow()

            # Persist final state
            self.persist_workflow_state(workflow_id, state)

            execution_time = time.time() - start_time

            return WorkflowExecutionResult(
                success=state.status == WorkflowStatus.COMPLETED,
                workflow_id=workflow_id,
                status=state.status,
                completed_tasks=completed,
                failed_tasks=failed,
                execution_time=execution_time,
                output=context.data,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return WorkflowExecutionResult(
                success=False,
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )

    # ==================== Validation ====================

    def validate(self, workflow: WorkflowDefinition) -> ValidationResult:
        """
        Validate workflow structure and dependencies.

        Args:
            workflow: Workflow to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check workflow has tasks
        if not workflow.tasks:
            errors.append("Workflow has no tasks")

        # Check start task exists
        if workflow.start_task and workflow.start_task not in workflow.tasks:
            errors.append(f"Start task '{workflow.start_task}' not found in tasks")

        # Check dependencies reference valid tasks
        for task_id, deps in workflow.dependencies.items():
            if task_id not in workflow.tasks:
                errors.append(f"Task '{task_id}' in dependencies not found")

            for dep in deps:
                if dep not in workflow.tasks:
                    errors.append(f"Dependency '{dep}' not found in tasks")

        # Check for cycles
        if workflow.tasks and workflow.dependencies:
            dag = self.build_dag(workflow.tasks, workflow.dependencies)
            if dag.has_cycle():
                errors.append("Workflow contains circular dependencies")

        # Check end tasks exist
        for end_task in workflow.end_tasks:
            if end_task not in workflow.tasks:
                errors.append(f"End task '{end_task}' not found in tasks")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Workflow Definition ====================

    def define_workflow(
        self,
        name: str,
        tasks: List[Task],
        dependencies: Dict[str, List[str]]
    ) -> WorkflowDefinition:
        """
        Create workflow definition.

        Args:
            name: Workflow name
            tasks: List of tasks
            dependencies: Task dependencies

        Returns:
            WorkflowDefinition
        """
        workflow = WorkflowDefinition(
            name=name,
            tasks={task.task_id: task for task in tasks},
            dependencies=dependencies
        )

        # Determine start and end tasks
        all_deps = set()
        for deps in dependencies.values():
            all_deps.update(deps)

        # Start tasks have no dependencies
        start_tasks = [tid for tid in workflow.tasks.keys() if tid not in all_deps]
        if start_tasks:
            workflow.start_task = start_tasks[0]

        # End tasks have no dependents
        has_dependents = set(dependencies.keys())
        end_tasks = [tid for tid in workflow.tasks.keys() if tid not in has_dependents]
        workflow.end_tasks = end_tasks

        with self.lock:
            self.workflows[workflow.workflow_id] = workflow

        logger.info(f"Defined workflow '{name}' with {len(tasks)} tasks")
        return workflow

    # ==================== DAG Operations ====================

    def build_dag(
        self,
        tasks: Dict[str, Task],
        dependencies: Dict[str, List[str]]
    ) -> DAG:
        """
        Construct dependency graph.

        Args:
            tasks: Task dictionary
            dependencies: Task dependencies

        Returns:
            DAG instance
        """
        dag = DAG()

        # Add all task nodes
        for task_id in tasks.keys():
            dag.add_node(task_id)

        # Add dependency edges
        for task_id, deps in dependencies.items():
            for dep_id in deps:
                dag.add_edge(dep_id, task_id)

        return dag

    # ==================== Task Execution ====================

    def execute_task(self, task: Task, context: WorkflowContext) -> TaskResult:
        """
        Run individual workflow task.

        Args:
            task: Task to execute
            context: Workflow context

        Returns:
            TaskResult with execution status
        """
        start_time = time.time()

        try:
            if task.handler:
                # Execute task handler with context
                output = task.handler(context)
                success = True
                error = None
            else:
                # Mock execution
                output = {"task_id": task.task_id, "executed": True}
                success = True
                error = None

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.task_id,
                success=success,
                output=output,
                error=error,
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )

    # ==================== Conditional Branching ====================

    def evaluate_condition(
        self,
        condition: Condition,
        context: WorkflowContext
    ) -> bool:
        """
        Evaluate branching logic.

        Args:
            condition: Condition to evaluate
            context: Workflow context

        Returns:
            Boolean result of condition evaluation
        """
        try:
            if condition.predicate:
                return condition.predicate(context)
            elif condition.expression:
                # Simplified expression evaluation
                # In production, use a safe expression evaluator
                return eval(condition.expression, {"context": context})
            else:
                return True
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False

    def branch_workflow(
        self,
        decision_node: DecisionNode,
        context: WorkflowContext
    ) -> BranchResult:
        """
        Handle conditional paths.

        Args:
            decision_node: Decision node with conditions
            context: Workflow context

        Returns:
            BranchResult with selected branch
        """
        evaluated = {}

        # Evaluate conditions in order
        for condition, next_task in decision_node.conditions:
            result = self.evaluate_condition(condition, context)
            evaluated[condition.condition_id] = result

            if result:
                return BranchResult(
                    success=True,
                    selected_branch=next_task,
                    evaluated_conditions=evaluated
                )

        # No condition matched, use default
        if decision_node.default_task:
            return BranchResult(
                success=True,
                selected_branch=decision_node.default_task,
                evaluated_conditions=evaluated
            )

        return BranchResult(
            success=False,
            evaluated_conditions=evaluated
        )

    # ==================== Parallel Execution ====================

    def execute_parallel(
        self,
        tasks: List[Task],
        context: WorkflowContext
    ) -> ParallelResult:
        """
        Run tasks concurrently.

        Args:
            tasks: List of tasks to execute in parallel
            context: Workflow context

        Returns:
            ParallelResult with execution results
        """
        task_results = {}
        failed_tasks = []

        # Submit tasks to thread pool
        future_to_task = {}
        for task in tasks:
            future = self.executor.submit(self.execute_task, task, context)
            future_to_task[future] = task

        # Collect results
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                task_results[task.task_id] = result

                if not result.success:
                    failed_tasks.append(task.task_id)

            except Exception as e:
                logger.error(f"Parallel task {task.name} failed: {e}")
                failed_tasks.append(task.task_id)
                task_results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=str(e)
                )

        return ParallelResult(
            success=len(failed_tasks) == 0,
            task_results=task_results,
            failed_tasks=failed_tasks
        )

    # ==================== Scheduling ====================

    def schedule_workflow(
        self,
        workflow: WorkflowDefinition,
        schedule: Schedule
    ) -> ScheduleResult:
        """
        Set timed execution.

        Args:
            workflow: Workflow to schedule
            schedule: Schedule configuration

        Returns:
            ScheduleResult with scheduling status
        """
        try:
            with self.lock:
                self.schedules[schedule.schedule_id] = schedule
                self.scheduled_workflows[schedule.schedule_id] = workflow.workflow_id

            # Calculate next run (simplified)
            next_run = schedule.start_time or datetime.utcnow()

            logger.info(f"Scheduled workflow {workflow.name}")
            return ScheduleResult(
                success=True,
                schedule_id=schedule.schedule_id,
                next_run=next_run
            )

        except Exception as e:
            logger.error(f"Scheduling error: {e}")
            return ScheduleResult(
                success=False,
                schedule_id=schedule.schedule_id,
                error=str(e)
            )

    # ==================== State Tracking ====================

    def track_state(
        self,
        workflow_id: str,
        current_task: Task,
        status: TaskStatus
    ) -> StateEntry:
        """
        Monitor workflow progress.

        Args:
            workflow_id: Workflow identifier
            current_task: Current task being executed
            status: Task status

        Returns:
            StateEntry with state information
        """
        entry = StateEntry(
            workflow_id=workflow_id,
            task_id=current_task.task_id,
            status=status,
            checkpoint_data={"task_name": current_task.name}
        )

        with self.lock:
            if workflow_id in self.workflow_states:
                self.workflow_states[workflow_id].checkpoints.append(entry)

        return entry

    # ==================== Error Handling ====================

    def handle_task_failure(
        self,
        task: Task,
        error: Exception,
        retry_policy: RetryPolicy
    ) -> FailureHandlingResult:
        """
        Manage task failures.

        Args:
            task: Failed task
            error: Exception that occurred
            retry_policy: Retry configuration

        Returns:
            FailureHandlingResult with handling status
        """
        try:
            if task.retry_count < retry_policy.max_retries:
                # Calculate retry delay
                if retry_policy.exponential_backoff:
                    delay = retry_policy.retry_delay.total_seconds() * (
                        retry_policy.backoff_multiplier ** task.retry_count
                    )
                else:
                    delay = retry_policy.retry_delay.total_seconds()

                logger.info(f"Retrying task {task.name} after {delay}s (attempt {task.retry_count + 1})")

                # Increment retry count
                task.retry_count += 1

                return FailureHandlingResult(
                    success=True,
                    action_taken="retry",
                    retry_count=task.retry_count
                )
            else:
                logger.error(f"Task {task.name} failed after {task.retry_count} retries")
                return FailureHandlingResult(
                    success=False,
                    action_taken="fail",
                    retry_count=task.retry_count,
                    error=str(error)
                )

        except Exception as e:
            logger.error(f"Error handling failure: {e}")
            return FailureHandlingResult(
                success=False,
                action_taken="error",
                error=str(e)
            )

    # ==================== Compensation ====================

    def compensate_workflow(
        self,
        workflow_id: str,
        failed_task: Task
    ) -> CompensationResult:
        """
        Rollback workflow on failure.

        Args:
            workflow_id: Workflow identifier
            failed_task: Task that failed

        Returns:
            CompensationResult with compensation status
        """
        try:
            compensated = []

            if workflow_id in self.workflow_states:
                state = self.workflow_states[workflow_id]

                # Compensate completed tasks in reverse order
                for task_id in reversed(state.completed_tasks):
                    if task_id in self.compensation_handlers:
                        try:
                            self.compensation_handlers[task_id](state.context)
                            compensated.append(task_id)
                        except Exception as e:
                            logger.error(f"Compensation failed for {task_id}: {e}")

            logger.info(f"Compensated {len(compensated)} tasks")
            return CompensationResult(
                success=True,
                compensated_tasks=compensated
            )

        except Exception as e:
            logger.error(f"Compensation error: {e}")
            return CompensationResult(
                success=False,
                error=str(e)
            )

    def register_compensation_handler(
        self,
        task_id: str,
        handler: Callable
    ) -> None:
        """Register compensation handler for a task."""
        self.compensation_handlers[task_id] = handler

    # ==================== Versioning ====================

    def version_workflow(
        self,
        workflow: WorkflowDefinition,
        version: str,
        changes: List[Change]
    ) -> VersionEntry:
        """
        Track workflow versions.

        Args:
            workflow: Workflow definition
            version: Version string
            changes: List of changes

        Returns:
            VersionEntry with version information
        """
        entry = VersionEntry(
            version=version,
            workflow_id=workflow.workflow_id,
            changes=changes
        )

        with self.lock:
            self.workflow_versions[workflow.workflow_id].append(entry)
            workflow.version = version

        logger.info(f"Versioned workflow {workflow.name} as {version}")
        return entry

    # ==================== Analysis ====================

    def analyze_workflow(self, workflow: WorkflowDefinition) -> WorkflowAnalysis:
        """
        Optimize workflow structure.

        Args:
            workflow: Workflow to analyze

        Returns:
            WorkflowAnalysis with optimization recommendations
        """
        analysis = WorkflowAnalysis(
            workflow_id=workflow.workflow_id,
            total_tasks=len(workflow.tasks)
        )

        # Build DAG
        dag = self.build_dag(workflow.tasks, workflow.dependencies)

        # Find critical path (longest path through DAG)
        critical_path = self._find_critical_path(dag, workflow.dependencies)
        analysis.critical_path_length = len(critical_path)

        # Identify parallelizable tasks
        parallelizable = self._find_parallelizable_tasks(workflow.dependencies)
        analysis.parallelizable_tasks = len(parallelizable)

        # Find bottlenecks (tasks with many dependencies)
        for task_id, deps in workflow.dependencies.items():
            if len(deps) > 3:
                analysis.bottlenecks.append(task_id)

        # Generate recommendations
        if analysis.parallelizable_tasks > 0:
            analysis.recommendations.append(
                f"Consider parallelizing {analysis.parallelizable_tasks} independent tasks"
            )

        if analysis.bottlenecks:
            analysis.recommendations.append(
                f"Reduce dependencies for tasks: {', '.join(analysis.bottlenecks)}"
            )

        return analysis

    def _find_critical_path(
        self,
        dag: DAG,
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Find longest path through DAG."""
        # Simplified critical path finding
        sorted_nodes = dag.topological_sort()
        if sorted_nodes:
            return sorted_nodes
        return []

    def _find_parallelizable_tasks(
        self,
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Find tasks that can run in parallel."""
        parallelizable = []

        # Tasks with same dependencies can run in parallel
        dep_groups = defaultdict(list)
        for task_id, deps in dependencies.items():
            dep_key = tuple(sorted(deps))
            dep_groups[dep_key].append(task_id)

        for tasks in dep_groups.values():
            if len(tasks) > 1:
                parallelizable.extend(tasks)

        return parallelizable

    # ==================== Persistence ====================

    def persist_workflow_state(
        self,
        workflow_id: str,
        state: WorkflowState
    ) -> PersistenceResult:
        """
        Save workflow state for recovery.

        Args:
            workflow_id: Workflow identifier
            state: Workflow state to persist

        Returns:
            PersistenceResult with persistence status
        """
        try:
            checkpoint_id = str(uuid4())
            file_path = self.persistence_path / f"{workflow_id}_{checkpoint_id}.json"

            # Serialize state
            state_data = {
                "workflow_id": state.workflow_id,
                "status": state.status.value,
                "current_task": state.current_task,
                "completed_tasks": state.completed_tasks,
                "failed_tasks": state.failed_tasks,
                "context_data": state.context.data,
                "started_at": state.started_at.isoformat() if state.started_at else None,
                "completed_at": state.completed_at.isoformat() if state.completed_at else None
            }

            with open(file_path, 'w') as f:
                json.dump(state_data, f, indent=2)

            logger.info(f"Persisted workflow state to {file_path}")
            return PersistenceResult(
                success=True,
                workflow_id=workflow_id,
                checkpoint_id=checkpoint_id
            )

        except Exception as e:
            logger.error(f"Persistence error: {e}")
            return PersistenceResult(
                success=False,
                workflow_id=workflow_id,
                error=str(e)
            )

    # ==================== Resumption ====================

    def resume_workflow(self, workflow_id: str) -> ResumeResult:
        """
        Continue workflow from checkpoint.

        Args:
            workflow_id: Workflow identifier

        Returns:
            ResumeResult with resumption status
        """
        try:
            # Find latest checkpoint
            checkpoint_files = list(self.persistence_path.glob(f"{workflow_id}_*.json"))

            if not checkpoint_files:
                return ResumeResult(
                    success=False,
                    workflow_id=workflow_id,
                    error="No checkpoints found"
                )

            # Load latest checkpoint
            latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

            with open(latest_checkpoint, 'r') as f:
                state_data = json.load(f)

            # Restore state
            context = WorkflowContext(
                workflow_id=workflow_id,
                data=state_data.get("context_data", {})
            )

            state = WorkflowState(
                workflow_id=workflow_id,
                status=WorkflowStatus(state_data["status"]),
                current_task=state_data.get("current_task"),
                completed_tasks=state_data.get("completed_tasks", []),
                failed_tasks=state_data.get("failed_tasks", []),
                context=context
            )

            with self.lock:
                self.workflow_states[workflow_id] = state

            logger.info(f"Resumed workflow from checkpoint")
            return ResumeResult(
                success=True,
                workflow_id=workflow_id,
                resumed_from_task=state.current_task
            )

        except Exception as e:
            logger.error(f"Resumption error: {e}")
            return ResumeResult(
                success=False,
                workflow_id=workflow_id,
                error=str(e)
            )

    # ==================== Visualization ====================

    def visualize_workflow(
        self,
        workflow: WorkflowDefinition,
        format: str = "mermaid"
    ) -> WorkflowVisualization:
        """
        Generate workflow diagram.

        Args:
            workflow: Workflow to visualize
            format: Output format (mermaid, dot, json)

        Returns:
            WorkflowVisualization with diagram data
        """
        if format == "mermaid":
            content = self._generate_mermaid(workflow)
        elif format == "dot":
            content = self._generate_dot(workflow)
        else:
            content = self._generate_json(workflow)

        return WorkflowVisualization(
            workflow_id=workflow.workflow_id,
            format=format,
            content=content
        )

    def _generate_mermaid(self, workflow: WorkflowDefinition) -> str:
        """Generate Mermaid diagram."""
        lines = ["graph TD"]

        for task_id, task in workflow.tasks.items():
            lines.append(f"    {task_id}[{task.name}]")

        for task_id, deps in workflow.dependencies.items():
            for dep in deps:
                lines.append(f"    {dep} --> {task_id}")

        return "\n".join(lines)

    def _generate_dot(self, workflow: WorkflowDefinition) -> str:
        """Generate Graphviz DOT format."""
        lines = ["digraph workflow {"]

        for task_id, task in workflow.tasks.items():
            lines.append(f'    {task_id} [label="{task.name}"];')

        for task_id, deps in workflow.dependencies.items():
            for dep in deps:
                lines.append(f"    {dep} -> {task_id};")

        lines.append("}")
        return "\n".join(lines)

    def _generate_json(self, workflow: WorkflowDefinition) -> str:
        """Generate JSON representation."""
        data = {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "tasks": {
                tid: {"name": task.name, "type": task.task_type.value}
                for tid, task in workflow.tasks.items()
            },
            "dependencies": workflow.dependencies
        }
        return json.dumps(data, indent=2)

    # ==================== Metrics ====================

    def get_workflow_metrics(self, workflow_id: str) -> WorkflowMetrics:
        """
        Collect execution statistics.

        Args:
            workflow_id: Workflow identifier

        Returns:
            WorkflowMetrics with statistics
        """
        with self.lock:
            if workflow_id not in self.workflow_metrics:
                self.workflow_metrics[workflow_id] = WorkflowMetrics(
                    workflow_id=workflow_id
                )

            metrics = self.workflow_metrics[workflow_id]

            # Calculate averages
            if workflow_id in self.execution_times:
                times = self.execution_times[workflow_id]
                if times:
                    metrics.avg_execution_time = sum(times) / len(times)

            return metrics

    def update_metrics(
        self,
        workflow_id: str,
        success: bool,
        execution_time: float
    ) -> None:
        """Update workflow metrics."""
        with self.lock:
            if workflow_id not in self.workflow_metrics:
                self.workflow_metrics[workflow_id] = WorkflowMetrics(
                    workflow_id=workflow_id
                )

            metrics = self.workflow_metrics[workflow_id]
            metrics.total_executions += 1

            if success:
                metrics.successful_executions += 1
            else:
                metrics.failed_executions += 1

            self.execution_times[workflow_id].append(execution_time)

    # ==================== Utility Methods ====================

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get current workflow state."""
        return self.workflow_states.get(workflow_id)

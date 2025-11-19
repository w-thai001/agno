"""Workflow Orchestrator FSA for Agno Framework.

This module provides a production-ready workflow orchestration system with:
- DAG-based dependency resolution
- Parallel step execution
- Automatic retry with exponential backoff
- Checkpoint/resume for long workflows
- Resource pooling and throttling
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

try:
    import networkx as nx
except ImportError:
    raise ImportError(
        "networkx is required for WorkflowOrchestrator. Install it with: pip install networkx"
    )

from agno.utils.log import logger


class StepStatus(Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class OrchestratorState(Enum):
    """State of the workflow orchestrator FSA."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepResult:
    """Result of a step execution."""

    step_id: str
    status: StepStatus
    output: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempt: int = 1
    execution_time: Optional[float] = None

    def __post_init__(self):
        if self.execution_time is None and self.start_time and self.end_time:
            self.execution_time = self.end_time - self.start_time


@dataclass
class WorkflowStep:
    """Definition of a workflow step."""

    step_id: str
    name: str
    function: Callable
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 3
    retry_delay: float = 1.0  # Initial delay in seconds
    retry_backoff: float = 2.0  # Exponential backoff multiplier
    timeout: Optional[float] = None  # Timeout in seconds
    required: bool = True  # If False, failure won't stop the workflow
    resource_pool: Optional[str] = None  # Name of resource pool to use
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourcePool:
    """Resource pool for throttling parallel execution."""

    name: str
    max_concurrent: int
    _semaphore: Optional[asyncio.Semaphore] = field(default=None, init=False, repr=False)

    def get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore for this pool."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore


@dataclass
class WorkflowCheckpoint:
    """Checkpoint data for resuming workflows."""

    workflow_id: str
    checkpoint_time: float
    completed_steps: Set[str]
    failed_steps: Set[str]
    step_results: Dict[str, StepResult]
    context: Dict[str, Any]


class WorkflowOrchestrator:
    """
    Production-ready Workflow Orchestrator with FSA-based execution.

    Features:
    - DAG-based dependency resolution using NetworkX
    - Parallel step execution with asyncio
    - Automatic retry with exponential backoff
    - Checkpoint/resume functionality
    - Resource pooling and throttling

    Example:
        ```python
        # Define workflow steps
        steps = [
            WorkflowStep(
                step_id="step1",
                name="Fetch Data",
                function=fetch_data,
                dependencies=[],
            ),
            WorkflowStep(
                step_id="step2",
                name="Process Data",
                function=process_data,
                dependencies=["step1"],
            ),
        ]

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            workflow_id="my_workflow",
            steps=steps,
            max_parallelism=5,
        )

        # Execute workflow
        result = await orchestrator.execute(initial_context={"user_id": "123"})
        ```
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        steps: Optional[List[WorkflowStep]] = None,
        max_parallelism: int = 10,
        checkpoint_interval: Optional[float] = None,  # Seconds between checkpoints
        enable_checkpointing: bool = True,
        resource_pools: Optional[Dict[str, ResourcePool]] = None,
    ):
        """Initialize the workflow orchestrator.

        Args:
            workflow_id: Unique identifier for this workflow instance
            steps: List of workflow steps to execute
            max_parallelism: Maximum number of parallel steps
            checkpoint_interval: Interval between automatic checkpoints (seconds)
            enable_checkpointing: Whether to enable checkpointing
            resource_pools: Dict of resource pools for throttling
        """
        self.workflow_id = workflow_id or str(uuid4())
        self.steps: Dict[str, WorkflowStep] = {}
        self.max_parallelism = max_parallelism
        self.checkpoint_interval = checkpoint_interval
        self.enable_checkpointing = enable_checkpointing
        self.resource_pools = resource_pools or {}

        # FSA state
        self.state = OrchestratorState.IDLE

        # Execution tracking
        self.step_results: Dict[str, StepResult] = {}
        self.completed_steps: Set[str] = set()
        self.failed_steps: Set[str] = set()
        self.running_steps: Set[str] = set()

        # DAG for dependency resolution
        self.dag: Optional[nx.DiGraph] = None

        # Context shared across steps
        self.context: Dict[str, Any] = {}

        # Checkpoint data
        self.last_checkpoint_time: Optional[float] = None
        self.checkpoints: List[WorkflowCheckpoint] = []

        # Semaphore for global parallelism control
        self._global_semaphore: Optional[asyncio.Semaphore] = None

        # Add steps if provided
        if steps:
            for step in steps:
                self.add_step(step)

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        if step.step_id in self.steps:
            raise ValueError(f"Step {step.step_id} already exists")
        self.steps[step.step_id] = step

    def add_resource_pool(self, pool: ResourcePool) -> None:
        """Add a resource pool for throttling."""
        self.resource_pools[pool.name] = pool

    def _build_dag(self) -> nx.DiGraph:
        """Build the dependency DAG from workflow steps."""
        dag = nx.DiGraph()

        # Add all steps as nodes
        for step_id in self.steps:
            dag.add_node(step_id)

        # Add edges for dependencies
        for step_id, step in self.steps.items():
            for dep_id in step.dependencies:
                if dep_id not in self.steps:
                    raise ValueError(f"Step {step_id} depends on unknown step {dep_id}")
                dag.add_edge(dep_id, step_id)

        # Check for cycles
        if not nx.is_directed_acyclic_graph(dag):
            cycles = list(nx.simple_cycles(dag))
            raise ValueError(f"Workflow contains cycles: {cycles}")

        return dag

    def _get_ready_steps(self) -> List[str]:
        """Get steps that are ready to execute (all dependencies completed)."""
        if self.dag is None:
            raise RuntimeError("DAG not built. Call execute() first.")

        ready = []
        for step_id in self.steps:
            # Skip if already completed, failed, or running
            if step_id in self.completed_steps or step_id in self.failed_steps or step_id in self.running_steps:
                continue

            # Check if all dependencies are completed
            dependencies = list(self.dag.predecessors(step_id))
            if all(dep in self.completed_steps for dep in dependencies):
                ready.append(step_id)

        return ready

    async def _execute_step(self, step_id: str) -> StepResult:
        """Execute a single step with retry logic."""
        step = self.steps[step_id]
        self.running_steps.add(step_id)

        logger.info(f"[{self.workflow_id}] Starting step: {step.name} ({step_id})")

        # Get the appropriate semaphore (resource pool or global)
        semaphore = None
        if step.resource_pool and step.resource_pool in self.resource_pools:
            semaphore = self.resource_pools[step.resource_pool].get_semaphore()
        elif self._global_semaphore:
            semaphore = self._global_semaphore

        attempt = 0
        last_error = None

        while attempt < step.retry_count:
            attempt += 1
            start_time = time.time()

            try:
                # Acquire semaphore if available
                if semaphore:
                    async with semaphore:
                        output = await self._run_step_function(step, attempt)
                else:
                    output = await self._run_step_function(step, attempt)

                end_time = time.time()
                result = StepResult(
                    step_id=step_id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    attempt=attempt,
                )

                self.running_steps.remove(step_id)
                self.completed_steps.add(step_id)
                self.step_results[step_id] = result

                logger.info(
                    f"[{self.workflow_id}] Completed step: {step.name} ({step_id}) "
                    f"in {result.execution_time:.2f}s (attempt {attempt})"
                )

                return result

            except Exception as e:
                last_error = e
                end_time = time.time()

                logger.warning(
                    f"[{self.workflow_id}] Step {step.name} ({step_id}) failed "
                    f"(attempt {attempt}/{step.retry_count}): {e}"
                )

                # If we have more retries, wait with exponential backoff
                if attempt < step.retry_count:
                    delay = step.retry_delay * (step.retry_backoff ** (attempt - 1))
                    logger.info(f"[{self.workflow_id}] Retrying step {step_id} in {delay:.2f}s")
                    await asyncio.sleep(delay)

        # All retries exhausted
        result = StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=last_error,
            start_time=start_time,
            end_time=time.time(),
            attempt=attempt,
        )

        self.running_steps.remove(step_id)
        self.failed_steps.add(step_id)
        self.step_results[step_id] = result

        logger.error(
            f"[{self.workflow_id}] Step {step.name} ({step_id}) failed after {attempt} attempts: {last_error}"
        )

        return result

    async def _run_step_function(self, step: WorkflowStep, attempt: int) -> Any:
        """Run the step function with timeout handling."""
        # Prepare step context
        step_context = {
            "workflow_id": self.workflow_id,
            "step_id": step.step_id,
            "attempt": attempt,
            "context": self.context,
            "results": {
                dep_id: self.step_results[dep_id].output
                for dep_id in step.dependencies
                if dep_id in self.step_results
            },
            **step.kwargs,
        }

        # Check if function is async
        if asyncio.iscoroutinefunction(step.function):
            if step.timeout:
                return await asyncio.wait_for(step.function(**step_context), timeout=step.timeout)
            else:
                return await step.function(**step_context)
        else:
            # Run sync function in executor
            loop = asyncio.get_event_loop()
            if step.timeout:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: step.function(**step_context)), timeout=step.timeout
                )
            else:
                return await loop.run_in_executor(None, lambda: step.function(**step_context))

    def _create_checkpoint(self) -> WorkflowCheckpoint:
        """Create a checkpoint of the current workflow state."""
        return WorkflowCheckpoint(
            workflow_id=self.workflow_id,
            checkpoint_time=time.time(),
            completed_steps=self.completed_steps.copy(),
            failed_steps=self.failed_steps.copy(),
            step_results=self.step_results.copy(),
            context=self.context.copy(),
        )

    def _should_checkpoint(self) -> bool:
        """Check if we should create a checkpoint."""
        if not self.enable_checkpointing:
            return False

        if self.checkpoint_interval is None:
            return False

        if self.last_checkpoint_time is None:
            return True

        return (time.time() - self.last_checkpoint_time) >= self.checkpoint_interval

    async def _checkpoint_if_needed(self) -> None:
        """Create a checkpoint if needed."""
        if self._should_checkpoint():
            checkpoint = self._create_checkpoint()
            self.checkpoints.append(checkpoint)
            self.last_checkpoint_time = time.time()
            logger.debug(f"[{self.workflow_id}] Created checkpoint at {checkpoint.checkpoint_time}")

    def load_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Load a checkpoint to resume workflow execution."""
        if checkpoint.workflow_id != self.workflow_id:
            raise ValueError(
                f"Checkpoint workflow_id {checkpoint.workflow_id} does not match {self.workflow_id}"
            )

        self.completed_steps = checkpoint.completed_steps.copy()
        self.failed_steps = checkpoint.failed_steps.copy()
        self.step_results = checkpoint.step_results.copy()
        self.context = checkpoint.context.copy()

        logger.info(
            f"[{self.workflow_id}] Loaded checkpoint from {checkpoint.checkpoint_time}. "
            f"Completed steps: {len(self.completed_steps)}, Failed steps: {len(self.failed_steps)}"
        )

    async def execute(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        resume_from_checkpoint: Optional[WorkflowCheckpoint] = None,
    ) -> Dict[str, Any]:
        """
        Execute the workflow.

        Args:
            initial_context: Initial context data for the workflow
            resume_from_checkpoint: Optional checkpoint to resume from

        Returns:
            Dict containing:
                - workflow_result: Final workflow results
                - execution_log: List of execution events
                - failed_steps: List of failed step IDs
                - step_results: Dict of all step results
        """
        # Transition to INITIALIZING state
        self.state = OrchestratorState.INITIALIZING

        # Initialize context
        self.context = initial_context or {}

        # Load checkpoint if resuming
        if resume_from_checkpoint:
            self.load_checkpoint(resume_from_checkpoint)

        # Build DAG
        self.dag = self._build_dag()
        logger.info(f"[{self.workflow_id}] Built DAG with {len(self.steps)} steps")

        # Initialize global semaphore
        self._global_semaphore = asyncio.Semaphore(self.max_parallelism)

        # Transition to EXECUTING state
        self.state = OrchestratorState.EXECUTING

        execution_log = []
        start_time = time.time()

        try:
            # Main execution loop
            while True:
                # Check if all steps are done
                total_done = len(self.completed_steps) + len(self.failed_steps)
                if total_done >= len(self.steps):
                    break

                # Get ready steps
                ready_steps = self._get_ready_steps()

                if not ready_steps:
                    # No steps ready - check if we're blocked
                    if not self.running_steps:
                        # Nothing running and nothing ready - we're stuck
                        logger.error(
                            f"[{self.workflow_id}] Workflow stuck. "
                            f"Completed: {len(self.completed_steps)}, "
                            f"Failed: {len(self.failed_steps)}, "
                            f"Total: {len(self.steps)}"
                        )
                        self.state = OrchestratorState.FAILED
                        break
                    # Wait for running steps to complete
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready steps in parallel
                tasks = [self._execute_step(step_id) for step_id in ready_steps]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log results
                for step_id, result in zip(ready_steps, results):
                    if isinstance(result, Exception):
                        logger.error(f"[{self.workflow_id}] Step {step_id} raised exception: {result}")
                        execution_log.append(
                            {
                                "step_id": step_id,
                                "status": "failed",
                                "error": str(result),
                                "time": time.time(),
                            }
                        )
                    else:
                        execution_log.append(
                            {
                                "step_id": step_id,
                                "status": result.status.value,
                                "execution_time": result.execution_time,
                                "attempt": result.attempt,
                                "time": time.time(),
                            }
                        )

                # Checkpoint if needed
                await self._checkpoint_if_needed()

                # Check if any required step failed
                for step_id in self.failed_steps:
                    if self.steps[step_id].required:
                        logger.error(
                            f"[{self.workflow_id}] Required step {step_id} failed. Stopping workflow."
                        )
                        self.state = OrchestratorState.FAILED
                        break

                if self.state == OrchestratorState.FAILED:
                    break

            # Determine final state
            if self.state != OrchestratorState.FAILED:
                if self.failed_steps:
                    # Some steps failed but they weren't required
                    self.state = OrchestratorState.COMPLETED
                    logger.warning(
                        f"[{self.workflow_id}] Workflow completed with {len(self.failed_steps)} failed steps"
                    )
                else:
                    self.state = OrchestratorState.COMPLETED
                    logger.info(f"[{self.workflow_id}] Workflow completed successfully")

        except Exception as e:
            logger.error(f"[{self.workflow_id}] Workflow execution failed: {e}")
            self.state = OrchestratorState.FAILED
            execution_log.append({"event": "workflow_failed", "error": str(e), "time": time.time()})
            raise

        finally:
            end_time = time.time()
            total_time = end_time - start_time

            logger.info(
                f"[{self.workflow_id}] Workflow {self.state.value}. "
                f"Total time: {total_time:.2f}s, "
                f"Completed steps: {len(self.completed_steps)}/{len(self.steps)}, "
                f"Failed steps: {len(self.failed_steps)}"
            )

        # Build final result
        return {
            "workflow_result": {
                "workflow_id": self.workflow_id,
                "state": self.state.value,
                "total_steps": len(self.steps),
                "completed_steps": len(self.completed_steps),
                "failed_steps": len(self.failed_steps),
                "execution_time": total_time,
                "context": self.context,
            },
            "execution_log": execution_log,
            "failed_steps": list(self.failed_steps),
            "step_results": {step_id: result for step_id, result in self.step_results.items()},
        }

    def get_execution_graph(self) -> Dict[str, Any]:
        """Get a visual representation of the execution graph."""
        if self.dag is None:
            return {}

        graph_data = {
            "nodes": [],
            "edges": [],
        }

        for step_id in self.steps:
            step = self.steps[step_id]
            status = "pending"
            if step_id in self.completed_steps:
                status = "completed"
            elif step_id in self.failed_steps:
                status = "failed"
            elif step_id in self.running_steps:
                status = "running"

            graph_data["nodes"].append(
                {
                    "id": step_id,
                    "name": step.name,
                    "status": status,
                    "dependencies": step.dependencies,
                }
            )

        for edge in self.dag.edges():
            graph_data["edges"].append({"from": edge[0], "to": edge[1]})

        return graph_data

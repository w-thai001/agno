"""
Meta-FSA Orchestrator

The master coordinator that manages and orchestrates multiple FSAs:
- Coordinates parallel and sequential FSA execution
- Manages dependencies between FSAs
- Intelligent routing and task delegation
- Monitors FSA execution and handles failures
- Provides unified interface for complex multi-FSA workflows

This is the CRITICAL component that enables all other FSAs to work together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class OrchestratorState(str, Enum):
    """States for the Meta-FSA Orchestrator"""
    INITIAL = "initial"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    AGGREGATING = "aggregating"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class FSADependency(BaseModel):
    """Represents a dependency between FSAs"""
    fsa_id: str
    depends_on: List[str]  # List of FSA IDs this FSA depends on
    execution_mode: str = "sequential"  # "sequential" or "parallel"


class FSAExecutionPlan(BaseModel):
    """Execution plan for orchestrating multiple FSAs"""
    plan_id: str
    execution_order: List[List[str]]  # List of FSA ID groups (each group runs in parallel)
    dependencies: Dict[str, List[str]]  # FSA ID -> list of dependency FSA IDs
    estimated_duration: float = 0.0
    priority: int = 1


class OrchestratorResult(BaseModel):
    """Result of orchestrator execution"""
    orchestrator_id: str
    success: bool
    fsa_results: Dict[str, FSAExecutionResult]
    execution_plan: FSAExecutionPlan
    total_execution_time: float
    failed_fsas: List[str] = []
    successful_fsas: List[str] = []
    error_message: Optional[str] = None


@dataclass
class MetaFSAOrchestrator(FSA):
    """
    Meta-FSA Orchestrator - Master Coordinator

    Coordinates multiple FSAs with:
    - Dependency management
    - Parallel and sequential execution
    - Intelligent task routing
    - Failure handling and recovery
    - Unified monitoring and reporting

    Example:
        ```python
        orchestrator = MetaFSAOrchestrator(name="TaskOrchestrator")

        # Register FSAs
        orchestrator.register_fsa(code_builder_fsa)
        orchestrator.register_fsa(validator_fsa, depends_on=[code_builder_fsa.fsa_id])

        # Execute
        result = orchestrator.run({"task": "Build and validate feature X"})
        ```
    """

    # Registered FSAs
    fsas: Dict[str, FSA] = field(default_factory=dict)

    # Dependencies between FSAs
    dependencies: Dict[str, List[str]] = field(default_factory=dict)

    # Execution results
    fsa_results: Dict[str, FSAExecutionResult] = field(default_factory=dict)

    # Execution plan
    execution_plan: Optional[FSAExecutionPlan] = None

    # Configuration
    allow_partial_success: bool = True
    parallel_execution: bool = True
    max_parallel_fsas: int = 5
    retry_failed_fsas: bool = True
    max_retries: int = 2

    # Optional agent for intelligent decision making
    orchestrator_agent: Optional[Agent] = None

    def __post_init__(self):
        """Initialize orchestrator with custom states"""
        self.initial_state = OrchestratorState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {
            OrchestratorState.SUCCESS,
            OrchestratorState.FAILED,
            OrchestratorState.PARTIAL_SUCCESS
        }
        self.state_history = [self.current_state]

        # Define orchestrator transitions
        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"MetaFSAOrchestrator {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup state transitions for the orchestrator"""
        # INITIAL -> ANALYZING
        self.add_transition(
            OrchestratorState.INITIAL,
            OrchestratorState.ANALYZING,
            action=self._analyze_task,
            description="Analyze incoming task and context"
        )

        # ANALYZING -> PLANNING
        self.add_transition(
            OrchestratorState.ANALYZING,
            OrchestratorState.PLANNING,
            condition=lambda ctx: ctx.get("analysis_complete", False),
            action=self._create_execution_plan,
            description="Create FSA execution plan"
        )

        # PLANNING -> EXECUTING
        self.add_transition(
            OrchestratorState.PLANNING,
            OrchestratorState.EXECUTING,
            condition=lambda ctx: ctx.get("plan_ready", False),
            action=self._execute_plan,
            description="Execute FSAs according to plan"
        )

        # EXECUTING -> MONITORING
        self.add_transition(
            OrchestratorState.EXECUTING,
            OrchestratorState.MONITORING,
            condition=lambda ctx: ctx.get("execution_started", False),
            action=self._monitor_execution,
            description="Monitor FSA execution"
        )

        # MONITORING -> AGGREGATING
        self.add_transition(
            OrchestratorState.MONITORING,
            OrchestratorState.AGGREGATING,
            condition=lambda ctx: ctx.get("all_fsas_complete", False),
            action=self._aggregate_results,
            description="Aggregate results from all FSAs"
        )

        # AGGREGATING -> SUCCESS/FAILED/PARTIAL_SUCCESS
        self.add_transition(
            OrchestratorState.AGGREGATING,
            OrchestratorState.SUCCESS,
            condition=lambda ctx: ctx.get("all_successful", False),
            description="All FSAs succeeded"
        )

        self.add_transition(
            OrchestratorState.AGGREGATING,
            OrchestratorState.PARTIAL_SUCCESS,
            condition=lambda ctx: ctx.get("partial_success", False) and self.allow_partial_success,
            description="Some FSAs succeeded"
        )

        self.add_transition(
            OrchestratorState.AGGREGATING,
            OrchestratorState.FAILED,
            condition=lambda ctx: ctx.get("all_failed", False) or (
                ctx.get("partial_success", False) and not self.allow_partial_success
            ),
            description="FSAs failed"
        )

    def register_fsa(
        self,
        fsa: FSA,
        depends_on: Optional[List[str]] = None,
        priority: int = 1
    ) -> str:
        """
        Register an FSA with the orchestrator

        Args:
            fsa: FSA instance to register
            depends_on: List of FSA IDs this FSA depends on
            priority: Execution priority (higher = earlier)

        Returns:
            FSA ID
        """
        fsa_id = fsa.fsa_id
        self.fsas[fsa_id] = fsa
        self.dependencies[fsa_id] = depends_on or []

        if self.debug_mode:
            logger.debug(f"Registered FSA {fsa.name} (ID: {fsa_id})")

        return fsa_id

    def unregister_fsa(self, fsa_id: str) -> bool:
        """
        Unregister an FSA

        Args:
            fsa_id: ID of FSA to unregister

        Returns:
            True if unregistered, False if not found
        """
        if fsa_id in self.fsas:
            del self.fsas[fsa_id]
            if fsa_id in self.dependencies:
                del self.dependencies[fsa_id]
            return True
        return False

    def _analyze_task(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the incoming task and determine which FSAs are needed"""
        task = context.get("task", "")

        if self.debug_mode:
            logger.debug(f"Analyzing task: {task}")

        # Use agent for intelligent analysis if available
        if self.orchestrator_agent:
            analysis_prompt = f"""
            Analyze this task and determine which FSAs should be used:
            Task: {task}

            Available FSAs: {[fsa.name for fsa in self.fsas.values()]}

            Provide analysis of:
            1. Which FSAs are needed
            2. Optimal execution order
            3. Expected dependencies
            """
            # Agent would analyze and update context
            # For now, mark as complete
            pass

        context["analysis_complete"] = True
        context["required_fsas"] = list(self.fsas.keys())  # Default: use all registered FSAs

        return context

    def _create_execution_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution plan based on FSA dependencies"""
        required_fsa_ids = context.get("required_fsas", list(self.fsas.keys()))

        # Build execution order using topological sort
        execution_order = self._topological_sort(required_fsa_ids)

        self.execution_plan = FSAExecutionPlan(
            plan_id=str(uuid4()),
            execution_order=execution_order,
            dependencies=self.dependencies
        )

        context["plan_ready"] = True
        context["execution_plan"] = self.execution_plan

        if self.debug_mode:
            logger.debug(f"Created execution plan: {len(execution_order)} stages")

        return context

    def _topological_sort(self, fsa_ids: List[str]) -> List[List[str]]:
        """
        Perform topological sort to determine execution order
        Returns list of FSA ID groups (each group can run in parallel)
        """
        # Build dependency graph
        in_degree = {fsa_id: 0 for fsa_id in fsa_ids}
        graph = {fsa_id: [] for fsa_id in fsa_ids}

        for fsa_id in fsa_ids:
            for dep_id in self.dependencies.get(fsa_id, []):
                if dep_id in fsa_ids:
                    graph[dep_id].append(fsa_id)
                    in_degree[fsa_id] += 1

        # Kahn's algorithm for topological sort
        execution_order = []
        queue = [fsa_id for fsa_id in fsa_ids if in_degree[fsa_id] == 0]

        while queue:
            # All FSAs in current queue can run in parallel
            current_level = queue[:]
            execution_order.append(current_level)
            queue = []

            for fsa_id in current_level:
                for dependent_id in graph[fsa_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return execution_order

    def _execute_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute FSAs according to the plan"""
        if not self.execution_plan:
            raise ValueError("No execution plan available")

        context["execution_started"] = True
        context["completed_fsas"] = []
        context["failed_fsas"] = []

        return context

    def _monitor_execution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor FSA execution and handle results"""
        if not self.execution_plan:
            raise ValueError("No execution plan available")

        # Execute each stage of the plan
        for stage_num, fsa_ids_in_stage in enumerate(self.execution_plan.execution_order):
            if self.debug_mode:
                logger.debug(f"Executing stage {stage_num + 1}/{len(self.execution_plan.execution_order)}")

            if self.parallel_execution and len(fsa_ids_in_stage) > 1:
                # Execute FSAs in parallel
                stage_results = self._execute_parallel(fsa_ids_in_stage, context)
            else:
                # Execute FSAs sequentially
                stage_results = self._execute_sequential(fsa_ids_in_stage, context)

            # Update results
            self.fsa_results.update(stage_results)

            # Check for failures
            for fsa_id, result in stage_results.items():
                if result.success:
                    context["completed_fsas"].append(fsa_id)
                else:
                    context["failed_fsas"].append(fsa_id)

                    # Handle failure
                    if not self.allow_partial_success:
                        logger.error(f"FSA {fsa_id} failed, stopping execution")
                        context["all_fsas_complete"] = True
                        return context

        context["all_fsas_complete"] = True
        return context

    def _execute_parallel(
        self,
        fsa_ids: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, FSAExecutionResult]:
        """Execute multiple FSAs in parallel"""
        results = {}

        with ThreadPoolExecutor(max_workers=min(len(fsa_ids), self.max_parallel_fsas)) as executor:
            future_to_fsa = {
                executor.submit(self._execute_single_fsa, fsa_id, context): fsa_id
                for fsa_id in fsa_ids
            }

            for future in as_completed(future_to_fsa):
                fsa_id = future_to_fsa[future]
                try:
                    result = future.result()
                    results[fsa_id] = result
                except Exception as e:
                    logger.error(f"FSA {fsa_id} execution failed: {e}")
                    results[fsa_id] = FSAExecutionResult(
                        fsa_id=fsa_id,
                        fsa_name=self.fsas[fsa_id].name,
                        final_state="failed",
                        success=False,
                        error=str(e)
                    )

        return results

    def _execute_sequential(
        self,
        fsa_ids: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, FSAExecutionResult]:
        """Execute FSAs sequentially"""
        results = {}

        for fsa_id in fsa_ids:
            try:
                result = self._execute_single_fsa(fsa_id, context)
                results[fsa_id] = result
            except Exception as e:
                logger.error(f"FSA {fsa_id} execution failed: {e}")
                results[fsa_id] = FSAExecutionResult(
                    fsa_id=fsa_id,
                    fsa_name=self.fsas[fsa_id].name,
                    final_state="failed",
                    success=False,
                    error=str(e)
                )

        return results

    def _execute_single_fsa(
        self,
        fsa_id: str,
        context: Dict[str, Any]
    ) -> FSAExecutionResult:
        """Execute a single FSA"""
        fsa = self.fsas[fsa_id]

        if self.debug_mode:
            logger.debug(f"Executing FSA: {fsa.name}")

        # Prepare FSA context (include outputs from dependencies)
        fsa_context = context.copy()
        for dep_id in self.dependencies.get(fsa_id, []):
            if dep_id in self.fsa_results:
                dep_result = self.fsa_results[dep_id]
                fsa_context[f"dep_{dep_id}_output"] = dep_result.output

        # Execute FSA
        result = fsa.run(initial_context=fsa_context)

        return result

    def _aggregate_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from all FSAs"""
        successful_fsas = context.get("completed_fsas", [])
        failed_fsas = context.get("failed_fsas", [])

        total_fsas = len(successful_fsas) + len(failed_fsas)

        if len(successful_fsas) == total_fsas:
            context["all_successful"] = True
        elif len(failed_fsas) == total_fsas:
            context["all_failed"] = True
        else:
            context["partial_success"] = True

        context["aggregated_output"] = {
            "successful_fsas": successful_fsas,
            "failed_fsas": failed_fsas,
            "results": {fsa_id: result.output for fsa_id, result in self.fsa_results.items()}
        }

        return context

    def run(self, initial_context: Optional[Dict[str, Any]] = None) -> OrchestratorResult:
        """
        Run the orchestrator

        Args:
            initial_context: Initial context including task description

        Returns:
            OrchestratorResult with execution details
        """
        import time
        start_time = time.time()

        # Execute base FSA run
        base_result = super().run(initial_context)

        execution_time = time.time() - start_time

        # Build orchestrator result
        return OrchestratorResult(
            orchestrator_id=self.fsa_id,
            success=base_result.success,
            fsa_results=self.fsa_results,
            execution_plan=self.execution_plan or FSAExecutionPlan(
                plan_id="none",
                execution_order=[],
                dependencies={}
            ),
            total_execution_time=execution_time,
            successful_fsas=self.context.get("completed_fsas", []),
            failed_fsas=self.context.get("failed_fsas", []),
            error_message=base_result.error
        )

    def get_execution_summary(self) -> str:
        """Get a human-readable summary of execution"""
        summary = f"Orchestrator: {self.name}\n"
        summary += f"Status: {self.current_state.value}\n"
        summary += f"Registered FSAs: {len(self.fsas)}\n"

        if self.fsa_results:
            summary += f"\nExecution Results:\n"
            for fsa_id, result in self.fsa_results.items():
                fsa_name = self.fsas[fsa_id].name
                status = "✓" if result.success else "✗"
                summary += f"  {status} {fsa_name}: {result.final_state}\n"

        return summary

"""
FSA Pipeline Manager - Dynamic pipeline construction and orchestration

Provides pipeline building, parallel execution, error recovery, caching,
and performance monitoring for FSA workflows.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime
import hashlib
import json

from agno.fsa.registry import FSARegistry, get_registry

logger = logging.getLogger(__name__)


class PipelineStageStatus(Enum):
    """Status of a pipeline stage execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage execution"""
    stage_name: str
    status: PipelineStageStatus
    output: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if stage completed successfully"""
        return self.status == PipelineStageStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "output": str(self.output) if self.output is not None else None,
            "error": str(self.error) if self.error else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class PipelineExecutionResult:
    """Result of complete pipeline execution"""
    pipeline_id: str
    status: str
    stage_results: List[PipelineStageResult]
    total_duration_ms: float
    start_time: datetime
    end_time: datetime
    success_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """Check if entire pipeline succeeded"""
        return all(stage.is_successful() for stage in self.stage_results)

    def get_stage_result(self, stage_name: str) -> Optional[PipelineStageResult]:
        """Get result for a specific stage"""
        for result in self.stage_results:
            if result.stage_name == stage_name:
                return result
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "stage_results": [stage.to_dict() for stage in self.stage_results],
            "total_duration_ms": self.total_duration_ms,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "success_rate": self.success_rate,
            "metadata": self.metadata,
        }


@dataclass
class PipelineStage:
    """Represents a single stage in an FSA pipeline"""
    name: str
    fsa_module_name: Optional[str] = None
    function: Optional[Callable] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    retry_config: Optional[Dict[str, Any]] = None
    timeout_ms: Optional[int] = None
    parallel: bool = False

    def __post_init__(self):
        """Validate stage configuration"""
        if self.fsa_module_name is None and self.function is None:
            raise ValueError(
                f"Pipeline stage '{self.name}' must have either fsa_module_name or function"
            )

        # Default retry config
        if self.retry_config is None:
            self.retry_config = {
                "max_retries": 3,
                "backoff_ms": 1000,
                "backoff_multiplier": 2,
            }


class FSAPipeline:
    """
    Represents an FSA execution pipeline with stages and dependencies

    Features:
    - Stage dependency management
    - Parallel execution for independent stages
    - Error handling and retry logic
    - Pipeline caching
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        registry: Optional[FSARegistry] = None,
    ):
        self.name = name
        self.description = description
        self.registry = registry or get_registry()
        self.stages: Dict[str, PipelineStage] = {}
        self._stage_order: List[str] = []
        self._logger = logging.getLogger(f"{__name__}.FSAPipeline.{name}")

    def add_stage(
        self,
        name: str,
        fsa_module_name: Optional[str] = None,
        function: Optional[Callable] = None,
        inputs: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
        parallel: bool = False,
    ) -> "FSAPipeline":
        """
        Add a stage to the pipeline

        Args:
            name: Stage name
            fsa_module_name: Name of FSA module to execute
            function: Direct function to execute
            inputs: Input parameters for the stage
            depends_on: List of stage names this depends on
            retry_config: Retry configuration
            timeout_ms: Timeout in milliseconds
            parallel: Whether this stage can run in parallel

        Returns:
            Self for chaining
        """
        if name in self.stages:
            raise ValueError(f"Stage '{name}' already exists in pipeline")

        depends_on = depends_on or []
        inputs = inputs or {}

        # Validate dependencies exist
        for dep in depends_on:
            if dep not in self.stages:
                self._logger.warning(
                    f"Stage '{name}' depends on '{dep}' which doesn't exist yet. "
                    "Ensure correct ordering."
                )

        stage = PipelineStage(
            name=name,
            fsa_module_name=fsa_module_name,
            function=function,
            inputs=inputs,
            depends_on=depends_on,
            retry_config=retry_config,
            timeout_ms=timeout_ms,
            parallel=parallel,
        )

        self.stages[name] = stage
        self._update_stage_order()

        self._logger.debug(f"Added stage '{name}' to pipeline '{self.name}'")
        return self

    def remove_stage(self, name: str) -> "FSAPipeline":
        """Remove a stage from the pipeline"""
        if name not in self.stages:
            raise ValueError(f"Stage '{name}' not found in pipeline")

        # Check if other stages depend on this
        dependents = [
            s.name for s in self.stages.values() if name in s.depends_on
        ]
        if dependents:
            raise ValueError(
                f"Cannot remove stage '{name}': depended on by {dependents}"
            )

        del self.stages[name]
        self._update_stage_order()

        self._logger.debug(f"Removed stage '{name}' from pipeline '{self.name}'")
        return self

    def get_execution_order(self) -> List[List[str]]:
        """
        Get execution order with parallel batches

        Returns:
            List of batches, where each batch contains stages that can run in parallel
        """
        return self._stage_order

    def _update_stage_order(self) -> None:
        """Update execution order using topological sort with parallelization"""
        if not self.stages:
            self._stage_order = []
            return

        # Build dependency graph
        in_degree = {name: len(stage.depends_on) for name, stage in self.stages.items()}
        graph = {name: [] for name in self.stages}

        for name, stage in self.stages.items():
            for dep in stage.depends_on:
                if dep in graph:
                    graph[dep].append(name)

        # Topological sort with batching for parallelization
        batches = []
        while any(degree == 0 for degree in in_degree.values()):
            # Find all stages with no dependencies (can run in parallel)
            batch = [name for name, degree in in_degree.items() if degree == 0]
            if not batch:
                break

            batches.append(batch)

            # Remove these stages and update dependencies
            for name in batch:
                del in_degree[name]
                for dependent in graph[name]:
                    if dependent in in_degree:
                        in_degree[dependent] -= 1

        if in_degree:
            raise ValueError(f"Circular dependency detected in pipeline: {list(in_degree.keys())}")

        self._stage_order = batches

    def __repr__(self) -> str:
        return f"<FSAPipeline '{self.name}': {len(self.stages)} stages>"


class FSAPipelineManager:
    """
    Manages FSA pipeline execution with caching and performance monitoring

    Features:
    - Dynamic pipeline construction
    - Parallel execution of independent stages
    - Error recovery and retry logic
    - Pipeline result caching
    - Performance metrics collection
    """

    def __init__(
        self,
        registry: Optional[FSARegistry] = None,
        max_workers: int = 4,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        self.registry = registry or get_registry()
        self.max_workers = max_workers
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Tuple[PipelineExecutionResult, float]] = {}
        self._metrics: Dict[str, List[float]] = {}
        self._logger = logging.getLogger(f"{__name__}.FSAPipelineManager")

    def execute_pipeline(
        self,
        pipeline: FSAPipeline,
        initial_inputs: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> PipelineExecutionResult:
        """
        Execute an FSA pipeline

        Args:
            pipeline: Pipeline to execute
            initial_inputs: Initial inputs for the pipeline
            use_cache: Whether to use cached results

        Returns:
            PipelineExecutionResult
        """
        initial_inputs = initial_inputs or {}
        pipeline_id = self._generate_pipeline_id(pipeline, initial_inputs)

        # Check cache
        if use_cache and self.enable_caching:
            cached_result = self._get_cached_result(pipeline_id)
            if cached_result:
                self._logger.info(f"Using cached result for pipeline '{pipeline.name}'")
                return cached_result

        self._logger.info(f"Executing pipeline '{pipeline.name}' with {len(pipeline.stages)} stages")
        start_time = datetime.now()
        stage_results: List[PipelineStageResult] = []
        stage_outputs: Dict[str, Any] = {}

        try:
            # Execute stages in batches (parallel where possible)
            execution_order = pipeline.get_execution_order()

            for batch in execution_order:
                batch_results = self._execute_batch(
                    pipeline,
                    batch,
                    stage_outputs,
                    initial_inputs,
                )
                stage_results.extend(batch_results)

                # Update outputs for next batch
                for result in batch_results:
                    stage_outputs[result.stage_name] = result.output

                # Check if any critical stage failed
                if any(not r.is_successful() for r in batch_results):
                    self._logger.warning(f"Pipeline '{pipeline.name}' batch failed, stopping execution")
                    # Mark remaining stages as skipped
                    for remaining_batch in execution_order[execution_order.index(batch) + 1:]:
                        for stage_name in remaining_batch:
                            stage_results.append(PipelineStageResult(
                                stage_name=stage_name,
                                status=PipelineStageStatus.SKIPPED,
                                metadata={"reason": "Previous stage failed"},
                            ))
                    break

            end_time = datetime.now()
            total_duration_ms = (end_time - start_time).total_seconds() * 1000

            # Calculate success rate
            successful_stages = sum(1 for r in stage_results if r.is_successful())
            success_rate = successful_stages / len(stage_results) if stage_results else 0.0

            result = PipelineExecutionResult(
                pipeline_id=pipeline_id,
                status="success" if success_rate == 1.0 else "partial" if success_rate > 0 else "failed",
                stage_results=stage_results,
                total_duration_ms=total_duration_ms,
                start_time=start_time,
                end_time=end_time,
                success_rate=success_rate,
                metadata={"pipeline_name": pipeline.name},
            )

            # Cache result
            if self.enable_caching and result.is_successful():
                self._cache_result(pipeline_id, result)

            # Record metrics
            self._record_metric(pipeline.name, total_duration_ms)

            self._logger.info(
                f"Pipeline '{pipeline.name}' completed: {result.status} "
                f"({total_duration_ms:.2f}ms, {success_rate*100:.1f}% success)"
            )

            return result

        except Exception as e:
            self._logger.error(f"Pipeline '{pipeline.name}' execution failed: {e}", exc_info=True)
            end_time = datetime.now()
            total_duration_ms = (end_time - start_time).total_seconds() * 1000

            return PipelineExecutionResult(
                pipeline_id=pipeline_id,
                status="error",
                stage_results=stage_results,
                total_duration_ms=total_duration_ms,
                start_time=start_time,
                end_time=end_time,
                success_rate=0.0,
                metadata={"error": str(e), "pipeline_name": pipeline.name},
            )

    def _execute_batch(
        self,
        pipeline: FSAPipeline,
        batch: List[str],
        stage_outputs: Dict[str, Any],
        initial_inputs: Dict[str, Any],
    ) -> List[PipelineStageResult]:
        """Execute a batch of stages in parallel"""
        if len(batch) == 1:
            # Single stage, execute directly
            result = self._execute_stage(
                pipeline.stages[batch[0]],
                stage_outputs,
                initial_inputs,
            )
            return [result]

        # Multiple stages, execute in parallel
        results = []
        with ThreadPoolExecutor(max_workers=min(len(batch), self.max_workers)) as executor:
            futures = {
                executor.submit(
                    self._execute_stage,
                    pipeline.stages[stage_name],
                    stage_outputs,
                    initial_inputs,
                ): stage_name
                for stage_name in batch
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    stage_name = futures[future]
                    self._logger.error(f"Stage '{stage_name}' execution failed: {e}")
                    results.append(PipelineStageResult(
                        stage_name=stage_name,
                        status=PipelineStageStatus.FAILED,
                        error=e,
                    ))

        return results

    def _execute_stage(
        self,
        stage: PipelineStage,
        stage_outputs: Dict[str, Any],
        initial_inputs: Dict[str, Any],
    ) -> PipelineStageResult:
        """Execute a single pipeline stage with retry logic"""
        retry_config = stage.retry_config or {}
        max_retries = retry_config.get("max_retries", 3)
        backoff_ms = retry_config.get("backoff_ms", 1000)
        backoff_multiplier = retry_config.get("backoff_multiplier", 2)

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                start_time = datetime.now()

                # Prepare inputs
                inputs = {**initial_inputs, **stage.inputs}

                # Add dependency outputs
                for dep_name in stage.depends_on:
                    if dep_name in stage_outputs:
                        inputs[f"{dep_name}_output"] = stage_outputs[dep_name]

                # Execute stage
                if stage.fsa_module_name:
                    fsa_instance = self.registry.get(stage.fsa_module_name)
                    if hasattr(fsa_instance, 'execute'):
                        output = fsa_instance.execute(**inputs)
                    elif hasattr(fsa_instance, '__call__'):
                        output = fsa_instance(**inputs)
                    else:
                        raise ValueError(
                            f"FSA module '{stage.fsa_module_name}' has no execute method or callable"
                        )
                elif stage.function:
                    output = stage.function(**inputs)
                else:
                    raise ValueError(f"Stage '{stage.name}' has no execution method")

                end_time = datetime.now()
                duration_ms = (end_time - start_time).total_seconds() * 1000

                return PipelineStageResult(
                    stage_name=stage.name,
                    status=PipelineStageStatus.COMPLETED,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                )

            except Exception as e:
                last_error = e
                retry_count += 1

                if retry_count <= max_retries:
                    wait_time_ms = backoff_ms * (backoff_multiplier ** (retry_count - 1))
                    self._logger.warning(
                        f"Stage '{stage.name}' failed (attempt {retry_count}/{max_retries}), "
                        f"retrying in {wait_time_ms}ms: {e}"
                    )
                    time.sleep(wait_time_ms / 1000.0)
                else:
                    self._logger.error(f"Stage '{stage.name}' failed after {max_retries} retries: {e}")

        # All retries exhausted
        return PipelineStageResult(
            stage_name=stage.name,
            status=PipelineStageStatus.FAILED,
            error=last_error,
            retry_count=retry_count - 1,
            metadata={"max_retries": max_retries},
        )

    def _generate_pipeline_id(
        self,
        pipeline: FSAPipeline,
        inputs: Dict[str, Any],
    ) -> str:
        """Generate a unique ID for pipeline + inputs combination"""
        pipeline_repr = {
            "name": pipeline.name,
            "stages": [stage.name for stage in pipeline.stages.values()],
            "inputs": inputs,
        }
        pipeline_str = json.dumps(pipeline_repr, sort_keys=True)
        return hashlib.sha256(pipeline_str.encode()).hexdigest()[:16]

    def _get_cached_result(self, pipeline_id: str) -> Optional[PipelineExecutionResult]:
        """Get cached pipeline result if valid"""
        if pipeline_id in self._cache:
            result, timestamp = self._cache[pipeline_id]
            age = time.time() - timestamp
            if age < self.cache_ttl_seconds:
                return result
            else:
                # Expired, remove from cache
                del self._cache[pipeline_id]
        return None

    def _cache_result(self, pipeline_id: str, result: PipelineExecutionResult) -> None:
        """Cache pipeline execution result"""
        self._cache[pipeline_id] = (result, time.time())

    def _record_metric(self, pipeline_name: str, duration_ms: float) -> None:
        """Record pipeline execution metric"""
        if pipeline_name not in self._metrics:
            self._metrics[pipeline_name] = []
        self._metrics[pipeline_name].append(duration_ms)

    def get_metrics(self, pipeline_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        if pipeline_name:
            if pipeline_name not in self._metrics:
                return {}

            durations = self._metrics[pipeline_name]
            return {
                "pipeline_name": pipeline_name,
                "execution_count": len(durations),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            }

        # All pipelines
        return {
            name: self.get_metrics(name)
            for name in self._metrics
        }

    def clear_cache(self, pipeline_id: Optional[str] = None) -> None:
        """Clear pipeline cache"""
        if pipeline_id:
            if pipeline_id in self._cache:
                del self._cache[pipeline_id]
        else:
            self._cache.clear()
        self._logger.info(f"Cleared cache for: {pipeline_id or 'all pipelines'}")

    def __repr__(self) -> str:
        return (
            f"<FSAPipelineManager: {len(self._cache)} cached, "
            f"{len(self._metrics)} tracked pipelines>"
        )

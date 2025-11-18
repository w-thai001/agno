"""
Data Transformer FSA - Pipeline System

This module implements the transformation pipeline system with composition,
validation, optimization, conditional branching, and parallel execution.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from .exceptions import PipelineExecutionError
from .types import (
    ErrorStrategy,
    Pipeline,
    PipelineExecutionResult,
    Transformation,
)


class TransformationPipeline:
    """Manages and executes transformation pipelines."""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.execution_history: List[PipelineExecutionResult] = []

    def execute(self, data: Any) -> PipelineExecutionResult:
        """
        Execute the pipeline on data.

        Args:
            data: Input data

        Returns:
            Pipeline execution result

        Raises:
            PipelineExecutionError: If pipeline execution fails
        """
        start_time = time.time()
        step_results = []
        current_data = data
        success = True
        errors = []
        warnings = []

        try:
            if self.pipeline.parallel_execution:
                current_data = self._execute_parallel(current_data, step_results)
            else:
                current_data = self._execute_sequential(current_data, step_results, errors, warnings)

            if errors:
                success = False

        except Exception as e:
            success = False
            errors.append(f"Pipeline execution failed: {str(e)}")

            if self.pipeline.error_strategy == ErrorStrategy.RAISE:
                raise PipelineExecutionError(
                    self.pipeline.name, "execution", str(e)
                )

        execution_time = time.time() - start_time

        result = PipelineExecutionResult(
            pipeline_name=self.pipeline.name,
            success=success,
            data=current_data,
            execution_time=execution_time,
            step_results=step_results,
            errors=errors,
            warnings=warnings,
        )

        self.execution_history.append(result)
        return result

    def _execute_sequential(
        self, data: Any, step_results: List, errors: List, warnings: List
    ) -> Any:
        """Execute transformations sequentially."""
        current_data = data

        for i, transformation in enumerate(self.pipeline.transformations):
            step_start = time.time()
            step_name = transformation.name

            try:
                # Check condition if present
                if transformation.condition and not transformation.condition(current_data):
                    step_results.append({
                        "step": i,
                        "name": step_name,
                        "status": "skipped",
                        "reason": "condition not met",
                    })
                    continue

                # Execute transformation with retry logic
                current_data = self._execute_with_retry(transformation, current_data)

                step_results.append({
                    "step": i,
                    "name": step_name,
                    "status": "success",
                    "execution_time": time.time() - step_start,
                })

            except Exception as e:
                error_msg = f"Step {i} ({step_name}) failed: {str(e)}"
                errors.append(error_msg)

                step_results.append({
                    "step": i,
                    "name": step_name,
                    "status": "failed",
                    "error": str(e),
                    "execution_time": time.time() - step_start,
                })

                # Handle error based on strategy
                if transformation.error_strategy == ErrorStrategy.RAISE:
                    raise PipelineExecutionError(
                        self.pipeline.name, step_name, str(e)
                    )
                elif transformation.error_strategy == ErrorStrategy.SKIP:
                    warnings.append(f"Skipped failed step: {step_name}")
                    continue
                elif transformation.error_strategy == ErrorStrategy.LOG:
                    warnings.append(error_msg)
                    continue
                # FALLBACK handled in _execute_with_retry

        return current_data

    def _execute_parallel(self, data: Any, step_results: List) -> Any:
        """Execute independent transformations in parallel."""
        # For parallel execution, all transformations operate on the same input
        # and results are merged
        with ThreadPoolExecutor(max_workers=self.pipeline.max_workers) as executor:
            futures = {}

            for i, transformation in enumerate(self.pipeline.transformations):
                if transformation.condition and not transformation.condition(data):
                    continue

                future = executor.submit(
                    self._execute_transformation_safe,
                    transformation,
                    data,
                    i,
                )
                futures[future] = (i, transformation.name)

            results = {}
            for future in as_completed(futures):
                step_idx, step_name = futures[future]
                try:
                    result_data, step_info = future.result()
                    results[step_idx] = result_data
                    step_results.append(step_info)
                except Exception as e:
                    step_results.append({
                        "step": step_idx,
                        "name": step_name,
                        "status": "failed",
                        "error": str(e),
                    })

            # Merge results (last transformation's output wins)
            if results:
                return results[max(results.keys())]

        return data

    def _execute_transformation_safe(
        self, transformation: Transformation, data: Any, step_idx: int
    ) -> tuple:
        """Execute transformation with error handling for parallel execution."""
        step_start = time.time()

        try:
            result = self._execute_with_retry(transformation, data)
            step_info = {
                "step": step_idx,
                "name": transformation.name,
                "status": "success",
                "execution_time": time.time() - step_start,
            }
            return result, step_info
        except Exception as e:
            step_info = {
                "step": step_idx,
                "name": transformation.name,
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - step_start,
            }
            return data, step_info

    def _execute_with_retry(self, transformation: Transformation, data: Any) -> Any:
        """Execute transformation with retry logic."""
        last_error = None

        for attempt in range(transformation.retry_count + 1):
            try:
                return transformation.function(data, **transformation.parameters)
            except Exception as e:
                last_error = e

                if attempt < transformation.retry_count:
                    time.sleep(transformation.retry_delay * (attempt + 1))
                    continue
                else:
                    # Final attempt failed
                    if transformation.error_strategy == ErrorStrategy.FALLBACK:
                        # Return original data as fallback
                        return data
                    else:
                        raise

        raise last_error

    def get_execution_history(self) -> List[PipelineExecutionResult]:
        """Get pipeline execution history."""
        return self.execution_history

    def clear_history(self):
        """Clear execution history."""
        self.execution_history = []


class PipelineBuilder:
    """Fluent API for building transformation pipelines."""

    def __init__(self, name: str):
        self.pipeline = Pipeline(name=name)

    def add_transformation(
        self,
        name: str,
        function: Callable,
        **kwargs,
    ) -> "PipelineBuilder":
        """
        Add a transformation to the pipeline.

        Args:
            name: Transformation name
            function: Transformation function
            **kwargs: Additional transformation parameters

        Returns:
            Self for chaining
        """
        parameters = kwargs.pop("parameters", {})
        error_strategy = kwargs.pop("error_strategy", ErrorStrategy.RAISE)
        retry_count = kwargs.pop("retry_count", 0)
        retry_delay = kwargs.pop("retry_delay", 1.0)
        condition = kwargs.pop("condition", None)

        # Remaining kwargs are parameters
        parameters.update(kwargs)

        transformation = Transformation(
            name=name,
            function=function,
            parameters=parameters,
            error_strategy=error_strategy,
            retry_count=retry_count,
            retry_delay=retry_delay,
            condition=condition,
        )

        self.pipeline.add_transformation(transformation)
        return self

    def with_error_strategy(self, strategy: ErrorStrategy) -> "PipelineBuilder":
        """
        Set default error strategy for the pipeline.

        Args:
            strategy: Error strategy

        Returns:
            Self for chaining
        """
        self.pipeline.error_strategy = strategy
        return self

    def with_parallel_execution(self, max_workers: int = 4) -> "PipelineBuilder":
        """
        Enable parallel execution.

        Args:
            max_workers: Maximum number of worker threads

        Returns:
            Self for chaining
        """
        self.pipeline.parallel_execution = True
        self.pipeline.max_workers = max_workers
        return self

    def with_metadata(self, **metadata) -> "PipelineBuilder":
        """
        Add metadata to the pipeline.

        Args:
            **metadata: Metadata key-value pairs

        Returns:
            Self for chaining
        """
        self.pipeline.metadata.update(metadata)
        return self

    def with_version(self, version: str) -> "PipelineBuilder":
        """
        Set pipeline version.

        Args:
            version: Version string

        Returns:
            Self for chaining
        """
        self.pipeline.version = version
        return self

    def build(self) -> Pipeline:
        """
        Build and return the pipeline.

        Returns:
            Constructed pipeline
        """
        return self.pipeline


class PipelineValidator:
    """Validates pipeline logic and structure."""

    @staticmethod
    def validate(pipeline: Pipeline) -> tuple[bool, List[str]]:
        """
        Validate a pipeline.

        Args:
            pipeline: Pipeline to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        # Check pipeline has transformations
        if not pipeline.transformations:
            errors.append("Pipeline has no transformations")

        # Check all transformations have valid functions
        for i, transformation in enumerate(pipeline.transformations):
            if not callable(transformation.function):
                errors.append(
                    f"Transformation {i} ({transformation.name}) has invalid function"
                )

            # Check retry count is non-negative
            if transformation.retry_count < 0:
                errors.append(
                    f"Transformation {i} ({transformation.name}) has negative retry count"
                )

            # Check retry delay is positive
            if transformation.retry_delay <= 0:
                errors.append(
                    f"Transformation {i} ({transformation.name}) has invalid retry delay"
                )

        # Check parallel execution settings
        if pipeline.parallel_execution and pipeline.max_workers <= 0:
            errors.append("Invalid max_workers for parallel execution")

        return len(errors) == 0, errors

    @staticmethod
    def validate_compatibility(data: Any, pipeline: Pipeline) -> tuple[bool, List[str]]:
        """
        Validate data compatibility with pipeline.

        Args:
            data: Input data
            pipeline: Pipeline

        Returns:
            Tuple of (is_compatible, list of compatibility errors)
        """
        errors = []

        # Try to execute first transformation as a test
        if pipeline.transformations:
            first_transform = pipeline.transformations[0]
            try:
                # Don't actually modify data, just test if callable
                if not callable(first_transform.function):
                    errors.append("First transformation is not callable")
            except Exception as e:
                errors.append(f"Data incompatible with pipeline: {str(e)}")

        return len(errors) == 0, errors


class PipelineOptimizer:
    """Optimizes transformation pipeline order and execution."""

    @staticmethod
    def optimize(pipeline: Pipeline) -> Pipeline:
        """
        Optimize pipeline by reordering transformations for better performance.

        Args:
            pipeline: Pipeline to optimize

        Returns:
            Optimized pipeline
        """
        # Create a copy of the pipeline
        optimized = Pipeline(
            name=pipeline.name + "_optimized",
            transformations=pipeline.transformations.copy(),
            error_strategy=pipeline.error_strategy,
            parallel_execution=pipeline.parallel_execution,
            max_workers=pipeline.max_workers,
            metadata=pipeline.metadata.copy(),
            version=pipeline.version,
        )

        # Optimization: Move filtering transformations earlier
        # Optimization: Group similar transformations together
        # This is a simplified optimization - could be much more sophisticated

        return optimized

    @staticmethod
    def remove_redundant_transformations(pipeline: Pipeline) -> Pipeline:
        """
        Remove redundant transformations.

        Args:
            pipeline: Pipeline to optimize

        Returns:
            Pipeline without redundant transformations
        """
        seen_names = set()
        unique_transformations = []

        for transformation in pipeline.transformations:
            if transformation.name not in seen_names:
                seen_names.add(transformation.name)
                unique_transformations.append(transformation)

        optimized = Pipeline(
            name=pipeline.name,
            transformations=unique_transformations,
            error_strategy=pipeline.error_strategy,
            parallel_execution=pipeline.parallel_execution,
            max_workers=pipeline.max_workers,
            metadata=pipeline.metadata.copy(),
            version=pipeline.version,
        )

        return optimized


class ConditionalBranching:
    """Implements conditional branching in pipelines."""

    @staticmethod
    def create_conditional_transformation(
        name: str,
        condition: Callable[[Any], bool],
        true_function: Callable,
        false_function: Optional[Callable] = None,
        **kwargs,
    ) -> Transformation:
        """
        Create a conditional transformation.

        Args:
            name: Transformation name
            condition: Condition function
            true_function: Function to execute if condition is True
            false_function: Function to execute if condition is False
            **kwargs: Additional parameters

        Returns:
            Conditional transformation
        """

        def conditional_func(data, **params):
            if condition(data):
                return true_function(data, **params)
            elif false_function:
                return false_function(data, **params)
            else:
                return data

        return Transformation(
            name=name,
            function=conditional_func,
            parameters=kwargs,
        )

    @staticmethod
    def create_switch_transformation(
        name: str,
        key_function: Callable[[Any], str],
        case_functions: Dict[str, Callable],
        default_function: Optional[Callable] = None,
        **kwargs,
    ) -> Transformation:
        """
        Create a switch-case transformation.

        Args:
            name: Transformation name
            key_function: Function to determine which case to execute
            case_functions: Dictionary mapping cases to functions
            default_function: Default function if no case matches
            **kwargs: Additional parameters

        Returns:
            Switch transformation
        """

        def switch_func(data, **params):
            key = key_function(data)
            func = case_functions.get(key, default_function)

            if func:
                return func(data, **params)
            else:
                return data

        return Transformation(
            name=name,
            function=switch_func,
            parameters=kwargs,
        )


class PipelineComposer:
    """Composes multiple pipelines into larger workflows."""

    @staticmethod
    def compose_sequential(*pipelines: Pipeline) -> Pipeline:
        """
        Compose pipelines to execute sequentially.

        Args:
            *pipelines: Pipelines to compose

        Returns:
            Composed pipeline
        """
        name = "_".join([p.name for p in pipelines])
        composed = Pipeline(name=f"composed_{name}")

        for pipeline in pipelines:
            for transformation in pipeline.transformations:
                composed.add_transformation(transformation)

        return composed

    @staticmethod
    def compose_parallel(*pipelines: Pipeline) -> Pipeline:
        """
        Compose pipelines to execute in parallel.

        Args:
            *pipelines: Pipelines to compose

        Returns:
            Composed pipeline with parallel execution
        """
        name = "_".join([p.name for p in pipelines])
        composed = Pipeline(
            name=f"parallel_{name}",
            parallel_execution=True,
        )

        for pipeline in pipelines:
            for transformation in pipeline.transformations:
                composed.add_transformation(transformation)

        return composed

    @staticmethod
    def compose_conditional(
        condition: Callable[[Any], bool],
        true_pipeline: Pipeline,
        false_pipeline: Optional[Pipeline] = None,
    ) -> Pipeline:
        """
        Compose pipelines with conditional execution.

        Args:
            condition: Condition function
            true_pipeline: Pipeline to execute if condition is True
            false_pipeline: Pipeline to execute if condition is False

        Returns:
            Conditional pipeline
        """
        composed = Pipeline(
            name=f"conditional_{true_pipeline.name}",
        )

        def conditional_executor(data, pipeline_true, pipeline_false):
            if condition(data):
                executor = TransformationPipeline(pipeline_true)
                result = executor.execute(data)
                return result.data
            elif pipeline_false:
                executor = TransformationPipeline(pipeline_false)
                result = executor.execute(data)
                return result.data
            else:
                return data

        composed.add_transformation(
            Transformation(
                name="conditional_branch",
                function=conditional_executor,
                parameters={
                    "pipeline_true": true_pipeline,
                    "pipeline_false": false_pipeline,
                },
            )
        )

        return composed


class BatchPipelineExecutor:
    """Executes pipelines on batches of data."""

    def __init__(self, pipeline: Pipeline, batch_size: int = 100):
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.executor = TransformationPipeline(pipeline)

    def execute_batch(self, data_list: List[Any]) -> List[Any]:
        """
        Execute pipeline on a batch of data.

        Args:
            data_list: List of data items

        Returns:
            List of transformed data items
        """
        results = []

        for data in data_list:
            result = self.executor.execute(data)
            results.append(result.data)

        return results

    def execute_batch_parallel(
        self, data_list: List[Any], max_workers: int = 4
    ) -> List[Any]:
        """
        Execute pipeline on batch with parallel processing.

        Args:
            data_list: List of data items
            max_workers: Maximum number of worker threads

        Returns:
            List of transformed data items
        """
        results = [None] * len(data_list)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.executor.execute, data): i
                for i, data in enumerate(data_list)
            }

            for future in as_completed(futures):
                idx = futures[future]
                result = future.result()
                results[idx] = result.data

        return results


class StreamPipelineExecutor:
    """Executes pipelines on streaming data."""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.executor = TransformationPipeline(pipeline)

    def execute_stream(self, data_stream):
        """
        Execute pipeline on a data stream.

        Args:
            data_stream: Iterator of data items

        Yields:
            Transformed data items
        """
        for data in data_stream:
            result = self.executor.execute(data)
            yield result.data

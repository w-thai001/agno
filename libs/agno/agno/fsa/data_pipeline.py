"""Data Pipeline FSA - Stream processing with backpressure handling and multi-stage composition."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, Generic, List, Optional, TypeVar, Union

from agno.utils.log import logger

T = TypeVar("T")
U = TypeVar("U")


class PipelineState(Enum):
    """Pipeline execution states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class TransformationType(Enum):
    """Transformation stage types."""

    MAP = "map"
    FILTER = "filter"
    REDUCE = "reduce"
    FLATMAP = "flatmap"
    BATCH = "batch"


@dataclass
class PipelineMetrics:
    """Pipeline execution metrics."""

    items_processed: int = 0
    items_failed: int = 0
    items_in_dlq: int = 0
    total_processing_time: float = 0.0
    throughput: float = 0.0
    backpressure_events: int = 0
    stage_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def update_throughput(self) -> None:
        """Calculate current throughput (items/second)."""
        if self.start_time and self.items_processed > 0:
            elapsed = (self.end_time or time.time()) - self.start_time
            self.throughput = self.items_processed / elapsed if elapsed > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        return {
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "items_in_dlq": self.items_in_dlq,
            "total_processing_time": self.total_processing_time,
            "throughput": self.throughput,
            "backpressure_events": self.backpressure_events,
            "stage_metrics": self.stage_metrics,
        }


@dataclass
class PipelineConfig:
    """Pipeline configuration."""

    # Backpressure settings
    max_buffer_size: int = 1000
    backpressure_threshold: float = 0.8  # Trigger backpressure at 80% capacity
    backpressure_cooldown: float = 0.1  # Cooldown period in seconds

    # Batch processing
    batch_size: int = 100
    batch_timeout: float = 5.0  # Max time to wait for batch completion

    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_dlq: bool = True

    # Monitoring
    enable_metrics: bool = True
    metrics_interval: float = 10.0  # Log metrics every N seconds


@dataclass
class PipelineItem(Generic[T]):
    """Item flowing through the pipeline with metadata."""

    data: T
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)


class TransformationStage(Generic[T, U]):
    """A single transformation stage in the pipeline."""

    def __init__(
        self,
        name: str,
        transform_fn: Callable[[T], Union[U, List[U], None]],
        transform_type: TransformationType = TransformationType.MAP,
        is_async: bool = False,
    ):
        self.name = name
        self.transform_fn = transform_fn
        self.transform_type = transform_type
        self.is_async = is_async
        self.metrics = {
            "processed": 0,
            "failed": 0,
            "avg_duration": 0.0,
            "total_duration": 0.0,
        }

    async def process(self, item: PipelineItem[T]) -> Union[List[PipelineItem[U]], None]:
        """Process a single item through this stage."""
        start_time = time.time()
        try:
            if self.is_async:
                result = await self.transform_fn(item.data)
            else:
                result = self.transform_fn(item.data)

            # Handle different transformation types
            if self.transform_type == TransformationType.FILTER:
                # Filter returns boolean or None
                if result:
                    output = [PipelineItem(data=item.data, metadata=item.metadata.copy())]
                else:
                    output = None
            elif self.transform_type == TransformationType.FLATMAP:
                # FlatMap returns list of items
                if isinstance(result, list):
                    output = [
                        PipelineItem(data=r, metadata=item.metadata.copy()) for r in result if r is not None
                    ]
                else:
                    output = None
            elif result is not None:
                # Map/Reduce returns single item
                output = [PipelineItem(data=result, metadata=item.metadata.copy())]
            else:
                output = None

            # Update metrics
            duration = time.time() - start_time
            self.metrics["processed"] += 1
            self.metrics["total_duration"] += duration
            self.metrics["avg_duration"] = self.metrics["total_duration"] / self.metrics["processed"]

            return output

        except Exception as e:
            self.metrics["failed"] += 1
            logger.error(f"Stage {self.name} failed: {e}")
            raise


class DeadLetterQueue:
    """Dead letter queue for failed items."""

    def __init__(self, max_size: int = 10000):
        self.queue: deque = deque(maxlen=max_size)
        self.max_size = max_size

    def add(self, item: PipelineItem, error: Exception, stage: str) -> None:
        """Add failed item to DLQ."""
        self.queue.append(
            {
                "item": item,
                "error": str(error),
                "stage": stage,
                "timestamp": time.time(),
            }
        )

    def get_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve items from DLQ."""
        if limit:
            return list(self.queue)[-limit:]
        return list(self.queue)

    def clear(self) -> None:
        """Clear the DLQ."""
        self.queue.clear()

    def size(self) -> int:
        """Get current DLQ size."""
        return len(self.queue)


class DataPipelineFSA(Generic[T]):
    """
    Finite State Automaton for data pipeline processing.

    Features:
    - Stream processing with backpressure handling
    - Multi-stage transformations (map, filter, reduce, flatmap)
    - Error handling with retries and dead letter queue
    - Pipeline metrics and monitoring
    - Configurable batch processing
    - Composable pipeline stages

    Example:
        >>> pipeline = DataPipelineFSA[int](name="numbers")
        >>> pipeline.add_stage("double", lambda x: x * 2)
        >>> pipeline.add_stage("filter_even", lambda x: x % 2 == 0, TransformationType.FILTER)
        >>> async for result in pipeline.process_stream(data_source):
        ...     print(result)
    """

    def __init__(
        self,
        name: str,
        config: Optional[PipelineConfig] = None,
    ):
        self.name = name
        self.config = config or PipelineConfig()
        self.state = PipelineState.IDLE
        self.stages: List[TransformationStage] = []
        self.metrics = PipelineMetrics()
        self.dlq = DeadLetterQueue() if self.config.enable_dlq else None
        self.buffer: deque = deque(maxlen=self.config.max_buffer_size)
        self._stop_requested = False
        self._pause_requested = False

    def add_stage(
        self,
        name: str,
        transform_fn: Callable,
        transform_type: TransformationType = TransformationType.MAP,
        is_async: bool = False,
    ) -> DataPipelineFSA[T]:
        """Add a transformation stage to the pipeline. Returns self for chaining."""
        stage = TransformationStage(
            name=name,
            transform_fn=transform_fn,
            transform_type=transform_type,
            is_async=is_async,
        )
        self.stages.append(stage)
        return self

    def map(self, name: str, fn: Callable, is_async: bool = False) -> DataPipelineFSA[T]:
        """Add a map transformation stage."""
        return self.add_stage(name, fn, TransformationType.MAP, is_async)

    def filter(self, name: str, fn: Callable, is_async: bool = False) -> DataPipelineFSA[T]:
        """Add a filter transformation stage."""
        return self.add_stage(name, fn, TransformationType.FILTER, is_async)

    def flatmap(self, name: str, fn: Callable, is_async: bool = False) -> DataPipelineFSA[T]:
        """Add a flatmap transformation stage."""
        return self.add_stage(name, fn, TransformationType.FLATMAP, is_async)

    async def _check_backpressure(self) -> bool:
        """Check if backpressure should be applied."""
        buffer_usage = len(self.buffer) / self.config.max_buffer_size
        if buffer_usage >= self.config.backpressure_threshold:
            self.metrics.backpressure_events += 1
            logger.warning(f"Pipeline {self.name}: Backpressure triggered at {buffer_usage:.1%} buffer usage")
            await asyncio.sleep(self.config.backpressure_cooldown)
            return True
        return False

    async def _process_item_through_stages(self, item: PipelineItem[T]) -> Optional[List[PipelineItem]]:
        """Process a single item through all stages."""
        current_items = [item]

        for stage in self.stages:
            next_items = []
            for current_item in current_items:
                retry_count = 0
                while retry_count <= self.config.max_retries:
                    try:
                        result = await stage.process(current_item)
                        if result:
                            next_items.extend(result)
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count > self.config.max_retries:
                            # Final failure - send to DLQ
                            logger.error(f"Item failed after {self.config.max_retries} retries: {e}")
                            if self.dlq:
                                self.dlq.add(current_item, e, stage.name)
                                self.metrics.items_in_dlq += 1
                            self.metrics.items_failed += 1
                            break
                        else:
                            # Retry with delay
                            await asyncio.sleep(self.config.retry_delay)

            current_items = next_items
            if not current_items:
                break

        return current_items if current_items else None

    async def process_stream(
        self,
        data_source: AsyncIterator[T],
        batch_processing: bool = False,
    ) -> AsyncIterator[Any]:
        """
        Process a stream of data through the pipeline.

        Args:
            data_source: Async iterator providing input data
            batch_processing: If True, process items in batches

        Yields:
            Processed items
        """
        self.state = PipelineState.RUNNING
        self.metrics.start_time = time.time()
        batch: List[PipelineItem] = []
        batch_start_time = time.time()

        try:
            async for data in data_source:
                # Check for stop/pause
                if self._stop_requested:
                    logger.info(f"Pipeline {self.name}: Stop requested")
                    break

                while self._pause_requested:
                    self.state = PipelineState.PAUSED
                    await asyncio.sleep(0.1)
                self.state = PipelineState.RUNNING

                # Check backpressure
                await self._check_backpressure()

                # Create pipeline item
                item = PipelineItem(data=data)

                if batch_processing:
                    batch.append(item)
                    batch_time_elapsed = time.time() - batch_start_time

                    # Process batch if full or timeout
                    if len(batch) >= self.config.batch_size or batch_time_elapsed >= self.config.batch_timeout:
                        async for result in self._process_batch(batch):
                            yield result
                        batch = []
                        batch_start_time = time.time()
                else:
                    # Process item immediately
                    start_time = time.time()
                    result = await self._process_item_through_stages(item)
                    processing_time = time.time() - start_time

                    if result:
                        self.metrics.items_processed += 1
                        self.metrics.total_processing_time += processing_time
                        for r in result:
                            yield r.data

            # Process remaining batch items
            if batch_processing and batch:
                async for result in self._process_batch(batch):
                    yield result

        except Exception as e:
            logger.error(f"Pipeline {self.name} error: {e}")
            self.state = PipelineState.ERROR
            raise
        finally:
            self.state = PipelineState.STOPPED
            self.metrics.end_time = time.time()
            self.metrics.update_throughput()
            self._log_final_metrics()

    async def _process_batch(self, batch: List[PipelineItem]) -> AsyncIterator[Any]:
        """Process a batch of items concurrently."""
        logger.debug(f"Processing batch of {len(batch)} items")
        start_time = time.time()

        # Process all items in batch concurrently
        tasks = [self._process_item_through_stages(item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processing_time = time.time() - start_time

        for result in results:
            if isinstance(result, Exception):
                self.metrics.items_failed += 1
                continue
            if result:
                self.metrics.items_processed += len(result)
                self.metrics.total_processing_time += processing_time / len(batch)
                for r in result:
                    yield r.data

    def pause(self) -> None:
        """Pause the pipeline."""
        self._pause_requested = True
        logger.info(f"Pipeline {self.name}: Pause requested")

    def resume(self) -> None:
        """Resume the pipeline."""
        self._pause_requested = False
        logger.info(f"Pipeline {self.name}: Resumed")

    def stop(self) -> None:
        """Stop the pipeline."""
        self._stop_requested = True
        logger.info(f"Pipeline {self.name}: Stop requested")

    def get_metrics(self) -> PipelineMetrics:
        """Get current pipeline metrics."""
        if self.config.enable_metrics:
            self.metrics.update_throughput()
            # Update stage metrics
            for stage in self.stages:
                self.metrics.stage_metrics[stage.name] = stage.metrics.copy()
        return self.metrics

    def _log_final_metrics(self) -> None:
        """Log final metrics after pipeline completion."""
        if not self.config.enable_metrics:
            return

        metrics = self.get_metrics()
        logger.info(f"Pipeline {self.name} completed:")
        logger.info(f"  Items processed: {metrics.items_processed}")
        logger.info(f"  Items failed: {metrics.items_failed}")
        logger.info(f"  Items in DLQ: {metrics.items_in_dlq}")
        logger.info(f"  Throughput: {metrics.throughput:.2f} items/sec")
        logger.info(f"  Backpressure events: {metrics.backpressure_events}")
        logger.info(f"  Total time: {metrics.total_processing_time:.2f}s")

        for stage_name, stage_metrics in metrics.stage_metrics.items():
            logger.info(
                f"  Stage '{stage_name}': "
                f"processed={stage_metrics['processed']}, "
                f"failed={stage_metrics['failed']}, "
                f"avg_duration={stage_metrics['avg_duration']:.4f}s"
            )

    def get_dlq_items(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get items from the dead letter queue."""
        if self.dlq:
            return self.dlq.get_items(limit)
        return []

    def clear_dlq(self) -> None:
        """Clear the dead letter queue."""
        if self.dlq:
            self.dlq.clear()

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = PipelineMetrics()
        for stage in self.stages:
            stage.metrics = {
                "processed": 0,
                "failed": 0,
                "avg_duration": 0.0,
                "total_duration": 0.0,
            }

    def compose(self, other: DataPipelineFSA) -> DataPipelineFSA[T]:
        """
        Compose this pipeline with another pipeline.
        Stages from the other pipeline are added to this pipeline.
        """
        for stage in other.stages:
            self.stages.append(stage)
        logger.info(f"Composed pipeline {other.name} into {self.name}")
        return self

"""Tests for Data Pipeline FSA."""

import asyncio
import pytest
from typing import AsyncIterator, List

from agno.fsa.data_pipeline import (
    DataPipelineFSA,
    DeadLetterQueue,
    PipelineConfig,
    PipelineItem,
    PipelineState,
    TransformationStage,
    TransformationType,
)


# Test fixtures and helpers
async def async_range(start: int, end: int) -> AsyncIterator[int]:
    """Async generator for testing."""
    for i in range(start, end):
        yield i
        await asyncio.sleep(0.001)  # Simulate async I/O


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue."""

    def test_add_and_retrieve(self):
        """Test adding and retrieving items from DLQ."""
        dlq = DeadLetterQueue(max_size=100)
        item = PipelineItem(data=42)
        error = Exception("Test error")

        dlq.add(item, error, "test_stage")

        items = dlq.get_items()
        assert len(items) == 1
        assert items[0]["item"] == item
        assert items[0]["error"] == "Test error"
        assert items[0]["stage"] == "test_stage"

    def test_max_size_limit(self):
        """Test DLQ respects max size limit."""
        dlq = DeadLetterQueue(max_size=3)
        item = PipelineItem(data=1)
        error = Exception("Test")

        for i in range(5):
            dlq.add(PipelineItem(data=i), error, "stage")

        # Should only keep last 3 items
        assert dlq.size() == 3
        items = dlq.get_items()
        assert items[0]["item"].data == 2
        assert items[-1]["item"].data == 4

    def test_clear(self):
        """Test clearing the DLQ."""
        dlq = DeadLetterQueue()
        dlq.add(PipelineItem(data=1), Exception("Test"), "stage")
        dlq.add(PipelineItem(data=2), Exception("Test"), "stage")

        assert dlq.size() == 2
        dlq.clear()
        assert dlq.size() == 0


class TestTransformationStage:
    """Tests for TransformationStage."""

    @pytest.mark.asyncio
    async def test_map_transformation(self):
        """Test map transformation."""
        stage = TransformationStage(
            name="double",
            transform_fn=lambda x: x * 2,
            transform_type=TransformationType.MAP,
        )

        item = PipelineItem(data=5)
        result = await stage.process(item)

        assert result is not None
        assert len(result) == 1
        assert result[0].data == 10

    @pytest.mark.asyncio
    async def test_filter_transformation(self):
        """Test filter transformation."""
        stage = TransformationStage(
            name="filter_even",
            transform_fn=lambda x: x % 2 == 0,
            transform_type=TransformationType.FILTER,
        )

        # Even number should pass
        item1 = PipelineItem(data=4)
        result1 = await stage.process(item1)
        assert result1 is not None
        assert len(result1) == 1
        assert result1[0].data == 4

        # Odd number should be filtered out
        item2 = PipelineItem(data=5)
        result2 = await stage.process(item2)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_flatmap_transformation(self):
        """Test flatmap transformation."""
        stage = TransformationStage(
            name="explode",
            transform_fn=lambda x: [x, x * 2, x * 3],
            transform_type=TransformationType.FLATMAP,
        )

        item = PipelineItem(data=2)
        result = await stage.process(item)

        assert result is not None
        assert len(result) == 3
        assert result[0].data == 2
        assert result[1].data == 4
        assert result[2].data == 6

    @pytest.mark.asyncio
    async def test_async_transformation(self):
        """Test async transformation function."""

        async def async_double(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        stage = TransformationStage(
            name="async_double",
            transform_fn=async_double,
            transform_type=TransformationType.MAP,
            is_async=True,
        )

        item = PipelineItem(data=7)
        result = await stage.process(item)

        assert result is not None
        assert result[0].data == 14

    @pytest.mark.asyncio
    async def test_stage_metrics(self):
        """Test stage metrics tracking."""
        stage = TransformationStage(
            name="test",
            transform_fn=lambda x: x * 2,
            transform_type=TransformationType.MAP,
        )

        for i in range(5):
            await stage.process(PipelineItem(data=i))

        assert stage.metrics["processed"] == 5
        assert stage.metrics["failed"] == 0
        assert stage.metrics["avg_duration"] > 0


class TestDataPipelineFSA:
    """Tests for DataPipelineFSA."""

    @pytest.mark.asyncio
    async def test_simple_pipeline(self):
        """Test simple pipeline with map transformation."""
        pipeline = DataPipelineFSA[int](name="test_pipeline")
        pipeline.map("double", lambda x: x * 2)

        results = []
        async for result in pipeline.process_stream(async_range(1, 6)):
            results.append(result)

        assert results == [2, 4, 6, 8, 10]
        assert pipeline.state == PipelineState.STOPPED
        assert pipeline.metrics.items_processed == 5

    @pytest.mark.asyncio
    async def test_multi_stage_pipeline(self):
        """Test pipeline with multiple stages."""
        pipeline = DataPipelineFSA[int](name="multi_stage")
        pipeline.map("double", lambda x: x * 2)
        pipeline.map("add_ten", lambda x: x + 10)
        pipeline.filter("greater_than_15", lambda x: x > 15)

        results = []
        async for result in pipeline.process_stream(async_range(1, 6)):
            results.append(result)

        # 1->2->12 (filtered), 2->4->14 (filtered), 3->6->16, 4->8->18, 5->10->20
        assert results == [16, 18, 20]

    @pytest.mark.asyncio
    async def test_flatmap_pipeline(self):
        """Test pipeline with flatmap transformation."""
        pipeline = DataPipelineFSA[int](name="flatmap_test")
        pipeline.flatmap("duplicate", lambda x: [x, x])

        results = []
        async for result in pipeline.process_stream(async_range(1, 4)):
            results.append(result)

        assert results == [1, 1, 2, 2, 3, 3]

    @pytest.mark.asyncio
    async def test_error_handling_with_retries(self):
        """Test error handling with retries."""
        call_count = 0

        def failing_transform(x: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first 2 attempts
                raise ValueError("Intentional failure")
            return x * 2

        config = PipelineConfig(max_retries=3, retry_delay=0.01)
        pipeline = DataPipelineFSA[int](name="retry_test", config=config)
        pipeline.map("failing", failing_transform)

        results = []
        async for result in pipeline.process_stream(async_range(1, 2)):
            results.append(result)

        # Should succeed on 3rd retry
        assert results == [2]

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self):
        """Test items are sent to DLQ after max retries."""

        def always_fail(x: int) -> int:
            raise ValueError("Always fails")

        config = PipelineConfig(max_retries=2, retry_delay=0.01, enable_dlq=True)
        pipeline = DataPipelineFSA[int](name="dlq_test", config=config)
        pipeline.map("failing", always_fail)

        results = []
        async for result in pipeline.process_stream(async_range(1, 4)):
            results.append(result)

        assert results == []  # No successful results
        assert pipeline.metrics.items_failed == 3
        assert pipeline.metrics.items_in_dlq == 3

        dlq_items = pipeline.get_dlq_items()
        assert len(dlq_items) == 3

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing mode."""
        config = PipelineConfig(batch_size=3, batch_timeout=1.0)
        pipeline = DataPipelineFSA[int](name="batch_test", config=config)
        pipeline.map("double", lambda x: x * 2)

        results = []
        async for result in pipeline.process_stream(async_range(1, 8), batch_processing=True):
            results.append(result)

        assert len(results) == 7
        assert set(results) == {2, 4, 6, 8, 10, 12, 14}

    @pytest.mark.asyncio
    async def test_backpressure(self):
        """Test backpressure handling."""
        config = PipelineConfig(max_buffer_size=10, backpressure_threshold=0.5)
        pipeline = DataPipelineFSA[int](name="backpressure_test", config=config)
        pipeline.map("slow", lambda x: x)

        results = []
        async for result in pipeline.process_stream(async_range(1, 6)):
            results.append(result)

        # Should complete but may have triggered backpressure
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        """Test pausing and resuming pipeline."""
        pipeline = DataPipelineFSA[int](name="pause_test")
        pipeline.map("double", lambda x: x * 2)

        results = []

        async def process_with_pause():
            count = 0
            async for result in pipeline.process_stream(async_range(1, 11)):
                results.append(result)
                count += 1
                if count == 3:
                    pipeline.pause()
                    await asyncio.sleep(0.05)
                    pipeline.resume()

        await process_with_pause()
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_stop_pipeline(self):
        """Test stopping pipeline mid-execution."""
        pipeline = DataPipelineFSA[int](name="stop_test")
        pipeline.map("double", lambda x: x * 2)

        results = []

        async def process_with_stop():
            count = 0
            async for result in pipeline.process_stream(async_range(1, 100)):
                results.append(result)
                count += 1
                if count == 5:
                    pipeline.stop()

        await process_with_stop()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test metrics are properly collected."""
        config = PipelineConfig(enable_metrics=True)
        pipeline = DataPipelineFSA[int](name="metrics_test", config=config)
        pipeline.map("double", lambda x: x * 2)
        pipeline.filter("even", lambda x: x % 4 == 0)

        results = []
        async for result in pipeline.process_stream(async_range(1, 11)):
            results.append(result)

        metrics = pipeline.get_metrics()
        assert metrics.items_processed > 0
        assert metrics.throughput > 0
        assert "double" in metrics.stage_metrics
        assert "even" in metrics.stage_metrics
        assert metrics.stage_metrics["double"]["processed"] == 10

    @pytest.mark.asyncio
    async def test_pipeline_composition(self):
        """Test composing multiple pipelines."""
        pipeline1 = DataPipelineFSA[int](name="pipe1")
        pipeline1.map("double", lambda x: x * 2)

        pipeline2 = DataPipelineFSA[int](name="pipe2")
        pipeline2.map("add_five", lambda x: x + 5)

        # Compose pipelines
        combined = pipeline1.compose(pipeline2)

        results = []
        async for result in combined.process_stream(async_range(1, 4)):
            results.append(result)

        # Should apply both transformations: double then add 5
        assert results == [7, 9, 11]  # (1*2)+5=7, (2*2)+5=9, (3*2)+5=11

    @pytest.mark.asyncio
    async def test_fluent_api(self):
        """Test fluent API for building pipelines."""
        pipeline = (
            DataPipelineFSA[int](name="fluent_test")
            .map("triple", lambda x: x * 3)
            .filter("greater_than_10", lambda x: x > 10)
            .map("subtract_5", lambda x: x - 5)
        )

        results = []
        async for result in pipeline.process_stream(async_range(1, 6)):
            results.append(result)

        # 1->3 (filtered), 2->6 (filtered), 3->9 (filtered), 4->12->7, 5->15->10
        assert results == [7, 10]

    @pytest.mark.asyncio
    async def test_metadata_preservation(self):
        """Test that metadata is preserved through pipeline stages."""
        pipeline = DataPipelineFSA[int](name="metadata_test")
        pipeline.map("double", lambda x: x * 2)

        # We need to test internal behavior
        item = PipelineItem(data=5, metadata={"source": "test"})
        result = await pipeline._process_item_through_stages(item)

        assert result is not None
        assert result[0].metadata["source"] == "test"

    @pytest.mark.asyncio
    async def test_reset_metrics(self):
        """Test resetting metrics."""
        pipeline = DataPipelineFSA[int](name="reset_test")
        pipeline.map("double", lambda x: x * 2)

        # Process some data
        results = []
        async for result in pipeline.process_stream(async_range(1, 4)):
            results.append(result)

        assert pipeline.metrics.items_processed > 0

        # Reset metrics
        pipeline.reset_metrics()
        assert pipeline.metrics.items_processed == 0
        assert pipeline.metrics.items_failed == 0

    @pytest.mark.asyncio
    async def test_clear_dlq(self):
        """Test clearing dead letter queue."""

        def always_fail(x: int) -> int:
            raise ValueError("Fail")

        config = PipelineConfig(max_retries=1, retry_delay=0.01, enable_dlq=True)
        pipeline = DataPipelineFSA[int](name="clear_dlq_test", config=config)
        pipeline.map("failing", always_fail)

        results = []
        async for result in pipeline.process_stream(async_range(1, 3)):
            results.append(result)

        assert len(pipeline.get_dlq_items()) > 0

        pipeline.clear_dlq()
        assert len(pipeline.get_dlq_items()) == 0

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        """Test pipeline with empty stream."""

        async def empty_stream() -> AsyncIterator[int]:
            return
            yield  # Make it an async generator

        pipeline = DataPipelineFSA[int](name="empty_test")
        pipeline.map("double", lambda x: x * 2)

        results = []
        async for result in pipeline.process_stream(empty_stream()):
            results.append(result)

        assert results == []
        assert pipeline.metrics.items_processed == 0

    @pytest.mark.asyncio
    async def test_none_filtering(self):
        """Test that None results are properly filtered."""
        pipeline = DataPipelineFSA[int](name="none_test")
        pipeline.map("return_none_for_even", lambda x: None if x % 2 == 0 else x)

        results = []
        async for result in pipeline.process_stream(async_range(1, 6)):
            results.append(result)

        # Only odd numbers should pass through
        assert results == [1, 3, 5]

    @pytest.mark.asyncio
    async def test_config_parameters(self):
        """Test various configuration parameters."""
        config = PipelineConfig(
            max_buffer_size=500,
            backpressure_threshold=0.9,
            batch_size=50,
            batch_timeout=2.0,
            max_retries=5,
            retry_delay=0.5,
            enable_dlq=False,
            enable_metrics=False,
        )

        pipeline = DataPipelineFSA[int](name="config_test", config=config)
        assert pipeline.config.max_buffer_size == 500
        assert pipeline.config.batch_size == 50
        assert pipeline.config.max_retries == 5
        assert pipeline.dlq is None  # DLQ disabled

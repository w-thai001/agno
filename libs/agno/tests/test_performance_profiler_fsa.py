"""
Comprehensive test suite for PerformanceProfilerFSA.

Test coverage:
- Basic start/stop profiling
- Execution time accuracy
- Memory tracking
- Event recording
- Nested profiling
- Decorator functionality
- Context manager usage
- Metrics aggregation
- Summary generation
- Thread safety
- Export functionality
- Smoke tests
"""

import json
import threading
import time
from unittest.mock import patch

import pytest

from agno.fsas.performance_profiler_fsa import PerformanceProfilerFSA, ProfileRecord, ProfileEvent


class TestBasicProfiling:
    """Test basic profiling operations."""

    def test_start_stop_profiling(self):
        """Test basic start and stop profiling."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        time.sleep(0.01)
        metrics = profiler.stop_profiling("task1")

        assert metrics["task_id"] == "task1"
        assert metrics["elapsed_time"] is not None
        assert metrics["elapsed_time"] >= 0.01

    def test_stop_without_start(self):
        """Test stopping profiling without starting raises error."""
        profiler = PerformanceProfilerFSA()
        with pytest.raises(ValueError, match="not being profiled"):
            profiler.stop_profiling("nonexistent")

    def test_multiple_tasks(self):
        """Test profiling multiple tasks."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        profiler.start_profiling("task2")
        time.sleep(0.01)
        metrics1 = profiler.stop_profiling("task1")
        metrics2 = profiler.stop_profiling("task2")

        assert metrics1["task_id"] == "task1"
        assert metrics2["task_id"] == "task2"

    def test_is_profiling(self):
        """Test checking if task is being profiled."""
        profiler = PerformanceProfilerFSA()
        assert profiler.is_profiling("task1") is False
        profiler.start_profiling("task1")
        assert profiler.is_profiling("task1") is True
        profiler.stop_profiling("task1")
        assert profiler.is_profiling("task1") is False

    def test_get_active_tasks(self):
        """Test getting active task list."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        profiler.start_profiling("task2")

        active = profiler.get_active_tasks()
        assert "task1" in active
        assert "task2" in active
        assert len(active) == 2


class TestExecutionTiming:
    """Test execution time tracking."""

    def test_elapsed_time_accuracy(self):
        """Test that elapsed time is accurate."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        time.sleep(0.05)
        metrics = profiler.stop_profiling("task1")

        # Allow for some variance
        assert 0.045 <= metrics["elapsed_time"] <= 0.1

    def test_cpu_time_tracking(self):
        """Test CPU time tracking."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        # Do some CPU work
        _ = sum(i * i for i in range(10000))
        metrics = profiler.stop_profiling("task1")

        assert metrics["cpu_time"] is not None
        assert metrics["cpu_time"] >= 0

    def test_multiple_executions_same_task(self):
        """Test profiling same task multiple times."""
        profiler = PerformanceProfilerFSA()

        for _ in range(3):
            profiler.start_profiling("task1")
            time.sleep(0.01)
            profiler.stop_profiling("task1")

        task_metrics = profiler.get_metrics("task1")
        assert task_metrics["executions"] == 3


class TestMemoryTracking:
    """Test memory usage tracking."""

    def test_memory_tracking_enabled(self):
        """Test memory tracking when enabled."""
        profiler = PerformanceProfilerFSA(enable_memory_tracking=True)
        profiler.start_profiling("task1")
        # Allocate some memory
        data = [i for i in range(1000)]
        metrics = profiler.stop_profiling("task1")

        # Memory tracking might not be available without psutil
        if metrics["memory_start"] is not None:
            assert metrics["memory_end"] is not None
            assert metrics["memory_delta"] is not None

    def test_memory_tracking_disabled(self):
        """Test memory tracking when disabled."""
        profiler = PerformanceProfilerFSA(enable_memory_tracking=False)
        profiler.start_profiling("task1")
        metrics = profiler.stop_profiling("task1")

        assert metrics["memory_start"] is None
        assert metrics["memory_end"] is None

    def test_memory_delta_calculation(self):
        """Test memory delta calculation."""
        record = ProfileRecord(
            task_id="test",
            start_time=0,
            memory_start=1000,
            memory_end=2000,
        )
        assert record.memory_delta() == 1000


class TestEventRecording:
    """Test event recording functionality."""

    def test_record_event(self):
        """Test recording custom events."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        profiler.record_event("task1", "checkpoint", {"step": 1})
        profiler.record_event("task1", "checkpoint", {"step": 2})
        metrics = profiler.stop_profiling("task1")

        assert len(metrics["events"]) == 2
        assert metrics["events"][0]["event_type"] == "checkpoint"
        assert metrics["events"][0]["metadata"]["step"] == 1

    def test_record_event_without_metadata(self):
        """Test recording event without metadata."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        profiler.record_event("task1", "milestone")
        metrics = profiler.stop_profiling("task1")

        assert len(metrics["events"]) == 1
        assert metrics["events"][0]["metadata"] == {}

    def test_record_event_inactive_task(self):
        """Test recording event for inactive task raises error."""
        profiler = PerformanceProfilerFSA()
        with pytest.raises(ValueError, match="not being profiled"):
            profiler.record_event("task1", "event")


class TestNestedProfiling:
    """Test nested profiling support."""

    def test_nested_tasks(self):
        """Test profiling nested tasks."""
        profiler = PerformanceProfilerFSA()

        profiler.start_profiling("parent")
        profiler.start_profiling("child", parent_task_id="parent")
        time.sleep(0.01)
        child_metrics = profiler.stop_profiling("child")
        parent_metrics = profiler.stop_profiling("parent")

        assert child_metrics["parent_task_id"] == "parent"
        assert parent_metrics["parent_task_id"] is None

    def test_nested_context_manager(self):
        """Test nested profiling with context managers."""
        profiler = PerformanceProfilerFSA()

        with profiler.profile("parent"):
            with profiler.profile("child"):
                time.sleep(0.01)

        parent_metrics = profiler.get_metrics("parent")
        child_metrics = profiler.get_metrics("child")

        assert parent_metrics["executions"] == 1
        assert child_metrics["executions"] == 1
        # Child should have parent as parent_task_id
        assert child_metrics["records"][0]["parent_task_id"] == "parent"


class TestContextManager:
    """Test context manager functionality."""

    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        profiler = PerformanceProfilerFSA()

        with profiler.profile("task1"):
            time.sleep(0.01)

        metrics = profiler.get_metrics("task1")
        assert metrics["executions"] == 1
        assert metrics["mean_elapsed_time"] >= 0.01

    def test_context_manager_exception(self):
        """Test context manager handles exceptions."""
        profiler = PerformanceProfilerFSA()

        try:
            with profiler.profile("task1"):
                raise ValueError("Test error")
        except ValueError:
            pass

        metrics = profiler.get_metrics("task1")
        assert metrics["executions"] == 1

    def test_context_manager_returns_record(self):
        """Test context manager yields record."""
        profiler = PerformanceProfilerFSA()

        with profiler.profile("task1") as record:
            assert record is not None
            assert record.task_id == "task1"


class TestDecorator:
    """Test decorator functionality."""

    def test_decorator_basic(self):
        """Test basic decorator usage."""
        profiler = PerformanceProfilerFSA()

        @profiler.profile_function()
        def test_func():
            time.sleep(0.01)
            return 42

        result = test_func()
        assert result == 42

        metrics = profiler.get_metrics("test_func")
        assert metrics["executions"] == 1

    def test_decorator_custom_task_id(self):
        """Test decorator with custom task ID."""
        profiler = PerformanceProfilerFSA()

        @profiler.profile_function(task_id="custom_task")
        def test_func():
            return 100

        result = test_func()
        assert result == 100

        metrics = profiler.get_metrics("custom_task")
        assert metrics["executions"] == 1

    def test_decorator_multiple_calls(self):
        """Test decorator with multiple function calls."""
        profiler = PerformanceProfilerFSA()

        @profiler.profile_function()
        def test_func(x):
            return x * 2

        for i in range(5):
            test_func(i)

        metrics = profiler.get_metrics("test_func")
        assert metrics["executions"] == 5

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function metadata."""
        profiler = PerformanceProfilerFSA()

        @profiler.profile_function()
        def test_func():
            """Test docstring."""
            pass

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test docstring."


class TestMetricsAggregation:
    """Test metrics aggregation and statistics."""

    def test_get_metrics_nonexistent_task(self):
        """Test getting metrics for nonexistent task."""
        profiler = PerformanceProfilerFSA()
        metrics = profiler.get_metrics("nonexistent")

        assert metrics["executions"] == 0
        assert metrics["records"] == []

    def test_metrics_statistics(self):
        """Test metrics statistical calculations."""
        profiler = PerformanceProfilerFSA()

        # Execute task multiple times with varying durations
        for i in range(5):
            profiler.start_profiling("task1")
            time.sleep(0.01 * (i + 1))
            profiler.stop_profiling("task1")

        metrics = profiler.get_metrics("task1")
        assert metrics["executions"] == 5
        assert metrics["mean_elapsed_time"] > 0
        assert metrics["median_elapsed_time"] > 0
        assert metrics["min_elapsed_time"] > 0
        assert metrics["max_elapsed_time"] > metrics["min_elapsed_time"]

    def test_total_elapsed_time(self):
        """Test total elapsed time calculation."""
        profiler = PerformanceProfilerFSA()

        for _ in range(3):
            profiler.start_profiling("task1")
            time.sleep(0.01)
            profiler.stop_profiling("task1")

        metrics = profiler.get_metrics("task1")
        assert metrics["total_elapsed_time"] >= 0.03


class TestSummaryGeneration:
    """Test summary generation."""

    def test_empty_summary(self):
        """Test summary with no metrics."""
        profiler = PerformanceProfilerFSA()
        summary = profiler.get_summary()

        assert summary["total_tasks"] == 0
        assert summary["total_executions"] == 0
        assert summary["active_tasks"] == 0

    def test_summary_with_tasks(self):
        """Test summary with multiple tasks."""
        profiler = PerformanceProfilerFSA()

        for i in range(3):
            profiler.start_profiling(f"task{i}")
            time.sleep(0.01)
            profiler.stop_profiling(f"task{i}")

        summary = profiler.get_summary()
        assert summary["total_tasks"] == 3
        assert summary["total_executions"] == 3
        assert "task0" in summary["tasks"]
        assert "task1" in summary["tasks"]
        assert "task2" in summary["tasks"]

    def test_summary_percentiles(self):
        """Test summary percentile calculations."""
        profiler = PerformanceProfilerFSA()

        for i in range(10):
            profiler.start_profiling("task1")
            time.sleep(0.01 * (i + 1))
            profiler.stop_profiling("task1")

        summary = profiler.get_summary()
        assert summary["p95_elapsed_time"] > 0
        assert summary["p99_elapsed_time"] > 0
        assert summary["p99_elapsed_time"] >= summary["p95_elapsed_time"]

    def test_summary_active_tasks(self):
        """Test summary includes active tasks count."""
        profiler = PerformanceProfilerFSA()
        profiler.start_profiling("task1")
        profiler.start_profiling("task2")

        summary = profiler.get_summary()
        assert summary["active_tasks"] == 2


class TestClearMetrics:
    """Test clearing metrics."""

    def test_clear_specific_task(self):
        """Test clearing metrics for specific task."""
        profiler = PerformanceProfilerFSA()

        profiler.start_profiling("task1")
        profiler.stop_profiling("task1")
        profiler.start_profiling("task2")
        profiler.stop_profiling("task2")

        profiler.clear_metrics("task1")

        metrics1 = profiler.get_metrics("task1")
        metrics2 = profiler.get_metrics("task2")

        assert metrics1["executions"] == 0
        assert metrics2["executions"] == 1

    def test_clear_all_metrics(self):
        """Test clearing all metrics."""
        profiler = PerformanceProfilerFSA()

        for i in range(3):
            profiler.start_profiling(f"task{i}")
            profiler.stop_profiling(f"task{i}")

        profiler.clear_metrics()

        summary = profiler.get_summary()
        assert summary["total_tasks"] == 0

    def test_clear_nonexistent_task(self):
        """Test clearing nonexistent task does not raise error."""
        profiler = PerformanceProfilerFSA()
        profiler.clear_metrics("nonexistent")  # Should not raise


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_profiling(self):
        """Test concurrent profiling from multiple threads."""
        profiler = PerformanceProfilerFSA()
        threads = []

        def worker(thread_id):
            for i in range(5):
                task_id = f"thread{thread_id}_task{i}"
                profiler.start_profiling(task_id)
                time.sleep(0.001)
                profiler.stop_profiling(task_id)

        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        summary = profiler.get_summary()
        assert summary["total_executions"] == 25

    def test_concurrent_metrics_access(self):
        """Test concurrent metrics access."""
        profiler = PerformanceProfilerFSA()

        profiler.start_profiling("task1")
        profiler.stop_profiling("task1")

        results = []

        def reader():
            for _ in range(10):
                metrics = profiler.get_metrics("task1")
                results.append(metrics["executions"])

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should return consistent results
        assert all(r == 1 for r in results)


class TestExportFunctionality:
    """Test export functionality."""

    def test_export_specific_task(self):
        """Test exporting specific task to JSON."""
        profiler = PerformanceProfilerFSA()

        profiler.start_profiling("task1")
        time.sleep(0.01)
        profiler.stop_profiling("task1")

        json_str = profiler.export_json("task1")
        data = json.loads(json_str)

        assert data["task_id"] == "task1"
        assert data["executions"] == 1

    def test_export_all_tasks(self):
        """Test exporting all tasks to JSON."""
        profiler = PerformanceProfilerFSA()

        for i in range(3):
            profiler.start_profiling(f"task{i}")
            profiler.stop_profiling(f"task{i}")

        json_str = profiler.export_json()
        data = json.loads(json_str)

        assert "summary" in data
        assert "tasks" in data
        assert len(data["tasks"]) == 3

    def test_export_json_valid_format(self):
        """Test exported JSON is valid."""
        profiler = PerformanceProfilerFSA()

        profiler.start_profiling("task1")
        profiler.record_event("task1", "checkpoint", {"value": 123})
        profiler.stop_profiling("task1")

        json_str = profiler.export_json("task1")
        # Should not raise
        data = json.loads(json_str)
        assert isinstance(data, dict)


class TestProfileRecord:
    """Test ProfileRecord dataclass."""

    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        record = ProfileRecord(task_id="test", start_time=1.0, end_time=2.5)
        assert record.elapsed_time() == 1.5

    def test_elapsed_time_none(self):
        """Test elapsed time when end_time is None."""
        record = ProfileRecord(task_id="test", start_time=1.0)
        assert record.elapsed_time() is None

    def test_cpu_time_calculation(self):
        """Test CPU time calculation."""
        record = ProfileRecord(
            task_id="test", start_time=1.0, start_cpu_time=0.5, end_cpu_time=1.5
        )
        assert record.cpu_time() == 1.0

    def test_to_dict(self):
        """Test converting record to dictionary."""
        record = ProfileRecord(task_id="test", start_time=1.0, end_time=2.0)
        data = record.to_dict()

        assert data["task_id"] == "test"
        assert data["start_time"] == 1.0
        assert data["end_time"] == 2.0
        assert data["elapsed_time"] == 1.0


class TestSmokeTests:
    """Smoke tests for overall functionality."""

    def test_smoke_basic_workflow(self):
        """Smoke test: basic profiling workflow."""
        profiler = PerformanceProfilerFSA()

        # Profile multiple tasks
        for i in range(5):
            profiler.start_profiling(f"task{i}")
            time.sleep(0.01)
            profiler.record_event(f"task{i}", "checkpoint")
            profiler.stop_profiling(f"task{i}")

        # Check summary
        summary = profiler.get_summary()
        assert summary["total_tasks"] == 5
        assert summary["total_executions"] == 5

        # Check specific metrics
        metrics = profiler.get_metrics("task0")
        assert metrics["executions"] == 1
        assert metrics["total_events"] == 1

    def test_smoke_full_features(self):
        """Smoke test: all features combined."""
        profiler = PerformanceProfilerFSA()

        # Test decorator
        @profiler.profile_function("decorated_task")
        def decorated_func():
            time.sleep(0.01)
            return 42

        result = decorated_func()
        assert result == 42

        # Test context manager
        with profiler.profile("context_task"):
            time.sleep(0.01)

        # Test nested profiling
        with profiler.profile("parent"):
            with profiler.profile("child"):
                time.sleep(0.01)

        # Test manual profiling
        profiler.start_profiling("manual_task")
        profiler.record_event("manual_task", "start")
        time.sleep(0.01)
        profiler.record_event("manual_task", "end")
        profiler.stop_profiling("manual_task")

        # Check summary
        summary = profiler.get_summary()
        assert summary["total_tasks"] == 5  # decorated, context, parent, child, manual
        assert summary["mean_elapsed_time"] > 0

        # Export to JSON
        json_str = profiler.export_json()
        data = json.loads(json_str)
        assert "summary" in data
        assert "tasks" in data

        # Clear and verify
        profiler.clear_metrics()
        summary_after = profiler.get_summary()
        assert summary_after["total_tasks"] == 0

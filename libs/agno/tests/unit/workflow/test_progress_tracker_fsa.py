"""
Unit tests for ProgressTrackerFSA.

Tests cover:
- Task creation and state transitions
- Progress tracking and metrics calculation
- Performance metrics
- Alert system
- Milestone tracking
- Parallel task tracking
- Reporting functionality
"""

import time
import pytest
from unittest.mock import patch

from agno.workflow.progress_tracker_fsa import (
    ProgressTrackerFSA,
    TaskState,
    TaskInfo,
    ProgressMetrics,
    PerformanceMetrics,
    Alert,
    AlertLevel,
    Milestone,
)


class TestTaskCreationAndStateTransitions:
    """Test task creation and FSA state transitions."""

    def test_create_task(self):
        """Test creating a new task."""
        tracker = ProgressTrackerFSA()
        task = tracker.create_task("task1", "Test Task")

        assert task.task_id == "task1"
        assert task.name == "Test Task"
        assert task.state == TaskState.IDLE
        assert task.progress == 0.0
        assert task.created_at > 0

    def test_create_duplicate_task_raises_error(self):
        """Test that creating duplicate task raises ValueError."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        with pytest.raises(ValueError, match="already exists"):
            tracker.create_task("task1", "Duplicate Task")

    def test_create_task_with_metadata(self):
        """Test creating task with metadata."""
        tracker = ProgressTrackerFSA()
        metadata = {"priority": "high", "category": "data-processing"}
        task = tracker.create_task("task1", "Test Task", metadata=metadata)

        assert task.metadata == metadata
        assert task.metadata["priority"] == "high"

    def test_create_task_with_parent(self):
        """Test creating task with parent for hierarchical tracking."""
        tracker = ProgressTrackerFSA()
        parent = tracker.create_task("parent", "Parent Task")
        child = tracker.create_task("child", "Child Task", parent_id="parent")

        assert child.parent_id == "parent"
        assert "child" in parent.subtask_ids

    def test_start_task(self):
        """Test transitioning task from IDLE to STARTED."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        task = tracker.start_task("task1")

        assert task.state == TaskState.STARTED
        assert task.started_at is not None
        assert task.started_at > 0

    def test_start_task_invalid_state(self):
        """Test that starting non-IDLE task raises error."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.start_task("task1")

    def test_mark_in_progress(self):
        """Test transitioning task to IN_PROGRESS."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        task = tracker.mark_in_progress("task1")

        assert task.state == TaskState.IN_PROGRESS

    def test_mark_in_progress_from_idle(self):
        """Test that marking IDLE task as IN_PROGRESS fails."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.mark_in_progress("task1")

    def test_complete_task(self):
        """Test completing a task."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        task = tracker.complete_task("task1")

        assert task.state == TaskState.COMPLETED
        assert task.completed_at is not None
        assert task.progress == 100.0

    def test_complete_task_from_in_progress(self):
        """Test completing task from IN_PROGRESS state."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")
        tracker.mark_in_progress("task1")

        task = tracker.complete_task("task1")

        assert task.state == TaskState.COMPLETED

    def test_complete_task_invalid_state(self):
        """Test that completing IDLE task raises error."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.complete_task("task1")

    def test_fail_task(self):
        """Test failing a task with error message."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        error_msg = "Connection timeout"
        task = tracker.fail_task("task1", error_msg)

        assert task.state == TaskState.FAILED
        assert task.error == error_msg
        assert task.completed_at is not None

    def test_fail_task_generates_alert(self):
        """Test that failing task generates error alert."""
        tracker = ProgressTrackerFSA(enable_alerts=True)
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        tracker.fail_task("task1", "Test error")

        alerts = tracker.get_alerts()
        assert len(alerts) > 0
        assert any(a.level == AlertLevel.ERROR for a in alerts)

    def test_task_not_found(self):
        """Test that accessing non-existent task raises error."""
        tracker = ProgressTrackerFSA()

        with pytest.raises(ValueError, match="not found"):
            tracker.start_task("nonexistent")


class TestTaskInfo:
    """Test TaskInfo class methods."""

    def test_task_get_duration(self):
        """Test calculating task duration."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        # Task not started - duration should be None
        task = tracker.get_task("task1")
        assert task.get_duration() is None

        # Start task and check duration
        tracker.start_task("task1")
        time.sleep(0.1)
        task = tracker.get_task("task1")
        duration = task.get_duration()
        assert duration is not None
        assert duration >= 0.1

    def test_task_is_active(self):
        """Test checking if task is active."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        task = tracker.get_task("task1")
        assert not task.is_active()

        tracker.start_task("task1")
        task = tracker.get_task("task1")
        assert task.is_active()

        tracker.complete_task("task1")
        task = tracker.get_task("task1")
        assert not task.is_active()

    def test_task_is_terminal(self):
        """Test checking if task is in terminal state."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")

        task = tracker.get_task("task1")
        assert not task.is_terminal()

        tracker.start_task("task1")
        task = tracker.get_task("task1")
        assert not task.is_terminal()

        tracker.complete_task("task1")
        task = tracker.get_task("task1")
        assert task.is_terminal()

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task", metadata={"key": "value"})

        task = tracker.get_task("task1")
        task_dict = task.to_dict()

        assert task_dict["task_id"] == "task1"
        assert task_dict["name"] == "Test Task"
        assert task_dict["state"] == "idle"
        assert task_dict["metadata"]["key"] == "value"


class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_update_progress(self):
        """Test updating task progress."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        tracker.update_progress("task1", 50.0)
        task = tracker.get_task("task1")

        assert task.progress == 50.0

    def test_update_progress_invalid_value(self):
        """Test that invalid progress value raises error."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Test Task")
        tracker.start_task("task1")

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            tracker.update_progress("task1", 150.0)

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            tracker.update_progress("task1", -10.0)

    def test_get_tasks_by_state(self):
        """Test filtering tasks by state."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.create_task("task2", "Task 2")
        tracker.create_task("task3", "Task 3")

        tracker.start_task("task1")
        tracker.start_task("task2")
        tracker.complete_task("task2")

        idle_tasks = tracker.get_tasks_by_state(TaskState.IDLE)
        started_tasks = tracker.get_tasks_by_state(TaskState.STARTED)
        completed_tasks = tracker.get_tasks_by_state(TaskState.COMPLETED)

        assert len(idle_tasks) == 1
        assert len(started_tasks) == 1
        assert len(completed_tasks) == 1

    def test_get_active_tasks(self):
        """Test getting all active tasks."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.create_task("task2", "Task 2")
        tracker.create_task("task3", "Task 3")

        tracker.start_task("task1")
        tracker.start_task("task2")
        tracker.mark_in_progress("task2")

        active_tasks = tracker.get_active_tasks()

        assert len(active_tasks) == 2
        assert all(t.is_active() for t in active_tasks)


class TestProgressMetrics:
    """Test progress metrics calculation."""

    def test_calculate_progress_metrics(self):
        """Test calculating progress metrics."""
        tracker = ProgressTrackerFSA()

        # Create and process some tasks
        for i in range(10):
            tracker.create_task(f"task{i}", f"Task {i}")

        for i in range(5):
            tracker.start_task(f"task{i}")
            tracker.complete_task(f"task{i}")

        tracker.start_task("task5")
        tracker.fail_task("task5", "Error")

        tracker.start_task("task6")
        tracker.mark_in_progress("task6")

        metrics = tracker.calculate_progress_metrics()

        assert metrics.total_tasks == 10
        assert metrics.completed_tasks == 5
        assert metrics.failed_tasks == 1
        assert metrics.active_tasks == 1
        assert metrics.completion_percentage == 50.0
        assert metrics.elapsed_time > 0

    def test_progress_metrics_empty_tracker(self):
        """Test metrics calculation with no tasks."""
        tracker = ProgressTrackerFSA()
        metrics = tracker.calculate_progress_metrics()

        assert metrics.total_tasks == 0
        assert metrics.completion_percentage == 0.0

    def test_progress_metrics_with_duration(self):
        """Test metrics calculation includes duration estimates."""
        tracker = ProgressTrackerFSA()

        # Create and complete tasks with measurable duration
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        time.sleep(0.1)
        tracker.complete_task("task1")

        tracker.create_task("task2", "Task 2")
        tracker.start_task("task2")

        metrics = tracker.calculate_progress_metrics()

        assert metrics.average_task_duration is not None
        assert metrics.average_task_duration >= 0.1


class TestPerformanceMetrics:
    """Test performance metrics calculation."""

    def test_calculate_performance_metrics(self):
        """Test calculating performance metrics."""
        tracker = ProgressTrackerFSA()

        # Create and process tasks
        for i in range(10):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        # Complete 7 tasks
        for i in range(7):
            tracker.complete_task(f"task{i}")

        # Fail 2 tasks
        tracker.fail_task("task7", "Error 1")
        tracker.fail_task("task8", "Error 2")

        performance = tracker.calculate_performance_metrics()

        assert performance.throughput > 0
        assert performance.success_rate == pytest.approx(77.78, rel=0.1)  # 7/9 * 100
        assert performance.error_rate == pytest.approx(22.22, rel=0.1)  # 2/9 * 100
        assert performance.total_processing_time >= 0

    def test_performance_metrics_peak_concurrent(self):
        """Test tracking peak concurrent tasks."""
        tracker = ProgressTrackerFSA()

        # Start multiple tasks concurrently
        for i in range(5):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        performance = tracker.calculate_performance_metrics()
        assert performance.peak_concurrent_tasks == 5

        # Complete some and start more
        tracker.complete_task("task0")
        tracker.complete_task("task1")

        for i in range(5, 8):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        performance = tracker.calculate_performance_metrics()
        # Peak should still be from when we had more concurrent
        assert performance.peak_concurrent_tasks >= 5


class TestReporting:
    """Test reporting functionality."""

    def test_get_progress_report(self):
        """Test generating progress report."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.complete_task("task1")

        report = tracker.get_progress_report()

        assert "timestamp" in report
        assert "progress_metrics" in report
        assert "performance_metrics" in report
        assert "active_tasks" in report
        assert "recent_alerts" in report
        assert "milestones" in report
        assert "summary" in report

    def test_get_metrics_dashboard(self):
        """Test generating metrics dashboard."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")

        dashboard = tracker.get_metrics_dashboard()

        assert "overview" in dashboard
        assert "performance" in dashboard
        assert "state_distribution" in dashboard
        assert "concurrent_tasks" in dashboard
        assert "alerts" in dashboard
        assert "milestones" in dashboard

        # Check overview fields
        assert "total_tasks" in dashboard["overview"]
        assert "completion_percentage" in dashboard["overview"]
        assert "elapsed_time" in dashboard["overview"]

    def test_get_task_report(self):
        """Test generating task-specific report."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("parent", "Parent Task")
        tracker.create_task("child", "Child Task", parent_id="parent")
        tracker.start_task("parent")

        report = tracker.get_task_report("parent")

        assert "task" in report
        assert "subtasks" in report
        assert "transitions" in report
        assert "duration" in report
        assert "is_active" in report
        assert "is_terminal" in report

        assert len(report["subtasks"]) == 1
        assert report["is_active"] is True


class TestAlerts:
    """Test alert system."""

    def test_alerts_enabled_on_failure(self):
        """Test that alerts are generated on task failure."""
        tracker = ProgressTrackerFSA(enable_alerts=True)
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.fail_task("task1", "Test error")

        alerts = tracker.get_alerts()
        assert len(alerts) > 0

        error_alerts = tracker.get_alerts_by_level(AlertLevel.ERROR)
        assert len(error_alerts) > 0

    def test_alerts_disabled(self):
        """Test that alerts are not generated when disabled."""
        tracker = ProgressTrackerFSA(enable_alerts=False)
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.fail_task("task1", "Test error")

        alerts = tracker.get_alerts()
        # Should still have alerts from fail_task
        assert len(alerts) == 0

    def test_error_rate_alert(self):
        """Test alert when error rate exceeds threshold."""
        tracker = ProgressTrackerFSA(
            enable_alerts=True,
            alert_thresholds={'error_rate': 0.2}  # 20% threshold
        )

        # Create tasks with 30% error rate
        for i in range(10):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        # Complete 7 successfully
        for i in range(7):
            tracker.complete_task(f"task{i}")

        # Fail 3 (30% error rate)
        for i in range(7, 10):
            tracker.fail_task(f"task{i}", "Error")

        # Should have critical alert for error rate
        critical_alerts = tracker.get_alerts_by_level(AlertLevel.CRITICAL)
        assert len(critical_alerts) > 0

    def test_get_recent_alerts(self):
        """Test getting recent alerts with limit."""
        tracker = ProgressTrackerFSA(enable_alerts=True)

        # Generate multiple alerts
        for i in range(10):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")
            tracker.fail_task(f"task{i}", f"Error {i}")

        recent = tracker.get_recent_alerts(limit=5)
        assert len(recent) == 5

    def test_clear_alerts(self):
        """Test clearing all alerts."""
        tracker = ProgressTrackerFSA(enable_alerts=True)
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.fail_task("task1", "Error")

        assert len(tracker.get_alerts()) > 0

        tracker.clear_alerts()
        assert len(tracker.get_alerts()) == 0


class TestMilestones:
    """Test milestone tracking."""

    def test_default_milestones(self):
        """Test that default milestones are created."""
        tracker = ProgressTrackerFSA()
        milestones = tracker.get_milestones()

        assert len(milestones) > 0
        assert any(m.target_percentage == 25.0 for m in milestones)
        assert any(m.target_percentage == 50.0 for m in milestones)
        assert any(m.target_percentage == 75.0 for m in milestones)
        assert any(m.target_percentage == 100.0 for m in milestones)

    def test_custom_milestones(self):
        """Test creating tracker with custom milestones."""
        custom_milestones = [
            {"name": "First Quarter", "target_percentage": 25.0},
            {"name": "Half Way", "target_percentage": 50.0},
        ]

        tracker = ProgressTrackerFSA(milestones=custom_milestones)
        milestones = tracker.get_milestones()

        assert len(milestones) == 2
        assert milestones[0].name == "First Quarter"
        assert milestones[1].name == "Half Way"

    def test_milestone_achievement(self):
        """Test that milestones are marked as achieved."""
        tracker = ProgressTrackerFSA()

        # Create 4 tasks and complete 2 (50%)
        for i in range(4):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        tracker.complete_task("task0")
        tracker.complete_task("task1")

        # Check that 25% and 50% milestones are achieved
        achieved = tracker.get_achieved_milestones()
        assert len(achieved) >= 2

        milestone_25 = next((m for m in achieved if m.target_percentage == 25.0), None)
        milestone_50 = next((m for m in achieved if m.target_percentage == 50.0), None)

        assert milestone_25 is not None
        assert milestone_50 is not None
        assert milestone_25.achieved_at is not None

    def test_add_milestone(self):
        """Test adding a new milestone."""
        tracker = ProgressTrackerFSA(milestones=[])
        milestone = tracker.add_milestone("Custom Milestone", 33.0)

        assert milestone.name == "Custom Milestone"
        assert milestone.target_percentage == 33.0
        assert not milestone.achieved

        milestones = tracker.get_milestones()
        assert len(milestones) == 1


class TestParallelTaskTracking:
    """Test support for parallel task execution."""

    def test_multiple_concurrent_tasks(self):
        """Test tracking multiple tasks running in parallel."""
        tracker = ProgressTrackerFSA()

        # Start 10 tasks concurrently
        for i in range(10):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        active = tracker.get_active_tasks()
        assert len(active) == 10

        # Complete them gradually
        for i in range(0, 5):
            tracker.complete_task(f"task{i}")

        active = tracker.get_active_tasks()
        assert len(active) == 5

        metrics = tracker.calculate_progress_metrics()
        assert metrics.active_tasks == 5
        assert metrics.completed_tasks == 5

    def test_peak_concurrent_tracking(self):
        """Test that peak concurrent tasks is tracked correctly."""
        tracker = ProgressTrackerFSA()

        # Start 5 tasks
        for i in range(5):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        performance = tracker.calculate_performance_metrics()
        assert performance.peak_concurrent_tasks == 5

        # Complete 3 tasks
        for i in range(3):
            tracker.complete_task(f"task{i}")

        # Start 2 more (now have 4 concurrent)
        for i in range(5, 7):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")

        performance = tracker.calculate_performance_metrics()
        assert performance.peak_concurrent_tasks == 5  # Peak was 5


class TestHierarchicalTasks:
    """Test hierarchical task tracking with parent/child relationships."""

    def test_parent_child_relationship(self):
        """Test creating parent-child task relationships."""
        tracker = ProgressTrackerFSA()

        parent = tracker.create_task("parent", "Parent Task")
        child1 = tracker.create_task("child1", "Child 1", parent_id="parent")
        child2 = tracker.create_task("child2", "Child 2", parent_id="parent")

        assert child1.parent_id == "parent"
        assert child2.parent_id == "parent"
        assert "child1" in parent.subtask_ids
        assert "child2" in parent.subtask_ids
        assert len(parent.subtask_ids) == 2

    def test_task_report_includes_subtasks(self):
        """Test that task report includes subtask information."""
        tracker = ProgressTrackerFSA()

        tracker.create_task("parent", "Parent Task")
        tracker.create_task("child1", "Child 1", parent_id="parent")
        tracker.create_task("child2", "Child 2", parent_id="parent")

        report = tracker.get_task_report("parent")

        assert len(report["subtasks"]) == 2
        assert any(t["task_id"] == "child1" for t in report["subtasks"])
        assert any(t["task_id"] == "child2" for t in report["subtasks"])


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = ProgressTrackerFSA()

        # Add some data
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.complete_task("task1")

        assert len(tracker.tasks) > 0

        # Reset
        tracker.reset()

        assert len(tracker.tasks) == 0
        assert len(tracker.alerts) == 0
        assert len(tracker.state_transitions) == 0
        assert tracker.peak_concurrent == 0

        # Milestones should be reset but not removed
        milestones = tracker.get_milestones()
        assert all(not m.achieved for m in milestones)

    def test_to_dict(self):
        """Test converting tracker to dictionary."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")

        tracker_dict = tracker.to_dict()

        assert "tasks" in tracker_dict
        assert "alerts" in tracker_dict
        assert "milestones" in tracker_dict
        assert "progress_metrics" in tracker_dict
        assert "performance_metrics" in tracker_dict
        assert "start_time" in tracker_dict
        assert "peak_concurrent" in tracker_dict

        assert "task1" in tracker_dict["tasks"]

    def test_format_duration(self):
        """Test duration formatting."""
        from agno.workflow.progress_tracker_fsa import ProgressTrackerFSA

        # Test seconds
        assert "s" in ProgressTrackerFSA._format_duration(30.5)

        # Test minutes
        assert "m" in ProgressTrackerFSA._format_duration(120.0)

        # Test hours
        assert "h" in ProgressTrackerFSA._format_duration(7200.0)


class TestStateTransitionHistory:
    """Test state transition tracking."""

    def test_transition_history_recorded(self):
        """Test that state transitions are recorded."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.mark_in_progress("task1")
        tracker.complete_task("task1")

        # Should have transitions: None->IDLE, IDLE->STARTED, STARTED->IN_PROGRESS, IN_PROGRESS->COMPLETED
        assert len(tracker.state_transitions) == 4

        transitions = [t for t in tracker.state_transitions if t["task_id"] == "task1"]
        assert len(transitions) == 4

    def test_task_report_includes_transitions(self):
        """Test that task report includes transition history."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.complete_task("task1")

        report = tracker.get_task_report("task1")

        assert "transitions" in report
        assert len(report["transitions"]) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_complete_already_completed_task(self):
        """Test completing an already completed task."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.complete_task("task1")

        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.complete_task("task1")

    def test_fail_already_failed_task(self):
        """Test failing an already failed task."""
        tracker = ProgressTrackerFSA()
        tracker.create_task("task1", "Task 1")
        tracker.start_task("task1")
        tracker.fail_task("task1", "First error")

        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.fail_task("task1", "Second error")

    def test_empty_tracker_metrics(self):
        """Test metrics with no tasks."""
        tracker = ProgressTrackerFSA()

        progress = tracker.calculate_progress_metrics()
        assert progress.total_tasks == 0
        assert progress.completion_percentage == 0.0

        performance = tracker.calculate_performance_metrics()
        assert performance.throughput == 0.0
        assert performance.success_rate == 0.0

    def test_all_tasks_failed(self):
        """Test metrics when all tasks failed."""
        tracker = ProgressTrackerFSA()

        for i in range(5):
            tracker.create_task(f"task{i}", f"Task {i}")
            tracker.start_task(f"task{i}")
            tracker.fail_task(f"task{i}", "Error")

        performance = tracker.calculate_performance_metrics()
        assert performance.success_rate == 0.0
        assert performance.error_rate == 100.0

    def test_task_timeout_alert(self):
        """Test alert generation for task timeout."""
        tracker = ProgressTrackerFSA(
            enable_alerts=True,
            alert_thresholds={'task_timeout': 0.05}  # 50ms timeout
        )

        tracker.create_task("task1", "Slow Task")
        tracker.start_task("task1")

        time.sleep(0.1)  # Wait to exceed timeout

        # Trigger timeout check via progress update
        tracker.update_progress("task1", 50.0)

        warnings = tracker.get_alerts_by_level(AlertLevel.WARNING)
        assert len(warnings) > 0


# Integration test combining multiple features
class TestIntegrationScenarios:
    """Integration tests combining multiple features."""

    def test_complete_workflow(self):
        """Test a complete workflow with multiple tasks."""
        tracker = ProgressTrackerFSA(enable_alerts=True)

        # Create a batch of tasks
        num_tasks = 20
        for i in range(num_tasks):
            tracker.create_task(f"task{i}", f"Processing item {i}")

        # Start all tasks
        for i in range(num_tasks):
            tracker.start_task(f"task{i}")

        # Complete most tasks
        for i in range(15):
            tracker.update_progress(f"task{i}", 50.0)
            tracker.mark_in_progress(f"task{i}")
            tracker.update_progress(f"task{i}", 100.0)
            tracker.complete_task(f"task{i}")

        # Fail some tasks
        for i in range(15, 18):
            tracker.fail_task(f"task{i}", f"Error processing item {i}")

        # Leave some in progress
        for i in range(18, 20):
            tracker.mark_in_progress(f"task{i}")
            tracker.update_progress(f"task{i}", 75.0)

        # Verify final state
        progress = tracker.calculate_progress_metrics()
        assert progress.completed_tasks == 15
        assert progress.failed_tasks == 3
        assert progress.active_tasks == 2
        assert progress.completion_percentage == 75.0

        # Check performance
        performance = tracker.calculate_performance_metrics()
        assert performance.success_rate > 0
        assert performance.error_rate > 0

        # Verify report generation works
        report = tracker.get_progress_report()
        assert report is not None

        dashboard = tracker.get_metrics_dashboard()
        assert dashboard is not None

        # Check milestones
        achieved = tracker.get_achieved_milestones()
        assert len(achieved) >= 2  # Should have 25%, 50%, and 75%

    def test_hierarchical_workflow(self):
        """Test workflow with hierarchical tasks."""
        tracker = ProgressTrackerFSA()

        # Create parent task
        tracker.create_task("main", "Main Processing")

        # Create child tasks
        for i in range(5):
            tracker.create_task(f"subtask{i}", f"Subtask {i}", parent_id="main")

        # Start parent
        tracker.start_task("main")

        # Process subtasks
        for i in range(5):
            tracker.start_task(f"subtask{i}")
            tracker.complete_task(f"subtask{i}")

        # Complete parent
        tracker.mark_in_progress("main")
        tracker.complete_task("main")

        # Verify
        report = tracker.get_task_report("main")
        assert len(report["subtasks"]) == 5
        assert all(t["state"] == "completed" for t in report["subtasks"])

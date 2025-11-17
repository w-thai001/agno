"""
Comprehensive unit tests for Progress Tracker FSA.

Tests cover:
- State transitions and FSA validation
- Metric calculations (velocity, ETA, completion percentage)
- Milestone tracking and variance analysis
- Bottleneck detection
- Progress snapshots
- Report generation and JSON export
"""

import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agno.progress import (
    BottleneckSeverity,
    Milestone,
    MilestoneStatus,
    ProgressState,
    ProgressTracker,
    StateTransitionError,
    validate_transition,
)


class TestStateTransitions:
    """Test FSA state transition logic."""

    def test_valid_transition_idle_to_queued(self):
        """Test valid transition from IDLE to QUEUED."""
        assert validate_transition(ProgressState.IDLE, ProgressState.QUEUED) is True

    def test_invalid_transition_idle_to_running(self):
        """Test invalid transition from IDLE to RUNNING."""
        assert validate_transition(ProgressState.IDLE, ProgressState.RUNNING) is False

    def test_running_to_completed(self):
        """Test valid transition from RUNNING to COMPLETED."""
        assert validate_transition(ProgressState.RUNNING, ProgressState.COMPLETED) is True

    def test_completed_is_terminal(self):
        """Test that COMPLETED state cannot transition."""
        assert validate_transition(ProgressState.COMPLETED, ProgressState.RUNNING) is False

    def test_tracker_enforces_valid_transitions(self):
        """Test that tracker enforces FSA transition rules."""
        tracker = ProgressTracker()

        # Should allow IDLE -> QUEUED
        tracker._transition_state(ProgressState.QUEUED)
        assert tracker.current_state == ProgressState.QUEUED

        # Should raise error for invalid transition
        with pytest.raises(StateTransitionError):
            tracker._transition_state(ProgressState.COMPLETED)


class TestProgressTrackerInitialization:
    """Test tracker initialization and setup."""

    def test_default_initialization(self):
        """Test tracker with default parameters."""
        tracker = ProgressTracker()
        assert tracker.current_state == ProgressState.IDLE
        assert tracker.total_steps == 1
        assert len(tracker.milestones) == 0
        assert tracker.task_id is not None

    def test_custom_initialization(self):
        """Test tracker with custom parameters."""
        tracker = ProgressTracker(task_id="test-123", total_steps=5)
        assert tracker.task_id == "test-123"
        assert tracker.total_steps == 5

    def test_start_tracking_creates_milestones(self):
        """Test that start_tracking creates default milestones."""
        tracker = ProgressTracker(total_steps=3)
        tracker.start_tracking()

        assert len(tracker.milestones) == 3
        assert tracker.current_state == ProgressState.RUNNING
        assert tracker.started_at is not None

    def test_start_tracking_with_custom_milestones(self):
        """Test start_tracking with predefined milestones."""
        milestones = [
            Milestone(name="Step 1", expected_duration=5.0),
            Milestone(name="Step 2", expected_duration=10.0),
        ]

        tracker = ProgressTracker()
        tracker.start_tracking(milestones)

        assert len(tracker.milestones) == 2
        assert tracker.milestones[0].name == "Step 1"
        assert tracker.total_steps == 2


class TestMetricCalculations:
    """Test metric calculation accuracy."""

    def test_completion_percentage_calculation(self):
        """Test completion percentage is calculated correctly."""
        tracker = ProgressTracker(total_steps=4)
        tracker.start_tracking()

        assert tracker._calculate_completion_percentage() == 0.0

        tracker._completed_steps = 2
        assert tracker._calculate_completion_percentage() == 50.0

        tracker._completed_steps = 4
        assert tracker._calculate_completion_percentage() == 100.0

    def test_velocity_calculation(self):
        """Test velocity calculation (progress per second)."""
        tracker = ProgressTracker(total_steps=4)
        tracker.start_tracking()

        # Mock time passage
        with patch.object(tracker, '_get_elapsed_time', return_value=10.0):
            tracker._completed_steps = 2
            velocity = tracker._calculate_velocity()
            # 50% completion in 10 seconds = 5% per second
            assert velocity == 5.0

    def test_eta_estimation(self):
        """Test ETA estimation based on velocity."""
        tracker = ProgressTracker(total_steps=4)
        tracker.start_tracking()

        # 50% complete at 5% per second velocity
        eta = tracker._estimate_remaining_time(50.0, 5.0)
        assert eta == 10.0  # 50% remaining / 5% per second = 10 seconds

        # No ETA when velocity is 0
        eta = tracker._estimate_remaining_time(50.0, 0.0)
        assert eta is None

        # No ETA when 100% complete
        eta = tracker._estimate_remaining_time(100.0, 5.0)
        assert eta is None

    def test_elapsed_time_calculation(self):
        """Test elapsed time is calculated correctly."""
        tracker = ProgressTracker()
        assert tracker._get_elapsed_time() == 0.0

        tracker.start_tracking()
        time.sleep(0.1)

        elapsed = tracker._get_elapsed_time()
        assert elapsed >= 0.1
        assert elapsed < 1.0


class TestMilestoneTracking:
    """Test milestone tracking and completion."""

    def test_milestone_completion(self):
        """Test marking milestone as complete."""
        milestones = [
            Milestone(name="Task 1", expected_duration=1.0),
            Milestone(name="Task 2", expected_duration=2.0),
        ]

        tracker = ProgressTracker()
        tracker.start_tracking(milestones)

        # Complete first milestone
        time.sleep(0.05)
        tracker.update_progress(milestone_name="Task 1")

        milestone = tracker.milestones[0]
        assert milestone.status == MilestoneStatus.COMPLETED
        assert milestone.started_at is not None
        assert milestone.completed_at is not None
        assert milestone.actual_duration is not None
        assert tracker._completed_steps == 1

    def test_milestone_variance_calculation(self):
        """Test variance calculation for milestones."""
        milestone = Milestone(name="Test", expected_duration=10.0)
        milestone.started_at = datetime.now()
        milestone.actual_duration = 15.0

        assert milestone.duration_variance == 5.0
        assert milestone.variance_percentage == 50.0

    def test_update_progress_by_percentage(self):
        """Test updating progress by completion percentage."""
        tracker = ProgressTracker(total_steps=10)
        tracker.start_tracking()

        tracker.update_progress(completion_pct=50.0)
        assert tracker._completed_steps == 5

        tracker.update_progress(completion_pct=100.0)
        assert tracker._completed_steps == 10

    def test_milestone_metadata(self):
        """Test adding metadata to milestones."""
        tracker = ProgressTracker()
        milestones = [Milestone(name="Task 1", expected_duration=1.0)]
        tracker.start_tracking(milestones)

        tracker.update_progress(
            milestone_name="Task 1",
            metadata={"agent": "test-agent", "tokens": 150},
        )

        assert tracker.milestones[0].metadata["agent"] == "test-agent"
        assert tracker.milestones[0].metadata["tokens"] == 150


class TestProgressSnapshots:
    """Test progress snapshot creation."""

    def test_snapshot_creation_on_start(self):
        """Test snapshot is created when tracking starts."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        assert len(tracker.snapshots) > 0
        snapshot = tracker.snapshots[0]
        assert snapshot.completion_pct == 0.0
        assert snapshot.timestamp is not None

    def test_snapshot_interval_throttling(self):
        """Test snapshots respect interval throttling."""
        tracker = ProgressTracker(snapshot_interval=1.0)
        tracker.start_tracking()

        initial_count = len(tracker.snapshots)

        # Update immediately should not create snapshot
        tracker.update_progress(completion_pct=10.0)
        assert len(tracker.snapshots) == initial_count

        # Update after interval should create snapshot
        time.sleep(1.1)
        tracker.update_progress(completion_pct=20.0)
        assert len(tracker.snapshots) > initial_count

    def test_snapshot_contains_metrics(self):
        """Test snapshots contain all required metrics."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        snapshot = tracker.snapshots[-1]
        assert hasattr(snapshot, 'timestamp')
        assert hasattr(snapshot, 'completion_pct')
        assert hasattr(snapshot, 'velocity')
        assert hasattr(snapshot, 'elapsed_time')
        assert hasattr(snapshot, 'estimated_remaining')


class TestBottleneckDetection:
    """Test bottleneck detection and alerting."""

    def test_velocity_degradation_detection(self):
        """Test detection of velocity degradation."""
        tracker = ProgressTracker(enable_bottleneck_detection=True, snapshot_interval=0.0)
        tracker.start_tracking()

        # Create snapshots with decreasing velocity
        for i in range(6):
            tracker._completed_steps = i
            tracker._create_snapshot()
            time.sleep(0.01)

        # Manually set last snapshot to very low velocity
        tracker.snapshots[-1].velocity = 0.1
        tracker._detect_bottlenecks()

        # Should have detected velocity degradation
        velocity_alerts = [b for b in tracker.bottlenecks if "degradation" in b.description.lower()]
        assert len(velocity_alerts) > 0

    def test_milestone_variance_detection(self):
        """Test detection of milestone duration variance."""
        tracker = ProgressTracker(enable_bottleneck_detection=True)
        milestone = Milestone(name="Slow Task", expected_duration=1.0)
        milestone.started_at = datetime.now()
        milestone.actual_duration = 5.0  # 400% variance
        milestone.status = MilestoneStatus.COMPLETED

        tracker.milestones.append(milestone)
        tracker._detect_bottlenecks()

        # Should detect high variance
        variance_alerts = [b for b in tracker.bottlenecks if "longer than expected" in b.description]
        assert len(variance_alerts) > 0
        assert variance_alerts[0].severity == BottleneckSeverity.HIGH

    def test_stalled_progress_detection(self):
        """Test detection of stalled progress."""
        tracker = ProgressTracker(enable_bottleneck_detection=True)
        tracker.start_tracking()
        tracker.current_state = ProgressState.RUNNING

        # Create 5 snapshots with same completion
        for _ in range(5):
            tracker.snapshots.append(
                tracker.snapshots[-1]  # Duplicate last snapshot
            )

        tracker._detect_bottlenecks()

        # Should detect stalled progress
        stalled_alerts = [b for b in tracker.bottlenecks if "No progress" in b.description]
        assert len(stalled_alerts) > 0
        assert stalled_alerts[0].severity == BottleneckSeverity.CRITICAL

    def test_manual_bottleneck_detection(self):
        """Test manual bottleneck detection trigger."""
        tracker = ProgressTracker(enable_bottleneck_detection=True)
        tracker.start_tracking()

        initial_count = len(tracker.bottlenecks)
        new_alerts = tracker.detect_bottlenecks()

        assert isinstance(new_alerts, list)


class TestStatusAndReporting:
    """Test status retrieval and report generation."""

    def test_get_status(self):
        """Test get_status returns correct format."""
        tracker = ProgressTracker(task_id="test-123", total_steps=5)
        tracker.start_tracking()
        tracker.update_progress(completion_pct=40.0)

        status = tracker.get_status()

        assert status["task_id"] == "test-123"
        assert status["state"] == "running"
        assert status["completion_percentage"] == 40.0
        assert status["milestones_completed"] == 2
        assert status["total_milestones"] == 5
        assert "elapsed_time" in status
        assert "velocity" in status

    def test_generate_report(self):
        """Test comprehensive report generation."""
        tracker = ProgressTracker(task_id="report-test")
        tracker.start_tracking()
        tracker.update_progress(completion_pct=50.0)

        report = tracker.generate_report()

        assert report.task_id == "report-test"
        assert report.current_state == "running"
        assert report.completion_pct == 50.0
        assert len(report.milestones) > 0
        assert len(report.snapshots) > 0
        assert isinstance(report.summary, dict)

    def test_export_to_json(self):
        """Test JSON export functionality."""
        tracker = ProgressTracker(task_id="json-test")
        tracker.start_tracking()
        tracker.update_progress(completion_pct=75.0)

        json_str = tracker.export_to_json()

        # Validate JSON structure
        data = json.loads(json_str)
        assert data["task_id"] == "json-test"
        assert data["completion_pct"] == 75.0
        assert "milestones" in data
        assert "snapshots" in data

    def test_export_to_json_file(self, tmp_path):
        """Test exporting report to JSON file."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        file_path = tmp_path / "progress_report.json"
        tracker.export_to_json(file_path)

        assert file_path.exists()

        # Validate file contents
        with file_path.open() as f:
            data = json.load(f)
        assert "task_id" in data
        assert "completion_pct" in data

    def test_summary_statistics(self):
        """Test summary statistics generation."""
        milestones = [
            Milestone(name="M1", expected_duration=10.0),
            Milestone(name="M2", expected_duration=20.0),
        ]

        tracker = ProgressTracker()
        tracker.start_tracking(milestones)

        # Complete milestones with variance
        tracker.milestones[0].status = MilestoneStatus.COMPLETED
        tracker.milestones[0].started_at = datetime.now()
        tracker.milestones[0].actual_duration = 15.0  # 50% variance

        summary = tracker._generate_summary_statistics()

        assert summary["total_milestones"] == 2
        assert summary["completed_milestones"] == 1
        assert "avg_variance_pct" in summary


class TestStateManagement:
    """Test state management operations."""

    def test_pause_and_resume(self):
        """Test pausing and resuming tracking."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        assert tracker.current_state == ProgressState.RUNNING

        tracker.pause()
        assert tracker.current_state == ProgressState.PAUSED

        tracker.resume()
        assert tracker.current_state == ProgressState.RUNNING

    def test_complete_marks_terminal_state(self):
        """Test completing tracking."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        tracker.complete()

        assert tracker.current_state == ProgressState.COMPLETED
        assert tracker.completed_at is not None

    def test_fail_marks_terminal_state(self):
        """Test failing tracking."""
        tracker = ProgressTracker()
        tracker.start_tracking()

        tracker.fail(error_message="Test error")

        assert tracker.current_state == ProgressState.FAILED
        assert tracker.completed_at is not None

        # Should create critical bottleneck alert
        critical_alerts = [b for b in tracker.bottlenecks if b.severity == BottleneckSeverity.CRITICAL]
        assert len(critical_alerts) > 0

    def test_auto_resume_on_update(self):
        """Test automatic resume when updating from paused state."""
        tracker = ProgressTracker()
        tracker.start_tracking()
        tracker.pause()

        assert tracker.current_state == ProgressState.PAUSED

        tracker.update_progress(completion_pct=50.0)

        assert tracker.current_state == ProgressState.RUNNING


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_full_workflow_execution(self):
        """Test complete workflow from start to finish."""
        # Setup
        milestones = [
            Milestone(name="Initialize", expected_duration=1.0),
            Milestone(name="Process", expected_duration=3.0),
            Milestone(name="Finalize", expected_duration=1.0),
        ]

        tracker = ProgressTracker(task_id="workflow-test", total_steps=3)
        tracker.start_tracking(milestones)

        # Execute workflow
        time.sleep(0.1)
        tracker.update_progress(milestone_name="Initialize")

        time.sleep(0.1)
        tracker.update_progress(milestone_name="Process")

        time.sleep(0.1)
        tracker.update_progress(milestone_name="Finalize")

        tracker.complete()

        # Verify
        assert tracker.current_state == ProgressState.COMPLETED
        assert tracker._completed_steps == 3
        assert all(m.status == MilestoneStatus.COMPLETED for m in tracker.milestones)

        # Generate report
        report = tracker.generate_report()
        assert report.completion_pct == 100.0
        assert len(report.snapshots) > 0

    def test_workflow_with_bottleneck(self):
        """Test workflow that triggers bottleneck detection."""
        tracker = ProgressTracker(enable_bottleneck_detection=True, snapshot_interval=0.01)

        milestone = Milestone(name="Slow Task", expected_duration=0.05)
        tracker.start_tracking([milestone])

        # Simulate slow execution
        time.sleep(0.2)
        tracker.update_progress(milestone_name="Slow Task")

        # Check for variance bottleneck
        tracker._detect_bottlenecks()

        variance_bottlenecks = [
            b for b in tracker.bottlenecks
            if b.milestone_name == "Slow Task"
        ]
        assert len(variance_bottlenecks) > 0

    def test_concurrent_milestone_tracking(self):
        """Test tracking multiple milestones in sequence."""
        milestones = [
            Milestone(name=f"Task {i}", expected_duration=0.05)
            for i in range(5)
        ]

        tracker = ProgressTracker()
        tracker.start_tracking(milestones)

        for i, milestone in enumerate(milestones):
            time.sleep(0.02)
            tracker.update_progress(milestone_name=milestone.name)

            status = tracker.get_status()
            expected_completion = ((i + 1) / 5) * 100
            assert abs(status["completion_percentage"] - expected_completion) < 1.0

        assert tracker._completed_steps == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

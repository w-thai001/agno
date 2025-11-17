"""
Progress Tracker FSA - Production-ready progress tracking with real-time monitoring.

This module provides comprehensive progress tracking capabilities including:
- Real-time execution monitoring with milestone tracking
- Time estimation vs actual tracking with variance analysis
- Multi-dimensional progress metrics
- Bottleneck detection and alerting
- Historical pattern analysis for future estimates
"""

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agno.progress.models import (
    BottleneckAlert,
    BottleneckSeverity,
    Milestone,
    MilestoneStatus,
    ProgressReport,
    ProgressSnapshot,
)
from agno.progress.state import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    ProgressState,
    StateTransitionError,
    is_active_state,
    is_terminal_state,
    validate_transition,
)


class ProgressTracker:
    """
    Production-ready Progress Tracker with FSA-based state management.

    This tracker provides real-time monitoring, metrics calculation, bottleneck
    detection, and historical analysis for task execution.

    Attributes:
        task_id: Unique identifier for the tracked task
        total_steps: Total number of steps/milestones expected
        current_state: Current FSA state
        milestones: List of execution milestones
        snapshots: Historical progress snapshots
        bottlenecks: Detected bottleneck alerts
    """

    def __init__(
        self,
        task_id: Optional[str] = None,
        total_steps: int = 1,
        enable_bottleneck_detection: bool = True,
        snapshot_interval: float = 1.0,
    ):
        """
        Initialize the Progress Tracker.

        Args:
            task_id: Unique task identifier (auto-generated if None)
            total_steps: Expected number of steps/milestones
            enable_bottleneck_detection: Enable automatic bottleneck detection
            snapshot_interval: Minimum seconds between snapshots
        """
        self.task_id = task_id or str(uuid4())
        self.total_steps = max(1, total_steps)
        self.enable_bottleneck_detection = enable_bottleneck_detection
        self.snapshot_interval = snapshot_interval

        # FSA state
        self.current_state = ProgressState.IDLE

        # Tracking data
        self.milestones: List[Milestone] = []
        self.snapshots: List[ProgressSnapshot] = []
        self.bottlenecks: List[BottleneckAlert] = []

        # Timing
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.last_snapshot_time: Optional[datetime] = None

        # Metrics
        self._completed_steps = 0
        self._current_milestone_index = -1

    def start_tracking(self, milestones: Optional[List[Milestone]] = None) -> None:
        """
        Start progress tracking and transition to QUEUED state.

        Args:
            milestones: Optional list of predefined milestones

        Raises:
            StateTransitionError: If transition from current state is invalid
        """
        self._transition_state(ProgressState.QUEUED)
        self.started_at = datetime.now()

        if milestones:
            self.milestones = milestones
            self.total_steps = len(milestones)
        elif not self.milestones:
            # Create default milestones if none provided
            for i in range(self.total_steps):
                self.milestones.append(
                    Milestone(
                        name=f"Step {i + 1}",
                        expected_duration=10.0,  # Default 10 seconds per step
                    )
                )

        self._create_snapshot()
        self._transition_state(ProgressState.RUNNING)

    def update_progress(
        self,
        milestone_name: Optional[str] = None,
        completion_pct: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update progress with new milestone completion or percentage.

        Args:
            milestone_name: Name of milestone to mark complete
            completion_pct: Direct completion percentage (0-100)
            metadata: Additional metadata to attach to the update

        Raises:
            ValueError: If neither milestone_name nor completion_pct provided
        """
        if not is_active_state(self.current_state):
            # Auto-resume if paused/waiting
            if self.current_state in {ProgressState.PAUSED, ProgressState.WAITING}:
                self._transition_state(ProgressState.RUNNING)

        now = datetime.now()

        # Update milestone if specified
        if milestone_name:
            self._complete_milestone(milestone_name, now, metadata)
        elif completion_pct is not None:
            self._update_completion_percentage(completion_pct)

        # Create snapshot if enough time has passed
        if self._should_create_snapshot(now):
            self._create_snapshot()

        # Check for bottlenecks
        if self.enable_bottleneck_detection:
            self._detect_bottlenecks()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status with all metrics.

        Returns:
            Dictionary containing current state, metrics, and progress info
        """
        elapsed_time = self._get_elapsed_time()
        completion_pct = self._calculate_completion_percentage()
        velocity = self._calculate_velocity()
        eta = self._estimate_remaining_time(completion_pct, velocity)

        return {
            "task_id": self.task_id,
            "state": self.current_state.value,
            "completion_percentage": round(completion_pct, 2),
            "elapsed_time": round(elapsed_time, 2),
            "estimated_remaining": round(eta, 2) if eta else None,
            "velocity": round(velocity, 4),
            "milestones_completed": self._completed_steps,
            "total_milestones": self.total_steps,
            "current_milestone": self._get_current_milestone_name(),
            "active_bottlenecks": len([b for b in self.bottlenecks if b.severity in {BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL}]),
        }

    def detect_bottlenecks(self) -> List[BottleneckAlert]:
        """
        Manually trigger bottleneck detection and return alerts.

        Returns:
            List of newly detected bottleneck alerts
        """
        initial_count = len(self.bottlenecks)
        self._detect_bottlenecks()
        return self.bottlenecks[initial_count:]

    def generate_report(self) -> ProgressReport:
        """
        Generate comprehensive progress report with analytics.

        Returns:
            ProgressReport with all metrics, milestones, and insights
        """
        elapsed_time = self._get_elapsed_time()
        completion_pct = self._calculate_completion_percentage()
        velocity = self._calculate_velocity()
        eta = self._estimate_remaining_time(completion_pct, velocity)

        # Calculate summary statistics
        summary = self._generate_summary_statistics()

        return ProgressReport(
            task_id=self.task_id,
            started_at=self.started_at or datetime.now(),
            completed_at=self.completed_at,
            current_state=self.current_state.value,
            completion_pct=completion_pct,
            elapsed_time=elapsed_time,
            estimated_remaining=eta,
            velocity=velocity,
            milestones=self.milestones,
            snapshots=self.snapshots,
            bottlenecks=self.bottlenecks,
            summary=summary,
        )

    def export_to_json(self, file_path: Optional[Path] = None) -> str:
        """
        Export progress report to JSON format.

        Args:
            file_path: Optional path to save JSON file

        Returns:
            JSON string representation of the report
        """
        report = self.generate_report()
        json_data = json.dumps(report.to_dict(), indent=2)

        if file_path:
            file_path.write_text(json_data)

        return json_data

    def pause(self) -> None:
        """Pause tracking (transition to PAUSED state)."""
        self._transition_state(ProgressState.PAUSED)
        self._create_snapshot()

    def resume(self) -> None:
        """Resume tracking (transition back to RUNNING state)."""
        if self.current_state == ProgressState.PAUSED:
            self._transition_state(ProgressState.RUNNING)
            self._create_snapshot()

    def complete(self) -> None:
        """Mark tracking as completed (transition to COMPLETED state)."""
        self.completed_at = datetime.now()
        self._transition_state(ProgressState.COMPLETED)
        self._create_snapshot()

    def fail(self, error_message: Optional[str] = None) -> None:
        """
        Mark tracking as failed (transition to FAILED state).

        Args:
            error_message: Optional error description
        """
        self.completed_at = datetime.now()
        self._transition_state(ProgressState.FAILED)

        if error_message:
            self.bottlenecks.append(
                BottleneckAlert(
                    detected_at=datetime.now(),
                    severity=BottleneckSeverity.CRITICAL,
                    description=f"Task failed: {error_message}",
                    suggestion="Review error logs and retry",
                )
            )

        self._create_snapshot()

    # Private helper methods

    def _transition_state(self, new_state: ProgressState) -> None:
        """
        Transition to a new FSA state with validation.

        Args:
            new_state: Target state

        Raises:
            StateTransitionError: If transition is invalid
        """
        if not validate_transition(self.current_state, new_state):
            raise StateTransitionError(self.current_state, new_state)

        self.current_state = new_state

    def _complete_milestone(
        self,
        milestone_name: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Complete a specific milestone and update metrics."""
        for idx, milestone in enumerate(self.milestones):
            if milestone.name == milestone_name and milestone.status != MilestoneStatus.COMPLETED:
                if milestone.started_at is None:
                    milestone.started_at = timestamp

                milestone.completed_at = timestamp
                milestone.actual_duration = (timestamp - milestone.started_at).total_seconds()
                milestone.status = MilestoneStatus.COMPLETED

                if metadata:
                    milestone.metadata.update(metadata)

                self._completed_steps += 1
                self._current_milestone_index = idx
                break

    def _update_completion_percentage(self, pct: float) -> None:
        """Update completion based on percentage."""
        pct = max(0.0, min(100.0, pct))
        self._completed_steps = int((pct / 100.0) * self.total_steps)

    def _get_elapsed_time(self) -> float:
        """Get total elapsed time in seconds."""
        if not self.started_at:
            return 0.0

        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def _calculate_completion_percentage(self) -> float:
        """Calculate current completion percentage."""
        if self.total_steps == 0:
            return 0.0
        return (self._completed_steps / self.total_steps) * 100.0

    def _calculate_velocity(self) -> float:
        """
        Calculate velocity (progress per second).

        Returns:
            Velocity in completion percentage per second
        """
        elapsed = self._get_elapsed_time()
        if elapsed == 0:
            return 0.0

        completion_pct = self._calculate_completion_percentage()
        return completion_pct / elapsed

    def _estimate_remaining_time(self, completion_pct: float, velocity: float) -> Optional[float]:
        """
        Estimate remaining time based on current velocity.

        Args:
            completion_pct: Current completion percentage
            velocity: Current velocity

        Returns:
            Estimated seconds remaining, or None if cannot estimate
        """
        if velocity == 0 or completion_pct >= 100:
            return None

        remaining_pct = 100.0 - completion_pct
        return remaining_pct / velocity

    def _get_current_milestone_name(self) -> Optional[str]:
        """Get name of current milestone being worked on."""
        for milestone in self.milestones:
            if milestone.status == MilestoneStatus.IN_PROGRESS:
                return milestone.name

        # Return next pending milestone
        for milestone in self.milestones:
            if milestone.status == MilestoneStatus.PENDING:
                return milestone.name

        return None

    def _should_create_snapshot(self, now: datetime) -> bool:
        """Determine if enough time has passed to create a new snapshot."""
        if not self.last_snapshot_time:
            return True

        elapsed = (now - self.last_snapshot_time).total_seconds()
        return elapsed >= self.snapshot_interval

    def _create_snapshot(self) -> None:
        """Create a progress snapshot with current metrics."""
        now = datetime.now()
        elapsed = self._get_elapsed_time()
        completion_pct = self._calculate_completion_percentage()
        velocity = self._calculate_velocity()
        eta = self._estimate_remaining_time(completion_pct, velocity)

        snapshot = ProgressSnapshot(
            timestamp=now,
            completion_pct=completion_pct,
            velocity=velocity,
            current_milestone=self._get_current_milestone_name(),
            elapsed_time=elapsed,
            estimated_remaining=eta,
            metrics={
                "state": self.current_state.value,
                "completed_steps": self._completed_steps,
                "total_steps": self.total_steps,
            },
        )

        self.snapshots.append(snapshot)
        self.last_snapshot_time = now

    def _detect_bottlenecks(self) -> None:
        """Detect bottlenecks based on velocity and milestone variance."""
        now = datetime.now()

        # Check velocity degradation
        if len(self.snapshots) >= 3:
            recent_velocities = [s.velocity for s in self.snapshots[-5:]]
            if len(recent_velocities) >= 3:
                avg_velocity = statistics.mean(recent_velocities)
                current_velocity = self.snapshots[-1].velocity

                if current_velocity < avg_velocity * 0.5 and current_velocity > 0:
                    self.bottlenecks.append(
                        BottleneckAlert(
                            detected_at=now,
                            severity=BottleneckSeverity.MEDIUM,
                            description=f"Velocity degradation detected: {current_velocity:.4f} vs avg {avg_velocity:.4f}",
                            suggestion="Review recent operations for performance issues",
                            metrics={"current_velocity": current_velocity, "avg_velocity": avg_velocity},
                        )
                    )

        # Check milestone duration variance
        for milestone in self.milestones:
            if milestone.status == MilestoneStatus.COMPLETED and milestone.variance_percentage:
                if milestone.variance_percentage > 100:  # Over 100% variance
                    self.bottlenecks.append(
                        BottleneckAlert(
                            detected_at=now,
                            severity=BottleneckSeverity.HIGH,
                            description=f"Milestone '{milestone.name}' took {milestone.variance_percentage:.1f}% longer than expected",
                            suggestion="Adjust time estimates or optimize this step",
                            milestone_name=milestone.name,
                            metrics={
                                "expected": milestone.expected_duration,
                                "actual": milestone.actual_duration,
                                "variance_pct": milestone.variance_percentage,
                            },
                        )
                    )

        # Check for stalled progress
        if len(self.snapshots) >= 5:
            recent_completion = [s.completion_pct for s in self.snapshots[-5:]]
            if len(set(recent_completion)) == 1 and is_active_state(self.current_state):
                self.bottlenecks.append(
                    BottleneckAlert(
                        detected_at=now,
                        severity=BottleneckSeverity.CRITICAL,
                        description="No progress detected in last 5 snapshots",
                        suggestion="Check for deadlock or infinite loop",
                        metrics={"completion_pct": recent_completion[0]},
                    )
                )

    def _generate_summary_statistics(self) -> Dict[str, Any]:
        """Generate summary statistics for the report."""
        completed_milestones = [m for m in self.milestones if m.status == MilestoneStatus.COMPLETED]

        summary: Dict[str, Any] = {
            "total_milestones": len(self.milestones),
            "completed_milestones": len(completed_milestones),
            "failed_milestones": len([m for m in self.milestones if m.status == MilestoneStatus.FAILED]),
            "total_snapshots": len(self.snapshots),
            "total_bottlenecks": len(self.bottlenecks),
        }

        # Variance statistics
        if completed_milestones:
            variances = [m.variance_percentage for m in completed_milestones if m.variance_percentage is not None]
            if variances:
                summary["avg_variance_pct"] = statistics.mean(variances)
                summary["max_variance_pct"] = max(variances)
                summary["min_variance_pct"] = min(variances)

        # Velocity statistics
        if len(self.snapshots) > 1:
            velocities = [s.velocity for s in self.snapshots if s.velocity > 0]
            if velocities:
                summary["avg_velocity"] = statistics.mean(velocities)
                summary["max_velocity"] = max(velocities)
                summary["min_velocity"] = min(velocities)

        return summary

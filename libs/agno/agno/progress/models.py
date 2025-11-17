"""
Data models for Progress Tracker FSA.

This module contains the core data structures used for tracking execution progress,
including snapshots, milestones, and bottleneck alerts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MilestoneStatus(str, Enum):
    """Status of a milestone in the execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class BottleneckSeverity(str, Enum):
    """Severity level for bottleneck alerts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Milestone:
    """
    Represents a milestone in the execution process.

    Attributes:
        name: Human-readable milestone name
        expected_duration: Expected duration in seconds
        actual_duration: Actual duration in seconds (None if not completed)
        status: Current status of the milestone
        started_at: Timestamp when milestone started
        completed_at: Timestamp when milestone completed
        metadata: Additional metadata for the milestone
    """

    name: str
    expected_duration: float
    actual_duration: Optional[float] = None
    status: MilestoneStatus = MilestoneStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_variance(self) -> Optional[float]:
        """Calculate variance between expected and actual duration."""
        if self.actual_duration is None:
            return None
        return self.actual_duration - self.expected_duration

    @property
    def variance_percentage(self) -> Optional[float]:
        """Calculate variance as percentage of expected duration."""
        if self.actual_duration is None or self.expected_duration == 0:
            return None
        return ((self.actual_duration - self.expected_duration) / self.expected_duration) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary."""
        return {
            "name": self.name,
            "expected_duration": self.expected_duration,
            "actual_duration": self.actual_duration,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_variance": self.duration_variance,
            "variance_percentage": self.variance_percentage,
            "metadata": self.metadata,
        }


@dataclass
class ProgressSnapshot:
    """
    Represents a point-in-time snapshot of progress metrics.

    Attributes:
        timestamp: When this snapshot was taken
        completion_pct: Completion percentage (0-100)
        velocity: Current velocity (progress units per second)
        current_milestone: Name of the current milestone
        elapsed_time: Total elapsed time in seconds
        estimated_remaining: Estimated time remaining in seconds
        metrics: Additional computed metrics
    """

    timestamp: datetime
    completion_pct: float
    velocity: float
    current_milestone: Optional[str] = None
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "completion_pct": round(self.completion_pct, 2),
            "velocity": round(self.velocity, 4),
            "current_milestone": self.current_milestone,
            "elapsed_time": round(self.elapsed_time, 2),
            "estimated_remaining": round(self.estimated_remaining, 2) if self.estimated_remaining else None,
            "metrics": self.metrics,
        }


@dataclass
class BottleneckAlert:
    """
    Represents a detected bottleneck in execution.

    Attributes:
        detected_at: Timestamp when bottleneck was detected
        severity: Severity level of the bottleneck
        description: Human-readable description
        suggestion: Suggested action to resolve bottleneck
        milestone_name: Name of milestone where bottleneck occurred
        metrics: Relevant metrics that triggered the alert
    """

    detected_at: datetime
    severity: BottleneckSeverity
    description: str
    suggestion: str
    milestone_name: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert bottleneck alert to dictionary."""
        return {
            "detected_at": self.detected_at.isoformat(),
            "severity": self.severity.value,
            "description": self.description,
            "suggestion": self.suggestion,
            "milestone_name": self.milestone_name,
            "metrics": self.metrics,
        }


@dataclass
class ProgressReport:
    """
    Comprehensive progress report with all metrics and analytics.

    Attributes:
        task_id: Unique identifier for the tracked task
        started_at: When tracking started
        completed_at: When tracking completed (if finished)
        current_state: Current FSA state
        completion_pct: Overall completion percentage
        elapsed_time: Total elapsed time
        estimated_remaining: Estimated time remaining
        velocity: Current velocity metric
        milestones: List of all milestones
        snapshots: Historical snapshots
        bottlenecks: Detected bottlenecks
        summary: Summary statistics and insights
    """

    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_state: str = "idle"
    completion_pct: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    velocity: float = 0.0
    milestones: List[Milestone] = field(default_factory=list)
    snapshots: List[ProgressSnapshot] = field(default_factory=list)
    bottlenecks: List[BottleneckAlert] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON export."""
        return {
            "task_id": self.task_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_state": self.current_state,
            "completion_pct": round(self.completion_pct, 2),
            "elapsed_time": round(self.elapsed_time, 2),
            "estimated_remaining": round(self.estimated_remaining, 2) if self.estimated_remaining else None,
            "velocity": round(self.velocity, 4),
            "milestones": [m.to_dict() for m in self.milestones],
            "snapshots": [s.to_dict() for s in self.snapshots],
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "summary": self.summary,
        }

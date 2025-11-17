"""
Progress Tracker FSA (Finite State Automaton) for monitoring execution progress.

This module provides a comprehensive progress tracking system that monitors task/action
execution, calculates progress metrics, and provides real-time reporting capabilities.

Features:
- Task state tracking (IDLE, STARTED, IN_PROGRESS, COMPLETED, FAILED)
- Progress metrics (completion %, time elapsed, ETA)
- Performance metrics (throughput, success rate, error rate)
- Real-time status updates and milestone tracking
- Support for parallel task tracking
- Alert system for critical events
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

from agno.utils.log import logger


class TaskState(str, Enum):
    """Enumeration of possible task states in the FSA."""
    IDLE = "idle"  # Task has been created but not started
    STARTED = "started"  # Task has been initiated
    IN_PROGRESS = "in_progress"  # Task is actively being processed
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"  # Task failed with error


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TaskInfo:
    """
    Information about a tracked task.

    Attributes:
        task_id: Unique identifier for the task
        name: Human-readable task name
        state: Current state of the task
        created_at: Timestamp when task was created
        started_at: Timestamp when task started execution
        completed_at: Timestamp when task completed/failed
        progress: Current progress percentage (0-100)
        error: Error message if task failed
        metadata: Additional task metadata
        parent_id: ID of parent task for hierarchical tracking
        subtask_ids: IDs of child tasks
    """
    task_id: str
    name: str
    state: TaskState = TaskState.IDLE
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    subtask_ids: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task info to dictionary."""
        data = asdict(self)
        data['state'] = self.state.value
        data['subtask_ids'] = list(self.subtask_ids)
        return data

    def get_duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at if self.completed_at else time.time()
        return end_time - self.started_at

    def is_active(self) -> bool:
        """Check if task is in an active state."""
        return self.state in {TaskState.STARTED, TaskState.IN_PROGRESS}

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in {TaskState.COMPLETED, TaskState.FAILED}


@dataclass
class ProgressMetrics:
    """
    Progress metrics for tracking overall execution.

    Attributes:
        total_tasks: Total number of tasks
        completed_tasks: Number of completed tasks
        failed_tasks: Number of failed tasks
        active_tasks: Number of tasks currently active
        completion_percentage: Overall completion percentage
        elapsed_time: Total elapsed time in seconds
        estimated_time_remaining: Estimated time to completion
        average_task_duration: Average duration per task
    """
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_tasks: int = 0
    completion_percentage: float = 0.0
    elapsed_time: float = 0.0
    estimated_time_remaining: Optional[float] = None
    average_task_duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """
    Performance metrics for monitoring execution efficiency.

    Attributes:
        throughput: Tasks completed per second
        success_rate: Percentage of successful tasks
        error_rate: Percentage of failed tasks
        average_completion_time: Average time to complete tasks
        peak_concurrent_tasks: Maximum concurrent tasks
        total_processing_time: Total time spent processing
    """
    throughput: float = 0.0
    success_rate: float = 0.0
    error_rate: float = 0.0
    average_completion_time: float = 0.0
    peak_concurrent_tasks: int = 0
    total_processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class Alert:
    """
    Alert for critical events or milestones.

    Attributes:
        level: Alert severity level
        message: Alert message
        task_id: Associated task ID (if applicable)
        timestamp: When the alert was created
        metadata: Additional alert data
    """
    level: AlertLevel
    message: str
    task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        data = asdict(self)
        data['level'] = self.level.value
        return data


@dataclass
class Milestone:
    """
    Milestone for tracking significant events.

    Attributes:
        name: Milestone name
        target_percentage: Target completion percentage
        achieved: Whether milestone has been reached
        achieved_at: Timestamp when milestone was achieved
    """
    name: str
    target_percentage: float
    achieved: bool = False
    achieved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary."""
        return asdict(self)


class ProgressTrackerFSA:
    """
    Finite State Automaton for tracking execution progress.

    This class provides comprehensive progress tracking capabilities including:
    - Task state management with FSA transitions
    - Real-time progress calculation
    - Performance metrics monitoring
    - Alert generation for critical events
    - Milestone tracking
    - Support for parallel task execution

    Example:
        >>> tracker = ProgressTrackerFSA()
        >>> tracker.create_task("task1", "Process data")
        >>> tracker.start_task("task1")
        >>> tracker.update_progress("task1", 50.0)
        >>> tracker.complete_task("task1")
        >>> report = tracker.get_progress_report()
    """

    def __init__(
        self,
        enable_alerts: bool = True,
        alert_thresholds: Optional[Dict[str, float]] = None,
        milestones: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the Progress Tracker FSA.

        Args:
            enable_alerts: Whether to generate alerts
            alert_thresholds: Custom thresholds for alerts (e.g., {'error_rate': 0.1})
            milestones: List of milestone definitions
        """
        # Core tracking data
        self.tasks: Dict[str, TaskInfo] = {}
        self.alerts: List[Alert] = []
        self.milestones: List[Milestone] = []

        # Configuration
        self.enable_alerts = enable_alerts
        self.alert_thresholds = alert_thresholds or {
            'error_rate': 0.1,  # Alert if error rate exceeds 10%
            'task_timeout': 300.0,  # Alert if task takes more than 5 minutes
        }

        # Initialize milestones
        if milestones is not None:
            for milestone_def in milestones:
                self.milestones.append(
                    Milestone(
                        name=milestone_def.get('name', 'Unnamed'),
                        target_percentage=milestone_def.get('target_percentage', 0.0)
                    )
                )
        else:
            # Default milestones
            self.milestones = [
                Milestone(name="25% Complete", target_percentage=25.0),
                Milestone(name="50% Complete", target_percentage=50.0),
                Milestone(name="75% Complete", target_percentage=75.0),
                Milestone(name="100% Complete", target_percentage=100.0),
            ]

        # Performance tracking
        self.start_time: float = time.time()
        self.peak_concurrent: int = 0

        # State transition history for analysis
        self.state_transitions: List[Dict[str, Any]] = []

        logger.debug("ProgressTrackerFSA initialized")

    # ========== Task Management Methods ==========

    def create_task(
        self,
        task_id: str,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskInfo:
        """
        Create a new task in IDLE state.

        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            parent_id: Optional parent task ID for hierarchical tracking
            metadata: Optional metadata dictionary

        Returns:
            TaskInfo object for the created task

        Raises:
            ValueError: If task_id already exists
        """
        if task_id in self.tasks:
            raise ValueError(f"Task {task_id} already exists")

        task = TaskInfo(
            task_id=task_id,
            name=name,
            state=TaskState.IDLE,
            parent_id=parent_id,
            metadata=metadata or {}
        )

        self.tasks[task_id] = task

        # Update parent's subtask list
        if parent_id and parent_id in self.tasks:
            self.tasks[parent_id].subtask_ids.add(task_id)

        self._record_transition(task_id, None, TaskState.IDLE)
        logger.debug(f"Created task {task_id}: {name}")

        return task

    def start_task(self, task_id: str) -> TaskInfo:
        """
        Transition task from IDLE to STARTED state.

        Args:
            task_id: Task identifier

        Returns:
            Updated TaskInfo object

        Raises:
            ValueError: If task doesn't exist or invalid state transition
        """
        task = self._get_task(task_id)

        if task.state != TaskState.IDLE:
            raise ValueError(
                f"Invalid state transition: {task.state} -> STARTED. "
                f"Task must be in IDLE state"
            )

        task.state = TaskState.STARTED
        task.started_at = time.time()

        self._record_transition(task_id, TaskState.IDLE, TaskState.STARTED)
        self._update_peak_concurrent()
        logger.debug(f"Started task {task_id}")

        return task

    def mark_in_progress(self, task_id: str) -> TaskInfo:
        """
        Transition task to IN_PROGRESS state.

        Args:
            task_id: Task identifier

        Returns:
            Updated TaskInfo object

        Raises:
            ValueError: If task doesn't exist or invalid state transition
        """
        task = self._get_task(task_id)

        if task.state not in {TaskState.STARTED, TaskState.IN_PROGRESS}:
            raise ValueError(
                f"Invalid state transition: {task.state} -> IN_PROGRESS. "
                f"Task must be in STARTED or IN_PROGRESS state"
            )

        old_state = task.state
        task.state = TaskState.IN_PROGRESS

        # Set started_at if not already set
        if task.started_at is None:
            task.started_at = time.time()

        self._record_transition(task_id, old_state, TaskState.IN_PROGRESS)
        self._update_peak_concurrent()
        logger.debug(f"Task {task_id} is now in progress")

        return task

    def update_progress(self, task_id: str, progress: float) -> TaskInfo:
        """
        Update task progress percentage.

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)

        Returns:
            Updated TaskInfo object

        Raises:
            ValueError: If task doesn't exist or invalid progress value
        """
        task = self._get_task(task_id)

        if not 0 <= progress <= 100:
            raise ValueError(f"Progress must be between 0 and 100, got {progress}")

        task.progress = progress

        # Check for milestone achievements
        self._check_milestones()

        # Check for timeout alerts
        if self.enable_alerts:
            self._check_task_timeout(task)

        logger.debug(f"Task {task_id} progress: {progress}%")

        return task

    def complete_task(self, task_id: str) -> TaskInfo:
        """
        Transition task to COMPLETED state.

        Args:
            task_id: Task identifier

        Returns:
            Updated TaskInfo object

        Raises:
            ValueError: If task doesn't exist or invalid state transition
        """
        task = self._get_task(task_id)

        if task.state not in {TaskState.STARTED, TaskState.IN_PROGRESS}:
            raise ValueError(
                f"Invalid state transition: {task.state} -> COMPLETED. "
                f"Task must be in STARTED or IN_PROGRESS state"
            )

        old_state = task.state
        task.state = TaskState.COMPLETED
        task.completed_at = time.time()
        task.progress = 100.0

        self._record_transition(task_id, old_state, TaskState.COMPLETED)

        # Check for milestone achievements
        self._check_milestones()

        logger.info(f"Task {task_id} completed in {task.get_duration():.2f}s")

        return task

    def fail_task(self, task_id: str, error: str) -> TaskInfo:
        """
        Transition task to FAILED state.

        Args:
            task_id: Task identifier
            error: Error message describing the failure

        Returns:
            Updated TaskInfo object

        Raises:
            ValueError: If task doesn't exist or invalid state transition
        """
        task = self._get_task(task_id)

        if task.state not in {TaskState.STARTED, TaskState.IN_PROGRESS}:
            raise ValueError(
                f"Invalid state transition: {task.state} -> FAILED. "
                f"Task must be in STARTED or IN_PROGRESS state"
            )

        old_state = task.state
        task.state = TaskState.FAILED
        task.completed_at = time.time()
        task.error = error

        self._record_transition(task_id, old_state, TaskState.FAILED)

        # Generate alert for task failure
        if self.enable_alerts:
            self._add_alert(
                AlertLevel.ERROR,
                f"Task failed: {task.name}",
                task_id=task_id,
                metadata={'error': error}
            )

        # Check error rate threshold
        if self.enable_alerts:
            self._check_error_rate()

        logger.error(f"Task {task_id} failed: {error}")

        return task

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task information.

        Args:
            task_id: Task identifier

        Returns:
            TaskInfo object or None if not found
        """
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[TaskInfo]:
        """Get list of all tasks."""
        return list(self.tasks.values())

    def get_tasks_by_state(self, state: TaskState) -> List[TaskInfo]:
        """
        Get all tasks in a specific state.

        Args:
            state: Task state to filter by

        Returns:
            List of TaskInfo objects
        """
        return [task for task in self.tasks.values() if task.state == state]

    def get_active_tasks(self) -> List[TaskInfo]:
        """Get all active tasks (STARTED or IN_PROGRESS)."""
        return [task for task in self.tasks.values() if task.is_active()]

    # ========== Metrics Calculation Methods ==========

    def calculate_progress_metrics(self) -> ProgressMetrics:
        """
        Calculate current progress metrics.

        Returns:
            ProgressMetrics object with current metrics
        """
        total = len(self.tasks)
        completed = len([t for t in self.tasks.values() if t.state == TaskState.COMPLETED])
        failed = len([t for t in self.tasks.values() if t.state == TaskState.FAILED])
        active = len([t for t in self.tasks.values() if t.is_active()])

        # Calculate completion percentage
        completion_pct = (completed / total * 100) if total > 0 else 0.0

        # Calculate elapsed time
        elapsed = time.time() - self.start_time

        # Calculate average task duration (from completed tasks)
        completed_tasks = [t for t in self.tasks.values() if t.state == TaskState.COMPLETED]
        avg_duration = None
        if completed_tasks:
            durations = [t.get_duration() for t in completed_tasks if t.get_duration()]
            avg_duration = sum(durations) / len(durations) if durations else None

        # Estimate time remaining
        eta = None
        if avg_duration and active > 0:
            remaining_tasks = total - completed - failed
            eta = remaining_tasks * avg_duration

        return ProgressMetrics(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            active_tasks=active,
            completion_percentage=completion_pct,
            elapsed_time=elapsed,
            estimated_time_remaining=eta,
            average_task_duration=avg_duration
        )

    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """
        Calculate performance metrics.

        Returns:
            PerformanceMetrics object with current performance data
        """
        total = len(self.tasks)
        completed = len([t for t in self.tasks.values() if t.state == TaskState.COMPLETED])
        failed = len([t for t in self.tasks.values() if t.state == TaskState.FAILED])

        # Calculate rates
        elapsed = time.time() - self.start_time
        throughput = completed / elapsed if elapsed > 0 else 0.0

        finished = completed + failed
        success_rate = (completed / finished * 100) if finished > 0 else 0.0
        error_rate = (failed / finished * 100) if finished > 0 else 0.0

        # Calculate average completion time
        completed_tasks = [t for t in self.tasks.values() if t.state == TaskState.COMPLETED]
        avg_completion = 0.0
        total_processing = 0.0
        if completed_tasks:
            durations = [t.get_duration() for t in completed_tasks if t.get_duration()]
            if durations:
                avg_completion = sum(durations) / len(durations)
                total_processing = sum(durations)

        return PerformanceMetrics(
            throughput=throughput,
            success_rate=success_rate,
            error_rate=error_rate,
            average_completion_time=avg_completion,
            peak_concurrent_tasks=self.peak_concurrent,
            total_processing_time=total_processing
        )

    # ========== Reporting Methods ==========

    def get_progress_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive progress report.

        Returns:
            Dictionary containing progress metrics, performance metrics,
            active tasks, and recent alerts
        """
        progress = self.calculate_progress_metrics()
        performance = self.calculate_performance_metrics()
        active_tasks = self.get_active_tasks()
        recent_alerts = self.get_recent_alerts(limit=10)

        return {
            'timestamp': time.time(),
            'progress_metrics': progress.to_dict(),
            'performance_metrics': performance.to_dict(),
            'active_tasks': [task.to_dict() for task in active_tasks],
            'recent_alerts': [alert.to_dict() for alert in recent_alerts],
            'milestones': [m.to_dict() for m in self.milestones],
            'summary': self._generate_summary()
        }

    def get_metrics_dashboard(self) -> Dict[str, Any]:
        """
        Generate metrics dashboard with key indicators.

        Returns:
            Dictionary with dashboard data suitable for visualization
        """
        progress = self.calculate_progress_metrics()
        performance = self.calculate_performance_metrics()

        # Get task distribution by state
        state_distribution = defaultdict(int)
        for task in self.tasks.values():
            state_distribution[task.state.value] += 1

        # Calculate ETA as human-readable string
        eta_str = "N/A"
        if progress.estimated_time_remaining:
            eta_str = self._format_duration(progress.estimated_time_remaining)

        return {
            'timestamp': time.time(),
            'overview': {
                'total_tasks': progress.total_tasks,
                'completion_percentage': f"{progress.completion_percentage:.1f}%",
                'elapsed_time': self._format_duration(progress.elapsed_time),
                'estimated_time_remaining': eta_str,
            },
            'performance': {
                'throughput': f"{performance.throughput:.2f} tasks/sec",
                'success_rate': f"{performance.success_rate:.1f}%",
                'error_rate': f"{performance.error_rate:.1f}%",
                'avg_completion_time': f"{performance.average_completion_time:.2f}s",
            },
            'state_distribution': dict(state_distribution),
            'concurrent_tasks': {
                'current': progress.active_tasks,
                'peak': self.peak_concurrent,
            },
            'alerts': {
                'total': len(self.alerts),
                'critical': len([a for a in self.alerts if a.level == AlertLevel.CRITICAL]),
                'errors': len([a for a in self.alerts if a.level == AlertLevel.ERROR]),
            },
            'milestones': {
                'total': len(self.milestones),
                'achieved': len([m for m in self.milestones if m.achieved]),
                'next': self._get_next_milestone()
            }
        }

    def get_task_report(self, task_id: str) -> Dict[str, Any]:
        """
        Generate detailed report for a specific task.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with detailed task information
        """
        task = self._get_task(task_id)

        # Get subtask information
        subtasks = []
        for subtask_id in task.subtask_ids:
            if subtask_id in self.tasks:
                subtasks.append(self.tasks[subtask_id].to_dict())

        # Get state transitions for this task
        transitions = [
            t for t in self.state_transitions
            if t.get('task_id') == task_id
        ]

        return {
            'task': task.to_dict(),
            'subtasks': subtasks,
            'transitions': transitions,
            'duration': task.get_duration(),
            'is_active': task.is_active(),
            'is_terminal': task.is_terminal(),
        }

    # ========== Alert Methods ==========

    def get_alerts(self) -> List[Alert]:
        """Get all alerts."""
        return self.alerts.copy()

    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of most recent alerts
        """
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """
        Get alerts by severity level.

        Args:
            level: Alert level to filter by

        Returns:
            List of alerts with specified level
        """
        return [alert for alert in self.alerts if alert.level == level]

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()
        logger.debug("Cleared all alerts")

    # ========== Milestone Methods ==========

    def add_milestone(self, name: str, target_percentage: float) -> Milestone:
        """
        Add a new milestone.

        Args:
            name: Milestone name
            target_percentage: Target completion percentage (0-100)

        Returns:
            Created Milestone object
        """
        milestone = Milestone(name=name, target_percentage=target_percentage)
        self.milestones.append(milestone)
        return milestone

    def get_milestones(self) -> List[Milestone]:
        """Get all milestones."""
        return self.milestones.copy()

    def get_achieved_milestones(self) -> List[Milestone]:
        """Get all achieved milestones."""
        return [m for m in self.milestones if m.achieved]

    # ========== Private Helper Methods ==========

    def _get_task(self, task_id: str) -> TaskInfo:
        """Get task or raise ValueError if not found."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        return self.tasks[task_id]

    def _record_transition(
        self,
        task_id: str,
        from_state: Optional[TaskState],
        to_state: TaskState
    ) -> None:
        """Record a state transition for analysis."""
        self.state_transitions.append({
            'task_id': task_id,
            'from_state': from_state.value if from_state else None,
            'to_state': to_state.value,
            'timestamp': time.time()
        })

    def _update_peak_concurrent(self) -> None:
        """Update peak concurrent tasks counter."""
        current = len(self.get_active_tasks())
        if current > self.peak_concurrent:
            self.peak_concurrent = current

    def _add_alert(
        self,
        level: AlertLevel,
        message: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an alert to the alerts list."""
        alert = Alert(
            level=level,
            message=message,
            task_id=task_id,
            metadata=metadata or {}
        )
        self.alerts.append(alert)
        logger.warning(f"Alert [{level.value}]: {message}")

    def _check_milestones(self) -> None:
        """Check if any milestones have been achieved."""
        progress = self.calculate_progress_metrics()

        for milestone in self.milestones:
            if not milestone.achieved and progress.completion_percentage >= milestone.target_percentage:
                milestone.achieved = True
                milestone.achieved_at = time.time()

                if self.enable_alerts:
                    self._add_alert(
                        AlertLevel.INFO,
                        f"Milestone achieved: {milestone.name}",
                        metadata={'target': milestone.target_percentage}
                    )

    def _check_task_timeout(self, task: TaskInfo) -> None:
        """Check if a task has exceeded timeout threshold."""
        duration = task.get_duration()
        timeout = self.alert_thresholds.get('task_timeout', 300.0)

        if duration and duration > timeout and task.is_active():
            self._add_alert(
                AlertLevel.WARNING,
                f"Task timeout: {task.name} running for {duration:.1f}s",
                task_id=task.task_id,
                metadata={'duration': duration, 'threshold': timeout}
            )

    def _check_error_rate(self) -> None:
        """Check if error rate exceeds threshold."""
        performance = self.calculate_performance_metrics()
        threshold = self.alert_thresholds.get('error_rate', 0.1) * 100

        if performance.error_rate > threshold:
            self._add_alert(
                AlertLevel.CRITICAL,
                f"Error rate {performance.error_rate:.1f}% exceeds threshold {threshold:.1f}%",
                metadata={'error_rate': performance.error_rate, 'threshold': threshold}
            )

    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        progress = self.calculate_progress_metrics()
        performance = self.calculate_performance_metrics()

        return (
            f"{progress.completed_tasks}/{progress.total_tasks} tasks completed "
            f"({progress.completion_percentage:.1f}%) with {performance.success_rate:.1f}% success rate. "
            f"{progress.active_tasks} tasks currently active."
        )

    def _get_next_milestone(self) -> Optional[str]:
        """Get the next unachieved milestone."""
        for milestone in sorted(self.milestones, key=lambda m: m.target_percentage):
            if not milestone.achieved:
                return milestone.name
        return None

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    # ========== Utility Methods ==========

    def reset(self) -> None:
        """Reset the tracker to initial state."""
        self.tasks.clear()
        self.alerts.clear()
        self.state_transitions.clear()
        self.start_time = time.time()
        self.peak_concurrent = 0

        # Reset milestones
        for milestone in self.milestones:
            milestone.achieved = False
            milestone.achieved_at = None

        logger.info("ProgressTrackerFSA reset")

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire tracker state to dictionary."""
        return {
            'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            'alerts': [alert.to_dict() for alert in self.alerts],
            'milestones': [m.to_dict() for m in self.milestones],
            'progress_metrics': self.calculate_progress_metrics().to_dict(),
            'performance_metrics': self.calculate_performance_metrics().to_dict(),
            'start_time': self.start_time,
            'peak_concurrent': self.peak_concurrent,
        }

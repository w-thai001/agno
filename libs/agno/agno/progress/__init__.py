"""
Progress Tracker FSA - Real-time execution monitoring for Agno framework.

This module provides comprehensive progress tracking capabilities including:
- FSA-based state management
- Real-time execution monitoring
- Time estimation and variance analysis
- Multi-dimensional progress metrics
- Bottleneck detection and alerting
- Historical pattern analysis

Example usage:
    ```python
    from agno.progress import ProgressTracker, Milestone

    # Create tracker with milestones
    tracker = ProgressTracker(task_id="my-task", total_steps=3)

    milestones = [
        Milestone(name="Data Loading", expected_duration=5.0),
        Milestone(name="Processing", expected_duration=10.0),
        Milestone(name="Saving Results", expected_duration=3.0),
    ]

    tracker.start_tracking(milestones)

    # Update progress
    tracker.update_progress(milestone_name="Data Loading")
    tracker.update_progress(milestone_name="Processing")

    # Get current status
    status = tracker.get_status()
    print(f"Completion: {status['completion_percentage']}%")

    # Generate report
    report = tracker.generate_report()
    tracker.export_to_json(Path("progress_report.json"))
    ```
"""

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
    INACTIVE_STATES,
    STATE_TRANSITIONS,
    TERMINAL_STATES,
    ProgressState,
    StateTransitionError,
    get_valid_transitions,
    is_active_state,
    is_terminal_state,
    validate_transition,
)
from agno.progress.tracker import ProgressTracker

__all__ = [
    # Main tracker
    "ProgressTracker",
    # States
    "ProgressState",
    "StateTransitionError",
    "STATE_TRANSITIONS",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
    "INACTIVE_STATES",
    "validate_transition",
    "get_valid_transitions",
    "is_active_state",
    "is_terminal_state",
    # Models
    "Milestone",
    "MilestoneStatus",
    "ProgressSnapshot",
    "BottleneckAlert",
    "BottleneckSeverity",
    "ProgressReport",
]

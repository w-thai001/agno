"""
Progress Tracker FSA Example - Real-time execution monitoring

This example demonstrates how to use the Progress Tracker FSA to monitor
long-running tasks with real-time metrics, bottleneck detection, and reporting.
"""

import sys
import time
from pathlib import Path

# Add libs to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "agno"))

from agno.progress import (
    ProgressTracker,
    Milestone,
    ProgressState,
    BottleneckSeverity,
)


def simulate_data_pipeline():
    """
    Simulate a data processing pipeline with progress tracking.

    This example shows:
    - Creating a tracker with predefined milestones
    - Updating progress as tasks complete
    - Real-time status monitoring
    - Bottleneck detection
    - Final report generation
    """
    print("=" * 70)
    print("Data Processing Pipeline with Progress Tracking")
    print("=" * 70)

    # Define pipeline milestones with expected durations
    milestones = [
        Milestone(name="Initialize Database", expected_duration=0.5),
        Milestone(name="Load Raw Data", expected_duration=1.0),
        Milestone(name="Data Validation", expected_duration=0.8),
        Milestone(name="Transform Data", expected_duration=2.0),
        Milestone(name="Run Analytics", expected_duration=1.5),
        Milestone(name="Generate Reports", expected_duration=0.7),
        Milestone(name="Save Results", expected_duration=0.5),
    ]

    # Create tracker with bottleneck detection enabled
    tracker = ProgressTracker(
        task_id="data-pipeline-001",
        enable_bottleneck_detection=True,
        snapshot_interval=0.5,  # Snapshot every 0.5 seconds
    )

    # Start tracking
    tracker.start_tracking(milestones)
    print(f"\n✓ Started tracking {len(milestones)} milestones\n")

    # Execute pipeline stages
    for i, milestone in enumerate(milestones):
        print(f"[{i+1}/{len(milestones)}] {milestone.name}...")

        # Simulate work (with some variance)
        work_duration = milestone.expected_duration * (0.8 + (i % 3) * 0.3)
        time.sleep(work_duration)

        # Update progress with metadata
        tracker.update_progress(
            milestone_name=milestone.name,
            metadata={
                "records_processed": (i + 1) * 1000,
                "stage": i + 1,
            },
        )

        # Display current status
        status = tracker.get_status()
        print(f"  ✓ Completed in {work_duration:.2f}s")
        print(f"  Progress: {status['completion_percentage']:.1f}%")
        print(f"  Velocity: {status['velocity']:.2f} %/sec")
        if status['estimated_remaining']:
            print(f"  ETA: {status['estimated_remaining']:.1f}s remaining")
        print()

    # Mark as completed
    tracker.complete()
    print("=" * 70)
    print("Pipeline Completed!")
    print("=" * 70)

    # Generate and display final report
    report = tracker.generate_report()

    print("\n📊 FINAL REPORT\n")
    print(f"Task ID: {report.task_id}")
    print(f"State: {report.current_state}")
    print(f"Total Time: {report.elapsed_time:.2f}s")
    print(f"Completion: {report.completion_pct:.1f}%")
    print(f"Avg Velocity: {report.velocity:.2f} %/sec")

    # Milestone summary
    print(f"\n📋 MILESTONE SUMMARY\n")
    for milestone in report.milestones:
        status_icon = "✓" if milestone.status.value == "completed" else "○"
        variance = ""
        if milestone.variance_percentage:
            variance = f" ({milestone.variance_percentage:+.1f}% variance)"
        print(f"{status_icon} {milestone.name}: {milestone.actual_duration:.2f}s{variance}")

    # Bottleneck alerts
    if report.bottlenecks:
        print(f"\n⚠️  BOTTLENECK ALERTS ({len(report.bottlenecks)})\n")
        for i, alert in enumerate(report.bottlenecks):
            severity_icon = {
                "low": "ℹ️",
                "medium": "⚠️",
                "high": "🔥",
                "critical": "🚨",
            }.get(alert.severity.value, "⚠️")
            print(f"{severity_icon} Alert {i+1} [{alert.severity.value.upper()}]")
            print(f"   {alert.description}")
            print(f"   Suggestion: {alert.suggestion}\n")
    else:
        print("\n✓ No bottlenecks detected")

    # Summary statistics
    if report.summary:
        print(f"\n📈 STATISTICS\n")
        for key, value in report.summary.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

    # Export to JSON
    output_file = Path("/tmp/progress_report.json")
    tracker.export_to_json(output_file)
    print(f"\n💾 Report exported to: {output_file}")

    return tracker


def demonstrate_pause_resume():
    """Demonstrate pause and resume functionality."""
    print("\n" + "=" * 70)
    print("Pause/Resume Example")
    print("=" * 70)

    tracker = ProgressTracker(task_id="pauseable-task", total_steps=5)
    tracker.start_tracking()

    # Work on some steps
    for i in range(3):
        time.sleep(0.1)
        tracker.update_progress(completion_pct=(i + 1) * 20)
        print(f"Completed step {i+1}")

    # Pause
    print("\n⏸️  Pausing execution...")
    tracker.pause()
    print(f"State: {tracker.current_state.value}")

    time.sleep(0.2)

    # Resume
    print("\n▶️  Resuming execution...")
    tracker.resume()
    print(f"State: {tracker.current_state.value}")

    # Complete remaining steps
    for i in range(3, 5):
        time.sleep(0.1)
        tracker.update_progress(completion_pct=(i + 1) * 20)
        print(f"Completed step {i+1}")

    tracker.complete()
    print(f"\n✓ Final state: {tracker.current_state.value}")


def demonstrate_bottleneck_detection():
    """Demonstrate bottleneck detection with a slow task."""
    print("\n" + "=" * 70)
    print("Bottleneck Detection Example")
    print("=" * 70)

    milestones = [
        Milestone(name="Quick Task 1", expected_duration=0.1),
        Milestone(name="Slow Task", expected_duration=0.1),  # Will take much longer
        Milestone(name="Quick Task 2", expected_duration=0.1),
    ]

    tracker = ProgressTracker(
        task_id="bottleneck-demo",
        enable_bottleneck_detection=True,
        snapshot_interval=0.05,
    )

    tracker.start_tracking(milestones)

    # Quick task
    time.sleep(0.1)
    tracker.update_progress(milestone_name="Quick Task 1")
    print("✓ Quick Task 1 completed normally")

    # Slow task (simulate bottleneck)
    print("\n⚠️  Executing slow task...")
    time.sleep(0.5)  # 5x longer than expected!
    tracker.update_progress(milestone_name="Slow Task")
    print("✓ Slow Task completed (took longer than expected)")

    # Quick task
    time.sleep(0.1)
    tracker.update_progress(milestone_name="Quick Task 2")
    print("✓ Quick Task 2 completed normally")

    # Check for bottlenecks
    bottlenecks = tracker.detect_bottlenecks()

    if bottlenecks:
        print(f"\n🔍 Detected {len(bottlenecks)} new bottleneck(s):")
        for alert in bottlenecks:
            print(f"\n  Severity: {alert.severity.value}")
            print(f"  Description: {alert.description}")
            print(f"  Suggestion: {alert.suggestion}")
    else:
        print("\nNo new bottlenecks detected in this cycle")

    # Show all bottlenecks
    all_bottlenecks = tracker.bottlenecks
    print(f"\n📊 Total bottlenecks detected: {len(all_bottlenecks)}")


if __name__ == "__main__":
    # Run all examples
    simulate_data_pipeline()
    demonstrate_pause_resume()
    demonstrate_bottleneck_detection()

    print("\n" + "=" * 70)
    print("All examples completed successfully! ✓")
    print("=" * 70)

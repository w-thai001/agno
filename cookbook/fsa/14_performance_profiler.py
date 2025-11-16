"""🔍 FSA Performance Profiler Example

This example demonstrates profiling FSA execution to identify bottlenecks
and optimize performance.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.performance_profiler import FSAPerformanceProfiler
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.task_deconstructor import MLATaskDeconstructor
import time


def main():
    """Demonstrate FSA Performance Profiling"""

    print("\n" + "=" * 60)
    print("FSA PERFORMANCE PROFILER")
    print("=" * 60)

    # Create profiler
    profiler = FSAPerformanceProfiler(
        name="Profiler",
        enable_detailed_profiling=True,
        bottleneck_threshold=0.15,  # 15% of total time
        debug_mode=True
    )

    print("\n✅ Performance Profiler Created")

    # Example 1: Profile Code Builder
    print("\n\n" + "=" * 60)
    print("EXAMPLE 1: PROFILING CODE BUILDER FSA")
    print("=" * 60)

    code_builder = MultiStepCodeBuilder(
        name="CodeBuilder",
        programming_language="python"
    )

    print("\n🔍 Profiling Code Builder FSA...")

    # Profile with 3 runs for statistical accuracy
    report = profiler.profile_fsa(
        fsa=code_builder,
        context={
            "task": "Create a simple calculator function",
            "requirements": ["add", "subtract", "multiply", "divide"]
        },
        num_runs=3
    )

    print(f"\n📊 PROFILING REPORT")
    print(f"FSA: {report.fsa_name}")
    print(f"Total Execution Time: {report.total_execution_time:.3f}s")

    # Show hotspots
    print(f"\n🔥 HOTSPOTS (Top Time Consumers):")
    for i, hotspot in enumerate(report.hotspots, 1):
        print(f"  {i}. {hotspot}")

    # Show state performance
    print(f"\n📈 STATE PERFORMANCE:")
    sorted_states = sorted(report.state_profiles, key=lambda p: p.total_time, reverse=True)
    for i, profile in enumerate(sorted_states[:5], 1):
        print(f"\n  {i}. {profile.state_name}")
        print(f"     Total Time: {profile.total_time:.3f}s")
        print(f"     Avg Time: {profile.avg_time:.3f}s")
        print(f"     Min/Max: {profile.min_time:.3f}s / {profile.max_time:.3f}s")
        print(f"     Std Dev: {profile.std_dev:.3f}s")
        print(f"     Entries: {profile.entry_count}")

    # Show bottlenecks
    if report.bottlenecks:
        print(f"\n⚠️  BOTTLENECKS DETECTED:")
        for i, bottleneck in enumerate(report.bottlenecks, 1):
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(bottleneck.severity, "⚪")

            print(f"\n  {i}. {severity_icon} [{bottleneck.severity.upper()}] {bottleneck.location}")
            print(f"     Type: {bottleneck.type}")
            print(f"     Impact: {bottleneck.impact:.1f}% of total time")
            print(f"     Issue: {bottleneck.description}")
            print(f"     Fix: {bottleneck.recommendation}")
    else:
        print(f"\n✅ No bottlenecks detected!")

    # Show recommendations
    if report.recommendations:
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

    # Example 2: Profile Task Deconstructor
    print("\n\n" + "=" * 60)
    print("EXAMPLE 2: PROFILING TASK DECONSTRUCTOR FSA")
    print("=" * 60)

    # Reset profiler for new profiling session
    profiler.state_times.clear()
    profiler.transition_times.clear()
    profiler.state_profiles.clear()
    profiler.transition_profiles.clear()
    profiler.bottlenecks.clear()
    profiler.reset()

    task_deconstructor = MLATaskDeconstructor(
        name="TaskDeconstructor",
        min_impact_threshold=3.0,
        min_leverage_threshold=1.5
    )

    print("\n🔍 Profiling Task Deconstructor FSA...")

    report2 = profiler.profile_fsa(
        fsa=task_deconstructor,
        context={
            "task": "Build a web application with authentication and database"
        },
        num_runs=2
    )

    print(f"\n📊 PROFILING REPORT")
    print(f"FSA: {report2.fsa_name}")
    print(f"Total Execution Time: {report2.total_execution_time:.3f}s")
    print(f"Hotspots: {', '.join(report2.hotspots[:3])}")

    # Example 3: Compare Performance Between Runs
    print("\n\n" + "=" * 60)
    print("EXAMPLE 3: COMPARING PERFORMANCE RUNS")
    print("=" * 60)

    comparison = profiler.compare_runs(report, report2)

    print(f"\n📊 PERFORMANCE COMPARISON")
    print(f"Time Change: {comparison['total_time_change']:+.3f}s")
    print(f"Time Change %: {comparison['total_time_change_pct']:+.1f}%")
    print(f"Bottleneck Change: {comparison['new_bottlenecks']:+d}")

    if comparison['improvement']:
        print(f"✅ Performance IMPROVED")
    else:
        print(f"⚠️  Performance DEGRADED")

    # Example 4: Generate Full Profiling Summary
    print("\n\n" + "=" * 60)
    print("EXAMPLE 4: PROFILING SUMMARY")
    print("=" * 60)

    summary = profiler.get_profiling_summary()
    print(f"\n{summary}")

    # Example 5: Performance Regression Detection
    print("\n\n" + "=" * 60)
    print("EXAMPLE 5: PERFORMANCE REGRESSION DETECTION")
    print("=" * 60)

    print("\n📉 Checking for performance regressions...")

    # Simulate a baseline and current run
    baseline_time = report.total_execution_time
    current_time = report2.total_execution_time

    regression_threshold = 0.10  # 10% regression threshold

    if current_time > baseline_time * (1 + regression_threshold):
        regression_pct = ((current_time - baseline_time) / baseline_time) * 100
        print(f"🔴 REGRESSION DETECTED!")
        print(f"   Baseline: {baseline_time:.3f}s")
        print(f"   Current: {current_time:.3f}s")
        print(f"   Regression: +{regression_pct:.1f}%")
        print(f"   Threshold: {regression_threshold * 100}%")
    elif current_time < baseline_time * (1 - regression_threshold):
        improvement_pct = ((baseline_time - current_time) / baseline_time) * 100
        print(f"✅ PERFORMANCE IMPROVED!")
        print(f"   Baseline: {baseline_time:.3f}s")
        print(f"   Current: {current_time:.3f}s")
        print(f"   Improvement: -{improvement_pct:.1f}%")
    else:
        print(f"➡️  Performance Stable")
        print(f"   Within {regression_threshold * 100}% threshold")

    # Example 6: Detailed Transition Analysis
    print("\n\n" + "=" * 60)
    print("EXAMPLE 6: TRANSITION ANALYSIS")
    print("=" * 60)

    if report.transition_profiles:
        print(f"\n🔄 TRANSITION PERFORMANCE:")
        sorted_transitions = sorted(
            report.transition_profiles,
            key=lambda p: p.total_time,
            reverse=True
        )

        for i, profile in enumerate(sorted_transitions[:5], 1):
            print(f"\n  {i}. {profile.from_state} → {profile.to_state}")
            print(f"     Total Time: {profile.total_time:.3f}s")
            print(f"     Avg Time: {profile.avg_time:.3f}s")
            print(f"     Executions: {profile.execution_count}")
            print(f"     Condition Check: {profile.condition_check_time:.3f}s")
            print(f"     Action Execution: {profile.action_execution_time:.3f}s")

            # Calculate breakdown
            if profile.total_time > 0:
                condition_pct = (profile.condition_check_time / profile.total_time) * 100
                action_pct = (profile.action_execution_time / profile.total_time) * 100
                print(f"     Breakdown: Condition {condition_pct:.1f}% | Action {action_pct:.1f}%")

    # Performance Tips
    print("\n\n" + "=" * 60)
    print("PERFORMANCE OPTIMIZATION TIPS")
    print("=" * 60)

    tips = [
        "1. Profile regularly to catch regressions early",
        "2. Focus on critical bottlenecks (>50% impact) first",
        "3. Run multiple iterations for statistical accuracy",
        "4. Monitor state time variability for inconsistent performance",
        "5. Optimize expensive actions in frequently-used transitions",
        "6. Use profiler in CI/CD to prevent performance regressions",
        "7. Compare profiles before/after optimizations to verify improvements"
    ]

    for tip in tips:
        print(f"  {tip}")

    print("\n" + "=" * 60)
    print("✅ Performance profiling complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

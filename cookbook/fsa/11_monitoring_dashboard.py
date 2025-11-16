"""📊 FSA Monitoring Dashboard Example

This example demonstrates real-time FSA execution monitoring and analytics.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.monitoring_dashboard import FSAMonitoringDashboard
from agno.fsa.code_builder import MultiStepCodeBuilder
from agno.fsa.base import FSA, FSAState
import time


def main():
    """Demonstrate FSA Monitoring Dashboard"""

    print("\n" + "=" * 60)
    print("FSA MONITORING DASHBOARD")
    print("=" * 60)

    # Create monitoring dashboard
    dashboard = FSAMonitoringDashboard(
        name="FSAMonitor",
        enable_real_time_alerts=True,
        alert_on_errors=True,
        alert_on_slow_execution=True,
        performance_threshold_ms=2000.0,
        debug_mode=True
    )

    # Create FSAs to monitor
    code_builder = MultiStepCodeBuilder(name="CodeBuilder")
    simple_fsa = FSA(name="SimpleFSA", initial_state=FSAState.INITIAL)
    simple_fsa.add_transition(FSAState.INITIAL, FSAState.RUNNING)
    simple_fsa.add_transition(FSAState.RUNNING, FSAState.SUCCESS)

    # Register FSAs for monitoring
    dashboard.register_fsa(code_builder)
    dashboard.register_fsa(simple_fsa)

    print(f"\n✅ Registered {len(dashboard.monitored_fsas)} FSAs for monitoring")

    # Simulate some executions
    print("\n🔄 Simulating FSA executions...")

    # Execute simple FSA multiple times
    for i in range(5):
        exec_id = dashboard.record_execution_start(simple_fsa, {"test": i})
        result = simple_fsa.run({"iteration": i})
        dashboard.record_execution_end(exec_id, result)
        simple_fsa.reset()
        time.sleep(0.1)

    # Execute code builder (slower)
    exec_id = dashboard.record_execution_start(code_builder, {"task": "test"})
    # Simulate slow execution
    time.sleep(0.5)
    result = code_builder.run({"task": "Simple function", "language": "python"})
    dashboard.record_execution_end(exec_id, result)

    # Simulate a failure
    exec_id = dashboard.record_execution_start(simple_fsa, {"test": "fail"})
    dashboard.record_execution_end(
        exec_id,
        simple_fsa.run({}),
        error="Simulated failure for testing"
    )

    print("✅ Executed FSAs")

    # Get metrics
    print("\n" + "=" * 60)
    print("DASHBOARD METRICS")
    print("=" * 60)

    metrics = dashboard.get_metrics()
    print(f"\nActive Executions: {metrics.active_executions}")
    print(f"Total Executions: {metrics.total_executions}")
    print(f"Successful: {metrics.successful_executions} ✅")
    print(f"Failed: {metrics.failed_executions} ❌")
    print(f"Success Rate: {(metrics.successful_executions / max(metrics.total_executions, 1)) * 100:.1f}%")
    print(f"Avg Execution Time: {metrics.average_execution_time:.3f}s")
    print(f"Active Alerts: {metrics.active_alerts} 🚨")

    # Show health scores
    print("\n💚 FSA HEALTH SCORES:")
    for fsa_name, score in metrics.fsa_health_scores.items():
        health_icon = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
        bar_length = 20
        filled = int(bar_length * score / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  {health_icon} {fsa_name:20} [{bar}] {score:.1f}/100")

    # Show performance metrics
    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS")
    print("=" * 60)

    perf = dashboard.get_performance_metrics()
    print(f"\nTotal Executions: {perf.total_executions}")
    print(f"Success Rate: {perf.success_rate:.1f}%")
    print(f"Error Rate: {perf.error_rate:.1f}%")
    print(f"\nExecution Time Statistics:")
    print(f"  Average: {perf.avg_execution_time:.3f}s")
    print(f"  Minimum: {perf.min_execution_time:.3f}s")
    print(f"  Maximum: {perf.max_execution_time:.3f}s")
    print(f"  P50 (Median): {perf.p50_execution_time:.3f}s")
    print(f"  P95: {perf.p95_execution_time:.3f}s")
    print(f"  P99: {perf.p99_execution_time:.3f}s")

    # Show alerts
    print("\n" + "=" * 60)
    print("ACTIVE ALERTS")
    print("=" * 60)

    alerts = dashboard.get_active_alerts()
    if alerts:
        for i, alert in enumerate(alerts, 1):
            severity_icon = {
                "info": "🔵",
                "warning": "🟡",
                "error": "🔴",
                "critical": "🔴🔴"
            }
            icon = severity_icon.get(alert.severity, "⚪")
            print(f"\n{i}. {icon} [{alert.severity.upper()}] {alert.fsa_name}")
            print(f"   {alert.message}")
            print(f"   Time: {alert.timestamp}")
            print(f"   Resolved: {'Yes' if alert.resolved else 'No'}")
    else:
        print("\n✅ No active alerts")

    # Show execution history
    print("\n" + "=" * 60)
    print("EXECUTION HISTORY (Last 5)")
    print("=" * 60)

    history = dashboard.get_execution_history(limit=5)
    for i, record in enumerate(reversed(history), 1):
        status_icon = {
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
            "timeout": "⏰"
        }
        icon = status_icon.get(record.status.value, "⚪")

        print(f"\n{i}. {icon} {record.fsa_name} ({record.execution_id})")
        print(f"   Status: {record.status.value}")
        print(f"   Duration: {record.duration:.3f}s" if record.duration else "   Duration: N/A")
        print(f"   States: {' → '.join(record.state_history[:3])}..." if len(record.state_history) > 3 else f"   States: {' → '.join(record.state_history)}")
        if record.error:
            print(f"   Error: {record.error}")

    # Show summary
    print("\n" + "=" * 60)
    print("DASHBOARD SUMMARY")
    print("=" * 60)
    print("\n" + dashboard.get_dashboard_summary())

    # Export metrics
    metrics_file = "/tmp/fsa_metrics.json"
    dashboard.export_metrics_json(metrics_file)
    print(f"\n📄 Metrics exported to: {metrics_file}")


if __name__ == "__main__":
    main()

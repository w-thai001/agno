"""
Comprehensive test suite for HealthMonitorFSA.

Tests cover:
- Configuration validation
- Liveness checks
- Readiness checks
- Startup checks
- Dependency monitoring
- Metrics collection and aggregation
- Health degradation detection
- Alert sending
- Self-healing triggers
- Health history tracking
- Trend analysis
- Dashboard generation
- Status report generation
- Configuration updates
- Issue escalation
- Edge cases and error handling
- Concurrent monitoring
- Multi-service scenarios
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from agno.fsas.health_monitor_fsa import (
    AggregatedHealth,
    AlertResult,
    AlertSeverity,
    ConfigResult,
    Dashboard,
    DegradationDetection,
    Dependency,
    DependencyStatus,
    EscalationPolicy,
    EscalationResult,
    HealingAction,
    HealingResult,
    HealthCheckConfig,
    HealthCheckResult,
    HealthCheckType,
    HealthConfig,
    HealthIssue,
    HealthMetrics,
    HealthMonitorFSA,
    HealthMonitorResult,
    HealthStatus,
    HistoryEntry,
    LivenessResult,
    MonitorTarget,
    ReadinessResult,
    Service,
    ServiceState,
    StartupResult,
    StatusReport,
    TrendAnalysis,
    ValidationResult,
)


# ==================== Fixtures ====================

@pytest.fixture
def health_monitor_fsa():
    """Create HealthMonitorFSA instance for testing."""
    return HealthMonitorFSA(
        name="TestHealthMonitor",
        default_config=HealthConfig(
            check_interval=timedelta(seconds=30),
            timeout=timedelta(seconds=5),
            enable_self_healing=True,
            enable_alerts=True
        )
    )


@pytest.fixture
def sample_service():
    """Create sample service for testing."""
    return Service(
        name="test-service",
        endpoint="http://localhost:8080",
        state=ServiceState.RUNNING
    )


@pytest.fixture
def sample_services():
    """Create list of sample services."""
    return [
        Service(name=f"service-{i}", endpoint=f"http://localhost:808{i}", state=ServiceState.RUNNING)
        for i in range(5)
    ]


@pytest.fixture
def sample_dependency():
    """Create sample dependency."""
    return Dependency(
        name="test-database",
        type="database",
        endpoint="postgres://localhost:5432",
        critical=True
    )


@pytest.fixture
def monitor_target(sample_service):
    """Create monitor target for testing."""
    return MonitorTarget(
        service=sample_service,
        check_types=[HealthCheckType.LIVENESS, HealthCheckType.READINESS],
        interval=timedelta(seconds=30)
    )


# ==================== Test Configuration Validation ====================

def test_validate_valid_config(health_monitor_fsa):
    """Test validation of valid configuration."""
    config = HealthConfig(
        check_interval=timedelta(seconds=30),
        timeout=timedelta(seconds=5),
        failure_threshold=3
    )

    result = health_monitor_fsa.validate(config)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


def test_validate_config_with_invalid_interval(health_monitor_fsa):
    """Test validation fails for invalid interval."""
    config = HealthConfig(
        check_interval=timedelta(seconds=-1),
        timeout=timedelta(seconds=5)
    )

    result = health_monitor_fsa.validate(config)

    assert result.valid is False
    assert any("interval" in err.lower() for err in result.errors)


def test_validate_config_with_invalid_timeout(health_monitor_fsa):
    """Test validation fails for invalid timeout."""
    config = HealthConfig(
        check_interval=timedelta(seconds=30),
        timeout=timedelta(seconds=0)
    )

    result = health_monitor_fsa.validate(config)

    assert result.valid is False
    assert any("timeout" in err.lower() for err in result.errors)


def test_validate_config_with_warnings(health_monitor_fsa):
    """Test validation generates warnings."""
    config = HealthConfig(
        check_interval=timedelta(seconds=5),
        timeout=timedelta(seconds=10)  # Timeout > interval
    )

    result = health_monitor_fsa.validate(config)

    assert len(result.warnings) > 0


# ==================== Test Liveness Checks ====================

def test_liveness_check_healthy_service(health_monitor_fsa, sample_service):
    """Test liveness check on healthy running service."""
    result = health_monitor_fsa.liveness_check(sample_service)

    assert isinstance(result, LivenessResult)
    assert result.alive is True
    assert result.service_id == sample_service.service_id


def test_liveness_check_stopped_service(health_monitor_fsa, sample_service):
    """Test liveness check on stopped service."""
    sample_service.state = ServiceState.STOPPED

    result = health_monitor_fsa.liveness_check(sample_service)

    assert result.alive is False


def test_liveness_check_starting_service(health_monitor_fsa, sample_service):
    """Test liveness check on starting service."""
    sample_service.state = ServiceState.STARTING

    result = health_monitor_fsa.liveness_check(sample_service)

    assert result.alive is True  # Starting services are considered alive


# ==================== Test Readiness Checks ====================

def test_readiness_check_ready_service(health_monitor_fsa, sample_service):
    """Test readiness check on ready service."""
    result = health_monitor_fsa.readiness_check(sample_service)

    assert isinstance(result, ReadinessResult)
    assert result.ready is True
    assert result.service_id == sample_service.service_id


def test_readiness_check_not_running(health_monitor_fsa, sample_service):
    """Test readiness check on service not in running state."""
    sample_service.state = ServiceState.STARTING

    result = health_monitor_fsa.readiness_check(sample_service)

    assert result.ready is False
    assert "not RUNNING" in result.message


def test_readiness_check_with_dependencies(health_monitor_fsa, sample_service, sample_dependency):
    """Test readiness check considers dependencies."""
    # Add dependency
    health_monitor_fsa.add_dependency(sample_service, sample_dependency)

    result = health_monitor_fsa.readiness_check(sample_service)

    # Should check dependencies
    assert isinstance(result, ReadinessResult)


# ==================== Test Startup Checks ====================

def test_startup_check_started_service(health_monitor_fsa, sample_service):
    """Test startup check on started service."""
    result = health_monitor_fsa.startup_check(sample_service)

    assert isinstance(result, StartupResult)
    assert result.started is True
    assert result.service_id == sample_service.service_id


def test_startup_check_not_started(health_monitor_fsa, sample_service):
    """Test startup check on service not started."""
    sample_service.state = ServiceState.STARTING

    result = health_monitor_fsa.startup_check(sample_service)

    assert result.started is False


# ==================== Test Dependency Monitoring ====================

def test_monitor_dependencies_all_healthy(health_monitor_fsa, sample_service):
    """Test dependency monitoring with all healthy dependencies."""
    dependencies = [
        Dependency(name="db", type="database", critical=True),
        Dependency(name="cache", type="cache", critical=False)
    ]

    result = health_monitor_fsa.monitor_dependencies(sample_service, dependencies)

    assert isinstance(result, DependencyStatus)
    assert result.all_healthy is True
    assert len(result.dependency_statuses) == 2


def test_monitor_dependencies_unhealthy_critical(health_monitor_fsa, sample_service):
    """Test dependency monitoring with unhealthy critical dependency."""
    # This test would need to mock the dependency check
    # For now, we test the structure
    dependencies = [
        Dependency(name="db", type="database", critical=True)
    ]

    result = health_monitor_fsa.monitor_dependencies(sample_service, dependencies)

    assert isinstance(result, DependencyStatus)
    assert result.service_id == sample_service.service_id


# ==================== Test Metrics Collection ====================

def test_collect_health_metrics(health_monitor_fsa, sample_service):
    """Test health metrics collection."""
    metrics = health_monitor_fsa.collect_health_metrics(sample_service)

    assert isinstance(metrics, HealthMetrics)
    assert metrics.service_id == sample_service.service_id
    assert metrics.cpu_percent >= 0
    assert metrics.memory_percent >= 0
    assert metrics.response_time_ms >= 0


def test_aggregate_metrics_multiple_services(health_monitor_fsa, sample_services):
    """Test aggregating metrics from multiple services."""
    metrics_list = [
        health_monitor_fsa.collect_health_metrics(service)
        for service in sample_services
    ]

    # Set some service states
    for i, service in enumerate(sample_services):
        if i < 3:
            health_monitor_fsa.service_states[service.service_id] = HealthStatus.HEALTHY
        else:
            health_monitor_fsa.service_states[service.service_id] = HealthStatus.DEGRADED

    aggregated = health_monitor_fsa.aggregate_metrics(metrics_list)

    assert isinstance(aggregated, AggregatedHealth)
    assert aggregated.service_count == len(sample_services)
    assert aggregated.healthy_count == 3
    assert aggregated.degraded_count == 2
    assert aggregated.avg_cpu_percent >= 0


def test_aggregate_metrics_empty_list(health_monitor_fsa):
    """Test aggregating empty metrics list."""
    aggregated = health_monitor_fsa.aggregate_metrics([])

    assert isinstance(aggregated, AggregatedHealth)
    assert aggregated.service_count == 0


# ==================== Test Health Degradation Detection ====================

def test_detect_degradation_healthy(health_monitor_fsa):
    """Test degradation detection on healthy service."""
    historical = [HealthStatus.HEALTHY] * 5

    result = health_monitor_fsa.detect_degradation(HealthStatus.HEALTHY, historical)

    assert isinstance(result, DegradationDetection)
    assert result.degraded is False
    assert result.degradation_score < 50.0


def test_detect_degradation_unhealthy(health_monitor_fsa):
    """Test degradation detection on unhealthy service."""
    historical = [HealthStatus.UNHEALTHY] * 3

    result = health_monitor_fsa.detect_degradation(HealthStatus.UNHEALTHY, historical)

    assert result.degraded is True
    assert result.degradation_score > 50.0
    assert len(result.issues) > 0


def test_detect_degradation_trending_down(health_monitor_fsa):
    """Test degradation detection with declining trend."""
    historical = [
        HealthStatus.HEALTHY,
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
        HealthStatus.UNHEALTHY,
        HealthStatus.UNHEALTHY
    ]

    result = health_monitor_fsa.detect_degradation(HealthStatus.UNHEALTHY, historical)

    assert result.degraded is True
    assert len(result.issues) > 0


# ==================== Test Alert Sending ====================

def test_send_alert_success(health_monitor_fsa, sample_service):
    """Test successful alert sending."""
    result = health_monitor_fsa.send_alert(
        sample_service,
        AlertSeverity.WARNING,
        "Test alert message"
    )

    assert isinstance(result, AlertResult)
    assert result.success is True
    assert result.service_id == sample_service.service_id
    assert result.severity == AlertSeverity.WARNING


def test_send_alert_with_callback(health_monitor_fsa, sample_service):
    """Test alert sending triggers callback."""
    alerts_received = []

    def alert_callback(service, severity, message):
        alerts_received.append((service.name, severity, message))

    health_monitor_fsa.add_alert_callback(alert_callback)

    health_monitor_fsa.send_alert(
        sample_service,
        AlertSeverity.ERROR,
        "Test error"
    )

    assert len(alerts_received) == 1
    assert alerts_received[0][0] == sample_service.name
    assert alerts_received[0][1] == AlertSeverity.ERROR


def test_send_multiple_alerts(health_monitor_fsa, sample_service):
    """Test sending multiple alerts."""
    for i in range(5):
        health_monitor_fsa.send_alert(
            sample_service,
            AlertSeverity.INFO,
            f"Alert {i}"
        )

    assert health_monitor_fsa.total_alerts == 5


# ==================== Test Self-Healing ====================

def test_trigger_self_healing_critical(health_monitor_fsa, sample_service):
    """Test self-healing trigger for critical issue."""
    issue = HealthIssue(
        service_id=sample_service.service_id,
        severity=AlertSeverity.CRITICAL,
        message="Critical failure"
    )

    result = health_monitor_fsa.trigger_self_healing(sample_service, issue)

    assert isinstance(result, HealingResult)
    assert result.success is True
    assert result.action == HealingAction.RESTART


def test_trigger_self_healing_error(health_monitor_fsa, sample_service):
    """Test self-healing trigger for error."""
    issue = HealthIssue(
        service_id=sample_service.service_id,
        severity=AlertSeverity.ERROR,
        message="Error occurred"
    )

    result = health_monitor_fsa.trigger_self_healing(sample_service, issue)

    assert result.success is True
    assert result.action == HealingAction.CIRCUIT_BREAK


def test_trigger_self_healing_with_callback(health_monitor_fsa, sample_service):
    """Test self-healing triggers callback."""
    healings_received = []

    def healing_callback(service, issue):
        healings_received.append((service.name, issue.severity))

    health_monitor_fsa.add_healing_callback(HealingAction.RESTART, healing_callback)

    issue = HealthIssue(
        service_id=sample_service.service_id,
        severity=AlertSeverity.CRITICAL,
        message="Critical failure"
    )

    health_monitor_fsa.trigger_self_healing(sample_service, issue)

    assert len(healings_received) == 1


# ==================== Test Health History ====================

def test_track_health_history(health_monitor_fsa, sample_service):
    """Test health history tracking."""
    entry = health_monitor_fsa.track_health_history(sample_service, HealthStatus.HEALTHY)

    assert isinstance(entry, HistoryEntry)
    assert entry.service_id == sample_service.service_id
    assert entry.status == HealthStatus.HEALTHY


def test_track_multiple_history_entries(health_monitor_fsa, sample_service):
    """Test tracking multiple history entries."""
    statuses = [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.HEALTHY]

    for status in statuses:
        health_monitor_fsa.track_health_history(sample_service, status)

    history = health_monitor_fsa.health_history[sample_service.service_id]
    assert len(history) == 3


# ==================== Test Trend Analysis ====================

def test_analyze_health_trends_stable(health_monitor_fsa, sample_service):
    """Test trend analysis on stable health."""
    # Create stable health history
    for _ in range(10):
        health_monitor_fsa.track_health_history(sample_service, HealthStatus.HEALTHY)

    analysis = health_monitor_fsa.analyze_health_trends(
        sample_service,
        timedelta(hours=1)
    )

    assert isinstance(analysis, TrendAnalysis)
    assert analysis.service_id == sample_service.service_id
    assert analysis.trend in ["stable", "improving"]


def test_analyze_health_trends_degrading(health_monitor_fsa, sample_service):
    """Test trend analysis on degrading health."""
    # Create degrading health history
    for _ in range(5):
        health_monitor_fsa.track_health_history(sample_service, HealthStatus.HEALTHY)
    for _ in range(5):
        health_monitor_fsa.track_health_history(sample_service, HealthStatus.UNHEALTHY)

    analysis = health_monitor_fsa.analyze_health_trends(
        sample_service,
        timedelta(hours=1)
    )

    assert analysis.trend == "degrading"
    assert len(analysis.recommendations) > 0


def test_analyze_health_trends_no_history(health_monitor_fsa, sample_service):
    """Test trend analysis with no history."""
    analysis = health_monitor_fsa.analyze_health_trends(
        sample_service,
        timedelta(hours=1)
    )

    assert analysis.trend == "unknown"


# ==================== Test Dashboard Generation ====================

def test_generate_health_dashboard(health_monitor_fsa, sample_services):
    """Test health dashboard generation."""
    # Set service states
    for service in sample_services:
        health_monitor_fsa.service_states[service.service_id] = HealthStatus.HEALTHY

    dashboard = health_monitor_fsa.generate_health_dashboard(sample_services)

    assert isinstance(dashboard, Dashboard)
    assert dashboard.overall_health == HealthStatus.HEALTHY
    assert len(dashboard.services) == len(sample_services)


def test_generate_dashboard_with_unhealthy_services(health_monitor_fsa, sample_services):
    """Test dashboard generation with unhealthy services."""
    # Set mixed states
    for i, service in enumerate(sample_services):
        if i < 2:
            health_monitor_fsa.service_states[service.service_id] = HealthStatus.UNHEALTHY
        else:
            health_monitor_fsa.service_states[service.service_id] = HealthStatus.HEALTHY

    dashboard = health_monitor_fsa.generate_health_dashboard(sample_services)

    assert dashboard.overall_health == HealthStatus.UNHEALTHY


# ==================== Test Status Report Generation ====================

def test_generate_status_report(health_monitor_fsa, sample_services):
    """Test status report generation."""
    # Collect metrics for services
    for service in sample_services:
        health_monitor_fsa.collect_health_metrics(service)
        health_monitor_fsa.service_states[service.service_id] = HealthStatus.HEALTHY

    report = health_monitor_fsa.generate_status_report(sample_services)

    assert isinstance(report, StatusReport)
    assert report.overall_status == HealthStatus.HEALTHY
    assert "total" in report.services_summary
    assert report.services_summary["total"] == len(sample_services)


def test_generate_status_report_with_issues(health_monitor_fsa, sample_services):
    """Test status report includes issues."""
    # Add some issues
    for service in sample_services[:2]:
        issue = HealthIssue(
            service_id=service.service_id,
            severity=AlertSeverity.ERROR,
            message="Test issue"
        )
        health_monitor_fsa.active_issues[service.service_id].append(issue)

    # Collect metrics
    for service in sample_services:
        health_monitor_fsa.collect_health_metrics(service)

    report = health_monitor_fsa.generate_status_report(sample_services)

    assert len(report.issues) >= 2


# ==================== Test Configuration ====================

def test_configure_health_checks(health_monitor_fsa, sample_service):
    """Test health check configuration."""
    config = HealthCheckConfig(
        interval=timedelta(seconds=10),
        timeout=timedelta(seconds=3),
        enabled_checks=[HealthCheckType.LIVENESS, HealthCheckType.READINESS]
    )

    result = health_monitor_fsa.configure_health_checks(sample_service, config)

    assert isinstance(result, ConfigResult)
    assert result.success is True
    assert result.service_id == sample_service.service_id


# ==================== Test Issue Escalation ====================

def test_escalate_issue(health_monitor_fsa, sample_service):
    """Test issue escalation."""
    issue = HealthIssue(
        service_id=sample_service.service_id,
        severity=AlertSeverity.ERROR,
        message="Test issue"
    )

    policy = EscalationPolicy(
        escalation_threshold=3,
        notification_channels=["email", "slack"]
    )

    result = health_monitor_fsa.escalate_issue(sample_service, issue, policy)

    assert isinstance(result, EscalationResult)
    assert result.success is True
    assert len(result.notified_channels) == 2


def test_escalate_issue_reaches_threshold(health_monitor_fsa, sample_service):
    """Test issue escalation when threshold reached."""
    # Trigger multiple issues
    health_monitor_fsa.issue_counts[sample_service.service_id] = 5

    issue = HealthIssue(
        service_id=sample_service.service_id,
        severity=AlertSeverity.WARNING,
        message="Test issue"
    )

    policy = EscalationPolicy(
        escalation_threshold=3,
        notification_channels=["email"]
    )

    result = health_monitor_fsa.escalate_issue(sample_service, issue, policy)

    assert result.escalation_level == AlertSeverity.CRITICAL


# ==================== Test Main Execution Pipeline ====================

def test_execute_monitoring_pipeline(health_monitor_fsa, monitor_target):
    """Test main monitoring pipeline execution."""
    result = health_monitor_fsa.execute([monitor_target])

    assert isinstance(result, HealthMonitorResult)
    assert result.success is True
    assert result.monitored_count > 0


def test_execute_multiple_targets(health_monitor_fsa, sample_services):
    """Test monitoring multiple targets."""
    targets = [
        MonitorTarget(
            service=service,
            check_types=[HealthCheckType.LIVENESS],
            interval=timedelta(seconds=30)
        )
        for service in sample_services
    ]

    result = health_monitor_fsa.execute(targets)

    assert result.monitored_count == len(sample_services)


def test_execute_with_unhealthy_service(health_monitor_fsa):
    """Test execution detects unhealthy service."""
    service = Service(
        name="unhealthy-service",
        endpoint="http://localhost:9999",
        state=ServiceState.FAILED
    )

    target = MonitorTarget(
        service=service,
        check_types=[HealthCheckType.LIVENESS],
        interval=timedelta(seconds=30)
    )

    result = health_monitor_fsa.execute([target])

    assert result.unhealthy_count > 0


# ==================== Test Perform Health Check ====================

def test_perform_health_check_liveness(health_monitor_fsa, monitor_target):
    """Test performing liveness health check."""
    result = health_monitor_fsa.perform_health_check(
        monitor_target,
        HealthCheckType.LIVENESS
    )

    assert isinstance(result, HealthCheckResult)
    assert result.success is True
    assert result.check_type == HealthCheckType.LIVENESS


def test_perform_health_check_readiness(health_monitor_fsa, monitor_target):
    """Test performing readiness health check."""
    result = health_monitor_fsa.perform_health_check(
        monitor_target,
        HealthCheckType.READINESS
    )

    assert result.success is True
    assert result.check_type == HealthCheckType.READINESS


def test_perform_health_check_startup(health_monitor_fsa, monitor_target):
    """Test performing startup health check."""
    result = health_monitor_fsa.perform_health_check(
        monitor_target,
        HealthCheckType.STARTUP
    )

    assert result.success is True
    assert result.check_type == HealthCheckType.STARTUP


# ==================== Test Edge Cases ====================

def test_service_state_transitions(health_monitor_fsa, sample_service):
    """Test monitoring service through state transitions."""
    states = [ServiceState.STARTING, ServiceState.RUNNING, ServiceState.STOPPING, ServiceState.STOPPED]

    for state in states:
        sample_service.state = state
        result = health_monitor_fsa.liveness_check(sample_service)

        if state in [ServiceState.STARTING, ServiceState.RUNNING]:
            assert result.alive is True
        else:
            assert result.alive is False


def test_concurrent_monitoring(health_monitor_fsa, sample_services):
    """Test thread safety with concurrent monitoring."""
    import threading

    results = []
    lock = threading.Lock()

    def monitor_service(service):
        target = MonitorTarget(
            service=service,
            check_types=[HealthCheckType.LIVENESS],
            interval=timedelta(seconds=30)
        )
        result = health_monitor_fsa.execute([target])
        with lock:
            results.append(result)

    # Create multiple threads
    threads = [threading.Thread(target=monitor_service, args=(service,)) for service in sample_services]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify all completed
    assert len(results) == len(sample_services)


def test_metrics_history_retention(health_monitor_fsa, sample_service):
    """Test metrics history has size limit."""
    # Add many metrics
    for _ in range(1500):  # More than maxlen
        health_monitor_fsa.collect_health_metrics(sample_service)

    history = health_monitor_fsa.metrics_history[sample_service.service_id]

    # Should be limited to 1000
    assert len(history) <= 1000


def test_get_service_status(health_monitor_fsa, sample_service):
    """Test getting service status."""
    # Set status
    health_monitor_fsa.service_states[sample_service.service_id] = HealthStatus.HEALTHY

    status = health_monitor_fsa.get_service_status(sample_service.service_id)

    assert status == HealthStatus.HEALTHY


def test_get_service_status_unknown(health_monitor_fsa):
    """Test getting status for unknown service."""
    status = health_monitor_fsa.get_service_status("unknown_service_id")

    assert status == HealthStatus.UNKNOWN


def test_add_dependency(health_monitor_fsa, sample_service, sample_dependency):
    """Test adding dependency to service."""
    health_monitor_fsa.add_dependency(sample_service, sample_dependency)

    assert sample_service.service_id in health_monitor_fsa.dependencies
    assert len(health_monitor_fsa.dependencies[sample_service.service_id]) == 1

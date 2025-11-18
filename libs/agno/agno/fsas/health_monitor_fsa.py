"""
Health Monitor FSA: Comprehensive health monitoring and observability for FSA systems.

This module provides comprehensive health monitoring with support for:
- Multiple health check types (liveness, readiness, startup)
- Service and dependency monitoring
- Metrics collection and aggregation
- Health degradation detection
- Alert management with severity levels
- Self-healing capabilities
- Health history tracking and trend analysis
- Dashboard generation and status reporting
- Thread-safe concurrent monitoring
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class HealthCheckType(Enum):
    """Health check types."""
    LIVENESS = "liveness"  # Is the service alive?
    READINESS = "readiness"  # Is the service ready for traffic?
    STARTUP = "startup"  # Has the service started successfully?


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealingAction(Enum):
    """Self-healing actions."""
    RESTART = "restart"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    FAILOVER = "failover"
    CIRCUIT_BREAK = "circuit_break"
    NONE = "none"


class ServiceState(Enum):
    """Service states."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


# ==================== Data Classes ====================

@dataclass
class Service:
    """Represents a monitored service."""
    service_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    endpoint: str = ""
    state: ServiceState = ServiceState.RUNNING
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dependency:
    """Represents an external dependency."""
    dependency_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    type: str = ""  # database, api, message_queue, cache, etc.
    endpoint: str = ""
    critical: bool = True  # Is this dependency critical?
    timeout: timedelta = timedelta(seconds=5)


@dataclass
class MonitorTarget:
    """Represents a monitoring target."""
    target_id: str = field(default_factory=lambda: str(uuid4()))
    service: Service = field(default_factory=Service)
    check_types: List[HealthCheckType] = field(default_factory=list)
    interval: timedelta = timedelta(seconds=30)


@dataclass
class HealthConfig:
    """Configuration for health monitoring."""
    check_interval: timedelta = timedelta(seconds=30)
    timeout: timedelta = timedelta(seconds=10)
    failure_threshold: int = 3
    success_threshold: int = 1
    enable_self_healing: bool = True
    enable_alerts: bool = True
    history_retention: timedelta = timedelta(hours=24)


@dataclass
class HealthMetrics:
    """Health metrics for a service."""
    service_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_latency_ms: float = 0.0
    error_rate: float = 0.0
    request_rate: float = 0.0
    response_time_ms: float = 0.0
    active_connections: int = 0


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    success: bool
    check_type: HealthCheckType
    service_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LivenessResult:
    """Result of liveness check."""
    alive: bool
    service_id: str
    message: str = ""


@dataclass
class ReadinessResult:
    """Result of readiness check."""
    ready: bool
    service_id: str
    message: str = ""
    dependencies_ready: bool = True


@dataclass
class StartupResult:
    """Result of startup check."""
    started: bool
    service_id: str
    startup_time_ms: float = 0.0
    message: str = ""


@dataclass
class DependencyStatus:
    """Status of dependencies check."""
    all_healthy: bool
    service_id: str
    dependency_statuses: Dict[str, HealthStatus] = field(default_factory=dict)
    failed_critical: List[str] = field(default_factory=list)


@dataclass
class AggregatedHealth:
    """Aggregated health metrics."""
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    service_count: int = 0
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    avg_cpu_percent: float = 0.0
    avg_memory_percent: float = 0.0
    avg_response_time_ms: float = 0.0
    total_errors: int = 0


@dataclass
class HealthIssue:
    """Represents a health issue."""
    issue_id: str = field(default_factory=lambda: str(uuid4()))
    service_id: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DegradationDetection:
    """Result of health degradation detection."""
    degraded: bool
    service_id: str
    degradation_score: float = 0.0  # 0-100
    issues: List[str] = field(default_factory=list)


@dataclass
class AlertResult:
    """Result of alert sending."""
    success: bool
    alert_id: str = field(default_factory=lambda: str(uuid4()))
    service_id: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    error: Optional[str] = None


@dataclass
class HealingResult:
    """Result of self-healing action."""
    success: bool
    service_id: str
    action: HealingAction = HealingAction.NONE
    message: str = ""
    error: Optional[str] = None


@dataclass
class HistoryEntry:
    """Health history entry."""
    entry_id: str = field(default_factory=lambda: str(uuid4()))
    service_id: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    metrics: Optional[HealthMetrics] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TrendAnalysis:
    """Health trend analysis."""
    service_id: str
    time_window: timedelta
    trend: str = "stable"  # improving, degrading, stable
    avg_status_score: float = 0.0  # 0-100
    status_changes: int = 0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Dashboard:
    """Health dashboard."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    overall_health: HealthStatus = HealthStatus.UNKNOWN
    services: List[Dict[str, Any]] = field(default_factory=list)
    active_alerts: int = 0
    total_checks: int = 0


@dataclass
class StatusReport:
    """System health status report."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    services_summary: Dict[str, Any] = field(default_factory=dict)
    issues: List[HealthIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConfigResult:
    """Result of configuration update."""
    success: bool
    service_id: str
    message: str = ""
    error: Optional[str] = None


@dataclass
class EscalationPolicy:
    """Issue escalation policy."""
    escalation_threshold: int = 3
    escalation_levels: List[AlertSeverity] = field(default_factory=list)
    notification_channels: List[str] = field(default_factory=list)


@dataclass
class EscalationResult:
    """Result of issue escalation."""
    success: bool
    service_id: str
    escalation_level: AlertSeverity = AlertSeverity.WARNING
    notified_channels: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class HealthMonitorResult:
    """Result of main monitoring pipeline."""
    success: bool
    monitored_count: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    alerts_sent: int = 0
    healings_triggered: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    interval: timedelta = timedelta(seconds=30)
    timeout: timedelta = timedelta(seconds=5)
    retries: int = 3
    enabled_checks: List[HealthCheckType] = field(default_factory=list)


# ==================== Main FSA Class ====================

class HealthMonitorFSA:
    """
    Health Monitor Finite State Automaton.

    Provides comprehensive health monitoring with multiple check types,
    dependency tracking, alerting, and self-healing capabilities.
    """

    def __init__(
        self,
        name: str = "HealthMonitorFSA",
        default_config: Optional[HealthConfig] = None,
    ):
        """
        Initialize Health Monitor FSA.

        Args:
            name: Name of the FSA instance
            default_config: Default health monitoring configuration
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.default_config = default_config or HealthConfig()

        # Service tracking
        self.services: Dict[str, Service] = {}
        self.service_states: Dict[str, HealthStatus] = {}
        self.service_configs: Dict[str, HealthCheckConfig] = {}

        # Dependency tracking
        self.dependencies: Dict[str, List[Dependency]] = defaultdict(list)

        # Health metrics
        self.current_metrics: Dict[str, HealthMetrics] = {}
        self.metrics_history: Dict[str, Deque[HealthMetrics]] = defaultdict(lambda: deque(maxlen=1000))

        # Health history
        self.health_history: Dict[str, Deque[HistoryEntry]] = defaultdict(lambda: deque(maxlen=1000))

        # Issue tracking
        self.active_issues: Dict[str, List[HealthIssue]] = defaultdict(list)
        self.issue_counts: Dict[str, int] = defaultdict(int)

        # Alert tracking
        self.alerts_sent: List[AlertResult] = []
        self.alert_callbacks: List[Callable] = []

        # Healing tracking
        self.healing_actions: Dict[str, List[HealingResult]] = defaultdict(list)
        self.healing_callbacks: Dict[HealingAction, List[Callable]] = defaultdict(list)

        # Check results
        self.check_results: Dict[str, List[HealthCheckResult]] = defaultdict(list)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)

        # Statistics
        self.total_checks: int = 0
        self.total_alerts: int = 0
        self.total_healings: int = 0

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, targets: List[MonitorTarget]) -> HealthMonitorResult:
        """
        Main monitoring pipeline.

        Args:
            targets: List of monitoring targets

        Returns:
            HealthMonitorResult with monitoring statistics
        """
        monitored = 0
        healthy = 0
        unhealthy = 0
        alerts_sent = 0
        healings_triggered = 0
        errors = []

        for target in targets:
            try:
                # Register service if not exists
                if target.service.service_id not in self.services:
                    self.services[target.service.service_id] = target.service

                # Perform health checks
                for check_type in target.check_types:
                    result = self.perform_health_check(target, check_type)

                    if result.success:
                        if result.status == HealthStatus.HEALTHY:
                            healthy += 1
                        elif result.status == HealthStatus.UNHEALTHY:
                            unhealthy += 1

                            # Send alert
                            if self.default_config.enable_alerts:
                                alert_result = self.send_alert(
                                    target.service,
                                    AlertSeverity.ERROR,
                                    f"Health check failed: {result.message}"
                                )
                                if alert_result.success:
                                    alerts_sent += 1

                            # Trigger self-healing
                            if self.default_config.enable_self_healing:
                                issue = HealthIssue(
                                    service_id=target.service.service_id,
                                    severity=AlertSeverity.ERROR,
                                    message=result.message
                                )
                                healing_result = self.trigger_self_healing(target.service, issue)
                                if healing_result.success:
                                    healings_triggered += 1

                    monitored += 1

            except Exception as e:
                errors.append(f"Error monitoring {target.service.name}: {str(e)}")
                logger.error(f"Error monitoring {target.service.name}: {e}")

        return HealthMonitorResult(
            success=len(errors) == 0,
            monitored_count=monitored,
            healthy_count=healthy,
            unhealthy_count=unhealthy,
            alerts_sent=alerts_sent,
            healings_triggered=healings_triggered,
            errors=errors
        )

    # ==================== Validation ====================

    def validate(self, health_config: HealthConfig) -> ValidationResult:
        """
        Validate health monitoring configuration.

        Args:
            health_config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check interval
        if health_config.check_interval <= timedelta(0):
            errors.append("Check interval must be positive")

        # Check timeout
        if health_config.timeout <= timedelta(0):
            errors.append("Timeout must be positive")

        if health_config.timeout >= health_config.check_interval:
            warnings.append("Timeout is greater than or equal to check interval")

        # Check thresholds
        if health_config.failure_threshold <= 0:
            errors.append("Failure threshold must be positive")

        if health_config.success_threshold <= 0:
            errors.append("Success threshold must be positive")

        # Check retention
        if health_config.history_retention <= timedelta(0):
            warnings.append("History retention should be positive")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Health Checks ====================

    def perform_health_check(
        self,
        target: MonitorTarget,
        check_type: HealthCheckType
    ) -> HealthCheckResult:
        """
        Execute health check.

        Args:
            target: Monitoring target
            check_type: Type of health check

        Returns:
            HealthCheckResult with check status
        """
        start_time = time.time()

        try:
            # Perform appropriate check
            if check_type == HealthCheckType.LIVENESS:
                liveness_result = self.liveness_check(target.service)
                status = HealthStatus.HEALTHY if liveness_result.alive else HealthStatus.UNHEALTHY
                message = liveness_result.message

            elif check_type == HealthCheckType.READINESS:
                readiness_result = self.readiness_check(target.service)
                status = HealthStatus.HEALTHY if readiness_result.ready else HealthStatus.DEGRADED
                message = readiness_result.message

            elif check_type == HealthCheckType.STARTUP:
                startup_result = self.startup_check(target.service)
                status = HealthStatus.HEALTHY if startup_result.started else HealthStatus.UNHEALTHY
                message = startup_result.message

            else:
                status = HealthStatus.UNKNOWN
                message = f"Unknown check type: {check_type}"

            response_time_ms = (time.time() - start_time) * 1000

            # Update service state
            with self.lock:
                self.service_states[target.service.service_id] = status
                self.total_checks += 1

                if status == HealthStatus.HEALTHY:
                    self.success_counts[target.service.service_id] += 1
                else:
                    self.failure_counts[target.service.service_id] += 1

            # Track history
            self.track_health_history(target.service, status)

            return HealthCheckResult(
                success=True,
                check_type=check_type,
                service_id=target.service.service_id,
                status=status,
                message=message,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            logger.error(f"Health check failed for {target.service.name}: {e}")
            return HealthCheckResult(
                success=False,
                check_type=check_type,
                service_id=target.service.service_id,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )

    def liveness_check(self, service: Service) -> LivenessResult:
        """
        Check if service is alive.

        Args:
            service: Service to check

        Returns:
            LivenessResult with liveness status
        """
        # Simple liveness check based on service state
        alive = service.state in [ServiceState.RUNNING, ServiceState.STARTING]

        return LivenessResult(
            alive=alive,
            service_id=service.service_id,
            message=f"Service is {service.state.value}"
        )

    def readiness_check(self, service: Service) -> ReadinessResult:
        """
        Check if service is ready for traffic.

        Args:
            service: Service to check

        Returns:
            ReadinessResult with readiness status
        """
        # Check if service is running
        if service.state != ServiceState.RUNNING:
            return ReadinessResult(
                ready=False,
                service_id=service.service_id,
                message=f"Service state is {service.state.value}, not RUNNING"
            )

        # Check dependencies
        if service.service_id in self.dependencies:
            dep_status = self.monitor_dependencies(
                service,
                self.dependencies[service.service_id]
            )

            if not dep_status.all_healthy:
                return ReadinessResult(
                    ready=False,
                    service_id=service.service_id,
                    message=f"Dependencies not healthy: {dep_status.failed_critical}",
                    dependencies_ready=False
                )

        return ReadinessResult(
            ready=True,
            service_id=service.service_id,
            message="Service is ready for traffic"
        )

    def startup_check(self, service: Service) -> StartupResult:
        """
        Check if service started successfully.

        Args:
            service: Service to check

        Returns:
            StartupResult with startup status
        """
        # Check if service has transitioned to running state
        started = service.state == ServiceState.RUNNING

        # Calculate startup time (mock)
        startup_time_ms = 0.0
        if service.service_id in self.health_history:
            history = self.health_history[service.service_id]
            if len(history) > 0:
                startup_time_ms = (datetime.utcnow() - history[0].timestamp).total_seconds() * 1000

        return StartupResult(
            started=started,
            service_id=service.service_id,
            startup_time_ms=startup_time_ms,
            message=f"Service started in {startup_time_ms:.2f}ms" if started else "Service not started"
        )

    # ==================== Dependency Monitoring ====================

    def monitor_dependencies(
        self,
        service: Service,
        dependencies: List[Dependency]
    ) -> DependencyStatus:
        """
        Check external dependencies.

        Args:
            service: Service to check dependencies for
            dependencies: List of dependencies

        Returns:
            DependencyStatus with dependency health
        """
        dependency_statuses = {}
        failed_critical = []

        for dep in dependencies:
            # Mock dependency health check
            # In production, this would actually check the dependency
            status = self._check_dependency_health(dep)
            dependency_statuses[dep.name] = status

            if status == HealthStatus.UNHEALTHY and dep.critical:
                failed_critical.append(dep.name)

        all_healthy = len(failed_critical) == 0

        return DependencyStatus(
            all_healthy=all_healthy,
            service_id=service.service_id,
            dependency_statuses=dependency_statuses,
            failed_critical=failed_critical
        )

    def _check_dependency_health(self, dependency: Dependency) -> HealthStatus:
        """Check health of a single dependency."""
        # Mock implementation - in production would ping the dependency
        # For now, assume healthy
        return HealthStatus.HEALTHY

    # ==================== Metrics Collection ====================

    def collect_health_metrics(self, service: Service) -> HealthMetrics:
        """
        Gather health indicators.

        Args:
            service: Service to collect metrics for

        Returns:
            HealthMetrics with current metrics
        """
        # Mock metrics collection
        # In production, this would collect real metrics from the service
        metrics = HealthMetrics(
            service_id=service.service_id,
            timestamp=datetime.utcnow(),
            cpu_percent=50.0,  # Mock value
            memory_percent=60.0,  # Mock value
            disk_percent=30.0,  # Mock value
            network_latency_ms=10.0,  # Mock value
            error_rate=0.01,  # 1% error rate
            request_rate=100.0,  # 100 req/s
            response_time_ms=50.0,  # 50ms avg response time
            active_connections=25
        )

        with self.lock:
            self.current_metrics[service.service_id] = metrics
            self.metrics_history[service.service_id].append(metrics)

        return metrics

    def aggregate_metrics(self, metrics_list: List[HealthMetrics]) -> AggregatedHealth:
        """
        Combine health data.

        Args:
            metrics_list: List of health metrics

        Returns:
            AggregatedHealth with aggregated data
        """
        if not metrics_list:
            return AggregatedHealth()

        total_cpu = sum(m.cpu_percent for m in metrics_list)
        total_memory = sum(m.memory_percent for m in metrics_list)
        total_response_time = sum(m.response_time_ms for m in metrics_list)
        count = len(metrics_list)

        # Calculate health counts
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0

        for metrics in metrics_list:
            status = self.service_states.get(metrics.service_id, HealthStatus.UNKNOWN)
            if status == HealthStatus.HEALTHY:
                healthy_count += 1
            elif status == HealthStatus.DEGRADED:
                degraded_count += 1
            elif status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return AggregatedHealth(
            overall_status=overall_status,
            service_count=count,
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            unhealthy_count=unhealthy_count,
            avg_cpu_percent=total_cpu / count,
            avg_memory_percent=total_memory / count,
            avg_response_time_ms=total_response_time / count,
            total_errors=sum(int(m.error_rate * m.request_rate) for m in metrics_list)
        )

    # ==================== Degradation Detection ====================

    def detect_degradation(
        self,
        current_health: HealthStatus,
        historical_data: List[HealthStatus]
    ) -> DegradationDetection:
        """
        Identify health decline.

        Args:
            current_health: Current health status
            historical_data: Historical health statuses

        Returns:
            DegradationDetection with degradation analysis
        """
        issues = []
        degradation_score = 0.0

        # Check current status
        if current_health == HealthStatus.UNHEALTHY:
            degradation_score += 50.0
            issues.append("Service is unhealthy")
        elif current_health == HealthStatus.DEGRADED:
            degradation_score += 25.0
            issues.append("Service is degraded")

        # Analyze trend
        if len(historical_data) >= 3:
            recent = historical_data[-3:]
            unhealthy_count = sum(1 for s in recent if s == HealthStatus.UNHEALTHY)
            degraded_count = sum(1 for s in recent if s == HealthStatus.DEGRADED)

            if unhealthy_count >= 2:
                degradation_score += 30.0
                issues.append("Multiple recent unhealthy checks")
            elif degraded_count >= 2:
                degradation_score += 15.0
                issues.append("Multiple recent degraded checks")

        degraded = degradation_score > 50.0

        return DegradationDetection(
            degraded=degraded,
            service_id="",
            degradation_score=degradation_score,
            issues=issues
        )

    # ==================== Alerting ====================

    def send_alert(
        self,
        service: Service,
        severity: AlertSeverity,
        message: str
    ) -> AlertResult:
        """
        Notify on health issues.

        Args:
            service: Service with issue
            severity: Alert severity
            message: Alert message

        Returns:
            AlertResult with alert status
        """
        try:
            alert_id = str(uuid4())

            # Execute alert callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(service, severity, message)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

            with self.lock:
                alert_result = AlertResult(
                    success=True,
                    alert_id=alert_id,
                    service_id=service.service_id,
                    severity=severity,
                    message=message
                )
                self.alerts_sent.append(alert_result)
                self.total_alerts += 1

            logger.warning(f"Alert [{severity.value}] for {service.name}: {message}")
            return alert_result

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return AlertResult(
                success=False,
                service_id=service.service_id,
                severity=severity,
                message=message,
                error=str(e)
            )

    def add_alert_callback(self, callback: Callable) -> None:
        """Add alert callback function."""
        self.alert_callbacks.append(callback)

    # ==================== Self-Healing ====================

    def trigger_self_healing(
        self,
        service: Service,
        issue: HealthIssue
    ) -> HealingResult:
        """
        Initiate automatic recovery.

        Args:
            service: Service to heal
            issue: Health issue

        Returns:
            HealingResult with healing status
        """
        try:
            # Determine healing action based on issue severity
            if issue.severity == AlertSeverity.CRITICAL:
                action = HealingAction.RESTART
            elif issue.severity == AlertSeverity.ERROR:
                action = HealingAction.CIRCUIT_BREAK
            else:
                action = HealingAction.NONE

            # Execute healing action
            success = self._execute_healing_action(service, action)

            result = HealingResult(
                success=success,
                service_id=service.service_id,
                action=action,
                message=f"Executed {action.value} for {service.name}"
            )

            with self.lock:
                self.healing_actions[service.service_id].append(result)
                self.total_healings += 1

            # Execute healing callbacks
            if action in self.healing_callbacks:
                for callback in self.healing_callbacks[action]:
                    try:
                        callback(service, issue)
                    except Exception as e:
                        logger.error(f"Healing callback error: {e}")

            logger.info(f"Self-healing triggered for {service.name}: {action.value}")
            return result

        except Exception as e:
            logger.error(f"Self-healing failed: {e}")
            return HealingResult(
                success=False,
                service_id=service.service_id,
                action=HealingAction.NONE,
                message="Healing failed",
                error=str(e)
            )

    def _execute_healing_action(self, service: Service, action: HealingAction) -> bool:
        """Execute specific healing action."""
        # Mock implementation - in production would actually execute the action
        logger.info(f"Executing {action.value} for service {service.name}")
        return True

    def add_healing_callback(self, action: HealingAction, callback: Callable) -> None:
        """Add healing callback for specific action."""
        self.healing_callbacks[action].append(callback)

    # ==================== Health History ====================

    def track_health_history(
        self,
        service: Service,
        health_status: HealthStatus
    ) -> HistoryEntry:
        """
        Record health data.

        Args:
            service: Service to track
            health_status: Current health status

        Returns:
            HistoryEntry with recorded data
        """
        metrics = self.current_metrics.get(service.service_id)

        entry = HistoryEntry(
            service_id=service.service_id,
            status=health_status,
            metrics=metrics,
            timestamp=datetime.utcnow()
        )

        with self.lock:
            self.health_history[service.service_id].append(entry)

        return entry

    # ==================== Trend Analysis ====================

    def analyze_health_trends(
        self,
        service: Service,
        time_window: timedelta
    ) -> TrendAnalysis:
        """
        Analyze health patterns.

        Args:
            service: Service to analyze
            time_window: Time window for analysis

        Returns:
            TrendAnalysis with trend data
        """
        with self.lock:
            history = list(self.health_history[service.service_id])

        if not history:
            return TrendAnalysis(
                service_id=service.service_id,
                time_window=time_window,
                trend="unknown"
            )

        # Filter to time window
        cutoff = datetime.utcnow() - time_window
        recent_history = [h for h in history if h.timestamp > cutoff]

        if not recent_history:
            return TrendAnalysis(
                service_id=service.service_id,
                time_window=time_window,
                trend="unknown"
            )

        # Calculate status scores (0=unhealthy, 50=degraded, 100=healthy)
        status_scores = []
        for entry in recent_history:
            if entry.status == HealthStatus.HEALTHY:
                status_scores.append(100.0)
            elif entry.status == HealthStatus.DEGRADED:
                status_scores.append(50.0)
            else:
                status_scores.append(0.0)

        avg_score = sum(status_scores) / len(status_scores)

        # Determine trend
        if len(status_scores) >= 2:
            first_half_avg = sum(status_scores[:len(status_scores)//2]) / (len(status_scores)//2)
            second_half_avg = sum(status_scores[len(status_scores)//2:]) / (len(status_scores) - len(status_scores)//2)

            if second_half_avg > first_half_avg + 10:
                trend = "improving"
            elif second_half_avg < first_half_avg - 10:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Count status changes
        status_changes = 0
        for i in range(1, len(recent_history)):
            if recent_history[i].status != recent_history[i-1].status:
                status_changes += 1

        # Generate recommendations
        recommendations = []
        if trend == "degrading":
            recommendations.append("Service health is declining - investigate recent changes")
        if status_changes > len(recent_history) / 2:
            recommendations.append("High status instability - check for intermittent issues")
        if avg_score < 50:
            recommendations.append("Average health is low - consider scaling or optimization")

        return TrendAnalysis(
            service_id=service.service_id,
            time_window=time_window,
            trend=trend,
            avg_status_score=avg_score,
            status_changes=status_changes,
            recommendations=recommendations
        )

    # ==================== Dashboard & Reporting ====================

    def generate_health_dashboard(self, services: List[Service]) -> Dashboard:
        """
        Create health visualization.

        Args:
            services: List of services to include

        Returns:
            Dashboard with health data
        """
        services_data = []
        overall_healthy = 0
        overall_unhealthy = 0

        for service in services:
            status = self.service_states.get(service.service_id, HealthStatus.UNKNOWN)
            metrics = self.current_metrics.get(service.service_id)

            if status == HealthStatus.HEALTHY:
                overall_healthy += 1
            elif status == HealthStatus.UNHEALTHY:
                overall_unhealthy += 1

            # Convert metrics to dict
            metrics_dict = None
            if metrics:
                metrics_dict = {
                    "service_id": metrics.service_id,
                    "timestamp": metrics.timestamp.isoformat(),
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "disk_percent": metrics.disk_percent,
                    "network_latency_ms": metrics.network_latency_ms,
                    "error_rate": metrics.error_rate,
                    "request_rate": metrics.request_rate,
                    "response_time_ms": metrics.response_time_ms,
                    "active_connections": metrics.active_connections
                }

            service_data = {
                "service_id": service.service_id,
                "name": service.name,
                "status": status.value,
                "state": service.state.value,
                "metrics": metrics_dict
            }
            services_data.append(service_data)

        # Determine overall health
        if overall_unhealthy > 0:
            overall_health = HealthStatus.UNHEALTHY
        elif overall_healthy == len(services):
            overall_health = HealthStatus.HEALTHY
        else:
            overall_health = HealthStatus.DEGRADED

        return Dashboard(
            generated_at=datetime.utcnow(),
            overall_health=overall_health,
            services=services_data,
            active_alerts=len([a for a in self.alerts_sent if a.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]]),
            total_checks=self.total_checks
        )

    def generate_status_report(self, services: List[Service]) -> StatusReport:
        """
        Summarize system health.

        Args:
            services: List of services to include

        Returns:
            StatusReport with health summary
        """
        # Collect all metrics
        all_metrics = [self.current_metrics[s.service_id] for s in services if s.service_id in self.current_metrics]

        # Aggregate health
        aggregated = self.aggregate_metrics(all_metrics)

        # Collect active issues
        issues = []
        for service_id, service_issues in self.active_issues.items():
            issues.extend(service_issues)

        # Generate recommendations
        recommendations = []
        if aggregated.unhealthy_count > 0:
            recommendations.append(f"{aggregated.unhealthy_count} service(s) are unhealthy - immediate attention required")
        if aggregated.avg_cpu_percent > 80:
            recommendations.append("High average CPU usage - consider scaling")
        if aggregated.avg_memory_percent > 80:
            recommendations.append("High average memory usage - check for memory leaks")

        return StatusReport(
            generated_at=datetime.utcnow(),
            overall_status=aggregated.overall_status,
            services_summary={
                "total": aggregated.service_count,
                "healthy": aggregated.healthy_count,
                "degraded": aggregated.degraded_count,
                "unhealthy": aggregated.unhealthy_count,
                "avg_cpu_percent": aggregated.avg_cpu_percent,
                "avg_memory_percent": aggregated.avg_memory_percent,
                "avg_response_time_ms": aggregated.avg_response_time_ms
            },
            issues=issues,
            recommendations=recommendations
        )

    # ==================== Configuration ====================

    def configure_health_checks(
        self,
        service: Service,
        check_config: HealthCheckConfig
    ) -> ConfigResult:
        """
        Set health check parameters.

        Args:
            service: Service to configure
            check_config: Health check configuration

        Returns:
            ConfigResult with configuration status
        """
        try:
            with self.lock:
                self.service_configs[service.service_id] = check_config

            logger.info(f"Configured health checks for {service.name}")
            return ConfigResult(
                success=True,
                service_id=service.service_id,
                message="Health checks configured successfully"
            )

        except Exception as e:
            logger.error(f"Failed to configure health checks: {e}")
            return ConfigResult(
                success=False,
                service_id=service.service_id,
                message="Configuration failed",
                error=str(e)
            )

    # ==================== Issue Escalation ====================

    def escalate_issue(
        self,
        service: Service,
        issue: HealthIssue,
        escalation_policy: EscalationPolicy
    ) -> EscalationResult:
        """
        Handle critical issues.

        Args:
            service: Service with issue
            issue: Health issue
            escalation_policy: Escalation policy

        Returns:
            EscalationResult with escalation status
        """
        try:
            issue_count = self.issue_counts[service.service_id]

            # Determine escalation level
            if issue_count >= escalation_policy.escalation_threshold:
                escalation_level = AlertSeverity.CRITICAL
            else:
                escalation_level = issue.severity

            # Send escalated alert
            notified_channels = []
            for channel in escalation_policy.notification_channels:
                # Mock notification
                logger.warning(f"Escalating to {channel}: {issue.message}")
                notified_channels.append(channel)

            with self.lock:
                self.issue_counts[service.service_id] += 1

            return EscalationResult(
                success=True,
                service_id=service.service_id,
                escalation_level=escalation_level,
                notified_channels=notified_channels
            )

        except Exception as e:
            logger.error(f"Failed to escalate issue: {e}")
            return EscalationResult(
                success=False,
                service_id=service.service_id,
                error=str(e)
            )

    # ==================== Utility Methods ====================

    def add_dependency(self, service: Service, dependency: Dependency) -> None:
        """Add dependency to service."""
        with self.lock:
            self.dependencies[service.service_id].append(dependency)

    def get_service_status(self, service_id: str) -> HealthStatus:
        """Get current status of service."""
        return self.service_states.get(service_id, HealthStatus.UNKNOWN)

"""
FSA Monitoring Dashboard

Real-time FSA execution monitoring and analytics:
- Live execution tracking
- Performance metrics visualization
- Error alerting and logging
- Execution history analysis
- Resource usage monitoring
- State transition analytics
- Bottleneck detection

Provides operational visibility for FSA systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timedelta
import json
from collections import defaultdict

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class MonitoringState(str, Enum):
    """States for Monitoring Dashboard"""
    INITIAL = "initial"
    INITIALIZING = "initializing"
    MONITORING = "monitoring"
    ANALYZING = "analyzing"
    ALERTING = "alerting"
    REPORTING = "reporting"
    SUCCESS = "success"
    FAILED = "failed"


class ExecutionStatus(str, Enum):
    """Execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionRecord(BaseModel):
    """Record of FSA execution"""
    execution_id: str
    fsa_name: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[float] = None
    status: ExecutionStatus
    initial_state: str
    final_state: Optional[str] = None
    state_history: List[str] = []
    error: Optional[str] = None
    context_size: int = 0
    transitions_executed: int = 0


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    p50_execution_time: float
    p95_execution_time: float
    p99_execution_time: float
    total_executions: int
    success_rate: float
    error_rate: float


class Alert(BaseModel):
    """Alert for monitoring issues"""
    alert_id: str
    severity: str  # "info", "warning", "error", "critical"
    fsa_name: str
    message: str
    timestamp: str
    resolved: bool = False


class DashboardMetrics(BaseModel):
    """Dashboard metrics"""
    active_executions: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: float
    active_alerts: int
    fsa_health_scores: Dict[str, float]


@dataclass
class FSAMonitoringDashboard(FSA):
    """
    FSA Monitoring Dashboard

    Real-time monitoring and analytics for FSA systems:
    - Track active and historical executions
    - Monitor performance metrics
    - Generate alerts for anomalies
    - Analyze execution patterns
    - Visualize state transitions
    - Resource usage tracking

    Example:
        ```python
        # Create monitoring dashboard
        dashboard = FSAMonitoringDashboard(
            name="FSAMonitor",
            enable_real_time_alerts=True,
            alert_on_errors=True,
            performance_threshold_ms=5000
        )

        # Register FSA for monitoring
        dashboard.register_fsa(my_fsa)

        # Start monitoring
        dashboard.start_monitoring()

        # Execute FSA (automatically monitored)
        result = my_fsa.run({"input": "data"})

        # Get metrics
        metrics = dashboard.get_metrics()
        print(f"Success rate: {metrics.success_rate}%")
        ```
    """

    # Monitored FSAs
    monitored_fsas: Dict[str, FSA] = field(default_factory=dict)

    # Execution records
    execution_records: List[ExecutionRecord] = field(default_factory=list)
    active_executions: Dict[str, ExecutionRecord] = field(default_factory=dict)

    # Alerts
    alerts: List[Alert] = field(default_factory=list)

    # Configuration
    enable_real_time_alerts: bool = True
    alert_on_errors: bool = True
    alert_on_slow_execution: bool = True
    performance_threshold_ms: float = 5000.0
    max_execution_history: int = 1000
    retention_hours: int = 24

    # Metrics
    metrics_cache: Optional[DashboardMetrics] = None

    def __post_init__(self):
        """Initialize monitoring dashboard"""
        self.initial_state = MonitoringState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {MonitoringState.SUCCESS, MonitoringState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSAMonitoringDashboard {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup monitoring workflow"""
        # INITIAL -> INITIALIZING
        self.add_transition(
            MonitoringState.INITIAL,
            MonitoringState.INITIALIZING,
            action=self._initialize_monitoring,
            description="Initialize monitoring"
        )

        # INITIALIZING -> MONITORING
        self.add_transition(
            MonitoringState.INITIALIZING,
            MonitoringState.MONITORING,
            condition=lambda ctx: ctx.get("initialization_complete", False),
            action=self._start_monitoring,
            description="Start monitoring"
        )

        # MONITORING -> ANALYZING
        self.add_transition(
            MonitoringState.MONITORING,
            MonitoringState.ANALYZING,
            condition=lambda ctx: ctx.get("analysis_requested", False),
            action=self._analyze_metrics,
            description="Analyze metrics"
        )

        # ANALYZING -> ALERTING
        self.add_transition(
            MonitoringState.ANALYZING,
            MonitoringState.ALERTING,
            condition=lambda ctx: len(ctx.get("issues", [])) > 0,
            action=self._generate_alerts,
            description="Generate alerts"
        )

        # ANALYZING -> REPORTING (no alerts)
        self.add_transition(
            MonitoringState.ANALYZING,
            MonitoringState.REPORTING,
            condition=lambda ctx: len(ctx.get("issues", [])) == 0,
            description="Skip to reporting"
        )

        # ALERTING -> REPORTING
        self.add_transition(
            MonitoringState.ALERTING,
            MonitoringState.REPORTING,
            condition=lambda ctx: ctx.get("alerts_generated", False),
            action=self._generate_report,
            description="Generate report"
        )

        # REPORTING -> SUCCESS
        self.add_transition(
            MonitoringState.REPORTING,
            MonitoringState.SUCCESS,
            condition=lambda ctx: ctx.get("report_generated", False),
            description="Monitoring complete"
        )

        # Error handling
        for state in MonitoringState:
            if state not in [MonitoringState.SUCCESS, MonitoringState.FAILED]:
                self.add_transition(
                    state,
                    MonitoringState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _initialize_monitoring(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize monitoring system"""
        if self.debug_mode:
            logger.debug("Initializing monitoring dashboard")

        # Clean old records
        self._cleanup_old_records()

        context["initialization_complete"] = True
        return context

    def _start_monitoring(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start monitoring FSAs"""
        if self.debug_mode:
            logger.debug(f"Monitoring {len(self.monitored_fsas)} FSAs")

        context["monitoring_active"] = True
        return context

    def _analyze_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze collected metrics"""
        if self.debug_mode:
            logger.debug("Analyzing metrics")

        issues = []

        # Check for high error rates
        if self.execution_records:
            total = len(self.execution_records)
            failed = len([r for r in self.execution_records if r.status == ExecutionStatus.FAILED])
            error_rate = (failed / total) * 100 if total > 0 else 0

            if error_rate > 10:  # More than 10% errors
                issues.append({
                    "type": "high_error_rate",
                    "severity": "warning",
                    "message": f"Error rate is {error_rate:.1f}% (threshold: 10%)"
                })

        # Check for slow executions
        slow_executions = [
            r for r in self.execution_records
            if r.duration and r.duration * 1000 > self.performance_threshold_ms
        ]

        if slow_executions:
            issues.append({
                "type": "slow_execution",
                "severity": "info",
                "message": f"{len(slow_executions)} slow executions detected"
            })

        context["issues"] = issues
        return context

    def _generate_alerts(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alerts for detected issues"""
        issues = context.get("issues", [])

        if self.debug_mode:
            logger.debug(f"Generating {len(issues)} alerts")

        for issue in issues:
            alert = Alert(
                alert_id=f"alert-{len(self.alerts) + 1}",
                severity=issue["severity"],
                fsa_name="multiple",
                message=issue["message"],
                timestamp=datetime.now().isoformat()
            )
            self.alerts.append(alert)

        context["alerts_generated"] = True
        return context

    def _generate_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monitoring report"""
        if self.debug_mode:
            logger.debug("Generating monitoring report")

        # Calculate metrics
        total_execs = len(self.execution_records)
        successful = len([r for r in self.execution_records if r.status == ExecutionStatus.COMPLETED])
        failed = len([r for r in self.execution_records if r.status == ExecutionStatus.FAILED])

        avg_time = 0.0
        if self.execution_records:
            times = [r.duration for r in self.execution_records if r.duration]
            avg_time = sum(times) / len(times) if times else 0.0

        self.metrics_cache = DashboardMetrics(
            active_executions=len(self.active_executions),
            total_executions=total_execs,
            successful_executions=successful,
            failed_executions=failed,
            average_execution_time=avg_time,
            active_alerts=len([a for a in self.alerts if not a.resolved]),
            fsa_health_scores=self._calculate_health_scores()
        )

        context["report_generated"] = True
        return context

    def _calculate_health_scores(self) -> Dict[str, float]:
        """Calculate health score for each FSA"""
        health_scores = {}

        for fsa_name, fsa in self.monitored_fsas.items():
            # Get executions for this FSA
            fsa_records = [r for r in self.execution_records if r.fsa_name == fsa_name]

            if not fsa_records:
                health_scores[fsa_name] = 100.0
                continue

            # Calculate success rate
            total = len(fsa_records)
            successful = len([r for r in fsa_records if r.status == ExecutionStatus.COMPLETED])
            success_rate = (successful / total) * 100 if total > 0 else 0

            # Calculate performance score (based on execution time)
            times = [r.duration for r in fsa_records if r.duration]
            avg_time = sum(times) / len(times) if times else 0
            perf_score = 100 - min(100, (avg_time / (self.performance_threshold_ms / 1000)) * 50)

            # Overall health: weighted average
            health_scores[fsa_name] = (success_rate * 0.7) + (perf_score * 0.3)

        return health_scores

    def _cleanup_old_records(self) -> None:
        """Remove old execution records"""
        if not self.execution_records:
            return

        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        self.execution_records = [
            r for r in self.execution_records
            if datetime.fromisoformat(r.start_time) > cutoff_time
        ]

        # Limit to max_execution_history
        if len(self.execution_records) > self.max_execution_history:
            self.execution_records = self.execution_records[-self.max_execution_history:]

    def register_fsa(self, fsa: FSA) -> str:
        """Register an FSA for monitoring"""
        fsa_id = fsa.fsa_id
        self.monitored_fsas[fsa_id] = fsa

        if self.debug_mode:
            logger.debug(f"Registered FSA for monitoring: {fsa.name}")

        return fsa_id

    def record_execution_start(self, fsa: FSA, context: Dict[str, Any]) -> str:
        """Record start of FSA execution"""
        exec_id = f"exec-{len(self.execution_records) + 1}"

        record = ExecutionRecord(
            execution_id=exec_id,
            fsa_name=fsa.name,
            start_time=datetime.now().isoformat(),
            status=ExecutionStatus.RUNNING,
            initial_state=str(fsa.current_state),
            context_size=len(str(context))
        )

        self.active_executions[exec_id] = record

        if self.debug_mode:
            logger.debug(f"Started monitoring execution: {exec_id}")

        return exec_id

    def record_execution_end(
        self,
        exec_id: str,
        result: FSAExecutionResult,
        error: Optional[str] = None
    ) -> None:
        """Record end of FSA execution"""
        if exec_id not in self.active_executions:
            logger.warning(f"Unknown execution ID: {exec_id}")
            return

        record = self.active_executions.pop(exec_id)
        record.end_time = datetime.now().isoformat()
        record.final_state = result.final_state
        record.state_history = result.state_history
        record.duration = result.execution_time
        record.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
        record.error = error or result.error
        record.transitions_executed = len(result.state_history) - 1

        self.execution_records.append(record)

        # Generate alert if needed
        if self.enable_real_time_alerts:
            if error and self.alert_on_errors:
                self._create_alert(
                    "error",
                    record.fsa_name,
                    f"Execution failed: {error}"
                )

            if record.duration and record.duration * 1000 > self.performance_threshold_ms:
                if self.alert_on_slow_execution:
                    self._create_alert(
                        "warning",
                        record.fsa_name,
                        f"Slow execution: {record.duration:.2f}s"
                    )

        if self.debug_mode:
            logger.debug(f"Recorded execution end: {exec_id}")

    def _create_alert(self, severity: str, fsa_name: str, message: str) -> None:
        """Create an alert"""
        alert = Alert(
            alert_id=f"alert-{len(self.alerts) + 1}",
            severity=severity,
            fsa_name=fsa_name,
            message=message,
            timestamp=datetime.now().isoformat()
        )
        self.alerts.append(alert)

        if self.debug_mode:
            logger.debug(f"Created alert: {alert.alert_id}")

    def get_metrics(self) -> DashboardMetrics:
        """Get current dashboard metrics"""
        if not self.metrics_cache:
            # Generate metrics
            self.run({"analysis_requested": True})

        return self.metrics_cache or DashboardMetrics(
            active_executions=0,
            total_executions=0,
            successful_executions=0,
            failed_executions=0,
            average_execution_time=0.0,
            active_alerts=0,
            fsa_health_scores={}
        )

    def get_performance_metrics(self, fsa_name: Optional[str] = None) -> PerformanceMetrics:
        """Get performance metrics for specific FSA or all FSAs"""
        records = self.execution_records

        if fsa_name:
            records = [r for r in records if r.fsa_name == fsa_name]

        if not records:
            return PerformanceMetrics(
                avg_execution_time=0.0,
                min_execution_time=0.0,
                max_execution_time=0.0,
                p50_execution_time=0.0,
                p95_execution_time=0.0,
                p99_execution_time=0.0,
                total_executions=0,
                success_rate=0.0,
                error_rate=0.0
            )

        times = sorted([r.duration for r in records if r.duration])
        successful = len([r for r in records if r.status == ExecutionStatus.COMPLETED])

        def percentile(data, p):
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])

        return PerformanceMetrics(
            avg_execution_time=sum(times) / len(times) if times else 0.0,
            min_execution_time=min(times) if times else 0.0,
            max_execution_time=max(times) if times else 0.0,
            p50_execution_time=percentile(times, 50),
            p95_execution_time=percentile(times, 95),
            p99_execution_time=percentile(times, 99),
            total_executions=len(records),
            success_rate=(successful / len(records)) * 100,
            error_rate=((len(records) - successful) / len(records)) * 100
        )

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        return [a for a in self.alerts if not a.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False

    def get_execution_history(
        self,
        fsa_name: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionRecord]:
        """Get execution history"""
        records = self.execution_records

        if fsa_name:
            records = [r for r in records if r.fsa_name == fsa_name]

        return records[-limit:]

    def get_dashboard_summary(self) -> str:
        """Generate dashboard summary text"""
        metrics = self.get_metrics()

        summary = "FSA Monitoring Dashboard\n"
        summary += "=" * 50 + "\n\n"

        summary += f"Active Executions: {metrics.active_executions}\n"
        summary += f"Total Executions: {metrics.total_executions}\n"
        summary += f"Successful: {metrics.successful_executions}\n"
        summary += f"Failed: {metrics.failed_executions}\n"
        summary += f"Success Rate: {(metrics.successful_executions / max(metrics.total_executions, 1)) * 100:.1f}%\n"
        summary += f"Avg Execution Time: {metrics.average_execution_time:.3f}s\n"
        summary += f"Active Alerts: {metrics.active_alerts}\n\n"

        summary += "FSA Health Scores:\n"
        for fsa_name, score in metrics.fsa_health_scores.items():
            health_icon = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
            summary += f"  {health_icon} {fsa_name}: {score:.1f}/100\n"

        return summary

    def export_metrics_json(self, filepath: str) -> None:
        """Export metrics to JSON file"""
        metrics = self.get_metrics()
        with open(filepath, 'w') as f:
            json.dump(metrics.dict(), f, indent=2)

        if self.debug_mode:
            logger.debug(f"Exported metrics to {filepath}")

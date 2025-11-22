#!/usr/bin/env python3
"""
FSA Meta-Pattern Analyzer Module

A production-ready module for analyzing Logical Quality (LQ) trends across FSA executions,
identifying patterns, calculating success rates, and generating optimization recommendations.

This module uses PowerShell subprocess commands for file operations and provides
comprehensive analysis capabilities for FSA (Finite State Automata) execution logs.

Author: Agno Team
Version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from uuid import uuid4

# Configure module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler if not exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class LQCategory(Enum):
    """Logical Quality categories for FSA execution assessment."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


class PatternType(Enum):
    """Types of patterns identifiable in FSA executions."""

    SUCCESS_STREAK = "success_streak"
    FAILURE_CLUSTER = "failure_cluster"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RECOVERY_PATTERN = "recovery_pattern"
    CYCLIC_BEHAVIOR = "cyclic_behavior"
    ANOMALY = "anomaly"
    STATE_OSCILLATION = "state_oscillation"


class RecommendationPriority(Enum):
    """Priority levels for optimization recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class ExecutionLog:
    """Represents a single FSA execution log entry."""

    execution_id: str
    timestamp: datetime
    fsa_name: str
    state_transitions: List[str]
    success: bool
    duration_ms: float
    lq_score: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution log to dictionary representation."""
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "fsa_name": self.fsa_name,
            "state_transitions": self.state_transitions,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "lq_score": self.lq_score,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionLog":
        """Create ExecutionLog from dictionary."""
        return cls(
            execution_id=data.get("execution_id", str(uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data.get("timestamp"), str)
            else data.get("timestamp", datetime.now()),
            fsa_name=data.get("fsa_name", "unknown"),
            state_transitions=data.get("state_transitions", []),
            success=data.get("success", False),
            duration_ms=float(data.get("duration_ms", 0)),
            lq_score=float(data.get("lq_score", 0)),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LQTrendAnalysis:
    """Results of LQ trend analysis across executions."""

    average_lq: float
    median_lq: float
    std_deviation: float
    trend_direction: str  # "improving", "stable", "degrading"
    trend_slope: float
    lq_distribution: Dict[str, int]
    time_series: List[Tuple[datetime, float]]
    anomalies: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "average_lq": self.average_lq,
            "median_lq": self.median_lq,
            "std_deviation": self.std_deviation,
            "trend_direction": self.trend_direction,
            "trend_slope": self.trend_slope,
            "lq_distribution": self.lq_distribution,
            "time_series": [
                {"timestamp": ts.isoformat(), "lq_score": score}
                for ts, score in self.time_series
            ],
            "anomalies": self.anomalies,
        }


@dataclass
class SuccessRateMetrics:
    """Metrics for success/failure rate analysis."""

    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    failure_rate: float
    mean_time_between_failures: float
    failure_patterns: List[Dict[str, Any]]
    success_by_fsa: Dict[str, float]
    failure_by_error_type: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "mean_time_between_failures": self.mean_time_between_failures,
            "failure_patterns": self.failure_patterns,
            "success_by_fsa": self.success_by_fsa,
            "failure_by_error_type": self.failure_by_error_type,
        }


@dataclass
class IdentifiedPattern:
    """Represents an identified pattern in FSA executions."""

    pattern_id: str
    pattern_type: PatternType
    confidence: float
    occurrences: int
    affected_fsas: List[str]
    description: str
    evidence: List[Dict[str, Any]]
    first_occurrence: datetime
    last_occurrence: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "affected_fsas": self.affected_fsas,
            "description": self.description,
            "evidence": self.evidence,
            "first_occurrence": self.first_occurrence.isoformat(),
            "last_occurrence": self.last_occurrence.isoformat(),
        }


@dataclass
class Recommendation:
    """An optimization recommendation based on meta-pattern analysis."""

    recommendation_id: str
    priority: RecommendationPriority
    title: str
    description: str
    rationale: str
    affected_components: List[str]
    estimated_impact: str
    implementation_steps: List[str]
    related_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "recommendation_id": self.recommendation_id,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "affected_components": self.affected_components,
            "estimated_impact": self.estimated_impact,
            "implementation_steps": self.implementation_steps,
            "related_patterns": self.related_patterns,
        }


@dataclass
class MetaLQAssessment:
    """Self-assessment of the analyzer's own Logical Quality."""

    assessment_id: str
    timestamp: datetime
    overall_lq: float
    category: LQCategory
    component_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    self_improvement_recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "assessment_id": self.assessment_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_lq": self.overall_lq,
            "category": self.category.value,
            "component_scores": self.component_scores,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "self_improvement_recommendations": self.self_improvement_recommendations,
        }


@dataclass
class AnalysisResult:
    """Complete analysis result from the Meta-Pattern Analyzer."""

    analysis_id: str
    timestamp: datetime
    lq_trends: Optional[LQTrendAnalysis]
    success_rates: Optional[SuccessRateMetrics]
    identified_patterns: List[IdentifiedPattern]
    recommendations: List[Recommendation]
    meta_lq: Optional[MetaLQAssessment]
    execution_count: int
    analysis_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete analysis result to dictionary."""
        return {
            "analysis_id": self.analysis_id,
            "timestamp": self.timestamp.isoformat(),
            "lq_trends": self.lq_trends.to_dict() if self.lq_trends else None,
            "success_rates": self.success_rates.to_dict()
            if self.success_rates
            else None,
            "identified_patterns": [p.to_dict() for p in self.identified_patterns],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "meta_lq": self.meta_lq.to_dict() if self.meta_lq else None,
            "execution_count": self.execution_count,
            "analysis_duration_ms": self.analysis_duration_ms,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize analysis result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class PowerShellExecutor:
    """
    Handles PowerShell subprocess execution for file operations.

    All file operations in this module use PowerShell subprocess commands
    to ensure consistent behavior and security.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize PowerShell executor.

        Args:
            timeout: Maximum execution time in seconds for PowerShell commands.
        """
        self.timeout = timeout
        self._validate_powershell_availability()

    def _validate_powershell_availability(self) -> None:
        """Validate that PowerShell is available on the system."""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "$PSVersionTable.PSVersion.Major"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning(
                    "PowerShell may not be fully available: %s", result.stderr
                )
        except FileNotFoundError:
            logger.warning(
                "PowerShell not found. Falling back to shell commands where possible."
            )
        except subprocess.TimeoutExpired:
            logger.warning("PowerShell availability check timed out.")

    def execute(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute a PowerShell command.

        Args:
            command: The PowerShell command to execute.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            logger.debug("Executing PowerShell command: %s", command)
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        except subprocess.TimeoutExpired:
            logger.error("PowerShell command timed out: %s", command)
            return False, "", "Command timed out"
        except FileNotFoundError:
            # Fallback to bash for Linux systems
            logger.debug("PowerShell not available, attempting bash fallback")
            return self._bash_fallback(command)
        except Exception as e:
            logger.error("PowerShell execution error: %s", str(e))
            return False, "", str(e)

    def _bash_fallback(self, ps_command: str) -> Tuple[bool, str, str]:
        """
        Fallback to bash for systems without PowerShell.

        Args:
            ps_command: Original PowerShell command to translate.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Translate common PowerShell commands to bash equivalents
        bash_command = self._translate_to_bash(ps_command)
        try:
            result = subprocess.run(
                ["bash", "-c", bash_command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        except Exception as e:
            return False, "", str(e)

    def _translate_to_bash(self, ps_command: str) -> str:
        """
        Translate PowerShell commands to bash equivalents.

        Args:
            ps_command: PowerShell command string.

        Returns:
            Equivalent bash command string.
        """
        translations = {
            "Get-ChildItem": "ls -la",
            "Get-Content": "cat",
            "Set-Content": "tee",
            "Test-Path": "test -e",
            "Remove-Item": "rm -rf",
            "New-Item": "mkdir -p",
            "Get-Date": "date",
            "Write-Output": "echo",
        }

        result = ps_command
        for ps_cmd, bash_cmd in translations.items():
            result = result.replace(ps_cmd, bash_cmd)

        return result

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        List files in a directory using PowerShell.

        Args:
            directory: Directory path to list.
            pattern: File pattern to match.

        Returns:
            List of file paths.
        """
        command = f"Get-ChildItem -Path '{directory}' -Filter '{pattern}' -Recurse | Select-Object -ExpandProperty FullName"
        success, stdout, stderr = self.execute(command)

        if success and stdout:
            return [f.strip() for f in stdout.split("\n") if f.strip()]

        logger.warning("Failed to list files: %s", stderr)
        return []

    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read file contents using PowerShell.

        Args:
            file_path: Path to the file to read.

        Returns:
            File contents or None if failed.
        """
        command = f"Get-Content -Path '{file_path}' -Raw"
        success, stdout, stderr = self.execute(command)

        if success:
            return stdout

        logger.warning("Failed to read file %s: %s", file_path, stderr)
        return None

    def write_file(self, file_path: str, content: str) -> bool:
        """
        Write content to file using PowerShell.

        Args:
            file_path: Path to the file to write.
            content: Content to write.

        Returns:
            True if successful, False otherwise.
        """
        # Escape special characters for PowerShell
        escaped_content = content.replace("'", "''").replace("`", "``")
        command = f"Set-Content -Path '{file_path}' -Value '{escaped_content}'"
        success, _, stderr = self.execute(command)

        if not success:
            logger.error("Failed to write file %s: %s", file_path, stderr)

        return success

    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists using PowerShell.

        Args:
            file_path: Path to check.

        Returns:
            True if file exists, False otherwise.
        """
        command = f"Test-Path -Path '{file_path}'"
        success, stdout, _ = self.execute(command)
        return success and stdout.lower() == "true"


class FSAIntegrationLayer:
    """
    Integration layer for cross-FSA communication and coordination.

    Provides mechanisms for FSA modules to communicate, share state,
    and coordinate their execution patterns.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize FSA Integration Layer.

        Args:
            config: Optional configuration dictionary.
        """
        self.config = config or {}
        self._registered_fsas: Dict[str, Dict[str, Any]] = {}
        self._message_queue: List[Dict[str, Any]] = []
        self._shared_state: Dict[str, Any] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        logger.info("FSAIntegrationLayer initialized")

    def register_fsa(
        self, fsa_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register an FSA with the integration layer.

        Args:
            fsa_name: Name of the FSA to register.
            metadata: Optional metadata about the FSA.

        Returns:
            Registration ID.
        """
        registration_id = str(uuid4())
        self._registered_fsas[fsa_name] = {
            "registration_id": registration_id,
            "registered_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "status": "active",
        }
        logger.info("Registered FSA: %s with ID: %s", fsa_name, registration_id)
        return registration_id

    def unregister_fsa(self, fsa_name: str) -> bool:
        """
        Unregister an FSA from the integration layer.

        Args:
            fsa_name: Name of the FSA to unregister.

        Returns:
            True if successful, False if FSA not found.
        """
        if fsa_name in self._registered_fsas:
            del self._registered_fsas[fsa_name]
            logger.info("Unregistered FSA: %s", fsa_name)
            return True
        return False

    def get_registered_fsas(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered FSAs and their metadata."""
        return self._registered_fsas.copy()

    def send_message(
        self,
        sender: str,
        recipient: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> str:
        """
        Send a message between FSAs.

        Args:
            sender: Name of the sending FSA.
            recipient: Name of the recipient FSA.
            message_type: Type of message being sent.
            payload: Message payload.

        Returns:
            Message ID.
        """
        message_id = str(uuid4())
        message = {
            "message_id": message_id,
            "sender": sender,
            "recipient": recipient,
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
        }
        self._message_queue.append(message)
        logger.debug("Message queued: %s -> %s", sender, recipient)
        return message_id

    def receive_messages(
        self, fsa_name: str, message_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Receive pending messages for an FSA.

        Args:
            fsa_name: Name of the FSA receiving messages.
            message_type: Optional filter by message type.

        Returns:
            List of pending messages.
        """
        messages = [
            msg
            for msg in self._message_queue
            if msg["recipient"] == fsa_name
            and msg["status"] == "pending"
            and (message_type is None or msg["message_type"] == message_type)
        ]

        # Mark messages as delivered
        for msg in messages:
            msg["status"] = "delivered"

        return messages

    def set_shared_state(self, key: str, value: Any, fsa_name: str) -> None:
        """
        Set a shared state value.

        Args:
            key: State key.
            value: State value.
            fsa_name: FSA setting the value.
        """
        self._shared_state[key] = {
            "value": value,
            "set_by": fsa_name,
            "timestamp": datetime.now().isoformat(),
        }

    def get_shared_state(self, key: str) -> Optional[Any]:
        """
        Get a shared state value.

        Args:
            key: State key to retrieve.

        Returns:
            State value or None if not found.
        """
        if key in self._shared_state:
            return self._shared_state[key]["value"]
        return None

    def register_event_handler(
        self, event_type: str, handler: Callable
    ) -> None:
        """
        Register an event handler for cross-FSA events.

        Args:
            event_type: Type of event to handle.
            handler: Callback function for the event.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def emit_event(
        self, event_type: str, source: str, data: Dict[str, Any]
    ) -> int:
        """
        Emit an event to all registered handlers.

        Args:
            event_type: Type of event being emitted.
            source: Source FSA emitting the event.
            data: Event data.

        Returns:
            Number of handlers that processed the event.
        """
        handlers = self._event_handlers.get(event_type, [])
        processed = 0

        for handler in handlers:
            try:
                handler(source, data)
                processed += 1
            except Exception as e:
                logger.error(
                    "Event handler error for %s: %s", event_type, str(e)
                )

        return processed

    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration layer status."""
        return {
            "registered_fsas": len(self._registered_fsas),
            "pending_messages": len(
                [m for m in self._message_queue if m["status"] == "pending"]
            ),
            "shared_state_keys": list(self._shared_state.keys()),
            "event_handlers": {
                k: len(v) for k, v in self._event_handlers.items()
            },
        }


class FSAMetaPatternAnalyzer:
    """
    Meta-Pattern Analyzer for FSA execution analysis.

    This analyzer collects execution logs, identifies patterns, calculates
    LQ trends and success rates, generates recommendations, and performs
    self-assessment for continuous improvement.
    """

    def __init__(
        self,
        log_directory: Optional[str] = None,
        integration_layer: Optional[FSAIntegrationLayer] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Meta-Pattern Analyzer.

        Args:
            log_directory: Directory containing FSA execution logs.
            integration_layer: Optional FSAIntegrationLayer for cross-FSA communication.
            config: Optional configuration dictionary.
        """
        self.analyzer_id = str(uuid4())
        self.log_directory = log_directory or "./fsa_logs"
        self.integration_layer = integration_layer or FSAIntegrationLayer()
        self.config = config or self._default_config()
        self.powershell = PowerShellExecutor(
            timeout=self.config.get("powershell_timeout", 30)
        )
        self._execution_logs: List[ExecutionLog] = []
        self._analysis_history: List[AnalysisResult] = []

        # Register with integration layer
        self.integration_layer.register_fsa(
            "MetaPatternAnalyzer",
            {"analyzer_id": self.analyzer_id, "type": "analyzer"},
        )

        logger.info(
            "FSAMetaPatternAnalyzer initialized with ID: %s", self.analyzer_id
        )

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "powershell_timeout": 30,
            "min_executions_for_trend": 5,
            "anomaly_threshold": 2.0,  # standard deviations
            "pattern_min_occurrences": 3,
            "lq_thresholds": {
                "excellent": 0.9,
                "good": 0.75,
                "acceptable": 0.6,
                "poor": 0.4,
            },
            "log_file_pattern": "*.json",
        }

    def collect_execution_logs(
        self,
        directory: Optional[str] = None,
        pattern: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ExecutionLog]:
        """
        Collect execution logs using PowerShell subprocess commands.

        Args:
            directory: Directory to collect logs from. Defaults to configured log_directory.
            pattern: File pattern to match. Defaults to configured log_file_pattern.
            limit: Maximum number of logs to collect.

        Returns:
            List of ExecutionLog objects.
        """
        logger.info("Collecting execution logs via PowerShell...")

        directory = directory or self.log_directory
        pattern = pattern or self.config.get("log_file_pattern", "*.json")

        # Use PowerShell to list log files
        ps_command = (
            f"Get-ChildItem -Path '{directory}' -Filter '{pattern}' -Recurse "
            f"| Sort-Object LastWriteTime -Descending "
            f"| Select-Object -ExpandProperty FullName"
        )

        if limit:
            ps_command += f" -First {limit}"

        success, stdout, stderr = self.powershell.execute(ps_command)

        if not success:
            logger.warning(
                "PowerShell log collection failed, attempting directory scan: %s",
                stderr,
            )
            return self._fallback_collect_logs(directory, pattern, limit)

        log_files = [f.strip() for f in stdout.split("\n") if f.strip()]
        logger.info("Found %d log files", len(log_files))

        collected_logs: List[ExecutionLog] = []

        for log_file in log_files:
            try:
                content = self.powershell.read_file(log_file)
                if content:
                    log_data = json.loads(content)
                    if isinstance(log_data, list):
                        for entry in log_data:
                            collected_logs.append(ExecutionLog.from_dict(entry))
                    else:
                        collected_logs.append(ExecutionLog.from_dict(log_data))
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse log file %s: %s", log_file, str(e))
            except Exception as e:
                logger.error("Error processing log file %s: %s", log_file, str(e))

        self._execution_logs = collected_logs
        logger.info("Collected %d execution logs", len(collected_logs))

        # Emit event for cross-FSA notification
        self.integration_layer.emit_event(
            "logs_collected",
            "MetaPatternAnalyzer",
            {"count": len(collected_logs), "timestamp": datetime.now().isoformat()},
        )

        return collected_logs

    def _fallback_collect_logs(
        self,
        directory: str,
        pattern: str,
        limit: Optional[int],
    ) -> List[ExecutionLog]:
        """
        Fallback method for collecting logs when PowerShell fails.

        Args:
            directory: Directory to collect logs from.
            pattern: File pattern to match.
            limit: Maximum number of logs.

        Returns:
            List of ExecutionLog objects.
        """
        collected_logs: List[ExecutionLog] = []

        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.warning("Log directory does not exist: %s", directory)
                return collected_logs

            # Convert glob pattern
            glob_pattern = pattern.replace("*", "**/*") if "**" not in pattern else pattern
            files = list(dir_path.glob(glob_pattern))

            if limit:
                files = files[:limit]

            for file_path in files:
                try:
                    with open(file_path, "r") as f:
                        log_data = json.load(f)
                        if isinstance(log_data, list):
                            for entry in log_data:
                                collected_logs.append(ExecutionLog.from_dict(entry))
                        else:
                            collected_logs.append(ExecutionLog.from_dict(log_data))
                except Exception as e:
                    logger.warning("Error reading %s: %s", file_path, str(e))

        except Exception as e:
            logger.error("Fallback log collection failed: %s", str(e))

        self._execution_logs = collected_logs
        return collected_logs

    def analyze_lq_trends(
        self, logs: Optional[List[ExecutionLog]] = None
    ) -> Optional[LQTrendAnalysis]:
        """
        Analyze LQ (Logical Quality) trends across FSA executions.

        Performs statistical analysis of LQ scores over time to identify
        trends, anomalies, and patterns in execution quality.

        Args:
            logs: Optional list of logs to analyze. Uses collected logs if not provided.

        Returns:
            LQTrendAnalysis object or None if insufficient data.
        """
        logger.info("Analyzing LQ trends...")

        logs = logs or self._execution_logs

        if len(logs) < self.config.get("min_executions_for_trend", 5):
            logger.warning(
                "Insufficient data for trend analysis. Need at least %d executions.",
                self.config.get("min_executions_for_trend", 5),
            )
            return None

        # Extract LQ scores and timestamps
        lq_scores = [log.lq_score for log in logs]
        time_series = [(log.timestamp, log.lq_score) for log in logs]
        time_series.sort(key=lambda x: x[0])

        # Calculate basic statistics
        avg_lq = mean(lq_scores)
        med_lq = median(lq_scores)
        std_dev = stdev(lq_scores) if len(lq_scores) > 1 else 0.0

        # Calculate trend using linear regression approximation
        trend_slope = self._calculate_trend_slope(time_series)

        if trend_slope > 0.01:
            trend_direction = "improving"
        elif trend_slope < -0.01:
            trend_direction = "degrading"
        else:
            trend_direction = "stable"

        # Calculate LQ distribution by category
        lq_distribution = self._calculate_lq_distribution(lq_scores)

        # Identify anomalies
        anomalies = self._identify_anomalies(logs, avg_lq, std_dev)

        trend_analysis = LQTrendAnalysis(
            average_lq=round(avg_lq, 4),
            median_lq=round(med_lq, 4),
            std_deviation=round(std_dev, 4),
            trend_direction=trend_direction,
            trend_slope=round(trend_slope, 6),
            lq_distribution=lq_distribution,
            time_series=time_series,
            anomalies=anomalies,
        )

        logger.info(
            "LQ Trend Analysis complete: avg=%.4f, trend=%s",
            avg_lq,
            trend_direction,
        )

        return trend_analysis

    def _calculate_trend_slope(
        self, time_series: List[Tuple[datetime, float]]
    ) -> float:
        """
        Calculate trend slope using simple linear regression.

        Args:
            time_series: List of (timestamp, value) tuples.

        Returns:
            Slope coefficient.
        """
        if len(time_series) < 2:
            return 0.0

        n = len(time_series)

        # Normalize timestamps to sequential indices
        x_values = list(range(n))
        y_values = [ts[1] for ts in time_series]

        x_mean = mean(x_values)
        y_mean = mean(y_values)

        numerator = sum(
            (x - x_mean) * (y - y_mean)
            for x, y in zip(x_values, y_values)
        )
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _calculate_lq_distribution(
        self, lq_scores: List[float]
    ) -> Dict[str, int]:
        """
        Calculate distribution of LQ scores by category.

        Args:
            lq_scores: List of LQ score values.

        Returns:
            Dictionary mapping category names to counts.
        """
        thresholds = self.config.get("lq_thresholds", {})
        distribution = {cat.value: 0 for cat in LQCategory}

        for score in lq_scores:
            if score >= thresholds.get("excellent", 0.9):
                distribution[LQCategory.EXCELLENT.value] += 1
            elif score >= thresholds.get("good", 0.75):
                distribution[LQCategory.GOOD.value] += 1
            elif score >= thresholds.get("acceptable", 0.6):
                distribution[LQCategory.ACCEPTABLE.value] += 1
            elif score >= thresholds.get("poor", 0.4):
                distribution[LQCategory.POOR.value] += 1
            else:
                distribution[LQCategory.CRITICAL.value] += 1

        return distribution

    def _identify_anomalies(
        self,
        logs: List[ExecutionLog],
        avg_lq: float,
        std_dev: float,
    ) -> List[Dict[str, Any]]:
        """
        Identify anomalous executions based on statistical deviation.

        Args:
            logs: List of execution logs.
            avg_lq: Average LQ score.
            std_dev: Standard deviation of LQ scores.

        Returns:
            List of anomaly dictionaries.
        """
        anomalies = []
        threshold = self.config.get("anomaly_threshold", 2.0)

        for log in logs:
            if std_dev > 0:
                z_score = abs(log.lq_score - avg_lq) / std_dev
                if z_score > threshold:
                    anomalies.append({
                        "execution_id": log.execution_id,
                        "timestamp": log.timestamp.isoformat(),
                        "lq_score": log.lq_score,
                        "z_score": round(z_score, 2),
                        "type": "low_lq" if log.lq_score < avg_lq else "high_lq",
                    })

        return anomalies

    def calculate_success_rates(
        self, logs: Optional[List[ExecutionLog]] = None
    ) -> SuccessRateMetrics:
        """
        Calculate success rates and failure metrics for FSA executions.

        Analyzes execution success/failure patterns, calculates rates,
        and identifies common failure modes.

        Args:
            logs: Optional list of logs to analyze. Uses collected logs if not provided.

        Returns:
            SuccessRateMetrics object.
        """
        logger.info("Calculating success rates...")

        logs = logs or self._execution_logs

        if not logs:
            logger.warning("No logs available for success rate calculation")
            return SuccessRateMetrics(
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                success_rate=0.0,
                failure_rate=0.0,
                mean_time_between_failures=0.0,
                failure_patterns=[],
                success_by_fsa={},
                failure_by_error_type={},
            )

        total = len(logs)
        successful = sum(1 for log in logs if log.success)
        failed = total - successful

        success_rate = successful / total if total > 0 else 0.0
        failure_rate = failed / total if total > 0 else 0.0

        # Calculate MTBF (Mean Time Between Failures)
        mtbf = self._calculate_mtbf(logs)

        # Calculate success rate by FSA
        success_by_fsa = self._calculate_success_by_fsa(logs)

        # Categorize failures by error type
        failure_by_error_type = self._categorize_failures(logs)

        # Identify failure patterns
        failure_patterns = self._identify_failure_patterns(logs)

        metrics = SuccessRateMetrics(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            success_rate=round(success_rate, 4),
            failure_rate=round(failure_rate, 4),
            mean_time_between_failures=round(mtbf, 2),
            failure_patterns=failure_patterns,
            success_by_fsa=success_by_fsa,
            failure_by_error_type=failure_by_error_type,
        )

        logger.info(
            "Success rate calculation complete: %.2f%% success rate",
            success_rate * 100,
        )

        return metrics

    def _calculate_mtbf(self, logs: List[ExecutionLog]) -> float:
        """
        Calculate Mean Time Between Failures.

        Args:
            logs: List of execution logs.

        Returns:
            MTBF in milliseconds.
        """
        sorted_logs = sorted(logs, key=lambda x: x.timestamp)
        failure_times = [
            log.timestamp for log in sorted_logs if not log.success
        ]

        if len(failure_times) < 2:
            return 0.0

        intervals = []
        for i in range(1, len(failure_times)):
            delta = (failure_times[i] - failure_times[i - 1]).total_seconds() * 1000
            intervals.append(delta)

        return mean(intervals) if intervals else 0.0

    def _calculate_success_by_fsa(
        self, logs: List[ExecutionLog]
    ) -> Dict[str, float]:
        """
        Calculate success rate per FSA.

        Args:
            logs: List of execution logs.

        Returns:
            Dictionary mapping FSA names to success rates.
        """
        fsa_stats: Dict[str, Dict[str, int]] = {}

        for log in logs:
            if log.fsa_name not in fsa_stats:
                fsa_stats[log.fsa_name] = {"total": 0, "success": 0}

            fsa_stats[log.fsa_name]["total"] += 1
            if log.success:
                fsa_stats[log.fsa_name]["success"] += 1

        return {
            fsa: round(stats["success"] / stats["total"], 4)
            for fsa, stats in fsa_stats.items()
        }

    def _categorize_failures(
        self, logs: List[ExecutionLog]
    ) -> Dict[str, int]:
        """
        Categorize failures by error type.

        Args:
            logs: List of execution logs.

        Returns:
            Dictionary mapping error types to counts.
        """
        error_counts: Dict[str, int] = {}

        for log in logs:
            if not log.success and log.error_message:
                # Extract error type from message
                error_type = self._extract_error_type(log.error_message)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return error_counts

    def _extract_error_type(self, error_message: str) -> str:
        """
        Extract error type category from error message.

        Args:
            error_message: Error message string.

        Returns:
            Error type category.
        """
        patterns = {
            "timeout": r"timeout|timed?\s*out",
            "validation": r"validation|invalid|schema",
            "state_transition": r"state|transition|illegal",
            "resource": r"resource|memory|cpu|disk",
            "network": r"network|connection|socket",
            "permission": r"permission|access|denied|forbidden",
            "configuration": r"config|configuration|setting",
        }

        lower_message = error_message.lower()
        for error_type, pattern in patterns.items():
            if re.search(pattern, lower_message):
                return error_type

        return "unknown"

    def _identify_failure_patterns(
        self, logs: List[ExecutionLog]
    ) -> List[Dict[str, Any]]:
        """
        Identify patterns in failure occurrences.

        Args:
            logs: List of execution logs.

        Returns:
            List of identified failure patterns.
        """
        patterns = []
        sorted_logs = sorted(logs, key=lambda x: x.timestamp)

        # Check for consecutive failures
        consecutive_failures = []
        current_streak = []

        for log in sorted_logs:
            if not log.success:
                current_streak.append(log)
            else:
                if len(current_streak) >= 3:
                    consecutive_failures.append(current_streak.copy())
                current_streak = []

        if len(current_streak) >= 3:
            consecutive_failures.append(current_streak)

        for streak in consecutive_failures:
            patterns.append({
                "type": "consecutive_failures",
                "count": len(streak),
                "start_time": streak[0].timestamp.isoformat(),
                "end_time": streak[-1].timestamp.isoformat(),
                "affected_fsas": list(set(log.fsa_name for log in streak)),
            })

        return patterns

    def identify_patterns(
        self, logs: Optional[List[ExecutionLog]] = None
    ) -> List[IdentifiedPattern]:
        """
        Identify meta-patterns across FSA executions.

        Performs pattern recognition on execution data to identify
        recurring behaviors, anomalies, and optimization opportunities.

        Args:
            logs: Optional list of logs to analyze. Uses collected logs if not provided.

        Returns:
            List of IdentifiedPattern objects.
        """
        logger.info("Identifying patterns in execution data...")

        logs = logs or self._execution_logs
        patterns: List[IdentifiedPattern] = []

        if not logs:
            logger.warning("No logs available for pattern identification")
            return patterns

        sorted_logs = sorted(logs, key=lambda x: x.timestamp)

        # Identify success streaks
        success_patterns = self._identify_success_streaks(sorted_logs)
        patterns.extend(success_patterns)

        # Identify failure clusters
        failure_patterns = self._identify_failure_clusters(sorted_logs)
        patterns.extend(failure_patterns)

        # Identify performance degradation
        perf_patterns = self._identify_performance_degradation(sorted_logs)
        patterns.extend(perf_patterns)

        # Identify recovery patterns
        recovery_patterns = self._identify_recovery_patterns(sorted_logs)
        patterns.extend(recovery_patterns)

        # Identify state oscillation patterns
        oscillation_patterns = self._identify_state_oscillation(sorted_logs)
        patterns.extend(oscillation_patterns)

        logger.info("Identified %d patterns", len(patterns))

        return patterns

    def _identify_success_streaks(
        self, logs: List[ExecutionLog]
    ) -> List[IdentifiedPattern]:
        """Identify periods of consistent success."""
        patterns = []
        min_streak = self.config.get("pattern_min_occurrences", 3)

        current_streak: List[ExecutionLog] = []

        for log in logs:
            if log.success:
                current_streak.append(log)
            else:
                if len(current_streak) >= min_streak:
                    patterns.append(
                        IdentifiedPattern(
                            pattern_id=str(uuid4()),
                            pattern_type=PatternType.SUCCESS_STREAK,
                            confidence=0.85,
                            occurrences=len(current_streak),
                            affected_fsas=list(
                                set(l.fsa_name for l in current_streak)
                            ),
                            description=f"Success streak of {len(current_streak)} consecutive executions",
                            evidence=[
                                {"execution_id": l.execution_id}
                                for l in current_streak[:5]
                            ],
                            first_occurrence=current_streak[0].timestamp,
                            last_occurrence=current_streak[-1].timestamp,
                        )
                    )
                current_streak = []

        # Check final streak
        if len(current_streak) >= min_streak:
            patterns.append(
                IdentifiedPattern(
                    pattern_id=str(uuid4()),
                    pattern_type=PatternType.SUCCESS_STREAK,
                    confidence=0.85,
                    occurrences=len(current_streak),
                    affected_fsas=list(set(l.fsa_name for l in current_streak)),
                    description=f"Success streak of {len(current_streak)} consecutive executions",
                    evidence=[
                        {"execution_id": l.execution_id}
                        for l in current_streak[:5]
                    ],
                    first_occurrence=current_streak[0].timestamp,
                    last_occurrence=current_streak[-1].timestamp,
                )
            )

        return patterns

    def _identify_failure_clusters(
        self, logs: List[ExecutionLog]
    ) -> List[IdentifiedPattern]:
        """Identify clusters of failures."""
        patterns = []
        min_cluster = self.config.get("pattern_min_occurrences", 3)

        current_cluster: List[ExecutionLog] = []

        for log in logs:
            if not log.success:
                current_cluster.append(log)
            else:
                if len(current_cluster) >= min_cluster:
                    patterns.append(
                        IdentifiedPattern(
                            pattern_id=str(uuid4()),
                            pattern_type=PatternType.FAILURE_CLUSTER,
                            confidence=0.9,
                            occurrences=len(current_cluster),
                            affected_fsas=list(
                                set(l.fsa_name for l in current_cluster)
                            ),
                            description=f"Failure cluster of {len(current_cluster)} consecutive failures",
                            evidence=[
                                {
                                    "execution_id": l.execution_id,
                                    "error": l.error_message,
                                }
                                for l in current_cluster[:5]
                            ],
                            first_occurrence=current_cluster[0].timestamp,
                            last_occurrence=current_cluster[-1].timestamp,
                        )
                    )
                current_cluster = []

        return patterns

    def _identify_performance_degradation(
        self, logs: List[ExecutionLog]
    ) -> List[IdentifiedPattern]:
        """Identify gradual performance degradation."""
        patterns = []
        window_size = 10

        if len(logs) < window_size * 2:
            return patterns

        # Calculate moving average of duration
        for i in range(window_size, len(logs)):
            prev_window = logs[i - window_size : i]
            curr_window = logs[i : min(i + window_size, len(logs))]

            if len(curr_window) < window_size // 2:
                continue

            prev_avg = mean(l.duration_ms for l in prev_window)
            curr_avg = mean(l.duration_ms for l in curr_window)

            # Check for significant degradation (>50% increase)
            if prev_avg > 0 and (curr_avg - prev_avg) / prev_avg > 0.5:
                patterns.append(
                    IdentifiedPattern(
                        pattern_id=str(uuid4()),
                        pattern_type=PatternType.PERFORMANCE_DEGRADATION,
                        confidence=0.75,
                        occurrences=1,
                        affected_fsas=list(
                            set(l.fsa_name for l in curr_window)
                        ),
                        description=f"Performance degradation: {prev_avg:.0f}ms -> {curr_avg:.0f}ms",
                        evidence=[
                            {"prev_avg_ms": prev_avg, "curr_avg_ms": curr_avg}
                        ],
                        first_occurrence=curr_window[0].timestamp,
                        last_occurrence=curr_window[-1].timestamp,
                    )
                )
                break  # Report first occurrence only

        return patterns

    def _identify_recovery_patterns(
        self, logs: List[ExecutionLog]
    ) -> List[IdentifiedPattern]:
        """Identify recovery patterns after failures."""
        patterns = []

        for i in range(1, len(logs)):
            # Look for failure followed by success
            if not logs[i - 1].success and logs[i].success:
                # Check if there's a subsequent streak of successes
                success_count = 0
                for j in range(i, min(i + 5, len(logs))):
                    if logs[j].success:
                        success_count += 1
                    else:
                        break

                if success_count >= 3:
                    patterns.append(
                        IdentifiedPattern(
                            pattern_id=str(uuid4()),
                            pattern_type=PatternType.RECOVERY_PATTERN,
                            confidence=0.8,
                            occurrences=1,
                            affected_fsas=[logs[i].fsa_name],
                            description=f"Recovery after failure with {success_count} subsequent successes",
                            evidence=[
                                {
                                    "failed_execution": logs[i - 1].execution_id,
                                    "recovery_execution": logs[i].execution_id,
                                }
                            ],
                            first_occurrence=logs[i - 1].timestamp,
                            last_occurrence=logs[min(i + success_count - 1, len(logs) - 1)].timestamp,
                        )
                    )

        return patterns

    def _identify_state_oscillation(
        self, logs: List[ExecutionLog]
    ) -> List[IdentifiedPattern]:
        """Identify state oscillation patterns (alternating success/failure)."""
        patterns = []

        if len(logs) < 6:
            return patterns

        # Look for alternating patterns
        for i in range(len(logs) - 5):
            window = logs[i : i + 6]
            alternating = all(
                window[j].success != window[j + 1].success
                for j in range(5)
            )

            if alternating:
                patterns.append(
                    IdentifiedPattern(
                        pattern_id=str(uuid4()),
                        pattern_type=PatternType.STATE_OSCILLATION,
                        confidence=0.85,
                        occurrences=1,
                        affected_fsas=list(set(l.fsa_name for l in window)),
                        description="State oscillation: alternating success/failure pattern",
                        evidence=[
                            {"execution_id": l.execution_id, "success": l.success}
                            for l in window
                        ],
                        first_occurrence=window[0].timestamp,
                        last_occurrence=window[-1].timestamp,
                    )
                )
                break  # Report first occurrence

        return patterns

    def generate_recommendations(
        self,
        lq_trends: Optional[LQTrendAnalysis] = None,
        success_rates: Optional[SuccessRateMetrics] = None,
        patterns: Optional[List[IdentifiedPattern]] = None,
    ) -> List[Recommendation]:
        """
        Generate actionable optimization recommendations based on analysis results.

        Synthesizes insights from LQ trends, success rates, and identified patterns
        to produce prioritized recommendations for improving FSA execution quality.

        Args:
            lq_trends: Optional LQ trend analysis results.
            success_rates: Optional success rate metrics.
            patterns: Optional list of identified patterns.

        Returns:
            List of Recommendation objects.
        """
        logger.info("Generating optimization recommendations...")

        recommendations: List[Recommendation] = []

        # Generate recommendations based on LQ trends
        if lq_trends:
            recommendations.extend(
                self._recommendations_from_lq_trends(lq_trends)
            )

        # Generate recommendations based on success rates
        if success_rates:
            recommendations.extend(
                self._recommendations_from_success_rates(success_rates)
            )

        # Generate recommendations based on patterns
        if patterns:
            recommendations.extend(
                self._recommendations_from_patterns(patterns)
            )

        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
            RecommendationPriority.INFORMATIONAL: 4,
        }

        recommendations.sort(key=lambda r: priority_order.get(r.priority, 5))

        logger.info("Generated %d recommendations", len(recommendations))

        return recommendations

    def _recommendations_from_lq_trends(
        self, trends: LQTrendAnalysis
    ) -> List[Recommendation]:
        """Generate recommendations from LQ trend analysis."""
        recommendations = []

        # Check for degrading trend
        if trends.trend_direction == "degrading":
            recommendations.append(
                Recommendation(
                    recommendation_id=str(uuid4()),
                    priority=RecommendationPriority.HIGH,
                    title="Address Degrading LQ Trend",
                    description="The overall Logical Quality is showing a downward trend.",
                    rationale=f"LQ trend slope is {trends.trend_slope:.4f}, indicating consistent degradation over time.",
                    affected_components=["All FSAs"],
                    estimated_impact="High - continued degradation may lead to system instability",
                    implementation_steps=[
                        "Review recent changes to FSA configurations",
                        "Analyze error logs for new failure modes",
                        "Consider implementing additional validation checks",
                        "Review resource allocation and scaling policies",
                    ],
                    related_patterns=[],
                )
            )

        # Check for high variance
        if trends.std_deviation > 0.2:
            recommendations.append(
                Recommendation(
                    recommendation_id=str(uuid4()),
                    priority=RecommendationPriority.MEDIUM,
                    title="Reduce LQ Score Variance",
                    description="High variance in LQ scores indicates inconsistent execution quality.",
                    rationale=f"Standard deviation of {trends.std_deviation:.4f} suggests unpredictable performance.",
                    affected_components=["All FSAs"],
                    estimated_impact="Medium - inconsistent quality affects reliability",
                    implementation_steps=[
                        "Identify and standardize execution environments",
                        "Implement retry logic for transient failures",
                        "Add input validation to reduce edge cases",
                        "Consider adding circuit breakers for unstable components",
                    ],
                    related_patterns=[],
                )
            )

        # Check for anomalies
        if trends.anomalies:
            recommendations.append(
                Recommendation(
                    recommendation_id=str(uuid4()),
                    priority=RecommendationPriority.MEDIUM,
                    title="Investigate LQ Anomalies",
                    description=f"Detected {len(trends.anomalies)} anomalous executions.",
                    rationale="Anomalies may indicate edge cases or environmental issues.",
                    affected_components=[
                        a.get("execution_id", "unknown")
                        for a in trends.anomalies[:5]
                    ],
                    estimated_impact="Medium - understanding anomalies improves overall quality",
                    implementation_steps=[
                        "Review execution logs for anomalous runs",
                        "Check for common factors (time, input, environment)",
                        "Implement monitoring alerts for anomaly detection",
                        "Add detailed logging for edge cases",
                    ],
                    related_patterns=[],
                )
            )

        return recommendations

    def _recommendations_from_success_rates(
        self, metrics: SuccessRateMetrics
    ) -> List[Recommendation]:
        """Generate recommendations from success rate metrics."""
        recommendations = []

        # Critical success rate
        if metrics.success_rate < 0.8:
            priority = (
                RecommendationPriority.CRITICAL
                if metrics.success_rate < 0.5
                else RecommendationPriority.HIGH
            )
            recommendations.append(
                Recommendation(
                    recommendation_id=str(uuid4()),
                    priority=priority,
                    title="Improve Overall Success Rate",
                    description=f"Current success rate of {metrics.success_rate * 100:.1f}% is below acceptable threshold.",
                    rationale=f"{metrics.failed_executions} failures out of {metrics.total_executions} total executions.",
                    affected_components=["All FSAs"],
                    estimated_impact="Critical - high failure rate affects system reliability",
                    implementation_steps=[
                        "Prioritize fixing most common error types",
                        "Implement comprehensive error handling",
                        "Add validation at system boundaries",
                        "Consider implementing graceful degradation",
                    ],
                    related_patterns=[],
                )
            )

        # Low-performing FSAs
        low_performers = [
            fsa for fsa, rate in metrics.success_by_fsa.items() if rate < 0.7
        ]
        if low_performers:
            recommendations.append(
                Recommendation(
                    recommendation_id=str(uuid4()),
                    priority=RecommendationPriority.HIGH,
                    title="Address Low-Performing FSAs",
                    description=f"{len(low_performers)} FSA(s) have success rates below 70%.",
                    rationale=f"Affected FSAs: {', '.join(low_performers)}",
                    affected_components=low_performers,
                    estimated_impact="High - targeted fixes can significantly improve overall success rate",
                    implementation_steps=[
                        "Analyze failure patterns for each low-performing FSA",
                        "Review state transition logic for edge cases",
                        "Add additional validation and error handling",
                        "Consider redesigning problematic FSA components",
                    ],
                    related_patterns=[],
                )
            )

        # Common error types
        if metrics.failure_by_error_type:
            top_errors = sorted(
                metrics.failure_by_error_type.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]

            for error_type, count in top_errors:
                if count >= 3:
                    recommendations.append(
                        Recommendation(
                            recommendation_id=str(uuid4()),
                            priority=RecommendationPriority.MEDIUM,
                            title=f"Address {error_type.title()} Errors",
                            description=f"{count} failures attributed to {error_type} errors.",
                            rationale=f"Systematic fix can prevent {count} failures.",
                            affected_components=["Error handling subsystem"],
                            estimated_impact="Medium - targeted fix for common error type",
                            implementation_steps=self._get_error_fix_steps(error_type),
                            related_patterns=[],
                        )
                    )

        return recommendations

    def _get_error_fix_steps(self, error_type: str) -> List[str]:
        """Get implementation steps for fixing specific error types."""
        steps_map = {
            "timeout": [
                "Review timeout configurations",
                "Implement adaptive timeout based on operation complexity",
                "Add progress tracking for long operations",
                "Consider async processing for heavy operations",
            ],
            "validation": [
                "Review input validation rules",
                "Add comprehensive schema validation",
                "Implement better error messages for validation failures",
                "Add validation test coverage",
            ],
            "state_transition": [
                "Review FSA state transition definitions",
                "Add guard conditions for state transitions",
                "Implement state recovery mechanisms",
                "Add state transition logging",
            ],
            "resource": [
                "Review resource allocation policies",
                "Implement resource pooling",
                "Add resource monitoring and alerts",
                "Consider scaling policies",
            ],
            "network": [
                "Implement retry logic with exponential backoff",
                "Add circuit breakers for network calls",
                "Implement connection pooling",
                "Add network timeout configurations",
            ],
        }

        return steps_map.get(
            error_type,
            [
                "Investigate error root cause",
                "Implement appropriate error handling",
                "Add monitoring for error type",
                "Document fix and prevention measures",
            ],
        )

    def _recommendations_from_patterns(
        self, patterns: List[IdentifiedPattern]
    ) -> List[Recommendation]:
        """Generate recommendations from identified patterns."""
        recommendations = []

        for pattern in patterns:
            if pattern.pattern_type == PatternType.FAILURE_CLUSTER:
                recommendations.append(
                    Recommendation(
                        recommendation_id=str(uuid4()),
                        priority=RecommendationPriority.HIGH,
                        title="Address Failure Cluster",
                        description=f"Detected cluster of {pattern.occurrences} consecutive failures.",
                        rationale=pattern.description,
                        affected_components=pattern.affected_fsas,
                        estimated_impact="High - failure clusters indicate systemic issues",
                        implementation_steps=[
                            "Analyze common factors in cluster failures",
                            "Review system state during failure period",
                            "Implement circuit breakers to prevent cascade",
                            "Add alerting for failure clusters",
                        ],
                        related_patterns=[pattern.pattern_id],
                    )
                )

            elif pattern.pattern_type == PatternType.PERFORMANCE_DEGRADATION:
                recommendations.append(
                    Recommendation(
                        recommendation_id=str(uuid4()),
                        priority=RecommendationPriority.MEDIUM,
                        title="Address Performance Degradation",
                        description="Detected gradual performance degradation pattern.",
                        rationale=pattern.description,
                        affected_components=pattern.affected_fsas,
                        estimated_impact="Medium - gradual degradation leads to eventual failure",
                        implementation_steps=[
                            "Profile execution to identify bottlenecks",
                            "Review resource usage trends",
                            "Check for memory leaks or resource accumulation",
                            "Implement performance monitoring and alerts",
                        ],
                        related_patterns=[pattern.pattern_id],
                    )
                )

            elif pattern.pattern_type == PatternType.STATE_OSCILLATION:
                recommendations.append(
                    Recommendation(
                        recommendation_id=str(uuid4()),
                        priority=RecommendationPriority.MEDIUM,
                        title="Investigate State Oscillation",
                        description="Detected alternating success/failure pattern.",
                        rationale=pattern.description,
                        affected_components=pattern.affected_fsas,
                        estimated_impact="Medium - oscillation indicates unstable state",
                        implementation_steps=[
                            "Analyze conditions causing alternating outcomes",
                            "Review state transition logic",
                            "Check for race conditions or timing issues",
                            "Implement state stabilization mechanisms",
                        ],
                        related_patterns=[pattern.pattern_id],
                    )
                )

        return recommendations

    def calculate_meta_lq(self) -> MetaLQAssessment:
        """
        Calculate meta-level LQ for the analyzer itself (self-assessment).

        Performs self-assessment of the analyzer's capabilities, coverage,
        and effectiveness to provide insights for continuous improvement.

        Returns:
            MetaLQAssessment object.
        """
        logger.info("Calculating meta-level LQ (self-assessment)...")

        component_scores: Dict[str, float] = {}
        strengths: List[str] = []
        weaknesses: List[str] = []
        recommendations: List[str] = []

        # Assess log collection capability
        log_collection_score = self._assess_log_collection()
        component_scores["log_collection"] = log_collection_score

        # Assess trend analysis capability
        trend_analysis_score = self._assess_trend_analysis()
        component_scores["trend_analysis"] = trend_analysis_score

        # Assess pattern recognition capability
        pattern_recognition_score = self._assess_pattern_recognition()
        component_scores["pattern_recognition"] = pattern_recognition_score

        # Assess recommendation quality
        recommendation_score = self._assess_recommendation_quality()
        component_scores["recommendation_quality"] = recommendation_score

        # Assess integration capability
        integration_score = self._assess_integration()
        component_scores["integration"] = integration_score

        # Calculate overall LQ
        overall_lq = mean(component_scores.values())

        # Determine category
        thresholds = self.config.get("lq_thresholds", {})
        if overall_lq >= thresholds.get("excellent", 0.9):
            category = LQCategory.EXCELLENT
        elif overall_lq >= thresholds.get("good", 0.75):
            category = LQCategory.GOOD
        elif overall_lq >= thresholds.get("acceptable", 0.6):
            category = LQCategory.ACCEPTABLE
        elif overall_lq >= thresholds.get("poor", 0.4):
            category = LQCategory.POOR
        else:
            category = LQCategory.CRITICAL

        # Identify strengths and weaknesses
        for component, score in component_scores.items():
            if score >= 0.8:
                strengths.append(f"Strong {component.replace('_', ' ')}: {score:.2f}")
            elif score < 0.6:
                weaknesses.append(f"Weak {component.replace('_', ' ')}: {score:.2f}")
                recommendations.append(f"Improve {component.replace('_', ' ')} capabilities")

        # Add general recommendations
        if overall_lq < 0.8:
            recommendations.append("Review and optimize analysis algorithms")
            recommendations.append("Expand pattern recognition capabilities")

        if not self._execution_logs:
            recommendations.append("Collect execution logs before analysis")
            weaknesses.append("No execution logs collected")

        assessment = MetaLQAssessment(
            assessment_id=str(uuid4()),
            timestamp=datetime.now(),
            overall_lq=round(overall_lq, 4),
            category=category,
            component_scores={k: round(v, 4) for k, v in component_scores.items()},
            strengths=strengths,
            weaknesses=weaknesses,
            self_improvement_recommendations=recommendations,
        )

        logger.info(
            "Meta-LQ assessment complete: %.4f (%s)",
            overall_lq,
            category.value,
        )

        return assessment

    def _assess_log_collection(self) -> float:
        """Assess log collection capability."""
        score = 0.5  # Base score

        # Check if PowerShell is available
        try:
            result = subprocess.run(
                ["powershell", "-Command", "echo 'test'"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                score += 0.2
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # PowerShell not available

        # Check if logs have been collected
        if self._execution_logs:
            score += 0.3

        return min(score, 1.0)

    def _assess_trend_analysis(self) -> float:
        """Assess trend analysis capability."""
        score = 0.7  # Base capability score

        # Check if sufficient data for trend analysis
        if len(self._execution_logs) >= self.config.get("min_executions_for_trend", 5):
            score += 0.2

        # Check if analysis has been performed
        if self._analysis_history:
            score += 0.1

        return min(score, 1.0)

    def _assess_pattern_recognition(self) -> float:
        """Assess pattern recognition capability."""
        score = 0.6  # Base capability score

        # Score based on number of pattern types supported
        supported_patterns = len(PatternType)
        score += 0.05 * min(supported_patterns, 6)

        return min(score, 1.0)

    def _assess_recommendation_quality(self) -> float:
        """Assess recommendation generation quality."""
        score = 0.65  # Base capability score

        # Score based on recommendation categories covered
        if self._analysis_history:
            latest = self._analysis_history[-1]
            if latest.recommendations:
                # More recommendations indicate better coverage
                score += min(len(latest.recommendations) * 0.05, 0.25)
        else:
            score += 0.1  # Capability exists even without history

        return min(score, 1.0)

    def _assess_integration(self) -> float:
        """Assess FSA integration capability."""
        score = 0.5  # Base capability score

        # Check integration layer status
        if self.integration_layer:
            status = self.integration_layer.get_integration_status()
            if status.get("registered_fsas", 0) > 0:
                score += 0.2
            if status.get("event_handlers"):
                score += 0.15
            score += 0.15  # Integration layer exists

        return min(score, 1.0)

    def run_full_analysis(self) -> AnalysisResult:
        """
        Run a complete analysis workflow.

        Executes all analysis steps: log collection, LQ trend analysis,
        success rate calculation, pattern identification, recommendation
        generation, and meta-LQ self-assessment.

        Returns:
            Complete AnalysisResult object.
        """
        logger.info("Starting full analysis workflow...")
        start_time = datetime.now()

        # Collect logs if not already done
        if not self._execution_logs:
            self.collect_execution_logs()

        # Run all analyses
        lq_trends = self.analyze_lq_trends()
        success_rates = self.calculate_success_rates()
        patterns = self.identify_patterns()
        recommendations = self.generate_recommendations(
            lq_trends, success_rates, patterns
        )
        meta_lq = self.calculate_meta_lq()

        # Calculate analysis duration
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        result = AnalysisResult(
            analysis_id=str(uuid4()),
            timestamp=end_time,
            lq_trends=lq_trends,
            success_rates=success_rates,
            identified_patterns=patterns,
            recommendations=recommendations,
            meta_lq=meta_lq,
            execution_count=len(self._execution_logs),
            analysis_duration_ms=round(duration_ms, 2),
        )

        self._analysis_history.append(result)

        logger.info(
            "Full analysis complete in %.2fms. Analyzed %d executions.",
            duration_ms,
            len(self._execution_logs),
        )

        return result

    def export_results(
        self,
        result: AnalysisResult,
        output_path: str,
    ) -> bool:
        """
        Export analysis results to JSON file using PowerShell.

        Args:
            result: AnalysisResult to export.
            output_path: Path for the output JSON file.

        Returns:
            True if export successful, False otherwise.
        """
        logger.info("Exporting results to %s...", output_path)

        json_content = result.to_json()

        # Use PowerShell to write file
        success = self.powershell.write_file(output_path, json_content)

        if success:
            logger.info("Results exported successfully to %s", output_path)
        else:
            # Fallback to direct file write
            try:
                with open(output_path, "w") as f:
                    f.write(json_content)
                logger.info("Results exported via fallback to %s", output_path)
                return True
            except Exception as e:
                logger.error("Failed to export results: %s", str(e))
                return False

        return success

    def load_logs_from_data(self, log_data: List[Dict[str, Any]]) -> None:
        """
        Load execution logs from provided data (for testing or direct input).

        Args:
            log_data: List of log dictionaries.
        """
        self._execution_logs = [
            ExecutionLog.from_dict(entry) for entry in log_data
        ]
        logger.info("Loaded %d logs from data", len(self._execution_logs))


def create_cli_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI interface.

    Returns:
        Configured ArgumentParser object.
    """
    parser = argparse.ArgumentParser(
        prog="fsa1_meta_pattern_analyzer",
        description="FSA Meta-Pattern Analyzer - Analyze LQ trends and patterns in FSA executions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --log-dir ./logs --output results.json
  %(prog)s --log-dir ./logs --analyze-only
  %(prog)s --demo
        """,
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        default="./fsa_logs",
        help="Directory containing FSA execution logs (default: ./fsa_logs)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="analysis_results.json",
        help="Output file path for results (default: analysis_results.json)",
    )

    parser.add_argument(
        "--log-pattern",
        type=str,
        default="*.json",
        help="Pattern for log files (default: *.json)",
    )

    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Run analysis without exporting results",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data for testing",
    )

    parser.add_argument(
        "--min-executions",
        type=int,
        default=5,
        help="Minimum executions required for trend analysis (default: 5)",
    )

    return parser


def generate_demo_data() -> List[Dict[str, Any]]:
    """
    Generate demo execution log data for testing.

    Returns:
        List of demo log dictionaries.
    """
    import random

    demo_logs = []
    base_time = datetime.now()
    fsa_names = ["AuthFSA", "PaymentFSA", "OrderFSA", "NotificationFSA"]

    for i in range(50):
        # Simulate varying success rates and LQ scores
        success = random.random() > 0.2  # 80% success rate
        lq_score = random.gauss(0.75, 0.15)
        lq_score = max(0.0, min(1.0, lq_score))  # Clamp to [0, 1]

        if not success:
            lq_score *= 0.5  # Lower LQ for failures

        log = {
            "execution_id": str(uuid4()),
            "timestamp": (base_time - timedelta(hours=i)).isoformat(),
            "fsa_name": random.choice(fsa_names),
            "state_transitions": [
                "init",
                "processing",
                "completed" if success else "failed",
            ],
            "success": success,
            "duration_ms": random.gauss(500, 200),
            "lq_score": lq_score,
            "error_message": "Timeout error" if not success and random.random() > 0.5 else None,
            "metadata": {"version": "1.0", "environment": "test"},
        }
        demo_logs.append(log)

    return demo_logs


def main() -> int:
    """
    Main entry point for CLI execution.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = create_cli_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    logger.info("FSA Meta-Pattern Analyzer starting...")

    # Initialize analyzer
    config = {
        "min_executions_for_trend": args.min_executions,
        "log_file_pattern": args.log_pattern,
    }

    analyzer = FSAMetaPatternAnalyzer(
        log_directory=args.log_dir,
        config=config,
    )

    try:
        if args.demo:
            # Run with demo data
            logger.info("Running with demo data...")
            demo_data = generate_demo_data()
            analyzer.load_logs_from_data(demo_data)
        else:
            # Collect logs from directory
            analyzer.collect_execution_logs()

        # Run full analysis
        result = analyzer.run_full_analysis()

        # Print summary to stdout
        print("\n" + "=" * 60)
        print("FSA Meta-Pattern Analysis Results")
        print("=" * 60)
        print(f"Analysis ID: {result.analysis_id}")
        print(f"Timestamp: {result.timestamp.isoformat()}")
        print(f"Executions Analyzed: {result.execution_count}")
        print(f"Analysis Duration: {result.analysis_duration_ms:.2f}ms")

        if result.lq_trends:
            print("\n--- LQ Trends ---")
            print(f"Average LQ: {result.lq_trends.average_lq:.4f}")
            print(f"Trend: {result.lq_trends.trend_direction}")
            print(f"Std Deviation: {result.lq_trends.std_deviation:.4f}")

        if result.success_rates:
            print("\n--- Success Rates ---")
            print(f"Success Rate: {result.success_rates.success_rate * 100:.1f}%")
            print(f"Total: {result.success_rates.total_executions}")
            print(f"Failures: {result.success_rates.failed_executions}")

        if result.identified_patterns:
            print(f"\n--- Patterns Identified: {len(result.identified_patterns)} ---")
            for pattern in result.identified_patterns[:3]:
                print(f"  - {pattern.pattern_type.value}: {pattern.description}")

        if result.recommendations:
            print(f"\n--- Recommendations: {len(result.recommendations)} ---")
            for rec in result.recommendations[:3]:
                print(f"  [{rec.priority.value.upper()}] {rec.title}")

        if result.meta_lq:
            print("\n--- Meta-LQ Self-Assessment ---")
            print(f"Overall LQ: {result.meta_lq.overall_lq:.4f} ({result.meta_lq.category.value})")

        print("=" * 60 + "\n")

        # Export results if not analyze-only
        if not args.analyze_only:
            success = analyzer.export_results(result, args.output)
            if success:
                print(f"Results exported to: {args.output}")
            else:
                print(f"Warning: Failed to export results to {args.output}")
                return 1

        return 0

    except Exception as e:
        logger.error("Analysis failed: %s", str(e))
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

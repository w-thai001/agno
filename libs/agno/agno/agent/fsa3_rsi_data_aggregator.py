"""
FSA RSI Data Aggregator - Multi-session FSA execution data aggregator.

Aggregates data across multiple FSA execution sessions, identifies cross-FSA
patterns, calculates Recursive Self-Improvement (RSI) metrics, and generates
optimization insights for the framework.

CRITICAL: All file operations use PowerShell subprocess commands exclusively:
- Get-ChildItem -Recurse for multi-directory scanning
- Get-Content -Raw for JSON log reading
- ConvertTo-Json piping for data export
- NO Python file I/O operations
"""

import argparse
import json
import logging
import subprocess
import sys
import threading
import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# Agno imports for integration
try:
    from agno.utils.log import get_logger, logger as agno_logger
    from agno.agent.metrics import SessionMetrics
    from agno.run.response import RunEvent, RunResponse
except ImportError:
    agno_logger = None
    SessionMetrics = None
    RunEvent = None
    RunResponse = None

# Try to import from sibling module
try:
    from agno.agent.fsa1_meta_pattern_analyzer import (
        FSAExecutionRecord,
        FSAExecutionStatus,
        FSAPatternAnalysis,
        PowerShellError,
        FSAIntegrationLayer,
    )
except ImportError:
    # Define locally if not available
    FSAExecutionRecord = None
    FSAExecutionStatus = None
    FSAPatternAnalysis = None
    PowerShellError = None
    FSAIntegrationLayer = None


# Module-level logger configuration
LOGGER_NAME = "fsa_rsi_data_aggregator"


def _setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure module logger with rich formatting if available."""
    _logger = logging.getLogger(name)

    if not _logger.handlers:
        try:
            from rich.logging import RichHandler
            handler = RichHandler(
                show_time=True,
                rich_tracebacks=True,
                show_path=True,
                tracebacks_show_locals=True,
            )
            handler.setFormatter(logging.Formatter(
                fmt="%(message)s",
                datefmt="[%X]",
            ))
        except ImportError:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))

        _logger.addHandler(handler)
        _logger.setLevel(level)
        _logger.propagate = False

    return _logger


logger = _setup_logger(LOGGER_NAME)


# ============================================================================
# Enums and Constants
# ============================================================================

class RSILevel(str, Enum):
    """Levels of Recursive Self-Improvement capability."""
    NONE = "none"  # No self-improvement detected
    BASIC = "basic"  # Simple parameter tuning
    INTERMEDIATE = "intermediate"  # Strategy adaptation
    ADVANCED = "advanced"  # Architecture modification
    RECURSIVE = "recursive"  # True recursive self-improvement


class PatternType(str, Enum):
    """Types of cross-FSA patterns."""
    CORRELATION = "correlation"  # Co-occurrence patterns
    CAUSATION = "causation"  # Cause-effect relationships
    TEMPORAL = "temporal"  # Time-based patterns
    PERFORMANCE = "performance"  # Performance clustering
    FAILURE = "failure"  # Failure propagation patterns
    OPTIMIZATION = "optimization"  # Self-optimization patterns


class StreamEventType(str, Enum):
    """Types of streaming events."""
    SESSION_DISCOVERED = "session_discovered"
    SESSION_PROCESSED = "session_processed"
    PATTERN_DETECTED = "pattern_detected"
    RSI_CALCULATED = "rsi_calculated"
    INSIGHT_GENERATED = "insight_generated"
    ERROR = "error"
    COMPLETE = "complete"


class ExecutionStatus(str, Enum):
    """Execution status when FSAExecutionStatus not available."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


# ============================================================================
# PowerShell Operations
# ============================================================================

class PowerShellOperations:
    """
    Handles all file operations using PowerShell subprocess commands.

    CRITICAL: This class enforces PowerShell-only file operations.
    No Python file I/O is permitted.
    """

    POWERSHELL_EXECUTABLE = "powershell" if sys.platform == "win32" else "pwsh"
    DEFAULT_TIMEOUT = 60  # seconds for larger operations

    @classmethod
    def _execute_powershell(
        cls,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Execute a PowerShell command via subprocess.

        Args:
            command: PowerShell command to execute
            timeout: Command timeout in seconds
            check: If True, raise exception on non-zero return code

        Returns:
            CompletedProcess with stdout, stderr, returncode

        Raises:
            PowerShellOperationError: If command execution fails
        """
        logger.debug(f"Executing PowerShell: {command[:100]}...")

        try:
            result = subprocess.run(
                [cls.POWERSHELL_EXECUTABLE, "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if check and result.returncode != 0:
                raise PowerShellOperationError(
                    message="PowerShell command failed",
                    returncode=result.returncode,
                    stderr=result.stderr.strip(),
                )

            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"PowerShell command timed out after {timeout}s")
            raise PowerShellOperationError(
                message=f"Command timed out after {timeout}s",
                returncode=-1,
                stderr=str(e),
            )
        except FileNotFoundError:
            error_msg = (
                f"PowerShell executable not found: {cls.POWERSHELL_EXECUTABLE}. "
                f"On Linux/macOS, install PowerShell Core (pwsh)."
            )
            logger.error(error_msg)
            raise PowerShellOperationError(message=error_msg, returncode=-1, stderr="")

    @classmethod
    def scan_directories_recursive(
        cls,
        base_directories: List[str],
        pattern: str = "*",
        max_depth: Optional[int] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> List[str]:
        """
        Recursively scan multiple directories using Get-ChildItem -Recurse.

        Args:
            base_directories: List of directories to scan
            pattern: File pattern filter
            max_depth: Maximum recursion depth (None for unlimited)
            timeout: Command timeout

        Returns:
            List of discovered file paths
        """
        all_files: List[str] = []

        for directory in base_directories:
            safe_dir = directory.replace("'", "''")
            safe_pattern = pattern.replace("'", "''")

            depth_param = f"-Depth {max_depth}" if max_depth is not None else ""

            command = (
                f"Get-ChildItem -Path '{safe_dir}' -Filter '{safe_pattern}' "
                f"-Recurse {depth_param} -File -ErrorAction SilentlyContinue | "
                f"Select-Object -ExpandProperty FullName"
            )

            try:
                result = cls._execute_powershell(command, timeout=timeout, check=False)

                files = [
                    line.strip()
                    for line in result.stdout.strip().split('\n')
                    if line.strip()
                ]
                all_files.extend(files)
                logger.debug(f"Found {len(files)} files in '{directory}'")

            except PowerShellOperationError as e:
                logger.warning(f"Error scanning '{directory}': {e}")

        # Remove duplicates
        unique_files = list(dict.fromkeys(all_files))
        logger.info(f"Total files discovered: {len(unique_files)}")
        return unique_files

    @classmethod
    def read_json_raw(
        cls,
        file_path: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Read JSON file using Get-Content -Raw.

        Args:
            file_path: Path to JSON file
            timeout: Command timeout

        Returns:
            Parsed JSON as dictionary
        """
        safe_path = file_path.replace("'", "''")

        command = f"Get-Content -Path '{safe_path}' -Raw -Encoding UTF8"

        try:
            result = cls._execute_powershell(command, timeout=timeout)
            content = result.stdout.strip()

            if not content:
                return {}

            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in '{file_path}': {e}")
            return {}
        except PowerShellOperationError as e:
            logger.error(f"Failed to read '{file_path}': {e}")
            raise

    @classmethod
    def read_multiple_json_files(
        cls,
        file_paths: List[str],
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
        """
        Read multiple JSON files as a generator using Get-Content -Raw.

        Args:
            file_paths: List of file paths
            timeout: Command timeout per file

        Yields:
            Tuple of (file_path, parsed_data)
        """
        for file_path in file_paths:
            try:
                data = cls.read_json_raw(file_path, timeout=timeout)
                yield (file_path, data)
            except PowerShellOperationError as e:
                logger.warning(f"Skipping '{file_path}': {e}")
                yield (file_path, {})

    @classmethod
    def export_with_convertto_json(
        cls,
        data: Dict[str, Any],
        output_path: str,
        depth: int = 10,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Export data using ConvertTo-Json piping to Out-File.

        Args:
            data: Data to export
            output_path: Output file path
            depth: JSON serialization depth
            timeout: Command timeout

        Returns:
            True if successful
        """
        safe_path = output_path.replace("'", "''")

        # Serialize to JSON string first (Python side)
        json_str = json.dumps(data, indent=2, default=str)
        # Escape for PowerShell
        safe_json = json_str.replace("'", "''").replace("`", "``")

        # Use PowerShell to convert and write
        command = (
            f"'{safe_json}' | ConvertFrom-Json | "
            f"ConvertTo-Json -Depth {depth} | "
            f"Out-File -FilePath '{safe_path}' -Encoding UTF8"
        )

        try:
            cls._execute_powershell(command, timeout=timeout)
            logger.info(f"Exported data to '{output_path}'")
            return True
        except PowerShellOperationError as e:
            logger.error(f"Failed to export to '{output_path}': {e}")
            return False

    @classmethod
    def write_json_direct(
        cls,
        data: Dict[str, Any],
        output_path: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Write JSON data directly using Out-File.

        Args:
            data: Data to write
            output_path: Output file path
            timeout: Command timeout

        Returns:
            True if successful
        """
        safe_path = output_path.replace("'", "''")
        json_str = json.dumps(data, indent=2, default=str)
        safe_content = json_str.replace("'", "''")

        command = f"'{safe_content}' | Out-File -FilePath '{safe_path}' -Encoding UTF8"

        try:
            cls._execute_powershell(command, timeout=timeout)
            return True
        except PowerShellOperationError as e:
            logger.error(f"Failed to write '{output_path}': {e}")
            return False

    @classmethod
    def get_file_metadata(
        cls,
        file_path: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Get file metadata using Get-Item.

        Args:
            file_path: Path to file
            timeout: Command timeout

        Returns:
            Dictionary with file metadata
        """
        safe_path = file_path.replace("'", "''")

        command = (
            f"$f = Get-Item '{safe_path}' -ErrorAction SilentlyContinue; "
            f"if ($f) {{ "
            f"@{{"
            f"'FullName'=$f.FullName;"
            f"'Length'=$f.Length;"
            f"'CreationTime'=$f.CreationTime.ToString('o');"
            f"'LastWriteTime'=$f.LastWriteTime.ToString('o');"
            f"'Extension'=$f.Extension"
            f"}} | ConvertTo-Json -Compress"
            f"}} else {{ '{{}}' }}"
        )

        try:
            result = cls._execute_powershell(command, timeout=timeout, check=False)
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            return {}
        except (json.JSONDecodeError, PowerShellOperationError):
            return {}


class PowerShellOperationError(Exception):
    """Exception for PowerShell operation failures."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        self.message = message
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"{message} (rc={returncode}): {stderr}")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SessionExecutionRecord:
    """Record of a single execution within a session."""
    record_id: str
    session_id: str
    fsa_id: str
    timestamp: datetime
    status: str
    leverage_quotient: float
    execution_time_ms: float
    tokens_used: int
    success_rate: float = 1.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "session_id": self.session_id,
            "fsa_id": self.fsa_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "leverage_quotient": self.leverage_quotient,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "success_rate": self.success_rate,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionExecutionRecord":
        """Create from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        else:
            timestamp = datetime.now()

        return cls(
            record_id=data.get("record_id", data.get("id", f"rec_{datetime.now().timestamp()}")),
            session_id=data.get("session_id", "unknown"),
            fsa_id=data.get("fsa_id", data.get("agent_id", "unknown")),
            timestamp=timestamp,
            status=data.get("status", "unknown"),
            leverage_quotient=float(data.get("leverage_quotient", data.get("lq", 0.0))),
            execution_time_ms=float(data.get("execution_time_ms", data.get("duration_ms", 0.0))),
            tokens_used=int(data.get("tokens_used", data.get("total_tokens", 0))),
            success_rate=float(data.get("success_rate", 1.0)),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionData:
    """Aggregated data for a single session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_executions: int
    successful_executions: int
    failed_executions: int
    fsa_ids: Set[str]
    total_tokens: int
    total_execution_time_ms: float
    average_lq: float
    records: List[SessionExecutionRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "fsa_ids": list(self.fsa_ids),
            "total_tokens": self.total_tokens,
            "total_execution_time_ms": self.total_execution_time_ms,
            "average_lq": self.average_lq,
            "records": [r.to_dict() for r in self.records],
            "metadata": self.metadata,
        }


@dataclass
class CrossFSAPattern:
    """Detected pattern across FSAs."""
    pattern_id: str
    pattern_type: PatternType
    fsa_ids_involved: List[str]
    confidence: float
    description: str
    supporting_evidence: List[str]
    timestamp_detected: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "fsa_ids_involved": self.fsa_ids_involved,
            "confidence": self.confidence,
            "description": self.description,
            "supporting_evidence": self.supporting_evidence,
            "timestamp_detected": self.timestamp_detected.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RSIMetrics:
    """Recursive Self-Improvement metrics."""
    fsa_id: str
    rsi_level: RSILevel
    improvement_rate: float  # Rate of performance improvement over time
    adaptation_score: float  # Ability to adapt to new patterns
    recursion_depth: int  # Depth of self-referential improvement
    stability_index: float  # Stability of improvements
    efficiency_gain: float  # Efficiency improvement percentage
    learning_velocity: float  # Speed of learning from feedback
    meta_awareness: float  # Awareness of own performance
    optimization_potential: float  # Remaining optimization potential
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fsa_id": self.fsa_id,
            "rsi_level": self.rsi_level.value,
            "improvement_rate": round(self.improvement_rate, 4),
            "adaptation_score": round(self.adaptation_score, 4),
            "recursion_depth": self.recursion_depth,
            "stability_index": round(self.stability_index, 4),
            "efficiency_gain": round(self.efficiency_gain, 4),
            "learning_velocity": round(self.learning_velocity, 4),
            "meta_awareness": round(self.meta_awareness, 4),
            "optimization_potential": round(self.optimization_potential, 4),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RSIInsight:
    """Meta-RSI insight for framework optimization."""
    insight_id: str
    category: str
    title: str
    description: str
    priority: int  # 1-5, 1 being highest
    affected_fsas: List[str]
    recommended_actions: List[str]
    expected_improvement: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_id": self.insight_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "affected_fsas": self.affected_fsas,
            "recommended_actions": self.recommended_actions,
            "expected_improvement": round(self.expected_improvement, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StreamEvent:
    """Event for real-time streaming."""
    event_type: StreamEventType
    timestamp: datetime
    data: Dict[str, Any]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "message": self.message,
        }


@dataclass
class DashboardData:
    """Aggregated data for RSI visualization dashboard."""
    generated_at: datetime
    total_sessions: int
    total_executions: int
    total_fsas: int
    overall_success_rate: float
    average_rsi_level: float
    patterns_detected: int
    insights_generated: int
    session_summaries: List[Dict[str, Any]]
    fsa_performance: Dict[str, Dict[str, Any]]
    rsi_metrics: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    time_series: Dict[str, List[Dict[str, Any]]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_sessions": self.total_sessions,
                "total_executions": self.total_executions,
                "total_fsas": self.total_fsas,
                "overall_success_rate": round(self.overall_success_rate, 4),
                "average_rsi_level": round(self.average_rsi_level, 4),
                "patterns_detected": self.patterns_detected,
                "insights_generated": self.insights_generated,
            },
            "session_summaries": self.session_summaries,
            "fsa_performance": self.fsa_performance,
            "rsi_metrics": self.rsi_metrics,
            "patterns": self.patterns,
            "insights": self.insights,
            "time_series": self.time_series,
        }


# ============================================================================
# Integration Hooks
# ============================================================================

class IntegrationHook(ABC):
    """Abstract base class for integration hooks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Hook name."""
        pass

    @abstractmethod
    def on_session_discovered(self, session_data: SessionData) -> None:
        """Called when a new session is discovered."""
        pass

    @abstractmethod
    def on_pattern_detected(self, pattern: CrossFSAPattern) -> None:
        """Called when a pattern is detected."""
        pass

    @abstractmethod
    def on_rsi_calculated(self, metrics: RSIMetrics) -> None:
        """Called when RSI metrics are calculated."""
        pass

    @abstractmethod
    def on_insight_generated(self, insight: RSIInsight) -> None:
        """Called when an insight is generated."""
        pass


class LoggingHook(IntegrationHook):
    """Hook that logs all events."""

    @property
    def name(self) -> str:
        return "logging_hook"

    def on_session_discovered(self, session_data: SessionData) -> None:
        logger.info(f"[Hook] Session discovered: {session_data.session_id}")

    def on_pattern_detected(self, pattern: CrossFSAPattern) -> None:
        logger.info(f"[Hook] Pattern detected: {pattern.pattern_type.value} - {pattern.description}")

    def on_rsi_calculated(self, metrics: RSIMetrics) -> None:
        logger.info(f"[Hook] RSI calculated for {metrics.fsa_id}: level={metrics.rsi_level.value}")

    def on_insight_generated(self, insight: RSIInsight) -> None:
        logger.info(f"[Hook] Insight generated: {insight.title} (priority={insight.priority})")


class CallbackHook(IntegrationHook):
    """Hook that calls user-provided callbacks."""

    def __init__(
        self,
        name: str = "callback_hook",
        on_session: Optional[Callable[[SessionData], None]] = None,
        on_pattern: Optional[Callable[[CrossFSAPattern], None]] = None,
        on_rsi: Optional[Callable[[RSIMetrics], None]] = None,
        on_insight: Optional[Callable[[RSIInsight], None]] = None,
    ):
        self._name = name
        self._on_session = on_session
        self._on_pattern = on_pattern
        self._on_rsi = on_rsi
        self._on_insight = on_insight

    @property
    def name(self) -> str:
        return self._name

    def on_session_discovered(self, session_data: SessionData) -> None:
        if self._on_session:
            self._on_session(session_data)

    def on_pattern_detected(self, pattern: CrossFSAPattern) -> None:
        if self._on_pattern:
            self._on_pattern(pattern)

    def on_rsi_calculated(self, metrics: RSIMetrics) -> None:
        if self._on_rsi:
            self._on_rsi(metrics)

    def on_insight_generated(self, insight: RSIInsight) -> None:
        if self._on_insight:
            self._on_insight(insight)


# ============================================================================
# Real-time Streaming
# ============================================================================

class StreamingAggregator:
    """
    Provides real-time streaming of aggregation events.

    Enables consumers to receive events as they occur during aggregation.
    """

    def __init__(self, buffer_size: int = 1000):
        """
        Initialize streaming aggregator.

        Args:
            buffer_size: Maximum number of events to buffer
        """
        self._event_queue: queue.Queue[StreamEvent] = queue.Queue(maxsize=buffer_size)
        self._subscribers: List[Callable[[StreamEvent], None]] = []
        self._is_streaming = False
        self._dispatch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_streaming(self) -> None:
        """Start the streaming dispatcher."""
        if self._is_streaming:
            return

        self._is_streaming = True
        self._stop_event.clear()
        self._dispatch_thread = threading.Thread(target=self._dispatch_events, daemon=True)
        self._dispatch_thread.start()
        logger.info("Streaming started")

    def stop_streaming(self) -> None:
        """Stop the streaming dispatcher."""
        if not self._is_streaming:
            return

        self._stop_event.set()
        self._is_streaming = False

        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=5.0)

        logger.info("Streaming stopped")

    def subscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """
        Subscribe to streaming events.

        Args:
            callback: Function to call for each event
        """
        self._subscribers.append(callback)
        logger.debug(f"Subscriber added. Total: {len(self._subscribers)}")

    def unsubscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        """
        Unsubscribe from streaming events.

        Args:
            callback: Previously subscribed callback
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.debug(f"Subscriber removed. Total: {len(self._subscribers)}")

    def emit(self, event_type: StreamEventType, data: Dict[str, Any], message: str) -> None:
        """
        Emit a streaming event.

        Args:
            event_type: Type of event
            data: Event data
            message: Human-readable message
        """
        event = StreamEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            message=message,
        )

        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue full, dropping event")

    def _dispatch_events(self) -> None:
        """Dispatch events to subscribers."""
        while not self._stop_event.is_set():
            try:
                event = self._event_queue.get(timeout=0.1)

                for subscriber in self._subscribers:
                    try:
                        subscriber(event)
                    except Exception as e:
                        logger.error(f"Subscriber error: {e}")

            except queue.Empty:
                continue

    def iter_events(self, timeout: float = 0.1) -> Iterator[StreamEvent]:
        """
        Iterate over events as they arrive.

        Args:
            timeout: Timeout for each poll

        Yields:
            StreamEvent objects
        """
        while self._is_streaming:
            try:
                event = self._event_queue.get(timeout=timeout)
                yield event
            except queue.Empty:
                continue


# ============================================================================
# Main Aggregator Class
# ============================================================================

class FSARSIDataAggregator:
    """
    Multi-session FSA execution data aggregator.

    Aggregates data from multiple FSA execution sessions, identifies patterns,
    calculates RSI metrics, and generates optimization insights.

    CRITICAL: All file operations use PowerShell subprocess exclusively.
    """

    VERSION = "1.0.0"
    DEFAULT_PATTERNS = ["*.json", "*.log", "*session*.txt", "*fsa*.txt"]

    def __init__(
        self,
        data_directories: Optional[List[str]] = None,
        hooks: Optional[List[IntegrationHook]] = None,
        enable_streaming: bool = False,
    ):
        """
        Initialize the RSI data aggregator.

        Args:
            data_directories: Directories containing FSA execution data
            hooks: Integration hooks for event notifications
            enable_streaming: Enable real-time event streaming
        """
        self.data_directories = data_directories or ["."]
        self.hooks = hooks or []
        self.ps_ops = PowerShellOperations()

        # Add default logging hook if no hooks provided
        if not self.hooks:
            self.hooks.append(LoggingHook())

        # Internal state
        self._sessions: Dict[str, SessionData] = {}
        self._all_records: List[SessionExecutionRecord] = []
        self._patterns: List[CrossFSAPattern] = []
        self._rsi_metrics: Dict[str, RSIMetrics] = {}
        self._insights: List[RSIInsight] = []

        # Streaming
        self._streaming = StreamingAggregator() if enable_streaming else None
        if self._streaming:
            self._streaming.start_streaming()

        # Metrics tracking
        self._aggregation_start: Optional[datetime] = None
        self._files_processed = 0
        self._total_records = 0

        logger.info(f"FSARSIDataAggregator v{self.VERSION} initialized")
        logger.info(f"Data directories: {self.data_directories}")

    def __del__(self):
        """Cleanup on destruction."""
        if self._streaming:
            self._streaming.stop_streaming()

    # ========================================================================
    # Core Aggregation Methods
    # ========================================================================

    def aggregate_sessions(
        self,
        patterns: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
    ) -> Dict[str, SessionData]:
        """
        Aggregate data from multiple FSA execution sessions.

        Uses PowerShell Get-ChildItem -Recurse for multi-directory scanning
        and Get-Content -Raw for JSON log reading.

        Args:
            patterns: File patterns to search for
            max_depth: Maximum directory recursion depth

        Returns:
            Dictionary mapping session IDs to SessionData
        """
        self._aggregation_start = datetime.now()
        patterns = patterns or self.DEFAULT_PATTERNS

        logger.info(f"Starting session aggregation across {len(self.data_directories)} directories")

        # Discover all data files
        all_files: List[str] = []
        for pattern in patterns:
            files = self.ps_ops.scan_directories_recursive(
                base_directories=self.data_directories,
                pattern=pattern,
                max_depth=max_depth,
            )
            all_files.extend(files)

        # Remove duplicates
        unique_files = list(dict.fromkeys(all_files))
        logger.info(f"Discovered {len(unique_files)} unique data files")

        # Stream discovery event
        if self._streaming:
            self._streaming.emit(
                StreamEventType.SESSION_DISCOVERED,
                {"file_count": len(unique_files)},
                f"Discovered {len(unique_files)} data files",
            )

        # Process each file
        for file_path, data in self.ps_ops.read_multiple_json_files(unique_files):
            self._files_processed += 1

            if not data:
                continue

            # Extract records from data
            records = self._extract_records(data, file_path)

            for record in records:
                self._all_records.append(record)
                self._total_records += 1

                # Group by session
                if record.session_id not in self._sessions:
                    self._sessions[record.session_id] = self._create_session_data(record)
                else:
                    self._update_session_data(self._sessions[record.session_id], record)

        # Finalize session data
        for session in self._sessions.values():
            self._finalize_session(session)

            # Notify hooks
            for hook in self.hooks:
                hook.on_session_discovered(session)

            # Stream event
            if self._streaming:
                self._streaming.emit(
                    StreamEventType.SESSION_PROCESSED,
                    {"session_id": session.session_id, "executions": session.total_executions},
                    f"Processed session {session.session_id}",
                )

        logger.info(f"Aggregated {len(self._sessions)} sessions with {self._total_records} records")
        return self._sessions

    def _extract_records(
        self,
        data: Dict[str, Any],
        source_file: str,
    ) -> List[SessionExecutionRecord]:
        """Extract execution records from parsed data."""
        records = []

        # Handle array of records
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    record = self._parse_record(item, source_file)
                    if record:
                        records.append(record)

        # Handle nested structures
        elif isinstance(data, dict):
            # Check for common container keys
            for key in ["executions", "records", "runs", "data", "sessions"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, dict):
                            record = self._parse_record(item, source_file)
                            if record:
                                records.append(record)
                    return records

            # Single record
            record = self._parse_record(data, source_file)
            if record:
                records.append(record)

        return records

    def _parse_record(
        self,
        data: Dict[str, Any],
        source_file: str,
    ) -> Optional[SessionExecutionRecord]:
        """Parse a single record from data."""
        try:
            # Extract session_id from various possible keys
            session_id = (
                data.get("session_id") or
                data.get("session") or
                self._extract_session_from_path(source_file) or
                "default_session"
            )

            # Extract other fields with fallbacks
            record_id = (
                data.get("record_id") or
                data.get("id") or
                data.get("run_id") or
                f"rec_{datetime.now().timestamp()}"
            )

            fsa_id = (
                data.get("fsa_id") or
                data.get("agent_id") or
                data.get("id") or
                "unknown_fsa"
            )

            # Parse timestamp
            timestamp_val = data.get("timestamp") or data.get("created_at")
            if isinstance(timestamp_val, str):
                timestamp = datetime.fromisoformat(timestamp_val.replace("Z", "+00:00"))
            elif isinstance(timestamp_val, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_val)
            else:
                timestamp = datetime.now()

            # Extract metrics
            metrics = data.get("metrics", {})
            lq = float(data.get("leverage_quotient") or data.get("lq") or 0.0)
            exec_time = float(
                data.get("execution_time_ms") or
                data.get("duration_ms") or
                (metrics.get("time", 0) * 1000) or
                0.0
            )
            tokens = int(
                data.get("tokens_used") or
                data.get("total_tokens") or
                metrics.get("total_tokens", 0) or
                0
            )

            # Calculate LQ if not provided
            if lq == 0.0 and exec_time > 0 and tokens > 0:
                lq = (tokens / 1000) / (exec_time / 1000 * 10)

            status = data.get("status", "unknown").lower()

            return SessionExecutionRecord(
                record_id=record_id,
                session_id=session_id,
                fsa_id=fsa_id,
                timestamp=timestamp,
                status=status,
                leverage_quotient=round(lq, 4),
                execution_time_ms=exec_time,
                tokens_used=tokens,
                success_rate=1.0 if status in ["success", "completed"] else 0.0,
                error_message=data.get("error_message") or data.get("error"),
                metadata={"source_file": source_file},
            )

        except Exception as e:
            logger.warning(f"Failed to parse record: {e}")
            return None

    def _extract_session_from_path(self, file_path: str) -> Optional[str]:
        """Extract session ID from file path."""
        import re

        # Common patterns: session_xxx, sess-xxx, xxx_session
        patterns = [
            r'session[_-]([a-zA-Z0-9]+)',
            r'sess[_-]([a-zA-Z0-9]+)',
            r'([a-zA-Z0-9]+)[_-]session',
        ]

        for pattern in patterns:
            match = re.search(pattern, file_path, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _create_session_data(self, record: SessionExecutionRecord) -> SessionData:
        """Create new SessionData from first record."""
        return SessionData(
            session_id=record.session_id,
            start_time=record.timestamp,
            end_time=None,
            total_executions=1,
            successful_executions=1 if record.success_rate > 0 else 0,
            failed_executions=0 if record.success_rate > 0 else 1,
            fsa_ids={record.fsa_id},
            total_tokens=record.tokens_used,
            total_execution_time_ms=record.execution_time_ms,
            average_lq=record.leverage_quotient,
            records=[record],
        )

    def _update_session_data(self, session: SessionData, record: SessionExecutionRecord) -> None:
        """Update SessionData with new record."""
        session.total_executions += 1
        session.fsa_ids.add(record.fsa_id)
        session.total_tokens += record.tokens_used
        session.total_execution_time_ms += record.execution_time_ms
        session.records.append(record)

        if record.success_rate > 0:
            session.successful_executions += 1
        else:
            session.failed_executions += 1

        # Update time bounds
        if record.timestamp < session.start_time:
            session.start_time = record.timestamp
        if session.end_time is None or record.timestamp > session.end_time:
            session.end_time = record.timestamp

    def _finalize_session(self, session: SessionData) -> None:
        """Finalize session calculations."""
        if session.records:
            lq_values = [r.leverage_quotient for r in session.records]
            session.average_lq = round(sum(lq_values) / len(lq_values), 4)

        if session.end_time is None:
            session.end_time = session.start_time

    # ========================================================================
    # Pattern Detection
    # ========================================================================

    def identify_patterns(
        self,
        min_confidence: float = 0.6,
    ) -> List[CrossFSAPattern]:
        """
        Identify cross-FSA correlation and patterns.

        Args:
            min_confidence: Minimum confidence threshold for patterns

        Returns:
            List of detected patterns
        """
        logger.info("Starting cross-FSA pattern identification")
        self._patterns.clear()

        if not self._all_records:
            logger.warning("No records available for pattern detection")
            return []

        # Group records by FSA
        fsa_records: Dict[str, List[SessionExecutionRecord]] = {}
        for record in self._all_records:
            if record.fsa_id not in fsa_records:
                fsa_records[record.fsa_id] = []
            fsa_records[record.fsa_id].append(record)

        # Detect correlation patterns
        self._detect_correlation_patterns(fsa_records, min_confidence)

        # Detect performance patterns
        self._detect_performance_patterns(fsa_records, min_confidence)

        # Detect temporal patterns
        self._detect_temporal_patterns(fsa_records, min_confidence)

        # Detect failure propagation patterns
        self._detect_failure_patterns(fsa_records, min_confidence)

        # Detect optimization patterns
        self._detect_optimization_patterns(fsa_records, min_confidence)

        logger.info(f"Identified {len(self._patterns)} patterns")
        return self._patterns

    def _detect_correlation_patterns(
        self,
        fsa_records: Dict[str, List[SessionExecutionRecord]],
        min_confidence: float,
    ) -> None:
        """Detect co-occurrence patterns between FSAs."""
        fsa_ids = list(fsa_records.keys())

        for i, fsa1 in enumerate(fsa_ids):
            for fsa2 in fsa_ids[i + 1:]:
                # Check session co-occurrence
                sessions1 = {r.session_id for r in fsa_records[fsa1]}
                sessions2 = {r.session_id for r in fsa_records[fsa2]}

                overlap = sessions1 & sessions2
                if not overlap:
                    continue

                # Calculate correlation confidence
                confidence = len(overlap) / min(len(sessions1), len(sessions2))

                if confidence >= min_confidence:
                    pattern = CrossFSAPattern(
                        pattern_id=f"corr_{fsa1}_{fsa2}",
                        pattern_type=PatternType.CORRELATION,
                        fsa_ids_involved=[fsa1, fsa2],
                        confidence=round(confidence, 4),
                        description=f"FSAs {fsa1} and {fsa2} frequently co-occur in same sessions",
                        supporting_evidence=[
                            f"Co-occurred in {len(overlap)} sessions",
                            f"Correlation confidence: {confidence:.1%}",
                        ],
                    )
                    self._patterns.append(pattern)
                    self._notify_pattern(pattern)

    def _detect_performance_patterns(
        self,
        fsa_records: Dict[str, List[SessionExecutionRecord]],
        min_confidence: float,
    ) -> None:
        """Detect performance clustering patterns."""
        # Calculate average LQ for each FSA
        fsa_lq: Dict[str, float] = {}
        for fsa_id, records in fsa_records.items():
            if records:
                fsa_lq[fsa_id] = sum(r.leverage_quotient for r in records) / len(records)

        if len(fsa_lq) < 2:
            return

        # Find high and low performers
        sorted_fsas = sorted(fsa_lq.items(), key=lambda x: x[1], reverse=True)
        avg_lq = sum(fsa_lq.values()) / len(fsa_lq)

        # High performers cluster
        high_performers = [fsa for fsa, lq in sorted_fsas if lq > avg_lq * 1.2]
        if len(high_performers) >= 2:
            pattern = CrossFSAPattern(
                pattern_id=f"perf_high_{len(self._patterns)}",
                pattern_type=PatternType.PERFORMANCE,
                fsa_ids_involved=high_performers,
                confidence=0.85,
                description="High-performing FSA cluster identified",
                supporting_evidence=[
                    f"Average LQ of cluster: {sum(fsa_lq[f] for f in high_performers) / len(high_performers):.4f}",
                    f"Overall average LQ: {avg_lq:.4f}",
                ],
            )
            self._patterns.append(pattern)
            self._notify_pattern(pattern)

        # Low performers cluster
        low_performers = [fsa for fsa, lq in sorted_fsas if lq < avg_lq * 0.8]
        if len(low_performers) >= 2:
            pattern = CrossFSAPattern(
                pattern_id=f"perf_low_{len(self._patterns)}",
                pattern_type=PatternType.PERFORMANCE,
                fsa_ids_involved=low_performers,
                confidence=0.80,
                description="Under-performing FSA cluster identified - optimization needed",
                supporting_evidence=[
                    f"Average LQ of cluster: {sum(fsa_lq[f] for f in low_performers) / len(low_performers):.4f}",
                    f"Overall average LQ: {avg_lq:.4f}",
                ],
            )
            self._patterns.append(pattern)
            self._notify_pattern(pattern)

    def _detect_temporal_patterns(
        self,
        fsa_records: Dict[str, List[SessionExecutionRecord]],
        min_confidence: float,
    ) -> None:
        """Detect time-based execution patterns."""
        for fsa_id, records in fsa_records.items():
            if len(records) < 5:
                continue

            # Sort by timestamp
            sorted_records = sorted(records, key=lambda r: r.timestamp)

            # Check for time-of-day patterns
            hours = [r.timestamp.hour for r in sorted_records]
            hour_counts: Dict[int, int] = {}
            for h in hours:
                hour_counts[h] = hour_counts.get(h, 0) + 1

            # Find peak hours
            if hour_counts:
                max_hour = max(hour_counts, key=hour_counts.get)
                max_count = hour_counts[max_hour]

                if max_count / len(hours) >= min_confidence:
                    pattern = CrossFSAPattern(
                        pattern_id=f"temp_{fsa_id}_{len(self._patterns)}",
                        pattern_type=PatternType.TEMPORAL,
                        fsa_ids_involved=[fsa_id],
                        confidence=round(max_count / len(hours), 4),
                        description=f"FSA {fsa_id} shows peak activity at hour {max_hour}",
                        supporting_evidence=[
                            f"{max_count} executions at hour {max_hour}",
                            f"Total executions: {len(hours)}",
                        ],
                    )
                    self._patterns.append(pattern)
                    self._notify_pattern(pattern)

    def _detect_failure_patterns(
        self,
        fsa_records: Dict[str, List[SessionExecutionRecord]],
        min_confidence: float,
    ) -> None:
        """Detect failure propagation patterns."""
        # Group failures by session
        session_failures: Dict[str, List[str]] = {}  # session_id -> list of failing FSAs

        for fsa_id, records in fsa_records.items():
            for record in records:
                if record.status in ["failed", "error", "timeout"]:
                    if record.session_id not in session_failures:
                        session_failures[record.session_id] = []
                    if fsa_id not in session_failures[record.session_id]:
                        session_failures[record.session_id].append(fsa_id)

        # Find co-failing FSAs
        failure_pairs: Dict[Tuple[str, str], int] = {}
        for session_id, failing_fsas in session_failures.items():
            if len(failing_fsas) >= 2:
                for i, fsa1 in enumerate(failing_fsas):
                    for fsa2 in failing_fsas[i + 1:]:
                        pair = tuple(sorted([fsa1, fsa2]))
                        failure_pairs[pair] = failure_pairs.get(pair, 0) + 1

        # Create patterns for frequent co-failures
        for (fsa1, fsa2), count in failure_pairs.items():
            if count >= 2:
                confidence = min(count / 5, 0.95)  # Cap confidence
                if confidence >= min_confidence:
                    pattern = CrossFSAPattern(
                        pattern_id=f"fail_{fsa1}_{fsa2}",
                        pattern_type=PatternType.FAILURE,
                        fsa_ids_involved=[fsa1, fsa2],
                        confidence=round(confidence, 4),
                        description=f"FSAs {fsa1} and {fsa2} frequently fail together - investigate coupling",
                        supporting_evidence=[
                            f"Co-failed in {count} sessions",
                            "Possible cascading failure or shared dependency",
                        ],
                    )
                    self._patterns.append(pattern)
                    self._notify_pattern(pattern)

    def _detect_optimization_patterns(
        self,
        fsa_records: Dict[str, List[SessionExecutionRecord]],
        min_confidence: float,
    ) -> None:
        """Detect self-optimization patterns."""
        for fsa_id, records in fsa_records.items():
            if len(records) < 10:
                continue

            # Sort by timestamp
            sorted_records = sorted(records, key=lambda r: r.timestamp)

            # Calculate LQ trend (first half vs second half)
            mid = len(sorted_records) // 2
            first_half_lq = sum(r.leverage_quotient for r in sorted_records[:mid]) / mid
            second_half_lq = sum(r.leverage_quotient for r in sorted_records[mid:]) / (len(sorted_records) - mid)

            improvement = (second_half_lq - first_half_lq) / max(first_half_lq, 0.01)

            if improvement > 0.1:  # 10% improvement
                pattern = CrossFSAPattern(
                    pattern_id=f"opt_{fsa_id}_{len(self._patterns)}",
                    pattern_type=PatternType.OPTIMIZATION,
                    fsa_ids_involved=[fsa_id],
                    confidence=min(improvement, 0.95),
                    description=f"FSA {fsa_id} shows self-optimization behavior",
                    supporting_evidence=[
                        f"LQ improvement: {improvement:.1%}",
                        f"First half avg LQ: {first_half_lq:.4f}",
                        f"Second half avg LQ: {second_half_lq:.4f}",
                    ],
                )
                self._patterns.append(pattern)
                self._notify_pattern(pattern)

    def _notify_pattern(self, pattern: CrossFSAPattern) -> None:
        """Notify hooks and streaming about detected pattern."""
        for hook in self.hooks:
            hook.on_pattern_detected(pattern)

        if self._streaming:
            self._streaming.emit(
                StreamEventType.PATTERN_DETECTED,
                pattern.to_dict(),
                f"Pattern detected: {pattern.pattern_type.value}",
            )

    # ========================================================================
    # RSI Metrics Calculation
    # ========================================================================

    def calculate_rsi_metrics(self) -> Dict[str, RSIMetrics]:
        """
        Calculate Recursive Self-Improvement metrics for each FSA.

        RSI metrics measure an FSA's ability to recursively improve its own
        performance through self-modification and adaptation.

        Returns:
            Dictionary mapping FSA IDs to RSI metrics
        """
        logger.info("Calculating RSI metrics")
        self._rsi_metrics.clear()

        # Group records by FSA
        fsa_records: Dict[str, List[SessionExecutionRecord]] = {}
        for record in self._all_records:
            if record.fsa_id not in fsa_records:
                fsa_records[record.fsa_id] = []
            fsa_records[record.fsa_id].append(record)

        for fsa_id, records in fsa_records.items():
            if len(records) < 3:
                continue

            metrics = self._calculate_fsa_rsi(fsa_id, records)
            self._rsi_metrics[fsa_id] = metrics

            # Notify hooks
            for hook in self.hooks:
                hook.on_rsi_calculated(metrics)

            # Stream event
            if self._streaming:
                self._streaming.emit(
                    StreamEventType.RSI_CALCULATED,
                    metrics.to_dict(),
                    f"RSI calculated for {fsa_id}: {metrics.rsi_level.value}",
                )

        logger.info(f"Calculated RSI metrics for {len(self._rsi_metrics)} FSAs")
        return self._rsi_metrics

    def _calculate_fsa_rsi(
        self,
        fsa_id: str,
        records: List[SessionExecutionRecord],
    ) -> RSIMetrics:
        """Calculate RSI metrics for a single FSA."""
        # Sort by timestamp
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        n = len(sorted_records)

        # Calculate improvement rate (LQ trend)
        lq_values = [r.leverage_quotient for r in sorted_records]
        improvement_rate = self._calculate_exponential_improvement(lq_values)

        # Calculate adaptation score (variance reduction over time)
        adaptation_score = self._calculate_adaptation_score(lq_values)

        # Calculate recursion depth (levels of self-referential improvement)
        recursion_depth = self._estimate_recursion_depth(sorted_records)

        # Calculate stability index
        stability_index = self._calculate_stability(lq_values)

        # Calculate efficiency gain
        if n >= 2 and lq_values[0] > 0:
            efficiency_gain = (lq_values[-1] - lq_values[0]) / lq_values[0]
        else:
            efficiency_gain = 0.0

        # Calculate learning velocity (rate of improvement per execution)
        learning_velocity = improvement_rate / max(n, 1)

        # Calculate meta-awareness (correlation between performance and self-adjustment)
        meta_awareness = self._calculate_meta_awareness(sorted_records)

        # Calculate optimization potential
        max_observed_lq = max(lq_values) if lq_values else 0
        current_lq = lq_values[-1] if lq_values else 0
        optimization_potential = max(0, (max_observed_lq - current_lq) / max(max_observed_lq, 0.01))

        # Determine RSI level
        rsi_level = self._determine_rsi_level(
            improvement_rate=improvement_rate,
            adaptation_score=adaptation_score,
            recursion_depth=recursion_depth,
            meta_awareness=meta_awareness,
        )

        return RSIMetrics(
            fsa_id=fsa_id,
            rsi_level=rsi_level,
            improvement_rate=improvement_rate,
            adaptation_score=adaptation_score,
            recursion_depth=recursion_depth,
            stability_index=stability_index,
            efficiency_gain=efficiency_gain,
            learning_velocity=learning_velocity,
            meta_awareness=meta_awareness,
            optimization_potential=optimization_potential,
        )

    def _calculate_exponential_improvement(self, values: List[float]) -> float:
        """Calculate exponential improvement rate."""
        if len(values) < 2:
            return 0.0

        # Use exponential regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        # Calculate slope
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalize to 0-1 range
        return min(max(slope * 10, -1.0), 1.0)

    def _calculate_adaptation_score(self, values: List[float]) -> float:
        """Calculate adaptation score based on variance reduction."""
        if len(values) < 4:
            return 0.5

        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        # Calculate variance for each half
        def variance(data: List[float]) -> float:
            if len(data) < 2:
                return 0.0
            mean = sum(data) / len(data)
            return sum((x - mean) ** 2 for x in data) / len(data)

        var1 = variance(first_half)
        var2 = variance(second_half)

        # Adaptation = variance reduction
        if var1 > 0:
            adaptation = 1 - (var2 / var1)
            return min(max(adaptation, 0.0), 1.0)

        return 0.5

    def _estimate_recursion_depth(self, records: List[SessionExecutionRecord]) -> int:
        """Estimate the depth of recursive self-improvement."""
        if len(records) < 5:
            return 0

        # Look for step changes in performance
        lq_values = [r.leverage_quotient for r in records]

        # Count significant improvements
        improvements = 0
        threshold = 0.1  # 10% improvement threshold

        for i in range(1, len(lq_values)):
            if lq_values[i-1] > 0:
                change = (lq_values[i] - lq_values[i-1]) / lq_values[i-1]
                if change > threshold:
                    improvements += 1

        # Recursion depth approximated by improvement cycles
        return min(improvements // 2, 5)

    def _calculate_stability(self, values: List[float]) -> float:
        """Calculate stability index (inverse of coefficient of variation)."""
        if len(values) < 2:
            return 1.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean

        # Stability = 1 - normalized CV
        return max(0.0, 1 - min(cv, 1.0))

    def _calculate_meta_awareness(self, records: List[SessionExecutionRecord]) -> float:
        """Calculate meta-awareness score."""
        if len(records) < 5:
            return 0.5

        # Check if FSA improves after failures
        improvements_after_failure = 0
        failure_count = 0

        for i in range(1, len(records)):
            if records[i-1].status in ["failed", "error"]:
                failure_count += 1
                if records[i].leverage_quotient > records[i-1].leverage_quotient:
                    improvements_after_failure += 1

        if failure_count > 0:
            return improvements_after_failure / failure_count

        return 0.5

    def _determine_rsi_level(
        self,
        improvement_rate: float,
        adaptation_score: float,
        recursion_depth: int,
        meta_awareness: float,
    ) -> RSILevel:
        """Determine RSI level based on metrics."""
        score = (
            improvement_rate * 0.3 +
            adaptation_score * 0.25 +
            (recursion_depth / 5) * 0.25 +
            meta_awareness * 0.2
        )

        if recursion_depth >= 3 and score > 0.7:
            return RSILevel.RECURSIVE
        elif score > 0.6:
            return RSILevel.ADVANCED
        elif score > 0.4:
            return RSILevel.INTERMEDIATE
        elif score > 0.2:
            return RSILevel.BASIC
        else:
            return RSILevel.NONE

    # ========================================================================
    # Insight Generation
    # ========================================================================

    def generate_insights(self) -> List[RSIInsight]:
        """
        Generate meta-RSI recommendations for framework optimization.

        Returns:
            List of actionable insights
        """
        logger.info("Generating optimization insights")
        self._insights.clear()

        # Insight from patterns
        self._generate_pattern_insights()

        # Insight from RSI metrics
        self._generate_rsi_insights()

        # Insight from session analysis
        self._generate_session_insights()

        # Sort by priority
        self._insights.sort(key=lambda x: x.priority)

        # Notify hooks
        for insight in self._insights:
            for hook in self.hooks:
                hook.on_insight_generated(insight)

            if self._streaming:
                self._streaming.emit(
                    StreamEventType.INSIGHT_GENERATED,
                    insight.to_dict(),
                    f"Insight: {insight.title}",
                )

        logger.info(f"Generated {len(self._insights)} insights")
        return self._insights

    def _generate_pattern_insights(self) -> None:
        """Generate insights from detected patterns."""
        # Failure patterns -> high priority
        failure_patterns = [p for p in self._patterns if p.pattern_type == PatternType.FAILURE]
        if failure_patterns:
            affected_fsas = set()
            for p in failure_patterns:
                affected_fsas.update(p.fsa_ids_involved)

            self._insights.append(RSIInsight(
                insight_id=f"insight_failure_{len(self._insights)}",
                category="reliability",
                title="Cascading Failure Risk Detected",
                description=f"Multiple FSAs show correlated failures, indicating potential cascading failure risk or shared dependencies",
                priority=1,
                affected_fsas=list(affected_fsas),
                recommended_actions=[
                    "Investigate shared dependencies between affected FSAs",
                    "Implement circuit breaker patterns",
                    "Add isolation boundaries between correlated FSAs",
                    "Review error handling and recovery mechanisms",
                ],
                expected_improvement=0.25,
                confidence=0.85,
            ))

        # Optimization patterns -> medium priority
        opt_patterns = [p for p in self._patterns if p.pattern_type == PatternType.OPTIMIZATION]
        if opt_patterns:
            optimizing_fsas = [p.fsa_ids_involved[0] for p in opt_patterns]

            self._insights.append(RSIInsight(
                insight_id=f"insight_opt_{len(self._insights)}",
                category="optimization",
                title="Self-Optimizing FSAs Identified",
                description=f"Some FSAs demonstrate self-optimization behavior - their patterns can be applied to others",
                priority=3,
                affected_fsas=optimizing_fsas,
                recommended_actions=[
                    "Analyze optimization patterns from high-performers",
                    "Extract and document successful strategies",
                    "Apply learned patterns to underperforming FSAs",
                    "Consider implementing adaptive learning across framework",
                ],
                expected_improvement=0.15,
                confidence=0.75,
            ))

        # Performance clustering -> low priority
        perf_patterns = [p for p in self._patterns if p.pattern_type == PatternType.PERFORMANCE]
        low_perf = [p for p in perf_patterns if "under-performing" in p.description.lower()]
        if low_perf:
            affected = set()
            for p in low_perf:
                affected.update(p.fsa_ids_involved)

            self._insights.append(RSIInsight(
                insight_id=f"insight_perf_{len(self._insights)}",
                category="performance",
                title="Performance Improvement Opportunity",
                description=f"A cluster of {len(affected)} FSAs shows below-average performance",
                priority=4,
                affected_fsas=list(affected),
                recommended_actions=[
                    "Review configuration of underperforming FSAs",
                    "Compare with high-performing FSAs for differences",
                    "Consider resource allocation adjustments",
                    "Profile and optimize hot paths",
                ],
                expected_improvement=0.20,
                confidence=0.70,
            ))

    def _generate_rsi_insights(self) -> None:
        """Generate insights from RSI metrics."""
        if not self._rsi_metrics:
            return

        # Find FSAs with highest RSI potential
        high_potential = [
            (fsa_id, m) for fsa_id, m in self._rsi_metrics.items()
            if m.optimization_potential > 0.3
        ]

        if high_potential:
            fsas = [fsa_id for fsa_id, _ in high_potential]
            avg_potential = sum(m.optimization_potential for _, m in high_potential) / len(high_potential)

            self._insights.append(RSIInsight(
                insight_id=f"insight_rsi_potential_{len(self._insights)}",
                category="rsi",
                title="High Optimization Potential Detected",
                description=f"{len(fsas)} FSAs have significant optimization potential based on RSI analysis",
                priority=2,
                affected_fsas=fsas,
                recommended_actions=[
                    "Focus optimization efforts on high-potential FSAs",
                    "Implement feedback loops for continuous improvement",
                    "Enable adaptive parameter tuning",
                    "Consider meta-learning approaches",
                ],
                expected_improvement=avg_potential,
                confidence=0.80,
            ))

        # Find FSAs with recursive improvement capability
        recursive_fsas = [
            fsa_id for fsa_id, m in self._rsi_metrics.items()
            if m.rsi_level == RSILevel.RECURSIVE
        ]

        if recursive_fsas:
            self._insights.append(RSIInsight(
                insight_id=f"insight_rsi_recursive_{len(self._insights)}",
                category="rsi",
                title="Recursive Self-Improvement Capability",
                description=f"{len(recursive_fsas)} FSAs demonstrate true recursive self-improvement",
                priority=3,
                affected_fsas=recursive_fsas,
                recommended_actions=[
                    "Study and document recursive improvement mechanisms",
                    "Ensure safeguards against runaway optimization",
                    "Consider applying patterns to other FSAs",
                    "Monitor for stability issues",
                ],
                expected_improvement=0.30,
                confidence=0.75,
            ))

    def _generate_session_insights(self) -> None:
        """Generate insights from session analysis."""
        if not self._sessions:
            return

        # Analyze session patterns
        session_list = list(self._sessions.values())

        # Find sessions with unusually high failure rates
        avg_success_rate = sum(
            s.successful_executions / max(s.total_executions, 1)
            for s in session_list
        ) / max(len(session_list), 1)

        problem_sessions = [
            s for s in session_list
            if s.total_executions > 5 and
            (s.successful_executions / s.total_executions) < avg_success_rate * 0.7
        ]

        if problem_sessions:
            affected_fsas = set()
            for s in problem_sessions:
                affected_fsas.update(s.fsa_ids)

            self._insights.append(RSIInsight(
                insight_id=f"insight_session_{len(self._insights)}",
                category="reliability",
                title="Problematic Sessions Identified",
                description=f"{len(problem_sessions)} sessions show significantly below-average success rates",
                priority=2,
                affected_fsas=list(affected_fsas),
                recommended_actions=[
                    "Investigate common factors in problematic sessions",
                    "Check for environmental or configuration issues",
                    "Review input patterns that lead to failures",
                    "Implement session-level monitoring alerts",
                ],
                expected_improvement=0.15,
                confidence=0.70,
            ))

    # ========================================================================
    # Dashboard Data
    # ========================================================================

    def dashboard_data(self) -> DashboardData:
        """
        Generate JSON output for RSI visualization dashboard.

        Returns:
            DashboardData with all aggregated metrics and insights
        """
        logger.info("Generating dashboard data")

        # Calculate summary metrics
        total_executions = sum(s.total_executions for s in self._sessions.values())
        successful = sum(s.successful_executions for s in self._sessions.values())
        all_fsas = set()
        for s in self._sessions.values():
            all_fsas.update(s.fsa_ids)

        overall_success_rate = successful / max(total_executions, 1)

        # Calculate average RSI level
        rsi_level_values = {
            RSILevel.NONE: 0,
            RSILevel.BASIC: 1,
            RSILevel.INTERMEDIATE: 2,
            RSILevel.ADVANCED: 3,
            RSILevel.RECURSIVE: 4,
        }

        if self._rsi_metrics:
            avg_rsi = sum(
                rsi_level_values[m.rsi_level] for m in self._rsi_metrics.values()
            ) / len(self._rsi_metrics)
        else:
            avg_rsi = 0.0

        # Session summaries
        session_summaries = [
            {
                "session_id": s.session_id,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "total_executions": s.total_executions,
                "success_rate": round(s.successful_executions / max(s.total_executions, 1), 4),
                "average_lq": s.average_lq,
                "fsa_count": len(s.fsa_ids),
            }
            for s in self._sessions.values()
        ]

        # FSA performance summary
        fsa_performance: Dict[str, Dict[str, Any]] = {}
        for record in self._all_records:
            if record.fsa_id not in fsa_performance:
                fsa_performance[record.fsa_id] = {
                    "total_executions": 0,
                    "successful": 0,
                    "total_tokens": 0,
                    "lq_values": [],
                }
            fsa_performance[record.fsa_id]["total_executions"] += 1
            if record.status in ["success", "completed"]:
                fsa_performance[record.fsa_id]["successful"] += 1
            fsa_performance[record.fsa_id]["total_tokens"] += record.tokens_used
            fsa_performance[record.fsa_id]["lq_values"].append(record.leverage_quotient)

        # Finalize FSA performance
        for fsa_id, perf in fsa_performance.items():
            perf["success_rate"] = round(perf["successful"] / max(perf["total_executions"], 1), 4)
            perf["average_lq"] = round(sum(perf["lq_values"]) / max(len(perf["lq_values"]), 1), 4)
            del perf["lq_values"]  # Remove raw data

        # Time series data
        time_series = self._generate_time_series()

        return DashboardData(
            generated_at=datetime.now(),
            total_sessions=len(self._sessions),
            total_executions=total_executions,
            total_fsas=len(all_fsas),
            overall_success_rate=overall_success_rate,
            average_rsi_level=avg_rsi,
            patterns_detected=len(self._patterns),
            insights_generated=len(self._insights),
            session_summaries=session_summaries,
            fsa_performance=fsa_performance,
            rsi_metrics=[m.to_dict() for m in self._rsi_metrics.values()],
            patterns=[p.to_dict() for p in self._patterns],
            insights=[i.to_dict() for i in self._insights],
            time_series=time_series,
        )

    def _generate_time_series(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate time series data for visualization."""
        if not self._all_records:
            return {"lq": [], "executions": [], "success_rate": []}

        # Sort records by time
        sorted_records = sorted(self._all_records, key=lambda r: r.timestamp)

        # Group by hour
        hourly_data: Dict[str, Dict[str, Any]] = {}

        for record in sorted_records:
            hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")

            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "timestamp": hour_key,
                    "executions": 0,
                    "successful": 0,
                    "lq_sum": 0.0,
                }

            hourly_data[hour_key]["executions"] += 1
            if record.status in ["success", "completed"]:
                hourly_data[hour_key]["successful"] += 1
            hourly_data[hour_key]["lq_sum"] += record.leverage_quotient

        # Convert to time series lists
        lq_series = []
        exec_series = []
        sr_series = []

        for hour_key in sorted(hourly_data.keys()):
            data = hourly_data[hour_key]
            avg_lq = data["lq_sum"] / max(data["executions"], 1)
            sr = data["successful"] / max(data["executions"], 1)

            lq_series.append({"timestamp": hour_key, "value": round(avg_lq, 4)})
            exec_series.append({"timestamp": hour_key, "value": data["executions"]})
            sr_series.append({"timestamp": hour_key, "value": round(sr, 4)})

        return {
            "lq": lq_series,
            "executions": exec_series,
            "success_rate": sr_series,
        }

    def export_dashboard(self, output_path: str) -> bool:
        """
        Export dashboard data using ConvertTo-Json piping.

        Args:
            output_path: Path for output file

        Returns:
            True if successful
        """
        dashboard = self.dashboard_data()
        return self.ps_ops.export_with_convertto_json(
            data=dashboard.to_dict(),
            output_path=output_path,
        )

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    def run_full_analysis(
        self,
        patterns: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
    ) -> DashboardData:
        """
        Run complete analysis pipeline.

        Args:
            patterns: File patterns to search for
            max_depth: Maximum directory recursion depth

        Returns:
            DashboardData with complete analysis results
        """
        logger.info("Starting full RSI analysis pipeline")

        # Step 1: Aggregate sessions
        self.aggregate_sessions(patterns=patterns, max_depth=max_depth)

        # Step 2: Identify patterns
        self.identify_patterns()

        # Step 3: Calculate RSI metrics
        self.calculate_rsi_metrics()

        # Step 4: Generate insights
        self.generate_insights()

        # Step 5: Generate dashboard
        dashboard = self.dashboard_data()

        # Emit completion event
        if self._streaming:
            self._streaming.emit(
                StreamEventType.COMPLETE,
                {"sessions": len(self._sessions), "insights": len(self._insights)},
                "Analysis complete",
            )

        logger.info("Full analysis pipeline complete")
        return dashboard

    def get_streaming_aggregator(self) -> Optional[StreamingAggregator]:
        """Get the streaming aggregator for external subscription."""
        return self._streaming


# ============================================================================
# CLI Interface
# ============================================================================

def create_cli_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fsa_rsi_data_aggregator",
        description="Multi-session FSA execution data aggregator with RSI metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate data from current directory
  python -m agno.agent.fsa3_rsi_data_aggregator

  # Aggregate from multiple directories
  python -m agno.agent.fsa3_rsi_data_aggregator -d ./logs ./archive ./data

  # Export dashboard JSON
  python -m agno.agent.fsa3_rsi_data_aggregator -d ./logs -o dashboard.json

  # Run with streaming enabled
  python -m agno.agent.fsa3_rsi_data_aggregator -d ./logs --stream

  # Verbose output
  python -m agno.agent.fsa3_rsi_data_aggregator -d ./logs -v
        """,
    )

    parser.add_argument(
        "-d", "--directories",
        type=str,
        nargs="+",
        default=["."],
        help="Directories containing FSA execution data (default: current directory)",
    )

    parser.add_argument(
        "-p", "--patterns",
        type=str,
        nargs="+",
        default=["*.json", "*.log"],
        help="File patterns to search for (default: *.json *.log)",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum directory recursion depth (default: unlimited)",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path for dashboard JSON",
    )

    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable real-time streaming output",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence threshold for patterns (default: 0.6)",
    )

    parser.add_argument(
        "--show-patterns",
        action="store_true",
        help="Display detected patterns",
    )

    parser.add_argument(
        "--show-insights",
        action="store_true",
        help="Display generated insights",
    )

    parser.add_argument(
        "--show-rsi",
        action="store_true",
        help="Display RSI metrics",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug output",
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {FSARSIDataAggregator.VERSION}",
    )

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_cli_parser()
    parsed = parser.parse_args(args)

    # Configure logging level
    if parsed.verbose:
        logger.setLevel(logging.DEBUG)
    elif parsed.quiet:
        logger.setLevel(logging.WARNING)

    try:
        # Initialize aggregator
        aggregator = FSARSIDataAggregator(
            data_directories=parsed.directories,
            enable_streaming=parsed.stream,
        )

        if not parsed.quiet:
            logger.info(f"FSA RSI Data Aggregator v{FSARSIDataAggregator.VERSION}")
            logger.info(f"Analyzing directories: {parsed.directories}")

        # Run full analysis
        dashboard = aggregator.run_full_analysis(
            patterns=parsed.patterns,
            max_depth=parsed.max_depth,
        )

        # Display results
        if not parsed.quiet:
            print("\n" + "=" * 70)
            print("FSA RSI DATA AGGREGATION RESULTS")
            print("=" * 70)

            summary = dashboard.to_dict()["summary"]
            print(f"\nSummary:")
            print(f"  Sessions: {summary['total_sessions']}")
            print(f"  Executions: {summary['total_executions']}")
            print(f"  FSAs: {summary['total_fsas']}")
            print(f"  Success Rate: {summary['overall_success_rate']:.1%}")
            print(f"  Avg RSI Level: {summary['average_rsi_level']:.2f}/4")
            print(f"  Patterns: {summary['patterns_detected']}")
            print(f"  Insights: {summary['insights_generated']}")

            # Show patterns if requested
            if parsed.show_patterns and dashboard.patterns:
                print(f"\nDetected Patterns:")
                print("-" * 50)
                for p in dashboard.patterns[:10]:
                    print(f"  [{p['pattern_type']}] {p['description']}")
                    print(f"    FSAs: {', '.join(p['fsa_ids_involved'])}")
                    print(f"    Confidence: {p['confidence']:.1%}")

            # Show insights if requested
            if parsed.show_insights and dashboard.insights:
                print(f"\nGenerated Insights:")
                print("-" * 50)
                for i in dashboard.insights:
                    print(f"  [P{i['priority']}] {i['title']}")
                    print(f"    {i['description']}")
                    print(f"    Expected Improvement: {i['expected_improvement']:.1%}")

            # Show RSI metrics if requested
            if parsed.show_rsi and dashboard.rsi_metrics:
                print(f"\nRSI Metrics:")
                print("-" * 50)
                for m in sorted(dashboard.rsi_metrics, key=lambda x: x['improvement_rate'], reverse=True)[:10]:
                    print(f"  {m['fsa_id']}: {m['rsi_level']} (improvement={m['improvement_rate']:.4f})")

        # Export if output specified
        if parsed.output:
            success = aggregator.export_dashboard(parsed.output)
            if success:
                logger.info(f"Dashboard exported to: {parsed.output}")
            else:
                logger.error(f"Failed to export dashboard to: {parsed.output}")
                return 1

        return 0

    except PowerShellOperationError as e:
        logger.error(f"PowerShell error: {e}")
        return 2
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

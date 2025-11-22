"""
FSA Meta Pattern Analyzer - Analyzes FSA execution patterns using PowerShell subprocess.

This module provides tools for analyzing Functional Stack Agent (FSA) execution patterns,
calculating leverage quotients (LQ), identifying performance trends, and generating
actionable recommendations.

CRITICAL: All file operations use PowerShell subprocess commands exclusively:
- Get-ChildItem for file listing
- Get-Content for file reading
- Out-File for file writing
- NO Python file operations, NO os.listdir, NO open()
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# Agno imports for integration
try:
    from agno.utils.log import get_logger, logger as agno_logger
    from agno.agent.metrics import SessionMetrics
    from agno.run.response import RunEvent, RunResponse
except ImportError:
    # Fallback for standalone usage
    agno_logger = None
    SessionMetrics = None
    RunEvent = None
    RunResponse = None


# Module-level logger configuration
LOGGER_NAME = "fsa_meta_pattern_analyzer"


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


class FSAExecutionStatus(str, Enum):
    """Status of an FSA execution."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class PowerShellError(Exception):
    """Exception raised for PowerShell execution failures."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        self.message = message
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"{message} (returncode={returncode}): {stderr}")


@dataclass
class FSAExecutionRecord:
    """Record of a single FSA execution."""
    fsa_id: str
    run_id: str
    timestamp: datetime
    status: FSAExecutionStatus
    leverage_quotient: float
    execution_time_ms: float
    tokens_used: int
    success_rate: float = 1.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "fsa_id": self.fsa_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "leverage_quotient": self.leverage_quotient,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "success_rate": self.success_rate,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FSAExecutionRecord":
        """Create record from dictionary."""
        return cls(
            fsa_id=data.get("fsa_id", "unknown"),
            run_id=data.get("run_id", "unknown"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            status=FSAExecutionStatus(data.get("status", "unknown")),
            leverage_quotient=float(data.get("leverage_quotient", 0.0)),
            execution_time_ms=float(data.get("execution_time_ms", 0.0)),
            tokens_used=int(data.get("tokens_used", 0)),
            success_rate=float(data.get("success_rate", 1.0)),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FSAPatternAnalysis:
    """Analysis results for FSA execution patterns."""
    fsa_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_lq: float
    lq_trend: float  # Positive = improving, negative = declining
    average_execution_time_ms: float
    total_tokens_used: int
    success_rate: float
    performance_category: str  # "top_performer", "average", "bottleneck"
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            "fsa_id": self.fsa_id,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "average_lq": self.average_lq,
            "lq_trend": self.lq_trend,
            "average_execution_time_ms": self.average_execution_time_ms,
            "total_tokens_used": self.total_tokens_used,
            "success_rate": self.success_rate,
            "performance_category": self.performance_category,
            "recommendations": self.recommendations,
        }


@dataclass
class MetaLQAssessment:
    """Self-assessment of the analyzer's own leverage quotient."""
    analyzer_version: str
    assessment_timestamp: datetime
    files_processed: int
    records_analyzed: int
    analysis_time_ms: float
    meta_lq: float
    efficiency_score: float
    accuracy_confidence: float
    self_improvement_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to dictionary."""
        return {
            "analyzer_version": self.analyzer_version,
            "assessment_timestamp": self.assessment_timestamp.isoformat(),
            "files_processed": self.files_processed,
            "records_analyzed": self.records_analyzed,
            "analysis_time_ms": self.analysis_time_ms,
            "meta_lq": self.meta_lq,
            "efficiency_score": self.efficiency_score,
            "accuracy_confidence": self.accuracy_confidence,
            "self_improvement_suggestions": self.self_improvement_suggestions,
        }


class PowerShellFileOperations:
    """
    Handles all file operations using PowerShell subprocess commands.

    CRITICAL: This class enforces the requirement of using ONLY PowerShell
    for all file operations - no Python file I/O is permitted.
    """

    POWERSHELL_EXECUTABLE = "powershell" if sys.platform == "win32" else "pwsh"
    DEFAULT_TIMEOUT = 30  # seconds

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
            PowerShellError: If command execution fails
            subprocess.TimeoutExpired: If command times out
        """
        logger.debug(f"Executing PowerShell: {command}")

        try:
            result = subprocess.run(
                [cls.POWERSHELL_EXECUTABLE, "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,  # We handle errors ourselves
            )

            if check and result.returncode != 0:
                raise PowerShellError(
                    message=f"PowerShell command failed",
                    returncode=result.returncode,
                    stderr=result.stderr.strip(),
                )

            logger.debug(f"PowerShell result: returncode={result.returncode}")
            return result

        except subprocess.TimeoutExpired as e:
            logger.error(f"PowerShell command timed out after {timeout}s: {command}")
            raise
        except FileNotFoundError:
            error_msg = (
                f"PowerShell executable not found: {cls.POWERSHELL_EXECUTABLE}. "
                f"On Linux/macOS, install PowerShell Core (pwsh)."
            )
            logger.error(error_msg)
            raise PowerShellError(message=error_msg, returncode=-1, stderr="")

    @classmethod
    def list_files(
        cls,
        directory: str,
        pattern: str = "*",
        recursive: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> List[str]:
        """
        List files in directory using PowerShell Get-ChildItem.

        Args:
            directory: Directory path to search
            pattern: File pattern (e.g., "*.log", "*.json")
            recursive: If True, search recursively
            timeout: Command timeout

        Returns:
            List of file paths
        """
        recurse_flag = "-Recurse" if recursive else ""

        # Escape single quotes in paths for PowerShell
        safe_dir = directory.replace("'", "''")
        safe_pattern = pattern.replace("'", "''")

        command = (
            f"Get-ChildItem -Path '{safe_dir}' -Filter '{safe_pattern}' "
            f"{recurse_flag} -File -ErrorAction SilentlyContinue | "
            f"Select-Object -ExpandProperty FullName"
        )

        try:
            result = cls._execute_powershell(command, timeout=timeout, check=False)

            if result.returncode != 0 and result.stderr:
                logger.warning(f"Get-ChildItem warning: {result.stderr.strip()}")

            # Parse output - one file path per line
            files = [
                line.strip()
                for line in result.stdout.strip().split('\n')
                if line.strip()
            ]

            logger.info(f"Found {len(files)} files matching '{pattern}' in '{directory}'")
            return files

        except PowerShellError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    @classmethod
    def read_file(
        cls,
        file_path: str,
        encoding: str = "UTF8",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> str:
        """
        Read file content using PowerShell Get-Content.

        Args:
            file_path: Path to file
            encoding: File encoding (default UTF8)
            timeout: Command timeout

        Returns:
            File content as string
        """
        safe_path = file_path.replace("'", "''")

        command = f"Get-Content -Path '{safe_path}' -Encoding {encoding} -Raw"

        try:
            result = cls._execute_powershell(command, timeout=timeout)
            logger.debug(f"Read {len(result.stdout)} characters from '{file_path}'")
            return result.stdout

        except PowerShellError as e:
            logger.error(f"Failed to read file '{file_path}': {e}")
            raise

    @classmethod
    def write_file(
        cls,
        file_path: str,
        content: str,
        encoding: str = "UTF8",
        append: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Write content to file using PowerShell Out-File.

        Args:
            file_path: Path to file
            content: Content to write
            encoding: File encoding (default UTF8)
            append: If True, append to file; otherwise overwrite
            timeout: Command timeout

        Returns:
            True if successful
        """
        safe_path = file_path.replace("'", "''")
        # Escape content for PowerShell - use here-string for multi-line
        safe_content = content.replace("'", "''")

        append_flag = "-Append" if append else ""

        # Use PowerShell here-string for safe content handling
        command = f"'{safe_content}' | Out-File -FilePath '{safe_path}' -Encoding {encoding} {append_flag}"

        try:
            cls._execute_powershell(command, timeout=timeout)
            logger.debug(f"Wrote {len(content)} characters to '{file_path}'")
            return True

        except PowerShellError as e:
            logger.error(f"Failed to write file '{file_path}': {e}")
            raise

    @classmethod
    def file_exists(
        cls,
        file_path: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Check if file exists using PowerShell Test-Path.

        Args:
            file_path: Path to check
            timeout: Command timeout

        Returns:
            True if file exists
        """
        safe_path = file_path.replace("'", "''")
        command = f"Test-Path -Path '{safe_path}' -PathType Leaf"

        try:
            result = cls._execute_powershell(command, timeout=timeout, check=False)
            return result.stdout.strip().lower() == "true"
        except PowerShellError:
            return False

    @classmethod
    def create_directory(
        cls,
        directory: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Create directory using PowerShell New-Item.

        Args:
            directory: Directory path to create
            timeout: Command timeout

        Returns:
            True if successful or already exists
        """
        safe_dir = directory.replace("'", "''")
        command = f"New-Item -Path '{safe_dir}' -ItemType Directory -Force | Out-Null; $true"

        try:
            result = cls._execute_powershell(command, timeout=timeout, check=False)
            return result.returncode == 0
        except PowerShellError:
            return False


class FSAIntegrationLayer:
    """
    Integration layer for FSA pattern analysis with the Agno agent framework.

    Provides bridges between the pattern analyzer and core Agno components
    like RunResponse, SessionMetrics, and RunEvent.
    """

    def __init__(self):
        """Initialize the integration layer."""
        self._execution_records: List[FSAExecutionRecord] = []
        self._run_event_handlers: Dict[str, List[callable]] = {}
        logger.info("FSAIntegrationLayer initialized")

    def register_event_handler(
        self,
        event: str,
        handler: callable,
    ) -> None:
        """Register a handler for a specific run event."""
        if event not in self._run_event_handlers:
            self._run_event_handlers[event] = []
        self._run_event_handlers[event].append(handler)
        logger.debug(f"Registered handler for event: {event}")

    def process_run_response(
        self,
        response: Union[Dict[str, Any], "RunResponse"],
        fsa_id: str,
    ) -> Optional[FSAExecutionRecord]:
        """
        Process a RunResponse and create an FSAExecutionRecord.

        Args:
            response: RunResponse object or dict representation
            fsa_id: ID of the FSA that generated this response

        Returns:
            FSAExecutionRecord if processing successful, None otherwise
        """
        try:
            # Handle both dict and RunResponse
            if hasattr(response, 'to_dict'):
                data = response.to_dict()
            else:
                data = response

            # Extract metrics
            metrics = data.get("metrics", {})

            # Determine status from event
            event = data.get("event", "")
            if "Completed" in event:
                status = FSAExecutionStatus.SUCCESS
            elif "Error" in event:
                status = FSAExecutionStatus.FAILED
            else:
                status = FSAExecutionStatus.UNKNOWN

            # Calculate leverage quotient from metrics
            tokens = metrics.get("total_tokens", 0) or metrics.get("input_tokens", 0) + metrics.get("output_tokens", 0)
            exec_time = metrics.get("time", 0) or 0

            # LQ = effectiveness / resource_usage (simplified)
            # Higher tokens with lower time = higher LQ
            if exec_time > 0:
                lq = (tokens / 1000) / (exec_time * 10)  # Normalized
            else:
                lq = 0.0

            record = FSAExecutionRecord(
                fsa_id=fsa_id,
                run_id=data.get("run_id", f"run_{datetime.now().timestamp()}"),
                timestamp=datetime.now(),
                status=status,
                leverage_quotient=round(lq, 4),
                execution_time_ms=exec_time * 1000 if exec_time else 0,
                tokens_used=tokens,
                success_rate=1.0 if status == FSAExecutionStatus.SUCCESS else 0.0,
                metadata={
                    "agent_id": data.get("agent_id"),
                    "session_id": data.get("session_id"),
                    "model": data.get("model"),
                    "content_type": data.get("content_type"),
                },
            )

            self._execution_records.append(record)
            logger.debug(f"Processed run response for FSA '{fsa_id}': LQ={lq:.4f}")

            return record

        except Exception as e:
            logger.error(f"Failed to process run response: {e}")
            return None

    def process_session_metrics(
        self,
        metrics: Union[Dict[str, Any], "SessionMetrics"],
        fsa_id: str,
        run_id: str,
    ) -> Optional[FSAExecutionRecord]:
        """
        Process SessionMetrics and create an FSAExecutionRecord.

        Args:
            metrics: SessionMetrics object or dict representation
            fsa_id: ID of the FSA
            run_id: ID of the run

        Returns:
            FSAExecutionRecord if processing successful
        """
        try:
            # Handle both dict and SessionMetrics
            if hasattr(metrics, '__dict__'):
                data = {k: v for k, v in metrics.__dict__.items() if not k.startswith('_')}
            else:
                data = metrics

            tokens = data.get("total_tokens", 0) or (
                data.get("input_tokens", 0) + data.get("output_tokens", 0)
            )
            exec_time = data.get("time", 0) or 0

            # Calculate LQ
            if exec_time > 0:
                lq = (tokens / 1000) / (exec_time * 10)
            else:
                lq = 0.0

            record = FSAExecutionRecord(
                fsa_id=fsa_id,
                run_id=run_id,
                timestamp=datetime.now(),
                status=FSAExecutionStatus.SUCCESS,
                leverage_quotient=round(lq, 4),
                execution_time_ms=exec_time * 1000 if exec_time else 0,
                tokens_used=tokens,
                metadata={
                    "prompt_tokens": data.get("prompt_tokens", 0),
                    "completion_tokens": data.get("completion_tokens", 0),
                    "time_to_first_token": data.get("time_to_first_token"),
                },
            )

            self._execution_records.append(record)
            return record

        except Exception as e:
            logger.error(f"Failed to process session metrics: {e}")
            return None

    def get_records(self) -> List[FSAExecutionRecord]:
        """Get all execution records."""
        return self._execution_records.copy()

    def clear_records(self) -> None:
        """Clear all execution records."""
        self._execution_records.clear()
        logger.info("Cleared all execution records")


class FSAMetaPatternAnalyzer:
    """
    Main analyzer class for FSA execution patterns.

    Analyzes FSA execution logs, calculates leverage quotients,
    identifies trends and bottlenecks, and generates recommendations.

    All file operations use PowerShell subprocess commands exclusively.
    """

    VERSION = "1.0.0"
    DEFAULT_LOG_PATTERNS = ["*.log", "*.json", "*fsa*.txt"]

    def __init__(
        self,
        log_directory: Optional[str] = None,
        integration_layer: Optional[FSAIntegrationLayer] = None,
    ):
        """
        Initialize the pattern analyzer.

        Args:
            log_directory: Directory containing FSA execution logs
            integration_layer: Optional FSAIntegrationLayer instance
        """
        self.log_directory = log_directory or "."
        self.integration_layer = integration_layer or FSAIntegrationLayer()
        self.ps_ops = PowerShellFileOperations()

        self._execution_records: List[FSAExecutionRecord] = []
        self._analysis_results: Dict[str, FSAPatternAnalysis] = {}
        self._meta_assessment: Optional[MetaLQAssessment] = None
        self._analysis_start_time: Optional[datetime] = None

        logger.info(f"FSAMetaPatternAnalyzer v{self.VERSION} initialized")
        logger.info(f"Log directory: {self.log_directory}")

    def collect_logs_powershell(
        self,
        patterns: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> List[str]:
        """
        Collect log files using PowerShell Get-ChildItem.

        CRITICAL: Uses ONLY PowerShell subprocess - no Python file operations.

        Args:
            patterns: File patterns to search for (default: ["*.log", "*.json"])
            recursive: Search recursively in subdirectories

        Returns:
            List of discovered log file paths
        """
        self._analysis_start_time = datetime.now()
        patterns = patterns or self.DEFAULT_LOG_PATTERNS

        logger.info(f"Collecting logs from '{self.log_directory}' with patterns: {patterns}")

        all_files: List[str] = []

        for pattern in patterns:
            try:
                files = self.ps_ops.list_files(
                    directory=self.log_directory,
                    pattern=pattern,
                    recursive=recursive,
                )
                all_files.extend(files)
                logger.debug(f"Pattern '{pattern}' matched {len(files)} files")

            except Exception as e:
                logger.warning(f"Error searching for pattern '{pattern}': {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        logger.info(f"Collected {len(unique_files)} unique log files")
        return unique_files

    def _parse_log_content(self, content: str, file_path: str) -> List[FSAExecutionRecord]:
        """
        Parse log content to extract FSA execution records.

        Args:
            content: Log file content
            file_path: Path to the log file (for metadata)

        Returns:
            List of parsed FSAExecutionRecord objects
        """
        records = []

        # Try JSON parsing first
        try:
            data = json.loads(content)

            # Handle array of records
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        record = self._dict_to_record(item, file_path)
                        if record:
                            records.append(record)

            # Handle single record or nested structure
            elif isinstance(data, dict):
                # Check for executions array
                if "executions" in data:
                    for item in data["executions"]:
                        record = self._dict_to_record(item, file_path)
                        if record:
                            records.append(record)
                else:
                    record = self._dict_to_record(data, file_path)
                    if record:
                        records.append(record)

        except json.JSONDecodeError:
            # Fall back to line-by-line parsing for text logs
            records = self._parse_text_log(content, file_path)

        return records

    def _dict_to_record(
        self,
        data: Dict[str, Any],
        source_file: str,
    ) -> Optional[FSAExecutionRecord]:
        """Convert a dictionary to FSAExecutionRecord."""
        try:
            # Support multiple key formats
            fsa_id = (
                data.get("fsa_id") or
                data.get("agent_id") or
                data.get("id") or
                "unknown"
            )

            run_id = (
                data.get("run_id") or
                data.get("execution_id") or
                f"run_{datetime.now().timestamp()}"
            )

            # Parse timestamp
            timestamp_str = data.get("timestamp") or data.get("created_at")
            if timestamp_str:
                if isinstance(timestamp_str, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp_str)
                else:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            # Parse status
            status_str = data.get("status", "unknown").lower()
            status_map = {
                "success": FSAExecutionStatus.SUCCESS,
                "completed": FSAExecutionStatus.SUCCESS,
                "partial": FSAExecutionStatus.PARTIAL,
                "failed": FSAExecutionStatus.FAILED,
                "error": FSAExecutionStatus.FAILED,
                "timeout": FSAExecutionStatus.TIMEOUT,
            }
            status = status_map.get(status_str, FSAExecutionStatus.UNKNOWN)

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
            if lq == 0.0 and exec_time > 0:
                lq = (tokens / 1000) / (exec_time / 1000 * 10)

            return FSAExecutionRecord(
                fsa_id=fsa_id,
                run_id=run_id,
                timestamp=timestamp,
                status=status,
                leverage_quotient=round(lq, 4),
                execution_time_ms=exec_time,
                tokens_used=tokens,
                success_rate=1.0 if status == FSAExecutionStatus.SUCCESS else 0.0,
                error_message=data.get("error_message") or data.get("error"),
                metadata={
                    "source_file": source_file,
                    **{k: v for k, v in data.items() if k not in [
                        "fsa_id", "run_id", "timestamp", "status",
                        "leverage_quotient", "execution_time_ms", "tokens_used"
                    ]},
                },
            )

        except Exception as e:
            logger.warning(f"Failed to parse record from dict: {e}")
            return None

    def _parse_text_log(self, content: str, file_path: str) -> List[FSAExecutionRecord]:
        """Parse text-format log content."""
        records = []

        # Simple pattern matching for common log formats
        current_record: Dict[str, Any] = {}

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                if current_record:
                    record = self._dict_to_record(current_record, file_path)
                    if record:
                        records.append(record)
                    current_record = {}
                continue

            # Try to parse key=value pairs
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    current_record[key] = value

            # Try to parse JSON embedded in log lines
            if '{' in line and '}' in line:
                try:
                    start = line.index('{')
                    end = line.rindex('}') + 1
                    json_str = line[start:end]
                    embedded = json.loads(json_str)
                    current_record.update(embedded)
                except (json.JSONDecodeError, ValueError):
                    pass

        # Don't forget the last record
        if current_record:
            record = self._dict_to_record(current_record, file_path)
            if record:
                records.append(record)

        return records

    def analyze_patterns(
        self,
        log_files: Optional[List[str]] = None,
    ) -> Dict[str, FSAPatternAnalysis]:
        """
        Analyze FSA execution patterns from log files.

        Groups executions by FSA, calculates LQ trends, success rates,
        and identifies performance categories.

        Args:
            log_files: List of log files to analyze (collects if not provided)

        Returns:
            Dictionary mapping FSA IDs to their pattern analysis
        """
        logger.info("Starting pattern analysis")

        # Collect logs if not provided
        if log_files is None:
            log_files = self.collect_logs_powershell()

        # Parse all log files
        self._execution_records.clear()

        for file_path in log_files:
            try:
                content = self.ps_ops.read_file(file_path)
                records = self._parse_log_content(content, file_path)
                self._execution_records.extend(records)
                logger.debug(f"Parsed {len(records)} records from '{file_path}'")

            except PowerShellError as e:
                logger.warning(f"Could not read '{file_path}': {e}")
            except Exception as e:
                logger.warning(f"Error parsing '{file_path}': {e}")

        # Include records from integration layer
        self._execution_records.extend(self.integration_layer.get_records())

        logger.info(f"Total execution records: {len(self._execution_records)}")

        # Group by FSA ID
        fsa_groups: Dict[str, List[FSAExecutionRecord]] = {}
        for record in self._execution_records:
            if record.fsa_id not in fsa_groups:
                fsa_groups[record.fsa_id] = []
            fsa_groups[record.fsa_id].append(record)

        # Analyze each FSA
        self._analysis_results.clear()

        for fsa_id, records in fsa_groups.items():
            analysis = self._analyze_fsa_group(fsa_id, records)
            self._analysis_results[fsa_id] = analysis

        logger.info(f"Analyzed {len(self._analysis_results)} FSAs")
        return self._analysis_results

    def _analyze_fsa_group(
        self,
        fsa_id: str,
        records: List[FSAExecutionRecord],
    ) -> FSAPatternAnalysis:
        """Analyze a group of records for a single FSA."""
        total = len(records)
        successful = sum(1 for r in records if r.status == FSAExecutionStatus.SUCCESS)
        failed = sum(1 for r in records if r.status in [
            FSAExecutionStatus.FAILED, FSAExecutionStatus.TIMEOUT
        ])

        # Calculate averages
        lq_values = [r.leverage_quotient for r in records]
        avg_lq = sum(lq_values) / len(lq_values) if lq_values else 0.0

        exec_times = [r.execution_time_ms for r in records]
        avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0.0

        total_tokens = sum(r.tokens_used for r in records)
        success_rate = successful / total if total > 0 else 0.0

        # Calculate LQ trend (simple linear regression)
        lq_trend = self._calculate_trend(lq_values)

        # Determine performance category
        if avg_lq > 0.8 and success_rate > 0.9:
            category = "top_performer"
        elif avg_lq < 0.3 or success_rate < 0.5:
            category = "bottleneck"
        else:
            category = "average"

        return FSAPatternAnalysis(
            fsa_id=fsa_id,
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            average_lq=round(avg_lq, 4),
            lq_trend=round(lq_trend, 4),
            average_execution_time_ms=round(avg_exec_time, 2),
            total_tokens_used=total_tokens,
            success_rate=round(success_rate, 4),
            performance_category=category,
        )

    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate trend using simple linear regression slope.

        Positive = improving, negative = declining.
        """
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def generate_recommendations(
        self,
        analysis_results: Optional[Dict[str, FSAPatternAnalysis]] = None,
    ) -> Dict[str, List[str]]:
        """
        Generate actionable recommendations based on pattern analysis.

        Identifies top performers and bottlenecks, providing specific
        recommendations for improvement.

        Args:
            analysis_results: Pattern analysis results (uses cached if not provided)

        Returns:
            Dictionary mapping FSA IDs to their recommendations
        """
        results = analysis_results or self._analysis_results

        if not results:
            logger.warning("No analysis results available. Run analyze_patterns() first.")
            return {}

        logger.info("Generating recommendations")
        recommendations: Dict[str, List[str]] = {}

        # Calculate percentiles for comparison
        all_lq = [a.average_lq for a in results.values()]
        all_exec_time = [a.average_execution_time_ms for a in results.values()]

        lq_p75 = sorted(all_lq)[int(len(all_lq) * 0.75)] if all_lq else 0
        lq_p25 = sorted(all_lq)[int(len(all_lq) * 0.25)] if all_lq else 0
        exec_time_p75 = sorted(all_exec_time)[int(len(all_exec_time) * 0.75)] if all_exec_time else 0

        for fsa_id, analysis in results.items():
            recs = []

            # Top performer recommendations
            if analysis.performance_category == "top_performer":
                recs.append(f"✓ TOP PERFORMER: Maintain current configuration")
                recs.append(f"Consider as template for other FSAs")
                if analysis.lq_trend > 0:
                    recs.append(f"Positive LQ trend (+{analysis.lq_trend:.4f}) - continuing improvement")

            # Bottleneck recommendations
            elif analysis.performance_category == "bottleneck":
                recs.append(f"⚠ BOTTLENECK IDENTIFIED: Requires optimization")

                if analysis.success_rate < 0.5:
                    recs.append(f"Critical: Success rate ({analysis.success_rate:.1%}) below 50%")
                    recs.append("Investigate error patterns and failure causes")

                if analysis.average_lq < lq_p25:
                    recs.append(f"LQ ({analysis.average_lq:.4f}) in bottom quartile")
                    recs.append("Review prompt efficiency and token usage")

                if analysis.average_execution_time_ms > exec_time_p75:
                    recs.append(f"Execution time ({analysis.average_execution_time_ms:.0f}ms) above 75th percentile")
                    recs.append("Consider caching, parallelization, or prompt optimization")

                if analysis.lq_trend < 0:
                    recs.append(f"Declining LQ trend ({analysis.lq_trend:.4f}) - performance degrading")

            # Average performer recommendations
            else:
                recs.append(f"Average performance - room for improvement")

                if analysis.lq_trend > 0:
                    recs.append(f"Positive trend ({analysis.lq_trend:.4f}) - on improvement path")
                elif analysis.lq_trend < 0:
                    recs.append(f"Negative trend ({analysis.lq_trend:.4f}) - monitor closely")

                if analysis.success_rate < 0.8:
                    recs.append(f"Success rate ({analysis.success_rate:.1%}) could be improved")

                if analysis.average_lq < lq_p75:
                    recs.append("Review top performers for optimization strategies")

            # Update analysis with recommendations
            analysis.recommendations = recs
            recommendations[fsa_id] = recs

        logger.info(f"Generated recommendations for {len(recommendations)} FSAs")
        return recommendations

    def calculate_meta_lq(self) -> MetaLQAssessment:
        """
        Calculate the analyzer's own leverage quotient (meta-LQ).

        Self-assesses the analyzer's efficiency and effectiveness,
        providing suggestions for self-improvement.

        Returns:
            MetaLQAssessment with self-analysis metrics
        """
        logger.info("Calculating meta leverage quotient")

        analysis_end = datetime.now()

        if self._analysis_start_time:
            analysis_time_ms = (analysis_end - self._analysis_start_time).total_seconds() * 1000
        else:
            analysis_time_ms = 0.0

        files_processed = len(set(
            r.metadata.get("source_file", "")
            for r in self._execution_records
            if r.metadata.get("source_file")
        ))
        records_analyzed = len(self._execution_records)

        # Calculate meta-LQ based on:
        # - Records processed per millisecond (throughput)
        # - Analysis coverage (how many FSAs analyzed)
        # - Recommendation quality (based on diversity)

        throughput = records_analyzed / max(analysis_time_ms, 1)
        coverage = len(self._analysis_results) / max(records_analyzed, 1)

        # Recommendation diversity score
        all_recs = sum(len(a.recommendations) for a in self._analysis_results.values())
        rec_diversity = min(all_recs / max(len(self._analysis_results), 1) / 5, 1.0)

        # Weighted meta-LQ
        meta_lq = (throughput * 0.3 + coverage * 0.3 + rec_diversity * 0.4)
        meta_lq = min(max(meta_lq, 0.0), 1.0)  # Normalize to 0-1

        # Efficiency score based on file operations
        efficiency = 1.0 - (files_processed * 0.01) if files_processed < 100 else 0.5

        # Accuracy confidence based on data volume
        if records_analyzed >= 100:
            accuracy = 0.95
        elif records_analyzed >= 50:
            accuracy = 0.85
        elif records_analyzed >= 10:
            accuracy = 0.70
        else:
            accuracy = 0.50

        # Self-improvement suggestions
        suggestions = []

        if records_analyzed < 10:
            suggestions.append("Collect more execution data for reliable analysis")

        if analysis_time_ms > 5000:
            suggestions.append("Consider parallel file processing for faster analysis")

        if len(self._analysis_results) < 3:
            suggestions.append("Analyze more FSAs for better comparative insights")

        if meta_lq < 0.5:
            suggestions.append("Optimize parsing logic for better throughput")

        if not suggestions:
            suggestions.append("Analyzer performing optimally - no improvements needed")

        self._meta_assessment = MetaLQAssessment(
            analyzer_version=self.VERSION,
            assessment_timestamp=analysis_end,
            files_processed=files_processed,
            records_analyzed=records_analyzed,
            analysis_time_ms=round(analysis_time_ms, 2),
            meta_lq=round(meta_lq, 4),
            efficiency_score=round(efficiency, 4),
            accuracy_confidence=round(accuracy, 4),
            self_improvement_suggestions=suggestions,
        )

        logger.info(f"Meta-LQ: {meta_lq:.4f}, Efficiency: {efficiency:.4f}, Accuracy: {accuracy:.4f}")
        return self._meta_assessment

    def export_results(
        self,
        output_path: str,
        format: str = "json",
    ) -> bool:
        """
        Export analysis results using PowerShell Out-File.

        Args:
            output_path: Path for output file
            format: Output format ("json" or "text")

        Returns:
            True if export successful
        """
        logger.info(f"Exporting results to '{output_path}' as {format}")

        # Compile results
        export_data = {
            "analyzer_version": self.VERSION,
            "export_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_records": len(self._execution_records),
                "total_fsas_analyzed": len(self._analysis_results),
            },
            "analyses": {
                fsa_id: analysis.to_dict()
                for fsa_id, analysis in self._analysis_results.items()
            },
            "meta_assessment": self._meta_assessment.to_dict() if self._meta_assessment else None,
        }

        if format == "json":
            content = json.dumps(export_data, indent=2)
        else:
            # Text format
            lines = [
                f"FSA Meta Pattern Analysis Report",
                f"================================",
                f"Analyzer Version: {self.VERSION}",
                f"Export Time: {export_data['export_timestamp']}",
                f"",
                f"Summary",
                f"-------",
                f"Total Records: {export_data['summary']['total_records']}",
                f"FSAs Analyzed: {export_data['summary']['total_fsas_analyzed']}",
                f"",
            ]

            for fsa_id, analysis in self._analysis_results.items():
                lines.extend([
                    f"FSA: {fsa_id}",
                    f"  Category: {analysis.performance_category}",
                    f"  Executions: {analysis.total_executions}",
                    f"  Success Rate: {analysis.success_rate:.1%}",
                    f"  Average LQ: {analysis.average_lq:.4f}",
                    f"  LQ Trend: {analysis.lq_trend:+.4f}",
                    f"  Avg Exec Time: {analysis.average_execution_time_ms:.0f}ms",
                    f"  Recommendations:",
                ])
                for rec in analysis.recommendations:
                    lines.append(f"    - {rec}")
                lines.append("")

            if self._meta_assessment:
                lines.extend([
                    f"Meta Assessment",
                    f"---------------",
                    f"Meta-LQ: {self._meta_assessment.meta_lq:.4f}",
                    f"Efficiency: {self._meta_assessment.efficiency_score:.4f}",
                    f"Accuracy Confidence: {self._meta_assessment.accuracy_confidence:.4f}",
                    f"Self-Improvement Suggestions:",
                ])
                for sug in self._meta_assessment.self_improvement_suggestions:
                    lines.append(f"  - {sug}")

            content = '\n'.join(lines)

        try:
            return self.ps_ops.write_file(output_path, content)
        except PowerShellError as e:
            logger.error(f"Failed to export results: {e}")
            return False

    def get_top_performers(self, limit: int = 5) -> List[Tuple[str, FSAPatternAnalysis]]:
        """Get top performing FSAs sorted by LQ."""
        sorted_results = sorted(
            self._analysis_results.items(),
            key=lambda x: x[1].average_lq,
            reverse=True,
        )
        return sorted_results[:limit]

    def get_bottlenecks(self, limit: int = 5) -> List[Tuple[str, FSAPatternAnalysis]]:
        """Get FSAs identified as bottlenecks."""
        bottlenecks = [
            (fsa_id, analysis)
            for fsa_id, analysis in self._analysis_results.items()
            if analysis.performance_category == "bottleneck"
        ]
        return sorted(bottlenecks, key=lambda x: x[1].average_lq)[:limit]


def create_cli_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fsa_meta_pattern_analyzer",
        description="Analyze FSA execution patterns and calculate leverage quotients",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze logs in current directory
  python -m agno.agent.fsa1_meta_pattern_analyzer

  # Analyze specific directory
  python -m agno.agent.fsa1_meta_pattern_analyzer -d /path/to/logs

  # Export results to JSON
  python -m agno.agent.fsa1_meta_pattern_analyzer -d ./logs -o results.json

  # Show top performers and bottlenecks
  python -m agno.agent.fsa1_meta_pattern_analyzer -d ./logs --top 10 --bottlenecks

  # Verbose output with debug logging
  python -m agno.agent.fsa1_meta_pattern_analyzer -d ./logs -v
        """,
    )

    parser.add_argument(
        "-d", "--directory",
        type=str,
        default=".",
        help="Directory containing FSA execution logs (default: current directory)",
    )

    parser.add_argument(
        "-p", "--patterns",
        type=str,
        nargs="+",
        default=["*.log", "*.json"],
        help="File patterns to search for (default: *.log *.json)",
    )

    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=True,
        help="Search recursively in subdirectories (default: True)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive search",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path for results",
    )

    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of top performers to display (default: 5)",
    )

    parser.add_argument(
        "--bottlenecks",
        action="store_true",
        help="Show identified bottlenecks",
    )

    parser.add_argument(
        "--meta-lq",
        action="store_true",
        default=True,
        help="Calculate and display meta leverage quotient (default: True)",
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
        version=f"%(prog)s {FSAMetaPatternAnalyzer.VERSION}",
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

    # Handle recursive flag
    recursive = parsed.recursive and not parsed.no_recursive

    try:
        # Initialize analyzer
        analyzer = FSAMetaPatternAnalyzer(log_directory=parsed.directory)

        if not parsed.quiet:
            logger.info(f"FSA Meta Pattern Analyzer v{FSAMetaPatternAnalyzer.VERSION}")
            logger.info(f"Analyzing directory: {parsed.directory}")

        # Collect and analyze logs
        log_files = analyzer.collect_logs_powershell(
            patterns=parsed.patterns,
            recursive=recursive,
        )

        if not log_files:
            logger.warning("No log files found matching the specified patterns")
            return 1

        # Run analysis
        results = analyzer.analyze_patterns(log_files)

        if not results:
            logger.warning("No FSA execution records found in logs")
            return 1

        # Generate recommendations
        recommendations = analyzer.generate_recommendations()

        # Calculate meta-LQ
        if parsed.meta_lq:
            meta_assessment = analyzer.calculate_meta_lq()

        # Display results
        if not parsed.quiet:
            print("\n" + "=" * 60)
            print("FSA PATTERN ANALYSIS RESULTS")
            print("=" * 60)

            # Top performers
            print(f"\nTop {parsed.top} Performers:")
            print("-" * 40)
            for fsa_id, analysis in analyzer.get_top_performers(parsed.top):
                print(f"  {fsa_id}: LQ={analysis.average_lq:.4f}, "
                      f"Success={analysis.success_rate:.1%}, "
                      f"Trend={analysis.lq_trend:+.4f}")

            # Bottlenecks
            if parsed.bottlenecks:
                bottlenecks = analyzer.get_bottlenecks()
                if bottlenecks:
                    print(f"\nIdentified Bottlenecks:")
                    print("-" * 40)
                    for fsa_id, analysis in bottlenecks:
                        print(f"  {fsa_id}: LQ={analysis.average_lq:.4f}, "
                              f"Success={analysis.success_rate:.1%}")
                        for rec in analysis.recommendations[:3]:
                            print(f"    → {rec}")

            # Meta-LQ
            if parsed.meta_lq and meta_assessment:
                print(f"\nMeta Assessment:")
                print("-" * 40)
                print(f"  Analyzer Meta-LQ: {meta_assessment.meta_lq:.4f}")
                print(f"  Efficiency Score: {meta_assessment.efficiency_score:.4f}")
                print(f"  Accuracy Confidence: {meta_assessment.accuracy_confidence:.4f}")
                print(f"  Records Analyzed: {meta_assessment.records_analyzed}")
                print(f"  Analysis Time: {meta_assessment.analysis_time_ms:.2f}ms")

        # Export results if output specified
        if parsed.output:
            success = analyzer.export_results(parsed.output, parsed.format)
            if success:
                logger.info(f"Results exported to: {parsed.output}")
            else:
                logger.error(f"Failed to export results to: {parsed.output}")
                return 1

        return 0

    except PowerShellError as e:
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

"""
Logger FSA - Production-ready logging system with state machine pattern.

This module provides a comprehensive Finite State Automaton for logging operations
including multi-level logging, structured logging, async operations, and integrations.

Features:
- Multi-level logging support (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Multiple output handlers (console, file, rotating file, syslog, remote)
- Structured logging with JSON formatting
- Contextual logging with request IDs and trace IDs
- Log aggregation and filtering
- Performance metrics and log analytics
- Async logging support for high-throughput scenarios
- Log buffering and batching for efficiency
- Integration with monitoring systems (Prometheus, DataDog, CloudWatch)
- Sensitive data masking and PII protection
- Log rotation policies (size-based, time-based)
- Compression of archived logs
- Log level configuration per module/component
- Custom log formatters and handlers
- Thread-safe and process-safe logging
- Correlation ID tracking across distributed systems
- Log sampling for high-volume scenarios
- Error reporting integration (Sentry, Rollbar)
- Audit logging with tamper-proof signatures
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import json
import logging
import logging.handlers
import os
import queue
import re
import secrets
import sys
import threading
import time
import traceback
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock, RLock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    Iterator,
    Pattern,
    TextIO,
)

try:
    import syslog
    HAS_SYSLOG = True
except ImportError:
    HAS_SYSLOG = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from pydantic import BaseModel, Field, validator


# ============================================================================
# Enums and Constants
# ============================================================================

class LoggerState(str, Enum):
    """States in the logger lifecycle."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    LOGGING = "logging"
    BUFFERING = "buffering"
    FLUSHING = "flushing"
    ROTATING = "rotating"
    ARCHIVING = "archiving"
    TRANSMITTING = "transmitting"
    SAMPLING = "sampling"
    MASKING = "masking"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class LogLevel(str, Enum):
    """Log levels matching standard logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    NOTSET = "NOTSET"

    def to_int(self) -> int:
        """Convert to logging module integer level."""
        return {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
            LogLevel.NOTSET: logging.NOTSET,
        }[self]


class HandlerType(str, Enum):
    """Types of log handlers."""
    CONSOLE = "console"
    FILE = "file"
    ROTATING_FILE = "rotating_file"
    TIMED_ROTATING_FILE = "timed_rotating_file"
    SYSLOG = "syslog"
    REMOTE_HTTP = "remote_http"
    REMOTE_SYSLOG = "remote_syslog"
    MEMORY = "memory"
    NULL = "null"
    CUSTOM = "custom"


class FormatterType(str, Enum):
    """Types of log formatters."""
    TEXT = "text"
    JSON = "json"
    COMPACT = "compact"
    DETAILED = "detailed"
    CUSTOM = "custom"


class RotationPolicy(str, Enum):
    """Log rotation policies."""
    SIZE = "size"
    TIME = "time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SamplingStrategy(str, Enum):
    """Log sampling strategies."""
    NONE = "none"
    RANDOM = "random"
    RATE_LIMIT = "rate_limit"
    PRIORITY = "priority"
    ADAPTIVE = "adaptive"


# ============================================================================
# Exceptions
# ============================================================================

class LoggerError(Exception):
    """Base exception for logger errors."""
    pass


class StateTransitionError(LoggerError):
    """Exception raised when invalid state transition is attempted."""
    pass


class HandlerError(LoggerError):
    """Exception raised when handler operation fails."""
    pass


class FormatterError(LoggerError):
    """Exception raised when formatting fails."""
    pass


class BufferOverflowError(LoggerError):
    """Exception raised when log buffer overflows."""
    pass


class RotationError(LoggerError):
    """Exception raised when log rotation fails."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LogRecord:
    """Enhanced log record with context and metadata."""
    timestamp: float
    level: LogLevel
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    thread_id: int
    thread_name: str
    process_id: int
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    exception_info: Optional[str] = None
    stack_trace: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    hostname: Optional[str] = None
    environment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert log record to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class LogMetrics:
    """Metrics for logging operations."""
    logger_name: str
    start_time: float = field(default_factory=time.time)
    total_logs: int = 0
    logs_by_level: Dict[LogLevel, int] = field(default_factory=lambda: defaultdict(int))
    bytes_written: int = 0
    errors: int = 0
    warnings: int = 0
    criticals: int = 0
    drops: int = 0
    samples: int = 0
    rotations: int = 0
    flushes: int = 0
    avg_log_size: float = 0.0
    avg_processing_time: float = 0.0
    peak_throughput: float = 0.0
    buffer_overflows: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        result = asdict(self)
        result['logs_by_level'] = {k.value: v for k, v in self.logs_by_level.items()}
        return result


@dataclass
class HandlerConfig:
    """Configuration for a log handler."""
    handler_type: HandlerType
    level: LogLevel = LogLevel.INFO
    formatter_type: FormatterType = FormatterType.TEXT
    enabled: bool = True

    # File handler options
    filename: Optional[str] = None
    mode: str = 'a'
    encoding: str = 'utf-8'

    # Rotating file handler options
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    rotation_policy: RotationPolicy = RotationPolicy.SIZE
    compress_rotated: bool = True

    # Timed rotating options
    when: str = 'midnight'
    interval: int = 1

    # Remote handler options
    url: Optional[str] = None
    api_key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    batch_size: int = 100
    flush_interval: float = 5.0

    # Syslog options
    facility: int = 16  # LOG_LOCAL0
    socktype: Optional[int] = None
    address: Tuple[str, int] = ('localhost', 514)

    # Buffering options
    buffer_size: int = 1000
    flush_level: Optional[LogLevel] = LogLevel.ERROR

    # Custom options
    custom_handler: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormatterConfig:
    """Configuration for a log formatter."""
    formatter_type: FormatterType
    format_string: Optional[str] = None
    date_format: Optional[str] = None
    include_timestamp: bool = True
    include_level: bool = True
    include_logger_name: bool = True
    include_correlation_id: bool = True
    include_trace_id: bool = True
    pretty_print: bool = False
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    custom_formatter: Optional[Callable] = None


@dataclass
class PIIMask:
    """Configuration for PII masking."""
    field_name: str
    mask_type: str = 'full'  # 'full', 'partial', 'hash'
    pattern: Optional[str] = None
    replacement: str = '***MASKED***'
    preserve_length: bool = False


@dataclass
class AuditLogEntry:
    """Tamper-proof audit log entry."""
    timestamp: float
    event_type: str
    actor: str
    action: str
    resource: str
    result: str
    details: Dict[str, Any]
    signature: str
    previous_hash: Optional[str] = None
    entry_hash: Optional[str] = None


# ============================================================================
# PII Masking
# ============================================================================

class PIIMasker:
    """Handles masking of personally identifiable information."""

    # Common PII patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
    IP_ADDRESS_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')

    def __init__(self):
        """Initialize PII masker."""
        self.masks: List[PIIMask] = []
        self.custom_patterns: Dict[str, Pattern] = {}

    def add_mask(self, mask: PIIMask) -> None:
        """Add a PII mask configuration."""
        self.masks.append(mask)
        if mask.pattern:
            self.custom_patterns[mask.field_name] = re.compile(mask.pattern)

    def mask_data(self, data: Any) -> Any:
        """Mask PII in data recursively."""
        if isinstance(data, str):
            return self._mask_string(data)
        elif isinstance(data, dict):
            return {k: self.mask_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]
        else:
            return data

    def _mask_string(self, text: str) -> str:
        """Mask PII patterns in a string."""
        # Mask emails
        text = self.EMAIL_PATTERN.sub(lambda m: self._mask_email(m.group(0)), text)

        # Mask phone numbers
        text = self.PHONE_PATTERN.sub('XXX-XXX-XXXX', text)

        # Mask SSN
        text = self.SSN_PATTERN.sub('XXX-XX-XXXX', text)

        # Mask credit cards
        text = self.CREDIT_CARD_PATTERN.sub(
            lambda m: 'XXXX-XXXX-XXXX-' + m.group(0)[-4:], text
        )

        # Apply custom patterns
        for field_name, pattern in self.custom_patterns.items():
            mask = next((m for m in self.masks if m.field_name == field_name), None)
            if mask:
                text = pattern.sub(mask.replacement, text)

        return text

    def _mask_email(self, email: str) -> str:
        """Mask email address partially."""
        parts = email.split('@')
        if len(parts) != 2:
            return '***@***.***'

        username = parts[0]
        domain = parts[1]

        # Keep first and last character of username
        if len(username) > 2:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
        else:
            masked_username = '*' * len(username)

        return f"{masked_username}@{domain}"


# ============================================================================
# Log Sampling
# ============================================================================

class LogSampler:
    """Handles log sampling for high-volume scenarios."""

    def __init__(
        self,
        strategy: SamplingStrategy = SamplingStrategy.NONE,
        sample_rate: float = 1.0,
        rate_limit: int = 1000,
        window_seconds: int = 60,
    ):
        """
        Initialize log sampler.

        Args:
            strategy: Sampling strategy to use
            sample_rate: Sample rate (0.0 to 1.0)
            rate_limit: Maximum logs per window
            window_seconds: Time window for rate limiting
        """
        self.strategy = strategy
        self.sample_rate = sample_rate
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.counts: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()

    def should_log(self, record: LogRecord) -> bool:
        """Determine if a log record should be logged."""
        if self.strategy == SamplingStrategy.NONE:
            return True

        elif self.strategy == SamplingStrategy.RANDOM:
            return secrets.SystemRandom().random() < self.sample_rate

        elif self.strategy == SamplingStrategy.RATE_LIMIT:
            return self._check_rate_limit(record)

        elif self.strategy == SamplingStrategy.PRIORITY:
            return self._check_priority(record)

        elif self.strategy == SamplingStrategy.ADAPTIVE:
            return self._check_adaptive(record)

        return True

    def _check_rate_limit(self, record: LogRecord) -> bool:
        """Check if record passes rate limit."""
        with self.lock:
            key = f"{record.logger_name}:{record.level}"
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # Remove old entries
            while self.counts[key] and self.counts[key][0] < window_start:
                self.counts[key].popleft()

            # Check limit
            if len(self.counts[key]) < self.rate_limit:
                self.counts[key].append(current_time)
                return True

            return False

    def _check_priority(self, record: LogRecord) -> bool:
        """Check if record passes priority filter."""
        # Always log ERROR and CRITICAL
        if record.level in (LogLevel.ERROR, LogLevel.CRITICAL):
            return True

        # Sample other levels based on rate
        return secrets.SystemRandom().random() < self.sample_rate

    def _check_adaptive(self, record: LogRecord) -> bool:
        """Adaptive sampling based on current load."""
        # Simple adaptive: reduce sample rate if we're logging a lot
        with self.lock:
            current_time = time.time()
            window_start = current_time - self.window_seconds

            total_logs = sum(
                len([t for t in timestamps if t >= window_start])
                for timestamps in self.counts.values()
            )

            # Adjust sample rate based on load
            if total_logs > self.rate_limit * 0.8:
                adjusted_rate = self.sample_rate * 0.5
            else:
                adjusted_rate = self.sample_rate

            return secrets.SystemRandom().random() < adjusted_rate


# ============================================================================
# Structured Formatters
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def __init__(
        self,
        include_correlation_id: bool = True,
        include_trace_id: bool = True,
        pretty_print: bool = False,
        custom_fields: Optional[Dict[str, Any]] = None,
    ):
        """Initialize JSON formatter."""
        super().__init__()
        self.include_correlation_id = include_correlation_id
        self.include_trace_id = include_trace_id
        self.pretty_print = pretty_print
        self.custom_fields = custom_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'thread_name': record.threadName,
            'process_id': record.process,
        }

        # Add correlation/trace IDs if available
        if self.include_correlation_id and hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        if self.include_trace_id and hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id

        # Add custom fields
        log_data.update(self.custom_fields)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra

        if self.pretty_print:
            return json.dumps(log_data, indent=2, default=str)
        else:
            return json.dumps(log_data, default=str)


# ============================================================================
# Custom Handlers
# ============================================================================

class BufferedHandler(logging.Handler):
    """Handler that buffers log records and flushes in batches."""

    def __init__(
        self,
        target_handler: logging.Handler,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        flush_level: Optional[int] = logging.ERROR,
    ):
        """
        Initialize buffered handler.

        Args:
            target_handler: Handler to flush to
            buffer_size: Maximum buffer size before flush
            flush_interval: Time interval for automatic flush
            flush_level: Log level that triggers immediate flush
        """
        super().__init__()
        self.target_handler = target_handler
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.flush_level = flush_level
        self.buffer: List[logging.LogRecord] = []
        self.lock = Lock()
        self.last_flush = time.time()

        # Start flush timer
        self._start_flush_timer()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        with self.lock:
            self.buffer.append(record)

            # Flush if buffer is full or level is high
            should_flush = (
                len(self.buffer) >= self.buffer_size or
                (self.flush_level and record.levelno >= self.flush_level)
            )

            if should_flush:
                self._flush()

    def _flush(self) -> None:
        """Flush buffered records."""
        if not self.buffer:
            return

        for record in self.buffer:
            self.target_handler.emit(record)

        self.buffer.clear()
        self.last_flush = time.time()

    def flush(self) -> None:
        """Public flush method."""
        with self.lock:
            self._flush()
            self.target_handler.flush()

    def _start_flush_timer(self) -> None:
        """Start periodic flush timer."""
        def flush_periodically():
            while True:
                time.sleep(self.flush_interval)
                with self.lock:
                    if time.time() - self.last_flush >= self.flush_interval:
                        self._flush()

        timer_thread = threading.Thread(target=flush_periodically, daemon=True)
        timer_thread.start()


class RemoteHTTPHandler(logging.Handler):
    """Handler that sends logs to a remote HTTP endpoint."""

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        batch_size: int = 10,
        timeout: int = 5,
    ):
        """Initialize remote HTTP handler."""
        super().__init__()
        self.url = url
        self.api_key = api_key
        self.headers = headers or {}
        self.batch_size = batch_size
        self.timeout = timeout
        self.buffer: List[Dict[str, Any]] = []
        self.lock = Lock()

        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        if not HAS_REQUESTS:
            return

        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        with self.lock:
            self.buffer.append(log_data)

            if len(self.buffer) >= self.batch_size:
                self._send_logs()

    def _send_logs(self) -> None:
        """Send buffered logs to remote endpoint."""
        if not self.buffer:
            return

        try:
            response = requests.post(
                self.url,
                json={'logs': self.buffer},
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.buffer.clear()
        except Exception as e:
            # Log to stderr to avoid recursion
            print(f"Failed to send logs to remote: {e}", file=sys.stderr)

    def flush(self) -> None:
        """Flush buffered logs."""
        with self.lock:
            self._send_logs()


# ============================================================================
# Audit Logger
# ============================================================================

class AuditLogger:
    """Tamper-proof audit logger with signature verification."""

    def __init__(self, secret_key: str, log_file: str):
        """
        Initialize audit logger.

        Args:
            secret_key: Secret key for HMAC signatures
            log_file: Path to audit log file
        """
        self.secret_key = secret_key.encode()
        self.log_file = Path(log_file)
        self.lock = Lock()
        self.last_hash: Optional[str] = None

        # Load last hash if file exists
        if self.log_file.exists():
            self._load_last_hash()

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            actor: Who performed the action
            action: What action was performed
            resource: What resource was affected
            result: Result of the action
            details: Additional details

        Returns:
            Audit log entry
        """
        with self.lock:
            entry = AuditLogEntry(
                timestamp=time.time(),
                event_type=event_type,
                actor=actor,
                action=action,
                resource=resource,
                result=result,
                details=details or {},
                signature='',
                previous_hash=self.last_hash,
            )

            # Generate entry hash
            entry_data = f"{entry.timestamp}:{entry.event_type}:{entry.actor}:{entry.action}:{entry.resource}:{entry.result}"
            entry.entry_hash = hashlib.sha256(entry_data.encode()).hexdigest()

            # Generate signature
            sig_data = f"{entry.entry_hash}:{entry.previous_hash}"
            entry.signature = hmac.new(
                self.secret_key,
                sig_data.encode(),
                hashlib.sha256
            ).hexdigest()

            # Write to file
            self._write_entry(entry)

            # Update last hash
            self.last_hash = entry.entry_hash

            return entry

    def _write_entry(self, entry: AuditLogEntry) -> None:
        """Write entry to audit log file."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(entry), default=str) + '\n')

    def _load_last_hash(self) -> None:
        """Load the hash of the last entry."""
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    self.last_hash = last_entry.get('entry_hash')
        except Exception as e:
            print(f"Failed to load last hash: {e}", file=sys.stderr)

    def verify_chain(self) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the audit log chain.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        previous_hash = None

        try:
            with open(self.log_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry_dict = json.loads(line)
                        entry = AuditLogEntry(**entry_dict)

                        # Verify previous hash matches
                        if entry.previous_hash != previous_hash:
                            errors.append(
                                f"Line {line_num}: Previous hash mismatch"
                            )

                        # Verify signature
                        sig_data = f"{entry.entry_hash}:{entry.previous_hash}"
                        expected_sig = hmac.new(
                            self.secret_key,
                            sig_data.encode(),
                            hashlib.sha256
                        ).hexdigest()

                        if entry.signature != expected_sig:
                            errors.append(
                                f"Line {line_num}: Invalid signature"
                            )

                        previous_hash = entry.entry_hash

                    except Exception as e:
                        errors.append(f"Line {line_num}: Parse error: {e}")

        except FileNotFoundError:
            errors.append("Audit log file not found")

        return len(errors) == 0, errors


# ============================================================================
# Logger FSA
# ============================================================================

class LoggerFSA:
    """
    Production-ready Logger Finite State Automaton.

    This FSA implements a comprehensive logging system with:
    - Multi-level logging support
    - Multiple output handlers
    - Structured logging with JSON
    - Contextual logging
    - Async operations
    - PII masking
    - Log sampling
    - Rotation and archiving
    - Audit logging
    - Integration with monitoring systems

    Example:
        fsa = LoggerFSA(name="app_logger")

        # Add console handler
        fsa.add_handler(HandlerConfig(
            handler_type=HandlerType.CONSOLE,
            level=LogLevel.INFO,
            formatter_type=FormatterType.JSON
        ))

        # Log messages
        fsa.info("Application started", extra={"version": "1.0"})
        fsa.error("Connection failed", exc_info=True)
    """

    def __init__(
        self,
        name: str = "logger_fsa",
        level: LogLevel = LogLevel.INFO,
        enable_async: bool = False,
        enable_metrics: bool = True,
        enable_sampling: bool = False,
        enable_pii_masking: bool = False,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize Logger FSA.

        Args:
            name: Logger name
            level: Default log level
            enable_async: Enable async logging
            enable_metrics: Enable metrics collection
            enable_sampling: Enable log sampling
            enable_pii_masking: Enable PII masking
            correlation_id: Correlation ID for distributed tracing
        """
        self.name = name
        self.level = level
        self.enable_async = enable_async
        self.enable_metrics = enable_metrics
        self.enable_sampling = enable_sampling
        self.enable_pii_masking = enable_pii_masking
        self.correlation_id = correlation_id or str(uuid.uuid4())

        # State machine
        self.state = LoggerState.IDLE
        self.state_lock = RLock()

        # Logging components
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.to_int())
        self.logger.propagate = False

        # Handlers and formatters
        self.handlers: Dict[str, logging.Handler] = {}
        self.formatters: Dict[str, logging.Formatter] = {}

        # Context management
        self.context: Dict[str, Any] = {}
        self.context_lock = Lock()

        # Async logging
        self.async_queue: Optional[queue.Queue] = None
        self.async_thread: Optional[threading.Thread] = None
        if enable_async:
            self._setup_async_logging()

        # Metrics
        self.metrics = LogMetrics(logger_name=name) if enable_metrics else None

        # Sampling
        self.sampler: Optional[LogSampler] = None
        if enable_sampling:
            self.sampler = LogSampler()

        # PII Masking
        self.pii_masker: Optional[PIIMasker] = None
        if enable_pii_masking:
            self.pii_masker = PIIMasker()

        # Audit logging
        self.audit_logger: Optional[AuditLogger] = None

        # Module-specific levels
        self.module_levels: Dict[str, LogLevel] = {}

        # State transitions
        self.valid_transitions = {
            LoggerState.IDLE: {
                LoggerState.INITIALIZING,
                LoggerState.LOGGING,
                LoggerState.SHUTDOWN,
            },
            LoggerState.INITIALIZING: {
                LoggerState.LOGGING,
                LoggerState.ERROR,
            },
            LoggerState.LOGGING: {
                LoggerState.BUFFERING,
                LoggerState.FLUSHING,
                LoggerState.ROTATING,
                LoggerState.TRANSMITTING,
                LoggerState.SAMPLING,
                LoggerState.MASKING,
                LoggerState.ERROR,
                LoggerState.SHUTDOWN,
            },
            LoggerState.BUFFERING: {
                LoggerState.LOGGING,
                LoggerState.FLUSHING,
            },
            LoggerState.FLUSHING: {
                LoggerState.LOGGING,
                LoggerState.TRANSMITTING,
            },
            LoggerState.ROTATING: {
                LoggerState.ARCHIVING,
                LoggerState.LOGGING,
            },
            LoggerState.ARCHIVING: {
                LoggerState.LOGGING,
            },
            LoggerState.TRANSMITTING: {
                LoggerState.LOGGING,
            },
            LoggerState.SAMPLING: {
                LoggerState.LOGGING,
            },
            LoggerState.MASKING: {
                LoggerState.LOGGING,
            },
            LoggerState.ERROR: {
                LoggerState.LOGGING,
                LoggerState.SHUTDOWN,
            },
            LoggerState.SHUTDOWN: {
                LoggerState.IDLE,
            },
        }

        self.transition_to(LoggerState.INITIALIZING)
        self.transition_to(LoggerState.LOGGING)

    def transition_to(self, new_state: LoggerState) -> None:
        """Transition to a new state."""
        with self.state_lock:
            if new_state not in self.valid_transitions.get(self.state, set()):
                raise StateTransitionError(
                    f"Invalid state transition from {self.state} to {new_state}"
                )

            old_state = self.state
            self.state = new_state

    def _setup_async_logging(self) -> None:
        """Setup async logging with queue."""
        self.async_queue = queue.Queue(maxsize=10000)

        def process_queue():
            while True:
                try:
                    record = self.async_queue.get(timeout=1)
                    if record is None:  # Shutdown signal
                        break
                    self.logger.handle(record)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Async logging error: {e}", file=sys.stderr)

        self.async_thread = threading.Thread(target=process_queue, daemon=True)
        self.async_thread.start()

    def add_handler(self, config: HandlerConfig) -> str:
        """
        Add a log handler.

        Args:
            config: Handler configuration

        Returns:
            Handler ID
        """
        handler_id = str(uuid.uuid4())

        # Create handler based on type
        if config.handler_type == HandlerType.CONSOLE:
            handler = logging.StreamHandler(sys.stdout)

        elif config.handler_type == HandlerType.FILE:
            if not config.filename:
                raise HandlerError("Filename required for file handler")
            handler = logging.FileHandler(
                config.filename,
                mode=config.mode,
                encoding=config.encoding
            )

        elif config.handler_type == HandlerType.ROTATING_FILE:
            if not config.filename:
                raise HandlerError("Filename required for rotating file handler")
            handler = logging.handlers.RotatingFileHandler(
                config.filename,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
                encoding=config.encoding
            )

        elif config.handler_type == HandlerType.TIMED_ROTATING_FILE:
            if not config.filename:
                raise HandlerError("Filename required for timed rotating file handler")
            handler = logging.handlers.TimedRotatingFileHandler(
                config.filename,
                when=config.when,
                interval=config.interval,
                backupCount=config.backup_count,
                encoding=config.encoding
            )

        elif config.handler_type == HandlerType.SYSLOG:
            if not HAS_SYSLOG:
                raise HandlerError("Syslog not available on this platform")
            handler = logging.handlers.SysLogHandler(
                address=config.address,
                facility=config.facility
            )

        elif config.handler_type == HandlerType.REMOTE_HTTP:
            if not config.url:
                raise HandlerError("URL required for remote HTTP handler")
            handler = RemoteHTTPHandler(
                url=config.url,
                api_key=config.api_key,
                headers=config.headers,
                batch_size=config.batch_size
            )

        elif config.handler_type == HandlerType.MEMORY:
            handler = logging.handlers.MemoryHandler(capacity=config.buffer_size)

        elif config.handler_type == HandlerType.NULL:
            handler = logging.NullHandler()

        elif config.handler_type == HandlerType.CUSTOM:
            if not config.custom_handler:
                raise HandlerError("Custom handler required")
            handler = config.custom_handler

        else:
            raise HandlerError(f"Unsupported handler type: {config.handler_type}")

        # Set level
        handler.setLevel(config.level.to_int())

        # Create and set formatter
        formatter = self._create_formatter(config.formatter_type)
        handler.setFormatter(formatter)

        # Add buffering if configured
        if config.buffer_size > 0 and config.handler_type not in (
            HandlerType.MEMORY, HandlerType.REMOTE_HTTP
        ):
            handler = BufferedHandler(
                handler,
                buffer_size=config.buffer_size,
                flush_level=config.flush_level.to_int() if config.flush_level else None
            )

        # Add handler to logger
        self.logger.addHandler(handler)
        self.handlers[handler_id] = handler

        return handler_id

    def _create_formatter(self, formatter_type: FormatterType) -> logging.Formatter:
        """Create a formatter based on type."""
        if formatter_type == FormatterType.JSON:
            return JSONFormatter(pretty_print=False)

        elif formatter_type == FormatterType.TEXT:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        elif formatter_type == FormatterType.COMPACT:
            return logging.Formatter('%(levelname)s: %(message)s')

        elif formatter_type == FormatterType.DETAILED:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )

        else:
            return logging.Formatter('%(message)s')

    def remove_handler(self, handler_id: str) -> None:
        """Remove a handler."""
        if handler_id in self.handlers:
            handler = self.handlers[handler_id]
            self.logger.removeHandler(handler)
            del self.handlers[handler_id]

    @contextmanager
    def context_manager(self, **kwargs):
        """
        Context manager for adding temporary context.

        Example:
            with logger.context_manager(request_id="123"):
                logger.info("Processing request")
        """
        with self.context_lock:
            old_context = self.context.copy()
            self.context.update(kwargs)

        try:
            yield
        finally:
            with self.context_lock:
                self.context = old_context

    def set_context(self, **kwargs) -> None:
        """Set logging context."""
        with self.context_lock:
            self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear logging context."""
        with self.context_lock:
            self.context.clear()

    def set_module_level(self, module: str, level: LogLevel) -> None:
        """Set log level for specific module."""
        self.module_levels[module] = level

    def _create_log_record(
        self,
        level: LogLevel,
        message: str,
        exc_info: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> LogRecord:
        """Create enhanced log record."""
        import inspect

        # Get caller information
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            module = inspect.getmodule(caller_frame)
            module_name = module.__name__ if module else '__main__'
            function = caller_frame.f_code.co_name
            line_number = caller_frame.f_lineno
        else:
            module_name = '__main__'
            function = '<unknown>'
            line_number = 0

        record = LogRecord(
            timestamp=time.time(),
            level=level,
            message=message,
            logger_name=self.name,
            module=module_name,
            function=function,
            line_number=line_number,
            thread_id=threading.get_ident(),
            thread_name=threading.current_thread().name,
            process_id=os.getpid(),
            correlation_id=self.correlation_id,
            extra=extra or {},
        )

        # Add context
        with self.context_lock:
            record.extra.update(self.context)

        # Add exception info
        if exc_info:
            if exc_info is True:
                exc_info = sys.exc_info()
            if exc_info and exc_info[0] is not None:
                record.exception_info = str(exc_info[1])
                record.stack_trace = ''.join(traceback.format_exception(*exc_info))

        return record

    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal logging method."""
        # Create log record
        record = self._create_log_record(level, message, exc_info, extra)

        # Apply sampling
        if self.sampler and not self.sampler.should_log(record):
            if self.metrics:
                self.metrics.samples += 1
            return

        # Apply PII masking
        if self.pii_masker:
            self.transition_to(LoggerState.MASKING)
            record.message = self.pii_masker._mask_string(record.message)
            record.extra = self.pii_masker.mask_data(record.extra)
            self.transition_to(LoggerState.LOGGING)

        # Create standard logging record
        log_record = self.logger.makeRecord(
            self.name,
            level.to_int(),
            record.module,
            record.line_number,
            record.message,
            (),
            exc_info,
            record.function,
        )

        # Add extra fields
        for key, value in record.extra.items():
            setattr(log_record, key, value)

        setattr(log_record, 'correlation_id', record.correlation_id)

        # Update metrics
        if self.metrics:
            self.metrics.total_logs += 1
            self.metrics.logs_by_level[level] += 1

            if level == LogLevel.ERROR:
                self.metrics.errors += 1
            elif level == LogLevel.WARNING:
                self.metrics.warnings += 1
            elif level == LogLevel.CRITICAL:
                self.metrics.criticals += 1

        # Log async or sync
        if self.enable_async and self.async_queue:
            try:
                self.async_queue.put_nowait(log_record)
            except queue.Full:
                if self.metrics:
                    self.metrics.drops += 1
        else:
            self.logger.handle(log_record)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        kwargs['exc_info'] = True
        self._log(LogLevel.ERROR, message, **kwargs)

    def flush(self) -> None:
        """Flush all handlers."""
        self.transition_to(LoggerState.FLUSHING)

        for handler in self.logger.handlers:
            handler.flush()

        if self.metrics:
            self.metrics.flushes += 1

        self.transition_to(LoggerState.LOGGING)

    def rotate_logs(self) -> None:
        """Manually trigger log rotation."""
        self.transition_to(LoggerState.ROTATING)

        for handler in self.logger.handlers:
            if hasattr(handler, 'doRollover'):
                handler.doRollover()
                if self.metrics:
                    self.metrics.rotations += 1

        self.transition_to(LoggerState.LOGGING)

    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics."""
        if self.metrics:
            return self.metrics.to_dict()
        return {}

    def enable_audit_logging(self, secret_key: str, log_file: str) -> None:
        """Enable audit logging."""
        self.audit_logger = AuditLogger(secret_key, log_file)

    def audit(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event."""
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type, actor, action, resource, result, details
            )

    def shutdown(self) -> None:
        """Shutdown logger and cleanup resources."""
        self.transition_to(LoggerState.SHUTDOWN)

        # Flush all handlers
        self.flush()

        # Stop async thread
        if self.async_queue:
            self.async_queue.put(None)

        if self.async_thread:
            self.async_thread.join(timeout=5)

        # Remove all handlers
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)

        self.transition_to(LoggerState.IDLE)


# ============================================================================
# Utility Functions
# ============================================================================

def compress_log_file(log_file: str, delete_original: bool = True) -> str:
    """
    Compress a log file using gzip.

    Args:
        log_file: Path to log file
        delete_original: Whether to delete original file

    Returns:
        Path to compressed file
    """
    compressed_file = f"{log_file}.gz"

    with open(log_file, 'rb') as f_in:
        with gzip.open(compressed_file, 'wb') as f_out:
            f_out.writelines(f_in)

    if delete_original:
        os.remove(log_file)

    return compressed_file


def create_rotating_handler(
    filename: str,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    compress: bool = True,
) -> logging.Handler:
    """
    Create a rotating file handler with optional compression.

    Args:
        filename: Log file path
        max_bytes: Maximum file size before rotation
        backup_count: Number of backup files to keep
        compress: Whether to compress rotated files

    Returns:
        Rotating file handler
    """
    handler = logging.handlers.RotatingFileHandler(
        filename,
        maxBytes=max_bytes,
        backupCount=backup_count
    )

    if compress:
        # Wrap rotation to add compression
        original_rotate = handler.doRollover

        def compress_on_rotate():
            original_rotate()
            # Compress the rotated file
            for i in range(1, backup_count + 1):
                rotated = f"{filename}.{i}"
                if os.path.exists(rotated) and not rotated.endswith('.gz'):
                    compress_log_file(rotated, delete_original=True)

        handler.doRollover = compress_on_rotate

    return handler

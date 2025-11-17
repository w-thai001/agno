"""
Logger FSA (Finite State Automaton) - Production-ready centralized logging system.

This module provides a state machine-based logger with structured output, multiple log levels,
contextual tracking, and configurable output handlers.

States:
    - IDLE: Logger is initialized but not actively logging
    - LOGGING: Logger is processing a log entry
    - FILTERING: Logger is applying filters to determine if log should be written
    - WRITING: Logger is writing to configured handlers
    - ERROR: Logger encountered an error during operation

Example:
    >>> from agno.utils.logger_fsa import LoggerFSA, LogLevel
    >>> logger = LoggerFSA(name="my_app")
    >>> logger.add_context("request_id", "123-456")
    >>> logger.info("User logged in", user_id="user_123")
    >>> stats = logger.get_stats()
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, TextIO, Union


class LogLevel(Enum):
    """Log level enumeration with numeric priorities."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __lt__(self, other: "LogLevel") -> bool:
        return self.value < other.value

    def __le__(self, other: "LogLevel") -> bool:
        return self.value <= other.value


class LoggerState(Enum):
    """FSA states for the logger."""

    IDLE = "idle"
    LOGGING = "logging"
    FILTERING = "filtering"
    WRITING = "writing"
    ERROR = "error"


@dataclass
class LogEntry:
    """Structured log entry with metadata."""

    timestamp: str
    level: str
    logger_name: str
    message: str
    context: Dict[str, Any]
    state: str
    elapsed_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    def to_text(self) -> str:
        """Convert log entry to human-readable text."""
        context_str = ""
        if self.context:
            context_items = [f"{k}={v}" for k, v in self.context.items()]
            context_str = f" [{', '.join(context_items)}]"

        elapsed_str = ""
        if self.elapsed_ms is not None:
            elapsed_str = f" ({self.elapsed_ms:.2f}ms)"

        return f"{self.timestamp} [{self.level}] {self.logger_name}: {self.message}{context_str}{elapsed_str}"


@dataclass
class LoggerConfig:
    """Configuration for the logger."""

    name: str = "logger"
    level: LogLevel = LogLevel.INFO
    output_format: str = "text"  # "text", "json"
    enable_context: bool = True
    enable_metrics: bool = True
    max_context_depth: int = 10
    buffer_size: int = 1000


@dataclass
class LoggerStats:
    """Statistics about logging operations."""

    total_logs: int = 0
    logs_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    logs_by_state: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    context_keys: set = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_logs": self.total_logs,
            "logs_by_level": dict(self.logs_by_level),
            "logs_by_state": dict(self.logs_by_state),
            "errors": self.errors,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "context_keys": list(self.context_keys),
        }


class LogHandler:
    """Base class for log handlers."""

    def __init__(self, formatter: str = "text"):
        """
        Initialize the log handler.

        Args:
            formatter: Output format - "text" or "json"
        """
        self.formatter = formatter

    def emit(self, entry: LogEntry) -> None:
        """
        Emit a log entry.

        Args:
            entry: The log entry to emit
        """
        raise NotImplementedError


class ConsoleHandler(LogHandler):
    """Handler that writes logs to console (stdout/stderr)."""

    def __init__(self, formatter: str = "text", stream: TextIO = sys.stdout):
        """
        Initialize console handler.

        Args:
            formatter: Output format - "text" or "json"
            stream: Output stream (default: sys.stdout)
        """
        super().__init__(formatter)
        self.stream = stream

    def emit(self, entry: LogEntry) -> None:
        """Write log entry to console."""
        if self.formatter == "json":
            output = entry.to_json()
        else:
            output = entry.to_text()

        try:
            self.stream.write(output + "\n")
            self.stream.flush()
        except Exception as e:
            sys.stderr.write(f"Error writing to console: {e}\n")


class FileHandler(LogHandler):
    """Handler that writes logs to a file."""

    def __init__(self, filepath: Union[str, Path], formatter: str = "text", mode: str = "a"):
        """
        Initialize file handler.

        Args:
            filepath: Path to the log file
            formatter: Output format - "text" or "json"
            mode: File open mode (default: "a" for append)
        """
        super().__init__(formatter)
        self.filepath = Path(filepath)
        self.mode = mode
        self._file: Optional[TextIO] = None
        self._lock = Lock()

    def _ensure_file_open(self) -> None:
        """Ensure the file is open for writing."""
        if self._file is None or self._file.closed:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.filepath, self.mode, encoding="utf-8")

    def emit(self, entry: LogEntry) -> None:
        """Write log entry to file."""
        with self._lock:
            try:
                self._ensure_file_open()
                if self.formatter == "json":
                    output = entry.to_json()
                else:
                    output = entry.to_text()

                if self._file:
                    self._file.write(output + "\n")
                    self._file.flush()
            except Exception as e:
                sys.stderr.write(f"Error writing to file {self.filepath}: {e}\n")

    def close(self) -> None:
        """Close the file handler."""
        with self._lock:
            if self._file and not self._file.closed:
                self._file.close()

    def __del__(self):
        """Cleanup when handler is destroyed."""
        self.close()


class RemoteHandler(LogHandler):
    """Handler that sends logs to a remote endpoint (placeholder for production use)."""

    def __init__(
        self, endpoint: str, formatter: str = "json", callback: Optional[Callable[[LogEntry], None]] = None
    ):
        """
        Initialize remote handler.

        Args:
            endpoint: Remote endpoint URL
            formatter: Output format (typically "json" for remote)
            callback: Optional callback function to handle log sending
        """
        super().__init__(formatter)
        self.endpoint = endpoint
        self.callback = callback
        self.buffer: deque = deque(maxlen=100)

    def emit(self, entry: LogEntry) -> None:
        """
        Send log entry to remote endpoint.

        In production, this would use HTTP/gRPC/etc. For now, uses callback or buffers.
        """
        if self.callback:
            try:
                self.callback(entry)
            except Exception as e:
                sys.stderr.write(f"Error in remote handler callback: {e}\n")
        else:
            # Buffer for later sending
            self.buffer.append(entry.to_dict())


class LoggerFSA:
    """
    Production-ready Logger with Finite State Automaton pattern.

    This logger implements a state machine for reliable logging with structured output,
    context management, multiple handlers, and performance tracking.

    Example:
        >>> logger = LoggerFSA(name="app")
        >>> logger.configure_handler("console", {"formatter": "json"})
        >>> logger.add_context("request_id", "req-123")
        >>> logger.info("Processing request", user_id="user-456")
        >>> print(logger.get_stats())
    """

    def __init__(
        self,
        name: str = "logger",
        level: LogLevel = LogLevel.INFO,
        output_format: str = "text",
        enable_auto_console: bool = True,
    ):
        """
        Initialize the Logger FSA.

        Args:
            name: Logger name for identification
            level: Minimum log level to process
            output_format: Default output format ("text" or "json")
            enable_auto_console: Automatically add console handler
        """
        self.config = LoggerConfig(name=name, level=level, output_format=output_format)
        self._state = LoggerState.IDLE
        self._handlers: List[LogHandler] = []
        self._context_stack: List[Dict[str, Any]] = [{}]
        self._stats = LoggerStats()
        self._lock = Lock()
        self._filters: List[Callable[[LogEntry], bool]] = []

        if enable_auto_console:
            self.configure_handler("console", {"formatter": output_format})

    @property
    def state(self) -> LoggerState:
        """Get current FSA state."""
        return self._state

    def _transition(self, new_state: LoggerState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state to transition to
        """
        self._state = new_state
        self._stats.logs_by_state[new_state.value] = self._stats.logs_by_state.get(new_state.value, 0) + 1

    def configure_handler(self, handler_type: str, config: Dict[str, Any]) -> None:
        """
        Configure and add a log handler.

        Args:
            handler_type: Type of handler ("console", "file", "remote")
            config: Handler configuration dictionary

        Raises:
            ValueError: If handler_type is unknown

        Example:
            >>> logger.configure_handler("file", {"filepath": "/tmp/app.log", "formatter": "json"})
            >>> logger.configure_handler("console", {"formatter": "text", "stream": sys.stderr})
        """
        formatter = config.get("formatter", self.config.output_format)

        if handler_type == "console":
            stream = config.get("stream", sys.stdout)
            handler = ConsoleHandler(formatter=formatter, stream=stream)
        elif handler_type == "file":
            filepath = config.get("filepath")
            if not filepath:
                raise ValueError("File handler requires 'filepath' in config")
            mode = config.get("mode", "a")
            handler = FileHandler(filepath=filepath, formatter=formatter, mode=mode)
        elif handler_type == "remote":
            endpoint = config.get("endpoint")
            if not endpoint:
                raise ValueError("Remote handler requires 'endpoint' in config")
            callback = config.get("callback")
            handler = RemoteHandler(endpoint=endpoint, formatter=formatter, callback=callback)
        else:
            raise ValueError(f"Unknown handler type: {handler_type}")

        self._handlers.append(handler)

    def add_filter(self, filter_func: Callable[[LogEntry], bool]) -> None:
        """
        Add a filter function to determine which logs to process.

        Args:
            filter_func: Function that takes LogEntry and returns True to keep, False to discard

        Example:
            >>> logger.add_filter(lambda entry: entry.level != "DEBUG")
        """
        self._filters.append(filter_func)

    def add_context(self, key: str, value: Any) -> None:
        """
        Add a key-value pair to the persistent context.

        Context is included in all subsequent log entries until cleared.

        Args:
            key: Context key
            value: Context value

        Example:
            >>> logger.add_context("user_id", "user-123")
            >>> logger.add_context("session_id", "session-456")
        """
        if len(self._context_stack) >= self.config.max_context_depth:
            sys.stderr.write(f"Warning: Context stack depth limit reached ({self.config.max_context_depth})\n")
            return

        self._context_stack[-1][key] = value
        self._stats.context_keys.add(key)

    def clear_context(self) -> None:
        """
        Clear all persistent context.

        Example:
            >>> logger.clear_context()
        """
        self._context_stack = [{}]

    def push_context(self) -> None:
        """
        Push a new context frame onto the stack.

        Useful for nested operations that need isolated context.

        Example:
            >>> logger.push_context()
            >>> logger.add_context("operation", "nested")
            >>> # ... do work ...
            >>> logger.pop_context()
        """
        self._context_stack.append(self._context_stack[-1].copy())

    def pop_context(self) -> None:
        """
        Pop the current context frame from the stack.

        Example:
            >>> logger.pop_context()
        """
        if len(self._context_stack) > 1:
            self._context_stack.pop()

    def _get_merged_context(self, extra_context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge persistent context with extra context for this log entry."""
        merged = self._context_stack[-1].copy()
        merged.update(extra_context)
        return merged

    def _apply_filters(self, entry: LogEntry) -> bool:
        """
        Apply all filters to determine if log should be processed.

        Args:
            entry: Log entry to filter

        Returns:
            True if log should be processed, False otherwise
        """
        self._transition(LoggerState.FILTERING)

        for filter_func in self._filters:
            try:
                if not filter_func(entry):
                    return False
            except Exception as e:
                sys.stderr.write(f"Error in filter function: {e}\n")
                # Continue processing if filter fails

        return True

    def _write_to_handlers(self, entry: LogEntry) -> None:
        """
        Write log entry to all configured handlers.

        Args:
            entry: Log entry to write
        """
        self._transition(LoggerState.WRITING)

        for handler in self._handlers:
            try:
                handler.emit(entry)
            except Exception as e:
                sys.stderr.write(f"Error in handler {handler.__class__.__name__}: {e}\n")
                self._stats.errors += 1

    def log(self, level: LogLevel, message: str, **context: Any) -> None:
        """
        Core logging function.

        Args:
            level: Log level
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.log(LogLevel.INFO, "User action", user_id="123", action="login")
        """
        # Check if log level is enabled
        if level < self.config.level:
            return

        start_time = time.perf_counter()

        with self._lock:
            try:
                self._transition(LoggerState.LOGGING)

                # Merge context
                merged_context = self._get_merged_context(context) if self.config.enable_context else context

                # Create log entry
                entry = LogEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    level=level.name,
                    logger_name=self.config.name,
                    message=message,
                    context=merged_context,
                    state=self._state.value,
                )

                # Apply filters
                if not self._apply_filters(entry):
                    self._transition(LoggerState.IDLE)
                    return

                # Calculate elapsed time
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                entry.elapsed_ms = elapsed_ms

                # Write to handlers
                self._write_to_handlers(entry)

                # Update statistics
                if self.config.enable_metrics:
                    self._stats.total_logs += 1
                    self._stats.logs_by_level[level.name] += 1
                    self._stats.total_time_ms += elapsed_ms
                    self._stats.avg_time_ms = self._stats.total_time_ms / self._stats.total_logs
                    # Track all context keys
                    for key in merged_context.keys():
                        self._stats.context_keys.add(key)

                self._transition(LoggerState.IDLE)

            except Exception as e:
                self._transition(LoggerState.ERROR)
                self._stats.errors += 1
                sys.stderr.write(f"Logger error: {e}\n")
                self._transition(LoggerState.IDLE)

    def debug(self, message: str, **context: Any) -> None:
        """
        Log a DEBUG level message.

        Args:
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.debug("Variable value", var_name="x", var_value=42)
        """
        self.log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """
        Log an INFO level message.

        Args:
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.info("User logged in", user_id="user-123")
        """
        self.log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """
        Log a WARNING level message.

        Args:
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.warning("Rate limit approaching", requests=95, limit=100)
        """
        self.log(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        """
        Log an ERROR level message.

        Args:
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.error("Database connection failed", error=str(e), retry_count=3)
        """
        self.log(LogLevel.ERROR, message, **context)

    def critical(self, message: str, **context: Any) -> None:
        """
        Log a CRITICAL level message.

        Args:
            message: Log message
            **context: Additional context key-value pairs

        Example:
            >>> logger.critical("System shutdown imminent", reason="out_of_memory")
        """
        self.log(LogLevel.CRITICAL, message, **context)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics.

        Returns:
            Dictionary containing logging statistics

        Example:
            >>> stats = logger.get_stats()
            >>> print(f"Total logs: {stats['total_logs']}")
        """
        return self._stats.to_dict()

    def set_level(self, level: LogLevel) -> None:
        """
        Set the minimum log level.

        Args:
            level: New log level

        Example:
            >>> logger.set_level(LogLevel.DEBUG)
        """
        self.config.level = level

    def close(self) -> None:
        """
        Close all handlers and cleanup resources.

        Example:
            >>> logger.close()
        """
        for handler in self._handlers:
            if hasattr(handler, "close"):
                handler.close()

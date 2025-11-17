"""
Unit tests for Logger FSA.

Tests cover:
- Log levels and filtering
- Context injection and management
- Multiple handlers
- State transitions
- Performance metrics
- Error handling
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

from agno.utils.logger_fsa import (
    ConsoleHandler,
    FileHandler,
    LogEntry,
    LoggerFSA,
    LoggerState,
    LogLevel,
    RemoteHandler,
)


class TestLogLevels:
    """Test log level functionality."""

    def test_log_level_filtering(self):
        """Test that logs below minimum level are filtered out."""
        output = StringIO()
        logger = LoggerFSA(name="test", level=LogLevel.WARNING, enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        # These should not appear
        logger.debug("debug message")
        logger.info("info message")

        # These should appear
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

        output_text = output.getvalue()
        assert "debug message" not in output_text
        assert "info message" not in output_text
        assert "warning message" in output_text
        assert "error message" in output_text
        assert "critical message" in output_text

    def test_all_log_levels(self):
        """Test all log level convenience methods."""
        output = StringIO()
        logger = LoggerFSA(name="test", level=LogLevel.DEBUG, enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")
        logger.critical("critical msg")

        output_text = output.getvalue()
        assert "[DEBUG]" in output_text
        assert "[INFO]" in output_text
        assert "[WARNING]" in output_text
        assert "[ERROR]" in output_text
        assert "[CRITICAL]" in output_text

    def test_set_level_dynamically(self):
        """Test changing log level dynamically."""
        output = StringIO()
        logger = LoggerFSA(name="test", level=LogLevel.INFO, enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.debug("should not appear")
        logger.info("should appear")

        # Change level to DEBUG
        logger.set_level(LogLevel.DEBUG)
        logger.debug("should now appear")

        output_text = output.getvalue()
        assert output_text.count("should not appear") == 0
        assert output_text.count("should appear") == 1
        assert output_text.count("should now appear") == 1


class TestContextInjection:
    """Test context management functionality."""

    def test_add_context(self):
        """Test adding persistent context."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.add_context("request_id", "req-123")
        logger.add_context("user_id", "user-456")
        logger.info("test message")

        output_text = output.getvalue()
        assert "request_id=req-123" in output_text
        assert "user_id=user-456" in output_text

    def test_clear_context(self):
        """Test clearing context."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.add_context("key1", "value1")
        logger.info("message1")

        logger.clear_context()
        logger.info("message2")

        output_text = output.getvalue()
        lines = output_text.strip().split("\n")
        assert "key1=value1" in lines[0]
        assert "key1=value1" not in lines[1]

    def test_context_stack_push_pop(self):
        """Test context stack push/pop operations."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.add_context("level1", "value1")
        logger.push_context()
        logger.add_context("level2", "value2")
        logger.info("nested message")

        logger.pop_context()
        logger.info("back to level1")

        output_text = output.getvalue()
        lines = output_text.strip().split("\n")

        # First message should have both contexts
        assert "level1=value1" in lines[0]
        assert "level2=value2" in lines[0]

        # Second message should only have level1
        assert "level1=value1" in lines[1]
        assert "level2=value2" not in lines[1]

    def test_inline_context(self):
        """Test adding context inline with log call."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.info("test message", user_id="user-789", action="login")

        output_text = output.getvalue()
        assert "user_id=user-789" in output_text
        assert "action=login" in output_text

    def test_merged_context(self):
        """Test that persistent and inline contexts are merged."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.add_context("persistent", "value1")
        logger.info("message", inline="value2")

        output_text = output.getvalue()
        assert "persistent=value1" in output_text
        assert "inline=value2" in output_text


class TestHandlers:
    """Test different log handlers."""

    def test_console_handler_text_format(self):
        """Test console handler with text format."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        logger.info("test message")

        output_text = output.getvalue()
        assert "[INFO]" in output_text
        assert "test message" in output_text
        assert "test:" in output_text  # logger name

    def test_console_handler_json_format(self):
        """Test console handler with JSON format."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "json", "stream": output})

        logger.info("test message", key="value")

        output_text = output.getvalue()
        log_entry = json.loads(output_text.strip())

        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "test message"
        assert log_entry["logger_name"] == "test"
        assert log_entry["context"]["key"] == "value"
        assert "timestamp" in log_entry

    def test_file_handler(self):
        """Test file handler writes to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = LoggerFSA(name="test", enable_auto_console=False)
            logger.configure_handler("file", {"filepath": str(log_file), "formatter": "text"})

            logger.info("test file message")
            logger.close()

            assert log_file.exists()
            content = log_file.read_text()
            assert "test file message" in content
            assert "[INFO]" in content

    def test_file_handler_json_format(self):
        """Test file handler with JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.json"
            logger = LoggerFSA(name="test", enable_auto_console=False)
            logger.configure_handler("file", {"filepath": str(log_file), "formatter": "json"})

            logger.info("json message", key="value")
            logger.close()

            content = log_file.read_text().strip()
            log_entry = json.loads(content)

            assert log_entry["level"] == "INFO"
            assert log_entry["message"] == "json message"

    def test_multiple_handlers(self):
        """Test logging to multiple handlers simultaneously."""
        output = StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = LoggerFSA(name="test", enable_auto_console=False)
            logger.configure_handler("console", {"formatter": "text", "stream": output})
            logger.configure_handler("file", {"filepath": str(log_file), "formatter": "text"})

            logger.info("multi-handler message")
            logger.close()

            # Check console output
            console_output = output.getvalue()
            assert "multi-handler message" in console_output

            # Check file output
            file_content = log_file.read_text()
            assert "multi-handler message" in file_content

    def test_remote_handler_with_callback(self):
        """Test remote handler with callback function."""
        captured_entries = []

        def capture_callback(entry: LogEntry):
            captured_entries.append(entry)

        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("remote", {"endpoint": "http://example.com", "callback": capture_callback})

        logger.info("remote message", key="value")

        assert len(captured_entries) == 1
        assert captured_entries[0].message == "remote message"
        assert captured_entries[0].context["key"] == "value"


class TestStateMachine:
    """Test FSA state transitions."""

    def test_initial_state(self):
        """Test logger starts in IDLE state."""
        logger = LoggerFSA(name="test")
        assert logger.state == LoggerState.IDLE

    def test_state_transitions_during_logging(self):
        """Test state transitions during log operation."""
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": StringIO()})

        # Before logging
        assert logger.state == LoggerState.IDLE

        # Log something
        logger.info("test")

        # Should return to IDLE after logging
        assert logger.state == LoggerState.IDLE

    def test_state_tracking_in_stats(self):
        """Test that state transitions are tracked in stats."""
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": StringIO()})

        logger.info("message 1")
        logger.info("message 2")

        stats = logger.get_stats()
        assert "logs_by_state" in stats
        # States visited: IDLE, LOGGING, FILTERING, WRITING, back to IDLE
        assert stats["logs_by_state"]["logging"] > 0
        assert stats["logs_by_state"]["filtering"] > 0
        assert stats["logs_by_state"]["writing"] > 0


class TestMetrics:
    """Test performance metrics and statistics."""

    def test_get_stats(self):
        """Test retrieving logging statistics."""
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": StringIO()})

        logger.info("message 1")
        logger.warning("message 2")
        logger.error("message 3")

        stats = logger.get_stats()

        assert stats["total_logs"] == 3
        assert stats["logs_by_level"]["INFO"] == 1
        assert stats["logs_by_level"]["WARNING"] == 1
        assert stats["logs_by_level"]["ERROR"] == 1
        assert "total_time_ms" in stats
        assert "avg_time_ms" in stats
        assert stats["avg_time_ms"] > 0

    def test_context_keys_tracked(self):
        """Test that context keys are tracked in stats."""
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": StringIO()})

        logger.add_context("key1", "value1")
        logger.info("message", key2="value2")

        stats = logger.get_stats()
        assert "key1" in stats["context_keys"]
        assert "key2" in stats["context_keys"]

    def test_performance_metrics(self):
        """Test that performance metrics are calculated."""
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": StringIO()})

        for i in range(10):
            logger.info(f"message {i}")

        stats = logger.get_stats()
        assert stats["total_logs"] == 10
        assert stats["total_time_ms"] >= 0
        assert stats["avg_time_ms"] >= 0
        # Check that average is approximately correct (accounting for rounding)
        # Note: values may be 0 if logging is extremely fast and rounds to 0.00
        if stats["total_time_ms"] > 0:
            expected_avg = round(stats["total_time_ms"] / stats["total_logs"], 2)
            assert abs(stats["avg_time_ms"] - expected_avg) < 0.01


class TestFiltering:
    """Test log filtering functionality."""

    def test_add_filter(self):
        """Test adding custom filter function."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        # Filter out messages containing "secret"
        logger.add_filter(lambda entry: "secret" not in entry.message.lower())

        logger.info("normal message")
        logger.info("secret message")
        logger.info("another normal message")

        output_text = output.getvalue()
        assert "normal message" in output_text
        assert "secret message" not in output_text
        assert "another normal message" in output_text

    def test_multiple_filters(self):
        """Test multiple filters are applied in sequence."""
        output = StringIO()
        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        # Filter 1: Only INFO level
        logger.add_filter(lambda entry: entry.level == "INFO")
        # Filter 2: Message must contain "important"
        logger.add_filter(lambda entry: "important" in entry.message.lower())

        logger.info("important message")  # Should pass
        logger.info("normal message")  # Should fail filter 2
        logger.warning("important warning")  # Should fail filter 1

        output_text = output.getvalue()
        assert output_text.count("important message") == 1
        assert "normal message" not in output_text
        assert "important warning" not in output_text


class TestErrorHandling:
    """Test error handling in logger."""

    def test_logger_continues_after_handler_error(self):
        """Test that logger continues if a handler fails."""
        output = StringIO()

        class FailingHandler:
            def emit(self, entry):
                raise RuntimeError("Handler failed")

        logger = LoggerFSA(name="test", enable_auto_console=False)
        logger._handlers.append(FailingHandler())
        logger.configure_handler("console", {"formatter": "text", "stream": output})

        # Should not raise exception
        logger.info("test message")

        # Console handler should still work
        assert "test message" in output.getvalue()

        # Error should be tracked
        stats = logger.get_stats()
        assert stats["errors"] > 0

    def test_invalid_handler_type(self):
        """Test that invalid handler type raises error."""
        logger = LoggerFSA(name="test")

        with pytest.raises(ValueError, match="Unknown handler type"):
            logger.configure_handler("invalid_type", {})

    def test_file_handler_missing_filepath(self):
        """Test that file handler requires filepath."""
        logger = LoggerFSA(name="test")

        with pytest.raises(ValueError, match="filepath"):
            logger.configure_handler("file", {"formatter": "json"})

    def test_remote_handler_missing_endpoint(self):
        """Test that remote handler requires endpoint."""
        logger = LoggerFSA(name="test")

        with pytest.raises(ValueError, match="endpoint"):
            logger.configure_handler("remote", {"formatter": "json"})


class TestLogEntry:
    """Test LogEntry dataclass."""

    def test_log_entry_to_dict(self):
        """Test converting log entry to dictionary."""
        entry = LogEntry(
            timestamp="2023-01-01T00:00:00",
            level="INFO",
            logger_name="test",
            message="test message",
            context={"key": "value"},
            state="logging",
            elapsed_ms=1.5,
        )

        entry_dict = entry.to_dict()
        assert entry_dict["timestamp"] == "2023-01-01T00:00:00"
        assert entry_dict["level"] == "INFO"
        assert entry_dict["logger_name"] == "test"
        assert entry_dict["message"] == "test message"
        assert entry_dict["context"]["key"] == "value"
        assert entry_dict["elapsed_ms"] == 1.5

    def test_log_entry_to_json(self):
        """Test converting log entry to JSON."""
        entry = LogEntry(
            timestamp="2023-01-01T00:00:00",
            level="INFO",
            logger_name="test",
            message="test message",
            context={},
            state="logging",
        )

        json_str = entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"

    def test_log_entry_to_text(self):
        """Test converting log entry to text."""
        entry = LogEntry(
            timestamp="2023-01-01T00:00:00",
            level="INFO",
            logger_name="test",
            message="test message",
            context={"key": "value"},
            state="logging",
            elapsed_ms=1.5,
        )

        text = entry.to_text()
        assert "2023-01-01T00:00:00" in text
        assert "[INFO]" in text
        assert "test:" in text
        assert "test message" in text
        assert "key=value" in text
        assert "(1.50ms)" in text

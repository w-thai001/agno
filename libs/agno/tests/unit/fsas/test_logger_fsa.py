"""
Comprehensive unit tests for Logger FSA.

This module contains 35 comprehensive tests covering all functionality
of the LoggerFSA including:
- State machine transitions
- Multi-level logging
- Handler management
- Formatters
- Async logging
- Buffering and batching
- PII masking
- Log sampling
- Metrics collection
- Audit logging
- Context management
- Log rotation
- Error handling
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from agno.fsas.infrastructure.logger_fsa import (
    LoggerFSA,
    LoggerState,
    LogLevel,
    HandlerType,
    FormatterType,
    RotationPolicy,
    SamplingStrategy,
    LoggerError,
    StateTransitionError,
    HandlerError,
    FormatterError,
    HandlerConfig,
    FormatterConfig,
    LogRecord,
    LogMetrics,
    PIIMask,
    PIIMasker,
    LogSampler,
    JSONFormatter,
    BufferedHandler,
    RemoteHTTPHandler,
    AuditLogger,
    AuditLogEntry,
    compress_log_file,
    create_rotating_handler,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_log_file():
    """Create a temporary log file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def temp_audit_file():
    """Create a temporary audit log file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.audit') as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def logger_fsa():
    """Create a LoggerFSA instance."""
    fsa = LoggerFSA(
        name="test_logger",
        level=LogLevel.DEBUG,
        enable_async=False,
        enable_metrics=True,
    )
    yield fsa
    # Cleanup
    fsa.shutdown()


@pytest.fixture
def async_logger_fsa():
    """Create an async LoggerFSA instance."""
    fsa = LoggerFSA(
        name="async_test_logger",
        level=LogLevel.DEBUG,
        enable_async=True,
        enable_metrics=True,
    )
    yield fsa
    # Cleanup
    fsa.shutdown()


# ============================================================================
# State Machine Tests
# ============================================================================

def test_initial_state():
    """Test 1: Logger FSA starts in correct state."""
    fsa = LoggerFSA(name="test")
    assert fsa.state == LoggerState.LOGGING
    fsa.shutdown()


def test_state_transition_to_flushing(logger_fsa):
    """Test 2: Valid state transition to FLUSHING."""
    logger_fsa.flush()
    # After flush, should return to LOGGING
    assert logger_fsa.state == LoggerState.LOGGING


def test_state_transition_to_rotating(logger_fsa):
    """Test 3: Valid state transition to ROTATING."""
    logger_fsa.rotate_logs()
    assert logger_fsa.state == LoggerState.LOGGING


def test_state_transition_to_shutdown(logger_fsa):
    """Test 4: Valid state transition to SHUTDOWN."""
    logger_fsa.shutdown()
    assert logger_fsa.state == LoggerState.IDLE


def test_invalid_state_transition():
    """Test 5: Invalid state transitions raise error."""
    fsa = LoggerFSA(name="test")
    # Manually set invalid state
    fsa.state = LoggerState.IDLE

    with pytest.raises(StateTransitionError):
        fsa.transition_to(LoggerState.ROTATING)

    fsa.shutdown()


# ============================================================================
# Log Level Tests
# ============================================================================

def test_debug_logging(logger_fsa, temp_log_file):
    """Test 6: Debug level logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.DEBUG,
    )
    logger_fsa.add_handler(config)

    logger_fsa.debug("Debug message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Debug message" in content
        assert "DEBUG" in content


def test_info_logging(logger_fsa, temp_log_file):
    """Test 7: Info level logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Info message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Info message" in content


def test_warning_logging(logger_fsa, temp_log_file):
    """Test 8: Warning level logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.WARNING,
    )
    logger_fsa.add_handler(config)

    logger_fsa.warning("Warning message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Warning message" in content


def test_error_logging(logger_fsa, temp_log_file):
    """Test 9: Error level logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.ERROR,
    )
    logger_fsa.add_handler(config)

    logger_fsa.error("Error message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Error message" in content


def test_critical_logging(logger_fsa, temp_log_file):
    """Test 10: Critical level logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.CRITICAL,
    )
    logger_fsa.add_handler(config)

    logger_fsa.critical("Critical message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Critical message" in content


def test_exception_logging(logger_fsa, temp_log_file):
    """Test 11: Exception logging with traceback."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.ERROR,
    )
    logger_fsa.add_handler(config)

    try:
        raise ValueError("Test exception")
    except ValueError:
        logger_fsa.exception("Exception occurred")

    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Exception occurred" in content
        assert "ValueError" in content or "Traceback" in content


# ============================================================================
# Handler Tests
# ============================================================================

def test_console_handler(logger_fsa):
    """Test 12: Console handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.CONSOLE,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers


def test_file_handler(logger_fsa, temp_log_file):
    """Test 13: File handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers

    logger_fsa.info("Test message")
    logger_fsa.flush()

    assert os.path.exists(temp_log_file)


def test_rotating_file_handler(logger_fsa, temp_log_file):
    """Test 14: Rotating file handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.ROTATING_FILE,
        filename=temp_log_file,
        max_bytes=1024,
        backup_count=3,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers


def test_timed_rotating_handler(logger_fsa, temp_log_file):
    """Test 15: Timed rotating file handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.TIMED_ROTATING_FILE,
        filename=temp_log_file,
        when='midnight',
        interval=1,
        backup_count=7,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers


def test_memory_handler(logger_fsa):
    """Test 16: Memory handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.MEMORY,
        buffer_size=100,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers


def test_null_handler(logger_fsa):
    """Test 17: Null handler creation."""
    config = HandlerConfig(
        handler_type=HandlerType.NULL,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers


def test_remove_handler(logger_fsa):
    """Test 18: Handler removal."""
    config = HandlerConfig(
        handler_type=HandlerType.CONSOLE,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)
    assert handler_id in logger_fsa.handlers

    logger_fsa.remove_handler(handler_id)
    assert handler_id not in logger_fsa.handlers


def test_multiple_handlers(logger_fsa, temp_log_file):
    """Test 19: Multiple handlers simultaneously."""
    # Add console handler
    config1 = HandlerConfig(
        handler_type=HandlerType.CONSOLE,
        level=LogLevel.INFO,
    )
    handler_id1 = logger_fsa.add_handler(config1)

    # Add file handler
    config2 = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.DEBUG,
    )
    handler_id2 = logger_fsa.add_handler(config2)

    assert len(logger_fsa.handlers) == 2

    logger_fsa.info("Test message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        assert "Test message" in f.read()


# ============================================================================
# Formatter Tests
# ============================================================================

def test_json_formatter(logger_fsa, temp_log_file):
    """Test 20: JSON formatter."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.JSON,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("JSON test message", extra={"key": "value"})
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        # Should be valid JSON
        log_entry = json.loads(content.strip())
        assert log_entry['message'] == "JSON test message"
        assert log_entry['level'] == "INFO"


def test_text_formatter(logger_fsa, temp_log_file):
    """Test 21: Text formatter."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.TEXT,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Text test message")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Text test message" in content
        assert "INFO" in content


def test_compact_formatter(logger_fsa, temp_log_file):
    """Test 22: Compact formatter."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.COMPACT,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Compact test")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Compact test" in content


# ============================================================================
# Context Management Tests
# ============================================================================

def test_set_context(logger_fsa, temp_log_file):
    """Test 23: Setting logging context."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.JSON,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.set_context(request_id="123", user_id="user1")
    logger_fsa.info("Context test")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = json.loads(f.read().strip())
        assert 'extra' in content or 'request_id' in str(content)


def test_context_manager(logger_fsa, temp_log_file):
    """Test 24: Context manager for temporary context."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    with logger_fsa.context_manager(temp_id="temp123"):
        logger_fsa.info("Inside context")

    logger_fsa.info("Outside context")
    logger_fsa.flush()

    # Context should be cleared after exiting context manager
    assert 'temp_id' not in logger_fsa.context


def test_clear_context(logger_fsa):
    """Test 25: Clearing logging context."""
    logger_fsa.set_context(key1="value1", key2="value2")
    assert len(logger_fsa.context) == 2

    logger_fsa.clear_context()
    assert len(logger_fsa.context) == 0


# ============================================================================
# Metrics Tests
# ============================================================================

def test_metrics_collection(logger_fsa):
    """Test 26: Metrics collection."""
    config = HandlerConfig(
        handler_type=HandlerType.NULL,
        level=LogLevel.DEBUG,
    )
    logger_fsa.add_handler(config)

    logger_fsa.debug("Debug")
    logger_fsa.info("Info")
    logger_fsa.warning("Warning")
    logger_fsa.error("Error")
    logger_fsa.critical("Critical")

    metrics = logger_fsa.get_metrics()
    assert metrics['total_logs'] == 5
    assert metrics['errors'] == 1
    assert metrics['warnings'] == 1
    assert metrics['criticals'] == 1


def test_metrics_by_level(logger_fsa):
    """Test 27: Metrics by log level."""
    config = HandlerConfig(
        handler_type=HandlerType.NULL,
        level=LogLevel.DEBUG,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Info 1")
    logger_fsa.info("Info 2")
    logger_fsa.error("Error 1")

    metrics = logger_fsa.get_metrics()
    assert metrics['logs_by_level']['INFO'] == 2
    assert metrics['logs_by_level']['ERROR'] == 1


# ============================================================================
# PII Masking Tests
# ============================================================================

def test_pii_masker_email():
    """Test 28: PII masking for emails."""
    masker = PIIMasker()
    text = "Contact me at john.doe@example.com"
    masked = masker._mask_string(text)

    assert "john.doe@example.com" not in masked
    assert "@example.com" in masked  # Domain preserved


def test_pii_masker_phone():
    """Test 29: PII masking for phone numbers."""
    masker = PIIMasker()
    text = "Call me at 555-123-4567"
    masked = masker._mask_string(text)

    assert "555-123-4567" not in masked
    assert "XXX-XXX-XXXX" in masked


def test_pii_masker_ssn():
    """Test 30: PII masking for SSN."""
    masker = PIIMasker()
    text = "SSN: 123-45-6789"
    masked = masker._mask_string(text)

    assert "123-45-6789" not in masked
    assert "XXX-XX-XXXX" in masked


def test_pii_masker_credit_card():
    """Test 31: PII masking for credit cards."""
    masker = PIIMasker()
    text = "Card: 4532-1234-5678-9010"
    masked = masker._mask_string(text)

    assert "4532-1234-5678" not in masked
    assert "9010" in masked  # Last 4 digits preserved


def test_pii_masking_in_logger(temp_log_file):
    """Test 32: PII masking in logger."""
    fsa = LoggerFSA(
        name="pii_test",
        enable_pii_masking=True,
    )

    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    fsa.add_handler(config)

    fsa.info("Email: test@example.com, Phone: 555-1234")
    fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "test@example.com" not in content
        assert "555-1234" not in content

    fsa.shutdown()


# ============================================================================
# Log Sampling Tests
# ============================================================================

def test_sampler_none_strategy():
    """Test 33: Sampler with NONE strategy (all logs pass)."""
    sampler = LogSampler(strategy=SamplingStrategy.NONE)

    record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.INFO,
        message="Test",
        logger_name="test",
        module="test",
        function="test",
        line_number=1,
        thread_id=1,
        thread_name="main",
        process_id=1,
    )

    assert sampler.should_log(record) is True


def test_sampler_random_strategy():
    """Test 34: Sampler with RANDOM strategy."""
    sampler = LogSampler(
        strategy=SamplingStrategy.RANDOM,
        sample_rate=0.5
    )

    record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.INFO,
        message="Test",
        logger_name="test",
        module="test",
        function="test",
        line_number=1,
        thread_id=1,
        thread_name="main",
        process_id=1,
    )

    # Run multiple times to test randomness
    results = [sampler.should_log(record) for _ in range(100)]
    # Should have some True and some False
    assert True in results
    assert False in results


def test_sampler_priority_strategy():
    """Test 35: Sampler with PRIORITY strategy (always logs errors)."""
    sampler = LogSampler(
        strategy=SamplingStrategy.PRIORITY,
        sample_rate=0.0  # 0% sampling for non-critical
    )

    error_record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.ERROR,
        message="Error",
        logger_name="test",
        module="test",
        function="test",
        line_number=1,
        thread_id=1,
        thread_name="main",
        process_id=1,
    )

    info_record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.INFO,
        message="Info",
        logger_name="test",
        module="test",
        function="test",
        line_number=1,
        thread_id=1,
        thread_name="main",
        process_id=1,
    )

    # Error should always pass
    assert sampler.should_log(error_record) is True


def test_sampler_rate_limit():
    """Test 36: Sampler with rate limiting."""
    sampler = LogSampler(
        strategy=SamplingStrategy.RATE_LIMIT,
        rate_limit=5,
        window_seconds=1
    )

    record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.INFO,
        message="Test",
        logger_name="test",
        module="test",
        function="test",
        line_number=1,
        thread_id=1,
        thread_name="main",
        process_id=1,
    )

    # First 5 should pass
    for i in range(5):
        assert sampler.should_log(record) is True

    # 6th should be rejected
    assert sampler.should_log(record) is False


# ============================================================================
# Async Logging Tests
# ============================================================================

def test_async_logging_enabled(async_logger_fsa):
    """Test 37: Async logging is enabled."""
    assert async_logger_fsa.enable_async is True
    assert async_logger_fsa.async_queue is not None
    assert async_logger_fsa.async_thread is not None


def test_async_logging_messages(async_logger_fsa, temp_log_file):
    """Test 38: Async logging of messages."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    async_logger_fsa.add_handler(config)

    async_logger_fsa.info("Async message 1")
    async_logger_fsa.info("Async message 2")

    # Give async thread time to process
    time.sleep(0.5)
    async_logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "Async message 1" in content
        assert "Async message 2" in content


# ============================================================================
# Audit Logging Tests
# ============================================================================

def test_audit_logger_creation(temp_audit_file):
    """Test 39: Audit logger creation."""
    audit_logger = AuditLogger(
        secret_key="test_secret",
        log_file=temp_audit_file
    )
    assert audit_logger is not None


def test_audit_log_entry(temp_audit_file):
    """Test 40: Audit log entry creation."""
    audit_logger = AuditLogger(
        secret_key="test_secret",
        log_file=temp_audit_file
    )

    entry = audit_logger.log_event(
        event_type="user_action",
        actor="user123",
        action="login",
        resource="system",
        result="success",
        details={"ip": "192.168.1.1"}
    )

    assert entry.event_type == "user_action"
    assert entry.actor == "user123"
    assert entry.signature is not None
    assert entry.entry_hash is not None


def test_audit_chain_verification(temp_audit_file):
    """Test 41: Audit log chain verification."""
    audit_logger = AuditLogger(
        secret_key="test_secret",
        log_file=temp_audit_file
    )

    # Log multiple events
    audit_logger.log_event("event1", "user1", "action1", "res1", "success")
    audit_logger.log_event("event2", "user2", "action2", "res2", "success")
    audit_logger.log_event("event3", "user3", "action3", "res3", "success")

    # Verify chain
    is_valid, errors = audit_logger.verify_chain()
    assert is_valid is True
    assert len(errors) == 0


def test_audit_logging_in_fsa(logger_fsa, temp_audit_file):
    """Test 42: Audit logging integration in FSA."""
    logger_fsa.enable_audit_logging(
        secret_key="test_secret",
        log_file=temp_audit_file
    )

    logger_fsa.audit(
        event_type="config_change",
        actor="admin",
        action="update_setting",
        resource="logger_config",
        result="success",
        details={"setting": "log_level", "value": "DEBUG"}
    )

    assert os.path.exists(temp_audit_file)


# ============================================================================
# Buffering Tests
# ============================================================================

def test_buffered_handler():
    """Test 43: Buffered handler functionality."""
    target_handler = logging.handlers.MemoryHandler(capacity=100)
    buffered = BufferedHandler(
        target_handler,
        buffer_size=5,
        flush_interval=10.0
    )

    # Create log records
    for i in range(3):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Message {i}",
            args=(),
            exc_info=None
        )
        buffered.emit(record)

    # Buffer should have 3 records
    assert len(buffered.buffer) == 3


# ============================================================================
# Log Rotation Tests
# ============================================================================

def test_manual_log_rotation(logger_fsa, temp_log_file):
    """Test 44: Manual log rotation trigger."""
    config = HandlerConfig(
        handler_type=HandlerType.ROTATING_FILE,
        filename=temp_log_file,
        max_bytes=1024,
        backup_count=3,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Before rotation")
    logger_fsa.rotate_logs()
    logger_fsa.info("After rotation")
    logger_fsa.flush()

    metrics = logger_fsa.get_metrics()
    assert metrics['rotations'] >= 1


# ============================================================================
# Utility Function Tests
# ============================================================================

def test_compress_log_file(temp_log_file):
    """Test 45: Log file compression."""
    # Write some content
    with open(temp_log_file, 'w') as f:
        f.write("Test log content\n" * 100)

    compressed_file = compress_log_file(temp_log_file, delete_original=True)

    assert compressed_file.endswith('.gz')
    assert os.path.exists(compressed_file)
    assert not os.path.exists(temp_log_file)  # Original should be deleted

    # Cleanup
    os.unlink(compressed_file)


def test_create_rotating_handler_utility(temp_log_file):
    """Test 46: Create rotating handler utility function."""
    handler = create_rotating_handler(
        filename=temp_log_file,
        max_bytes=1024,
        backup_count=3,
        compress=False
    )

    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert handler.maxBytes == 1024
    assert handler.backupCount == 3


# ============================================================================
# Thread Safety Tests
# ============================================================================

def test_concurrent_logging(logger_fsa, temp_log_file):
    """Test 47: Thread-safe concurrent logging."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    def log_messages(thread_id):
        for i in range(10):
            logger_fsa.info(f"Thread {thread_id} message {i}")

    threads = []
    for i in range(5):
        thread = threading.Thread(target=log_messages, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logger_fsa.flush()

    # Should have 50 log messages total
    with open(temp_log_file, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 50


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_logging_with_empty_message(logger_fsa, temp_log_file):
    """Test 48: Logging empty message."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("")
    logger_fsa.flush()

    assert os.path.exists(temp_log_file)


def test_logging_with_special_characters(logger_fsa, temp_log_file):
    """Test 49: Logging with special characters."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
        encoding='utf-8',
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Special chars: émojis 🎉 unicode ñ")
    logger_fsa.flush()

    with open(temp_log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Special chars" in content


def test_logging_large_message(logger_fsa, temp_log_file):
    """Test 50: Logging very large message."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    large_message = "X" * 10000
    logger_fsa.info(large_message)
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = f.read()
        assert "X" * 100 in content  # Check partial match


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_logging_workflow(logger_fsa, temp_log_file, temp_audit_file):
    """Test 51: Complete logging workflow integration."""
    # Setup handlers
    file_config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.JSON,
        level=LogLevel.DEBUG,
    )
    logger_fsa.add_handler(file_config)

    # Enable audit logging
    logger_fsa.enable_audit_logging("secret", temp_audit_file)

    # Set context
    logger_fsa.set_context(session_id="sess123", user_id="user456")

    # Log various levels
    logger_fsa.debug("Debug info")
    logger_fsa.info("Info message")
    logger_fsa.warning("Warning message")
    logger_fsa.error("Error message")

    # Log audit event
    logger_fsa.audit(
        event_type="test",
        actor="test_user",
        action="test_action",
        resource="test_resource",
        result="success"
    )

    # Flush and check
    logger_fsa.flush()

    # Verify logs
    assert os.path.exists(temp_log_file)
    assert os.path.exists(temp_audit_file)

    # Check metrics
    metrics = logger_fsa.get_metrics()
    assert metrics['total_logs'] == 4


def test_correlation_id_tracking(logger_fsa, temp_log_file):
    """Test 52: Correlation ID tracking across logs."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        formatter_type=FormatterType.JSON,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    # Correlation ID should be set
    assert logger_fsa.correlation_id is not None

    logger_fsa.info("Message with correlation ID")
    logger_fsa.flush()

    with open(temp_log_file, 'r') as f:
        content = json.loads(f.read().strip())
        assert 'correlation_id' in content


def test_module_level_configuration(logger_fsa):
    """Test 53: Module-specific log level configuration."""
    logger_fsa.set_module_level("module1", LogLevel.DEBUG)
    logger_fsa.set_module_level("module2", LogLevel.ERROR)

    assert logger_fsa.module_levels["module1"] == LogLevel.DEBUG
    assert logger_fsa.module_levels["module2"] == LogLevel.ERROR


def test_log_record_creation(logger_fsa):
    """Test 54: Log record creation with metadata."""
    record = logger_fsa._create_log_record(
        level=LogLevel.INFO,
        message="Test message",
        extra={"key": "value"}
    )

    assert record.level == LogLevel.INFO
    assert record.message == "Test message"
    assert record.extra["key"] == "value"
    assert record.correlation_id == logger_fsa.correlation_id


def test_log_record_to_json():
    """Test 55: Log record JSON serialization."""
    record = LogRecord(
        timestamp=time.time(),
        level=LogLevel.INFO,
        message="Test",
        logger_name="test",
        module="test_module",
        function="test_func",
        line_number=42,
        thread_id=12345,
        thread_name="MainThread",
        process_id=9999,
        correlation_id="corr-123",
    )

    json_str = record.to_json()
    parsed = json.loads(json_str)

    assert parsed['level'] == "INFO"
    assert parsed['message'] == "Test"
    assert parsed['correlation_id'] == "corr-123"


def test_metrics_dict_conversion():
    """Test 56: Metrics dictionary conversion."""
    metrics = LogMetrics(logger_name="test")
    metrics.total_logs = 100
    metrics.errors = 5
    metrics.logs_by_level[LogLevel.INFO] = 50
    metrics.logs_by_level[LogLevel.ERROR] = 5

    metrics_dict = metrics.to_dict()

    assert metrics_dict['total_logs'] == 100
    assert metrics_dict['errors'] == 5
    assert 'INFO' in metrics_dict['logs_by_level']


def test_shutdown_cleanup(logger_fsa, temp_log_file):
    """Test 57: Proper cleanup on shutdown."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    handler_id = logger_fsa.add_handler(config)

    logger_fsa.info("Before shutdown")
    logger_fsa.shutdown()

    # After shutdown, state should be IDLE
    assert logger_fsa.state == LoggerState.IDLE

    # Handlers should be cleaned up
    assert len(logger_fsa.logger.handlers) == 0


def test_flush_operation(logger_fsa, temp_log_file):
    """Test 58: Flush operation."""
    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
        buffer_size=10,
    )
    logger_fsa.add_handler(config)

    logger_fsa.info("Message 1")
    logger_fsa.info("Message 2")
    logger_fsa.flush()

    metrics = logger_fsa.get_metrics()
    assert metrics['flushes'] >= 1


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_handler_error_missing_filename():
    """Test 59: Handler error when filename is missing."""
    fsa = LoggerFSA(name="test")

    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        # Missing filename
        level=LogLevel.INFO,
    )

    with pytest.raises(HandlerError):
        fsa.add_handler(config)

    fsa.shutdown()


def test_handler_error_missing_url():
    """Test 60: Handler error when URL is missing for remote handler."""
    fsa = LoggerFSA(name="test")

    config = HandlerConfig(
        handler_type=HandlerType.REMOTE_HTTP,
        # Missing URL
        level=LogLevel.INFO,
    )

    with pytest.raises(HandlerError):
        fsa.add_handler(config)

    fsa.shutdown()


# ============================================================================
# Performance Tests
# ============================================================================

def test_high_volume_logging(logger_fsa):
    """Test 61: High volume logging performance."""
    config = HandlerConfig(
        handler_type=HandlerType.NULL,
        level=LogLevel.INFO,
    )
    logger_fsa.add_handler(config)

    start_time = time.time()

    # Log 1000 messages
    for i in range(1000):
        logger_fsa.info(f"Message {i}")

    elapsed = time.time() - start_time

    # Should complete reasonably fast (under 2 seconds)
    assert elapsed < 2.0

    metrics = logger_fsa.get_metrics()
    assert metrics['total_logs'] == 1000


def test_sampling_reduces_volume(temp_log_file):
    """Test 62: Sampling reduces log volume."""
    # Logger with sampling enabled
    fsa = LoggerFSA(
        name="sampling_test",
        enable_sampling=True,
    )

    # Set very low sample rate
    fsa.sampler = LogSampler(
        strategy=SamplingStrategy.RANDOM,
        sample_rate=0.1  # 10% sampling
    )

    config = HandlerConfig(
        handler_type=HandlerType.FILE,
        filename=temp_log_file,
        level=LogLevel.INFO,
    )
    fsa.add_handler(config)

    # Log 100 messages
    for i in range(100):
        fsa.info(f"Message {i}")

    fsa.flush()

    # Count logged messages
    with open(temp_log_file, 'r') as f:
        lines = f.readlines()

    # Should be significantly less than 100 (approximately 10)
    assert len(lines) < 50

    fsa.shutdown()

"""Unit tests for CommandPatternFSA."""

import pytest
import time
from datetime import datetime, timedelta

from agno.fsas.command_pattern_fsa import (
    CommandPatternFSA,
    Command,
    CommandConfig,
    CommandStatus,
    CommandPriority,
    TransactionStatus,
    SetValueCommand,
    DeleteKeyCommand,
    AppendCommand,
    CommandOp,
    CommandResult,
    ValidationResult,
    ExecuteResult,
    UndoResult,
    RedoResult,
    PushResult,
    ClearResult,
    CommandHistory,
    EnqueueResult,
    QueueExecuteResult,
    MacroCommand,
    MacroExecuteResult,
    MacroUndoResult,
    ScheduleResult,
    CancelResult,
    Transaction,
    CommitResult,
    RollbackResult,
    CloneResult,
)


# ==================== Mock Commands ====================

class MockCommand(Command):
    """Mock command for testing."""

    def __init__(self, should_fail=False):
        super().__init__()
        self.should_fail = should_fail
        self.executed_count = 0
        self.undone_count = 0

    def execute(self) -> bool:
        """Execute the command."""
        self.executed_count += 1
        if self.should_fail:
            self.error = "Mock execution failed"
            self.status = CommandStatus.FAILED
            return False
        self.status = CommandStatus.EXECUTED
        self.executed_at = datetime.now()
        return True

    def undo(self) -> bool:
        """Undo the command."""
        self.undone_count += 1
        if self.should_fail:
            self.error = "Mock undo failed"
            return False
        self.status = CommandStatus.UNDONE
        self.undone_at = datetime.now()
        return True


class NonUndoableCommand(Command):
    """Command that cannot be undone."""

    def __init__(self):
        super().__init__()
        self.can_undo_flag = False

    def execute(self) -> bool:
        """Execute the command."""
        self.status = CommandStatus.EXECUTED
        self.executed_at = datetime.now()
        return True

    def undo(self) -> bool:
        """Undo (not supported)."""
        return False


# ==================== Fixtures ====================

@pytest.fixture
def command_pattern():
    """Create command pattern instance."""
    config = CommandConfig()
    return CommandPatternFSA(config)


@pytest.fixture
def configured_pattern():
    """Create pre-configured command pattern."""
    config = CommandConfig(
        enable_undo=True,
        enable_redo=True,
        enable_queue=True,
        enable_scheduling=True,
        enable_transactions=True,
        thread_safe=True,
    )
    return CommandPatternFSA(config)


@pytest.fixture
def test_data():
    """Create test data dictionary."""
    return {}


@pytest.fixture
def test_list():
    """Create test list."""
    return []


# ==================== Test Classes ====================

class TestCommandPatternBasics:
    """Test basic command pattern functionality."""

    def test_initialization(self):
        """Test command pattern initialization."""
        config = CommandConfig()
        pattern = CommandPatternFSA(config)
        assert pattern.config == config
        assert pattern.fsa_id is not None

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = CommandConfig(
            enable_undo=False,
            enable_redo=False,
        )
        pattern = CommandPatternFSA(config)
        assert pattern.config.enable_undo is False
        assert pattern.config.enable_redo is False

    def test_validation_success(self, command_pattern):
        """Test successful configuration validation."""
        config = CommandConfig(max_undo_stack_size=500)
        result = command_pattern.validate(config)
        assert result.valid is True

    def test_validation_failure(self, command_pattern):
        """Test configuration validation failure."""
        config = CommandConfig(max_undo_stack_size=-1)
        result = command_pattern.validate(config)
        assert result.valid is False
        assert len(result.errors) > 0


class TestCommandCreation:
    """Test command creation."""

    def test_create_command(self, command_pattern, test_data):
        """Test creating a command."""
        command = command_pattern.create_command(
            "set_value",
            {"target": test_data, "key": "test", "value": 42}
        )
        assert command is not None
        assert isinstance(command, SetValueCommand)

    def test_create_command_unknown_type(self, command_pattern):
        """Test creating unknown command type."""
        command = command_pattern.create_command("unknown", {})
        assert command is None

    def test_create_delete_command(self, command_pattern, test_data):
        """Test creating delete command."""
        test_data["key"] = "value"
        command = command_pattern.create_command(
            "delete_key",
            {"target": test_data, "key": "key"}
        )
        assert command is not None
        assert isinstance(command, DeleteKeyCommand)

    def test_create_append_command(self, command_pattern, test_list):
        """Test creating append command."""
        command = command_pattern.create_command(
            "append",
            {"target": test_list, "value": "item"}
        )
        assert command is not None
        assert isinstance(command, AppendCommand)


class TestCommandExecution:
    """Test command execution."""

    def test_execute_command(self, command_pattern):
        """Test executing a command."""
        command = MockCommand()
        result = command_pattern.execute_command(command)
        assert result.executed is True
        assert command.executed_count == 1

    def test_execute_failing_command(self, command_pattern):
        """Test executing failing command."""
        command = MockCommand(should_fail=True)
        result = command_pattern.execute_command(command)
        assert result.executed is False
        assert result.error is not None

    def test_execute_set_value_command(self, command_pattern, test_data):
        """Test executing set value command."""
        command = SetValueCommand(test_data, "key", "value")
        result = command_pattern.execute_command(command)
        assert result.executed is True
        assert test_data["key"] == "value"


class TestCommandUndo:
    """Test command undo."""

    def test_undo_command(self, command_pattern):
        """Test undoing a command."""
        command = MockCommand()
        command_pattern.execute_command(command)

        result = command_pattern.undo_command(command)
        assert result.undone is True
        assert command.undone_count == 1

    def test_undo_disabled(self):
        """Test undo when disabled."""
        config = CommandConfig(enable_undo=False)
        pattern = CommandPatternFSA(config)

        command = MockCommand()
        pattern.execute_command(command)

        result = pattern.undo_command(command)
        assert result.undone is False

    def test_undo_set_value_command(self, command_pattern, test_data):
        """Test undoing set value command."""
        command = SetValueCommand(test_data, "key", "value")
        command_pattern.execute_command(command)

        command_pattern.undo_command(command)
        assert "key" not in test_data


class TestCommandRedo:
    """Test command redo."""

    def test_redo_command(self, command_pattern):
        """Test redoing a command."""
        command = MockCommand()
        command_pattern.execute_command(command)
        command_pattern.undo_command(command)

        result = command_pattern.redo_command(command)
        assert result.redone is True

    def test_redo_disabled(self):
        """Test redo when disabled."""
        config = CommandConfig(enable_redo=False)
        pattern = CommandPatternFSA(config)

        command = MockCommand()
        pattern.execute_command(command)
        pattern.undo_command(command)

        result = pattern.redo_command(command)
        assert result.redone is False


class TestUndoCapability:
    """Test undo capability checking."""

    def test_can_undo(self, command_pattern):
        """Test checking if command can be undone."""
        command = MockCommand()
        command_pattern.execute_command(command)

        assert command_pattern.can_undo(command) is True

    def test_cannot_undo_non_undoable(self, command_pattern):
        """Test non-undoable command."""
        command = NonUndoableCommand()
        command_pattern.execute_command(command)

        assert command_pattern.can_undo(command) is False


class TestRedoCapability:
    """Test redo capability checking."""

    def test_can_redo(self, command_pattern):
        """Test checking if command can be redone."""
        command = MockCommand()
        command_pattern.execute_command(command)
        command_pattern.undo_command(command)

        assert command_pattern.can_redo(command) is True

    def test_cannot_redo_executed(self, command_pattern):
        """Test cannot redo executed command."""
        command = MockCommand()
        command_pattern.execute_command(command)

        assert command_pattern.can_redo(command) is False


class TestUndoStack:
    """Test undo stack operations."""

    def test_push_undo_stack(self, command_pattern):
        """Test pushing to undo stack."""
        command = MockCommand()
        result = command_pattern.push_undo_stack(command)
        assert result.pushed is True
        assert result.stack_size > 0

    def test_pop_undo_stack(self, command_pattern):
        """Test popping from undo stack."""
        command = MockCommand()
        command_pattern.push_undo_stack(command)

        popped = command_pattern.pop_undo_stack()
        assert popped == command

    def test_pop_empty_undo_stack(self, command_pattern):
        """Test popping from empty undo stack."""
        command = command_pattern.pop_undo_stack()
        assert command is None


class TestRedoStack:
    """Test redo stack operations."""

    def test_push_redo_stack(self, command_pattern):
        """Test pushing to redo stack."""
        command = MockCommand()
        result = command_pattern.push_redo_stack(command)
        assert result.pushed is True
        assert result.stack_size > 0

    def test_pop_redo_stack(self, command_pattern):
        """Test popping from redo stack."""
        command = MockCommand()
        command_pattern.push_redo_stack(command)

        popped = command_pattern.pop_redo_stack()
        assert popped == command

    def test_pop_empty_redo_stack(self, command_pattern):
        """Test popping from empty redo stack."""
        command = command_pattern.pop_redo_stack()
        assert command is None


class TestStackClearing:
    """Test stack clearing."""

    def test_clear_undo_stack(self, command_pattern):
        """Test clearing undo stack."""
        command = MockCommand()
        command_pattern.push_undo_stack(command)

        result = command_pattern.clear_undo_stack()
        assert result.cleared is True
        assert result.cleared_count > 0

    def test_clear_redo_stack(self, command_pattern):
        """Test clearing redo stack."""
        command = MockCommand()
        command_pattern.push_redo_stack(command)

        result = command_pattern.clear_redo_stack()
        assert result.cleared is True
        assert result.cleared_count > 0


class TestHistoryRetrieval:
    """Test history retrieval."""

    def test_get_command_history(self, command_pattern):
        """Test getting command history."""
        command = MockCommand()
        command_pattern.execute_command(command)

        history = command_pattern.get_command_history()
        assert isinstance(history, CommandHistory)
        assert len(history.commands) > 0

    def test_get_history_with_limit(self, command_pattern):
        """Test getting history with limit."""
        for _ in range(5):
            command = MockCommand()
            command_pattern.execute_command(command)

        history = command_pattern.get_command_history(limit=2)
        assert len(history.commands) == 2


class TestCommandEnqueue:
    """Test command enqueueing."""

    def test_enqueue_command(self, command_pattern):
        """Test enqueueing a command."""
        command = MockCommand()
        result = command_pattern.enqueue_command(command)
        assert result.enqueued is True

    def test_enqueue_with_priority(self, command_pattern):
        """Test enqueueing with priority."""
        command = MockCommand()
        result = command_pattern.enqueue_command(
            command,
            CommandPriority.HIGH.value
        )
        assert result.enqueued is True

    def test_enqueue_disabled(self):
        """Test enqueue when disabled."""
        config = CommandConfig(enable_queue=False)
        pattern = CommandPatternFSA(config)

        command = MockCommand()
        result = pattern.enqueue_command(command)
        assert result.enqueued is False


class TestCommandDequeue:
    """Test command dequeueing."""

    def test_dequeue_command(self, command_pattern):
        """Test dequeueing a command."""
        command = MockCommand()
        command_pattern.enqueue_command(command)

        dequeued = command_pattern.dequeue_command()
        assert dequeued == command

    def test_dequeue_empty_queue(self, command_pattern):
        """Test dequeueing from empty queue."""
        command = command_pattern.dequeue_command()
        assert command is None


class TestQueueExecution:
    """Test queue execution."""

    def test_execute_queue(self, command_pattern):
        """Test executing command queue."""
        for _ in range(3):
            command = MockCommand()
            command_pattern.enqueue_command(command)

        result = command_pattern.execute_queue()
        assert result.executed is True
        assert result.commands_executed == 3

    def test_execute_queue_with_limit(self, command_pattern):
        """Test executing queue with limit."""
        for _ in range(5):
            command = MockCommand()
            command_pattern.enqueue_command(command)

        result = command_pattern.execute_queue(max_commands=2)
        assert result.commands_executed == 2


class TestMacroCreation:
    """Test macro command creation."""

    def test_create_macro_command(self, command_pattern):
        """Test creating a macro command."""
        commands = [MockCommand(), MockCommand()]
        macro = command_pattern.create_macro_command(commands, "test_macro")
        assert macro is not None
        assert macro.name == "test_macro"
        assert len(macro.commands) == 2


class TestMacroExecution:
    """Test macro execution."""

    def test_execute_macro(self, command_pattern):
        """Test executing a macro command."""
        commands = [MockCommand(), MockCommand()]
        macro = command_pattern.create_macro_command(commands, "test_macro")

        result = command_pattern.execute_macro(macro)
        assert result.executed is True
        assert result.commands_executed == 2

    def test_execute_macro_with_failure(self, command_pattern):
        """Test executing macro with failing command."""
        commands = [MockCommand(), MockCommand(should_fail=True)]
        macro = command_pattern.create_macro_command(commands, "test_macro")

        result = command_pattern.execute_macro(macro)
        assert result.executed is False
        assert len(result.errors) > 0


class TestMacroUndo:
    """Test macro undo."""

    def test_undo_macro(self, command_pattern):
        """Test undoing a macro command."""
        commands = [MockCommand(), MockCommand()]
        macro = command_pattern.create_macro_command(commands, "test_macro")
        command_pattern.execute_macro(macro)

        result = command_pattern.undo_macro(macro)
        assert result.undone is True
        assert result.commands_undone == 2

    def test_undo_unexecuted_macro(self, command_pattern):
        """Test undoing unexecuted macro."""
        commands = [MockCommand()]
        macro = command_pattern.create_macro_command(commands, "test_macro")

        result = command_pattern.undo_macro(macro)
        assert result.undone is False


class TestCommandScheduling:
    """Test command scheduling."""

    def test_schedule_command(self, command_pattern):
        """Test scheduling a command."""
        command = MockCommand()
        execute_time = datetime.now() + timedelta(seconds=1)

        result = command_pattern.schedule_command(command, execute_time)
        assert result.scheduled is True
        assert result.schedule_id != ""

    def test_schedule_disabled(self):
        """Test scheduling when disabled."""
        config = CommandConfig(enable_scheduling=False)
        pattern = CommandPatternFSA(config)

        command = MockCommand()
        execute_time = datetime.now() + timedelta(seconds=1)

        result = pattern.schedule_command(command, execute_time)
        assert result.scheduled is False


class TestScheduledCancellation:
    """Test scheduled command cancellation."""

    def test_cancel_scheduled_command(self, command_pattern):
        """Test cancelling a scheduled command."""
        command = MockCommand()
        execute_time = datetime.now() + timedelta(seconds=5)

        schedule_result = command_pattern.schedule_command(command, execute_time)
        cancel_result = command_pattern.cancel_scheduled_command(
            schedule_result.schedule_id
        )

        assert cancel_result.cancelled is True

    def test_cancel_nonexistent_schedule(self, command_pattern):
        """Test cancelling non-existent schedule."""
        result = command_pattern.cancel_scheduled_command("nonexistent")
        assert result.cancelled is False


class TestTransactionBegin:
    """Test transaction begin."""

    def test_begin_transaction(self, command_pattern):
        """Test beginning a transaction."""
        transaction = command_pattern.begin_transaction()
        assert transaction is not None
        assert transaction.status == TransactionStatus.ACTIVE


class TestTransactionCommit:
    """Test transaction commit."""

    def test_commit_transaction(self, command_pattern, test_data):
        """Test committing a transaction."""
        transaction = command_pattern.begin_transaction()

        command = SetValueCommand(test_data, "key", "value")
        command_pattern.execute_command(command)

        result = command_pattern.commit_transaction(transaction)
        assert result.committed is True
        assert test_data["key"] == "value"

    def test_commit_disabled(self):
        """Test commit when transactions disabled."""
        config = CommandConfig(enable_transactions=False)
        pattern = CommandPatternFSA(config)

        transaction = Transaction()
        result = pattern.commit_transaction(transaction)
        assert result.committed is False


class TestTransactionRollback:
    """Test transaction rollback."""

    def test_rollback_transaction(self, command_pattern, test_data):
        """Test rolling back a transaction."""
        transaction = command_pattern.begin_transaction()

        command = SetValueCommand(test_data, "key", "value")
        command_pattern.execute_command(command)

        result = command_pattern.rollback_transaction(transaction)
        assert result.rolled_back is True
        assert "key" not in test_data

    def test_rollback_with_multiple_commands(self, command_pattern, test_data):
        """Test rollback with multiple commands."""
        transaction = command_pattern.begin_transaction()

        cmd1 = SetValueCommand(test_data, "key1", "value1")
        cmd2 = SetValueCommand(test_data, "key2", "value2")

        command_pattern.execute_command(cmd1)
        command_pattern.execute_command(cmd2)

        result = command_pattern.rollback_transaction(transaction)
        assert result.rolled_back is True
        assert "key1" not in test_data
        assert "key2" not in test_data


class TestCommandSerialization:
    """Test command serialization."""

    def test_serialize_command(self, command_pattern, test_data):
        """Test serializing a command."""
        command = SetValueCommand(test_data, "key", "value")
        data = command_pattern.serialize_command(command)
        assert data is not None
        assert isinstance(data, bytes)

    def test_serialize_disabled(self):
        """Test serialization when disabled."""
        config = CommandConfig(enable_serialization=False)
        pattern = CommandPatternFSA(config)

        command = MockCommand()
        data = pattern.serialize_command(command)
        assert data is None


class TestCommandDeserialization:
    """Test command deserialization."""

    def test_deserialize_command(self, command_pattern, test_data):
        """Test deserializing a command."""
        command = SetValueCommand(test_data, "key", "value")
        data = command_pattern.serialize_command(command)

        deserialized = command_pattern.deserialize_command(data)
        assert deserialized is not None
        assert isinstance(deserialized, SetValueCommand)

    def test_deserialize_disabled(self):
        """Test deserialization when disabled."""
        config = CommandConfig(enable_serialization=False)
        pattern = CommandPatternFSA(config)

        deserialized = pattern.deserialize_command(b"data")
        assert deserialized is None


class TestCommandValidation:
    """Test command validation."""

    def test_validate_command(self, command_pattern):
        """Test validating a command."""
        command = MockCommand()
        result = command_pattern.validate_command(command)
        assert result.valid is True

    def test_validate_failed_command(self, command_pattern):
        """Test validating failed command."""
        command = MockCommand(should_fail=True)
        command_pattern.execute_command(command)

        result = command_pattern.validate_command(command)
        assert len(result.warnings) > 0


class TestCommandCloning:
    """Test command cloning."""

    def test_clone_command(self, command_pattern, test_data):
        """Test cloning a command."""
        command = SetValueCommand(test_data, "key", "value")
        result = command_pattern.clone_command(command)
        assert result.cloned is True
        assert result.original_id != result.clone_id


class TestExecuteMethod:
    """Test execute method."""

    def test_execute_operations(self, command_pattern, test_data):
        """Test executing command pattern operations."""
        ops = [
            CommandOp(
                operation="create",
                command_type="set_value",
                params={"target": test_data, "key": "test", "value": 42},
            ),
        ]

        result = command_pattern.execute(ops)
        assert isinstance(result, CommandResult)

    def test_execute_multiple_ops(self, command_pattern):
        """Test executing multiple operations."""
        command = MockCommand()
        ops = [
            CommandOp(operation="execute", command=command),
            CommandOp(operation="undo"),
        ]

        result = command_pattern.execute(ops)
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_execute_empty_queue(self, command_pattern):
        """Test executing empty queue."""
        result = command_pattern.execute_queue()
        assert result.executed is True
        assert result.commands_executed == 0

    def test_undo_before_execute(self, command_pattern):
        """Test undo before execute."""
        command = MockCommand()
        result = command_pattern.undo_command(command)
        assert result.undone is False


class TestThreadSafety:
    """Test thread safety."""

    def test_thread_safe_pattern(self):
        """Test thread-safe pattern creation."""
        config = CommandConfig(thread_safe=True)
        pattern = CommandPatternFSA(config)
        assert pattern._lock is not None

    def test_non_thread_safe_pattern(self):
        """Test non-thread-safe pattern."""
        config = CommandConfig(thread_safe=False)
        pattern = CommandPatternFSA(config)
        assert pattern._lock is None


class TestComplexMacroScenarios:
    """Test complex macro scenarios."""

    def test_nested_macro_execution(self, command_pattern, test_data):
        """Test executing macro with mixed commands."""
        commands = [
            SetValueCommand(test_data, "k1", "v1"),
            SetValueCommand(test_data, "k2", "v2"),
            SetValueCommand(test_data, "k3", "v3"),
        ]
        macro = command_pattern.create_macro_command(commands, "complex_macro")

        result = command_pattern.execute_macro(macro)
        assert result.executed is True
        assert test_data["k1"] == "v1"
        assert test_data["k2"] == "v2"
        assert test_data["k3"] == "v3"

    def test_macro_partial_execution(self, command_pattern):
        """Test macro with partial execution."""
        commands = [
            MockCommand(),
            MockCommand(should_fail=True),
            MockCommand(),
        ]
        macro = command_pattern.create_macro_command(commands, "partial_macro")

        result = command_pattern.execute_macro(macro)
        assert result.executed is False
        assert result.commands_executed == 2

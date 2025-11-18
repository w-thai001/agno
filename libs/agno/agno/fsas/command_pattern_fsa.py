"""Command Pattern FSA for agno.

This module provides a comprehensive command pattern implementation with support for:
- Command encapsulation and execution
- Undo/redo operations with unlimited history
- Command queuing with priority
- Macro commands for command composition
- Command scheduling with delayed execution
- Transaction support with commit/rollback
- Command serialization for persistence
- Thread-safe operations
- Async command support
"""

import logging
import pickle
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Type
from uuid import uuid4

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class CommandStatus(Enum):
    """Command execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    UNDONE = "undone"
    FAILED = "failed"


class CommandPriority(Enum):
    """Command priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class TransactionStatus(Enum):
    """Transaction status."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


# ==================== Base Classes ====================

class Command(ABC):
    """Base command class."""

    def __init__(self):
        self.command_id = str(uuid4())
        self.status = CommandStatus.PENDING
        self.executed_at: Optional[datetime] = None
        self.undone_at: Optional[datetime] = None
        self.can_undo_flag = True
        self.metadata: Dict[str, Any] = {}
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command."""
        pass

    def can_undo(self) -> bool:
        """Check if command can be undone."""
        return self.can_undo_flag and self.status == CommandStatus.EXECUTED

    def can_redo(self) -> bool:
        """Check if command can be redone."""
        return self.status == CommandStatus.UNDONE


# ==================== Data Classes ====================

@dataclass
class Event:
    """Command event."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    command_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandOp:
    """Command operation."""
    operation: str = ""
    command: Optional[Command] = None
    command_type: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = CommandPriority.NORMAL.value
    execute_time: Optional[datetime] = None


@dataclass
class CommandResult:
    """Command pattern pipeline result."""
    success: bool
    operations_count: int = 0
    commands_executed: int = 0
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    results: List[Any] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExecuteResult:
    """Command execution result."""
    executed: bool
    command_id: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class UndoResult:
    """Command undo result."""
    undone: bool
    command_id: str = ""
    error: Optional[str] = None


@dataclass
class RedoResult:
    """Command redo result."""
    redone: bool
    command_id: str = ""
    error: Optional[str] = None


@dataclass
class PushResult:
    """Stack push result."""
    pushed: bool
    stack_size: int = 0
    error: Optional[str] = None


@dataclass
class ClearResult:
    """Stack clear result."""
    cleared: bool
    cleared_count: int = 0


@dataclass
class CommandHistory:
    """Command execution history."""
    commands: List[Command] = field(default_factory=list)
    total_count: int = 0


@dataclass
class EnqueueResult:
    """Command enqueue result."""
    enqueued: bool
    command_id: str = ""
    queue_position: int = 0
    error: Optional[str] = None


@dataclass
class QueueExecuteResult:
    """Queue execution result."""
    executed: bool
    commands_executed: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class MacroCommand:
    """Macro command containing multiple commands."""
    macro_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    commands: List[Command] = field(default_factory=list)
    status: CommandStatus = CommandStatus.PENDING
    executed_at: Optional[datetime] = None


@dataclass
class MacroExecuteResult:
    """Macro execution result."""
    executed: bool
    macro_id: str = ""
    commands_executed: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class MacroUndoResult:
    """Macro undo result."""
    undone: bool
    macro_id: str = ""
    commands_undone: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ScheduledCommand:
    """Scheduled command."""
    schedule_id: str = field(default_factory=lambda: str(uuid4()))
    command: Command = field(default=None)  # type: ignore
    execute_time: datetime = field(default_factory=datetime.now)
    status: str = "scheduled"
    timer: Optional[threading.Timer] = None


@dataclass
class ScheduleResult:
    """Command scheduling result."""
    scheduled: bool
    schedule_id: str = ""
    execute_time: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class CancelResult:
    """Command cancellation result."""
    cancelled: bool
    schedule_id: str = ""
    error: Optional[str] = None


@dataclass
class Transaction:
    """Command transaction."""
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    commands: List[Command] = field(default_factory=list)
    status: TransactionStatus = TransactionStatus.ACTIVE
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class CommitResult:
    """Transaction commit result."""
    committed: bool
    transaction_id: str = ""
    commands_executed: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class RollbackResult:
    """Transaction rollback result."""
    rolled_back: bool
    transaction_id: str = ""
    commands_undone: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class CloneResult:
    """Command clone result."""
    cloned: bool
    original_id: str = ""
    clone_id: str = ""
    error: Optional[str] = None


@dataclass
class CommandConfig:
    """Command pattern configuration."""
    enable_undo: bool = True
    enable_redo: bool = True
    enable_queue: bool = True
    enable_scheduling: bool = True
    enable_transactions: bool = True
    enable_serialization: bool = True
    max_undo_stack_size: int = 1000
    max_redo_stack_size: int = 1000
    max_queue_size: int = 10000
    max_history_size: int = 10000
    thread_safe: bool = True
    enable_async: bool = True
    command_timeout: float = 30.0


# ==================== Concrete Commands ====================

class SetValueCommand(Command):
    """Command to set a value in a dictionary."""

    def __init__(self, target: Dict[str, Any], key: str, value: Any):
        super().__init__()
        self.target = target
        self.key = key
        self.value = value
        self.old_value: Optional[Any] = None

    def execute(self) -> bool:
        """Execute the command."""
        try:
            self.old_value = self.target.get(self.key)
            self.target[self.key] = self.value
            self.status = CommandStatus.EXECUTED
            self.executed_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            self.status = CommandStatus.FAILED
            return False

    def undo(self) -> bool:
        """Undo the command."""
        try:
            if self.old_value is not None:
                self.target[self.key] = self.old_value
            elif self.key in self.target:
                del self.target[self.key]
            self.status = CommandStatus.UNDONE
            self.undone_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            return False


class DeleteKeyCommand(Command):
    """Command to delete a key from a dictionary."""

    def __init__(self, target: Dict[str, Any], key: str):
        super().__init__()
        self.target = target
        self.key = key
        self.old_value: Optional[Any] = None

    def execute(self) -> bool:
        """Execute the command."""
        try:
            if self.key in self.target:
                self.old_value = self.target[self.key]
                del self.target[self.key]
            self.status = CommandStatus.EXECUTED
            self.executed_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            self.status = CommandStatus.FAILED
            return False

    def undo(self) -> bool:
        """Undo the command."""
        try:
            if self.old_value is not None:
                self.target[self.key] = self.old_value
            self.status = CommandStatus.UNDONE
            self.undone_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            return False


class AppendCommand(Command):
    """Command to append to a list."""

    def __init__(self, target: List[Any], value: Any):
        super().__init__()
        self.target = target
        self.value = value

    def execute(self) -> bool:
        """Execute the command."""
        try:
            self.target.append(self.value)
            self.status = CommandStatus.EXECUTED
            self.executed_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            self.status = CommandStatus.FAILED
            return False

    def undo(self) -> bool:
        """Undo the command."""
        try:
            if self.value in self.target:
                self.target.remove(self.value)
            self.status = CommandStatus.UNDONE
            self.undone_at = datetime.now()
            return True
        except Exception as e:
            self.error = str(e)
            return False


# ==================== Main FSA Class ====================

class CommandPatternFSA:
    """
    Command Pattern FSA implementation.

    Provides command pattern functionality with undo/redo, queuing, macros,
    scheduling, and transactions.
    """

    def __init__(self, config: CommandConfig):
        """
        Initialize Command Pattern FSA.

        Args:
            config: Command pattern configuration
        """
        self.config = config
        self.fsa_id = str(uuid4())

        # Command storage
        self.commands: Dict[str, Command] = {}
        self.undo_stack: Deque[Command] = deque(maxlen=config.max_undo_stack_size)
        self.redo_stack: Deque[Command] = deque(maxlen=config.max_redo_stack_size)
        self.command_queue: Deque[tuple[int, Command]] = deque(maxlen=config.max_queue_size)
        self.command_history: Deque[Command] = deque(maxlen=config.max_history_size)

        # Macro storage
        self.macros: Dict[str, MacroCommand] = {}

        # Scheduled commands
        self.scheduled_commands: Dict[str, ScheduledCommand] = {}

        # Transaction storage
        self.transactions: Dict[str, Transaction] = {}
        self.active_transaction: Optional[Transaction] = None

        # Command factories
        self.command_factories: Dict[str, Callable] = {
            "set_value": lambda params: SetValueCommand(**params),
            "delete_key": lambda params: DeleteKeyCommand(**params),
            "append": lambda params: AppendCommand(**params),
        }

        # Thread safety
        self._lock = threading.RLock() if config.thread_safe else None

        logger.info(f"Initialized CommandPatternFSA: {self.fsa_id}")

    def _acquire_lock(self):
        """Acquire lock for thread-safe operations."""
        if self._lock:
            self._lock.acquire()

    def _release_lock(self):
        """Release lock after thread-safe operations."""
        if self._lock:
            self._lock.release()

    def validate(self, config: CommandConfig) -> ValidationResult:
        """
        Validate command pattern configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if config.max_undo_stack_size < 1:
            errors.append("max_undo_stack_size must be positive")

        if config.max_redo_stack_size < 1:
            errors.append("max_redo_stack_size must be positive")

        if config.max_queue_size < 1:
            errors.append("max_queue_size must be positive")

        if config.command_timeout <= 0:
            errors.append("command_timeout must be positive")

        if not config.enable_undo and config.enable_redo:
            warnings.append("Redo is enabled but undo is disabled")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def create_command(
        self,
        command_type: str,
        params: Dict[str, Any],
    ) -> Optional[Command]:
        """
        Create a command instance.

        Args:
            command_type: Type of command to create
            params: Command parameters

        Returns:
            Command instance or None if factory not found
        """
        try:
            self._acquire_lock()

            if command_type not in self.command_factories:
                logger.error(f"Unknown command type: {command_type}")
                return None

            factory = self.command_factories[command_type]
            command = factory(params)

            self.commands[command.command_id] = command
            logger.info(f"Created command: {command.command_id}")

            return command

        except Exception as e:
            logger.error(f"Error creating command: {str(e)}")
            return None

        finally:
            self._release_lock()

    def execute_command(self, command: Command) -> ExecuteResult:
        """
        Execute a command.

        Args:
            command: Command to execute

        Returns:
            ExecuteResult with execution status
        """
        try:
            self._acquire_lock()

            start_time = time.time()
            command.status = CommandStatus.EXECUTING

            # Execute command
            success = command.execute()

            execution_time = time.time() - start_time

            if success:
                # Add to history
                self.command_history.append(command)

                # Add to undo stack if undo is enabled
                if self.config.enable_undo and command.can_undo():
                    self.undo_stack.append(command)

                # Clear redo stack on new command
                if self.config.enable_redo:
                    self.redo_stack.clear()

                # Add to active transaction if exists
                if self.active_transaction:
                    self.active_transaction.commands.append(command)

                logger.info(f"Executed command: {command.command_id}")

                return ExecuteResult(
                    executed=True,
                    command_id=command.command_id,
                    result=command.result,
                    execution_time=execution_time,
                )
            else:
                return ExecuteResult(
                    executed=False,
                    command_id=command.command_id,
                    error=command.error or "Execution failed",
                    execution_time=execution_time,
                )

        except Exception as e:
            return ExecuteResult(
                executed=False,
                command_id=command.command_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def undo_command(self, command: Command) -> UndoResult:
        """
        Undo a command.

        Args:
            command: Command to undo

        Returns:
            UndoResult with undo status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_undo:
                return UndoResult(
                    undone=False,
                    command_id=command.command_id,
                    error="Undo is disabled",
                )

            if not command.can_undo():
                return UndoResult(
                    undone=False,
                    command_id=command.command_id,
                    error="Command cannot be undone",
                )

            # Undo command
            success = command.undo()

            if success:
                # Add to redo stack
                if self.config.enable_redo:
                    self.redo_stack.append(command)

                logger.info(f"Undone command: {command.command_id}")

                return UndoResult(
                    undone=True,
                    command_id=command.command_id,
                )
            else:
                return UndoResult(
                    undone=False,
                    command_id=command.command_id,
                    error=command.error or "Undo failed",
                )

        except Exception as e:
            return UndoResult(
                undone=False,
                command_id=command.command_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def redo_command(self, command: Command) -> RedoResult:
        """
        Redo a command.

        Args:
            command: Command to redo

        Returns:
            RedoResult with redo status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_redo:
                return RedoResult(
                    redone=False,
                    command_id=command.command_id,
                    error="Redo is disabled",
                )

            if not command.can_redo():
                return RedoResult(
                    redone=False,
                    command_id=command.command_id,
                    error="Command cannot be redone",
                )

            # Re-execute command
            success = command.execute()

            if success:
                # Add back to undo stack
                if self.config.enable_undo:
                    self.undo_stack.append(command)

                logger.info(f"Redone command: {command.command_id}")

                return RedoResult(
                    redone=True,
                    command_id=command.command_id,
                )
            else:
                return RedoResult(
                    redone=False,
                    command_id=command.command_id,
                    error=command.error or "Redo failed",
                )

        except Exception as e:
            return RedoResult(
                redone=False,
                command_id=command.command_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def can_undo(self, command: Command) -> bool:
        """
        Check if a command can be undone.

        Args:
            command: Command to check

        Returns:
            True if command can be undone
        """
        return command.can_undo()

    def can_redo(self, command: Command) -> bool:
        """
        Check if a command can be redone.

        Args:
            command: Command to check

        Returns:
            True if command can be redone
        """
        return command.can_redo()

    def push_undo_stack(self, command: Command) -> PushResult:
        """
        Push a command onto the undo stack.

        Args:
            command: Command to push

        Returns:
            PushResult with push status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_undo:
                return PushResult(
                    pushed=False,
                    error="Undo is disabled",
                )

            self.undo_stack.append(command)

            return PushResult(
                pushed=True,
                stack_size=len(self.undo_stack),
            )

        except Exception as e:
            return PushResult(
                pushed=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def pop_undo_stack(self) -> Optional[Command]:
        """
        Pop a command from the undo stack.

        Returns:
            Command or None if stack is empty
        """
        try:
            self._acquire_lock()

            if len(self.undo_stack) == 0:
                return None

            return self.undo_stack.pop()

        finally:
            self._release_lock()

    def push_redo_stack(self, command: Command) -> PushResult:
        """
        Push a command onto the redo stack.

        Args:
            command: Command to push

        Returns:
            PushResult with push status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_redo:
                return PushResult(
                    pushed=False,
                    error="Redo is disabled",
                )

            self.redo_stack.append(command)

            return PushResult(
                pushed=True,
                stack_size=len(self.redo_stack),
            )

        except Exception as e:
            return PushResult(
                pushed=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def pop_redo_stack(self) -> Optional[Command]:
        """
        Pop a command from the redo stack.

        Returns:
            Command or None if stack is empty
        """
        try:
            self._acquire_lock()

            if len(self.redo_stack) == 0:
                return None

            return self.redo_stack.pop()

        finally:
            self._release_lock()

    def clear_undo_stack(self) -> ClearResult:
        """
        Clear the undo stack.

        Returns:
            ClearResult with clear status
        """
        try:
            self._acquire_lock()

            count = len(self.undo_stack)
            self.undo_stack.clear()

            return ClearResult(
                cleared=True,
                cleared_count=count,
            )

        finally:
            self._release_lock()

    def clear_redo_stack(self) -> ClearResult:
        """
        Clear the redo stack.

        Returns:
            ClearResult with clear status
        """
        try:
            self._acquire_lock()

            count = len(self.redo_stack)
            self.redo_stack.clear()

            return ClearResult(
                cleared=True,
                cleared_count=count,
            )

        finally:
            self._release_lock()

    def get_command_history(self, limit: Optional[int] = None) -> CommandHistory:
        """
        Get command execution history.

        Args:
            limit: Maximum number of commands to return

        Returns:
            CommandHistory with command list
        """
        try:
            self._acquire_lock()

            if limit:
                commands = list(self.command_history)[-limit:]
            else:
                commands = list(self.command_history)

            return CommandHistory(
                commands=commands,
                total_count=len(self.command_history),
            )

        finally:
            self._release_lock()

    def enqueue_command(
        self,
        command: Command,
        priority: int = CommandPriority.NORMAL.value,
    ) -> EnqueueResult:
        """
        Enqueue a command for execution.

        Args:
            command: Command to enqueue
            priority: Command priority

        Returns:
            EnqueueResult with enqueue status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_queue:
                return EnqueueResult(
                    enqueued=False,
                    command_id=command.command_id,
                    error="Queue is disabled",
                )

            # Add command to queue with priority
            self.command_queue.append((priority, command))

            # Sort by priority (higher priority first)
            self.command_queue = deque(
                sorted(self.command_queue, key=lambda x: x[0], reverse=True)
            )

            logger.info(f"Enqueued command: {command.command_id}")

            return EnqueueResult(
                enqueued=True,
                command_id=command.command_id,
                queue_position=len(self.command_queue),
            )

        except Exception as e:
            return EnqueueResult(
                enqueued=False,
                command_id=command.command_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def dequeue_command(self) -> Optional[Command]:
        """
        Dequeue the next command.

        Returns:
            Command or None if queue is empty
        """
        try:
            self._acquire_lock()

            if len(self.command_queue) == 0:
                return None

            priority, command = self.command_queue.popleft()
            return command

        finally:
            self._release_lock()

    def execute_queue(self, max_commands: Optional[int] = None) -> QueueExecuteResult:
        """
        Execute commands from the queue.

        Args:
            max_commands: Maximum number of commands to execute

        Returns:
            QueueExecuteResult with execution status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_queue:
                return QueueExecuteResult(
                    executed=False,
                    errors=["Queue is disabled"],
                )

            commands_executed = 0
            errors = []

            while len(self.command_queue) > 0:
                if max_commands and commands_executed >= max_commands:
                    break

                command = self.dequeue_command()
                if not command:
                    break

                result = self.execute_command(command)
                if result.executed:
                    commands_executed += 1
                else:
                    errors.append(result.error or "Execution failed")

            return QueueExecuteResult(
                executed=True,
                commands_executed=commands_executed,
                errors=errors,
            )

        except Exception as e:
            return QueueExecuteResult(
                executed=False,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def create_macro_command(
        self,
        commands: List[Command],
        name: str,
    ) -> MacroCommand:
        """
        Create a macro command.

        Args:
            commands: List of commands in macro
            name: Macro name

        Returns:
            MacroCommand instance
        """
        try:
            self._acquire_lock()

            macro = MacroCommand(
                name=name,
                commands=commands,
            )

            self.macros[macro.macro_id] = macro
            logger.info(f"Created macro command: {macro.macro_id}")

            return macro

        finally:
            self._release_lock()

    def execute_macro(self, macro: MacroCommand) -> MacroExecuteResult:
        """
        Execute a macro command.

        Args:
            macro: Macro to execute

        Returns:
            MacroExecuteResult with execution status
        """
        try:
            self._acquire_lock()

            commands_executed = 0
            errors = []

            macro.status = CommandStatus.EXECUTING

            for command in macro.commands:
                result = self.execute_command(command)
                if result.executed:
                    commands_executed += 1
                else:
                    errors.append(result.error or "Execution failed")

            if len(errors) == 0:
                macro.status = CommandStatus.EXECUTED
                macro.executed_at = datetime.now()

            logger.info(f"Executed macro: {macro.macro_id}")

            return MacroExecuteResult(
                executed=len(errors) == 0,
                macro_id=macro.macro_id,
                commands_executed=commands_executed,
                errors=errors,
            )

        except Exception as e:
            return MacroExecuteResult(
                executed=False,
                macro_id=macro.macro_id,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def undo_macro(self, macro: MacroCommand) -> MacroUndoResult:
        """
        Undo a macro command.

        Args:
            macro: Macro to undo

        Returns:
            MacroUndoResult with undo status
        """
        try:
            self._acquire_lock()

            if macro.status != CommandStatus.EXECUTED:
                return MacroUndoResult(
                    undone=False,
                    macro_id=macro.macro_id,
                    errors=["Macro not executed"],
                )

            commands_undone = 0
            errors = []

            # Undo in reverse order
            for command in reversed(macro.commands):
                result = self.undo_command(command)
                if result.undone:
                    commands_undone += 1
                else:
                    errors.append(result.error or "Undo failed")

            if len(errors) == 0:
                macro.status = CommandStatus.UNDONE

            logger.info(f"Undone macro: {macro.macro_id}")

            return MacroUndoResult(
                undone=len(errors) == 0,
                macro_id=macro.macro_id,
                commands_undone=commands_undone,
                errors=errors,
            )

        except Exception as e:
            return MacroUndoResult(
                undone=False,
                macro_id=macro.macro_id,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def schedule_command(
        self,
        command: Command,
        execute_time: datetime,
    ) -> ScheduleResult:
        """
        Schedule a command for delayed execution.

        Args:
            command: Command to schedule
            execute_time: When to execute the command

        Returns:
            ScheduleResult with scheduling status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_scheduling:
                return ScheduleResult(
                    scheduled=False,
                    error="Scheduling is disabled",
                )

            delay = (execute_time - datetime.now()).total_seconds()
            if delay < 0:
                delay = 0

            scheduled_cmd = ScheduledCommand(
                command=command,
                execute_time=execute_time,
            )

            # Create timer for delayed execution
            timer = threading.Timer(
                delay,
                lambda: self.execute_command(command),
            )
            scheduled_cmd.timer = timer
            timer.start()

            self.scheduled_commands[scheduled_cmd.schedule_id] = scheduled_cmd
            logger.info(f"Scheduled command: {scheduled_cmd.schedule_id}")

            return ScheduleResult(
                scheduled=True,
                schedule_id=scheduled_cmd.schedule_id,
                execute_time=execute_time,
            )

        except Exception as e:
            return ScheduleResult(
                scheduled=False,
                error=str(e),
            )

        finally:
            self._release_lock()

    def cancel_scheduled_command(self, schedule_id: str) -> CancelResult:
        """
        Cancel a scheduled command.

        Args:
            schedule_id: Schedule identifier

        Returns:
            CancelResult with cancellation status
        """
        try:
            self._acquire_lock()

            if schedule_id not in self.scheduled_commands:
                return CancelResult(
                    cancelled=False,
                    schedule_id=schedule_id,
                    error="Scheduled command not found",
                )

            scheduled_cmd = self.scheduled_commands[schedule_id]

            if scheduled_cmd.timer:
                scheduled_cmd.timer.cancel()

            scheduled_cmd.status = "cancelled"
            del self.scheduled_commands[schedule_id]

            logger.info(f"Cancelled scheduled command: {schedule_id}")

            return CancelResult(
                cancelled=True,
                schedule_id=schedule_id,
            )

        except Exception as e:
            return CancelResult(
                cancelled=False,
                schedule_id=schedule_id,
                error=str(e),
            )

        finally:
            self._release_lock()

    def begin_transaction(self) -> Transaction:
        """
        Begin a command transaction.

        Returns:
            Transaction instance
        """
        try:
            self._acquire_lock()

            transaction = Transaction()
            self.transactions[transaction.transaction_id] = transaction
            self.active_transaction = transaction

            logger.info(f"Began transaction: {transaction.transaction_id}")

            return transaction

        finally:
            self._release_lock()

    def commit_transaction(self, transaction: Transaction) -> CommitResult:
        """
        Commit a transaction.

        Args:
            transaction: Transaction to commit

        Returns:
            CommitResult with commit status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_transactions:
                return CommitResult(
                    committed=False,
                    transaction_id=transaction.transaction_id,
                    errors=["Transactions are disabled"],
                )

            if transaction.status != TransactionStatus.ACTIVE:
                return CommitResult(
                    committed=False,
                    transaction_id=transaction.transaction_id,
                    errors=["Transaction not active"],
                )

            # All commands already executed, just mark as committed
            transaction.status = TransactionStatus.COMMITTED
            transaction.completed_at = datetime.now()

            if self.active_transaction == transaction:
                self.active_transaction = None

            logger.info(f"Committed transaction: {transaction.transaction_id}")

            return CommitResult(
                committed=True,
                transaction_id=transaction.transaction_id,
                commands_executed=len(transaction.commands),
            )

        except Exception as e:
            return CommitResult(
                committed=False,
                transaction_id=transaction.transaction_id,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def rollback_transaction(self, transaction: Transaction) -> RollbackResult:
        """
        Rollback a transaction.

        Args:
            transaction: Transaction to rollback

        Returns:
            RollbackResult with rollback status
        """
        try:
            self._acquire_lock()

            if not self.config.enable_transactions:
                return RollbackResult(
                    rolled_back=False,
                    transaction_id=transaction.transaction_id,
                    errors=["Transactions are disabled"],
                )

            if transaction.status != TransactionStatus.ACTIVE:
                return RollbackResult(
                    rolled_back=False,
                    transaction_id=transaction.transaction_id,
                    errors=["Transaction not active"],
                )

            commands_undone = 0
            errors = []

            # Undo all commands in reverse order
            for command in reversed(transaction.commands):
                result = self.undo_command(command)
                if result.undone:
                    commands_undone += 1
                else:
                    errors.append(result.error or "Undo failed")

            transaction.status = TransactionStatus.ROLLED_BACK
            transaction.completed_at = datetime.now()

            if self.active_transaction == transaction:
                self.active_transaction = None

            logger.info(f"Rolled back transaction: {transaction.transaction_id}")

            return RollbackResult(
                rolled_back=True,
                transaction_id=transaction.transaction_id,
                commands_undone=commands_undone,
                errors=errors,
            )

        except Exception as e:
            return RollbackResult(
                rolled_back=False,
                transaction_id=transaction.transaction_id,
                errors=[str(e)],
            )

        finally:
            self._release_lock()

    def serialize_command(self, command: Command) -> Optional[bytes]:
        """
        Serialize a command to bytes.

        Args:
            command: Command to serialize

        Returns:
            Serialized bytes or None on failure
        """
        try:
            if not self.config.enable_serialization:
                logger.error("Serialization is disabled")
                return None

            return pickle.dumps(command)

        except Exception as e:
            logger.error(f"Error serializing command: {str(e)}")
            return None

    def deserialize_command(self, data: bytes) -> Optional[Command]:
        """
        Deserialize a command from bytes.

        Args:
            data: Serialized command data

        Returns:
            Command instance or None on failure
        """
        try:
            if not self.config.enable_serialization:
                logger.error("Serialization is disabled")
                return None

            command = pickle.loads(data)
            if isinstance(command, Command):
                return command
            return None

        except Exception as e:
            logger.error(f"Error deserializing command: {str(e)}")
            return None

    def validate_command(self, command: Command) -> ValidationResult:
        """
        Validate a command.

        Args:
            command: Command to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        if not hasattr(command, 'execute'):
            errors.append("Command missing execute method")

        if not hasattr(command, 'undo'):
            errors.append("Command missing undo method")

        if command.status == CommandStatus.FAILED:
            warnings.append("Command previously failed")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def clone_command(self, command: Command) -> CloneResult:
        """
        Clone a command.

        Args:
            command: Command to clone

        Returns:
            CloneResult with cloned command
        """
        try:
            # Use serialization for cloning
            data = self.serialize_command(command)
            if not data:
                return CloneResult(
                    cloned=False,
                    original_id=command.command_id,
                    error="Serialization failed",
                )

            cloned = self.deserialize_command(data)
            if not cloned:
                return CloneResult(
                    cloned=False,
                    original_id=command.command_id,
                    error="Deserialization failed",
                )

            # Generate new ID for clone
            cloned.command_id = str(uuid4())

            return CloneResult(
                cloned=True,
                original_id=command.command_id,
                clone_id=cloned.command_id,
            )

        except Exception as e:
            return CloneResult(
                cloned=False,
                original_id=command.command_id,
                error=str(e),
            )

    def execute(self, ops: List[CommandOp]) -> CommandResult:
        """
        Execute command pattern pipeline.

        Args:
            ops: List of command operations

        Returns:
            CommandResult with pipeline result
        """
        try:
            start_time = time.time()
            commands_executed = 0
            errors = []
            results = []

            for op in ops:
                if op.operation == "create":
                    if op.command_type:
                        command = self.create_command(op.command_type, op.params)
                        if command:
                            results.append(command)
                        else:
                            errors.append("Failed to create command")

                elif op.operation == "execute":
                    if op.command:
                        result = self.execute_command(op.command)
                        if result.executed:
                            commands_executed += 1
                            results.append(result)
                        else:
                            errors.append(result.error or "Execution failed")

                elif op.operation == "undo":
                    command = self.pop_undo_stack()
                    if command:
                        result = self.undo_command(command)
                        results.append(result)

                elif op.operation == "redo":
                    command = self.pop_redo_stack()
                    if command:
                        result = self.redo_command(command)
                        results.append(result)

                elif op.operation == "enqueue":
                    if op.command:
                        result = self.enqueue_command(op.command, op.priority)
                        results.append(result)

                elif op.operation == "execute_queue":
                    result = self.execute_queue()
                    results.append(result)

            execution_time = time.time() - start_time

            return CommandResult(
                success=len(errors) == 0,
                operations_count=len(ops),
                commands_executed=commands_executed,
                errors=errors,
                execution_time=execution_time,
                results=results,
            )

        except Exception as e:
            return CommandResult(
                success=False,
                errors=[str(e)],
            )

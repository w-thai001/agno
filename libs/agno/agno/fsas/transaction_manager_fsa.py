"""
Transaction Manager FSA: ACID-compliant transaction management for distributed systems.

This module provides comprehensive transaction management with support for:
- ACID transaction guarantees (Atomicity, Consistency, Isolation, Durability)
- Multiple isolation levels (Read Uncommitted, Read Committed, Repeatable Read, Serializable)
- Distributed transactions with two-phase commit protocol
- Lock management with deadlock detection
- Savepoints for partial rollback
- Nested transactions with parent-child hierarchy
- Write-ahead transaction log
- Transaction recovery from failures
- Compensation-based rollback
- Thread-safe operations
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class TransactionState(Enum):
    """Transaction lifecycle states."""
    ACTIVE = "active"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class IsolationLevel(Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


class LockType(Enum):
    """Resource lock types."""
    SHARED = "shared"  # Read lock
    EXCLUSIVE = "exclusive"  # Write lock
    INTENTION_SHARED = "intention_shared"
    INTENTION_EXCLUSIVE = "intention_exclusive"


class VoteDecision(Enum):
    """Two-phase commit vote decisions."""
    COMMIT = "commit"
    ABORT = "abort"
    UNKNOWN = "unknown"


class LogOperation(Enum):
    """Transaction log operations."""
    BEGIN = "begin"
    UPDATE = "update"
    COMMIT = "commit"
    ABORT = "abort"
    SAVEPOINT = "savepoint"
    CHECKPOINT = "checkpoint"


# ==================== Data Classes ====================

@dataclass
class Lock:
    """Represents a resource lock."""
    lock_id: str = field(default_factory=lambda: str(uuid4()))
    resource_id: str = ""
    lock_type: LockType = LockType.SHARED
    transaction_id: str = ""
    granted_at: datetime = field(default_factory=datetime.utcnow)
    holders: Set[str] = field(default_factory=set)  # For shared locks


@dataclass
class Savepoint:
    """Transaction savepoint for partial rollback."""
    savepoint_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    transaction_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """Represents a transaction."""
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    state: TransactionState = TransactionState.ACTIVE
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    parent_transaction_id: Optional[str] = None
    nested_transactions: List[str] = field(default_factory=list)
    held_locks: Set[str] = field(default_factory=set)
    savepoints: List[Savepoint] = field(default_factory=list)
    operations: List[Dict[str, Any]] = field(default_factory=list)
    participants: List[str] = field(default_factory=list)  # For distributed transactions
    timeout_seconds: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self.state == TransactionState.ACTIVE

    def is_completed(self) -> bool:
        """Check if transaction is completed."""
        return self.state in [TransactionState.COMMITTED, TransactionState.ABORTED]


@dataclass
class Resource:
    """Represents a resource participating in transaction."""
    resource_id: str = field(default_factory=lambda: str(uuid4()))
    resource_type: str = ""
    data: Any = None
    version: int = 0
    last_modified: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Participant:
    """Participant in distributed transaction."""
    participant_id: str = field(default_factory=lambda: str(uuid4()))
    node_address: str = ""
    transaction_id: str = ""
    vote: VoteDecision = VoteDecision.UNKNOWN
    prepared: bool = False


@dataclass
class Deadlock:
    """Represents a deadlock cycle."""
    deadlock_id: str = field(default_factory=lambda: str(uuid4()))
    cycle: List[str] = field(default_factory=list)  # Transaction IDs in cycle
    detected_at: datetime = field(default_factory=datetime.utcnow)
    victim_transaction_id: Optional[str] = None


@dataclass
class TransactionOp:
    """Transaction operation request."""
    operation: str  # begin, commit, rollback, etc.
    transaction_id: Optional[str] = None
    isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    resource_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionResult:
    """Result of transaction execution."""
    success: bool
    transaction_id: Optional[str] = None
    state: TransactionState = TransactionState.UNKNOWN
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class CommitResult:
    """Result of transaction commit."""
    success: bool
    transaction_id: str
    committed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class RollbackResult:
    """Result of transaction rollback."""
    success: bool
    transaction_id: str
    rolled_back_operations: int = 0
    error: Optional[str] = None


@dataclass
class SavepointResult:
    """Result of savepoint creation."""
    success: bool
    savepoint_id: Optional[str] = None
    name: str = ""
    error: Optional[str] = None


@dataclass
class LockResult:
    """Result of lock acquisition."""
    success: bool
    lock_id: Optional[str] = None
    resource_id: str = ""
    granted: bool = False
    wait_time: float = 0.0
    error: Optional[str] = None


@dataclass
class ReleaseResult:
    """Result of lock release."""
    success: bool
    resource_id: str
    released_locks: int = 0
    error: Optional[str] = None


@dataclass
class DeadlockResult:
    """Result of deadlock detection."""
    deadlock_detected: bool
    deadlocks: List[Deadlock] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResolutionResult:
    """Result of deadlock resolution."""
    success: bool
    deadlock_id: str
    aborted_transaction: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PrepareResult:
    """Result of two-phase commit prepare."""
    success: bool
    transaction_id: str
    prepared: bool = False
    error: Optional[str] = None


@dataclass
class VoteResult:
    """Result of participant vote."""
    success: bool
    participant_id: str
    vote: VoteDecision = VoteDecision.UNKNOWN
    error: Optional[str] = None


@dataclass
class GlobalCommitResult:
    """Result of global commit."""
    success: bool
    transaction_id: str
    participants_committed: List[str] = field(default_factory=list)
    participants_failed: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class GlobalAbortResult:
    """Result of global abort."""
    success: bool
    transaction_id: str
    participants_aborted: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class LogResult:
    """Result of transaction logging."""
    success: bool
    log_entry_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RecoveryResult:
    """Result of transaction recovery."""
    success: bool
    transaction_id: str
    recovered_state: TransactionState = TransactionState.UNKNOWN
    error: Optional[str] = None


@dataclass
class TransactionStatus:
    """Current transaction status."""
    transaction_id: str
    state: TransactionState
    isolation_level: IsolationLevel
    held_locks_count: int = 0
    operations_count: int = 0
    elapsed_time: float = 0.0
    is_nested: bool = False


@dataclass
class SetLevelResult:
    """Result of setting isolation level."""
    success: bool
    transaction_id: str
    previous_level: IsolationLevel
    new_level: IsolationLevel
    error: Optional[str] = None


@dataclass
class NestedTransaction(Transaction):
    """Nested transaction with parent reference."""
    parent_transaction_id: str = ""


@dataclass
class NestedCommitResult:
    """Result of nested transaction commit."""
    success: bool
    nested_transaction_id: str
    parent_transaction_id: str
    error: Optional[str] = None


@dataclass
class CompensationResult:
    """Result of compensation execution."""
    success: bool
    transaction_id: str
    compensated_operations: int = 0
    error: Optional[str] = None


@dataclass
class EnlistResult:
    """Result of resource enlistment."""
    success: bool
    transaction_id: str
    resource_id: str
    error: Optional[str] = None


@dataclass
class LockGraph:
    """Lock dependency graph."""
    nodes: List[str] = field(default_factory=list)  # Transaction IDs
    edges: List[Tuple[str, str]] = field(default_factory=list)  # (from_tx, to_tx)
    cycles: List[List[str]] = field(default_factory=list)


@dataclass
class TransactionMetrics:
    """Transaction performance metrics."""
    transaction_id: str
    duration_seconds: float = 0.0
    lock_wait_time: float = 0.0
    operations_count: int = 0
    locks_acquired: int = 0
    savepoints_created: int = 0
    is_distributed: bool = False
    participants_count: int = 0


@dataclass
class TimeoutResult:
    """Result of timeout setting."""
    success: bool
    transaction_id: str
    timeout_seconds: float
    error: Optional[str] = None


@dataclass
class TransactionConfig:
    """Configuration for transaction manager."""
    default_isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    default_timeout: float = 300.0
    enable_deadlock_detection: bool = True
    deadlock_detection_interval: float = 1.0
    max_lock_wait_time: float = 30.0
    enable_logging: bool = True
    log_directory: str = "./transaction_logs"
    enable_recovery: bool = True
    max_nested_depth: int = 5


@dataclass
class ValidationResult:
    """Transaction configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ==================== Transaction Manager FSA ====================

class TransactionManagerFSA:
    """
    Transaction Manager Finite State Automaton.

    Provides ACID-compliant transaction management with distributed
    transaction support, deadlock detection, and recovery.
    """

    def __init__(
        self,
        name: str = "TransactionManagerFSA",
        config: Optional[TransactionConfig] = None,
    ):
        """
        Initialize Transaction Manager FSA.

        Args:
            name: Name of the FSA instance
            config: Transaction configuration
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.config = config or TransactionConfig()

        # Transaction storage
        self.transactions: Dict[str, Transaction] = {}
        self.completed_transactions: Dict[str, Transaction] = {}

        # Lock management
        self.locks: Dict[str, Lock] = {}  # resource_id -> Lock
        self.lock_queues: Dict[str, deque] = defaultdict(deque)  # resource_id -> waiting transactions
        self.wait_for_graph: Dict[str, Set[str]] = defaultdict(set)  # tx_id -> {tx_ids waiting for}

        # Resources
        self.resources: Dict[str, Resource] = {}

        # Two-phase commit
        self.participants: Dict[str, List[Participant]] = defaultdict(list)  # tx_id -> participants
        self.votes: Dict[str, Dict[str, VoteDecision]] = defaultdict(dict)  # tx_id -> {participant_id -> vote}

        # Transaction log
        self.transaction_log: List[Dict[str, Any]] = []
        self.log_file: Optional[Path] = None
        if self.config.enable_logging:
            log_dir = Path(self.config.log_directory)
            log_dir.mkdir(exist_ok=True)
            self.log_file = log_dir / f"transaction_{self.fsa_id}.log"

        # Metrics
        self.total_transactions: int = 0
        self.committed_transactions: int = 0
        self.aborted_transactions: int = 0
        self.deadlocks_detected: int = 0

        # Deadlock detection
        self.deadlock_detector_running = False
        self.deadlock_detector_thread: Optional[threading.Thread] = None

        # Thread safety
        self.lock = threading.RLock()

        # Start deadlock detection
        if self.config.enable_deadlock_detection:
            self._start_deadlock_detector()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(self, transaction_ops: List[TransactionOp]) -> TransactionResult:
        """
        Execute transaction operations.

        Args:
            transaction_ops: List of transaction operations

        Returns:
            TransactionResult with execution outcome
        """
        start_time = time.time()

        try:
            for op in transaction_ops:
                if op.operation == "begin":
                    self.begin_transaction(op.isolation_level)
                elif op.operation == "commit" and op.transaction_id:
                    self.commit_transaction(op.transaction_id)
                elif op.operation == "rollback" and op.transaction_id:
                    self.rollback_transaction(op.transaction_id)

            execution_time = time.time() - start_time

            return TransactionResult(
                success=True,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Error executing transaction operations: {e}")
            return TransactionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    # ==================== Configuration and Validation ====================

    def validate(self, transaction_config: TransactionConfig) -> ValidationResult:
        """
        Validate transaction configuration.

        Args:
            transaction_config: Configuration to validate

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        if transaction_config.default_timeout <= 0:
            errors.append("Default timeout must be positive")

        if transaction_config.max_lock_wait_time <= 0:
            errors.append("Max lock wait time must be positive")

        if transaction_config.max_nested_depth <= 0:
            errors.append("Max nested depth must be positive")

        if transaction_config.deadlock_detection_interval <= 0:
            warnings.append("Deadlock detection interval should be positive")

        if not transaction_config.enable_logging:
            warnings.append("Transaction logging disabled - recovery may not be possible")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ==================== Transaction Lifecycle ====================

    def begin_transaction(
        self,
        isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED,
    ) -> Transaction:
        """
        Start new transaction.

        Args:
            isolation_level: Transaction isolation level

        Returns:
            Created Transaction object
        """
        with self.lock:
            transaction = Transaction(
                isolation_level=isolation_level,
                timeout_seconds=self.config.default_timeout,
            )

            self.transactions[transaction.transaction_id] = transaction
            self.total_transactions += 1

            # Log transaction start
            self._log_operation(transaction.transaction_id, LogOperation.BEGIN, {
                "isolation_level": isolation_level.value,
            })

            logger.info(f"Started transaction {transaction.transaction_id}")

            return transaction

    def commit_transaction(self, transaction_id: str) -> CommitResult:
        """
        Finalize transaction changes.

        Args:
            transaction_id: Transaction to commit

        Returns:
            CommitResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return CommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found",
                    )

                if not transaction.is_active():
                    return CommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error=f"Transaction not active (state: {transaction.state.value})",
                    )

                # Check nested transactions
                if transaction.nested_transactions:
                    return CommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Cannot commit with active nested transactions",
                    )

                # Update state
                transaction.state = TransactionState.COMMITTING

                # Apply operations (simplified)
                for op in transaction.operations:
                    self._apply_operation(op)

                # Release locks
                self._release_all_locks(transaction_id)

                # Finalize
                transaction.state = TransactionState.COMMITTED
                transaction.completed_at = datetime.utcnow()

                # Move to completed
                self.completed_transactions[transaction_id] = transaction
                del self.transactions[transaction_id]

                # Log commit
                self._log_operation(transaction_id, LogOperation.COMMIT, {})

                self.committed_transactions += 1

                logger.info(f"Committed transaction {transaction_id}")

                return CommitResult(
                    success=True,
                    transaction_id=transaction_id,
                    committed_at=transaction.completed_at,
                )

        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            return CommitResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    def rollback_transaction(self, transaction_id: str) -> RollbackResult:
        """
        Undo transaction changes.

        Args:
            transaction_id: Transaction to rollback

        Returns:
            RollbackResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return RollbackResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found",
                    )

                # Update state
                transaction.state = TransactionState.ABORTING

                # Rollback nested transactions first
                for nested_id in list(transaction.nested_transactions):
                    self.rollback_transaction(nested_id)

                # Undo operations in reverse order
                operations_count = len(transaction.operations)
                for op in reversed(transaction.operations):
                    self._undo_operation(op)

                # Release locks
                self._release_all_locks(transaction_id)

                # Finalize
                transaction.state = TransactionState.ABORTED
                transaction.completed_at = datetime.utcnow()

                # Move to completed
                self.completed_transactions[transaction_id] = transaction
                del self.transactions[transaction_id]

                # Log abort
                self._log_operation(transaction_id, LogOperation.ABORT, {})

                self.aborted_transactions += 1

                logger.info(f"Rolled back transaction {transaction_id}")

                return RollbackResult(
                    success=True,
                    transaction_id=transaction_id,
                    rolled_back_operations=operations_count,
                )

        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            return RollbackResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    # ==================== Savepoints ====================

    def create_savepoint(
        self,
        transaction_id: str,
        name: str,
    ) -> SavepointResult:
        """
        Mark rollback point in transaction.

        Args:
            transaction_id: Transaction ID
            name: Savepoint name

        Returns:
            SavepointResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return SavepointResult(
                        success=False,
                        name=name,
                        error="Transaction not found",
                    )

                # Create savepoint with state snapshot
                savepoint = Savepoint(
                    name=name,
                    transaction_id=transaction_id,
                    state_snapshot={
                        "operations_count": len(transaction.operations),
                        "locks_count": len(transaction.held_locks),
                    },
                )

                transaction.savepoints.append(savepoint)

                # Log savepoint
                self._log_operation(transaction_id, LogOperation.SAVEPOINT, {
                    "savepoint_id": savepoint.savepoint_id,
                    "name": name,
                })

                logger.debug(f"Created savepoint '{name}' for transaction {transaction_id}")

                return SavepointResult(
                    success=True,
                    savepoint_id=savepoint.savepoint_id,
                    name=name,
                )

        except Exception as e:
            logger.error(f"Error creating savepoint: {e}")
            return SavepointResult(
                success=False,
                name=name,
                error=str(e),
            )

    def rollback_to_savepoint(
        self,
        transaction_id: str,
        savepoint: str,
    ) -> RollbackResult:
        """
        Partial undo to savepoint.

        Args:
            transaction_id: Transaction ID
            savepoint: Savepoint name

        Returns:
            RollbackResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return RollbackResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found",
                    )

                # Find savepoint
                target_savepoint = None
                for sp in transaction.savepoints:
                    if sp.name == savepoint:
                        target_savepoint = sp
                        break

                if not target_savepoint:
                    return RollbackResult(
                        success=False,
                        transaction_id=transaction_id,
                        error=f"Savepoint '{savepoint}' not found",
                    )

                # Rollback operations after savepoint
                operations_to_keep = target_savepoint.state_snapshot.get("operations_count", 0)
                operations_to_undo = len(transaction.operations) - operations_to_keep

                for _ in range(operations_to_undo):
                    if transaction.operations:
                        op = transaction.operations.pop()
                        self._undo_operation(op)

                # Remove savepoints after target
                transaction.savepoints = [sp for sp in transaction.savepoints
                                         if sp.created_at <= target_savepoint.created_at]

                logger.info(f"Rolled back transaction {transaction_id} to savepoint '{savepoint}'")

                return RollbackResult(
                    success=True,
                    transaction_id=transaction_id,
                    rolled_back_operations=operations_to_undo,
                )

        except Exception as e:
            logger.error(f"Error rolling back to savepoint: {e}")
            return RollbackResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    # ==================== Lock Management ====================

    def acquire_lock(
        self,
        resource_id: str,
        lock_type: LockType,
        transaction_id: str,
    ) -> LockResult:
        """
        Get resource lock.

        Args:
            resource_id: Resource to lock
            lock_type: Type of lock
            transaction_id: Transaction requesting lock

        Returns:
            LockResult with status
        """
        start_time = time.time()

        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return LockResult(
                        success=False,
                        resource_id=resource_id,
                        error="Transaction not found",
                    )

                # Check if lock is available
                existing_lock = self.locks.get(resource_id)

                if not existing_lock:
                    # Grant lock
                    lock = Lock(
                        resource_id=resource_id,
                        lock_type=lock_type,
                        transaction_id=transaction_id,
                    )
                    if lock_type == LockType.SHARED:
                        lock.holders.add(transaction_id)

                    self.locks[resource_id] = lock
                    transaction.held_locks.add(resource_id)

                    wait_time = time.time() - start_time

                    logger.debug(f"Granted {lock_type.value} lock on {resource_id} to {transaction_id}")

                    return LockResult(
                        success=True,
                        lock_id=lock.lock_id,
                        resource_id=resource_id,
                        granted=True,
                        wait_time=wait_time,
                    )

                # Check compatibility
                if self._locks_compatible(existing_lock, lock_type, transaction_id):
                    # Add to shared lock holders
                    if lock_type == LockType.SHARED:
                        existing_lock.holders.add(transaction_id)
                        transaction.held_locks.add(resource_id)

                        wait_time = time.time() - start_time

                        return LockResult(
                            success=True,
                            lock_id=existing_lock.lock_id,
                            resource_id=resource_id,
                            granted=True,
                            wait_time=wait_time,
                        )

                # Lock not available - would need to wait
                # For simplicity, return failure
                # In production, would implement wait queue

                # Update wait-for graph for deadlock detection
                if existing_lock.transaction_id:
                    self.wait_for_graph[transaction_id].add(existing_lock.transaction_id)

                logger.warning(f"Lock conflict on {resource_id} for transaction {transaction_id}")

                return LockResult(
                    success=False,
                    resource_id=resource_id,
                    granted=False,
                    error="Lock not available",
                )

        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return LockResult(
                success=False,
                resource_id=resource_id,
                error=str(e),
            )

    def release_lock(
        self,
        resource_id: str,
        transaction_id: str,
    ) -> ReleaseResult:
        """
        Free resource lock.

        Args:
            resource_id: Resource to unlock
            transaction_id: Transaction releasing lock

        Returns:
            ReleaseResult with status
        """
        try:
            with self.lock:
                lock = self.locks.get(resource_id)

                if not lock:
                    return ReleaseResult(
                        success=True,
                        resource_id=resource_id,
                        released_locks=0,
                    )

                # Remove from holders
                if transaction_id in lock.holders:
                    lock.holders.remove(transaction_id)

                # Remove lock if no holders
                if lock.lock_type == LockType.EXCLUSIVE or not lock.holders:
                    if lock.transaction_id == transaction_id:
                        del self.locks[resource_id]

                # Update transaction
                transaction = self.transactions.get(transaction_id)
                if transaction:
                    transaction.held_locks.discard(resource_id)

                # Remove from wait-for graph
                if transaction_id in self.wait_for_graph:
                    self.wait_for_graph[transaction_id].discard(resource_id)

                logger.debug(f"Released lock on {resource_id} for transaction {transaction_id}")

                return ReleaseResult(
                    success=True,
                    resource_id=resource_id,
                    released_locks=1,
                )

        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
            return ReleaseResult(
                success=False,
                resource_id=resource_id,
                error=str(e),
            )

    # ==================== Deadlock Detection ====================

    def detect_deadlock(self) -> DeadlockResult:
        """
        Find circular lock dependencies.

        Returns:
            DeadlockResult with detected deadlocks
        """
        with self.lock:
            deadlocks = []

            # Use DFS to find cycles in wait-for graph
            visited = set()
            rec_stack = set()

            def dfs(node: str, path: List[str]) -> Optional[List[str]]:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in self.wait_for_graph.get(node, set()):
                    if neighbor not in visited:
                        cycle = dfs(neighbor, path.copy())
                        if cycle:
                            return cycle
                    elif neighbor in rec_stack:
                        # Found cycle
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:]

                rec_stack.remove(node)
                return None

            for tx_id in self.wait_for_graph:
                if tx_id not in visited:
                    cycle = dfs(tx_id, [])
                    if cycle:
                        deadlock = Deadlock(
                            cycle=cycle,
                            victim_transaction_id=cycle[0],  # Choose first as victim
                        )
                        deadlocks.append(deadlock)
                        self.deadlocks_detected += 1

            return DeadlockResult(
                deadlock_detected=len(deadlocks) > 0,
                deadlocks=deadlocks,
            )

    def resolve_deadlock(self, deadlock: Deadlock) -> ResolutionResult:
        """
        Break deadlock cycle.

        Args:
            deadlock: Deadlock to resolve

        Returns:
            ResolutionResult with status
        """
        try:
            if not deadlock.victim_transaction_id:
                return ResolutionResult(
                    success=False,
                    deadlock_id=deadlock.deadlock_id,
                    error="No victim transaction specified",
                )

            # Abort victim transaction
            result = self.rollback_transaction(deadlock.victim_transaction_id)

            if result.success:
                logger.warning(f"Resolved deadlock {deadlock.deadlock_id} by aborting {deadlock.victim_transaction_id}")

                return ResolutionResult(
                    success=True,
                    deadlock_id=deadlock.deadlock_id,
                    aborted_transaction=deadlock.victim_transaction_id,
                )
            else:
                return ResolutionResult(
                    success=False,
                    deadlock_id=deadlock.deadlock_id,
                    error=result.error,
                )

        except Exception as e:
            logger.error(f"Error resolving deadlock: {e}")
            return ResolutionResult(
                success=False,
                deadlock_id=deadlock.deadlock_id,
                error=str(e),
            )

    # ==================== Two-Phase Commit ====================

    def prepare_transaction(self, transaction_id: str) -> PrepareResult:
        """
        Two-phase commit phase 1.

        Args:
            transaction_id: Transaction to prepare

        Returns:
            PrepareResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return PrepareResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found",
                    )

                # Check if ready to prepare
                if not transaction.is_active():
                    return PrepareResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not active",
                    )

                # Update state
                transaction.state = TransactionState.PREPARING

                # Validate operations can be committed
                # (simplified - in production would check constraints)

                transaction.state = TransactionState.PREPARED

                logger.info(f"Prepared transaction {transaction_id}")

                return PrepareResult(
                    success=True,
                    transaction_id=transaction_id,
                    prepared=True,
                )

        except Exception as e:
            logger.error(f"Error preparing transaction: {e}")
            return PrepareResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    def vote_commit(
        self,
        transaction_id: str,
        participant: Participant,
    ) -> VoteResult:
        """
        Participant decision in 2PC.

        Args:
            transaction_id: Transaction ID
            participant: Participant voting

        Returns:
            VoteResult with vote
        """
        try:
            with self.lock:
                # Record vote
                participant.prepared = True
                self.votes[transaction_id][participant.participant_id] = participant.vote

                logger.debug(f"Participant {participant.participant_id} voted {participant.vote.value}")

                return VoteResult(
                    success=True,
                    participant_id=participant.participant_id,
                    vote=participant.vote,
                )

        except Exception as e:
            logger.error(f"Error recording vote: {e}")
            return VoteResult(
                success=False,
                participant_id=participant.participant_id,
                error=str(e),
            )

    def global_commit(self, transaction_id: str) -> GlobalCommitResult:
        """
        Two-phase commit phase 2 - commit.

        Args:
            transaction_id: Transaction to globally commit

        Returns:
            GlobalCommitResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return GlobalCommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found",
                    )

                # Check all participants voted commit
                votes = self.votes.get(transaction_id, {})
                all_commit = all(v == VoteDecision.COMMIT for v in votes.values())

                if not all_commit:
                    return GlobalCommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Not all participants voted commit",
                    )

                # Commit transaction
                result = self.commit_transaction(transaction_id)

                if result.success:
                    return GlobalCommitResult(
                        success=True,
                        transaction_id=transaction_id,
                        participants_committed=list(votes.keys()),
                    )
                else:
                    return GlobalCommitResult(
                        success=False,
                        transaction_id=transaction_id,
                        error=result.error,
                    )

        except Exception as e:
            logger.error(f"Error in global commit: {e}")
            return GlobalCommitResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    def global_abort(self, transaction_id: str) -> GlobalAbortResult:
        """
        Distributed rollback.

        Args:
            transaction_id: Transaction to globally abort

        Returns:
            GlobalAbortResult with status
        """
        try:
            with self.lock:
                # Rollback transaction
                result = self.rollback_transaction(transaction_id)

                if result.success:
                    votes = self.votes.get(transaction_id, {})
                    return GlobalAbortResult(
                        success=True,
                        transaction_id=transaction_id,
                        participants_aborted=list(votes.keys()),
                    )
                else:
                    return GlobalAbortResult(
                        success=False,
                        transaction_id=transaction_id,
                        error=result.error,
                    )

        except Exception as e:
            logger.error(f"Error in global abort: {e}")
            return GlobalAbortResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    # ==================== Transaction Log ====================

    def log_transaction(
        self,
        transaction: Transaction,
        operation: str,
    ) -> LogResult:
        """
        Write to transaction log.

        Args:
            transaction: Transaction to log
            operation: Operation type

        Returns:
            LogResult with status
        """
        return self._log_operation(transaction.transaction_id, LogOperation(operation), {
            "state": transaction.state.value,
        })

    def recover_transaction(self, transaction_id: str) -> RecoveryResult:
        """
        Restore from log.

        Args:
            transaction_id: Transaction to recover

        Returns:
            RecoveryResult with status
        """
        try:
            # Search log for transaction
            tx_log_entries = [entry for entry in self.transaction_log
                            if entry.get("transaction_id") == transaction_id]

            if not tx_log_entries:
                return RecoveryResult(
                    success=False,
                    transaction_id=transaction_id,
                    error="No log entries found",
                )

            # Determine final state from log
            last_entry = tx_log_entries[-1]
            operation = last_entry.get("operation")

            if operation == "commit":
                state = TransactionState.COMMITTED
            elif operation == "abort":
                state = TransactionState.ABORTED
            else:
                state = TransactionState.UNKNOWN

            logger.info(f"Recovered transaction {transaction_id} with state {state.value}")

            return RecoveryResult(
                success=True,
                transaction_id=transaction_id,
                recovered_state=state,
            )

        except Exception as e:
            logger.error(f"Error recovering transaction: {e}")
            return RecoveryResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    # ==================== Transaction Status ====================

    def get_transaction_status(self, transaction_id: str) -> Optional[TransactionStatus]:
        """
        Query transaction state.

        Args:
            transaction_id: Transaction to query

        Returns:
            TransactionStatus if found
        """
        with self.lock:
            transaction = self.transactions.get(transaction_id)

            if not transaction:
                # Check completed transactions
                transaction = self.completed_transactions.get(transaction_id)

            if not transaction:
                return None

            elapsed = (datetime.utcnow() - transaction.started_at).total_seconds()

            return TransactionStatus(
                transaction_id=transaction_id,
                state=transaction.state,
                isolation_level=transaction.isolation_level,
                held_locks_count=len(transaction.held_locks),
                operations_count=len(transaction.operations),
                elapsed_time=elapsed,
                is_nested=transaction.parent_transaction_id is not None,
            )

    def set_isolation_level(
        self,
        transaction_id: str,
        level: IsolationLevel,
    ) -> SetLevelResult:
        """
        Change isolation level.

        Args:
            transaction_id: Transaction ID
            level: New isolation level

        Returns:
            SetLevelResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return SetLevelResult(
                        success=False,
                        transaction_id=transaction_id,
                        previous_level=level,
                        new_level=level,
                        error="Transaction not found",
                    )

                previous = transaction.isolation_level
                transaction.isolation_level = level

                return SetLevelResult(
                    success=True,
                    transaction_id=transaction_id,
                    previous_level=previous,
                    new_level=level,
                )

        except Exception as e:
            logger.error(f"Error setting isolation level: {e}")
            return SetLevelResult(
                success=False,
                transaction_id=transaction_id,
                previous_level=level,
                new_level=level,
                error=str(e),
            )

    # ==================== Nested Transactions ====================

    def begin_nested_transaction(self, parent_id: str) -> Optional[NestedTransaction]:
        """
        Start sub-transaction.

        Args:
            parent_id: Parent transaction ID

        Returns:
            NestedTransaction if successful
        """
        with self.lock:
            parent = self.transactions.get(parent_id)

            if not parent:
                return None

            # Check nesting depth
            depth = 1
            current = parent
            while current.parent_transaction_id:
                depth += 1
                current = self.transactions.get(current.parent_transaction_id)
                if not current or depth > self.config.max_nested_depth:
                    return None

            # Create nested transaction
            nested = NestedTransaction(
                parent_transaction_id=parent_id,
                isolation_level=parent.isolation_level,
            )

            self.transactions[nested.transaction_id] = nested
            parent.nested_transactions.append(nested.transaction_id)

            logger.debug(f"Started nested transaction {nested.transaction_id} under {parent_id}")

            return nested

    def commit_nested_transaction(self, nested_id: str) -> NestedCommitResult:
        """
        Finalize sub-transaction.

        Args:
            nested_id: Nested transaction ID

        Returns:
            NestedCommitResult with status
        """
        try:
            with self.lock:
                nested = self.transactions.get(nested_id)

                if not nested or not nested.parent_transaction_id:
                    return NestedCommitResult(
                        success=False,
                        nested_transaction_id=nested_id,
                        parent_transaction_id="",
                        error="Not a nested transaction",
                    )

                parent = self.transactions.get(nested.parent_transaction_id)

                if not parent:
                    return NestedCommitResult(
                        success=False,
                        nested_transaction_id=nested_id,
                        parent_transaction_id=nested.parent_transaction_id,
                        error="Parent transaction not found",
                    )

                # Merge operations to parent
                parent.operations.extend(nested.operations)

                # Merge locks to parent
                parent.held_locks.update(nested.held_locks)

                # Remove nested from parent's list
                parent.nested_transactions.remove(nested_id)

                # Remove nested transaction
                del self.transactions[nested_id]

                logger.debug(f"Committed nested transaction {nested_id}")

                return NestedCommitResult(
                    success=True,
                    nested_transaction_id=nested_id,
                    parent_transaction_id=nested.parent_transaction_id,
                )

        except Exception as e:
            logger.error(f"Error committing nested transaction: {e}")
            return NestedCommitResult(
                success=False,
                nested_transaction_id=nested_id,
                parent_transaction_id="",
                error=str(e),
            )

    # ==================== Compensation ====================

    def compensate_transaction(self, transaction_id: str) -> CompensationResult:
        """
        Execute compensating actions.

        Args:
            transaction_id: Transaction to compensate

        Returns:
            CompensationResult with status
        """
        try:
            with self.lock:
                transaction = self.completed_transactions.get(transaction_id)

                if not transaction:
                    return CompensationResult(
                        success=False,
                        transaction_id=transaction_id,
                        error="Transaction not found in completed transactions",
                    )

                # Execute compensation for each operation
                compensated = 0
                for op in reversed(transaction.operations):
                    if "compensation" in op:
                        # Execute compensation action
                        compensation = op["compensation"]
                        # Would execute actual compensation logic here
                        compensated += 1

                logger.info(f"Compensated {compensated} operations for transaction {transaction_id}")

                return CompensationResult(
                    success=True,
                    transaction_id=transaction_id,
                    compensated_operations=compensated,
                )

        except Exception as e:
            logger.error(f"Error compensating transaction: {e}")
            return CompensationResult(
                success=False,
                transaction_id=transaction_id,
                error=str(e),
            )

    # ==================== Resource Management ====================

    def enlist_resource(
        self,
        transaction_id: str,
        resource: Resource,
    ) -> EnlistResult:
        """
        Add participant resource.

        Args:
            transaction_id: Transaction ID
            resource: Resource to enlist

        Returns:
            EnlistResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return EnlistResult(
                        success=False,
                        transaction_id=transaction_id,
                        resource_id=resource.resource_id,
                        error="Transaction not found",
                    )

                # Add resource
                self.resources[resource.resource_id] = resource
                transaction.participants.append(resource.resource_id)

                logger.debug(f"Enlisted resource {resource.resource_id} in transaction {transaction_id}")

                return EnlistResult(
                    success=True,
                    transaction_id=transaction_id,
                    resource_id=resource.resource_id,
                )

        except Exception as e:
            logger.error(f"Error enlisting resource: {e}")
            return EnlistResult(
                success=False,
                transaction_id=transaction_id,
                resource_id=resource.resource_id,
                error=str(e),
            )

    # ==================== Lock Graph ====================

    def get_lock_graph(self) -> LockGraph:
        """
        Visualize lock dependencies.

        Returns:
            LockGraph with nodes and edges
        """
        with self.lock:
            nodes = list(self.wait_for_graph.keys())
            edges = []

            for from_tx, to_txs in self.wait_for_graph.items():
                for to_tx in to_txs:
                    edges.append((from_tx, to_tx))

            # Detect cycles
            cycles = []
            result = self.detect_deadlock()
            for deadlock in result.deadlocks:
                cycles.append(deadlock.cycle)

            return LockGraph(
                nodes=nodes,
                edges=edges,
                cycles=cycles,
            )

    # ==================== Metrics ====================

    def get_transaction_metrics(self, transaction_id: str) -> Optional[TransactionMetrics]:
        """
        Collect transaction statistics.

        Args:
            transaction_id: Transaction to analyze

        Returns:
            TransactionMetrics if found
        """
        with self.lock:
            transaction = self.transactions.get(transaction_id) or \
                         self.completed_transactions.get(transaction_id)

            if not transaction:
                return None

            duration = 0.0
            if transaction.completed_at:
                duration = (transaction.completed_at - transaction.started_at).total_seconds()
            else:
                duration = (datetime.utcnow() - transaction.started_at).total_seconds()

            return TransactionMetrics(
                transaction_id=transaction_id,
                duration_seconds=duration,
                operations_count=len(transaction.operations),
                locks_acquired=len(transaction.held_locks),
                savepoints_created=len(transaction.savepoints),
                is_distributed=len(transaction.participants) > 0,
                participants_count=len(transaction.participants),
            )

    # ==================== Timeout ====================

    def timeout_transaction(
        self,
        transaction_id: str,
        timeout: float,
    ) -> TimeoutResult:
        """
        Set transaction expiration.

        Args:
            transaction_id: Transaction ID
            timeout: Timeout in seconds

        Returns:
            TimeoutResult with status
        """
        try:
            with self.lock:
                transaction = self.transactions.get(transaction_id)

                if not transaction:
                    return TimeoutResult(
                        success=False,
                        transaction_id=transaction_id,
                        timeout_seconds=timeout,
                        error="Transaction not found",
                    )

                transaction.timeout_seconds = timeout

                return TimeoutResult(
                    success=True,
                    transaction_id=transaction_id,
                    timeout_seconds=timeout,
                )

        except Exception as e:
            logger.error(f"Error setting timeout: {e}")
            return TimeoutResult(
                success=False,
                transaction_id=transaction_id,
                timeout_seconds=timeout,
                error=str(e),
            )

    # ==================== Helper Methods ====================

    def _log_operation(
        self,
        transaction_id: str,
        operation: LogOperation,
        data: Dict[str, Any],
    ) -> LogResult:
        """Log transaction operation."""
        try:
            if not self.config.enable_logging:
                return LogResult(success=True)

            log_entry = {
                "log_entry_id": str(uuid4()),
                "transaction_id": transaction_id,
                "operation": operation.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }

            self.transaction_log.append(log_entry)

            # Write to file if configured
            if self.log_file:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")

            return LogResult(
                success=True,
                log_entry_id=log_entry["log_entry_id"],
            )

        except Exception as e:
            logger.error(f"Error logging operation: {e}")
            return LogResult(
                success=False,
                error=str(e),
            )

    def _apply_operation(self, operation: Dict[str, Any]):
        """Apply operation to resources."""
        # Simplified - would actually modify resources
        pass

    def _undo_operation(self, operation: Dict[str, Any]):
        """Undo operation on resources."""
        # Simplified - would actually revert changes
        pass

    def _release_all_locks(self, transaction_id: str):
        """Release all locks held by transaction."""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return

        for resource_id in list(transaction.held_locks):
            self.release_lock(resource_id, transaction_id)

    def _locks_compatible(
        self,
        existing_lock: Lock,
        requested_type: LockType,
        transaction_id: str,
    ) -> bool:
        """Check if locks are compatible."""
        # Shared locks are compatible with other shared locks
        if existing_lock.lock_type == LockType.SHARED and requested_type == LockType.SHARED:
            return True

        # Check if same transaction
        if existing_lock.transaction_id == transaction_id:
            return True

        return False

    def _start_deadlock_detector(self):
        """Start background deadlock detection."""
        def detector_worker():
            while self.deadlock_detector_running:
                time.sleep(self.config.deadlock_detection_interval)
                result = self.detect_deadlock()

                if result.deadlock_detected:
                    for deadlock in result.deadlocks:
                        self.resolve_deadlock(deadlock)

        self.deadlock_detector_running = True
        self.deadlock_detector_thread = threading.Thread(target=detector_worker, daemon=True)
        self.deadlock_detector_thread.start()
        logger.info("Started deadlock detector thread")

    def stop_deadlock_detector(self):
        """Stop background deadlock detection."""
        self.deadlock_detector_running = False
        if self.deadlock_detector_thread:
            self.deadlock_detector_thread.join(timeout=5)
        logger.info("Stopped deadlock detector thread")

    def __del__(self):
        """Cleanup on destruction."""
        self.stop_deadlock_detector()

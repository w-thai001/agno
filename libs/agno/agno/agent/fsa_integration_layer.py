"""
FSA Integration Layer - Central FSA communication hub enabling recursive exponentiation.

This module provides the core infrastructure for FSA orchestration, including:
- FSA registration and discovery
- Workflow execution and orchestration
- Execution logging for meta-learning
- Recursive self-improvement activation
- Cross-FSA communication

Pure in-memory coordination - no file operations.
"""

import asyncio
import copy
import functools
import logging
import threading
import time
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from queue import Queue, Empty
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
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


# Module-level logger configuration
LOGGER_NAME = "fsa_integration_layer"


def _setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure module logger."""
    _logger = logging.getLogger(name)

    if not _logger.handlers:
        try:
            from rich.logging import RichHandler
            handler = RichHandler(
                show_time=True,
                rich_tracebacks=True,
                show_path=True,
            )
            handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
        except ImportError:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))

        _logger.addHandler(handler)
        _logger.setLevel(level)
        _logger.propagate = False

    return _logger


logger = _setup_logger(LOGGER_NAME)


# ============================================================================
# Type Variables and Protocols
# ============================================================================

T = TypeVar('T')
R = TypeVar('R')
FSAType = TypeVar('FSAType', bound='FSAProtocol')


@runtime_checkable
class FSAProtocol(Protocol):
    """Protocol defining the FSA interface."""

    @property
    def fsa_id(self) -> str:
        """Unique FSA identifier."""
        ...

    @property
    def fsa_type(self) -> str:
        """FSA type/category."""
        ...

    def execute(self, input_data: Any, **kwargs) -> Any:
        """Execute the FSA with given input."""
        ...

    async def aexecute(self, input_data: Any, **kwargs) -> Any:
        """Async execute the FSA with given input."""
        ...


# ============================================================================
# Enums
# ============================================================================

class FSAStatus(Enum):
    """Status of an FSA instance."""
    REGISTERED = auto()
    ACTIVE = auto()
    BUSY = auto()
    PAUSED = auto()
    ERROR = auto()
    DEPRECATED = auto()
    SWAPPING = auto()


class ExecutionStatus(Enum):
    """Status of an execution."""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    TIMEOUT = auto()
    CANCELLED = auto()
    RETRYING = auto()


class WorkflowStatus(Enum):
    """Status of a workflow."""
    CREATED = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class RSIPhase(Enum):
    """Phases of Recursive Self-Improvement."""
    OBSERVATION = auto()  # Observing performance
    ANALYSIS = auto()  # Analyzing patterns
    HYPOTHESIS = auto()  # Forming improvement hypotheses
    EXPERIMENT = auto()  # Testing improvements
    INTEGRATION = auto()  # Integrating successful changes
    RECURSION = auto()  # Recursively applying to self


class RetryStrategy(Enum):
    """Retry strategies for failed executions."""
    NONE = auto()
    IMMEDIATE = auto()
    LINEAR_BACKOFF = auto()
    EXPONENTIAL_BACKOFF = auto()
    FIBONACCI_BACKOFF = auto()


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FSAMetadata:
    """Metadata for a registered FSA."""
    fsa_id: str
    fsa_type: str
    version: str
    description: str
    capabilities: List[str]
    dependencies: List[str]
    max_concurrency: int
    timeout_seconds: float
    retry_strategy: RetryStrategy
    max_retries: int
    tags: Set[str] = field(default_factory=set)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time_ms: float = 0.0
    average_lq: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fsa_id": self.fsa_id,
            "fsa_type": self.fsa_type,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout_seconds,
            "retry_strategy": self.retry_strategy.name,
            "max_retries": self.max_retries,
            "tags": list(self.tags),
            "custom_metadata": self.custom_metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_execution_time_ms": self.average_execution_time_ms,
            "average_lq": self.average_lq,
        }


@dataclass
class ExecutionRecord:
    """Record of a single FSA execution."""
    execution_id: str
    fsa_id: str
    workflow_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: ExecutionStatus
    input_data: Any
    output_data: Optional[Any]
    error_message: Optional[str]
    execution_time_ms: float
    tokens_used: int
    leverage_quotient: float
    retry_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "fsa_id": self.fsa_id,
            "workflow_id": self.workflow_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.name,
            "input_summary": str(self.input_data)[:200] if self.input_data else None,
            "output_summary": str(self.output_data)[:200] if self.output_data else None,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "leverage_quotient": self.leverage_quotient,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class WorkflowStep:
    """Definition of a workflow step."""
    step_id: str
    fsa_id: str
    input_mapping: Dict[str, str]  # Maps step input keys to source
    output_key: str  # Key to store output
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    timeout_seconds: Optional[float] = None
    retry_override: Optional[int] = None
    parallel_group: Optional[str] = None  # Steps in same group run in parallel


@dataclass
class WorkflowDefinition:
    """Definition of a multi-FSA workflow."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_context: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 300.0
    max_parallel: int = 10
    on_error: str = "fail"  # "fail", "continue", "rollback"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkflowExecution:
    """Runtime state of a workflow execution."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    context: Dict[str, Any]
    current_step_index: int
    step_results: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime]
    error_message: Optional[str]
    total_execution_time_ms: float
    step_executions: List[ExecutionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.name,
            "current_step_index": self.current_step_index,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "total_execution_time_ms": self.total_execution_time_ms,
            "step_count": len(self.step_executions),
        }


@dataclass
class RSIState:
    """State of the Recursive Self-Improvement system."""
    current_phase: RSIPhase
    iteration: int
    observations: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    experiments: List[Dict[str, Any]]
    successful_improvements: List[Dict[str, Any]]
    improvement_history: List[Dict[str, Any]]
    current_lq: float
    target_lq: float
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class CrossFSAMessage:
    """Message for cross-FSA communication."""
    message_id: str
    source_fsa_id: str
    target_fsa_id: str
    message_type: str
    payload: Any
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl_seconds: Optional[float] = None


# ============================================================================
# Exceptions
# ============================================================================

class FSAIntegrationError(Exception):
    """Base exception for FSA integration errors."""
    pass


class FSANotFoundError(FSAIntegrationError):
    """Raised when an FSA is not found in the registry."""
    pass


class FSARegistrationError(FSAIntegrationError):
    """Raised when FSA registration fails."""
    pass


class WorkflowExecutionError(FSAIntegrationError):
    """Raised when workflow execution fails."""
    pass


class ExecutionTimeoutError(FSAIntegrationError):
    """Raised when execution times out."""
    pass


class RSIError(FSAIntegrationError):
    """Raised when RSI operations fail."""
    pass


class HotSwapError(FSAIntegrationError):
    """Raised when hot-swapping fails."""
    pass


# ============================================================================
# FSA Registry
# ============================================================================

class FSARegistry:
    """
    Registry for FSA instances with metadata tracking.

    Provides registration, discovery, and lifecycle management for FSAs.
    Thread-safe implementation for concurrent access.
    """

    def __init__(self):
        """Initialize the FSA registry."""
        self._lock = threading.RLock()
        self._fsas: Dict[str, Any] = {}  # fsa_id -> FSA instance
        self._metadata: Dict[str, FSAMetadata] = {}  # fsa_id -> metadata
        self._status: Dict[str, FSAStatus] = {}  # fsa_id -> status
        self._type_index: Dict[str, Set[str]] = defaultdict(set)  # type -> fsa_ids
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> fsa_ids
        self._capability_index: Dict[str, Set[str]] = defaultdict(set)  # capability -> fsa_ids
        self._listeners: List[Callable[[str, str, Any], None]] = []  # event listeners

        logger.info("FSARegistry initialized")

    def register(
        self,
        fsa: Any,
        metadata: Optional[FSAMetadata] = None,
        **kwargs,
    ) -> str:
        """
        Register an FSA instance.

        Args:
            fsa: FSA instance to register (must have fsa_id property)
            metadata: Optional metadata (auto-generated if not provided)
            **kwargs: Additional metadata fields

        Returns:
            FSA ID

        Raises:
            FSARegistrationError: If registration fails
        """
        with self._lock:
            # Get or generate FSA ID
            if hasattr(fsa, 'fsa_id'):
                fsa_id = fsa.fsa_id
            elif 'fsa_id' in kwargs:
                fsa_id = kwargs['fsa_id']
            else:
                fsa_id = f"fsa_{uuid.uuid4().hex[:8]}"

            # Check for duplicate
            if fsa_id in self._fsas:
                raise FSARegistrationError(f"FSA '{fsa_id}' is already registered")

            # Build metadata
            if metadata is None:
                metadata = FSAMetadata(
                    fsa_id=fsa_id,
                    fsa_type=getattr(fsa, 'fsa_type', kwargs.get('fsa_type', 'generic')),
                    version=getattr(fsa, 'version', kwargs.get('version', '1.0.0')),
                    description=getattr(fsa, 'description', kwargs.get('description', '')),
                    capabilities=getattr(fsa, 'capabilities', kwargs.get('capabilities', [])),
                    dependencies=getattr(fsa, 'dependencies', kwargs.get('dependencies', [])),
                    max_concurrency=kwargs.get('max_concurrency', 10),
                    timeout_seconds=kwargs.get('timeout_seconds', 30.0),
                    retry_strategy=kwargs.get('retry_strategy', RetryStrategy.EXPONENTIAL_BACKOFF),
                    max_retries=kwargs.get('max_retries', 3),
                    tags=set(kwargs.get('tags', [])),
                    custom_metadata=kwargs.get('custom_metadata', {}),
                )

            # Store FSA and metadata
            self._fsas[fsa_id] = fsa
            self._metadata[fsa_id] = metadata
            self._status[fsa_id] = FSAStatus.REGISTERED

            # Update indices
            self._type_index[metadata.fsa_type].add(fsa_id)
            for tag in metadata.tags:
                self._tag_index[tag].add(fsa_id)
            for capability in metadata.capabilities:
                self._capability_index[capability].add(fsa_id)

            # Notify listeners
            self._notify_listeners("registered", fsa_id, metadata)

            logger.info(f"Registered FSA: {fsa_id} (type={metadata.fsa_type})")
            return fsa_id

    def unregister(self, fsa_id: str) -> bool:
        """
        Unregister an FSA.

        Args:
            fsa_id: ID of FSA to unregister

        Returns:
            True if successfully unregistered
        """
        with self._lock:
            if fsa_id not in self._fsas:
                return False

            metadata = self._metadata[fsa_id]

            # Remove from indices
            self._type_index[metadata.fsa_type].discard(fsa_id)
            for tag in metadata.tags:
                self._tag_index[tag].discard(fsa_id)
            for capability in metadata.capabilities:
                self._capability_index[capability].discard(fsa_id)

            # Remove FSA
            del self._fsas[fsa_id]
            del self._metadata[fsa_id]
            del self._status[fsa_id]

            # Notify listeners
            self._notify_listeners("unregistered", fsa_id, None)

            logger.info(f"Unregistered FSA: {fsa_id}")
            return True

    def get(self, fsa_id: str) -> Any:
        """
        Get an FSA instance by ID.

        Args:
            fsa_id: FSA ID

        Returns:
            FSA instance

        Raises:
            FSANotFoundError: If FSA not found
        """
        with self._lock:
            if fsa_id not in self._fsas:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")
            return self._fsas[fsa_id]

    def get_metadata(self, fsa_id: str) -> FSAMetadata:
        """Get metadata for an FSA."""
        with self._lock:
            if fsa_id not in self._metadata:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")
            return self._metadata[fsa_id]

    def get_status(self, fsa_id: str) -> FSAStatus:
        """Get status of an FSA."""
        with self._lock:
            if fsa_id not in self._status:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")
            return self._status[fsa_id]

    def set_status(self, fsa_id: str, status: FSAStatus) -> None:
        """Set status of an FSA."""
        with self._lock:
            if fsa_id not in self._status:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")
            old_status = self._status[fsa_id]
            self._status[fsa_id] = status
            self._notify_listeners("status_changed", fsa_id, {"old": old_status, "new": status})

    def find_by_type(self, fsa_type: str) -> List[str]:
        """Find FSAs by type."""
        with self._lock:
            return list(self._type_index.get(fsa_type, set()))

    def find_by_tag(self, tag: str) -> List[str]:
        """Find FSAs by tag."""
        with self._lock:
            return list(self._tag_index.get(tag, set()))

    def find_by_capability(self, capability: str) -> List[str]:
        """Find FSAs by capability."""
        with self._lock:
            return list(self._capability_index.get(capability, set()))

    def find_available(self, fsa_type: Optional[str] = None) -> List[str]:
        """Find available (not busy/error) FSAs."""
        with self._lock:
            available_statuses = {FSAStatus.REGISTERED, FSAStatus.ACTIVE}
            candidates = self._type_index.get(fsa_type, self._fsas.keys()) if fsa_type else self._fsas.keys()
            return [
                fsa_id for fsa_id in candidates
                if self._status.get(fsa_id) in available_statuses
            ]

    def list_all(self) -> List[str]:
        """List all registered FSA IDs."""
        with self._lock:
            return list(self._fsas.keys())

    def get_all_metadata(self) -> Dict[str, FSAMetadata]:
        """Get metadata for all FSAs."""
        with self._lock:
            return dict(self._metadata)

    def update_metadata(self, fsa_id: str, **updates) -> None:
        """Update metadata fields for an FSA."""
        with self._lock:
            if fsa_id not in self._metadata:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")

            metadata = self._metadata[fsa_id]
            for key, value in updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)

    def add_listener(self, listener: Callable[[str, str, Any], None]) -> None:
        """Add an event listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[str, str, Any], None]) -> None:
        """Remove an event listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_listeners(self, event: str, fsa_id: str, data: Any) -> None:
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                listener(event, fsa_id, data)
            except Exception as e:
                logger.warning(f"Listener error: {e}")

    def __len__(self) -> int:
        """Return number of registered FSAs."""
        return len(self._fsas)

    def __contains__(self, fsa_id: str) -> bool:
        """Check if FSA is registered."""
        return fsa_id in self._fsas


# ============================================================================
# Execution Logger
# ============================================================================

class ExecutionLogger:
    """
    Logger for FSA executions enabling meta-learning.

    Tracks all FSA calls with detailed metrics for analysis and improvement.
    """

    def __init__(self, max_history: int = 10000):
        """
        Initialize the execution logger.

        Args:
            max_history: Maximum execution records to keep
        """
        self._lock = threading.RLock()
        self._history: List[ExecutionRecord] = []
        self._max_history = max_history
        self._fsa_index: Dict[str, List[int]] = defaultdict(list)  # fsa_id -> record indices
        self._workflow_index: Dict[str, List[int]] = defaultdict(list)  # workflow_id -> record indices
        self._listeners: List[Callable[[ExecutionRecord], None]] = []

        # Aggregated metrics
        self._fsa_metrics: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0.0,
            "total_tokens": 0,
            "lq_sum": 0.0,
        })

        logger.info("ExecutionLogger initialized")

    def log_execution(
        self,
        fsa_id: str,
        input_data: Any,
        output_data: Optional[Any] = None,
        status: ExecutionStatus = ExecutionStatus.SUCCESS,
        error_message: Optional[str] = None,
        execution_time_ms: float = 0.0,
        tokens_used: int = 0,
        workflow_id: Optional[str] = None,
        retry_count: int = 0,
        **metadata,
    ) -> ExecutionRecord:
        """
        Log an FSA execution.

        Args:
            fsa_id: ID of the executed FSA
            input_data: Input to the FSA
            output_data: Output from the FSA
            status: Execution status
            error_message: Error message if failed
            execution_time_ms: Execution time in milliseconds
            tokens_used: Number of tokens used
            workflow_id: Optional workflow ID
            retry_count: Number of retries
            **metadata: Additional metadata

        Returns:
            ExecutionRecord
        """
        with self._lock:
            # Calculate leverage quotient
            if execution_time_ms > 0 and tokens_used > 0:
                lq = (tokens_used / 1000) / (execution_time_ms / 1000 * 10)
            else:
                lq = 0.0

            record = ExecutionRecord(
                execution_id=f"exec_{uuid.uuid4().hex[:12]}",
                fsa_id=fsa_id,
                workflow_id=workflow_id,
                start_time=datetime.now() - timedelta(milliseconds=execution_time_ms),
                end_time=datetime.now(),
                status=status,
                input_data=input_data,
                output_data=output_data,
                error_message=error_message,
                execution_time_ms=execution_time_ms,
                tokens_used=tokens_used,
                leverage_quotient=round(lq, 4),
                retry_count=retry_count,
                metadata=metadata,
            )

            # Store record
            index = len(self._history)
            self._history.append(record)

            # Update indices
            self._fsa_index[fsa_id].append(index)
            if workflow_id:
                self._workflow_index[workflow_id].append(index)

            # Update aggregated metrics
            metrics = self._fsa_metrics[fsa_id]
            metrics["total_executions"] += 1
            metrics["total_time_ms"] += execution_time_ms
            metrics["total_tokens"] += tokens_used
            metrics["lq_sum"] += lq
            if status == ExecutionStatus.SUCCESS:
                metrics["successful"] += 1
            else:
                metrics["failed"] += 1

            # Trim history if needed
            if len(self._history) > self._max_history:
                self._trim_history()

            # Notify listeners
            for listener in self._listeners:
                try:
                    listener(record)
                except Exception as e:
                    logger.warning(f"Listener error: {e}")

            return record

    def _trim_history(self) -> None:
        """Trim history to max size."""
        trim_count = len(self._history) - self._max_history
        if trim_count <= 0:
            return

        # Remove oldest records
        self._history = self._history[trim_count:]

        # Rebuild indices
        self._fsa_index.clear()
        self._workflow_index.clear()

        for i, record in enumerate(self._history):
            self._fsa_index[record.fsa_id].append(i)
            if record.workflow_id:
                self._workflow_index[record.workflow_id].append(i)

    def get_fsa_history(
        self,
        fsa_id: str,
        limit: Optional[int] = None,
    ) -> List[ExecutionRecord]:
        """Get execution history for an FSA."""
        with self._lock:
            indices = self._fsa_index.get(fsa_id, [])
            records = [self._history[i] for i in indices]
            if limit:
                records = records[-limit:]
            return records

    def get_workflow_history(
        self,
        workflow_id: str,
    ) -> List[ExecutionRecord]:
        """Get execution history for a workflow."""
        with self._lock:
            indices = self._workflow_index.get(workflow_id, [])
            return [self._history[i] for i in indices]

    def get_fsa_metrics(self, fsa_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for an FSA."""
        with self._lock:
            metrics = self._fsa_metrics.get(fsa_id, {})
            if not metrics or metrics.get("total_executions", 0) == 0:
                return {}

            total = metrics["total_executions"]
            return {
                "total_executions": total,
                "success_rate": metrics["successful"] / total,
                "failure_rate": metrics["failed"] / total,
                "average_time_ms": metrics["total_time_ms"] / total,
                "average_tokens": metrics["total_tokens"] / total,
                "average_lq": metrics["lq_sum"] / total,
            }

    def get_recent_executions(self, limit: int = 100) -> List[ExecutionRecord]:
        """Get recent executions across all FSAs."""
        with self._lock:
            return self._history[-limit:]

    def get_failed_executions(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """Get failed executions."""
        with self._lock:
            failed = [
                r for r in self._history
                if r.status in {ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT}
                and (since is None or r.start_time >= since)
            ]
            return failed[-limit:]

    def calculate_workflow_lq(self, workflow_id: str) -> float:
        """Calculate leverage quotient for a workflow."""
        with self._lock:
            records = self.get_workflow_history(workflow_id)
            if not records:
                return 0.0

            total_lq = sum(r.leverage_quotient for r in records)
            return total_lq / len(records)

    def add_listener(self, listener: Callable[[ExecutionRecord], None]) -> None:
        """Add an execution listener."""
        self._listeners.append(listener)

    def get_meta_learning_data(self) -> Dict[str, Any]:
        """Get data formatted for meta-learning."""
        with self._lock:
            return {
                "total_executions": len(self._history),
                "fsa_metrics": {
                    fsa_id: self.get_fsa_metrics(fsa_id)
                    for fsa_id in self._fsa_metrics.keys()
                },
                "recent_patterns": self._extract_patterns(),
                "performance_trends": self._calculate_trends(),
            }

    def _extract_patterns(self) -> List[Dict[str, Any]]:
        """Extract patterns from execution history."""
        patterns = []

        # Failure patterns
        failure_counts: Dict[str, int] = defaultdict(int)
        for record in self._history[-1000:]:
            if record.status == ExecutionStatus.FAILED:
                failure_counts[record.fsa_id] += 1

        for fsa_id, count in failure_counts.items():
            if count >= 5:
                patterns.append({
                    "type": "high_failure_rate",
                    "fsa_id": fsa_id,
                    "failure_count": count,
                })

        return patterns

    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate performance trends."""
        if len(self._history) < 10:
            return {}

        # Split history into halves
        mid = len(self._history) // 2
        first_half = self._history[:mid]
        second_half = self._history[mid:]

        # Calculate average LQ for each half
        first_lq = sum(r.leverage_quotient for r in first_half) / len(first_half)
        second_lq = sum(r.leverage_quotient for r in second_half) / len(second_half)

        return {
            "lq_trend": "improving" if second_lq > first_lq else "declining",
            "first_half_avg_lq": round(first_lq, 4),
            "second_half_avg_lq": round(second_lq, 4),
            "improvement": round((second_lq - first_lq) / max(first_lq, 0.01), 4),
        }


# ============================================================================
# Workflow Executor
# ============================================================================

class WorkflowExecutor:
    """
    Executes multi-FSA workflows with orchestration support.

    Handles sequential and parallel execution, error recovery,
    and workflow lifecycle management.
    """

    def __init__(
        self,
        registry: FSARegistry,
        logger: ExecutionLogger,
        max_workers: int = 10,
    ):
        """
        Initialize the workflow executor.

        Args:
            registry: FSA registry
            logger: Execution logger
            max_workers: Maximum parallel workers
        """
        self._registry = registry
        self._logger = logger
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._lock = threading.RLock()

        logger.info("WorkflowExecutor initialized")

    def define_workflow(self, workflow: WorkflowDefinition) -> str:
        """
        Define a new workflow.

        Args:
            workflow: Workflow definition

        Returns:
            Workflow ID
        """
        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
            logger.info(f"Defined workflow: {workflow.workflow_id}")
            return workflow.workflow_id

    def execute(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow synchronously.

        Args:
            workflow_id: ID of workflow to execute
            initial_context: Optional initial context overrides

        Returns:
            WorkflowExecution with results
        """
        workflow = self._get_workflow(workflow_id)

        # Create execution state
        execution = WorkflowExecution(
            execution_id=f"wf_exec_{uuid.uuid4().hex[:12]}",
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            context={**workflow.initial_context, **(initial_context or {})},
            current_step_index=0,
            step_results={},
            start_time=datetime.now(),
            end_time=None,
            error_message=None,
            total_execution_time_ms=0.0,
        )

        with self._lock:
            self._executions[execution.execution_id] = execution

        try:
            # Execute steps
            self._execute_steps(workflow, execution)
            execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")

        finally:
            execution.end_time = datetime.now()
            execution.total_execution_time_ms = (
                execution.end_time - execution.start_time
            ).total_seconds() * 1000

        return execution

    async def aexecute(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow asynchronously.

        Args:
            workflow_id: ID of workflow to execute
            initial_context: Optional initial context overrides

        Returns:
            WorkflowExecution with results
        """
        workflow = self._get_workflow(workflow_id)

        execution = WorkflowExecution(
            execution_id=f"wf_exec_{uuid.uuid4().hex[:12]}",
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            context={**workflow.initial_context, **(initial_context or {})},
            current_step_index=0,
            step_results={},
            start_time=datetime.now(),
            end_time=None,
            error_message=None,
            total_execution_time_ms=0.0,
        )

        with self._lock:
            self._executions[execution.execution_id] = execution

        try:
            await self._aexecute_steps(workflow, execution)
            execution.status = WorkflowStatus.COMPLETED

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")

        finally:
            execution.end_time = datetime.now()
            execution.total_execution_time_ms = (
                execution.end_time - execution.start_time
            ).total_seconds() * 1000

        return execution

    def _get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        """Get workflow definition."""
        if workflow_id not in self._workflows:
            raise WorkflowExecutionError(f"Workflow '{workflow_id}' not found")
        return self._workflows[workflow_id]

    def _execute_steps(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> None:
        """Execute workflow steps."""
        # Group steps by parallel_group
        step_groups = self._group_steps(workflow.steps)

        for group in step_groups:
            if len(group) == 1:
                # Single step - execute directly
                self._execute_step(group[0], execution)
            else:
                # Parallel group - execute concurrently
                self._execute_parallel_steps(group, execution)

            execution.current_step_index += len(group)

    async def _aexecute_steps(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> None:
        """Execute workflow steps asynchronously."""
        step_groups = self._group_steps(workflow.steps)

        for group in step_groups:
            if len(group) == 1:
                await self._aexecute_step(group[0], execution)
            else:
                await self._aexecute_parallel_steps(group, execution)

            execution.current_step_index += len(group)

    def _group_steps(self, steps: List[WorkflowStep]) -> List[List[WorkflowStep]]:
        """Group steps by parallel_group."""
        groups: List[List[WorkflowStep]] = []
        current_group: List[WorkflowStep] = []
        current_parallel_id: Optional[str] = None

        for step in steps:
            if step.parallel_group:
                if step.parallel_group == current_parallel_id:
                    current_group.append(step)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [step]
                    current_parallel_id = step.parallel_group
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_parallel_id = None
                groups.append([step])

        if current_group:
            groups.append(current_group)

        return groups

    def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> Any:
        """Execute a single workflow step."""
        # Check condition
        if step.condition and not step.condition(execution.context):
            logger.debug(f"Step {step.step_id} skipped due to condition")
            return None

        # Get FSA
        fsa = self._registry.get(step.fsa_id)

        # Build input
        input_data = self._build_step_input(step, execution.context)

        # Execute with retry
        start_time = time.time()
        result = None
        error = None
        retry_count = 0
        max_retries = step.retry_override or self._registry.get_metadata(step.fsa_id).max_retries

        while retry_count <= max_retries:
            try:
                if hasattr(fsa, 'execute'):
                    result = fsa.execute(input_data)
                else:
                    result = fsa(input_data)
                break
            except Exception as e:
                error = e
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(self._calculate_backoff(retry_count))

        execution_time_ms = (time.time() - start_time) * 1000

        # Log execution
        record = self._logger.log_execution(
            fsa_id=step.fsa_id,
            input_data=input_data,
            output_data=result,
            status=ExecutionStatus.SUCCESS if error is None else ExecutionStatus.FAILED,
            error_message=str(error) if error else None,
            execution_time_ms=execution_time_ms,
            workflow_id=execution.workflow_id,
            retry_count=retry_count,
        )
        execution.step_executions.append(record)

        if error:
            raise WorkflowExecutionError(f"Step {step.step_id} failed: {error}")

        # Store result
        execution.step_results[step.output_key] = result
        execution.context[step.output_key] = result

        return result

    async def _aexecute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution,
    ) -> Any:
        """Execute a single workflow step asynchronously."""
        if step.condition and not step.condition(execution.context):
            return None

        fsa = self._registry.get(step.fsa_id)
        input_data = self._build_step_input(step, execution.context)

        start_time = time.time()
        result = None
        error = None
        retry_count = 0
        max_retries = step.retry_override or self._registry.get_metadata(step.fsa_id).max_retries

        while retry_count <= max_retries:
            try:
                if hasattr(fsa, 'aexecute'):
                    result = await fsa.aexecute(input_data)
                elif hasattr(fsa, 'execute'):
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, fsa.execute, input_data
                    )
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, fsa, input_data
                    )
                break
            except Exception as e:
                error = e
                retry_count += 1
                if retry_count <= max_retries:
                    await asyncio.sleep(self._calculate_backoff(retry_count))

        execution_time_ms = (time.time() - start_time) * 1000

        record = self._logger.log_execution(
            fsa_id=step.fsa_id,
            input_data=input_data,
            output_data=result,
            status=ExecutionStatus.SUCCESS if error is None else ExecutionStatus.FAILED,
            error_message=str(error) if error else None,
            execution_time_ms=execution_time_ms,
            workflow_id=execution.workflow_id,
            retry_count=retry_count,
        )
        execution.step_executions.append(record)

        if error:
            raise WorkflowExecutionError(f"Step {step.step_id} failed: {error}")

        execution.step_results[step.output_key] = result
        execution.context[step.output_key] = result

        return result

    def _execute_parallel_steps(
        self,
        steps: List[WorkflowStep],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """Execute multiple steps in parallel."""
        futures: Dict[str, Future] = {}

        for step in steps:
            if step.condition and not step.condition(execution.context):
                continue
            future = self._executor.submit(self._execute_step, step, execution)
            futures[step.step_id] = future

        results = {}
        for step_id, future in futures.items():
            try:
                results[step_id] = future.result()
            except Exception as e:
                logger.error(f"Parallel step {step_id} failed: {e}")
                raise

        return results

    async def _aexecute_parallel_steps(
        self,
        steps: List[WorkflowStep],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """Execute multiple steps in parallel asynchronously."""
        tasks = []
        step_ids = []

        for step in steps:
            if step.condition and not step.condition(execution.context):
                continue
            task = asyncio.create_task(self._aexecute_step(step, execution))
            tasks.append(task)
            step_ids.append(step.step_id)

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for step_id, result in zip(step_ids, results_list):
            if isinstance(result, Exception):
                raise result
            results[step_id] = result

        return results

    def _build_step_input(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build input for a step from context."""
        input_data = {}
        for target_key, source_path in step.input_mapping.items():
            if source_path.startswith("$"):
                # Direct context reference
                key = source_path[1:]
                input_data[target_key] = context.get(key)
            elif "." in source_path:
                # Nested reference
                parts = source_path.split(".")
                value = context
                for part in parts:
                    value = value.get(part, {}) if isinstance(value, dict) else None
                input_data[target_key] = value
            else:
                # Literal value
                input_data[target_key] = source_path
        return input_data

    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate backoff time for retry."""
        return min(2 ** retry_count, 30)

    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID."""
        return self._executions.get(execution_id)

    def calculate_workflow_lq(self, execution_id: str) -> float:
        """Calculate LQ for a workflow execution."""
        execution = self._executions.get(execution_id)
        if not execution or not execution.step_executions:
            return 0.0

        total_lq = sum(r.leverage_quotient for r in execution.step_executions)
        return total_lq / len(execution.step_executions)


# ============================================================================
# Cross-FSA Communication
# ============================================================================

class CrossFSACommunication:
    """
    Enables method calling and messaging between FSAs.

    Provides both synchronous and asynchronous communication patterns.
    """

    def __init__(self, registry: FSARegistry):
        """
        Initialize cross-FSA communication.

        Args:
            registry: FSA registry
        """
        self._registry = registry
        self._message_queue: Dict[str, Queue] = defaultdict(Queue)
        self._handlers: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        self._lock = threading.RLock()
        self._message_history: List[CrossFSAMessage] = []

        logger.info("CrossFSACommunication initialized")

    def call(
        self,
        source_fsa_id: str,
        target_fsa_id: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Call a method on another FSA synchronously.

        Args:
            source_fsa_id: Calling FSA ID
            target_fsa_id: Target FSA ID
            method: Method name to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result
        """
        target = self._registry.get(target_fsa_id)

        if not hasattr(target, method):
            raise AttributeError(f"FSA '{target_fsa_id}' has no method '{method}'")

        logger.debug(f"Cross-FSA call: {source_fsa_id} -> {target_fsa_id}.{method}")
        return getattr(target, method)(*args, **kwargs)

    async def acall(
        self,
        source_fsa_id: str,
        target_fsa_id: str,
        method: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Call a method on another FSA asynchronously.

        Args:
            source_fsa_id: Calling FSA ID
            target_fsa_id: Target FSA ID
            method: Method name to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result
        """
        target = self._registry.get(target_fsa_id)

        if not hasattr(target, method):
            raise AttributeError(f"FSA '{target_fsa_id}' has no method '{method}'")

        func = getattr(target, method)

        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return await asyncio.get_event_loop().run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )

    def send_message(
        self,
        source_fsa_id: str,
        target_fsa_id: str,
        message_type: str,
        payload: Any,
        correlation_id: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> str:
        """
        Send a message to another FSA.

        Args:
            source_fsa_id: Source FSA ID
            target_fsa_id: Target FSA ID
            message_type: Type of message
            payload: Message payload
            correlation_id: Optional correlation ID for request/response
            ttl_seconds: Time-to-live for message

        Returns:
            Message ID
        """
        message = CrossFSAMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            source_fsa_id=source_fsa_id,
            target_fsa_id=target_fsa_id,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            correlation_id=correlation_id,
            ttl_seconds=ttl_seconds,
        )

        with self._lock:
            self._message_queue[target_fsa_id].put(message)
            self._message_history.append(message)

            # Trim history
            if len(self._message_history) > 10000:
                self._message_history = self._message_history[-5000:]

        logger.debug(f"Message sent: {source_fsa_id} -> {target_fsa_id} ({message_type})")
        return message.message_id

    def receive_message(
        self,
        fsa_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[CrossFSAMessage]:
        """
        Receive a message for an FSA.

        Args:
            fsa_id: FSA ID to receive for
            timeout: Optional timeout in seconds

        Returns:
            Message or None if timeout
        """
        try:
            message = self._message_queue[fsa_id].get(timeout=timeout)

            # Check TTL
            if message.ttl_seconds:
                age = (datetime.now() - message.timestamp).total_seconds()
                if age > message.ttl_seconds:
                    logger.debug(f"Message {message.message_id} expired")
                    return None

            return message

        except Empty:
            return None

    def register_handler(
        self,
        fsa_id: str,
        message_type: str,
        handler: Callable[[CrossFSAMessage], Any],
    ) -> None:
        """
        Register a message handler for an FSA.

        Args:
            fsa_id: FSA ID
            message_type: Message type to handle
            handler: Handler function
        """
        with self._lock:
            self._handlers[fsa_id][message_type] = handler
            logger.debug(f"Handler registered: {fsa_id} for {message_type}")

    def broadcast(
        self,
        source_fsa_id: str,
        message_type: str,
        payload: Any,
        target_type: Optional[str] = None,
    ) -> List[str]:
        """
        Broadcast a message to multiple FSAs.

        Args:
            source_fsa_id: Source FSA ID
            message_type: Message type
            payload: Message payload
            target_type: Optional FSA type filter

        Returns:
            List of message IDs
        """
        if target_type:
            targets = self._registry.find_by_type(target_type)
        else:
            targets = self._registry.list_all()

        # Exclude source
        targets = [t for t in targets if t != source_fsa_id]

        message_ids = []
        for target_id in targets:
            msg_id = self.send_message(
                source_fsa_id=source_fsa_id,
                target_fsa_id=target_id,
                message_type=message_type,
                payload=payload,
            )
            message_ids.append(msg_id)

        logger.debug(f"Broadcast from {source_fsa_id}: {len(message_ids)} messages")
        return message_ids

    def request_response(
        self,
        source_fsa_id: str,
        target_fsa_id: str,
        request_type: str,
        payload: Any,
        timeout: float = 30.0,
    ) -> Optional[Any]:
        """
        Send a request and wait for response.

        Args:
            source_fsa_id: Source FSA ID
            target_fsa_id: Target FSA ID
            request_type: Request type
            payload: Request payload
            timeout: Response timeout

        Returns:
            Response payload or None
        """
        correlation_id = f"corr_{uuid.uuid4().hex[:8]}"

        # Send request
        self.send_message(
            source_fsa_id=source_fsa_id,
            target_fsa_id=target_fsa_id,
            message_type=request_type,
            payload=payload,
            correlation_id=correlation_id,
        )

        # Wait for response
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = self.receive_message(source_fsa_id, timeout=1.0)
            if message and message.correlation_id == correlation_id:
                return message.payload
            time.sleep(0.1)

        return None


# ============================================================================
# RSI Activator
# ============================================================================

class RSIActivator:
    """
    Activates and manages Recursive Self-Improvement loops.

    Enables FSAs to observe, analyze, hypothesize, experiment, and
    integrate improvements recursively.
    """

    def __init__(
        self,
        registry: FSARegistry,
        logger: ExecutionLogger,
        communication: CrossFSACommunication,
    ):
        """
        Initialize the RSI activator.

        Args:
            registry: FSA registry
            logger: Execution logger
            communication: Cross-FSA communication
        """
        self._registry = registry
        self._logger = logger
        self._communication = communication
        self._lock = threading.RLock()

        self._rsi_states: Dict[str, RSIState] = {}
        self._improvement_queue: Queue = Queue()
        self._active = False
        self._rsi_thread: Optional[threading.Thread] = None

        logger.info("RSIActivator initialized")

    def activate(self, fsa_id: str) -> bool:
        """
        Activate RSI for an FSA.

        Args:
            fsa_id: FSA ID to activate RSI for

        Returns:
            True if activation successful
        """
        with self._lock:
            if fsa_id in self._rsi_states:
                logger.warning(f"RSI already active for {fsa_id}")
                return False

            if fsa_id not in self._registry:
                raise FSANotFoundError(f"FSA '{fsa_id}' not found")

            self._rsi_states[fsa_id] = RSIState(
                current_phase=RSIPhase.OBSERVATION,
                iteration=0,
                observations=[],
                hypotheses=[],
                experiments=[],
                successful_improvements=[],
                improvement_history=[],
                current_lq=self._get_current_lq(fsa_id),
                target_lq=1.0,
            )

            logger.info(f"RSI activated for {fsa_id}")
            return True

    def deactivate(self, fsa_id: str) -> bool:
        """Deactivate RSI for an FSA."""
        with self._lock:
            if fsa_id not in self._rsi_states:
                return False

            del self._rsi_states[fsa_id]
            logger.info(f"RSI deactivated for {fsa_id}")
            return True

    def start_rsi_loop(self) -> None:
        """Start the RSI processing loop."""
        if self._active:
            return

        self._active = True
        self._rsi_thread = threading.Thread(target=self._rsi_loop, daemon=True)
        self._rsi_thread.start()
        logger.info("RSI loop started")

    def stop_rsi_loop(self) -> None:
        """Stop the RSI processing loop."""
        self._active = False
        if self._rsi_thread:
            self._rsi_thread.join(timeout=5.0)
        logger.info("RSI loop stopped")

    def _rsi_loop(self) -> None:
        """Main RSI processing loop."""
        while self._active:
            with self._lock:
                fsa_ids = list(self._rsi_states.keys())

            for fsa_id in fsa_ids:
                try:
                    self._process_rsi_cycle(fsa_id)
                except Exception as e:
                    logger.error(f"RSI error for {fsa_id}: {e}")

            time.sleep(1.0)  # Cycle interval

    def _process_rsi_cycle(self, fsa_id: str) -> None:
        """Process one RSI cycle for an FSA."""
        with self._lock:
            state = self._rsi_states.get(fsa_id)
            if not state:
                return

        if state.current_phase == RSIPhase.OBSERVATION:
            self._observe(fsa_id, state)
        elif state.current_phase == RSIPhase.ANALYSIS:
            self._analyze(fsa_id, state)
        elif state.current_phase == RSIPhase.HYPOTHESIS:
            self._hypothesize(fsa_id, state)
        elif state.current_phase == RSIPhase.EXPERIMENT:
            self._experiment(fsa_id, state)
        elif state.current_phase == RSIPhase.INTEGRATION:
            self._integrate(fsa_id, state)
        elif state.current_phase == RSIPhase.RECURSION:
            self._recurse(fsa_id, state)

    def _observe(self, fsa_id: str, state: RSIState) -> None:
        """Observation phase - collect performance data."""
        history = self._logger.get_fsa_history(fsa_id, limit=100)

        observation = {
            "timestamp": datetime.now().isoformat(),
            "execution_count": len(history),
            "success_rate": sum(1 for h in history if h.status == ExecutionStatus.SUCCESS) / max(len(history), 1),
            "average_lq": sum(h.leverage_quotient for h in history) / max(len(history), 1),
            "average_time_ms": sum(h.execution_time_ms for h in history) / max(len(history), 1),
        }

        state.observations.append(observation)
        state.current_lq = observation["average_lq"]

        # Move to analysis after enough observations
        if len(state.observations) >= 5:
            state.current_phase = RSIPhase.ANALYSIS
            logger.debug(f"RSI {fsa_id}: Observation -> Analysis")

    def _analyze(self, fsa_id: str, state: RSIState) -> None:
        """Analysis phase - identify patterns and issues."""
        if not state.observations:
            state.current_phase = RSIPhase.OBSERVATION
            return

        recent = state.observations[-5:]

        # Analyze trends
        lq_values = [o["average_lq"] for o in recent]
        lq_trend = (lq_values[-1] - lq_values[0]) / max(abs(lq_values[0]), 0.01) if len(lq_values) >= 2 else 0

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "lq_trend": lq_trend,
            "current_lq": state.current_lq,
            "target_lq": state.target_lq,
            "gap": state.target_lq - state.current_lq,
            "needs_improvement": state.current_lq < state.target_lq * 0.9,
        }

        if analysis["needs_improvement"]:
            state.current_phase = RSIPhase.HYPOTHESIS
            logger.debug(f"RSI {fsa_id}: Analysis -> Hypothesis (needs improvement)")
        else:
            state.current_phase = RSIPhase.OBSERVATION
            logger.debug(f"RSI {fsa_id}: Analysis -> Observation (no improvement needed)")

    def _hypothesize(self, fsa_id: str, state: RSIState) -> None:
        """Hypothesis phase - form improvement hypotheses."""
        # Generate hypotheses based on analysis
        hypotheses = []

        if state.current_lq < 0.3:
            hypotheses.append({
                "id": f"hyp_{uuid.uuid4().hex[:8]}",
                "type": "parameter_tuning",
                "description": "Adjust timeout and retry parameters",
                "expected_improvement": 0.1,
                "confidence": 0.7,
            })

        if state.observations and state.observations[-1].get("success_rate", 1.0) < 0.8:
            hypotheses.append({
                "id": f"hyp_{uuid.uuid4().hex[:8]}",
                "type": "error_handling",
                "description": "Improve error handling and recovery",
                "expected_improvement": 0.15,
                "confidence": 0.6,
            })

        state.hypotheses.extend(hypotheses)

        if hypotheses:
            state.current_phase = RSIPhase.EXPERIMENT
            logger.debug(f"RSI {fsa_id}: Hypothesis -> Experiment ({len(hypotheses)} hypotheses)")
        else:
            state.current_phase = RSIPhase.OBSERVATION
            logger.debug(f"RSI {fsa_id}: Hypothesis -> Observation (no hypotheses)")

    def _experiment(self, fsa_id: str, state: RSIState) -> None:
        """Experiment phase - test improvement hypotheses."""
        if not state.hypotheses:
            state.current_phase = RSIPhase.OBSERVATION
            return

        hypothesis = state.hypotheses.pop(0)

        # Simulate experiment (in real implementation, would apply changes)
        experiment = {
            "hypothesis_id": hypothesis["id"],
            "timestamp": datetime.now().isoformat(),
            "before_lq": state.current_lq,
            "simulated_improvement": hypothesis["expected_improvement"] * 0.8,  # Conservative
            "success": True,
        }

        state.experiments.append(experiment)

        if experiment["success"]:
            state.successful_improvements.append({
                "hypothesis": hypothesis,
                "experiment": experiment,
            })

        state.current_phase = RSIPhase.INTEGRATION
        logger.debug(f"RSI {fsa_id}: Experiment -> Integration")

    def _integrate(self, fsa_id: str, state: RSIState) -> None:
        """Integration phase - integrate successful improvements."""
        for improvement in state.successful_improvements:
            state.improvement_history.append({
                "iteration": state.iteration,
                "improvement": improvement,
                "timestamp": datetime.now().isoformat(),
            })

        state.successful_improvements.clear()
        state.current_phase = RSIPhase.RECURSION
        logger.debug(f"RSI {fsa_id}: Integration -> Recursion")

    def _recurse(self, fsa_id: str, state: RSIState) -> None:
        """Recursion phase - apply RSI to RSI process itself."""
        state.iteration += 1

        # Meta-analysis of RSI effectiveness
        if state.improvement_history:
            total_improvement = sum(
                imp["improvement"]["experiment"]["simulated_improvement"]
                for imp in state.improvement_history
            )
            logger.debug(f"RSI {fsa_id}: Total improvement after {state.iteration} iterations: {total_improvement:.4f}")

        # Reset for next cycle
        state.current_phase = RSIPhase.OBSERVATION
        state.observations.clear()
        state.last_update = datetime.now()

        logger.debug(f"RSI {fsa_id}: Recursion -> Observation (iteration {state.iteration})")

    def _get_current_lq(self, fsa_id: str) -> float:
        """Get current LQ for an FSA."""
        metrics = self._logger.get_fsa_metrics(fsa_id)
        return metrics.get("average_lq", 0.0)

    def get_rsi_state(self, fsa_id: str) -> Optional[RSIState]:
        """Get RSI state for an FSA."""
        return self._rsi_states.get(fsa_id)

    def get_improvement_history(self, fsa_id: str) -> List[Dict[str, Any]]:
        """Get improvement history for an FSA."""
        state = self._rsi_states.get(fsa_id)
        if state:
            return state.improvement_history.copy()
        return []


# ============================================================================
# Hot-Swapping Support
# ============================================================================

class HotSwapper:
    """
    Enables hot-swapping of FSA implementations.

    Allows replacing FSA instances without disrupting ongoing operations.
    """

    def __init__(self, registry: FSARegistry):
        """
        Initialize the hot swapper.

        Args:
            registry: FSA registry
        """
        self._registry = registry
        self._lock = threading.RLock()
        self._pending_swaps: Dict[str, Any] = {}
        self._swap_history: List[Dict[str, Any]] = []

        logger.info("HotSwapper initialized")

    def prepare_swap(
        self,
        fsa_id: str,
        new_implementation: Any,
        validation_func: Optional[Callable[[Any], bool]] = None,
    ) -> str:
        """
        Prepare an FSA swap.

        Args:
            fsa_id: ID of FSA to swap
            new_implementation: New FSA implementation
            validation_func: Optional validation function

        Returns:
            Swap ID
        """
        if fsa_id not in self._registry:
            raise FSANotFoundError(f"FSA '{fsa_id}' not found")

        # Validate new implementation
        if validation_func and not validation_func(new_implementation):
            raise HotSwapError("New implementation failed validation")

        swap_id = f"swap_{uuid.uuid4().hex[:8]}"

        with self._lock:
            self._pending_swaps[swap_id] = {
                "fsa_id": fsa_id,
                "new_implementation": new_implementation,
                "prepared_at": datetime.now(),
            }

        logger.info(f"Prepared swap {swap_id} for FSA {fsa_id}")
        return swap_id

    def execute_swap(self, swap_id: str) -> bool:
        """
        Execute a prepared swap.

        Args:
            swap_id: ID of prepared swap

        Returns:
            True if swap successful
        """
        with self._lock:
            if swap_id not in self._pending_swaps:
                raise HotSwapError(f"Swap '{swap_id}' not found")

            swap_info = self._pending_swaps.pop(swap_id)
            fsa_id = swap_info["fsa_id"]
            new_impl = swap_info["new_implementation"]

            # Get current FSA
            old_impl = self._registry.get(fsa_id)
            old_metadata = self._registry.get_metadata(fsa_id)

            try:
                # Set swapping status
                self._registry.set_status(fsa_id, FSAStatus.SWAPPING)

                # Update FSA
                self._registry._fsas[fsa_id] = new_impl

                # Update metadata version
                old_version = old_metadata.version
                version_parts = old_version.split(".")
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                old_metadata.version = ".".join(version_parts)

                # Set active status
                self._registry.set_status(fsa_id, FSAStatus.ACTIVE)

                # Record swap
                self._swap_history.append({
                    "swap_id": swap_id,
                    "fsa_id": fsa_id,
                    "old_version": old_version,
                    "new_version": old_metadata.version,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                })

                logger.info(f"Executed swap {swap_id}: {fsa_id} v{old_version} -> v{old_metadata.version}")
                return True

            except Exception as e:
                # Rollback
                self._registry._fsas[fsa_id] = old_impl
                self._registry.set_status(fsa_id, FSAStatus.ACTIVE)

                self._swap_history.append({
                    "swap_id": swap_id,
                    "fsa_id": fsa_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e),
                })

                logger.error(f"Swap {swap_id} failed: {e}")
                raise HotSwapError(f"Swap failed: {e}")

    def cancel_swap(self, swap_id: str) -> bool:
        """Cancel a prepared swap."""
        with self._lock:
            if swap_id in self._pending_swaps:
                del self._pending_swaps[swap_id]
                logger.info(f"Cancelled swap {swap_id}")
                return True
            return False

    def get_swap_history(self, fsa_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get swap history."""
        if fsa_id:
            return [s for s in self._swap_history if s["fsa_id"] == fsa_id]
        return self._swap_history.copy()


# ============================================================================
# Integration Layer Facade
# ============================================================================

class FSAIntegrationLayerHub:
    """
    Central hub providing unified access to all FSA integration components.

    Facade pattern for simplified access to registry, workflow execution,
    logging, communication, RSI, and hot-swapping.
    """

    def __init__(self, max_workers: int = 10, max_history: int = 10000):
        """
        Initialize the integration layer hub.

        Args:
            max_workers: Maximum parallel workers
            max_history: Maximum execution history
        """
        # Core components
        self.registry = FSARegistry()
        self.logger = ExecutionLogger(max_history=max_history)
        self.workflow_executor = WorkflowExecutor(
            registry=self.registry,
            logger=self.logger,
            max_workers=max_workers,
        )
        self.communication = CrossFSACommunication(registry=self.registry)
        self.rsi = RSIActivator(
            registry=self.registry,
            logger=self.logger,
            communication=self.communication,
        )
        self.hot_swapper = HotSwapper(registry=self.registry)

        logger.info("FSAIntegrationLayerHub initialized")

    def register_fsa(
        self,
        fsa: Any,
        **kwargs,
    ) -> str:
        """Register an FSA (convenience method)."""
        return self.registry.register(fsa, **kwargs)

    def execute_fsa(
        self,
        fsa_id: str,
        input_data: Any,
        **kwargs,
    ) -> Tuple[Any, ExecutionRecord]:
        """
        Execute an FSA and log the execution.

        Args:
            fsa_id: FSA to execute
            input_data: Input data
            **kwargs: Additional arguments

        Returns:
            Tuple of (result, execution_record)
        """
        fsa = self.registry.get(fsa_id)
        metadata = self.registry.get_metadata(fsa_id)

        self.registry.set_status(fsa_id, FSAStatus.BUSY)

        start_time = time.time()
        result = None
        error = None

        try:
            if hasattr(fsa, 'execute'):
                result = fsa.execute(input_data, **kwargs)
            else:
                result = fsa(input_data, **kwargs)

        except Exception as e:
            error = e

        finally:
            self.registry.set_status(fsa_id, FSAStatus.ACTIVE)

        execution_time_ms = (time.time() - start_time) * 1000

        record = self.logger.log_execution(
            fsa_id=fsa_id,
            input_data=input_data,
            output_data=result,
            status=ExecutionStatus.SUCCESS if error is None else ExecutionStatus.FAILED,
            error_message=str(error) if error else None,
            execution_time_ms=execution_time_ms,
        )

        # Update metadata
        metadata.execution_count += 1
        metadata.last_execution = datetime.now()
        if error is None:
            metadata.success_count += 1
        else:
            metadata.failure_count += 1

        # Update average execution time
        metadata.average_execution_time_ms = (
            (metadata.average_execution_time_ms * (metadata.execution_count - 1) + execution_time_ms)
            / metadata.execution_count
        )

        if error:
            raise error

        return result, record

    async def aexecute_fsa(
        self,
        fsa_id: str,
        input_data: Any,
        **kwargs,
    ) -> Tuple[Any, ExecutionRecord]:
        """Execute an FSA asynchronously."""
        fsa = self.registry.get(fsa_id)

        self.registry.set_status(fsa_id, FSAStatus.BUSY)

        start_time = time.time()
        result = None
        error = None

        try:
            if hasattr(fsa, 'aexecute'):
                result = await fsa.aexecute(input_data, **kwargs)
            elif hasattr(fsa, 'execute'):
                result = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(fsa.execute, input_data, **kwargs)
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(fsa, input_data, **kwargs)
                )

        except Exception as e:
            error = e

        finally:
            self.registry.set_status(fsa_id, FSAStatus.ACTIVE)

        execution_time_ms = (time.time() - start_time) * 1000

        record = self.logger.log_execution(
            fsa_id=fsa_id,
            input_data=input_data,
            output_data=result,
            status=ExecutionStatus.SUCCESS if error is None else ExecutionStatus.FAILED,
            error_message=str(error) if error else None,
            execution_time_ms=execution_time_ms,
        )

        if error:
            raise error

        return result, record

    def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """Execute a workflow (convenience method)."""
        return self.workflow_executor.execute(workflow_id, initial_context)

    async def aexecute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """Execute a workflow asynchronously (convenience method)."""
        return await self.workflow_executor.aexecute(workflow_id, initial_context)

    def get_meta_learning_data(self) -> Dict[str, Any]:
        """Get comprehensive meta-learning data."""
        return {
            "execution_data": self.logger.get_meta_learning_data(),
            "registry_data": {
                fsa_id: metadata.to_dict()
                for fsa_id, metadata in self.registry.get_all_metadata().items()
            },
            "rsi_states": {
                fsa_id: {
                    "phase": state.current_phase.name,
                    "iteration": state.iteration,
                    "current_lq": state.current_lq,
                    "improvements": len(state.improvement_history),
                }
                for fsa_id, state in self.rsi._rsi_states.items()
            },
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "registered_fsas": len(self.registry),
            "active_fsas": len(self.registry.find_available()),
            "total_executions": len(self.logger._history),
            "rsi_enabled_fsas": len(self.rsi._rsi_states),
            "pending_swaps": len(self.hot_swapper._pending_swaps),
        }


# ============================================================================
# Module-level singleton
# ============================================================================

_hub_instance: Optional[FSAIntegrationLayerHub] = None
_hub_lock = threading.Lock()


def get_integration_hub() -> FSAIntegrationLayerHub:
    """Get the singleton integration hub instance."""
    global _hub_instance

    with _hub_lock:
        if _hub_instance is None:
            _hub_instance = FSAIntegrationLayerHub()
        return _hub_instance


def reset_integration_hub() -> None:
    """Reset the singleton integration hub (for testing)."""
    global _hub_instance

    with _hub_lock:
        _hub_instance = None


# ============================================================================
# Convenience exports
# ============================================================================

__all__ = [
    # Core classes
    "FSARegistry",
    "ExecutionLogger",
    "WorkflowExecutor",
    "CrossFSACommunication",
    "RSIActivator",
    "HotSwapper",
    "FSAIntegrationLayerHub",
    # Data classes
    "FSAMetadata",
    "ExecutionRecord",
    "WorkflowStep",
    "WorkflowDefinition",
    "WorkflowExecution",
    "RSIState",
    "CrossFSAMessage",
    # Enums
    "FSAStatus",
    "ExecutionStatus",
    "WorkflowStatus",
    "RSIPhase",
    "RetryStrategy",
    # Exceptions
    "FSAIntegrationError",
    "FSANotFoundError",
    "FSARegistrationError",
    "WorkflowExecutionError",
    "ExecutionTimeoutError",
    "RSIError",
    "HotSwapError",
    # Functions
    "get_integration_hub",
    "reset_integration_hub",
]

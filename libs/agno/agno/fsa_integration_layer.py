#!/usr/bin/env python3
"""
FSA Integration Layer - Phase 2 Full Production System

This module provides a comprehensive integration layer for FSA (Financial Services Agent)
orchestration with production-ready features including parallel execution, fault tolerance,
real-time monitoring, hot-swapping, and performance optimization.

Features:
    - Full workflow orchestration with parallel execution
    - Asyncio-based parallel FSA execution engine
    - Error recovery with exponential backoff and circuit breaker
    - Real-time monitoring dashboard with WebSocket support
    - Hot-swapping of FSA implementations
    - Performance metrics and auto-optimization

Example:
    >>> layer = FSAIntegrationLayer()
    >>> await layer.execute_workflow("financial_analysis", {"symbol": "AAPL"})
    >>> layer.start_monitoring_server(port=8765)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import copy
import dataclasses
import datetime
import functools
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import os
import queue
import random
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import types
import uuid
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Deque,
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FSAIntegrationLayer")

# Type variables
T = TypeVar("T")
R = TypeVar("R")
FSAType = TypeVar("FSAType", bound="BaseFSA")


# =============================================================================
# Enums and Constants
# =============================================================================


class ExecutionState(Enum):
    """FSA execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    CIRCUIT_OPEN = "circuit_open"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class Priority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class MetricType(Enum):
    """Types of performance metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_CIRCUIT_THRESHOLD = 5
DEFAULT_CIRCUIT_TIMEOUT = 30.0
DEFAULT_CONCURRENCY_LIMIT = 10
DEFAULT_WEBSOCKET_PORT = 8765
METRICS_HISTORY_SIZE = 1000


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class FSAConfig:
    """Configuration for an FSA instance."""
    name: str
    module_path: str
    class_name: str
    version: str = "1.0.0"
    enabled: bool = True
    priority: Priority = Priority.NORMAL
    timeout: float = 60.0
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    circuit_threshold: int = DEFAULT_CIRCUIT_THRESHOLD
    circuit_timeout: float = DEFAULT_CIRCUIT_TIMEOUT
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Context for FSA execution."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: Optional[str] = None
    parent_id: Optional[str] = None
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    end_time: Optional[datetime.datetime] = None
    state: ExecutionState = ExecutionState.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    trace: List[str] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def add_trace(self, message: str) -> None:
        """Add a trace message with timestamp."""
        timestamp = datetime.datetime.now().isoformat()
        self.trace.append(f"[{timestamp}] {message}")


@dataclass
class WorkflowStep:
    """Definition of a workflow step."""
    name: str
    fsa_name: str
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None
    parallel_group: Optional[str] = None
    timeout: float = 60.0
    on_failure: str = "fail"  # fail, skip, retry, fallback
    fallback_fsa: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 300.0
    max_parallel: int = DEFAULT_CONCURRENCY_LIMIT
    error_handling: str = "fail_fast"  # fail_fast, continue, rollback
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetric:
    """Single performance metric."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker."""
    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime.datetime] = None
    last_success_time: Optional[datetime.datetime] = None
    opened_at: Optional[datetime.datetime] = None
    half_open_calls: int = 0


@dataclass
class MonitoringEvent:
    """Event for monitoring system."""
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    severity: str = "info"  # debug, info, warning, error, critical


# =============================================================================
# Base FSA Protocol
# =============================================================================


@runtime_checkable
class BaseFSA(Protocol):
    """Protocol for FSA implementations."""

    @property
    def name(self) -> str:
        """FSA name."""
        ...

    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the FSA with given context."""
        ...

    async def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data."""
        ...

    def get_health(self) -> Dict[str, Any]:
        """Get FSA health status."""
        ...


class AbstractFSA(ABC):
    """Abstract base class for FSA implementations."""

    def __init__(self, config: Optional[FSAConfig] = None):
        self._config = config
        self._execution_count = 0
        self._error_count = 0
        self._total_duration = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """FSA name."""
        pass

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the FSA with given context."""
        pass

    async def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data. Override for custom validation."""
        return True

    def get_health(self) -> Dict[str, Any]:
        """Get FSA health status."""
        avg_duration = (
            self._total_duration / self._execution_count
            if self._execution_count > 0 else 0.0
        )
        error_rate = (
            self._error_count / self._execution_count
            if self._execution_count > 0 else 0.0
        )
        return {
            "name": self.name,
            "healthy": error_rate < 0.5,
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "error_rate": error_rate,
            "avg_duration": avg_duration,
        }

    def record_execution(self, duration: float, success: bool) -> None:
        """Record execution metrics."""
        self._execution_count += 1
        self._total_duration += duration
        if not success:
            self._error_count += 1


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.

    Prevents cascading failures by temporarily disabling calls to failing services.
    Implements three states: CLOSED (normal), OPEN (blocking), HALF_OPEN (testing).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = DEFAULT_CIRCUIT_THRESHOLD,
        recovery_timeout: float = DEFAULT_CIRCUIT_TIMEOUT,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState(name=name)
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[CircuitBreakerState], None]] = []

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (operational)."""
        return self._state.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking)."""
        return self._state.state == CircuitState.OPEN

    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if self._state.state == CircuitState.CLOSED:
                return True

            if self._state.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._state.opened_at:
                    elapsed = (datetime.datetime.now() - self._state.opened_at).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self._transition_to_half_open()
                        return True
                return False

            # HALF_OPEN state
            if self._state.half_open_calls < self.half_open_max_calls:
                self._state.half_open_calls += 1
                return True
            return False

    async def record_success(self) -> None:
        """Record a successful execution."""
        async with self._lock:
            self._state.success_count += 1
            self._state.last_success_time = datetime.datetime.now()

            if self._state.state == CircuitState.HALF_OPEN:
                # Successful call in half-open state - close the circuit
                self._transition_to_closed()
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed execution."""
        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = datetime.datetime.now()

            if self._state.state == CircuitState.HALF_OPEN:
                # Failure in half-open state - reopen the circuit
                self._transition_to_open()
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.failure_threshold:
                    self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self._state.state = CircuitState.OPEN
        self._state.opened_at = datetime.datetime.now()
        self._state.half_open_calls = 0
        self._notify_listeners()
        logger.warning(f"Circuit breaker '{self.name}' OPENED after {self._state.failure_count} failures")

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._state.state = CircuitState.CLOSED
        self._state.failure_count = 0
        self._state.opened_at = None
        self._state.half_open_calls = 0
        self._notify_listeners()
        logger.info(f"Circuit breaker '{self.name}' CLOSED")

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._state.state = CircuitState.HALF_OPEN
        self._state.half_open_calls = 0
        self._notify_listeners()
        logger.info(f"Circuit breaker '{self.name}' HALF_OPEN")

    def add_listener(self, listener: Callable[[CircuitBreakerState], None]) -> None:
        """Add state change listener."""
        self._listeners.append(listener)

    def _notify_listeners(self) -> None:
        """Notify all listeners of state change."""
        for listener in self._listeners:
            try:
                listener(copy.copy(self._state))
            except Exception as e:
                logger.error(f"Circuit breaker listener error: {e}")

    def get_state_dict(self) -> Dict[str, Any]:
        """Get circuit breaker state as dictionary."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure": self._state.last_failure_time.isoformat() if self._state.last_failure_time else None,
            "last_success": self._state.last_success_time.isoformat() if self._state.last_success_time else None,
            "opened_at": self._state.opened_at.isoformat() if self._state.opened_at else None,
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitBreakerState(name=self.name)
        logger.info(f"Circuit breaker '{self.name}' manually reset")


# =============================================================================
# Error Recovery Manager
# =============================================================================


class ErrorRecoveryManager:
    """
    Manages error recovery with retry logic and exponential backoff.

    Features:
        - Configurable retry strategies
        - Exponential backoff with jitter
        - Circuit breaker integration
        - Error classification and handling
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_RETRY_DELAY,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._error_handlers: Dict[Type[Exception], Callable] = {}
        self._retry_predicates: List[Callable[[Exception], bool]] = []
        self._lock = asyncio.Lock()

        # Statistics
        self._total_retries = 0
        self._successful_recoveries = 0
        self._failed_recoveries = 0

    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = DEFAULT_CIRCUIT_THRESHOLD,
        recovery_timeout: float = DEFAULT_CIRCUIT_TIMEOUT,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for the given name."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self._circuit_breakers[name]

    def register_error_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception, ExecutionContext], Awaitable[Any]],
    ) -> None:
        """Register a handler for specific exception type."""
        self._error_handlers[exception_type] = handler

    def add_retry_predicate(
        self,
        predicate: Callable[[Exception], bool],
    ) -> None:
        """Add a predicate to determine if an exception should be retried."""
        self._retry_predicates.append(predicate)

    def should_retry(self, exception: Exception) -> bool:
        """Determine if the exception should trigger a retry."""
        # Default retryable exceptions
        retryable = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,
        )

        if isinstance(exception, retryable):
            return True

        # Check custom predicates
        for predicate in self._retry_predicates:
            try:
                if predicate(exception):
                    return True
            except Exception:
                pass

        return False

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given retry attempt."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[T]],
        context: ExecutionContext,
        circuit_name: Optional[str] = None,
        *args,
        **kwargs,
    ) -> T:
        """
        Execute a function with retry logic and circuit breaker protection.

        Args:
            func: Async function to execute
            context: Execution context
            circuit_name: Optional circuit breaker name
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function execution

        Raises:
            Exception: If all retries are exhausted
        """
        circuit = (
            self.get_circuit_breaker(circuit_name)
            if circuit_name else None
        )

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            # Check circuit breaker
            if circuit and not await circuit.can_execute():
                context.state = ExecutionState.CIRCUIT_OPEN
                raise RuntimeError(f"Circuit breaker '{circuit_name}' is open")

            try:
                context.retry_count = attempt
                if attempt > 0:
                    context.state = ExecutionState.RETRYING
                    context.add_trace(f"Retry attempt {attempt}/{self.max_retries}")

                result = await func(*args, **kwargs)

                # Success
                if circuit:
                    await circuit.record_success()

                if attempt > 0:
                    self._successful_recoveries += 1

                return result

            except Exception as e:
                last_exception = e
                context.add_trace(f"Error on attempt {attempt}: {type(e).__name__}: {str(e)}")

                # Record failure with circuit breaker
                if circuit:
                    await circuit.record_failure()

                # Check if we should retry
                if attempt < self.max_retries and self.should_retry(e):
                    self._total_retries += 1
                    delay = self.calculate_delay(attempt)
                    context.add_trace(f"Waiting {delay:.2f}s before retry")
                    await asyncio.sleep(delay)
                else:
                    # Try error handler
                    handler = self._find_handler(type(e))
                    if handler:
                        try:
                            return await handler(e, context)
                        except Exception as handler_error:
                            last_exception = handler_error

                    self._failed_recoveries += 1
                    break

        # All retries exhausted
        context.state = ExecutionState.FAILED
        context.error = str(last_exception)
        raise last_exception  # type: ignore

    def _find_handler(
        self,
        exception_type: Type[Exception],
    ) -> Optional[Callable]:
        """Find the most specific handler for an exception type."""
        for exc_type in exception_type.__mro__:
            if exc_type in self._error_handlers:
                return self._error_handlers[exc_type]
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total_recovery_attempts = self._successful_recoveries + self._failed_recoveries
        success_rate = (
            self._successful_recoveries / total_recovery_attempts
            if total_recovery_attempts > 0 else 0.0
        )
        return {
            "total_retries": self._total_retries,
            "successful_recoveries": self._successful_recoveries,
            "failed_recoveries": self._failed_recoveries,
            "recovery_success_rate": success_rate,
            "circuit_breakers": {
                name: cb.get_state_dict()
                for name, cb in self._circuit_breakers.items()
            },
        }

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._total_retries = 0
        self._successful_recoveries = 0
        self._failed_recoveries = 0


# =============================================================================
# Parallel Executor
# =============================================================================


class ParallelExecutor:
    """
    Asyncio-based parallel FSA execution engine.

    Features:
        - Concurrent FSA execution with configurable limits
        - Priority-based task scheduling
        - Resource management and throttling
        - Execution dependency resolution
    """

    def __init__(
        self,
        max_concurrency: int = DEFAULT_CONCURRENCY_LIMIT,
        error_recovery: Optional[ErrorRecoveryManager] = None,
    ):
        self.max_concurrency = max_concurrency
        self.error_recovery = error_recovery or ErrorRecoveryManager()

        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._completed_count = 0
        self._failed_count = 0
        self._total_execution_time = 0.0

    async def execute_single(
        self,
        fsa: BaseFSA,
        context: ExecutionContext,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Execute a single FSA with concurrency control.

        Args:
            fsa: FSA instance to execute
            context: Execution context
            timeout: Optional timeout in seconds

        Returns:
            FSA execution result
        """
        async with self._semaphore:
            context.state = ExecutionState.RUNNING
            context.add_trace(f"Starting execution of {fsa.name}")

            start_time = time.time()

            try:
                if timeout:
                    result = await asyncio.wait_for(
                        self.error_recovery.execute_with_retry(
                            fsa.execute,
                            context,
                            circuit_name=fsa.name,
                            context,
                        ),
                        timeout=timeout,
                    )
                else:
                    result = await self.error_recovery.execute_with_retry(
                        fsa.execute,
                        context,
                        circuit_name=fsa.name,
                        context,
                    )

                context.state = ExecutionState.COMPLETED
                context.output_data = result
                context.end_time = datetime.datetime.now()
                self._completed_count += 1

                return result

            except asyncio.TimeoutError:
                context.state = ExecutionState.FAILED
                context.error = f"Execution timed out after {timeout}s"
                context.end_time = datetime.datetime.now()
                self._failed_count += 1
                raise

            except Exception as e:
                context.state = ExecutionState.FAILED
                context.error = str(e)
                context.end_time = datetime.datetime.now()
                self._failed_count += 1
                raise

            finally:
                duration = time.time() - start_time
                self._total_execution_time += duration
                context.metrics["execution_time"] = duration
                context.add_trace(f"Completed in {duration:.3f}s")

    async def execute_parallel(
        self,
        tasks: List[Tuple[BaseFSA, ExecutionContext]],
        timeout: Optional[float] = None,
        return_exceptions: bool = False,
    ) -> List[Any]:
        """
        Execute multiple FSAs in parallel.

        Args:
            tasks: List of (FSA, context) tuples
            timeout: Optional timeout for all tasks
            return_exceptions: If True, return exceptions instead of raising

        Returns:
            List of results in the same order as input tasks
        """
        if not tasks:
            return []

        async def execute_task(fsa: BaseFSA, ctx: ExecutionContext) -> Any:
            try:
                return await self.execute_single(fsa, ctx, timeout=timeout)
            except Exception as e:
                if return_exceptions:
                    return e
                raise

        coroutines = [execute_task(fsa, ctx) for fsa, ctx in tasks]

        if return_exceptions:
            results = await asyncio.gather(*coroutines, return_exceptions=True)
        else:
            results = await asyncio.gather(*coroutines)

        return results

    async def execute_with_dependencies(
        self,
        tasks: Dict[str, Tuple[BaseFSA, ExecutionContext, List[str]]],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute FSAs respecting their dependencies.

        Args:
            tasks: Dict mapping task_id to (FSA, context, dependencies)
            timeout: Optional timeout for all tasks

        Returns:
            Dict mapping task_id to result
        """
        results: Dict[str, Any] = {}
        completed: Set[str] = set()
        pending = set(tasks.keys())

        while pending:
            # Find tasks whose dependencies are satisfied
            ready = [
                task_id for task_id in pending
                if all(dep in completed for dep in tasks[task_id][2])
            ]

            if not ready:
                # Circular dependency or missing dependency
                raise RuntimeError(
                    f"Cannot resolve dependencies. Pending: {pending}, Completed: {completed}"
                )

            # Execute ready tasks in parallel
            task_list = [(tasks[tid][0], tasks[tid][1]) for tid in ready]
            task_results = await self.execute_parallel(
                task_list,
                timeout=timeout,
                return_exceptions=True,
            )

            for task_id, result in zip(ready, task_results):
                results[task_id] = result
                completed.add(task_id)
                pending.remove(task_id)

                # Pass output to dependent tasks
                if not isinstance(result, Exception):
                    for dep_id in pending:
                        if task_id in tasks[dep_id][2]:
                            tasks[dep_id][1].input_data[f"dep_{task_id}"] = result

        return results

    async def execute_batch(
        self,
        fsa: BaseFSA,
        inputs: List[Dict[str, Any]],
        batch_size: int = 10,
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """
        Execute an FSA on multiple inputs in batches.

        Args:
            fsa: FSA to execute
            inputs: List of input dictionaries
            batch_size: Number of parallel executions per batch
            timeout: Optional timeout per execution

        Returns:
            List of results
        """
        results = []

        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            tasks = [
                (fsa, ExecutionContext(input_data=inp))
                for inp in batch
            ]
            batch_results = await self.execute_parallel(
                tasks,
                timeout=timeout,
                return_exceptions=True,
            )
            results.extend(batch_results)

        return results

    def cancel_task(self, execution_id: str) -> bool:
        """Cancel a running task."""
        if execution_id in self._active_tasks:
            self._active_tasks[execution_id].cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all running tasks."""
        cancelled = 0
        for task in self._active_tasks.values():
            if not task.done():
                task.cancel()
                cancelled += 1
        return cancelled

    def get_statistics(self) -> Dict[str, Any]:
        """Get executor statistics."""
        avg_time = (
            self._total_execution_time / (self._completed_count + self._failed_count)
            if (self._completed_count + self._failed_count) > 0 else 0.0
        )
        return {
            "max_concurrency": self.max_concurrency,
            "active_tasks": len(self._active_tasks),
            "completed_count": self._completed_count,
            "failed_count": self._failed_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": avg_time,
            "error_recovery": self.error_recovery.get_statistics(),
        }


# =============================================================================
# Hot Swap Manager
# =============================================================================


class HotSwapManager:
    """
    Manages dynamic loading and unloading of FSA implementations.

    Features:
        - Runtime FSA module loading/unloading
        - Version management and rollback
        - Zero-downtime updates
        - Dependency tracking
    """

    def __init__(self):
        self._loaded_fsas: Dict[str, BaseFSA] = {}
        self._fsa_configs: Dict[str, FSAConfig] = {}
        self._module_cache: Dict[str, types.ModuleType] = {}
        self._version_history: Dict[str, List[Tuple[str, datetime.datetime]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[str, str, BaseFSA], None]] = []

    async def load_fsa(
        self,
        config: FSAConfig,
        force_reload: bool = False,
    ) -> BaseFSA:
        """
        Load an FSA from configuration.

        Args:
            config: FSA configuration
            force_reload: Force reload even if already loaded

        Returns:
            Loaded FSA instance
        """
        async with self._lock:
            if config.name in self._loaded_fsas and not force_reload:
                logger.info(f"FSA '{config.name}' already loaded")
                return self._loaded_fsas[config.name]

            try:
                # Load the module
                module = self._load_module(config.module_path, force_reload)

                # Get the FSA class
                fsa_class = getattr(module, config.class_name)

                # Create instance
                fsa = fsa_class(config=config, **config.parameters)

                # Store
                old_version = self._fsa_configs.get(config.name, FSAConfig(name="", module_path="", class_name="")).version
                self._loaded_fsas[config.name] = fsa
                self._fsa_configs[config.name] = config

                # Track version history
                self._version_history[config.name].append(
                    (config.version, datetime.datetime.now())
                )

                # Notify listeners
                self._notify_listeners("load", config.name, fsa)

                logger.info(
                    f"Loaded FSA '{config.name}' v{config.version} "
                    f"(previous: v{old_version})"
                )

                return fsa

            except Exception as e:
                logger.error(f"Failed to load FSA '{config.name}': {e}")
                raise

    def _load_module(
        self,
        module_path: str,
        force_reload: bool = False,
    ) -> types.ModuleType:
        """Load a Python module from path."""
        path = Path(module_path)

        if not path.exists():
            raise FileNotFoundError(f"Module not found: {module_path}")

        module_name = path.stem
        cache_key = str(path.absolute())

        if cache_key in self._module_cache and not force_reload:
            return self._module_cache[cache_key]

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module: {module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        self._module_cache[cache_key] = module

        return module

    async def unload_fsa(self, name: str) -> bool:
        """
        Unload an FSA.

        Args:
            name: FSA name

        Returns:
            True if unloaded, False if not found
        """
        async with self._lock:
            if name not in self._loaded_fsas:
                return False

            fsa = self._loaded_fsas.pop(name)
            self._fsa_configs.pop(name, None)

            self._notify_listeners("unload", name, fsa)
            logger.info(f"Unloaded FSA '{name}'")

            return True

    async def reload_fsa(self, name: str) -> Optional[BaseFSA]:
        """
        Reload an FSA with its current configuration.

        Args:
            name: FSA name

        Returns:
            Reloaded FSA instance or None if not found
        """
        if name not in self._fsa_configs:
            logger.warning(f"FSA '{name}' not found for reload")
            return None

        config = self._fsa_configs[name]
        return await self.load_fsa(config, force_reload=True)

    async def hot_swap(
        self,
        name: str,
        new_config: FSAConfig,
        graceful: bool = True,
        drain_timeout: float = 30.0,
    ) -> BaseFSA:
        """
        Hot-swap an FSA implementation with zero downtime.

        Args:
            name: FSA name
            new_config: New configuration
            graceful: Wait for current executions to complete
            drain_timeout: Timeout for draining existing executions

        Returns:
            New FSA instance
        """
        async with self._lock:
            old_fsa = self._loaded_fsas.get(name)

            if graceful and old_fsa:
                # Wait for in-flight requests (simplified - real impl would track)
                logger.info(f"Gracefully draining FSA '{name}'...")
                await asyncio.sleep(min(drain_timeout, 5.0))

            # Load new version
            new_fsa = await self.load_fsa(new_config, force_reload=True)

            self._notify_listeners("swap", name, new_fsa)
            logger.info(f"Hot-swapped FSA '{name}' to v{new_config.version}")

            return new_fsa

    async def rollback(self, name: str, version: Optional[str] = None) -> bool:
        """
        Rollback an FSA to a previous version.

        Args:
            name: FSA name
            version: Target version (defaults to previous)

        Returns:
            True if rollback successful
        """
        if name not in self._version_history or len(self._version_history[name]) < 2:
            logger.warning(f"No version history for FSA '{name}'")
            return False

        # Find target version
        history = self._version_history[name]
        if version:
            target_idx = next(
                (i for i, (v, _) in enumerate(history) if v == version),
                None
            )
            if target_idx is None:
                logger.warning(f"Version '{version}' not found in history")
                return False
        else:
            target_idx = -2  # Previous version

        target_version, _ = history[target_idx]
        logger.info(f"Rolling back FSA '{name}' to v{target_version}")

        # Update config version and reload
        if name in self._fsa_configs:
            config = self._fsa_configs[name]
            config.version = target_version
            await self.load_fsa(config, force_reload=True)
            return True

        return False

    def get_fsa(self, name: str) -> Optional[BaseFSA]:
        """Get a loaded FSA by name."""
        return self._loaded_fsas.get(name)

    def get_all_fsas(self) -> Dict[str, BaseFSA]:
        """Get all loaded FSAs."""
        return dict(self._loaded_fsas)

    def get_config(self, name: str) -> Optional[FSAConfig]:
        """Get FSA configuration."""
        return self._fsa_configs.get(name)

    def get_version_history(self, name: str) -> List[Tuple[str, datetime.datetime]]:
        """Get version history for an FSA."""
        return list(self._version_history.get(name, []))

    def add_listener(
        self,
        listener: Callable[[str, str, BaseFSA], None],
    ) -> None:
        """Add a listener for FSA events (load, unload, swap)."""
        self._listeners.append(listener)

    def _notify_listeners(self, event: str, name: str, fsa: BaseFSA) -> None:
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                listener(event, name, fsa)
            except Exception as e:
                logger.error(f"FSA listener error: {e}")

    async def load_from_directory(
        self,
        directory: str,
        pattern: str = "*.py",
    ) -> List[str]:
        """
        Load all FSA modules from a directory.

        Args:
            directory: Directory path
            pattern: File pattern to match

        Returns:
            List of loaded FSA names
        """
        loaded = []
        dir_path = Path(directory)

        for file_path in dir_path.glob(pattern):
            if file_path.name.startswith("_"):
                continue

            try:
                module = self._load_module(str(file_path))

                # Find FSA classes in module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        hasattr(obj, "execute")
                        and hasattr(obj, "name")
                        and name != "AbstractFSA"
                    ):
                        config = FSAConfig(
                            name=name,
                            module_path=str(file_path),
                            class_name=name,
                        )
                        await self.load_fsa(config)
                        loaded.append(name)

            except Exception as e:
                logger.error(f"Error loading FSAs from {file_path}: {e}")

        return loaded


# =============================================================================
# Performance Optimizer
# =============================================================================


class PerformanceOptimizer:
    """
    Performance metrics collection and auto-optimization.

    Features:
        - Real-time performance metrics
        - Bottleneck detection
        - Auto-scaling recommendations
        - Resource utilization tracking
    """

    def __init__(self, history_size: int = METRICS_HISTORY_SIZE):
        self._metrics: Dict[str, Deque[PerformanceMetric]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._optimizations: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

        # Profiling state
        self._profiling_enabled = False
        self._profile_data: Dict[str, List[float]] = defaultdict(list)

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
        unit: str = "",
    ) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            unit=unit,
        )

        async with self._lock:
            self._metrics[name].append(metric)

            # Check thresholds
            if name in self._thresholds:
                await self._check_thresholds(name, value)

    async def _check_thresholds(self, name: str, value: float) -> None:
        """Check if metric exceeds thresholds."""
        thresholds = self._thresholds[name]

        if "warning" in thresholds and value > thresholds["warning"]:
            logger.warning(f"Metric '{name}' exceeded warning threshold: {value}")

        if "critical" in thresholds and value > thresholds["critical"]:
            logger.error(f"Metric '{name}' exceeded critical threshold: {value}")
            await self._trigger_optimization(name, value)

    async def _trigger_optimization(self, metric_name: str, value: float) -> None:
        """Trigger auto-optimization based on metric."""
        optimization = {
            "timestamp": datetime.datetime.now().isoformat(),
            "metric": metric_name,
            "value": value,
            "action": "auto_scale" if "execution_time" in metric_name else "alert",
            "status": "pending",
        }
        self._optimizations.append(optimization)

    def set_threshold(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        critical: Optional[float] = None,
    ) -> None:
        """Set thresholds for a metric."""
        self._thresholds[metric_name] = {}
        if warning is not None:
            self._thresholds[metric_name]["warning"] = warning
        if critical is not None:
            self._thresholds[metric_name]["critical"] = critical

    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Get statistical summary for a metric."""
        if name not in self._metrics or not self._metrics[name]:
            return {}

        values = [m.value for m in self._metrics[name]]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        return {name: self.get_metric_stats(name) for name in self._metrics}

    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks."""
        bottlenecks = []

        for name, metrics in self._metrics.items():
            if not metrics:
                continue

            stats = self.get_metric_stats(name)

            # High variance indicates inconsistent performance
            if stats.get("stdev", 0) > stats.get("mean", 1) * 0.5:
                bottlenecks.append({
                    "metric": name,
                    "type": "high_variance",
                    "description": f"High variance in {name}",
                    "mean": stats["mean"],
                    "stdev": stats["stdev"],
                })

            # P99 >> P95 indicates tail latency issues
            if stats.get("p99", 0) > stats.get("p95", 1) * 2:
                bottlenecks.append({
                    "metric": name,
                    "type": "tail_latency",
                    "description": f"Tail latency issue in {name}",
                    "p95": stats["p95"],
                    "p99": stats["p99"],
                })

        return bottlenecks

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on metrics."""
        recommendations = []
        bottlenecks = self.detect_bottlenecks()

        for bottleneck in bottlenecks:
            if bottleneck["type"] == "high_variance":
                recommendations.append({
                    "metric": bottleneck["metric"],
                    "recommendation": "Consider implementing caching or connection pooling",
                    "priority": "medium",
                })
            elif bottleneck["type"] == "tail_latency":
                recommendations.append({
                    "metric": bottleneck["metric"],
                    "recommendation": "Investigate slow queries or external service calls",
                    "priority": "high",
                })

        # Check overall throughput
        execution_metrics = [
            name for name in self._metrics
            if "execution_time" in name
        ]
        for name in execution_metrics:
            stats = self.get_metric_stats(name)
            if stats.get("mean", 0) > 5.0:  # > 5 second average
                recommendations.append({
                    "metric": name,
                    "recommendation": "Consider increasing concurrency or optimizing FSA logic",
                    "priority": "high",
                })

        return recommendations

    @contextlib.contextmanager
    def profile(self, name: str) -> Iterator[None]:
        """Context manager for profiling code blocks."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._profile_data[name].append(duration)
            if self._profiling_enabled:
                logger.debug(f"Profile '{name}': {duration:.4f}s")

    async def profile_async(self, name: str, coro: Coroutine[Any, Any, T]) -> T:
        """Profile an async coroutine."""
        start = time.perf_counter()
        try:
            return await coro
        finally:
            duration = time.perf_counter() - start
            self._profile_data[name].append(duration)
            await self.record_metric(
                f"profile.{name}",
                duration,
                MetricType.TIMER,
                unit="seconds",
            )

    def enable_profiling(self, enabled: bool = True) -> None:
        """Enable or disable profiling output."""
        self._profiling_enabled = enabled

    def get_profile_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of profiled code blocks."""
        summary = {}
        for name, durations in self._profile_data.items():
            if durations:
                summary[name] = {
                    "calls": len(durations),
                    "total_time": sum(durations),
                    "mean_time": statistics.mean(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                }
        return summary

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._profile_data.clear()
        self._optimizations.clear()


# =============================================================================
# Monitoring Dashboard
# =============================================================================


class MonitoringDashboard:
    """
    Real-time monitoring dashboard with WebSocket support.

    Features:
        - WebSocket server for real-time updates
        - Event streaming
        - Health checks
        - Alert management
    """

    def __init__(
        self,
        optimizer: Optional[PerformanceOptimizer] = None,
        hot_swap_manager: Optional[HotSwapManager] = None,
        executor: Optional[ParallelExecutor] = None,
    ):
        self.optimizer = optimizer or PerformanceOptimizer()
        self.hot_swap_manager = hot_swap_manager
        self.executor = executor

        self._events: Deque[MonitoringEvent] = deque(maxlen=1000)
        self._alerts: List[Dict[str, Any]] = []
        self._websocket_clients: Set[Any] = set()
        self._server: Optional[Any] = None
        self._lock = asyncio.Lock()

        # Dashboard state
        self._start_time = datetime.datetime.now()
        self._is_running = False

    async def emit_event(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        """Emit a monitoring event."""
        event = MonitoringEvent(
            event_type=event_type,
            source=source,
            data=data,
            severity=severity,
        )

        async with self._lock:
            self._events.append(event)

        # Broadcast to WebSocket clients
        await self._broadcast({
            "type": "event",
            "event": {
                "event_type": event.event_type,
                "source": event.source,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "severity": event.severity,
            }
        })

        # Check for alert conditions
        if severity in ("error", "critical"):
            await self._create_alert(event)

    async def _create_alert(self, event: MonitoringEvent) -> None:
        """Create an alert from an event."""
        alert = {
            "id": str(uuid.uuid4()),
            "event_type": event.event_type,
            "source": event.source,
            "message": str(event.data),
            "severity": event.severity,
            "timestamp": event.timestamp.isoformat(),
            "acknowledged": False,
        }
        self._alerts.append(alert)

        await self._broadcast({
            "type": "alert",
            "alert": alert,
        })

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data snapshot."""
        uptime = (datetime.datetime.now() - self._start_time).total_seconds()

        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "status": "healthy",
            "metrics": self.optimizer.get_all_metrics() if self.optimizer else {},
            "alerts": [a for a in self._alerts if not a["acknowledged"]],
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "source": e.source,
                    "timestamp": e.timestamp.isoformat(),
                    "severity": e.severity,
                }
                for e in list(self._events)[-20:]
            ],
        }

        if self.executor:
            data["executor"] = self.executor.get_statistics()

        if self.hot_swap_manager:
            data["loaded_fsas"] = list(self.hot_swap_manager.get_all_fsas().keys())

        # Determine overall status
        critical_alerts = [a for a in self._alerts if a["severity"] == "critical" and not a["acknowledged"]]
        if critical_alerts:
            data["status"] = "critical"
        elif self._alerts:
            data["status"] = "warning"

        return data

    def get_health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health = {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "checks": {},
        }

        # Check optimizer
        if self.optimizer:
            bottlenecks = self.optimizer.detect_bottlenecks()
            health["checks"]["optimizer"] = {
                "status": "degraded" if bottlenecks else "healthy",
                "bottlenecks": len(bottlenecks),
            }

        # Check executor
        if self.executor:
            stats = self.executor.get_statistics()
            error_rate = (
                stats["failed_count"] / (stats["completed_count"] + stats["failed_count"])
                if (stats["completed_count"] + stats["failed_count"]) > 0 else 0.0
            )
            health["checks"]["executor"] = {
                "status": "degraded" if error_rate > 0.1 else "healthy",
                "error_rate": error_rate,
                "active_tasks": stats["active_tasks"],
            }

        # Check hot swap manager
        if self.hot_swap_manager:
            fsas = self.hot_swap_manager.get_all_fsas()
            fsa_health = {}
            for name, fsa in fsas.items():
                try:
                    fsa_health[name] = fsa.get_health()
                except Exception:
                    fsa_health[name] = {"healthy": False}

            unhealthy_count = sum(1 for h in fsa_health.values() if not h.get("healthy", False))
            health["checks"]["fsas"] = {
                "status": "degraded" if unhealthy_count > 0 else "healthy",
                "total": len(fsas),
                "unhealthy": unhealthy_count,
                "details": fsa_health,
            }

        # Determine overall status
        if any(c.get("status") == "degraded" for c in health["checks"].values()):
            health["status"] = "degraded"

        return health

    async def start_websocket_server(self, host: str = "0.0.0.0", port: int = DEFAULT_WEBSOCKET_PORT) -> None:
        """Start WebSocket server for real-time monitoring."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed. Run: pip install websockets")
            return

        async def handler(websocket: Any, path: str) -> None:
            """Handle WebSocket connections."""
            self._websocket_clients.add(websocket)
            logger.info(f"WebSocket client connected: {websocket.remote_address}")

            try:
                # Send initial dashboard data
                await websocket.send(json.dumps({
                    "type": "init",
                    "data": self.get_dashboard_data(),
                }))

                # Keep connection alive and handle messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_websocket_message(websocket, data)
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({"error": "Invalid JSON"}))

            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self._websocket_clients.discard(websocket)
                logger.info(f"WebSocket client disconnected: {websocket.remote_address}")

        self._server = await websockets.serve(handler, host, port)
        self._is_running = True
        logger.info(f"WebSocket monitoring server started on ws://{host}:{port}")

    async def _handle_websocket_message(self, websocket: Any, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        msg_type = data.get("type")

        if msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))

        elif msg_type == "get_dashboard":
            await websocket.send(json.dumps({
                "type": "dashboard",
                "data": self.get_dashboard_data(),
            }))

        elif msg_type == "get_health":
            await websocket.send(json.dumps({
                "type": "health",
                "data": self.get_health_check(),
            }))

        elif msg_type == "acknowledge_alert":
            alert_id = data.get("alert_id")
            success = await self.acknowledge_alert(alert_id)
            await websocket.send(json.dumps({
                "type": "alert_acknowledged",
                "success": success,
                "alert_id": alert_id,
            }))

        elif msg_type == "subscribe":
            # Client wants to subscribe to specific events
            pass  # Could implement filtered subscriptions

    async def _broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all WebSocket clients."""
        if not self._websocket_clients:
            return

        message_str = json.dumps(message)

        # Send to all clients, remove dead connections
        dead_clients = set()
        for client in self._websocket_clients:
            try:
                await client.send(message_str)
            except Exception:
                dead_clients.add(client)

        self._websocket_clients -= dead_clients

    async def stop_websocket_server(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._is_running = False
            logger.info("WebSocket monitoring server stopped")

    def generate_html_dashboard(self) -> str:
        """Generate a static HTML dashboard."""
        data = self.get_dashboard_data()
        health = self.get_health_check()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FSA Integration Layer - Monitoring Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
        .header {{ background: linear-gradient(135deg, #16213e, #1a1a2e); padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: #16213e; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        .card h3 {{ margin-top: 0; color: #0f3460; border-bottom: 2px solid #e94560; padding-bottom: 10px; color: #e94560; }}
        .status-healthy {{ color: #4ecca3; }}
        .status-degraded {{ color: #ffc107; }}
        .status-critical {{ color: #e94560; }}
        .metric {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #0f3460; }}
        .metric-value {{ font-weight: bold; color: #4ecca3; }}
        .alert {{ background: #e945601a; border-left: 4px solid #e94560; padding: 10px; margin: 10px 0; border-radius: 0 5px 5px 0; }}
        .event {{ padding: 8px; border-bottom: 1px solid #0f3460; font-size: 0.9em; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; }}
        .badge-info {{ background: #17a2b8; }}
        .badge-warning {{ background: #ffc107; color: #000; }}
        .badge-error {{ background: #e94560; }}
        .refresh-btn {{ background: #e94560; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #d63050; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 FSA Integration Layer Dashboard</h1>
        <p>Status: <span class="status-{health['status']}">{health['status'].upper()}</span></p>
        <p>Uptime: {data['uptime_seconds']:.0f} seconds</p>
        <p>Last Updated: {data['timestamp']}</p>
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
    </div>

    <div class="grid">
        <div class="card">
            <h3>📊 Executor Statistics</h3>
            {"".join(f'<div class="metric"><span>{k}</span><span class="metric-value">{v}</span></div>' for k, v in data.get('executor', {}).items() if not isinstance(v, dict))}
        </div>

        <div class="card">
            <h3>⚡ Loaded FSAs</h3>
            {"".join(f'<div class="metric"><span>{fsa}</span><span class="badge badge-info">Active</span></div>' for fsa in data.get('loaded_fsas', []))}
            {f'<p>No FSAs loaded</p>' if not data.get('loaded_fsas') else ''}
        </div>

        <div class="card">
            <h3>🔔 Active Alerts</h3>
            {"".join(f'<div class="alert"><strong>{a["event_type"]}</strong><br>{a["message"]}</div>' for a in data.get('alerts', []))}
            {f'<p class="status-healthy">No active alerts</p>' if not data.get('alerts') else ''}
        </div>

        <div class="card">
            <h3>📝 Recent Events</h3>
            {"".join(f'<div class="event"><span class="badge badge-{e["severity"]}">{e["severity"]}</span> {e["event_type"]} - {e["source"]}</div>' for e in data.get('recent_events', [])[-10:])}
        </div>

        <div class="card">
            <h3>💪 Health Checks</h3>
            {"".join(f'<div class="metric"><span>{name}</span><span class="status-{check.get("status", "healthy")}">{check.get("status", "unknown").upper()}</span></div>' for name, check in health.get('checks', {}).items())}
        </div>

        <div class="card">
            <h3>📈 Performance Metrics</h3>
            {"".join(f'<div class="metric"><span>{name}</span><span class="metric-value">{stats.get("mean", 0):.3f} (avg)</span></div>' for name, stats in list(data.get('metrics', {}).items())[:10])}
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        """
        return html


# =============================================================================
# Workflow Orchestrator
# =============================================================================


class WorkflowOrchestrator:
    """
    Orchestrates complex FSA workflows with parallel execution support.
    """

    def __init__(
        self,
        executor: ParallelExecutor,
        hot_swap_manager: HotSwapManager,
        monitoring: MonitoringDashboard,
    ):
        self.executor = executor
        self.hot_swap_manager = hot_swap_manager
        self.monitoring = monitoring

        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._execution_history: Deque[Dict[str, Any]] = deque(maxlen=100)

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.name] = workflow
        logger.info(f"Registered workflow: {workflow.name} v{workflow.version}")

    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """Get a workflow by name."""
        return self._workflows.get(name)

    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.

        Args:
            workflow_name: Name of workflow to execute
            input_data: Input data for the workflow
            timeout: Optional timeout

        Returns:
            Workflow execution results
        """
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")

        workflow_id = str(uuid.uuid4())
        start_time = datetime.datetime.now()

        await self.monitoring.emit_event(
            "workflow_started",
            workflow_name,
            {"workflow_id": workflow_id, "input_keys": list(input_data.keys())},
        )

        try:
            # Group steps by parallel execution
            step_groups = self._group_parallel_steps(workflow.steps)

            results: Dict[str, Any] = {"input": input_data}
            step_results: Dict[str, Any] = {}

            for group in step_groups:
                if len(group) == 1:
                    # Sequential execution
                    step = group[0]
                    result = await self._execute_step(
                        step, results, workflow_id, timeout
                    )
                    step_results[step.name] = result
                    results[step.name] = result
                else:
                    # Parallel execution
                    tasks = []
                    for step in group:
                        tasks.append(
                            self._execute_step(step, results, workflow_id, timeout)
                        )

                    group_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for step, result in zip(group, group_results):
                        step_results[step.name] = result
                        results[step.name] = result

            # Record execution
            execution_record = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_name,
                "start_time": start_time.isoformat(),
                "end_time": datetime.datetime.now().isoformat(),
                "status": "completed",
                "results": step_results,
            }
            self._execution_history.append(execution_record)

            await self.monitoring.emit_event(
                "workflow_completed",
                workflow_name,
                {"workflow_id": workflow_id, "duration": (datetime.datetime.now() - start_time).total_seconds()},
            )

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "results": step_results,
            }

        except Exception as e:
            await self.monitoring.emit_event(
                "workflow_failed",
                workflow_name,
                {"workflow_id": workflow_id, "error": str(e)},
                severity="error",
            )

            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
            }

    def _group_parallel_steps(
        self,
        steps: List[WorkflowStep],
    ) -> List[List[WorkflowStep]]:
        """Group steps that can be executed in parallel."""
        groups: List[List[WorkflowStep]] = []
        current_group: List[WorkflowStep] = []
        current_parallel_group: Optional[str] = None

        for step in steps:
            if step.parallel_group:
                if step.parallel_group == current_parallel_group:
                    current_group.append(step)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [step]
                    current_parallel_group = step.parallel_group
            else:
                if current_group:
                    groups.append(current_group)
                groups.append([step])
                current_group = []
                current_parallel_group = None

        if current_group:
            groups.append(current_group)

        return groups

    async def _execute_step(
        self,
        step: WorkflowStep,
        context_data: Dict[str, Any],
        workflow_id: str,
        timeout: Optional[float],
    ) -> Any:
        """Execute a single workflow step."""
        fsa = self.hot_swap_manager.get_fsa(step.fsa_name)
        if not fsa:
            raise ValueError(f"FSA not found: {step.fsa_name}")

        # Map input data
        step_input = {}
        for target_key, source_key in step.input_mapping.items():
            if "." in source_key:
                parts = source_key.split(".")
                value = context_data
                for part in parts:
                    value = value.get(part, {}) if isinstance(value, dict) else {}
                step_input[target_key] = value
            else:
                step_input[target_key] = context_data.get(source_key)

        # Add unmapped input data
        for key, value in context_data.get("input", {}).items():
            if key not in step_input:
                step_input[key] = value

        # Create execution context
        exec_context = ExecutionContext(
            workflow_id=workflow_id,
            input_data=step_input,
        )

        # Execute
        result = await self.executor.execute_single(
            fsa,
            exec_context,
            timeout=step.timeout or timeout,
        )

        return result


# =============================================================================
# FSA Integration Layer (Main Class)
# =============================================================================


class FSAIntegrationLayer:
    """
    Main FSA Integration Layer - Full Production System.

    Orchestrates all components for FSA workflow execution with:
        - Parallel execution engine
        - Error recovery and fault tolerance
        - Real-time monitoring
        - Hot-swapping capabilities
        - Performance optimization

    Example:
        >>> layer = FSAIntegrationLayer()
        >>> await layer.initialize()
        >>> await layer.load_fsa(config)
        >>> result = await layer.execute("my_fsa", {"query": "test"})
        >>> await layer.start_monitoring(port=8765)
    """

    def __init__(
        self,
        max_concurrency: int = DEFAULT_CONCURRENCY_LIMIT,
        enable_monitoring: bool = True,
        enable_optimization: bool = True,
    ):
        # Core components
        self.error_recovery = ErrorRecoveryManager()
        self.executor = ParallelExecutor(
            max_concurrency=max_concurrency,
            error_recovery=self.error_recovery,
        )
        self.hot_swap_manager = HotSwapManager()

        # Optional components
        self.optimizer = PerformanceOptimizer() if enable_optimization else None
        self.monitoring = MonitoringDashboard(
            optimizer=self.optimizer,
            hot_swap_manager=self.hot_swap_manager,
            executor=self.executor,
        ) if enable_monitoring else None

        # Workflow orchestrator
        self.orchestrator = WorkflowOrchestrator(
            executor=self.executor,
            hot_swap_manager=self.hot_swap_manager,
            monitoring=self.monitoring,
        ) if self.monitoring else None

        # State
        self._initialized = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize the integration layer."""
        if self._initialized:
            return

        logger.info("Initializing FSA Integration Layer...")

        # Set up default error handlers
        self.error_recovery.add_retry_predicate(
            lambda e: "temporary" in str(e).lower() or "timeout" in str(e).lower()
        )

        # Set up monitoring thresholds
        if self.optimizer:
            self.optimizer.set_threshold("execution_time", warning=5.0, critical=30.0)
            self.optimizer.set_threshold("error_rate", warning=0.1, critical=0.5)

        # Register FSA lifecycle listeners
        if self.monitoring:
            self.hot_swap_manager.add_listener(self._on_fsa_lifecycle_event)

        self._initialized = True
        logger.info("FSA Integration Layer initialized")

    def _on_fsa_lifecycle_event(self, event: str, name: str, fsa: BaseFSA) -> None:
        """Handle FSA lifecycle events."""
        if self.monitoring:
            asyncio.create_task(
                self.monitoring.emit_event(
                    f"fsa_{event}",
                    name,
                    {"fsa_name": name, "event": event},
                )
            )

    async def load_fsa(self, config: FSAConfig) -> BaseFSA:
        """Load an FSA from configuration."""
        return await self.hot_swap_manager.load_fsa(config)

    async def unload_fsa(self, name: str) -> bool:
        """Unload an FSA."""
        return await self.hot_swap_manager.unload_fsa(name)

    async def execute(
        self,
        fsa_name: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
        priority: Priority = Priority.NORMAL,
    ) -> Any:
        """
        Execute an FSA.

        Args:
            fsa_name: Name of the FSA to execute
            input_data: Input data for execution
            timeout: Optional timeout
            priority: Execution priority

        Returns:
            Execution result
        """
        fsa = self.hot_swap_manager.get_fsa(fsa_name)
        if not fsa:
            raise ValueError(f"FSA not found: {fsa_name}")

        context = ExecutionContext(input_data=input_data)

        # Profile execution if optimizer available
        if self.optimizer:
            result = await self.optimizer.profile_async(
                f"fsa.{fsa_name}",
                self.executor.execute_single(fsa, context, timeout=timeout),
            )

            # Record metrics
            await self.optimizer.record_metric(
                f"fsa.{fsa_name}.execution_time",
                context.duration or 0.0,
                MetricType.TIMER,
                unit="seconds",
            )
        else:
            result = await self.executor.execute_single(fsa, context, timeout=timeout)

        return result

    async def execute_parallel(
        self,
        tasks: List[Tuple[str, Dict[str, Any]]],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """
        Execute multiple FSAs in parallel.

        Args:
            tasks: List of (fsa_name, input_data) tuples
            timeout: Optional timeout

        Returns:
            List of results
        """
        fsa_tasks = []
        for fsa_name, input_data in tasks:
            fsa = self.hot_swap_manager.get_fsa(fsa_name)
            if not fsa:
                raise ValueError(f"FSA not found: {fsa_name}")
            context = ExecutionContext(input_data=input_data)
            fsa_tasks.append((fsa, context))

        return await self.executor.execute_parallel(
            fsa_tasks,
            timeout=timeout,
            return_exceptions=True,
        )

    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute a registered workflow."""
        if not self.orchestrator:
            raise RuntimeError("Workflow orchestration not available")

        return await self.orchestrator.execute_workflow(
            workflow_name, input_data, timeout
        )

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        if not self.orchestrator:
            raise RuntimeError("Workflow orchestration not available")

        self.orchestrator.register_workflow(workflow)

    async def hot_swap(
        self,
        name: str,
        new_config: FSAConfig,
        graceful: bool = True,
    ) -> BaseFSA:
        """Hot-swap an FSA implementation."""
        return await self.hot_swap_manager.hot_swap(name, new_config, graceful)

    async def start_monitoring(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_WEBSOCKET_PORT,
    ) -> None:
        """Start the monitoring WebSocket server."""
        if not self.monitoring:
            raise RuntimeError("Monitoring not enabled")

        await self.monitoring.start_websocket_server(host, port)

    async def stop_monitoring(self) -> None:
        """Stop the monitoring server."""
        if self.monitoring:
            await self.monitoring.stop_websocket_server()

    def get_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        if self.monitoring:
            return self.monitoring.get_health_check()

        return {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "checks": {},
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        stats = {
            "executor": self.executor.get_statistics(),
            "error_recovery": self.error_recovery.get_statistics(),
            "loaded_fsas": list(self.hot_swap_manager.get_all_fsas().keys()),
        }

        if self.optimizer:
            stats["performance"] = self.optimizer.get_all_metrics()
            stats["bottlenecks"] = self.optimizer.detect_bottlenecks()
            stats["recommendations"] = self.optimizer.get_optimization_recommendations()

        return stats

    def generate_dashboard_html(self, output_path: str) -> str:
        """Generate static HTML dashboard."""
        if not self.monitoring:
            raise RuntimeError("Monitoring not enabled")

        html = self.monitoring.generate_html_dashboard()

        # Write using subprocess
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            escaped = html.replace("'", "''")
            subprocess.run(
                ["powershell", "-Command", f"Set-Content -Path '{output_path}' -Value '{escaped}' -Encoding UTF8"],
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["tee", output_path],
                input=html.encode("utf-8"),
                check=True,
                capture_output=True,
            )

        logger.info(f"Generated dashboard: {output_path}")
        return output_path

    async def shutdown(self, graceful: bool = True) -> None:
        """Shutdown the integration layer."""
        logger.info("Shutting down FSA Integration Layer...")

        if graceful:
            # Wait for active tasks
            await asyncio.sleep(1)
            self.executor.cancel_all()
        else:
            self.executor.cancel_all()

        await self.stop_monitoring()

        self._shutdown_event.set()
        logger.info("FSA Integration Layer shutdown complete")


# =============================================================================
# CLI Interface
# =============================================================================


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fsa_integration_layer",
        description="FSA Integration Layer - Production System for FSA Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start server command
    server_parser = subparsers.add_parser("server", help="Start monitoring server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Server host")
    server_parser.add_argument("--port", type=int, default=8765, help="Server port")
    server_parser.add_argument("--concurrency", type=int, default=10, help="Max concurrency")

    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Generate static dashboard")
    dashboard_parser.add_argument("--output", "-o", default="dashboard.html", help="Output file")

    # Health check command
    health_parser = subparsers.add_parser("health", help="Check system health")
    health_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Load FSA command
    load_parser = subparsers.add_parser("load", help="Load an FSA")
    load_parser.add_argument("--module", "-m", required=True, help="Module path")
    load_parser.add_argument("--class", "-c", dest="class_name", required=True, help="Class name")
    load_parser.add_argument("--name", "-n", help="FSA name (default: class name)")

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute an FSA")
    exec_parser.add_argument("fsa_name", help="FSA name")
    exec_parser.add_argument("--input", "-i", help="Input JSON file or string")
    exec_parser.add_argument("--timeout", type=float, help="Execution timeout")

    # General options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--version", action="version", version="%(prog)s 2.0.0")

    return parser


async def run_server(args: argparse.Namespace) -> None:
    """Run the monitoring server."""
    layer = FSAIntegrationLayer(max_concurrency=args.concurrency)
    await layer.initialize()

    await layer.start_monitoring(host=args.host, port=args.port)

    print(f"Monitoring server running on ws://{args.host}:{args.port}")
    print("Press Ctrl+C to stop...")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await layer.shutdown()


async def main_async(args: argparse.Namespace) -> int:
    """Async main function."""
    if args.command == "server":
        await run_server(args)
        return 0

    layer = FSAIntegrationLayer()
    await layer.initialize()

    try:
        if args.command == "dashboard":
            output = layer.generate_dashboard_html(args.output)
            print(f"Dashboard generated: {output}")

        elif args.command == "health":
            health = layer.get_health()
            if args.json:
                print(json.dumps(health, indent=2))
            else:
                print(f"Status: {health['status'].upper()}")
                for name, check in health.get("checks", {}).items():
                    print(f"  {name}: {check.get('status', 'unknown')}")

        elif args.command == "stats":
            stats = layer.get_statistics()
            if args.json:
                print(json.dumps(stats, indent=2, default=str))
            else:
                print("Executor Statistics:")
                for k, v in stats.get("executor", {}).items():
                    if not isinstance(v, dict):
                        print(f"  {k}: {v}")
                print(f"\nLoaded FSAs: {stats.get('loaded_fsas', [])}")

        elif args.command == "load":
            config = FSAConfig(
                name=args.name or args.class_name,
                module_path=args.module,
                class_name=args.class_name,
            )
            await layer.load_fsa(config)
            print(f"Loaded FSA: {config.name}")

        elif args.command == "execute":
            input_data = {}
            if args.input:
                if args.input.startswith("{"):
                    input_data = json.loads(args.input)
                elif Path(args.input).exists():
                    with open(args.input) as f:
                        input_data = json.load(f)

            result = await layer.execute(
                args.fsa_name,
                input_data,
                timeout=args.timeout,
            )
            print(json.dumps(result, indent=2, default=str))

        else:
            print("Use --help for usage information")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1

    finally:
        await layer.shutdown(graceful=False)


# =============================================================================
# Production Configuration Loader
# =============================================================================


def load_production_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load production configuration from JSON file.

    Args:
        config_path: Path to configuration file. If None, uses default location.

    Returns:
        Configuration dictionary with all production settings.

    Example:
        >>> config = load_production_config()
        >>> print(config["parallel_executor"]["max_concurrency"])
        50
    """
    if config_path is None:
        # Try default locations
        search_paths = [
            Path(__file__).parent / "production_config.json",
            Path.cwd() / "production_config.json",
            Path.home() / ".config" / "fsa" / "production_config.json",
        ]
        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path is None or not Path(config_path).exists():
        logger.warning("Production config not found, using defaults")
        return get_default_production_config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"Loaded production config from: {config_path}")
        return config
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return get_default_production_config()


def get_default_production_config() -> Dict[str, Any]:
    """
    Get default production configuration.

    Returns:
        Default configuration dictionary.
    """
    return {
        "parallel_executor": {
            "max_concurrency": DEFAULT_CONCURRENCY_LIMIT,
            "task_queue_size": 1000,
            "default_task_timeout": 60.0,
        },
        "error_recovery_manager": {
            "retry": {
                "max_attempts": DEFAULT_MAX_RETRIES,
                "base_delay_seconds": DEFAULT_RETRY_DELAY,
                "max_delay_seconds": 60.0,
                "exponential_base": 2.0,
                "jitter_enabled": True,
            },
            "circuit_breaker": {
                "failure_threshold": DEFAULT_CIRCUIT_THRESHOLD,
                "recovery_timeout_seconds": DEFAULT_CIRCUIT_TIMEOUT,
                "half_open_max_calls": 3,
            },
        },
        "monitoring_dashboard": {
            "websocket": {
                "host": "0.0.0.0",
                "port": DEFAULT_WEBSOCKET_PORT,
                "max_connections": 100,
            },
            "metrics": {
                "history_size": METRICS_HISTORY_SIZE,
                "collection_interval_seconds": 5,
            },
        },
        "hot_swap_manager": {
            "graceful_shutdown": {
                "drain_timeout_seconds": 30,
            },
            "version_management": {
                "max_versions_retained": 5,
            },
        },
        "performance_optimizer": {
            "profiling": {
                "enabled": False,
                "sample_rate": 0.1,
            },
            "caching": {
                "enabled": True,
                "max_size_mb": 256,
            },
        },
    }


async def create_production_layer(
    config_path: Optional[str] = None,
    **overrides,
) -> FSAIntegrationLayer:
    """
    Create a production-ready FSA Integration Layer with optimized settings.

    Args:
        config_path: Path to production config file
        **overrides: Override specific configuration values

    Returns:
        Initialized FSAIntegrationLayer instance

    Example:
        >>> layer = await create_production_layer()
        >>> await layer.execute("my_fsa", {"input": "data"})

        >>> # With custom config
        >>> layer = await create_production_layer(
        ...     config_path="custom_config.json",
        ...     max_concurrency=100
        ... )
    """
    config = load_production_config(config_path)

    # Apply overrides
    executor_config = config.get("parallel_executor", {})
    max_concurrency = overrides.get(
        "max_concurrency",
        executor_config.get("max_concurrency", DEFAULT_CONCURRENCY_LIMIT)
    )

    monitoring_config = config.get("monitoring_dashboard", {})
    enable_monitoring = overrides.get(
        "enable_monitoring",
        monitoring_config.get("enabled", True)
    )

    optimizer_config = config.get("performance_optimizer", {})
    enable_optimization = overrides.get(
        "enable_optimization",
        optimizer_config.get("enabled", True)
    )

    # Create layer with production settings
    layer = FSAIntegrationLayer(
        max_concurrency=max_concurrency,
        enable_monitoring=enable_monitoring,
        enable_optimization=enable_optimization,
    )

    # Apply additional configuration
    if layer.error_recovery:
        retry_config = config.get("error_recovery_manager", {}).get("retry", {})
        layer.error_recovery.max_retries = retry_config.get("max_attempts", DEFAULT_MAX_RETRIES)
        layer.error_recovery.base_delay = retry_config.get("base_delay_seconds", DEFAULT_RETRY_DELAY)
        layer.error_recovery.max_delay = retry_config.get("max_delay_seconds", 60.0)
        layer.error_recovery.jitter = retry_config.get("jitter_enabled", True)

    if layer.optimizer:
        opt_config = config.get("performance_optimizer", {})
        thresholds = opt_config.get("bottleneck_detection", {})
        if thresholds.get("enabled", True):
            layer.optimizer.set_threshold(
                "execution_time",
                warning=thresholds.get("latency_threshold_ms", 1000) / 1000,
                critical=thresholds.get("latency_threshold_ms", 1000) / 1000 * 3,
            )

    await layer.initialize()

    logger.info("Production FSA Integration Layer initialized")
    return layer


def main() -> int:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.command:
        parser.print_help()
        return 0

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())

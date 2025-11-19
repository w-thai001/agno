"""
Base classes and utilities for data connectors.

Provides connection pooling, retry logic, and base connector interfaces.
"""

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Queue, Empty, Full
from typing import Any, Callable, Dict, Generic, Iterator, Optional, TypeVar, List
from datetime import datetime
import threading

from agno.utils.log import logger

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt with exponential backoff."""
        import random

        delay = min(self.initial_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


@dataclass
class DataConnectorConfig:
    """Base configuration for data connectors."""

    connection_timeout: int = 30
    read_timeout: int = 300
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    pool_size: int = 5
    pool_timeout: int = 30
    enable_metrics: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionPool(Generic[T]):
    """Thread-safe connection pool with health checking and auto-cleanup."""

    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 5,
        timeout: int = 30,
        health_check: Optional[Callable[[T], bool]] = None,
        cleanup: Optional[Callable[[T], None]] = None,
    ):
        """
        Initialize connection pool.

        Args:
            factory: Callable that creates new connections
            max_size: Maximum number of connections in pool
            timeout: Timeout in seconds for acquiring connection
            health_check: Optional function to check connection health
            cleanup: Optional cleanup function for connections
        """
        self.factory = factory
        self.max_size = max_size
        self.timeout = timeout
        self.health_check = health_check
        self.cleanup = cleanup

        self._pool: Queue[T] = Queue(maxsize=max_size)
        self._size = 0
        self._lock = threading.Lock()
        self._metrics = {
            "created": 0,
            "acquired": 0,
            "released": 0,
            "health_check_failures": 0,
        }

    def _create_connection(self) -> T:
        """Create a new connection using the factory."""
        with self._lock:
            if self._size >= self.max_size:
                raise RuntimeError(f"Connection pool exhausted (max_size={self.max_size})")

            connection = self.factory()
            self._size += 1
            self._metrics["created"] += 1
            logger.debug(f"Created new connection (pool size: {self._size}/{self.max_size})")
            return connection

    def _is_healthy(self, connection: T) -> bool:
        """Check if connection is healthy."""
        if self.health_check is None:
            return True

        try:
            return self.health_check(connection)
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._metrics["health_check_failures"] += 1
            return False

    @contextmanager
    def acquire(self) -> Iterator[T]:
        """
        Acquire a connection from the pool.

        Yields:
            A connection from the pool

        Raises:
            Empty: If no connection available within timeout
        """
        connection = None
        try:
            # Try to get existing connection from pool
            try:
                connection = self._pool.get(timeout=self.timeout)

                # Health check
                if not self._is_healthy(connection):
                    logger.warning("Connection failed health check, creating new one")
                    if self.cleanup:
                        try:
                            self.cleanup(connection)
                        except Exception as e:
                            logger.error(f"Error cleaning up unhealthy connection: {e}")
                    with self._lock:
                        self._size -= 1
                    connection = self._create_connection()
            except Empty:
                # Create new connection if pool is empty
                connection = self._create_connection()

            self._metrics["acquired"] += 1
            yield connection

        finally:
            # Return connection to pool
            if connection is not None:
                try:
                    self._pool.put(connection, timeout=1)
                    self._metrics["released"] += 1
                except Full:
                    # Pool is full, cleanup connection
                    logger.warning("Pool full, cleaning up connection")
                    if self.cleanup:
                        try:
                            self.cleanup(connection)
                        except Exception as e:
                            logger.error(f"Error cleaning up connection: {e}")
                    with self._lock:
                        self._size -= 1

    def close_all(self):
        """Close all connections in the pool."""
        logger.info(f"Closing connection pool (size: {self._size})")

        while not self._pool.empty():
            try:
                connection = self._pool.get_nowait()
                if self.cleanup:
                    try:
                        self.cleanup(connection)
                    except Exception as e:
                        logger.error(f"Error cleaning up connection: {e}")
            except Empty:
                break

        with self._lock:
            self._size = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics."""
        return {
            **self._metrics,
            "current_size": self._size,
            "max_size": self.max_size,
            "available": self._pool.qsize(),
        }


def with_retry(
    func: Callable[..., T],
    retry_config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[..., T]:
    """
    Decorator to add retry logic with exponential backoff.

    Args:
        func: Function to wrap with retry logic
        retry_config: Retry configuration
        on_retry: Optional callback called on each retry

    Returns:
        Wrapped function with retry logic
    """
    config = retry_config or RetryConfig()

    def wrapper(*args, **kwargs) -> T:
        last_exception = None

        for attempt in range(config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < config.max_retries:
                    delay = config.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception as callback_error:
                            logger.error(f"Error in retry callback: {callback_error}")

                    time.sleep(delay)
                else:
                    logger.error(f"All {config.max_retries + 1} attempts failed")

        raise last_exception  # type: ignore

    return wrapper


class DataConnectorBase(ABC):
    """Abstract base class for all data connectors."""

    def __init__(self, config: Optional[DataConnectorConfig] = None):
        """
        Initialize base connector.

        Args:
            config: Connector configuration
        """
        self.config = config or DataConnectorConfig()
        self._metrics = {
            "connections": 0,
            "reads": 0,
            "writes": 0,
            "errors": 0,
            "last_activity": None,
        }
        self._is_connected = False

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to data source."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to data source."""
        pass

    @abstractmethod
    def read(self, query: Any, **kwargs) -> Any:
        """
        Read data from source.

        Args:
            query: Query or identifier for data to read
            **kwargs: Additional parameters

        Returns:
            Retrieved data
        """
        pass

    def write(self, data: Any, target: str, **kwargs) -> None:
        """
        Write data to source.

        Args:
            data: Data to write
            target: Target location/table
            **kwargs: Additional parameters
        """
        raise NotImplementedError("Write operation not supported by this connector")

    def test_connection(self) -> bool:
        """
        Test if connection is working.

        Returns:
            True if connection is healthy
        """
        try:
            self.connect()
            return self._is_connected
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _record_metric(self, metric: str, value: Any = 1):
        """Record a metric."""
        if self.config.enable_metrics:
            if metric in ["connections", "reads", "writes", "errors"]:
                self._metrics[metric] += value
            else:
                self._metrics[metric] = value
            self._metrics["last_activity"] = datetime.utcnow().isoformat()

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        return self._metrics.copy()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False

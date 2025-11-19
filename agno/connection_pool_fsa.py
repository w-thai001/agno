"""Connection Pool Finite State Automaton for managing pooled connections."""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Set

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for connection lifecycle."""
    IDLE = "idle"
    ACTIVE = "active"
    HEALTH_CHECK = "health_check"
    CLOSED = "closed"


class PoolState(Enum):
    """States for the connection pool."""
    INITIALIZING = "initializing"
    READY = "ready"
    DRAINING = "draining"
    SHUTDOWN = "shutdown"


@dataclass
class Connection:
    """Represents a pooled connection."""
    conn_id: str
    state: State
    handle: Any
    created_at: float
    last_used: float
    use_count: int = 0


class ConnectionPoolFSA:
    """Finite State Automaton for connection pool management."""

    def __init__(
        self,
        max_connections: int = 10,
        idle_timeout: float = 300.0,
        health_check_interval: float = 60.0,
        connection_factory: Optional[Callable] = None
    ):
        self.max_connections = max_connections
        self.idle_timeout = idle_timeout
        self.health_check_interval = health_check_interval
        self.connection_factory = connection_factory or self._default_factory

        self.pool_state = PoolState.INITIALIZING
        self._idle_connections: list[Connection] = []
        self._active_connections: Set[str] = set()
        self._all_connections: dict[str, Connection] = {}
        self._conn_counter = 0
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

        self._transition_pool(PoolState.INITIALIZING, PoolState.READY)
        logger.info(f"Connection pool initialized (max: {max_connections})")

    def acquire(self, timeout: float = 30.0) -> Connection:
        """Acquire a connection from the pool."""
        start_time = time.time()

        with self._condition:
            while True:
                if self.pool_state == PoolState.SHUTDOWN:
                    raise RuntimeError("Pool is shutdown")

                # Try to reuse idle connection
                conn = self._get_idle_connection()
                if conn:
                    return conn

                # Create new connection if under limit
                if len(self._all_connections) < self.max_connections:
                    conn = self._create_connection()
                    return conn

                # Wait for available connection
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                if remaining <= 0:
                    raise TimeoutError("Timeout acquiring connection from pool")

                logger.debug(f"Waiting for connection (active: {len(self._active_connections)})")
                self._condition.wait(timeout=remaining)

    def release(self, connection: Connection):
        """Release connection back to the pool."""
        with self._lock:
            if connection.conn_id not in self._all_connections:
                logger.warning(f"Connection {connection.conn_id} not in pool")
                return

            if connection.conn_id not in self._active_connections:
                logger.warning(f"Connection {connection.conn_id} not active")
                return

            # Update connection state
            connection.last_used = time.time()
            self._active_connections.remove(connection.conn_id)

            # Check if connection should be closed
            if self._should_close_connection(connection):
                self._close_connection(connection)
            else:
                self._transition_conn(connection, connection.state, State.IDLE)
                self._idle_connections.append(connection)
                logger.debug(f"Released connection {connection.conn_id} to pool")

            self._condition.notify()

    def shutdown(self, wait: bool = True):
        """Shutdown the pool and close all connections."""
        with self._lock:
            logger.info("Shutting down connection pool")
            self._transition_pool(self.pool_state, PoolState.DRAINING)

            if wait:
                # Close idle connections immediately
                for conn in list(self._idle_connections):
                    self._close_connection(conn)
                self._idle_connections.clear()

            self._transition_pool(PoolState.DRAINING, PoolState.SHUTDOWN)

    def cleanup_idle(self):
        """Remove connections that exceeded idle timeout."""
        with self._lock:
            now = time.time()
            to_remove = []

            for conn in self._idle_connections:
                idle_time = now - conn.last_used
                if idle_time > self.idle_timeout:
                    to_remove.append(conn)
                    logger.info(f"Removing idle connection {conn.conn_id} (idle: {idle_time:.1f}s)")

            for conn in to_remove:
                self._idle_connections.remove(conn)
                self._close_connection(conn)

    def get_stats(self) -> dict:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_state": self.pool_state.value,
                "total_connections": len(self._all_connections),
                "active_connections": len(self._active_connections),
                "idle_connections": len(self._idle_connections),
                "max_connections": self.max_connections
            }

    def _get_idle_connection(self) -> Optional[Connection]:
        """Get and validate an idle connection."""
        while self._idle_connections:
            conn = self._idle_connections.pop(0)

            # Perform health check
            if self._health_check(conn):
                conn.use_count += 1
                self._active_connections.add(conn.conn_id)
                self._transition_conn(conn, State.IDLE, State.ACTIVE)
                logger.debug(f"Reusing connection {conn.conn_id} (uses: {conn.use_count})")
                return conn
            else:
                logger.warning(f"Health check failed for {conn.conn_id}")
                self._close_connection(conn)

        return None

    def _create_connection(self) -> Connection:
        """Create a new connection."""
        self._conn_counter += 1
        conn_id = f"conn_{self._conn_counter}"

        try:
            handle = self.connection_factory()
            conn = Connection(
                conn_id=conn_id,
                state=State.ACTIVE,
                handle=handle,
                created_at=time.time(),
                last_used=time.time(),
                use_count=1
            )

            self._all_connections[conn_id] = conn
            self._active_connections.add(conn_id)
            logger.info(f"Created new connection {conn_id}")
            return conn

        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise

    def _health_check(self, connection: Connection) -> bool:
        """Perform health check on connection."""
        self._transition_conn(connection, connection.state, State.HEALTH_CHECK)

        # Simple health check: verify handle exists and check age
        is_healthy = (
            connection.handle is not None and
            time.time() - connection.last_used < self.health_check_interval * 2
        )

        logger.debug(f"Health check for {connection.conn_id}: {'passed' if is_healthy else 'failed'}")
        return is_healthy

    def _should_close_connection(self, connection: Connection) -> bool:
        """Determine if connection should be closed instead of pooled."""
        return self.pool_state in (PoolState.DRAINING, PoolState.SHUTDOWN)

    def _close_connection(self, connection: Connection):
        """Close and remove a connection."""
        self._transition_conn(connection, connection.state, State.CLOSED)
        self._all_connections.pop(connection.conn_id, None)
        logger.debug(f"Closed connection {connection.conn_id}")

    def _default_factory(self) -> Any:
        """Default connection factory."""
        return {"created_at": time.time()}

    def _transition_conn(self, conn: Connection, from_state: State, to_state: State):
        """Transition connection state."""
        conn.state = to_state
        logger.debug(f"Connection {conn.conn_id}: {from_state.value} -> {to_state.value}")

    def _transition_pool(self, from_state: PoolState, to_state: PoolState):
        """Transition pool state."""
        self.pool_state = to_state
        logger.debug(f"Pool state: {from_state.value} -> {to_state.value}")

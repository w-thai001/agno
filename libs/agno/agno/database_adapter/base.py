"""
Base Database Adapter with FSA

Provides the base class for database adapters with Finite State Automaton
for connection lifecycle management.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from agno.database_adapter.exceptions import (
    ConnectionError,
    InvalidStateTransition,
    QueryError,
    UnsupportedOperation,
)
from agno.database_adapter.migration import MigrationManager
from agno.database_adapter.query_builder import Query
from agno.database_adapter.retry import RetryConfig, with_retry
from agno.database_adapter.states import ConnectionState, VALID_CONNECTION_TRANSITIONS
from agno.database_adapter.transaction import Transaction, transaction
from agno.utils.log import logger


class DatabaseAdapter(ABC):
    """
    Base class for database adapters with FSA state management.

    Manages connection lifecycle through states:
    DISCONNECTED -> CONNECTING -> CONNECTED -> IN_TRANSACTION -> CONNECTED -> DISCONNECTED

    Provides unified interface for:
    - Connection pooling
    - Query execution
    - Transaction management
    - Schema migrations
    - Error handling with retry logic
    """

    def __init__(
        self,
        connection_string: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
        auto_connect: bool = True,
    ):
        """
        Initialize database adapter.

        Args:
            connection_string: Database connection string
            pool_size: Number of connections in pool (default: 5)
            max_overflow: Maximum overflow connections (default: 10)
            pool_timeout: Timeout for getting connection from pool in seconds (default: 30)
            retry_config: Configuration for retry logic (uses default if None)
            auto_connect: Automatically connect on initialization (default: True)
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.retry_config = retry_config or RetryConfig()

        # FSA state
        self.state = ConnectionState.DISCONNECTED

        # Connection pool and resources
        self._pool: Optional[Any] = None
        self._connection: Optional[Any] = None
        self._migration_manager: Optional[MigrationManager] = None

        # Auto-connect if requested
        if auto_connect:
            self.connect()

    @property
    @abstractmethod
    def db_type(self) -> str:
        """Return the database type identifier."""
        raise NotImplementedError

    def _transition_state(self, new_state: ConnectionState) -> None:
        """
        Transition to a new state if valid.

        Args:
            new_state: Target state

        Raises:
            InvalidStateTransition: If transition is invalid
        """
        if new_state not in VALID_CONNECTION_TRANSITIONS.get(self.state, set()):
            raise InvalidStateTransition(f"Invalid state transition: {self.state} -> {new_state}")

        logger.debug(f"[{self.db_type}] State transition: {self.state} -> {new_state}")
        self.state = new_state

    @abstractmethod
    def _create_pool(self) -> Any:
        """
        Create and return a connection pool.

        Returns:
            Connection pool object

        Raises:
            ConnectionError: If pool creation fails
        """
        raise NotImplementedError

    @abstractmethod
    def _get_connection_from_pool(self) -> Any:
        """
        Get a connection from the pool.

        Returns:
            Database connection object

        Raises:
            ConnectionError: If connection cannot be obtained
        """
        raise NotImplementedError

    @abstractmethod
    def _return_connection_to_pool(self, connection: Any) -> None:
        """
        Return a connection to the pool.

        Args:
            connection: Connection to return
        """
        raise NotImplementedError

    @abstractmethod
    def _close_pool(self) -> None:
        """Close the connection pool and all connections."""
        raise NotImplementedError

    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a query and return results.

        Args:
            query: SQL query or MongoDB query dict
            params: Query parameters

        Returns:
            Query results

        Raises:
            QueryError: If query execution fails
        """
        raise NotImplementedError

    @with_retry()
    def connect(self) -> None:
        """
        Establish connection to the database.

        Uses retry logic for resilience.

        Raises:
            ConnectionError: If connection fails after retries
        """
        try:
            self._transition_state(ConnectionState.CONNECTING)

            # Create connection pool
            self._pool = self._create_pool()
            logger.info(f"[{self.db_type}] Connection pool created (size={self.pool_size})")

            # Get initial connection to verify
            self._connection = self._get_connection_from_pool()

            self._transition_state(ConnectionState.CONNECTED)
            logger.info(f"[{self.db_type}] Successfully connected to database")

        except Exception as e:
            self._transition_state(ConnectionState.ERROR)
            raise ConnectionError(f"Failed to connect to database: {str(e)}") from e

    def disconnect(self) -> None:
        """
        Disconnect from the database and close pool.

        Raises:
            ConnectionError: If disconnection fails
        """
        try:
            if self.state == ConnectionState.DISCONNECTED:
                logger.debug(f"[{self.db_type}] Already disconnected")
                return

            # Return current connection to pool
            if self._connection:
                self._return_connection_to_pool(self._connection)
                self._connection = None

            # Close pool
            if self._pool:
                self._close_pool()
                self._pool = None

            self._transition_state(ConnectionState.DISCONNECTED)
            logger.info(f"[{self.db_type}] Disconnected from database")

        except Exception as e:
            self._transition_state(ConnectionState.ERROR)
            raise ConnectionError(f"Failed to disconnect: {str(e)}") from e

    def reconnect(self) -> None:
        """
        Reconnect to the database.

        Raises:
            ConnectionError: If reconnection fails
        """
        logger.info(f"[{self.db_type}] Attempting to reconnect...")
        self._transition_state(ConnectionState.RECONNECTING)

        try:
            # Close existing connections
            if self.state != ConnectionState.DISCONNECTED:
                try:
                    self.disconnect()
                except Exception as e:
                    logger.warning(f"Error during disconnect before reconnect: {e}")

            # Connect again
            self.connect()

        except Exception as e:
            self._transition_state(ConnectionState.ERROR)
            raise ConnectionError(f"Failed to reconnect: {str(e)}") from e

    def is_connected(self) -> bool:
        """Check if currently connected to the database."""
        return self.state == ConnectionState.CONNECTED

    def query(self) -> Query:
        """
        Create a new query builder.

        Returns:
            Query builder instance
        """
        return Query(self.db_type)

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Context manager for getting a connection from the pool.

        Yields:
            Database connection

        Example:
            with adapter.get_connection() as conn:
                # Use connection
                pass
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to database")

        conn = self._get_connection_from_pool()
        try:
            yield conn
        finally:
            self._return_connection_to_pool(conn)

    def begin_transaction(self) -> Transaction:
        """
        Begin a new transaction.

        Returns:
            Transaction object

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to database")

        self._transition_state(ConnectionState.IN_TRANSACTION)

        conn = self._get_connection_from_pool()
        return Transaction(conn, self.db_type)

    @contextmanager
    def transaction(self) -> Generator[Transaction, None, None]:
        """
        Context manager for transactions.

        Yields:
            Transaction object

        Example:
            with adapter.transaction() as txn:
                # Execute queries
                txn.execute(...)
                # Auto-commit on success, auto-rollback on exception
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to database")

        self._transition_state(ConnectionState.IN_TRANSACTION)

        with self.get_connection() as conn:
            with transaction(conn, self.db_type) as txn:
                yield txn

        self._transition_state(ConnectionState.CONNECTED)

    def get_migration_manager(self) -> MigrationManager:
        """
        Get the migration manager for this adapter.

        Returns:
            MigrationManager instance
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to database")

        if not self._migration_manager:
            self._migration_manager = MigrationManager(self._connection, self.db_type)

        return self._migration_manager

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a query with automatic retry logic.

        Args:
            query: Query string or dict (for MongoDB)
            params: Query parameters

        Returns:
            Query results

        Raises:
            QueryError: If query fails
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to database")

        try:
            return self.execute_query(query, params)
        except Exception as e:
            raise QueryError(f"Query execution failed: {str(e)}") from e

    def fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a query and fetch one result.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            Single result as dict or None

        Raises:
            QueryError: If query fails
        """
        result = self.execute(query, params)

        if hasattr(result, "fetchone"):
            row = result.fetchone()
            if row:
                # Convert to dict if result has keys
                if hasattr(result, "keys"):
                    return dict(zip(result.keys(), row))
                return {"result": row}
            return None

        # For MongoDB or other non-SQL
        if isinstance(result, list) and len(result) > 0:
            return result[0]

        return None

    def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and fetch all results.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            List of results as dicts

        Raises:
            QueryError: If query fails
        """
        result = self.execute(query, params)

        if hasattr(result, "fetchall"):
            rows = result.fetchall()
            # Convert to list of dicts if result has keys
            if hasattr(result, "keys"):
                return [dict(zip(result.keys(), row)) for row in rows]
            return [{"result": row} for row in rows]

        # For MongoDB or other non-SQL
        if isinstance(result, list):
            return result

        return []

    def close(self) -> None:
        """
        Close the adapter and all connections.

        This is a terminal operation.
        """
        try:
            self.disconnect()
            self._transition_state(ConnectionState.CLOSED)
            logger.info(f"[{self.db_type}] Adapter closed")

        except Exception as e:
            logger.error(f"Error closing adapter: {e}")
            self._transition_state(ConnectionState.CLOSED)

    def __enter__(self) -> "DatabaseAdapter":
        """Context manager entry."""
        if not self.is_connected():
            self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()

    def __del__(self) -> None:
        """Destructor - ensure cleanup."""
        try:
            if self.state not in (ConnectionState.DISCONNECTED, ConnectionState.CLOSED):
                self.close()
        except Exception:
            pass  # Ignore errors in destructor

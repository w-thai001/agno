"""
PostgreSQL Database Adapter

Provides PostgreSQL-specific implementation with connection pooling,
query execution, and transaction support.
"""

from typing import Any, Dict, Optional

from agno.database_adapter.base import DatabaseAdapter
from agno.database_adapter.exceptions import ConnectionError, QueryError
from agno.database_adapter.retry import RetryConfig
from agno.utils.log import logger

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import NullPool, QueuePool
except ImportError:
    raise ImportError(
        "PostgreSQL adapter requires sqlalchemy and psycopg. "
        "Install with: pip install sqlalchemy psycopg-binary"
    )


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL database adapter with FSA state management.

    Features:
    - Connection pooling using SQLAlchemy
    - Automatic reconnection with retry logic
    - Transaction support with savepoints
    - Query parameter binding
    - Schema migrations
    """

    def __init__(
        self,
        connection_string: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        retry_config: Optional[RetryConfig] = None,
        auto_connect: bool = True,
        echo: bool = False,
    ):
        """
        Initialize PostgreSQL adapter.

        Args:
            connection_string: PostgreSQL connection string
                              (e.g., 'postgresql://user:pass@localhost/dbname')
            pool_size: Number of connections in pool (default: 5)
            max_overflow: Maximum overflow connections (default: 10)
            pool_timeout: Timeout for getting connection from pool in seconds (default: 30)
            pool_recycle: Recycle connections after N seconds (default: 3600)
            retry_config: Configuration for retry logic (uses default if None)
            auto_connect: Automatically connect on initialization (default: True)
            echo: Echo SQL queries to stdout (default: False)
        """
        self.pool_recycle = pool_recycle
        self.echo = echo
        self._engine: Optional[Engine] = None

        super().__init__(
            connection_string=connection_string,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            retry_config=retry_config,
            auto_connect=auto_connect,
        )

    @property
    def db_type(self) -> str:
        """Return the database type identifier."""
        return "postgres"

    def _create_pool(self) -> Any:
        """
        Create and return a SQLAlchemy engine with connection pooling.

        Returns:
            SQLAlchemy Engine

        Raises:
            ConnectionError: If pool creation fails
        """
        try:
            # Create engine with QueuePool (default)
            self._engine = create_engine(
                self.connection_string,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Verify connections before using
                echo=self.echo,
            )

            logger.debug(f"[PostgreSQL] Engine created with pool_size={self.pool_size}")
            return self._engine

        except Exception as e:
            raise ConnectionError(f"Failed to create PostgreSQL connection pool: {str(e)}") from e

    def _get_connection_from_pool(self) -> Any:
        """
        Get a connection from the pool.

        Returns:
            SQLAlchemy Connection

        Raises:
            ConnectionError: If connection cannot be obtained
        """
        try:
            if not self._engine:
                raise ConnectionError("Engine not initialized")

            conn = self._engine.connect()
            logger.debug("[PostgreSQL] Connection acquired from pool")
            return conn

        except Exception as e:
            raise ConnectionError(f"Failed to get connection from pool: {str(e)}") from e

    def _return_connection_to_pool(self, connection: Any) -> None:
        """
        Return a connection to the pool.

        Args:
            connection: SQLAlchemy Connection to return
        """
        try:
            if connection:
                connection.close()
                logger.debug("[PostgreSQL] Connection returned to pool")

        except Exception as e:
            logger.warning(f"Error returning connection to pool: {e}")

    def _close_pool(self) -> None:
        """Close the connection pool and all connections."""
        try:
            if self._engine:
                self._engine.dispose()
                logger.debug("[PostgreSQL] Connection pool disposed")

        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a query and return results.

        Args:
            query: SQL query string (supports named parameters with :param syntax)
            params: Query parameters as dict

        Returns:
            SQLAlchemy Result object

        Raises:
            QueryError: If query execution fails
        """
        try:
            if not self._connection:
                raise QueryError("No active connection")

            # Convert query string to SQLAlchemy text
            sql = text(query)

            # Execute query with parameters
            if params:
                result = self._connection.execute(sql, params)
            else:
                result = self._connection.execute(sql)

            logger.debug(f"[PostgreSQL] Query executed: {query[:100]}...")
            return result

        except Exception as e:
            raise QueryError(f"Failed to execute query: {str(e)}") from e

    def execute_raw(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Execute a raw SQL query with positional parameters.

        Args:
            query: SQL query string (supports %s placeholders)
            params: Query parameters as tuple

        Returns:
            SQLAlchemy Result object

        Raises:
            QueryError: If query execution fails
        """
        try:
            if not self._connection:
                raise QueryError("No active connection")

            # Get raw DBAPI connection
            raw_conn = self._connection.connection

            cursor = raw_conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            logger.debug(f"[PostgreSQL] Raw query executed: {query[:100]}...")
            return cursor

        except Exception as e:
            raise QueryError(f"Failed to execute raw query: {str(e)}") from e

    def get_table_names(self) -> list:
        """
        Get list of all table names in the database.

        Returns:
            List of table names

        Raises:
            QueryError: If query fails
        """
        query = """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema'
        ORDER BY tablename
        """

        result = self.fetch_all(query)
        return [row.get("tablename") for row in result]

    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """
        Check if a table exists.

        Args:
            table_name: Name of the table
            schema: Schema name (default: public)

        Returns:
            True if table exists, False otherwise
        """
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_name = :table_name
        )
        """

        result = self.fetch_one(query, {"schema": schema, "table_name": table_name})
        return result.get("exists", False) if result else False

    def create_table(self, table_name: str, columns: Dict[str, str], schema: str = "public") -> None:
        """
        Create a table.

        Args:
            table_name: Name of the table
            columns: Dict of column_name -> column_definition
            schema: Schema name (default: public)

        Example:
            adapter.create_table("users", {
                "id": "SERIAL PRIMARY KEY",
                "name": "VARCHAR(100) NOT NULL",
                "email": "VARCHAR(255) UNIQUE",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            })
        """
        column_defs = ", ".join([f"{name} {definition}" for name, definition in columns.items()])
        query = f"CREATE TABLE {schema}.{table_name} ({column_defs})"

        self.execute(query)
        logger.info(f"[PostgreSQL] Created table: {schema}.{table_name}")

    def drop_table(self, table_name: str, schema: str = "public", if_exists: bool = True) -> None:
        """
        Drop a table.

        Args:
            table_name: Name of the table
            schema: Schema name (default: public)
            if_exists: Add IF EXISTS clause (default: True)
        """
        if_exists_clause = "IF EXISTS" if if_exists else ""
        query = f"DROP TABLE {if_exists_clause} {schema}.{table_name}"

        self.execute(query)
        logger.info(f"[PostgreSQL] Dropped table: {schema}.{table_name}")

    def get_engine(self) -> Optional[Engine]:
        """
        Get the underlying SQLAlchemy engine.

        Returns:
            SQLAlchemy Engine or None
        """
        return self._engine

"""
SQLite Database Adapter

Provides SQLite-specific implementation with connection pooling,
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
    from sqlalchemy.pool import StaticPool
except ImportError:
    raise ImportError("SQLite adapter requires sqlalchemy. " "Install with: pip install sqlalchemy")


class SQLiteAdapter(DatabaseAdapter):
    """
    SQLite database adapter with FSA state management.

    Features:
    - Connection pooling using SQLAlchemy (with StaticPool for SQLite)
    - Automatic reconnection with retry logic
    - Transaction support
    - Query parameter binding
    - Schema migrations

    Note:
        SQLite uses StaticPool by default since it's typically single-threaded.
        For multi-threaded applications, consider using PostgreSQL or MySQL.
    """

    def __init__(
        self,
        database_path: str = ":memory:",
        check_same_thread: bool = False,
        retry_config: Optional[RetryConfig] = None,
        auto_connect: bool = True,
        echo: bool = False,
    ):
        """
        Initialize SQLite adapter.

        Args:
            database_path: Path to SQLite database file or ':memory:' for in-memory
            check_same_thread: SQLite check_same_thread parameter (default: False)
            retry_config: Configuration for retry logic (uses default if None)
            auto_connect: Automatically connect on initialization (default: True)
            echo: Echo SQL queries to stdout (default: False)
        """
        self.database_path = database_path
        self.check_same_thread = check_same_thread
        self.echo = echo
        self._engine: Optional[Engine] = None

        # Build connection string
        connection_string = f"sqlite:///{database_path}"

        # SQLite doesn't use traditional pooling
        super().__init__(
            connection_string=connection_string,
            pool_size=1,  # SQLite typically uses single connection
            max_overflow=0,
            pool_timeout=30,
            retry_config=retry_config,
            auto_connect=auto_connect,
        )

    @property
    def db_type(self) -> str:
        """Return the database type identifier."""
        return "sqlite"

    def _create_pool(self) -> Any:
        """
        Create and return a SQLAlchemy engine with StaticPool.

        Returns:
            SQLAlchemy Engine

        Raises:
            ConnectionError: If pool creation fails
        """
        try:
            # Create engine with StaticPool (recommended for SQLite)
            connect_args = {"check_same_thread": self.check_same_thread}

            self._engine = create_engine(
                self.connection_string,
                poolclass=StaticPool,
                connect_args=connect_args,
                echo=self.echo,
            )

            logger.debug(f"[SQLite] Engine created for database: {self.database_path}")
            return self._engine

        except Exception as e:
            raise ConnectionError(f"Failed to create SQLite connection pool: {str(e)}") from e

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
            logger.debug("[SQLite] Connection acquired")
            return conn

        except Exception as e:
            raise ConnectionError(f"Failed to get connection: {str(e)}") from e

    def _return_connection_to_pool(self, connection: Any) -> None:
        """
        Return a connection to the pool.

        Args:
            connection: SQLAlchemy Connection to return
        """
        try:
            if connection:
                connection.close()
                logger.debug("[SQLite] Connection returned")

        except Exception as e:
            logger.warning(f"Error returning connection: {e}")

    def _close_pool(self) -> None:
        """Close the connection pool and all connections."""
        try:
            if self._engine:
                self._engine.dispose()
                logger.debug("[SQLite] Connection pool disposed")

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

            logger.debug(f"[SQLite] Query executed: {query[:100]}...")
            return result

        except Exception as e:
            raise QueryError(f"Failed to execute query: {str(e)}") from e

    def get_table_names(self) -> list:
        """
        Get list of all table names in the database.

        Returns:
            List of table names

        Raises:
            QueryError: If query fails
        """
        query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """

        result = self.fetch_all(query)
        return [row.get("name") for row in result]

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists, False otherwise
        """
        query = """
        SELECT COUNT(*) as count FROM sqlite_master
        WHERE type='table' AND name = :table_name
        """

        result = self.fetch_one(query, {"table_name": table_name})
        return (result.get("count", 0) > 0) if result else False

    def create_table(self, table_name: str, columns: Dict[str, str]) -> None:
        """
        Create a table.

        Args:
            table_name: Name of the table
            columns: Dict of column_name -> column_definition

        Example:
            adapter.create_table("users", {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "name": "TEXT NOT NULL",
                "email": "TEXT UNIQUE",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            })
        """
        column_defs = ", ".join([f"{name} {definition}" for name, definition in columns.items()])
        query = f"CREATE TABLE {table_name} ({column_defs})"

        self.execute(query)
        logger.info(f"[SQLite] Created table: {table_name}")

    def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        Drop a table.

        Args:
            table_name: Name of the table
            if_exists: Add IF EXISTS clause (default: True)
        """
        if_exists_clause = "IF EXISTS" if if_exists else ""
        query = f"DROP TABLE {if_exists_clause} {table_name}"

        self.execute(query)
        logger.info(f"[SQLite] Dropped table: {table_name}")

    def vacuum(self) -> None:
        """
        Optimize the database file by running VACUUM.

        This rebuilds the database file, repacking it into a minimal amount of disk space.
        """
        self.execute("VACUUM")
        logger.info("[SQLite] Database vacuumed")

    def get_database_size(self) -> int:
        """
        Get the size of the database in bytes.

        Returns:
            Database size in bytes

        Raises:
            QueryError: If query fails
        """
        if self.database_path == ":memory:":
            # In-memory database, get page count * page size
            query = "PRAGMA page_count; PRAGMA page_size"
            # This is a simplification; actual implementation would need proper handling
            return 0

        import os

        if os.path.exists(self.database_path):
            return os.path.getsize(self.database_path)
        return 0

    def get_engine(self) -> Optional[Engine]:
        """
        Get the underlying SQLAlchemy engine.

        Returns:
            SQLAlchemy Engine or None
        """
        return self._engine

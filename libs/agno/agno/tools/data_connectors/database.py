"""
Database connectors for SQL and NoSQL databases.

Supports:
- PostgreSQL, MySQL, SQLite, SQL Server (SQL)
- MongoDB, Redis, Elasticsearch (NoSQL)
"""

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from agno.tools.data_connectors.base import (
    ConnectionPool,
    DataConnectorBase,
    DataConnectorConfig,
    with_retry,
)
from agno.utils.log import logger


@dataclass
class DatabaseConfig(DataConnectorConfig):
    """Configuration for database connectors."""

    host: str = "localhost"
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None


class SQLConnector(DataConnectorBase):
    """Generic SQL database connector supporting multiple engines."""

    def __init__(
        self,
        engine: str = "postgresql",
        config: Optional[DatabaseConfig] = None,
        use_pool: bool = True,
        **connection_kwargs,
    ):
        """
        Initialize SQL connector.

        Args:
            engine: Database engine (postgresql, mysql, sqlite, mssql)
            config: Database configuration
            use_pool: Whether to use connection pooling
            **connection_kwargs: Additional connection parameters
        """
        super().__init__(config or DatabaseConfig())
        self.engine = engine.lower()
        self.connection_kwargs = connection_kwargs
        self.use_pool = use_pool
        self._connection = None
        self._pool: Optional[ConnectionPool] = None

        # Set default ports
        default_ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "mssql": 1433,
            "sqlite": None,
        }
        if isinstance(self.config, DatabaseConfig) and self.config.port is None:
            self.config.port = default_ports.get(self.engine)

    def _create_connection(self) -> Any:
        """Create a new database connection."""
        config = self.config
        if not isinstance(config, DatabaseConfig):
            raise ValueError("Invalid config type")

        if self.engine == "postgresql":
            try:
                import psycopg2
            except ImportError:
                raise ImportError(
                    "psycopg2 not installed. Install with: pip install psycopg2-binary"
                )

            conn_params = {
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "user": config.username,
                "password": config.password,
                **self.connection_kwargs,
            }
            return psycopg2.connect(**{k: v for k, v in conn_params.items() if v is not None})

        elif self.engine == "mysql":
            try:
                import pymysql
            except ImportError:
                raise ImportError("pymysql not installed. Install with: pip install pymysql")

            conn_params = {
                "host": config.host,
                "port": config.port or 3306,
                "database": config.database,
                "user": config.username,
                "password": config.password,
                **self.connection_kwargs,
            }
            return pymysql.connect(**{k: v for k, v in conn_params.items() if v is not None})

        elif self.engine == "sqlite":
            try:
                import sqlite3
            except ImportError:
                raise ImportError("sqlite3 not available")

            db_path = config.database or ":memory:"
            return sqlite3.connect(db_path, **self.connection_kwargs)

        elif self.engine == "mssql":
            try:
                import pymssql
            except ImportError:
                raise ImportError("pymssql not installed. Install with: pip install pymssql")

            conn_params = {
                "server": config.host,
                "port": config.port or 1433,
                "database": config.database,
                "user": config.username,
                "password": config.password,
                **self.connection_kwargs,
            }
            return pymssql.connect(**{k: v for k, v in conn_params.items() if v is not None})

        else:
            raise ValueError(f"Unsupported SQL engine: {self.engine}")

    def _cleanup_connection(self, connection: Any):
        """Cleanup a database connection."""
        try:
            connection.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    def _health_check(self, connection: Any) -> bool:
        """Check if connection is healthy."""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False

    def connect(self) -> None:
        """Establish database connection or connection pool."""
        try:
            if self.use_pool:
                self._pool = ConnectionPool(
                    factory=self._create_connection,
                    max_size=self.config.pool_size,
                    timeout=self.config.pool_timeout,
                    health_check=self._health_check,
                    cleanup=self._cleanup_connection,
                )
                logger.info(f"Created connection pool for {self.engine}")
            else:
                self._connection = self._create_connection()
                logger.info(f"Connected to {self.engine} database")

            self._is_connected = True
            self._record_metric("connections")
        except Exception as e:
            logger.error(f"Failed to connect to {self.engine}: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        try:
            if self._pool:
                self._pool.close_all()
                self._pool = None
            elif self._connection:
                self._cleanup_connection(self._connection)
                self._connection = None

            self._is_connected = False
            logger.info(f"Disconnected from {self.engine}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.engine}: {e}")

    def read(
        self, query: str, params: Optional[Union[tuple, dict]] = None, fetch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_size: Maximum number of rows to fetch

        Returns:
            List of result dictionaries
        """
        if not self._is_connected:
            self.connect()

        def _execute_query():
            if self._pool:
                with self._pool.acquire() as conn:
                    return self._execute_on_connection(conn, query, params, fetch_size)
            elif self._connection:
                return self._execute_on_connection(self._connection, query, params, fetch_size)
            else:
                raise RuntimeError("Not connected to database")

        try:
            result = with_retry(_execute_query, self.config.retry_config)()
            self._record_metric("reads")
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self._record_metric("errors")
            raise

    def _execute_on_connection(
        self, conn: Any, query: str, params: Optional[Union[tuple, dict]], fetch_size: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Execute query on a specific connection."""
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_size:
                rows = cursor.fetchmany(fetch_size)
            else:
                rows = cursor.fetchall()

            # Get column names
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        finally:
            cursor.close()

    def write(
        self, data: Union[List[Dict[str, Any]], Dict[str, Any]], target: str, **kwargs
    ) -> None:
        """
        Insert data into table.

        Args:
            data: Data to insert (dict or list of dicts)
            target: Table name
            **kwargs: Additional parameters
        """
        if not self._is_connected:
            self.connect()

        if isinstance(data, dict):
            data = [data]

        if not data:
            return

        # Build INSERT query
        columns = list(data[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {target} ({', '.join(columns)}) VALUES ({placeholders})"

        def _execute_write():
            if self._pool:
                with self._pool.acquire() as conn:
                    self._execute_write_on_connection(conn, query, data, columns)
            elif self._connection:
                self._execute_write_on_connection(self._connection, query, data, columns)
            else:
                raise RuntimeError("Not connected to database")

        try:
            with_retry(_execute_write, self.config.retry_config)()
            self._record_metric("writes", len(data))
            logger.info(f"Inserted {len(data)} rows into {target}")
        except Exception as e:
            logger.error(f"Error writing data: {e}")
            self._record_metric("errors")
            raise

    def _execute_write_on_connection(
        self, conn: Any, query: str, data: List[Dict[str, Any]], columns: List[str]
    ):
        """Execute write on a specific connection."""
        cursor = conn.cursor()
        try:
            values = [[row[col] for col in columns] for row in data]
            cursor.executemany(query, values)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()


class MongoDBConnector(DataConnectorBase):
    """MongoDB connector with connection pooling."""

    def __init__(self, config: Optional[DatabaseConfig] = None, **mongo_kwargs):
        """
        Initialize MongoDB connector.

        Args:
            config: Database configuration
            **mongo_kwargs: Additional MongoDB client parameters
        """
        super().__init__(config or DatabaseConfig())
        self.mongo_kwargs = mongo_kwargs
        self._client = None
        self._db = None

    def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo not installed. Install with: pip install pymongo")

        config = self.config
        if not isinstance(config, DatabaseConfig):
            raise ValueError("Invalid config type")

        try:
            if config.connection_string:
                self._client = MongoClient(config.connection_string, **self.mongo_kwargs)
            else:
                uri = f"mongodb://"
                if config.username and config.password:
                    uri += f"{config.username}:{config.password}@"
                uri += f"{config.host}:{config.port or 27017}"
                self._client = MongoClient(uri, **self.mongo_kwargs)

            self._db = self._client[config.database] if config.database else None
            self._is_connected = True
            self._record_metric("connections")
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._record_metric("errors")
            raise

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._is_connected = False
            logger.info("Disconnected from MongoDB")

    def read(
        self, query: Dict[str, Any], collection: str, limit: Optional[int] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query MongoDB collection.

        Args:
            query: MongoDB query filter
            collection: Collection name
            limit: Maximum number of documents
            **kwargs: Additional find parameters

        Returns:
            List of documents
        """
        if not self._is_connected or not self._db:
            raise RuntimeError("Not connected to MongoDB")

        try:
            coll = self._db[collection]
            cursor = coll.find(query, **kwargs)

            if limit:
                cursor = cursor.limit(limit)

            results = list(cursor)
            self._record_metric("reads")
            return results
        except Exception as e:
            logger.error(f"Error querying MongoDB: {e}")
            self._record_metric("errors")
            raise

    def write(self, data: Union[Dict[str, Any], List[Dict[str, Any]]], target: str, **kwargs) -> None:
        """
        Insert documents into MongoDB collection.

        Args:
            data: Document or list of documents
            target: Collection name
            **kwargs: Additional insert parameters
        """
        if not self._is_connected or not self._db:
            raise RuntimeError("Not connected to MongoDB")

        try:
            coll = self._db[target]

            if isinstance(data, dict):
                result = coll.insert_one(data, **kwargs)
                count = 1
            else:
                result = coll.insert_many(data, **kwargs)
                count = len(result.inserted_ids)

            self._record_metric("writes", count)
            logger.info(f"Inserted {count} documents into {target}")
        except Exception as e:
            logger.error(f"Error writing to MongoDB: {e}")
            self._record_metric("errors")
            raise


class DatabaseConnector(DataConnectorBase):
    """Unified database connector supporting both SQL and NoSQL databases."""

    def __init__(
        self,
        db_type: str,
        config: Optional[DatabaseConfig] = None,
        **kwargs,
    ):
        """
        Initialize database connector.

        Args:
            db_type: Database type (postgresql, mysql, sqlite, mssql, mongodb, etc.)
            config: Database configuration
            **kwargs: Additional database-specific parameters
        """
        super().__init__(config or DatabaseConfig())
        self.db_type = db_type.lower()
        self.kwargs = kwargs

        # Create appropriate connector
        if self.db_type in ["postgresql", "postgres", "mysql", "sqlite", "mssql"]:
            self._connector = SQLConnector(
                engine=self.db_type if self.db_type != "postgres" else "postgresql",
                config=config,
                **kwargs,
            )
        elif self.db_type == "mongodb":
            self._connector = MongoDBConnector(config=config, **kwargs)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def connect(self) -> None:
        """Establish database connection."""
        self._connector.connect()
        self._is_connected = self._connector._is_connected

    def disconnect(self) -> None:
        """Close database connection."""
        self._connector.disconnect()
        self._is_connected = False

    def read(self, query: Any, **kwargs) -> Any:
        """Read data from database."""
        return self._connector.read(query, **kwargs)

    def write(self, data: Any, target: str, **kwargs) -> None:
        """Write data to database."""
        self._connector.write(data, target, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        return self._connector.get_metrics()

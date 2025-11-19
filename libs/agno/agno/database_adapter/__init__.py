"""
Database Adapter FSA

A production-ready database adapter with Finite State Automaton (FSA) for managing
database connection lifecycle across multiple database types.

Features:
- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, MongoDB
- **Connection Pooling**: Efficient connection management with configurable pool sizes
- **FSA State Management**: Robust connection lifecycle management
- **Query Builder**: Unified query interface across different databases
- **Transaction Management**: ACID transactions with savepoint support (SQL)
- **Schema Migrations**: Automatic schema versioning and migration
- **Error Handling**: Production-ready error handling with retry logic
- **Connection Retry**: Automatic reconnection with exponential backoff

## Quick Start

### PostgreSQL

```python
from agno.database_adapter import PostgresAdapter

# Create adapter with connection pooling
adapter = PostgresAdapter(
    connection_string="postgresql://user:pass@localhost/mydb",
    pool_size=10,
    max_overflow=20,
    retry_config=RetryConfig(max_retries=3)
)

# Execute queries
users = adapter.fetch_all("SELECT * FROM users WHERE active = :active", {"active": True})

# Use transactions
with adapter.transaction() as txn:
    adapter.execute("INSERT INTO users (name, email) VALUES (:name, :email)",
                   {"name": "John", "email": "john@example.com"})
    # Auto-commit on success, auto-rollback on exception

# Use query builder
query = adapter.query()
    .select("id", "name", "email")
    .from_table("users")
    .where("age", ">", 18)
    .order_by("name", "ASC")
    .limit(10)

results = adapter.execute(query.build())
```

### MySQL

```python
from agno.database_adapter import MySQLAdapter

adapter = MySQLAdapter(
    connection_string="mysql://user:pass@localhost/mydb",
    pool_size=5
)

# Same API as PostgreSQL
users = adapter.fetch_all("SELECT * FROM users")
```

### SQLite

```python
from agno.database_adapter import SQLiteAdapter

# File-based database
adapter = SQLiteAdapter(database_path="./myapp.db")

# In-memory database
adapter = SQLiteAdapter(database_path=":memory:")

# Same API as other SQL databases
adapter.create_table("users", {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "name": "TEXT NOT NULL",
    "email": "TEXT UNIQUE"
})
```

### MongoDB

```python
from agno.database_adapter import MongoDBAdapter

adapter = MongoDBAdapter(
    connection_string="mongodb://localhost:27017/",
    database_name="mydb",
    pool_size=10
)

# Use query builder for MongoDB
query = adapter.query()
    .select("name", "email")
    .from_table("users")
    .where("age", ">", 18)
    .limit(10)

# Execute MongoDB query
results = adapter.execute(query.build())

# Or use MongoDB operations directly
adapter.execute({
    "collection": "users",
    "operation": "find",
    "filter": {"age": {"$gt": 18}},
    "limit": 10
})
```

## Schema Migrations

```python
from agno.database_adapter import PostgresAdapter, Migration

class CreateUsersTable(Migration):
    def __init__(self):
        super().__init__(version=1, description="Create users table")

    def up(self, connection):
        connection.execute('''
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    def down(self, connection):
        connection.execute("DROP TABLE users")

# Apply migrations
adapter = PostgresAdapter("postgresql://user:pass@localhost/mydb")
migration_mgr = adapter.get_migration_manager()
migration_mgr.register(CreateUsersTable())
migration_mgr.migrate()  # Apply all pending migrations
```

## FSA States

The adapter manages connections through the following states:

- **DISCONNECTED**: No active connection
- **CONNECTING**: Establishing connection
- **CONNECTED**: Ready for operations
- **IN_TRANSACTION**: Active transaction in progress
- **RECONNECTING**: Attempting to reconnect after failure
- **ERROR**: Connection error state
- **CLOSED**: Adapter closed (terminal state)

## Error Handling

All database operations include automatic retry logic with exponential backoff:

```python
from agno.database_adapter import PostgresAdapter, RetryConfig

adapter = PostgresAdapter(
    connection_string="postgresql://user:pass@localhost/mydb",
    retry_config=RetryConfig(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True
    )
)

# Operations automatically retry on transient failures
adapter.connect()  # Will retry up to 5 times if connection fails
```

## Context Managers

```python
# Adapter as context manager
with PostgresAdapter("postgresql://user:pass@localhost/mydb") as adapter:
    users = adapter.fetch_all("SELECT * FROM users")
    # Auto-disconnect on exit

# Connection from pool
with adapter.get_connection() as conn:
    # Use connection
    pass
    # Auto-return to pool

# Transaction
with adapter.transaction() as txn:
    adapter.execute("INSERT INTO users ...")
    # Auto-commit on success, auto-rollback on exception
```
"""

from agno.database_adapter.base import DatabaseAdapter
from agno.database_adapter.adapters import (
    MongoDBAdapter,
    MySQLAdapter,
    PostgresAdapter,
    SQLiteAdapter,
)
from agno.database_adapter.exceptions import (
    ConfigurationError,
    ConnectionError,
    ConnectionPoolExhausted,
    DatabaseAdapterError,
    InvalidStateTransition,
    MigrationError,
    QueryError,
    RetryExhausted,
    TransactionError,
    UnsupportedOperation,
)
from agno.database_adapter.migration import Migration, MigrationManager
from agno.database_adapter.query_builder import JoinType, Query, QueryType
from agno.database_adapter.retry import RetryConfig, RetryContext, with_retry
from agno.database_adapter.states import ConnectionState, TransactionState
from agno.database_adapter.transaction import Transaction, transaction

__all__ = [
    # Base
    "DatabaseAdapter",
    # Adapters
    "PostgresAdapter",
    "MySQLAdapter",
    "SQLiteAdapter",
    "MongoDBAdapter",
    # Exceptions
    "DatabaseAdapterError",
    "ConnectionError",
    "ConnectionPoolExhausted",
    "TransactionError",
    "QueryError",
    "MigrationError",
    "InvalidStateTransition",
    "ConfigurationError",
    "RetryExhausted",
    "UnsupportedOperation",
    # States
    "ConnectionState",
    "TransactionState",
    # Query Builder
    "Query",
    "QueryType",
    "JoinType",
    # Transactions
    "Transaction",
    "transaction",
    # Migrations
    "Migration",
    "MigrationManager",
    # Retry
    "RetryConfig",
    "RetryContext",
    "with_retry",
]

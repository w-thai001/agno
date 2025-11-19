# Database Adapter FSA Examples

This directory contains examples demonstrating the Database Adapter FSA (Finite State Automaton) for unified database access across multiple database types.

## Features

- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, MongoDB
- **Connection Pooling**: Efficient connection management
- **FSA State Management**: Robust connection lifecycle
- **Query Builder**: Unified query interface
- **Transaction Management**: ACID transactions with savepoints
- **Schema Migrations**: Automatic versioning and migration
- **Error Handling**: Production-ready retry logic
- **Connection Retry**: Automatic reconnection with exponential backoff

## Examples

### 01_basic_usage.py

Demonstrates basic usage of the Database Adapter FSA:

- SQLite adapter with in-memory database
- Creating tables and inserting data
- Querying with parameterized queries
- Using the query builder
- Transaction management
- Connection pooling
- Retry logic configuration
- PostgreSQL example (requires server)
- MongoDB example (requires server)

Run the example:

```bash
python cookbook/database_adapter/01_basic_usage.py
```

### 02_migrations.py

Demonstrates schema migration support:

- Defining migrations with version numbers
- Registering migrations
- Applying migrations (up)
- Rolling back migrations (down)
- Migrating to specific versions
- Migration tracking and versioning

Run the example:

```bash
python cookbook/database_adapter/02_migrations.py
```

## Quick Start

### SQLite (No Server Required)

```python
from agno.database_adapter import SQLiteAdapter

# Create in-memory database
adapter = SQLiteAdapter(database_path=":memory:")

# Create table
adapter.create_table("users", {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "name": "TEXT NOT NULL",
    "email": "TEXT UNIQUE"
})

# Insert data
adapter.execute(
    "INSERT INTO users (name, email) VALUES (:name, :email)",
    {"name": "Alice", "email": "alice@example.com"}
)

# Query data
users = adapter.fetch_all("SELECT * FROM users")
print(users)

adapter.close()
```

### PostgreSQL

```python
from agno.database_adapter import PostgresAdapter

adapter = PostgresAdapter(
    connection_string="postgresql://user:pass@localhost/mydb",
    pool_size=10,
    max_overflow=20
)

# Use transactions
with adapter.transaction():
    adapter.execute("INSERT INTO users (name) VALUES (:name)", {"name": "Bob"})
    # Auto-commit on success, auto-rollback on exception

adapter.close()
```

### MongoDB

```python
from agno.database_adapter import MongoDBAdapter

adapter = MongoDBAdapter(
    connection_string="mongodb://localhost:27017/",
    database_name="mydb"
)

# Insert document
adapter.execute({
    "collection": "users",
    "operation": "insert_one",
    "document": {"name": "Alice", "age": 30}
})

# Query documents
users = adapter.execute({
    "collection": "users",
    "operation": "find",
    "filter": {"age": {"$gte": 25}}
})

adapter.close()
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

## Requirements

### Core Requirements (SQLite)

```bash
pip install sqlalchemy
```

### PostgreSQL

```bash
pip install sqlalchemy psycopg-binary
```

### MySQL

```bash
pip install sqlalchemy mysqlclient
```

### MongoDB

```bash
pip install pymongo
```

## Testing

Run the tests:

```bash
pytest tests/test_database_adapter.py -v
```

## Documentation

See the main documentation in `/home/user/agno/libs/agno/agno/database_adapter/__init__.py` for detailed API documentation.

"""
Tests for Database Adapter FSA

Tests cover:
- Connection lifecycle and FSA states
- Query execution
- Transaction management
- Connection pooling
- Error handling and retry logic
- Schema migrations
"""

import pytest

from agno.database_adapter import (
    ConnectionError,
    ConnectionState,
    PostgresAdapter,
    Query,
    RetryConfig,
    SQLiteAdapter,
    TransactionState,
)


class TestSQLiteAdapter:
    """Test SQLite adapter with in-memory database."""

    def test_connection_lifecycle(self):
        """Test FSA state transitions during connection lifecycle."""
        adapter = SQLiteAdapter(database_path=":memory:", auto_connect=False)

        # Initial state
        assert adapter.state == ConnectionState.DISCONNECTED
        assert not adapter.is_connected()

        # Connect
        adapter.connect()
        assert adapter.state == ConnectionState.CONNECTED
        assert adapter.is_connected()

        # Disconnect
        adapter.disconnect()
        assert adapter.state == ConnectionState.DISCONNECTED
        assert not adapter.is_connected()

    def test_auto_connect(self):
        """Test automatic connection on initialization."""
        adapter = SQLiteAdapter(database_path=":memory:", auto_connect=True)
        assert adapter.is_connected()
        assert adapter.state == ConnectionState.CONNECTED
        adapter.close()

    def test_create_and_query_table(self):
        """Test table creation and querying."""
        adapter = SQLiteAdapter(database_path=":memory:")

        # Create table
        adapter.create_table(
            "users",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "name": "TEXT NOT NULL",
                "email": "TEXT UNIQUE",
                "age": "INTEGER",
            },
        )

        # Verify table exists
        assert adapter.table_exists("users")
        assert "users" in adapter.get_table_names()

        # Insert data
        adapter.execute("INSERT INTO users (name, email, age) VALUES (:name, :email, :age)", {"name": "Alice", "email": "alice@example.com", "age": 30})

        adapter.execute("INSERT INTO users (name, email, age) VALUES (:name, :email, :age)", {"name": "Bob", "email": "bob@example.com", "age": 25})

        # Query data
        users = adapter.fetch_all("SELECT * FROM users ORDER BY name")
        assert len(users) == 2
        assert users[0]["name"] == "Alice"
        assert users[1]["name"] == "Bob"

        # Fetch one
        user = adapter.fetch_one("SELECT * FROM users WHERE name = :name", {"name": "Alice"})
        assert user is not None
        assert user["email"] == "alice@example.com"
        assert user["age"] == 30

        adapter.close()

    def test_query_builder(self):
        """Test unified query builder."""
        adapter = SQLiteAdapter(database_path=":memory:")

        # Create and populate table
        adapter.create_table(
            "products",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "name": "TEXT NOT NULL",
                "price": "REAL",
                "category": "TEXT",
            },
        )

        adapter.execute("INSERT INTO products (name, price, category) VALUES ('Laptop', 999.99, 'Electronics')")
        adapter.execute("INSERT INTO products (name, price, category) VALUES ('Phone', 599.99, 'Electronics')")
        adapter.execute("INSERT INTO products (name, price, category) VALUES ('Desk', 299.99, 'Furniture')")

        # Build query
        query = adapter.query().select("name", "price").from_table("products").where("category", "=", "Electronics").order_by("price", "DESC").limit(10)

        # Execute query
        sql = query.build()
        results = adapter.fetch_all(sql)

        assert len(results) == 2
        assert results[0]["name"] == "Laptop"
        assert results[1]["name"] == "Phone"

        adapter.close()

    def test_transactions(self):
        """Test transaction management."""
        adapter = SQLiteAdapter(database_path=":memory:")

        # Create table
        adapter.create_table("accounts", {"id": "INTEGER PRIMARY KEY", "balance": "REAL"})

        # Insert initial data
        adapter.execute("INSERT INTO accounts (id, balance) VALUES (1, 1000)")
        adapter.execute("INSERT INTO accounts (id, balance) VALUES (2, 500)")

        # Successful transaction
        with adapter.transaction() as txn:
            assert adapter.state == ConnectionState.IN_TRANSACTION
            adapter.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
            adapter.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")

        # Verify state returned to CONNECTED
        assert adapter.state == ConnectionState.CONNECTED

        # Verify changes
        account1 = adapter.fetch_one("SELECT balance FROM accounts WHERE id = 1")
        account2 = adapter.fetch_one("SELECT balance FROM accounts WHERE id = 2")
        assert account1["balance"] == 900
        assert account2["balance"] == 600

        # Failed transaction (should rollback)
        try:
            with adapter.transaction() as txn:
                adapter.execute("UPDATE accounts SET balance = balance - 200 WHERE id = 1")
                raise Exception("Simulated error")
        except Exception:
            pass

        # Verify rollback
        account1 = adapter.fetch_one("SELECT balance FROM accounts WHERE id = 1")
        assert account1["balance"] == 900  # Should not have changed

        adapter.close()

    def test_context_manager(self):
        """Test adapter as context manager."""
        with SQLiteAdapter(database_path=":memory:") as adapter:
            assert adapter.is_connected()
            adapter.create_table("test", {"id": "INTEGER PRIMARY KEY", "value": "TEXT"})
            assert adapter.table_exists("test")

        # Adapter should be disconnected after context
        assert adapter.state == ConnectionState.DISCONNECTED

    def test_connection_pool(self):
        """Test getting connections from pool."""
        adapter = SQLiteAdapter(database_path=":memory:")
        adapter.create_table("test", {"id": "INTEGER PRIMARY KEY", "value": "TEXT"})

        # Get connection from pool
        with adapter.get_connection() as conn:
            assert conn is not None
            # Connection should be usable
            result = conn.execute("SELECT 1")
            assert result is not None

        adapter.close()

    def test_insert_and_update(self):
        """Test insert and update operations."""
        adapter = SQLiteAdapter(database_path=":memory:")

        adapter.create_table("posts", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "title": "TEXT", "views": "INTEGER DEFAULT 0"})

        # Insert
        adapter.execute("INSERT INTO posts (title, views) VALUES (:title, :views)", {"title": "First Post", "views": 10})

        # Update
        adapter.execute("UPDATE posts SET views = views + 1 WHERE title = :title", {"title": "First Post"})

        # Verify
        post = adapter.fetch_one("SELECT * FROM posts WHERE title = :title", {"title": "First Post"})
        assert post["views"] == 11

        adapter.close()

    def test_delete_operation(self):
        """Test delete operations."""
        adapter = SQLiteAdapter(database_path=":memory:")

        adapter.create_table("items", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})

        # Insert
        adapter.execute("INSERT INTO items (id, name) VALUES (1, 'Item1')")
        adapter.execute("INSERT INTO items (id, name) VALUES (2, 'Item2')")

        # Delete
        adapter.execute("DELETE FROM items WHERE id = :id", {"id": 1})

        # Verify
        items = adapter.fetch_all("SELECT * FROM items")
        assert len(items) == 1
        assert items[0]["name"] == "Item2"

        adapter.close()


class TestQueryBuilder:
    """Test unified query builder."""

    def test_select_query(self):
        """Test SELECT query building."""
        query = Query("sqlite").select("id", "name", "email").from_table("users").where("age", ">", 18).order_by("name", "ASC").limit(10)

        sql = query.build()
        assert "SELECT id, name, email" in sql
        assert "FROM users" in sql
        assert "WHERE age > 18" in sql
        assert "ORDER BY name ASC" in sql
        assert "LIMIT 10" in sql

    def test_insert_query(self):
        """Test INSERT query building."""
        query = Query("sqlite").insert({"name": "John", "email": "john@example.com", "age": 30}).from_table("users")

        sql = query.build()
        assert "INSERT INTO users" in sql
        assert "name, email, age" in sql
        assert "VALUES" in sql

    def test_update_query(self):
        """Test UPDATE query building."""
        query = Query("sqlite").update({"name": "Jane", "age": 31}).from_table("users").where("id", "=", 1)

        sql = query.build()
        assert "UPDATE users" in sql
        assert "SET" in sql
        assert "name = 'Jane'" in sql
        assert "WHERE id = 1" in sql

    def test_delete_query(self):
        """Test DELETE query building."""
        query = Query("sqlite").delete().from_table("users").where("id", "=", 1)

        sql = query.build()
        assert "DELETE FROM users" in sql
        assert "WHERE id = 1" in sql

    def test_complex_select(self):
        """Test complex SELECT with multiple conditions."""
        query = (
            Query("sqlite")
            .select("id", "name", "email")
            .from_table("users")
            .where("age", ">", 18)
            .where("active", "=", True)
            .order_by("created_at", "DESC")
            .limit(20)
            .offset(10)
        )

        sql = query.build()
        assert "WHERE" in sql
        assert "age > 18" in sql
        assert "active = TRUE" in sql
        assert "LIMIT 20" in sql
        assert "OFFSET 10" in sql

    def test_mongodb_query(self):
        """Test MongoDB query building."""
        query = Query("mongodb").select("name", "email").from_table("users").where("age", ">", 18).limit(10)

        mongo_query = query.build()
        assert isinstance(mongo_query, dict)
        assert mongo_query["collection"] == "users"
        assert mongo_query["operation"] == "find"
        assert mongo_query["filter"] == {"age": {"$gt": 18}}
        assert mongo_query["limit"] == 10


class TestRetryLogic:
    """Test retry logic and error handling."""

    def test_retry_config(self):
        """Test retry configuration."""
        config = RetryConfig(max_retries=3, initial_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=False)

        # Test delay calculation
        delay0 = config.calculate_delay(0)
        delay1 = config.calculate_delay(1)
        delay2 = config.calculate_delay(2)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_retry_with_jitter(self):
        """Test retry delay with jitter."""
        config = RetryConfig(initial_delay=1.0, jitter=True)

        delays = [config.calculate_delay(0) for _ in range(10)]

        # With jitter, delays should vary
        assert len(set(delays)) > 1  # Should have some variation
        assert all(1.0 <= d <= 1.25 for d in delays)  # Within expected range


# Integration test (requires actual PostgreSQL - skip in CI)
@pytest.mark.skip(reason="Requires PostgreSQL server")
class TestPostgresAdapter:
    """Test PostgreSQL adapter (requires running PostgreSQL server)."""

    def test_postgres_connection(self):
        """Test PostgreSQL connection."""
        adapter = PostgresAdapter(
            connection_string="postgresql://postgres:postgres@localhost/test_db", pool_size=5, max_overflow=10
        )

        assert adapter.is_connected()
        assert adapter.db_type == "postgres"

        # Get table names
        tables = adapter.get_table_names()
        assert isinstance(tables, list)

        adapter.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

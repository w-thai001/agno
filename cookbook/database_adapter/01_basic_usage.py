"""
Database Adapter FSA - Basic Usage

This example demonstrates the basic usage of the Database Adapter FSA
with SQLite, PostgreSQL, MySQL, and MongoDB.
"""

from agno.database_adapter import (
    MongoDBAdapter,
    MySQLAdapter,
    PostgresAdapter,
    RetryConfig,
    SQLiteAdapter,
)
from agno.utils.log import logger


def sqlite_example():
    """Example using SQLite adapter."""
    logger.info("=== SQLite Adapter Example ===")

    # Create in-memory SQLite database
    with SQLiteAdapter(database_path=":memory:") as adapter:
        logger.info(f"Connected to SQLite, state: {adapter.state}")

        # Create table
        adapter.create_table(
            "users",
            {
                "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                "name": "TEXT NOT NULL",
                "email": "TEXT UNIQUE",
                "age": "INTEGER",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )
        logger.info("Created 'users' table")

        # Insert data using parameterized queries
        adapter.execute(
            "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
            {"name": "Alice Johnson", "email": "alice@example.com", "age": 30},
        )

        adapter.execute(
            "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
            {"name": "Bob Smith", "email": "bob@example.com", "age": 25},
        )

        adapter.execute(
            "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
            {"name": "Charlie Brown", "email": "charlie@example.com", "age": 35},
        )

        logger.info("Inserted 3 users")

        # Query data
        all_users = adapter.fetch_all("SELECT * FROM users ORDER BY name")
        logger.info(f"All users ({len(all_users)}):")
        for user in all_users:
            logger.info(f"  - {user['name']} ({user['email']}) - Age: {user['age']}")

        # Query with filter
        young_users = adapter.fetch_all("SELECT * FROM users WHERE age < :max_age ORDER BY age", {"max_age": 30})
        logger.info(f"\nUsers under 30 ({len(young_users)}):")
        for user in young_users:
            logger.info(f"  - {user['name']} - Age: {user['age']}")

        # Fetch single user
        user = adapter.fetch_one("SELECT * FROM users WHERE email = :email", {"email": "alice@example.com"})
        logger.info(f"\nFound user by email: {user['name']}")

        # Update data
        adapter.execute("UPDATE users SET age = :age WHERE email = :email", {"age": 31, "email": "alice@example.com"})
        logger.info("Updated Alice's age")

        # Verify update
        user = adapter.fetch_one("SELECT * FROM users WHERE email = :email", {"email": "alice@example.com"})
        logger.info(f"Alice's new age: {user['age']}")

        # Use query builder
        logger.info("\n=== Using Query Builder ===")
        query = (
            adapter.query()
            .select("name", "email", "age")
            .from_table("users")
            .where("age", ">=", 30)
            .order_by("age", "DESC")
            .limit(5)
        )

        sql = query.build()
        logger.info(f"Generated SQL: {sql}")

        results = adapter.fetch_all(sql)
        logger.info(f"Results ({len(results)}):")
        for row in results:
            logger.info(f"  - {row['name']} - Age: {row['age']}")


def transaction_example():
    """Example demonstrating transaction management."""
    logger.info("\n=== Transaction Example ===")

    with SQLiteAdapter(database_path=":memory:") as adapter:
        # Create accounts table
        adapter.create_table("accounts", {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "balance": "REAL"})

        # Insert initial data
        adapter.execute("INSERT INTO accounts (id, name, balance) VALUES (1, 'Alice', 1000.0)")
        adapter.execute("INSERT INTO accounts (id, name, balance) VALUES (2, 'Bob', 500.0)")

        logger.info("Initial balances:")
        for account in adapter.fetch_all("SELECT * FROM accounts ORDER BY id"):
            logger.info(f"  {account['name']}: ${account['balance']}")

        # Successful transaction - transfer money
        logger.info("\n--- Transfer $200 from Alice to Bob ---")
        try:
            with adapter.transaction() as txn:
                logger.info(f"Transaction state: {txn.state}")

                # Debit Alice
                adapter.execute("UPDATE accounts SET balance = balance - :amount WHERE id = :id", {"amount": 200, "id": 1})

                # Credit Bob
                adapter.execute("UPDATE accounts SET balance = balance + :amount WHERE id = :id", {"amount": 200, "id": 2})

                logger.info("Transaction will commit...")

            logger.info("Transaction committed successfully")

        except Exception as e:
            logger.error(f"Transaction failed: {e}")

        logger.info("\nBalances after successful transaction:")
        for account in adapter.fetch_all("SELECT * FROM accounts ORDER BY id"):
            logger.info(f"  {account['name']}: ${account['balance']}")

        # Failed transaction - should rollback
        logger.info("\n--- Attempting invalid transaction (will fail) ---")
        try:
            with adapter.transaction() as txn:
                # Debit Alice
                adapter.execute("UPDATE accounts SET balance = balance - :amount WHERE id = :id", {"amount": 300, "id": 1})

                # Simulate error before crediting Bob
                raise Exception("Simulated error - insufficient funds check failed")

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            logger.info("Transaction automatically rolled back")

        logger.info("\nBalances after failed transaction (should be unchanged):")
        for account in adapter.fetch_all("SELECT * FROM accounts ORDER BY id"):
            logger.info(f"  {account['name']}: ${account['balance']}")


def connection_pool_example():
    """Example demonstrating connection pooling."""
    logger.info("\n=== Connection Pool Example ===")

    adapter = SQLiteAdapter(database_path=":memory:")

    # Create table
    adapter.create_table("logs", {"id": "INTEGER PRIMARY KEY AUTOINCREMENT", "message": "TEXT", "level": "TEXT"})

    # Use connection from pool
    logger.info("Getting connection from pool...")
    with adapter.get_connection() as conn:
        logger.info("Got connection, executing queries...")

        # Direct connection usage
        result = conn.execute("INSERT INTO logs (message, level) VALUES ('Test log 1', 'INFO')")
        result = conn.execute("INSERT INTO logs (message, level) VALUES ('Test log 2', 'DEBUG')")
        result = conn.execute("INSERT INTO logs (message, level) VALUES ('Test log 3', 'ERROR')")

    logger.info("Connection returned to pool")

    # Verify data
    logs = adapter.fetch_all("SELECT * FROM logs")
    logger.info(f"\nLogs in database ({len(logs)}):")
    for log in logs:
        logger.info(f"  [{log['level']}] {log['message']}")

    adapter.close()


def retry_logic_example():
    """Example demonstrating retry logic."""
    logger.info("\n=== Retry Logic Example ===")

    # Create adapter with custom retry config
    retry_config = RetryConfig(max_retries=3, initial_delay=0.5, max_delay=5.0, exponential_base=2.0, jitter=True)

    adapter = SQLiteAdapter(database_path=":memory:", retry_config=retry_config)

    logger.info(f"Adapter created with retry config: max_retries={retry_config.max_retries}")
    logger.info(f"Connection established (with automatic retry on failure)")

    # Connection state
    logger.info(f"Connection state: {adapter.state}")
    logger.info(f"Is connected: {adapter.is_connected()}")

    adapter.close()


def postgres_example():
    """
    Example using PostgreSQL adapter.

    Note: Requires PostgreSQL server running.
    Update connection string with your credentials.
    """
    logger.info("\n=== PostgreSQL Adapter Example ===")

    try:
        # Create PostgreSQL adapter
        adapter = PostgresAdapter(
            connection_string="postgresql://postgres:postgres@localhost/test_db",
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )

        logger.info(f"Connected to PostgreSQL, state: {adapter.state}")

        # Check if table exists
        if adapter.table_exists("demo_users", schema="public"):
            logger.info("Table 'demo_users' already exists, dropping it...")
            adapter.drop_table("demo_users", schema="public")

        # Create table
        adapter.create_table(
            "demo_users",
            {
                "id": "SERIAL PRIMARY KEY",
                "name": "VARCHAR(100) NOT NULL",
                "email": "VARCHAR(255) UNIQUE",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            schema="public",
        )
        logger.info("Created 'demo_users' table")

        # Insert and query
        adapter.execute("INSERT INTO demo_users (name, email) VALUES (:name, :email)", {"name": "John Doe", "email": "john@example.com"})

        users = adapter.fetch_all("SELECT * FROM demo_users")
        logger.info(f"Users: {users}")

        # Cleanup
        adapter.drop_table("demo_users", schema="public")
        adapter.close()

        logger.info("PostgreSQL example completed")

    except Exception as e:
        logger.error(f"PostgreSQL example failed: {e}")
        logger.info("Make sure PostgreSQL is running and credentials are correct")


def mongodb_example():
    """
    Example using MongoDB adapter.

    Note: Requires MongoDB server running.
    Update connection string with your credentials.
    """
    logger.info("\n=== MongoDB Adapter Example ===")

    try:
        # Create MongoDB adapter
        adapter = MongoDBAdapter(
            connection_string="mongodb://localhost:27017/", database_name="test_db", pool_size=10
        )

        logger.info(f"Connected to MongoDB, state: {adapter.state}")

        # Drop collection if exists
        if adapter.collection_exists("demo_users"):
            adapter.drop_collection("demo_users")

        # Insert documents
        adapter.execute(
            {"collection": "demo_users", "operation": "insert_one", "document": {"name": "Alice", "email": "alice@example.com", "age": 30}}
        )

        adapter.execute(
            {"collection": "demo_users", "operation": "insert_one", "document": {"name": "Bob", "email": "bob@example.com", "age": 25}}
        )

        logger.info("Inserted documents")

        # Query documents
        users = adapter.execute({"collection": "demo_users", "operation": "find", "filter": {"age": {"$gte": 25}}})

        logger.info(f"Found {len(users)} users:")
        for user in users:
            logger.info(f"  - {user['name']} ({user['email']}) - Age: {user['age']}")

        # Use query builder
        query = adapter.query().select("name", "email").from_table("demo_users").where("age", ">", 25).limit(10)

        mongo_query = query.build()
        logger.info(f"\nMongoDB query: {mongo_query}")

        results = adapter.execute(mongo_query)
        logger.info(f"Query results: {results}")

        # Cleanup
        adapter.drop_collection("demo_users")
        adapter.close()

        logger.info("MongoDB example completed")

    except Exception as e:
        logger.error(f"MongoDB example failed: {e}")
        logger.info("Make sure MongoDB is running")


if __name__ == "__main__":
    # Run SQLite examples (no server required)
    sqlite_example()
    transaction_example()
    connection_pool_example()
    retry_logic_example()

    # Run PostgreSQL example (requires server)
    # Uncomment to run:
    # postgres_example()

    # Run MongoDB example (requires server)
    # Uncomment to run:
    # mongodb_example()

    logger.info("\n=== All examples completed ===")

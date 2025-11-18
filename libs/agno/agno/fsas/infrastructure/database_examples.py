"""
Example usage of Database Connector FSA

This module demonstrates various use cases for the DatabaseConnectorFSA
including connection pooling, transactions, query building, migrations,
read/write splitting, and more.
"""

import asyncio
import os
from agno.fsas.infrastructure.database_connector_fsa import (
    DatabaseConnectorFSA,
    DatabaseConfig,
    DatabaseType,
    Migration,
    QueryBuilder,
)


async def example_basic_connection():
    """Example 1: Basic database connection and query"""
    print("\n=== Example 1: Basic Database Connection ===")

    # Configure database
    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "myapp"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
        min_connections=2,
        max_connections=10
    )

    # Create connector
    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        # Initialize
        await connector.initialize()
        print("✓ Database connector initialized")

        # Execute simple query
        result = await connector.execute(
            "SELECT * FROM users WHERE age > :min_age",
            params={"min_age": 18},
            read_only=True
        )

        print(f"✓ Query executed: {result.row_count} rows in {result.execution_time:.3f}s")

    finally:
        await connector.close()


async def example_query_builder():
    """Example 2: Using the query builder"""
    print("\n=== Example 2: Query Builder ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        # Build SELECT query
        qb = connector.query_builder("users")
        query, params = (
            qb.select("id", "name", "email")
            .where("age", ">", 18)
            .where("status", "=", "active")
            .order_by("created_at", "DESC")
            .limit(10)
            .build()
        )

        print(f"Query: {query}")
        print(f"Params: {params}")

        # Execute query
        result = await connector.execute(query, params, read_only=True)
        print(f"✓ Retrieved {result.row_count} users")

        # Build INSERT query
        insert_query, insert_params = QueryBuilder.insert(
            "users",
            {"name": "John Doe", "email": "john@example.com", "age": 25}
        )

        print(f"\nInsert query: {insert_query}")
        print(f"Insert params: {insert_params}")

        # Build UPDATE query
        update_query, update_params = QueryBuilder.update(
            "users",
            {"status": "inactive"},
            {"id": 1}
        )

        print(f"\nUpdate query: {update_query}")

    finally:
        await connector.close()


async def example_transactions():
    """Example 3: Transaction management"""
    print("\n=== Example 3: Transaction Management ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        # Use transaction context manager
        async with connector.transaction() as txn:
            print("✓ Transaction started")

            # Execute queries within transaction
            await txn.connection.execute(
                "INSERT INTO users (name, email) VALUES ($1, $2)",
                "Jane Doe", "jane@example.com"
            )

            await txn.connection.execute(
                "UPDATE accounts SET balance = balance - 100 WHERE user_id = $1",
                1
            )

            # Create savepoint
            await txn.savepoint("sp1")
            print("✓ Savepoint created")

            # More operations...
            await txn.connection.execute(
                "INSERT INTO audit_log (action) VALUES ($1)",
                "transfer"
            )

            # Transaction will auto-commit on successful exit

        print("✓ Transaction committed")

        # Example with rollback
        try:
            async with connector.transaction() as txn:
                await txn.connection.execute(
                    "INSERT INTO users (name) VALUES ($1)",
                    "Test User"
                )

                # Simulate error
                raise Exception("Simulated error")

        except Exception as e:
            print(f"✓ Transaction rolled back due to: {e}")

    finally:
        await connector.close()


async def example_connection_pooling():
    """Example 4: Connection pooling"""
    print("\n=== Example 4: Connection Pooling ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp",
        min_connections=5,
        max_connections=20,
        connection_timeout=30.0,
        idle_timeout=600.0
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()
        print(f"✓ Pool initialized with {config.min_connections} connections")

        # Execute multiple queries concurrently
        async def run_query(query_id):
            result = await connector.execute(
                f"SELECT {query_id} as id",
                read_only=True
            )
            return result

        # Run 10 concurrent queries
        tasks = [run_query(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        print(f"✓ Executed {len(results)} concurrent queries")

        # Check pool status
        info = connector.error_handling()
        print(f"✓ Active connections: {info['active_connections']}")

    finally:
        await connector.close()


async def example_read_write_splitting():
    """Example 5: Read/write splitting"""
    print("\n=== Example 5: Read/Write Splitting ===")

    # Primary database for writes
    primary_config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="primary.db.example.com",
        port=5432,
        database="myapp"
    )

    # Replica databases for reads
    replica_configs = [
        DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="replica1.db.example.com",
            port=5432,
            database="myapp"
        ),
        DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="replica2.db.example.com",
            port=5432,
            database="myapp"
        )
    ]

    connector = DatabaseConnectorFSA(
        primary_config=primary_config,
        replica_configs=replica_configs
    )

    try:
        await connector.initialize()
        print("✓ Initialized with 1 primary and 2 replicas")

        # Read query - routed to replica
        result = await connector.execute(
            "SELECT * FROM users",
            read_only=True
        )
        print(f"✓ Read query executed on replica: {result.row_count} rows")

        # Write query - routed to primary
        result = await connector.execute(
            "INSERT INTO users (name) VALUES (:name)",
            params={"name": "New User"},
            read_only=False
        )
        print("✓ Write query executed on primary")

    finally:
        await connector.close()


async def example_migrations():
    """Example 6: Database migrations"""
    print("\n=== Example 6: Database Migrations ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        # Define migrations
        migration1 = Migration(
            version=1,
            name="create_users_table",
            up_sql="""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            down_sql="DROP TABLE users"
        )

        migration2 = Migration(
            version=2,
            name="add_users_status",
            up_sql="ALTER TABLE users ADD COLUMN status VARCHAR(50) DEFAULT 'active'",
            down_sql="ALTER TABLE users DROP COLUMN status"
        )

        # Add migrations
        connector.migration_manager.add_migration(migration1)
        connector.migration_manager.add_migration(migration2)
        print("✓ Added 2 migrations")

        # Apply migrations
        await connector.migration_manager.migrate_up()
        print("✓ Migrations applied")

        # Rollback to version 1
        # await connector.migration_manager.migrate_down(target_version=1)
        # print("✓ Rolled back to version 1")

    finally:
        await connector.close()


async def example_circuit_breaker():
    """Example 7: Circuit breaker and failover"""
    print("\n=== Example 7: Circuit Breaker ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="unreliable.db.example.com",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        # Simulate failures
        for i in range(7):
            try:
                result = await connector.execute("SELECT 1", read_only=True)
                print(f"Query {i+1}: Success")
            except Exception as e:
                print(f"Query {i+1}: {type(e).__name__}")

        # Check circuit breaker state
        info = connector.error_handling()
        print(f"\nCircuit breaker state: {info['circuit_breaker_state']}")
        print(f"Failure count: {info['failure_count']}")

    finally:
        await connector.close()


async def example_query_caching():
    """Example 8: Query result caching"""
    print("\n=== Example 8: Query Caching ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        query = "SELECT * FROM users WHERE status = :status"
        params = {"status": "active"}

        # First query - not cached
        result1 = await connector.execute(query, params, read_only=True, use_cache=True)
        print(f"First query: cached={result1.cached}, time={result1.execution_time:.3f}s")

        # Second query - should be cached
        result2 = await connector.execute(query, params, read_only=True, use_cache=True)
        print(f"Second query: cached={result2.cached}, time={result2.execution_time:.3f}s")

        # Invalidate cache
        connector.query_cache.invalidate()
        print("✓ Cache invalidated")

        # Third query - not cached again
        result3 = await connector.execute(query, params, read_only=True, use_cache=True)
        print(f"Third query: cached={result3.cached}, time={result3.execution_time:.3f}s")

    finally:
        await connector.close()


async def example_metrics_monitoring():
    """Example 9: Metrics and monitoring"""
    print("\n=== Example 9: Metrics and Monitoring ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()

        # Execute several queries
        for i in range(5):
            await connector.execute(f"SELECT {i}", read_only=True)

        # Get metrics
        metrics = connector.metrics_collector.get_metrics()

        print(f"Total queries: {metrics.total_queries}")
        print(f"Successful: {metrics.successful_queries}")
        print(f"Failed: {metrics.failed_queries}")
        print(f"Cached: {metrics.cached_queries}")
        print(f"Average time: {connector.metrics_collector.get_average_query_time():.3f}s")
        print(f"Transactions committed: {metrics.transactions_committed}")
        print(f"Transactions rolled back: {metrics.transactions_rolled_back}")

        # Get slow queries
        slow_queries = connector.metrics_collector.slow_queries
        if slow_queries:
            print(f"\nSlow queries detected: {len(slow_queries)}")
            for query, duration in slow_queries[:5]:
                print(f"  {duration:.2f}s: {query[:50]}...")

    finally:
        await connector.close()


async def example_redis_connection():
    """Example 10: Redis database operations"""
    print("\n=== Example 10: Redis Operations ===")

    config = DatabaseConfig(
        db_type=DatabaseType.REDIS,
        host="localhost",
        port=6379,
        database="0",
        password=""
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    try:
        await connector.initialize()
        print("✓ Connected to Redis")

        # Redis operations would use execute with Redis commands
        # Example: SET key value
        # result = await connector.execute("SET mykey myvalue")

        print("✓ Redis operations ready")

    finally:
        await connector.close()


def example_validation():
    """Example 11: Configuration validation"""
    print("\n=== Example 11: Configuration Validation ===")

    config = DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="myapp"
    )

    connector = DatabaseConnectorFSA(primary_config=config)

    # Validate configuration
    is_valid = connector.validate()
    print(f"Configuration valid: {is_valid}")

    # Get error handling info
    info = connector.error_handling()
    print(f"Circuit breaker state: {info['circuit_breaker_state']}")
    print(f"Active connections: {info['active_connections']}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Database Connector FSA Examples")
    print("=" * 60)

    # Note: Most examples require actual database servers
    # Uncomment to run specific examples

    # await example_basic_connection()
    await example_query_builder()
    # await example_transactions()
    # await example_connection_pooling()
    # await example_read_write_splitting()
    # await example_migrations()
    # await example_circuit_breaker()
    # await example_query_caching()
    # await example_metrics_monitoring()
    # await example_redis_connection()
    example_validation()

    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

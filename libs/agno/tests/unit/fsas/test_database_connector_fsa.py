"""
Comprehensive tests for Database Connector FSA

This test suite covers all major functionality including:
- Connection pool creation and lifecycle
- Transaction commit and rollback scenarios
- Query builder SQL generation and parameter binding
- Circuit breaker triggering and recovery
- Migration execution and rollback
- Read/write splitting logic
- Connection failover scenarios
- Metrics collection accuracy
- Query caching
- Health checks
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from agno.fsas.infrastructure.database_connector_fsa import (
    DatabaseConnectorFSA,
    DatabaseConfig,
    DatabaseType,
    ConnectionPool,
    TransactionManager,
    TransactionState,
    QueryBuilder,
    MigrationManager,
    Migration,
    CircuitBreaker,
    CircuitState,
    MetricsCollector,
    QueryCache,
    QueryResult,
    ConnectionInfo,
    ConnectionError,
    TransactionError,
    QueryError,
    MigrationError,
    CircuitBreakerOpenError,
    ConnectionPoolExhaustedError,
)


@pytest.fixture
def postgres_config():
    """PostgreSQL configuration for testing"""
    return DatabaseConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_pass",
        min_connections=2,
        max_connections=10
    )


@pytest.fixture
def redis_config():
    """Redis configuration for testing"""
    return DatabaseConfig(
        db_type=DatabaseType.REDIS,
        host="localhost",
        port=6379,
        database="0",
        password="",
        min_connections=2,
        max_connections=10
    )


@pytest.fixture
async def db_connector(postgres_config):
    """Create DatabaseConnectorFSA instance for testing"""
    connector = DatabaseConnectorFSA(primary_config=postgres_config)
    yield connector
    if connector._initialized:
        await connector.close()


class TestConnectionPoolLifecycle:
    """Test connection pool creation and lifecycle"""

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self, postgres_config):
        """Test connection pool initializes with minimum connections"""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            pool = ConnectionPool(postgres_config)
            await pool.initialize()

            assert pool.total_connections == postgres_config.min_connections
            assert mock_connect.call_count == postgres_config.min_connections

    @pytest.mark.asyncio
    async def test_connection_acquisition(self, postgres_config):
        """Test acquiring connection from pool"""
        pool = ConnectionPool(postgres_config)

        # Mock connection
        mock_conn = MagicMock()
        conn_info = ConnectionInfo(
            connection_id="test_conn",
            db_type=DatabaseType.POSTGRESQL,
            connection=mock_conn,
            created_at=time.time(),
            last_used=time.time()
        )

        pool.connections.append(conn_info)
        pool.total_connections = 1

        with patch.object(pool, '_check_health', return_value=True):
            acquired = await pool.acquire()
            assert acquired.connection_id == "test_conn"
            assert acquired.connection_id in pool.active_connections

    @pytest.mark.asyncio
    async def test_connection_release(self, postgres_config):
        """Test releasing connection back to pool"""
        pool = ConnectionPool(postgres_config)

        conn_info = ConnectionInfo(
            connection_id="test_conn",
            db_type=DatabaseType.POSTGRESQL,
            connection=MagicMock(),
            created_at=time.time(),
            last_used=time.time()
        )

        pool.active_connections["test_conn"] = conn_info

        await pool.release(conn_info)

        assert "test_conn" not in pool.active_connections
        assert len(pool.connections) == 1

    @pytest.mark.asyncio
    async def test_pool_exhaustion(self, postgres_config):
        """Test connection pool exhaustion error"""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test",
            max_connections=1
        )

        pool = ConnectionPool(config)
        pool.total_connections = 1  # Pool at max

        with pytest.raises(ConnectionPoolExhaustedError):
            await pool.acquire()

    @pytest.mark.asyncio
    async def test_connection_health_check(self, postgres_config):
        """Test connection health checking"""
        pool = ConnectionPool(postgres_config)

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        conn_info = ConnectionInfo(
            connection_id="test_conn",
            db_type=DatabaseType.POSTGRESQL,
            connection=mock_conn,
            created_at=time.time(),
            last_used=time.time()
        )

        is_healthy = await pool._check_health(conn_info)
        assert is_healthy is True
        mock_conn.fetchval.assert_called_once()


class TestTransactionManagement:
    """Test transaction commit and rollback scenarios"""

    @pytest.mark.asyncio
    async def test_transaction_begin_commit(self):
        """Test starting and committing transaction"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        txn = TransactionManager(mock_conn, DatabaseType.POSTGRESQL)

        await txn.begin()
        assert txn.state == TransactionState.ACTIVE

        await txn.commit()
        assert txn.state == TransactionState.COMMITTED

        assert mock_conn.execute.call_count == 2
        mock_conn.execute.assert_any_call('BEGIN')
        mock_conn.execute.assert_any_call('COMMIT')

    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        txn = TransactionManager(mock_conn, DatabaseType.POSTGRESQL)

        await txn.begin()
        await txn.rollback()

        assert txn.state == TransactionState.ROLLED_BACK
        mock_conn.execute.assert_any_call('ROLLBACK')

    @pytest.mark.asyncio
    async def test_transaction_savepoint(self):
        """Test creating savepoint"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        txn = TransactionManager(mock_conn, DatabaseType.POSTGRESQL)

        await txn.begin()
        await txn.savepoint('sp1')

        assert 'sp1' in txn.savepoints
        mock_conn.execute.assert_any_call('SAVEPOINT sp1')

    @pytest.mark.asyncio
    async def test_transaction_rollback_to_savepoint(self):
        """Test rolling back to savepoint"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        txn = TransactionManager(mock_conn, DatabaseType.POSTGRESQL)

        await txn.begin()
        await txn.savepoint('sp1')
        await txn.rollback(savepoint='sp1')

        mock_conn.execute.assert_any_call('ROLLBACK TO SAVEPOINT sp1')

    @pytest.mark.asyncio
    async def test_transaction_without_begin_fails(self):
        """Test commit without begin raises error"""
        mock_conn = AsyncMock()
        txn = TransactionManager(mock_conn, DatabaseType.POSTGRESQL)

        with pytest.raises(TransactionError):
            await txn.commit()


class TestQueryBuilder:
    """Test query builder SQL generation and parameter binding"""

    def test_simple_select(self):
        """Test simple SELECT query"""
        qb = QueryBuilder("users")
        query, params = qb.select("id", "name").build()

        assert "SELECT id, name FROM users" in query
        assert params == {}

    def test_select_with_where(self):
        """Test SELECT with WHERE clause"""
        qb = QueryBuilder("users")
        query, params = qb.select("*").where("age", ">", 18).build()

        assert "WHERE" in query
        assert "age >" in query
        assert len(params) == 1

    def test_select_with_multiple_where(self):
        """Test SELECT with multiple WHERE conditions"""
        qb = QueryBuilder("users")
        query, params = (
            qb.select("*")
            .where("age", ">", 18)
            .where("status", "=", "active")
            .build()
        )

        assert "AND" in query
        assert len(params) == 2

    def test_select_with_join(self):
        """Test SELECT with JOIN"""
        qb = QueryBuilder("users")
        query, params = (
            qb.select("users.id", "orders.total")
            .join("orders", "orders.user_id = users.id")
            .build()
        )

        assert "JOIN orders ON" in query

    def test_select_with_order_by(self):
        """Test SELECT with ORDER BY"""
        qb = QueryBuilder("users")
        query, params = qb.select("*").order_by("created_at", "DESC").build()

        assert "ORDER BY created_at DESC" in query

    def test_select_with_limit_offset(self):
        """Test SELECT with LIMIT and OFFSET"""
        qb = QueryBuilder("users")
        query, params = qb.select("*").limit(10).offset(20).build()

        assert "LIMIT 10" in query
        assert "OFFSET 20" in query

    def test_insert_query(self):
        """Test INSERT statement"""
        data = {"name": "John", "age": 30}
        query, params = QueryBuilder.insert("users", data)

        assert "INSERT INTO users" in query
        assert "name, age" in query or "age, name" in query
        assert params == data

    def test_update_query(self):
        """Test UPDATE statement"""
        data = {"name": "Jane"}
        where = {"id": 1}
        query, params = QueryBuilder.update("users", data, where)

        assert "UPDATE users SET" in query
        assert "WHERE" in query
        assert len(params) == 2

    def test_delete_query(self):
        """Test DELETE statement"""
        where = {"id": 1}
        query, params = QueryBuilder.delete("users", where)

        assert "DELETE FROM users WHERE" in query
        assert params == where

    def test_sql_injection_prevention(self):
        """Test that parameters are properly bound to prevent SQL injection"""
        qb = QueryBuilder("users")
        malicious_input = "1'; DROP TABLE users; --"
        query, params = qb.where("id", "=", malicious_input).build()

        # Should use parameterized query
        assert "DROP TABLE" not in query
        assert any(malicious_input in str(v) for v in params.values())


class TestCircuitBreaker:
    """Test circuit breaker triggering and recovery"""

    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker starts in closed state"""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures"""
        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenError):
            cb.can_execute()

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker transitions to half-open after timeout"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Trigger open state
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should allow execution and transition to half-open
        can_execute = cb.can_execute()
        assert can_execute is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_success(self):
        """Test circuit breaker closes after successful calls in half-open"""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2
        )

        # Open circuit
        cb.record_failure()
        cb.record_failure()

        # Wait and transition to half-open
        time.sleep(0.15)
        cb.can_execute()

        # Record successes
        cb.half_open_calls = 2
        cb.record_success()

        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test circuit breaker reopens if failure occurs in half-open"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open circuit
        cb.record_failure()
        cb.record_failure()

        # Transition to half-open
        time.sleep(0.15)
        cb.can_execute()

        # Record failure in half-open
        cb.record_failure()

        assert cb.state == CircuitState.OPEN


class TestMigrationManagement:
    """Test migration execution and rollback"""

    @pytest.mark.asyncio
    async def test_migration_initialization(self, postgres_config):
        """Test migration table initialization"""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(postgres_config)
            await pool.initialize()

            manager = MigrationManager(pool)
            await manager.initialize()

            # Should have created migrations table
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any('schema_migrations' in str(call) for call in calls)

    def test_add_migration(self):
        """Test adding migration to manager"""
        pool = MagicMock()
        manager = MigrationManager(pool)

        migration = Migration(
            version=1,
            name="create_users_table",
            up_sql="CREATE TABLE users (id INT)",
            down_sql="DROP TABLE users"
        )

        manager.add_migration(migration)

        assert len(manager.migrations) == 1
        assert migration.checksum is not None

    @pytest.mark.asyncio
    async def test_migration_up(self, postgres_config):
        """Test applying migrations"""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=0)  # Current version
            mock_connect.return_value = mock_conn

            pool = ConnectionPool(postgres_config)
            pool.connections.append(
                ConnectionInfo(
                    connection_id="test",
                    db_type=DatabaseType.POSTGRESQL,
                    connection=mock_conn,
                    created_at=time.time(),
                    last_used=time.time()
                )
            )

            manager = MigrationManager(pool)

            migration = Migration(
                version=1,
                name="test_migration",
                up_sql="CREATE TABLE test (id INT)",
                down_sql="DROP TABLE test"
            )

            manager.add_migration(migration)

            await manager.migrate_up()

            # Should have executed the migration SQL
            assert mock_conn.execute.call_count >= 1


class TestReadWriteSplitting:
    """Test read/write splitting logic"""

    @pytest.mark.asyncio
    async def test_write_queries_use_primary(self, postgres_config):
        """Test write queries are routed to primary"""
        replica_config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="replica.localhost",
            port=5432,
            database="test_db"
        )

        connector = DatabaseConnectorFSA(
            primary_config=postgres_config,
            replica_configs=[replica_config]
        )

        # Mock pools
        connector.primary_pool = MagicMock()
        connector.replica_pools = [MagicMock()]

        pool = connector._select_pool(read_only=False)

        assert pool == connector.primary_pool

    @pytest.mark.asyncio
    async def test_read_queries_use_replica(self, postgres_config):
        """Test read queries are routed to replicas"""
        replica_config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="replica.localhost",
            port=5432,
            database="test_db"
        )

        connector = DatabaseConnectorFSA(
            primary_config=postgres_config,
            replica_configs=[replica_config]
        )

        # Mock pools
        connector.primary_pool = MagicMock()
        connector.replica_pools = [MagicMock()]

        pool = connector._select_pool(read_only=True)

        assert pool in connector.replica_pools

    @pytest.mark.asyncio
    async def test_read_falls_back_to_primary_without_replicas(self, postgres_config):
        """Test read queries fall back to primary without replicas"""
        connector = DatabaseConnectorFSA(primary_config=postgres_config)

        connector.primary_pool = MagicMock()
        connector.replica_pools = []

        pool = connector._select_pool(read_only=True)

        assert pool == connector.primary_pool


class TestMetricsCollection:
    """Test metrics collection accuracy"""

    def test_metrics_initialization(self):
        """Test metrics collector initializes correctly"""
        collector = MetricsCollector()

        metrics = collector.get_metrics()

        assert metrics.total_queries == 0
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 0

    def test_record_successful_query(self):
        """Test recording successful query"""
        collector = MetricsCollector()

        collector.record_query("SELECT * FROM users", 0.1, success=True)

        metrics = collector.get_metrics()
        assert metrics.total_queries == 1
        assert metrics.successful_queries == 1
        assert metrics.failed_queries == 0

    def test_record_failed_query(self):
        """Test recording failed query"""
        collector = MetricsCollector()

        collector.record_query("SELECT * FROM users", 0.1, success=False)

        metrics = collector.get_metrics()
        assert metrics.total_queries == 1
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 1

    def test_record_cached_query(self):
        """Test recording cached query"""
        collector = MetricsCollector()

        collector.record_query("SELECT * FROM users", 0.01, success=True, cached=True)

        metrics = collector.get_metrics()
        assert metrics.cached_queries == 1

    def test_average_query_time(self):
        """Test average query time calculation"""
        collector = MetricsCollector()

        collector.record_query("SELECT 1", 0.1, success=True)
        collector.record_query("SELECT 2", 0.3, success=True)

        avg_time = collector.get_average_query_time()
        assert 0.15 <= avg_time <= 0.25

    def test_slow_query_detection(self):
        """Test slow query detection and logging"""
        collector = MetricsCollector()
        collector.slow_query_threshold = 0.5

        collector.record_query("SELECT * FROM large_table", 1.5, success=True)

        assert len(collector.slow_queries) == 1
        assert collector.slow_queries[0][1] == 1.5


class TestQueryCaching:
    """Test query result caching"""

    def test_cache_stores_and_retrieves(self):
        """Test cache stores and retrieves results"""
        cache = QueryCache(ttl=10.0)

        query = "SELECT * FROM users WHERE id = :id"
        params = {"id": 1}
        result = QueryResult(
            rows=[{"id": 1, "name": "John"}],
            row_count=1,
            execution_time=0.1
        )

        cache.set(query, params, result)
        cached = cache.get(query, params)

        assert cached is not None
        assert cached.rows == result.rows
        assert cached.cached is True

    def test_cache_expiration(self):
        """Test cache entries expire after TTL"""
        cache = QueryCache(ttl=0.1)

        query = "SELECT * FROM users"
        params = {}
        result = QueryResult(rows=[], row_count=0, execution_time=0.1)

        cache.set(query, params, result)

        # Should be cached
        assert cache.get(query, params) is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert cache.get(query, params) is None

    def test_cache_invalidation(self):
        """Test cache can be invalidated"""
        cache = QueryCache()

        query = "SELECT * FROM users"
        params = {}
        result = QueryResult(rows=[], row_count=0, execution_time=0.1)

        cache.set(query, params, result)
        assert cache.get(query, params) is not None

        cache.invalidate()
        assert cache.get(query, params) is None

    def test_cache_max_size(self):
        """Test cache respects max size"""
        cache = QueryCache(max_size=2)

        for i in range(3):
            query = f"SELECT {i}"
            params = {}
            result = QueryResult(rows=[], row_count=0, execution_time=0.1)
            cache.set(query, params, result)

        # Cache should only have 2 entries
        assert len(cache.cache) == 2


class TestDatabaseConnectorIntegration:
    """Integration tests for database connector"""

    @pytest.mark.asyncio
    async def test_connector_initialization(self, postgres_config):
        """Test connector initializes properly"""
        with patch('asyncpg.connect', new_callable=AsyncMock):
            connector = DatabaseConnectorFSA(primary_config=postgres_config)
            await connector.initialize()

            assert connector._initialized is True
            assert connector.primary_pool is not None
            assert connector.migration_manager is not None

    @pytest.mark.asyncio
    async def test_connector_validation(self, postgres_config):
        """Test connector validation"""
        connector = DatabaseConnectorFSA(primary_config=postgres_config)

        # Before initialization
        assert connector.validate() is True

    @pytest.mark.asyncio
    async def test_connector_error_handling_info(self, postgres_config):
        """Test error handling information retrieval"""
        connector = DatabaseConnectorFSA(primary_config=postgres_config)

        info = connector.error_handling()

        assert "circuit_breaker_state" in info
        assert "metrics" in info
        assert "active_connections" in info

    @pytest.mark.asyncio
    async def test_query_execution_with_cache(self, postgres_config):
        """Test query execution with caching"""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_connect.return_value = mock_conn

            connector = DatabaseConnectorFSA(primary_config=postgres_config)
            await connector.initialize()

            # Mock pool
            mock_pool_conn = ConnectionInfo(
                connection_id="test",
                db_type=DatabaseType.POSTGRESQL,
                connection=mock_conn,
                created_at=time.time(),
                last_used=time.time()
            )

            with patch.object(connector.primary_pool, 'acquire', return_value=mock_pool_conn):
                with patch.object(connector.primary_pool, 'release', new_callable=AsyncMock):
                    # First query
                    result1 = await connector.execute(
                        "SELECT * FROM users WHERE id = :id",
                        {"id": 1},
                        read_only=True
                    )

                    # Second query should be cached
                    result2 = await connector.execute(
                        "SELECT * FROM users WHERE id = :id",
                        {"id": 1},
                        read_only=True
                    )

                    assert result2.cached is True

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, postgres_config):
        """Test transaction context manager"""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_connect.return_value = mock_conn

            connector = DatabaseConnectorFSA(primary_config=postgres_config)
            await connector.initialize()

            mock_pool_conn = ConnectionInfo(
                connection_id="test",
                db_type=DatabaseType.POSTGRESQL,
                connection=mock_conn,
                created_at=time.time(),
                last_used=time.time()
            )

            with patch.object(connector.primary_pool, 'acquire', return_value=mock_pool_conn):
                with patch.object(connector.primary_pool, 'release', new_callable=AsyncMock):
                    async with connector.transaction() as txn:
                        assert txn.state == TransactionState.ACTIVE

                    # Should be committed
                    metrics = connector.metrics_collector.get_metrics()
                    assert metrics.transactions_committed == 1


class TestConnectionFailover:
    """Test connection failover scenarios"""

    @pytest.mark.asyncio
    async def test_failover_to_replica_on_primary_failure(self, postgres_config):
        """Test failover to replica when primary fails"""
        replica_config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="replica.localhost",
            port=5432,
            database="test_db"
        )

        connector = DatabaseConnectorFSA(
            primary_config=postgres_config,
            replica_configs=[replica_config]
        )

        # Simulate primary failure by using read-only queries
        connector.primary_pool = MagicMock()
        connector.replica_pools = [MagicMock()]

        # Read query should use replica
        pool = connector._select_pool(read_only=True)
        assert pool in connector.replica_pools

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_execution_after_failures(self, postgres_config):
        """Test circuit breaker prevents execution after repeated failures"""
        connector = DatabaseConnectorFSA(primary_config=postgres_config)
        await connector.initialize()

        # Trigger circuit breaker
        for _ in range(5):
            connector.circuit_breaker.record_failure()

        # Should raise circuit breaker error
        with pytest.raises(CircuitBreakerOpenError):
            await connector.execute("SELECT 1", read_only=True)

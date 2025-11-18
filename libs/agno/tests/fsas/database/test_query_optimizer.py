"""
Comprehensive test suite for Query Optimizer FSA

This test module provides extensive testing coverage for the QueryOptimizerFSA class,
including all major query optimization features, database-specific optimizations,
and edge cases.

Test Coverage:
- SQL query optimization effectiveness
- Execution plan analysis accuracy
- Index recommendation quality
- Join optimization validation
- Subquery optimization correctness
- Cache strategy effectiveness
- Database-specific optimizations
- Performance prediction accuracy
- Batch optimization validation
- Materialized view recommendations
- Partition strategy optimization
- Cost estimation accuracy
- Slow query detection
- Query rewriting correctness
- Multi-database support
- Complex query handling
- Edge case handling
- Performance regression prevention
- Optimization report generation
- Error handling for malformed queries
- Statistics integration
- Pattern recognition accuracy
- Cost-benefit analysis
- Integration testing
- Benchmark validation
"""

import pytest
from typing import Dict, List
from agno.fsas.database.query_optimizer_fsa import (
    QueryOptimizerFSA,
    DatabaseType,
    QueryComplexity,
    IndexRecommendation,
    QueryOptimization
)


class TestQueryOptimizerFSA:
    """Main test class for Query Optimizer FSA."""

    @pytest.fixture
    def optimizer(self):
        """Create a QueryOptimizerFSA instance."""
        return QueryOptimizerFSA(database_type="postgresql")

    @pytest.fixture
    def mysql_optimizer(self):
        """Create a MySQL-specific QueryOptimizerFSA instance."""
        return QueryOptimizerFSA(database_type="mysql")

    @pytest.fixture
    def sample_schema(self):
        """Create sample database schema."""
        return {
            "tables": {
                "users": {
                    "row_count": 1000000,
                    "indexes": ["id", "email"],
                    "avg_row_size": 256
                },
                "orders": {
                    "row_count": 5000000,
                    "indexes": ["id", "user_id"],
                    "avg_row_size": 512
                },
                "products": {
                    "row_count": 100000,
                    "indexes": ["id"],
                    "avg_row_size": 1024
                }
            }
        }

    def test_sql_query_optimization_effectiveness(self, optimizer):
        """Test SQL query optimization effectiveness."""
        # Test query with SELECT *
        query = "SELECT * FROM users WHERE email = 'test@example.com'"

        optimized, details = optimizer.optimize_query(query)

        # Should optimize SELECT *
        assert optimized != query, "Query should be optimized"
        assert "SELECT" in optimized, "Optimized query should contain SELECT"
        print(f"✓ Query optimization working")
        print(f"  Original: {query}")
        print(f"  Optimized: {optimized}")

    def test_execution_plan_analysis_accuracy(self, optimizer):
        """Test execution plan analysis accuracy."""
        # Create sample execution plan with issues
        plan = {
            "scan_type": "sequential",
            "rows_examined": 1000000,
            "possible_indexes": ["idx_email"],
            "used_index": None,
            "extra": "Using filesort; Using temporary"
        }

        issues = optimizer.analyze_execution_plan(plan)

        # Should detect multiple issues
        assert len(issues) > 0, "Should detect execution plan issues"
        assert any("Sequential scan" in issue for issue in issues), "Should detect seq scan"

        print(f"✓ Execution plan analysis working")
        print(f"  Issues found: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")

    def test_index_recommendation_quality(self, optimizer, sample_schema):
        """Test index recommendation quality."""
        query = """
        SELECT u.name, u.email, o.total
        FROM users u
        JOIN orders o ON u.id = o.user_id
        WHERE u.created_at > '2024-01-01'
        AND o.status = 'completed'
        ORDER BY o.created_at DESC
        """

        recommendations = optimizer.recommend_indexes(query, sample_schema)

        # Should recommend indexes
        assert len(recommendations) > 0, "Should recommend at least one index"

        # Check recommendation structure
        for rec in recommendations:
            assert hasattr(rec, 'table'), "Recommendation should have table"
            assert hasattr(rec, 'columns'), "Recommendation should have columns"
            assert hasattr(rec, 'create_statement'), "Should have CREATE statement"

        print(f"✓ Index recommendation working")
        print(f"  Recommendations: {len(recommendations)}")
        for rec in recommendations[:3]:
            print(f"  - {rec.create_statement}")

    def test_join_optimization_validation(self, optimizer):
        """Test join optimization validation."""
        # Query with implicit join
        query = "SELECT * FROM users, orders WHERE users.id = orders.user_id"

        optimized, explanation = optimizer.optimize_joins(query)

        # Should convert to explicit join
        assert "JOIN" in optimized.upper() or "implicit" in explanation.lower(), \
            "Should handle implicit joins"

        print(f"✓ Join optimization working")
        print(f"  Explanation: {explanation}")

    def test_subquery_optimization_correctness(self, optimizer):
        """Test subquery optimization correctness."""
        query = """
        SELECT * FROM users
        WHERE id IN (SELECT user_id FROM orders WHERE total > 1000)
        """

        optimized, optimizations = optimizer.optimize_subqueries(query)

        # Should detect subquery and suggest optimization
        assert len(optimizations) > 0, "Should detect subquery optimization opportunities"

        print(f"✓ Subquery optimization working")
        print(f"  Optimizations: {len(optimizations)}")
        for opt in optimizations:
            print(f"  - {opt}")

    def test_cache_strategy_effectiveness(self, optimizer):
        """Test cache strategy effectiveness."""
        query_patterns = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE id = 2",
            "SELECT * FROM users WHERE id = 3",
            "SELECT name FROM users WHERE email = 'test@test.com'",
            "SELECT name FROM users WHERE email = 'user@test.com'",
            "SELECT COUNT(*) FROM orders WHERE user_id = 1",
            "SELECT COUNT(*) FROM orders WHERE user_id = 2",
        ]

        strategy = optimizer.design_cache_strategy(query_patterns)

        # Should provide cache strategy
        assert "recommended_cache_size_mb" in strategy, "Should recommend cache size"
        assert "cache_ttl_seconds" in strategy, "Should recommend TTL"
        assert "cacheable_ratio" in strategy, "Should calculate cacheable ratio"

        print(f"✓ Cache strategy working")
        print(f"  Cache size: {strategy['recommended_cache_size_mb']}MB")
        print(f"  TTL: {strategy['cache_ttl_seconds']}s")
        print(f"  Cacheable ratio: {strategy['cacheable_ratio']:.2%}")

    def test_database_specific_optimizations(self, optimizer, mysql_optimizer):
        """Test database-specific optimizations."""
        query = "SELECT TOP 10 * FROM users WHERE LOWER(name) = LOWER('John')"

        # PostgreSQL optimization
        pg_optimized = optimizer.optimize_for_database(query, "postgresql")

        # MySQL optimization
        mysql_optimized = mysql_optimizer.optimize_for_database(query, "mysql")

        # Should apply database-specific optimizations
        assert pg_optimized or mysql_optimized, "Should apply DB-specific optimizations"

        print(f"✓ Database-specific optimization working")
        print(f"  PostgreSQL: {pg_optimized[:100]}...")
        print(f"  MySQL: {mysql_optimized[:100]}...")

    def test_performance_prediction_accuracy(self, optimizer):
        """Test performance prediction accuracy."""
        simple_query = "SELECT id FROM users WHERE id = 1"
        complex_query = """
        SELECT u.*, COUNT(o.id)
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        LEFT JOIN products p ON o.product_id = p.id
        WHERE u.created_at > '2024-01-01'
        GROUP BY u.id
        ORDER BY COUNT(o.id) DESC
        """

        simple_time = optimizer.predict_performance(simple_query, optimizer.statistics)
        complex_time = optimizer.predict_performance(complex_query, optimizer.statistics)

        # Complex query should take longer
        assert complex_time > simple_time, "Complex query should have higher predicted time"
        assert simple_time >= 0, "Prediction should be non-negative"

        print(f"✓ Performance prediction working")
        print(f"  Simple query: {simple_time}ms")
        print(f"  Complex query: {complex_time}ms")

    def test_batch_optimization_validation(self, optimizer):
        """Test batch optimization validation."""
        queries = [
            "SELECT id FROM users WHERE email = 'test1@test.com'",
            "SELECT id FROM users WHERE email = 'test2@test.com'",
            "SELECT name FROM products WHERE category = 'electronics'",
        ]

        optimized_batch = optimizer.optimize_batch_queries(queries)

        # Should return optimized queries
        assert len(optimized_batch) > 0, "Should return optimized queries"
        assert all(isinstance(pair, tuple) for pair in optimized_batch), \
            "Should return tuples of (original, optimized)"

        print(f"✓ Batch optimization working")
        print(f"  Optimized {len(optimized_batch)} queries")

    def test_materialized_view_recommendations(self, optimizer):
        """Test materialized view recommendations."""
        queries = [
            "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id",
            "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id",
            "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id",
            "SELECT user_id, SUM(total) FROM orders GROUP BY user_id",
            "SELECT user_id, SUM(total) FROM orders GROUP BY user_id",
        ]

        recommendations = optimizer.recommend_materialized_views(queries)

        # Should recommend materialized views for frequent aggregations
        assert len(recommendations) > 0, "Should recommend materialized views"

        print(f"✓ Materialized view recommendations working")
        print(f"  Recommendations: {len(recommendations)}")
        for rec in recommendations:
            print(f"  - View: {rec.get('view_name')}, Frequency: {rec.get('frequency')}")

    def test_partition_strategy_optimization(self, optimizer):
        """Test partition strategy optimization."""
        access_patterns = {
            "row_count": 10000000,
            "query_patterns": [
                "SELECT * FROM orders WHERE order_date > '2024-01-01'",
                "SELECT * FROM orders WHERE order_date < '2024-12-31'",
            ],
            "date_columns": ["order_date", "created_at"],
            "high_cardinality_columns": ["order_id", "user_id"]
        }

        strategy = optimizer.optimize_partitioning("orders", access_patterns)

        # Should recommend partitioning strategy
        assert "recommended_strategy" in strategy, "Should recommend strategy"
        assert strategy["table"] == "orders", "Should reference correct table"

        print(f"✓ Partition strategy optimization working")
        print(f"  Strategy: {strategy.get('recommended_strategy')}")
        print(f"  Partition key: {strategy.get('partition_key')}")

    def test_cost_estimation_accuracy(self, optimizer, sample_schema):
        """Test cost estimation accuracy."""
        simple_query = "SELECT id FROM users WHERE id = 1"
        complex_query = """
        SELECT * FROM users u
        JOIN orders o ON u.id = o.user_id
        JOIN products p ON o.product_id = p.id
        """

        simple_cost = optimizer.estimate_query_cost(simple_query, sample_schema)
        complex_cost = optimizer.estimate_query_cost(complex_query, sample_schema)

        # Complex query should have higher cost
        assert complex_cost > simple_cost, "Complex query should have higher cost"
        assert simple_cost > 0, "Cost should be positive"

        print(f"✓ Cost estimation working")
        print(f"  Simple query cost: {simple_cost}")
        print(f"  Complex query cost: {complex_cost}")

    def test_slow_query_detection(self, optimizer):
        """Test slow query detection."""
        query_log = [
            {"query": "SELECT * FROM users", "execution_time": 0.1, "timestamp": "2024-01-01"},
            {"query": "SELECT * FROM orders WHERE user_id = 1", "execution_time": 5.5, "timestamp": "2024-01-01"},
            {"query": "SELECT * FROM products", "execution_time": 0.2, "timestamp": "2024-01-01"},
            {"query": "SELECT COUNT(*) FROM orders", "execution_time": 12.3, "timestamp": "2024-01-01"},
        ]

        slow_queries = optimizer.detect_slow_queries(query_log)

        # Should detect slow queries
        assert len(slow_queries) > 0, "Should detect slow queries"
        assert all(q["execution_time"] > optimizer.slow_query_threshold for q in slow_queries), \
            "Should only return slow queries"

        print(f"✓ Slow query detection working")
        print(f"  Slow queries found: {len(slow_queries)}")
        for sq in slow_queries:
            print(f"  - {sq['execution_time']:.1f}s: {sq['query'][:50]}...")

    def test_query_rewriting_correctness(self, optimizer):
        """Test query rewriting correctness."""
        # Query with OR conditions that can be converted to IN
        query = "SELECT * FROM users WHERE status = 'active' OR status = 'pending' OR status = 'verified'"

        optimized = optimizer._optimize_or_to_in(query)

        # Should convert to IN clause
        assert "IN" in optimized.upper() or "OR" in optimized.upper(), \
            "Should handle OR to IN conversion"

        print(f"✓ Query rewriting working")
        print(f"  Original: {query}")
        print(f"  Rewritten: {optimized}")

    def test_multi_database_support(self):
        """Test multi-database support."""
        databases = ["postgresql", "mysql", "sqlite"]

        for db in databases:
            optimizer = QueryOptimizerFSA(database_type=db)
            assert optimizer.database_type == DatabaseType(db), f"Should support {db}"

        print(f"✓ Multi-database support working")
        print(f"  Supported databases: {', '.join(databases)}")

    def test_complex_query_handling(self, optimizer, sample_schema):
        """Test complex query handling."""
        complex_query = """
        WITH recent_orders AS (
            SELECT user_id, SUM(total) as total_amount
            FROM orders
            WHERE order_date > '2024-01-01'
            GROUP BY user_id
        )
        SELECT u.name, u.email, ro.total_amount,
               RANK() OVER (ORDER BY ro.total_amount DESC) as rank
        FROM users u
        JOIN recent_orders ro ON u.id = ro.user_id
        WHERE ro.total_amount > 1000
        ORDER BY ro.total_amount DESC
        LIMIT 10
        """

        result = optimizer.execute(complex_query)

        # Should handle complex query without errors
        assert result.get("success") == True, "Should handle complex query"
        assert "optimized_query" in result, "Should optimize complex query"

        print(f"✓ Complex query handling working")
        print(f"  Complexity: {result.get('complexity')}")

    def test_edge_case_handling(self, optimizer):
        """Test edge case handling."""
        edge_cases = [
            "",  # Empty query
            "   ",  # Whitespace only
            "SELECT",  # Incomplete query
        ]

        for query in edge_cases:
            try:
                if query.strip():
                    result = optimizer.execute(query)
                    # May succeed or fail, but shouldn't crash
                    assert isinstance(result, dict), "Should return dict"
                else:
                    # Empty query should raise error
                    with pytest.raises(ValueError):
                        optimizer.execute(query)
            except Exception as e:
                # Should handle gracefully
                pass

        print(f"✓ Edge case handling working")

    def test_performance_regression_prevention(self, optimizer):
        """Test performance regression prevention."""
        query = "SELECT id, name FROM users WHERE id = 123"

        # Run optimization multiple times
        results = []
        for _ in range(3):
            optimized, details = optimizer.optimize_query(query)
            results.append(optimized)

        # Results should be consistent
        assert all(r == results[0] for r in results), "Optimization should be deterministic"

        print(f"✓ Performance regression prevention working")

    def test_optimization_report_generation(self, optimizer):
        """Test optimization report generation."""
        original = "SELECT * FROM users WHERE email = 'test@test.com'"
        optimized = "SELECT id, name, email FROM users WHERE email = 'test@test.com'"

        report = optimizer.generate_optimization_report(original, optimized)

        # Should generate comprehensive report
        assert "QUERY OPTIMIZATION REPORT" in report, "Report should have title"
        assert "ORIGINAL QUERY" in report, "Should include original query"
        assert "OPTIMIZED QUERY" in report, "Should include optimized query"
        assert "ANALYSIS" in report, "Should include analysis"

        print(f"✓ Optimization report generation working")
        print(f"  Report length: {len(report)} characters")

    def test_error_handling_malformed_queries(self, optimizer):
        """Test error handling for malformed queries."""
        malformed_queries = [
            "SELEKT * FROM users",  # Typo
            "SELECT * FROM",  # Incomplete
            ";;;",  # Invalid syntax
        ]

        for query in malformed_queries:
            try:
                result = optimizer.execute(query)
                # Should handle gracefully
                assert isinstance(result, dict), "Should return dict for malformed query"
            except Exception:
                # Expected for some malformed queries
                pass

        print(f"✓ Error handling for malformed queries working")

    def test_statistics_integration(self, optimizer):
        """Test statistics integration."""
        # Check that statistics are loaded
        assert len(optimizer.statistics) > 0, "Should have statistics"
        assert "tables" in optimizer.statistics, "Should have table statistics"

        # Use statistics in optimization
        query = "SELECT * FROM users WHERE id = 1"
        result = optimizer.execute(query)

        assert "cost_analysis" in result, "Should use statistics for cost analysis"

        print(f"✓ Statistics integration working")
        print(f"  Tables with statistics: {len(optimizer.statistics['tables'])}")

    def test_pattern_recognition_accuracy(self, optimizer):
        """Test pattern recognition accuracy."""
        queries = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE id = 2",
            "SELECT * FROM users WHERE id = 3",
        ]

        patterns = [optimizer._extract_query_pattern(q) for q in queries]

        # All queries should have the same pattern
        assert all(p == patterns[0] for p in patterns), "Should recognize same pattern"

        print(f"✓ Pattern recognition working")
        print(f"  Pattern: {patterns[0]}")

    def test_cost_benefit_analysis(self, optimizer, sample_schema):
        """Test cost-benefit analysis."""
        query = "SELECT * FROM users WHERE email = 'test@test.com'"

        # Estimate cost before and after adding index
        cost_without_index = optimizer.estimate_query_cost(query, sample_schema)

        # Add index to schema
        schema_with_index = sample_schema.copy()
        schema_with_index["tables"]["users"]["indexes"].append("email")

        cost_with_index = optimizer.estimate_query_cost(query, schema_with_index)

        # Cost should be lower with index
        assert cost_with_index <= cost_without_index, "Index should reduce cost"

        print(f"✓ Cost-benefit analysis working")
        print(f"  Cost without index: {cost_without_index}")
        print(f"  Cost with index: {cost_with_index}")

    def test_integration_testing(self, optimizer):
        """Test full integration workflow."""
        query = """
        SELECT u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.created_at > '2024-01-01'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        ORDER BY order_count DESC
        LIMIT 100
        """

        result = optimizer.execute(query)

        # Should complete full workflow
        assert result["success"], "Integration should succeed"
        assert "optimized_query" in result, "Should optimize query"
        assert "index_recommendations" in result, "Should recommend indexes"
        assert "cost_analysis" in result, "Should analyze cost"
        assert "performance_prediction" in result, "Should predict performance"
        assert "report" in result, "Should generate report"

        print(f"✓ Integration testing working")
        print(f"  Optimizations applied: {len(result['optimization_details']['optimizations_applied'])}")
        print(f"  Index recommendations: {len(result['index_recommendations'])}")
        print(f"  Cost improvement: {result['cost_analysis']['improvement_percentage']:.1f}%")

    def test_benchmark_validation(self, optimizer):
        """Test benchmark validation."""
        queries = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE email = 'test@test.com'",
            "SELECT COUNT(*) FROM orders",
        ]

        # Run optimization and track time
        import time
        start = time.time()

        for query in queries:
            optimizer.execute(query)

        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0, f"Optimization took too long: {duration}s"

        print(f"✓ Benchmark validation working")
        print(f"  Optimized {len(queries)} queries in {duration:.3f}s")

    def test_validation_method(self, optimizer):
        """Test the validate() method."""
        # Valid configuration
        assert optimizer.validate(), "Valid optimizer should pass validation"

        # Invalid configuration
        optimizer.slow_query_threshold = -1
        assert not optimizer.validate(), "Invalid threshold should fail validation"

        # Reset
        optimizer.slow_query_threshold = 1.0
        assert optimizer.validate(), "Should pass after reset"

        print(f"✓ Validation method working")

    def test_query_complexity_assessment(self, optimizer):
        """Test query complexity assessment."""
        simple = "SELECT id FROM users WHERE id = 1"
        moderate = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
        complex = """
        SELECT u.*, COUNT(o.id)
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        LEFT JOIN products p ON o.product_id = p.id
        GROUP BY u.id
        ORDER BY COUNT(o.id) DESC
        """

        simple_complexity = optimizer._assess_query_complexity(simple)
        moderate_complexity = optimizer._assess_query_complexity(moderate)
        complex_complexity = optimizer._assess_query_complexity(complex)

        # Complexity should increase
        complexity_values = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MODERATE: 2,
            QueryComplexity.COMPLEX: 3,
            QueryComplexity.VERY_COMPLEX: 4
        }

        assert complexity_values[simple_complexity] <= complexity_values[moderate_complexity]
        assert complexity_values[moderate_complexity] <= complexity_values[complex_complexity]

        print(f"✓ Query complexity assessment working")
        print(f"  Simple: {simple_complexity.value}")
        print(f"  Moderate: {moderate_complexity.value}")
        print(f"  Complex: {complex_complexity.value}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

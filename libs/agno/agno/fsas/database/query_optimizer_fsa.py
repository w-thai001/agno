"""
Query Optimizer FSA (Focused Specialized Agent)

This module provides comprehensive database query optimization and analysis capabilities
for the MLA (Multi-Layer Agent) framework. It performs SQL query optimization, execution
plan analysis, index recommendations, and database-specific tuning.

Features:
- SQL query optimization and rewriting
- Query execution plan analysis
- Index recommendation engine
- Join order optimization
- Subquery optimization
- Query caching strategy
- Database-specific optimization (PostgreSQL, MySQL, SQLite, MongoDB)
- Query performance prediction
- Batch query optimization
- Materialized view recommendations
- Partition strategy optimization
- Query cost estimation
- Slow query detection and remediation

Author: Agno Database Team
Version: 1.0.0
"""

import re
import json
import hashlib
import math
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import sys


class DatabaseType(Enum):
    """Enumeration of supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    MSSQL = "mssql"
    ORACLE = "oracle"


class OptimizationType(Enum):
    """Enumeration of optimization types."""
    INDEX = "index"
    JOIN = "join"
    SUBQUERY = "subquery"
    CACHE = "cache"
    PARTITION = "partition"
    REWRITE = "rewrite"


class QueryComplexity(Enum):
    """Enumeration of query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class IndexRecommendation:
    """Represents an index recommendation."""
    table: str
    columns: List[str]
    index_type: str
    estimated_benefit: float
    reason: str
    create_statement: str


@dataclass
class QueryOptimization:
    """Represents a query optimization result."""
    original_query: str
    optimized_query: str
    optimization_type: str
    estimated_improvement: float
    explanation: str
    recommendations: List[str]


@dataclass
class SlowQueryAnalysis:
    """Represents slow query analysis results."""
    query: str
    execution_time: float
    issues: List[str]
    recommendations: List[str]
    severity: str


class QueryOptimizerFSA:
    """
    Query Optimizer FSA (Focused Specialized Agent)

    This agent performs comprehensive database query optimization and analysis,
    providing recommendations for improving query performance across multiple
    database platforms.

    Attributes:
        database_type (DatabaseType): Type of database being optimized
        query_cache (Dict): Cache of previously analyzed queries
        statistics (Dict): Database statistics for cost estimation
        optimization_rules (List): List of optimization rules to apply
    """

    def __init__(self, database_type: str = "postgresql"):
        """
        Initialize the Query Optimizer FSA.

        Args:
            database_type (str): Type of database (postgresql, mysql, sqlite, mongodb)
        """
        self.database_type = DatabaseType(database_type.lower()) if isinstance(database_type, str) else database_type
        self.query_cache: Dict[str, Any] = {}
        self.statistics: Dict[str, Any] = {}
        self.optimization_rules: List[Dict[str, Any]] = []
        self.slow_query_threshold = 1.0  # seconds
        self.metadata: Dict[str, Any] = {
            "queries_optimized": 0,
            "total_improvement": 0.0,
            "cache_hits": 0,
        }
        self._initialize_optimization_rules()
        self._initialize_database_statistics()

    def _initialize_optimization_rules(self) -> None:
        """Initialize query optimization rules."""
        self.optimization_rules = [
            {
                "name": "avoid_select_star",
                "pattern": r"SELECT\s+\*\s+FROM",
                "severity": "medium",
                "description": "SELECT * retrieves unnecessary columns",
                "recommendation": "Specify only required columns"
            },
            {
                "name": "missing_where_clause",
                "pattern": r"SELECT\s+.+\s+FROM\s+\w+\s*;?\s*$",
                "severity": "high",
                "description": "Query without WHERE clause may return entire table",
                "recommendation": "Add WHERE clause to filter results"
            },
            {
                "name": "or_to_in_conversion",
                "pattern": r"WHERE\s+\w+\s*=\s*.+\s+OR\s+\w+\s*=",
                "severity": "low",
                "description": "Multiple OR conditions can be converted to IN",
                "recommendation": "Use IN clause for better performance"
            },
            {
                "name": "function_in_where",
                "pattern": r"WHERE\s+\w+\s*\(\s*\w+\s*\)",
                "severity": "high",
                "description": "Function in WHERE clause prevents index usage",
                "recommendation": "Avoid functions on indexed columns in WHERE"
            },
            {
                "name": "implicit_conversion",
                "pattern": r"WHERE\s+\w+\s*=\s*['\"]",
                "severity": "medium",
                "description": "Potential implicit type conversion",
                "recommendation": "Ensure data types match column definitions"
            },
            {
                "name": "not_null_check",
                "pattern": r"IS\s+NOT\s+NULL",
                "severity": "low",
                "description": "IS NOT NULL checks can sometimes be optimized",
                "recommendation": "Consider restructuring query or using default values"
            },
            {
                "name": "order_by_without_limit",
                "pattern": r"ORDER\s+BY\s+.+(?!.*LIMIT)",
                "severity": "medium",
                "description": "ORDER BY without LIMIT sorts entire result set",
                "recommendation": "Add LIMIT clause if not all results needed"
            },
            {
                "name": "subquery_in_select",
                "pattern": r"SELECT\s+.+\(\s*SELECT",
                "severity": "high",
                "description": "Subquery in SELECT executes for each row",
                "recommendation": "Convert to JOIN or use window functions"
            },
        ]

    def _initialize_database_statistics(self) -> None:
        """Initialize sample database statistics for cost estimation."""
        self.statistics = {
            "tables": {
                "users": {
                    "row_count": 1000000,
                    "avg_row_size": 256,
                    "indexes": ["id", "email", "created_at"],
                    "cardinality": {"id": 1000000, "email": 1000000, "created_at": 365}
                },
                "orders": {
                    "row_count": 5000000,
                    "avg_row_size": 512,
                    "indexes": ["id", "user_id", "order_date"],
                    "cardinality": {"id": 5000000, "user_id": 1000000, "order_date": 1095}
                },
                "products": {
                    "row_count": 100000,
                    "avg_row_size": 1024,
                    "indexes": ["id", "category_id", "sku"],
                    "cardinality": {"id": 100000, "category_id": 100, "sku": 100000}
                },
            },
            "io_cost": 1.0,
            "cpu_cost": 0.01,
            "page_size": 8192,
            "cache_hit_ratio": 0.95
        }

    def execute(self, query: str, database_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute comprehensive query optimization analysis.

        Args:
            query (str): SQL query to optimize
            database_type (str, optional): Database type override

        Returns:
            Dict[str, Any]: Optimization results and recommendations
        """
        if database_type:
            self.database_type = DatabaseType(database_type.lower())

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Check cache
        query_hash = self._hash_query(query)
        if query_hash in self.query_cache:
            self.metadata["cache_hits"] += 1
            return self.query_cache[query_hash]

        try:
            # Normalize query
            normalized_query = self._normalize_query(query)

            # Optimize query
            optimized_query, optimization_details = self.optimize_query(normalized_query)

            # Analyze execution plan
            execution_plan = self._generate_execution_plan(optimized_query)
            plan_issues = self.analyze_execution_plan(execution_plan)

            # Recommend indexes
            schema = self._extract_schema_from_query(normalized_query)
            index_recommendations = self.recommend_indexes(normalized_query, schema)

            # Estimate costs
            original_cost = self.estimate_query_cost(normalized_query, schema)
            optimized_cost = self.estimate_query_cost(optimized_query, schema)

            # Predict performance
            performance_prediction = self.predict_performance(optimized_query, self.statistics)

            # Generate optimization report
            report = self.generate_optimization_report(normalized_query, optimized_query)

            result = {
                "success": True,
                "original_query": normalized_query,
                "optimized_query": optimized_query,
                "optimization_details": optimization_details,
                "execution_plan_issues": plan_issues,
                "index_recommendations": [self._index_to_dict(idx) for idx in index_recommendations],
                "cost_analysis": {
                    "original_cost": original_cost,
                    "optimized_cost": optimized_cost,
                    "improvement_percentage": ((original_cost - optimized_cost) / original_cost * 100) if original_cost > 0 else 0
                },
                "performance_prediction": performance_prediction,
                "complexity": self._assess_query_complexity(normalized_query).value,
                "report": report,
                "metadata": self.metadata
            }

            # Cache result
            self.query_cache[query_hash] = result
            self.metadata["queries_optimized"] += 1

            return result

        except Exception as e:
            return self.error_handling(e)

    def optimize_query(self, sql: str) -> Tuple[str, Dict[str, Any]]:
        """
        Optimize SQL query using various optimization techniques.

        Args:
            sql (str): SQL query to optimize

        Returns:
            Tuple[str, Dict[str, Any]]: Optimized query and optimization details
        """
        optimized = sql
        optimizations_applied = []

        # Apply optimization rules
        for rule in self.optimization_rules:
            if re.search(rule["pattern"], optimized, re.IGNORECASE):
                optimizations_applied.append({
                    "rule": rule["name"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "recommendation": rule["recommendation"]
                })

        # Optimize SELECT *
        if re.search(r"SELECT\s+\*", optimized, re.IGNORECASE):
            # Extract table name
            table_match = re.search(r"FROM\s+(\w+)", optimized, re.IGNORECASE)
            if table_match:
                optimized = self._replace_select_star(optimized, table_match.group(1))

        # Optimize OR conditions to IN
        optimized = self._optimize_or_to_in(optimized)

        # Optimize subqueries
        optimized, subquery_opts = self.optimize_subqueries(optimized)
        if subquery_opts:
            optimizations_applied.extend(subquery_opts)

        # Optimize joins
        optimized, join_explanation = self.optimize_joins(optimized)

        # Database-specific optimizations
        optimized = self.optimize_for_database(optimized, self.database_type.value)

        # Add query hints if beneficial
        optimized = self._add_query_hints(optimized)

        details = {
            "optimizations_applied": optimizations_applied,
            "join_optimization": join_explanation,
            "estimated_improvement": self._calculate_improvement(sql, optimized)
        }

        return optimized, details

    def analyze_execution_plan(self, plan: Dict[str, Any]) -> List[str]:
        """
        Analyze query execution plan for potential issues.

        Args:
            plan (Dict[str, Any]): Execution plan data

        Returns:
            List[str]: List of identified issues and recommendations
        """
        issues = []

        # Check for sequential scans
        if self._contains_sequential_scan(plan):
            issues.append("Sequential scan detected - consider adding indexes")

        # Check for nested loop joins on large tables
        if self._contains_nested_loop_join(plan):
            issues.append("Nested loop join on large table - consider hash join or merge join")

        # Check for filesort
        if self._contains_filesort(plan):
            issues.append("Filesort operation detected - consider adding index on ORDER BY columns")

        # Check for temporary tables
        if self._contains_temp_table(plan):
            issues.append("Temporary table created - query may benefit from restructuring")

        # Check for full table scans
        if plan.get("scan_type") == "full_table":
            issues.append("Full table scan detected - add WHERE clause or indexes")

        # Check for high row estimates
        if plan.get("rows_examined", 0) > 10000:
            issues.append(f"High number of rows examined ({plan.get('rows_examined')}) - optimize filters")

        # Check for missing statistics
        if plan.get("statistics_missing"):
            issues.append("Missing table statistics - run ANALYZE/UPDATE STATISTICS")

        # Check for index not used
        if plan.get("possible_indexes") and not plan.get("used_index"):
            issues.append("Available indexes not used - check query predicates")

        return issues

    def recommend_indexes(self, query: str, schema: Dict[str, Any]) -> List[IndexRecommendation]:
        """
        Recommend indexes based on query analysis.

        Args:
            query (str): SQL query to analyze
            schema (Dict[str, Any]): Database schema information

        Returns:
            List[IndexRecommendation]: List of index recommendations
        """
        recommendations = []

        # Extract WHERE clause columns
        where_columns = self._extract_where_columns(query)
        for table, columns in where_columns.items():
            if columns and table in schema.get("tables", {}):
                existing_indexes = schema["tables"][table].get("indexes", [])

                # Check if columns are already indexed
                for col in columns:
                    if col not in existing_indexes:
                        recommendations.append(IndexRecommendation(
                            table=table,
                            columns=[col],
                            index_type="btree",
                            estimated_benefit=self._estimate_index_benefit(table, [col]),
                            reason=f"Column '{col}' used in WHERE clause",
                            create_statement=f"CREATE INDEX idx_{table}_{col} ON {table}({col});"
                        ))

        # Extract JOIN columns
        join_columns = self._extract_join_columns(query)
        for table, columns in join_columns.items():
            if columns and table in schema.get("tables", {}):
                for col in columns:
                    existing_indexes = schema["tables"][table].get("indexes", [])
                    if col not in existing_indexes:
                        recommendations.append(IndexRecommendation(
                            table=table,
                            columns=[col],
                            index_type="btree",
                            estimated_benefit=self._estimate_index_benefit(table, [col]),
                            reason=f"Column '{col}' used in JOIN condition",
                            create_statement=f"CREATE INDEX idx_{table}_{col}_join ON {table}({col});"
                        ))

        # Extract ORDER BY columns
        order_columns = self._extract_order_by_columns(query)
        for table, columns in order_columns.items():
            if columns and table in schema.get("tables", {}):
                existing_indexes = schema["tables"][table].get("indexes", [])
                cols_str = ", ".join(columns)
                if not any(col in existing_indexes for col in columns):
                    recommendations.append(IndexRecommendation(
                        table=table,
                        columns=columns,
                        index_type="btree",
                        estimated_benefit=self._estimate_index_benefit(table, columns),
                        reason=f"Columns {columns} used in ORDER BY clause",
                        create_statement=f"CREATE INDEX idx_{table}_order ON {table}({cols_str});"
                    ))

        # Composite index recommendations
        if len(where_columns) > 0:
            for table, columns in where_columns.items():
                if len(columns) > 1:
                    cols_str = ", ".join(columns[:3])  # Limit to 3 columns
                    recommendations.append(IndexRecommendation(
                        table=table,
                        columns=columns[:3],
                        index_type="btree",
                        estimated_benefit=self._estimate_index_benefit(table, columns[:3]) * 1.5,
                        reason="Composite index for multiple WHERE conditions",
                        create_statement=f"CREATE INDEX idx_{table}_composite ON {table}({cols_str});"
                    ))

        # Sort by estimated benefit
        recommendations.sort(key=lambda x: x.estimated_benefit, reverse=True)

        return recommendations[:10]  # Return top 10 recommendations

    def optimize_joins(self, query: str) -> Tuple[str, str]:
        """
        Optimize JOIN operations in the query.

        Args:
            query (str): SQL query with JOINs

        Returns:
            Tuple[str, str]: Optimized query and explanation
        """
        optimized = query
        explanations = []

        # Check for implicit joins (comma-separated tables)
        implicit_join_pattern = r"FROM\s+(\w+)\s*,\s*(\w+)"
        if re.search(implicit_join_pattern, query, re.IGNORECASE):
            # Convert to explicit INNER JOIN
            optimized = re.sub(
                implicit_join_pattern,
                r"FROM \1 INNER JOIN \2",
                optimized,
                flags=re.IGNORECASE
            )
            explanations.append("Converted implicit JOIN to explicit INNER JOIN")

        # Optimize join order (put smaller tables first)
        join_tables = self._extract_join_tables(query)
        if len(join_tables) > 1:
            ordered_tables = self._order_join_tables(join_tables)
            explanations.append(f"Recommended join order: {' -> '.join(ordered_tables)}")

        # Check for cross joins
        if re.search(r"CROSS\s+JOIN", query, re.IGNORECASE):
            explanations.append("Warning: CROSS JOIN detected - ensure this is intentional")

        # Recommend join type based on data distribution
        if "LEFT JOIN" in query.upper():
            explanations.append("LEFT JOIN detected - consider if INNER JOIN is sufficient")

        # Check for join conditions
        if re.search(r"JOIN\s+\w+\s+(?!ON|USING)", query, re.IGNORECASE):
            explanations.append("Warning: JOIN without ON clause may cause Cartesian product")

        explanation = "; ".join(explanations) if explanations else "No join optimizations needed"

        return optimized, explanation

    def optimize_subqueries(self, query: str) -> Tuple[str, List[str]]:
        """
        Optimize subqueries in the SQL query.

        Args:
            query (str): SQL query with subqueries

        Returns:
            Tuple[str, List[str]]: Optimized query and list of optimizations
        """
        optimized = query
        optimizations = []

        # Detect subqueries in SELECT clause
        select_subquery_pattern = r"SELECT\s+[^,]*\(\s*SELECT\s+.+?\)\s*[^,]*"
        if re.search(select_subquery_pattern, query, re.IGNORECASE):
            optimizations.append("Subquery in SELECT clause - consider converting to JOIN")

        # Detect subqueries in WHERE IN
        where_in_subquery = r"WHERE\s+\w+\s+IN\s*\(\s*SELECT"
        if re.search(where_in_subquery, query, re.IGNORECASE):
            # Can often be converted to EXISTS or JOIN
            optimizations.append("WHERE IN subquery - consider converting to EXISTS or JOIN for better performance")

        # Detect correlated subqueries
        if self._is_correlated_subquery(query):
            optimizations.append("Correlated subquery detected - consider converting to JOIN or window function")
            # Attempt to convert to JOIN
            optimized = self._convert_correlated_to_join(query)

        # Detect subqueries in FROM clause (derived tables)
        from_subquery_pattern = r"FROM\s*\(\s*SELECT"
        if re.search(from_subquery_pattern, query, re.IGNORECASE):
            optimizations.append("Derived table in FROM clause - ensure proper indexing and filtering")

        # Optimize NOT IN to NOT EXISTS
        not_in_pattern = r"WHERE\s+\w+\s+NOT\s+IN\s*\(\s*SELECT"
        if re.search(not_in_pattern, query, re.IGNORECASE):
            optimizations.append("WHERE NOT IN - consider converting to NOT EXISTS or LEFT JOIN with NULL check")

        return optimized, optimizations

    def design_cache_strategy(self, query_patterns: List[str]) -> Dict[str, Any]:
        """
        Design caching strategy based on query patterns.

        Args:
            query_patterns (List[str]): List of query patterns

        Returns:
            Dict[str, Any]: Caching strategy recommendations
        """
        # Analyze query patterns
        pattern_frequency = Counter()
        cacheable_queries = []
        volatile_queries = []

        for query in query_patterns:
            # Normalize query
            normalized = self._normalize_query(query)
            pattern_hash = self._extract_query_pattern(normalized)
            pattern_frequency[pattern_hash] += 1

            # Determine if query is cacheable
            if self._is_cacheable(normalized):
                cacheable_queries.append(normalized)
            else:
                volatile_queries.append(normalized)

        # Identify frequently executed queries
        frequent_queries = [
            pattern for pattern, count in pattern_frequency.most_common(10)
            if count > 1
        ]

        # Calculate cache parameters
        total_queries = len(query_patterns)
        cacheable_ratio = len(cacheable_queries) / total_queries if total_queries > 0 else 0

        strategy = {
            "recommended_cache_size_mb": self._calculate_cache_size(cacheable_queries),
            "cache_ttl_seconds": self._calculate_cache_ttl(query_patterns),
            "cacheable_ratio": cacheable_ratio,
            "frequent_query_patterns": frequent_queries,
            "cache_key_strategy": "query_hash_with_params",
            "eviction_policy": "LRU",
            "cache_warming_queries": frequent_queries[:5],
            "recommendations": []
        }

        if cacheable_ratio > 0.7:
            strategy["recommendations"].append("High cacheable ratio - aggressive caching recommended")
        elif cacheable_ratio < 0.3:
            strategy["recommendations"].append("Low cacheable ratio - focus on query optimization over caching")

        if len(frequent_queries) > 5:
            strategy["recommendations"].append("Many frequent query patterns - implement query result caching")

        if len(volatile_queries) > len(cacheable_queries):
            strategy["recommendations"].append("Many volatile queries - consider materialized views for aggregations")

        return strategy

    def optimize_for_database(self, query: str, db_type: str) -> str:
        """
        Apply database-specific optimizations.

        Args:
            query (str): SQL query to optimize
            db_type (str): Database type

        Returns:
            str: Database-optimized query
        """
        optimized = query
        db = DatabaseType(db_type.lower())

        if db == DatabaseType.POSTGRESQL:
            # PostgreSQL-specific optimizations
            # Use EXPLAIN ANALYZE for performance testing
            # Prefer LIMIT over subqueries
            if "TOP" in optimized.upper():
                optimized = optimized.replace("TOP", "LIMIT")

            # Use ILIKE for case-insensitive search
            optimized = re.sub(r"LOWER\((\w+)\)\s*=\s*LOWER\('([^']+)'\)",
                             r"\1 ILIKE '\2'", optimized, flags=re.IGNORECASE)

        elif db == DatabaseType.MYSQL:
            # MySQL-specific optimizations
            # Use LIMIT for pagination
            # Prefer JOIN over subqueries
            # Use FORCE INDEX hints when necessary
            if "OFFSET" in optimized.upper() and "LIMIT" not in optimized.upper():
                optimized += " LIMIT 1000"  # Add reasonable default

        elif db == DatabaseType.SQLITE:
            # SQLite-specific optimizations
            # Avoid complex subqueries
            # Use INDEXED BY for specific index usage
            # Prefer simple queries
            pass

        elif db == DatabaseType.MONGODB:
            # MongoDB is NoSQL, different optimization approach
            # Would need to convert SQL to MongoDB aggregation pipeline
            pass

        return optimized

    def predict_performance(self, query: str, statistics: Dict[str, Any]) -> float:
        """
        Predict query performance based on statistics.

        Args:
            query (str): SQL query
            statistics (Dict[str, Any]): Database statistics

        Returns:
            float: Predicted execution time in milliseconds
        """
        # Extract query components
        tables = self._extract_tables_from_query(query)
        has_joins = bool(re.search(r"\bJOIN\b", query, re.IGNORECASE))
        has_subquery = bool(re.search(r"\(\s*SELECT", query, re.IGNORECASE))
        has_aggregation = bool(re.search(r"\b(COUNT|SUM|AVG|MAX|MIN|GROUP BY)\b", query, re.IGNORECASE))
        has_order_by = bool(re.search(r"\bORDER BY\b", query, re.IGNORECASE))

        # Estimate rows to scan
        total_rows = 0
        for table in tables:
            if table in statistics.get("tables", {}):
                total_rows += statistics["tables"][table].get("row_count", 1000)

        # Base cost calculation
        io_cost = total_rows * statistics.get("io_cost", 1.0)
        cpu_cost = total_rows * statistics.get("cpu_cost", 0.01)

        # Adjust for operations
        multiplier = 1.0
        if has_joins:
            multiplier *= (len(tables) ** 0.5)  # Join complexity
        if has_subquery:
            multiplier *= 2.0  # Subqueries are expensive
        if has_aggregation:
            multiplier *= 1.5  # Aggregation overhead
        if has_order_by:
            multiplier *= 1.3  # Sorting overhead

        # Calculate predicted time
        predicted_cost = (io_cost + cpu_cost) * multiplier

        # Apply cache hit ratio
        cache_benefit = statistics.get("cache_hit_ratio", 0.95)
        predicted_time = predicted_cost * (1 - cache_benefit)

        # Convert to milliseconds
        return round(predicted_time, 2)

    def optimize_batch_queries(self, queries: List[str]) -> List[Tuple[str, str]]:
        """
        Optimize a batch of queries together.

        Args:
            queries (List[str]): List of SQL queries

        Returns:
            List[Tuple[str, str]]: List of (original, optimized) query pairs
        """
        optimized_queries = []

        # Identify common patterns
        common_tables = self._find_common_tables(queries)

        for query in queries:
            optimized, _ = self.optimize_query(query)

            # Check if queries can be combined
            if self._can_combine_with_previous(optimized, optimized_queries):
                # Merge with previous query
                if optimized_queries:
                    prev_query = optimized_queries[-1][1]
                    combined = self._combine_queries(prev_query, optimized)
                    optimized_queries[-1] = (query, combined)
                    continue

            optimized_queries.append((query, optimized))

        return optimized_queries

    def recommend_materialized_views(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Recommend materialized views based on query patterns.

        Args:
            queries (List[str]): List of frequently executed queries

        Returns:
            List[Dict[str, Any]]: List of materialized view recommendations
        """
        recommendations = []

        # Analyze queries for common aggregations
        aggregation_patterns = defaultdict(int)

        for query in queries:
            if re.search(r"\b(GROUP BY|COUNT|SUM|AVG)\b", query, re.IGNORECASE):
                pattern = self._extract_aggregation_pattern(query)
                aggregation_patterns[pattern] += 1

        # Recommend materialized views for frequent aggregations
        for pattern, frequency in aggregation_patterns.items():
            if frequency >= 3:  # Appears in at least 3 queries
                recommendations.append({
                    "view_name": f"mv_{hashlib.md5(pattern.encode()).hexdigest()[:8]}",
                    "query_pattern": pattern,
                    "frequency": frequency,
                    "estimated_benefit": frequency * 0.8,  # 80% speedup per usage
                    "create_statement": f"CREATE MATERIALIZED VIEW mv_... AS {pattern}",
                    "refresh_strategy": "ON DEMAND" if frequency < 10 else "ON COMMIT"
                })

        # Check for complex joins that are frequently executed
        join_patterns = defaultdict(int)
        for query in queries:
            if query.upper().count("JOIN") >= 2:
                tables = self._extract_tables_from_query(query)
                join_pattern = "-".join(sorted(tables))
                join_patterns[join_pattern] += 1

        for pattern, frequency in join_patterns.items():
            if frequency >= 5:
                recommendations.append({
                    "view_name": f"mv_join_{pattern.replace('-', '_')}",
                    "tables_involved": pattern.split('-'),
                    "frequency": frequency,
                    "estimated_benefit": frequency * 0.6,
                    "reason": "Frequently joined tables",
                    "refresh_strategy": "SCHEDULED"
                })

        # Sort by estimated benefit
        recommendations.sort(key=lambda x: x.get("estimated_benefit", 0), reverse=True)

        return recommendations[:5]  # Top 5 recommendations

    def optimize_partitioning(self, table: str, access_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize table partitioning strategy.

        Args:
            table (str): Table name
            access_patterns (Dict[str, Any]): Access pattern data

        Returns:
            Dict[str, Any]: Partitioning recommendations
        """
        recommendations = {
            "table": table,
            "current_partitioning": access_patterns.get("current_partitioning", "none"),
            "recommended_strategy": None,
            "partition_key": None,
            "estimated_benefit": 0.0,
            "implementation": None
        }

        # Analyze access patterns
        row_count = access_patterns.get("row_count", 0)
        query_patterns = access_patterns.get("query_patterns", [])
        date_columns = access_patterns.get("date_columns", [])
        high_cardinality_columns = access_patterns.get("high_cardinality_columns", [])

        # Large table benefit from partitioning
        if row_count > 1000000:
            # Check for date-based queries
            date_based_queries = sum(1 for q in query_patterns if any(col in q for col in date_columns))

            if date_based_queries > len(query_patterns) * 0.5:
                # Recommend date-based partitioning
                recommendations["recommended_strategy"] = "RANGE"
                recommendations["partition_key"] = date_columns[0] if date_columns else "created_at"
                recommendations["estimated_benefit"] = 0.7
                recommendations["implementation"] = f"""
ALTER TABLE {table} PARTITION BY RANGE ({recommendations['partition_key']}) (
    PARTITION p_2023 VALUES LESS THAN ('2024-01-01'),
    PARTITION p_2024 VALUES LESS THAN ('2025-01-01'),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
"""

            elif high_cardinality_columns:
                # Recommend hash partitioning
                recommendations["recommended_strategy"] = "HASH"
                recommendations["partition_key"] = high_cardinality_columns[0]
                recommendations["estimated_benefit"] = 0.5
                recommendations["implementation"] = f"""
ALTER TABLE {table} PARTITION BY HASH({recommendations['partition_key']})
PARTITIONS 16;
"""

        return recommendations

    def estimate_query_cost(self, query: str, schema: Dict[str, Any]) -> float:
        """
        Estimate the cost of executing a query.

        Args:
            query (str): SQL query
            schema (Dict[str, Any]): Database schema information

        Returns:
            float: Estimated cost (arbitrary units)
        """
        cost = 0.0

        # Extract tables
        tables = self._extract_tables_from_query(query)

        # Base cost: sum of table sizes
        for table in tables:
            if table in schema.get("tables", {}):
                row_count = schema["tables"][table].get("row_count", 1000)
                cost += row_count * 0.01  # Base scan cost

        # Join cost
        join_count = len(re.findall(r"\bJOIN\b", query, re.IGNORECASE))
        if join_count > 0:
            # Nested loop join cost is multiplicative
            cost *= (1 + join_count * 0.5)

        # Subquery cost
        subquery_count = len(re.findall(r"\(\s*SELECT", query, re.IGNORECASE))
        cost += subquery_count * 100  # Subqueries are expensive

        # Sort cost
        if re.search(r"\bORDER BY\b", query, re.IGNORECASE):
            cost *= 1.3  # Sorting overhead

        # Aggregation cost
        if re.search(r"\b(GROUP BY|COUNT|SUM|AVG)\b", query, re.IGNORECASE):
            cost *= 1.2

        # Check for index usage
        where_columns = self._extract_where_columns(query)
        indexed_columns = 0
        for table, columns in where_columns.items():
            if table in schema.get("tables", {}):
                indexes = schema["tables"][table].get("indexes", [])
                indexed_columns += sum(1 for col in columns if col in indexes)

        # Reduce cost if indexes are used
        if indexed_columns > 0:
            cost *= (1 - (indexed_columns * 0.1))  # 10% reduction per indexed column

        return round(cost, 2)

    def detect_slow_queries(self, query_log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect and analyze slow queries from query log.

        Args:
            query_log (List[Dict[str, Any]]): List of query execution records

        Returns:
            List[Dict[str, Any]]: List of slow query analyses
        """
        slow_queries = []

        for entry in query_log:
            query = entry.get("query", "")
            execution_time = entry.get("execution_time", 0)

            if execution_time > self.slow_query_threshold:
                # Analyze the slow query
                issues = []
                recommendations = []

                # Check for missing indexes
                if "WHERE" in query.upper() and "INDEX" not in query.upper():
                    issues.append("No index scan detected")
                    recommendations.append("Add indexes on WHERE clause columns")

                # Check for SELECT *
                if "SELECT *" in query.upper():
                    issues.append("SELECT * used")
                    recommendations.append("Select only necessary columns")

                # Check for missing WHERE
                if "WHERE" not in query.upper() and "SELECT" in query.upper():
                    issues.append("No WHERE clause - full table scan")
                    recommendations.append("Add WHERE clause to filter results")

                # Check for complex joins
                join_count = query.upper().count("JOIN")
                if join_count > 3:
                    issues.append(f"Complex query with {join_count} joins")
                    recommendations.append("Consider denormalization or materialized views")

                # Determine severity
                if execution_time > 10.0:
                    severity = "critical"
                elif execution_time > 5.0:
                    severity = "high"
                elif execution_time > 2.0:
                    severity = "medium"
                else:
                    severity = "low"

                slow_queries.append({
                    "query": query,
                    "execution_time": execution_time,
                    "issues": issues,
                    "recommendations": recommendations,
                    "severity": severity,
                    "timestamp": entry.get("timestamp", "")
                })

        # Sort by execution time (slowest first)
        slow_queries.sort(key=lambda x: x["execution_time"], reverse=True)

        return slow_queries

    def generate_optimization_report(self, original: str, optimized: str) -> str:
        """
        Generate comprehensive optimization report.

        Args:
            original (str): Original query
            optimized (str): Optimized query

        Returns:
            str: Formatted optimization report
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("QUERY OPTIMIZATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Database Type: {self.database_type.value}")
        report_lines.append("")

        # Original Query
        report_lines.append("ORIGINAL QUERY:")
        report_lines.append("-" * 80)
        report_lines.append(original)
        report_lines.append("")

        # Optimized Query
        report_lines.append("OPTIMIZED QUERY:")
        report_lines.append("-" * 80)
        report_lines.append(optimized)
        report_lines.append("")

        # Analysis
        report_lines.append("ANALYSIS:")
        report_lines.append("-" * 80)

        # Calculate improvements
        original_complexity = self._assess_query_complexity(original)
        optimized_complexity = self._assess_query_complexity(optimized)

        report_lines.append(f"Original Complexity: {original_complexity.value}")
        report_lines.append(f"Optimized Complexity: {optimized_complexity.value}")

        # Estimate improvements
        schema = self._extract_schema_from_query(original)
        original_cost = self.estimate_query_cost(original, schema)
        optimized_cost = self.estimate_query_cost(optimized, schema)
        improvement = ((original_cost - optimized_cost) / original_cost * 100) if original_cost > 0 else 0

        report_lines.append(f"Original Estimated Cost: {original_cost:.2f}")
        report_lines.append(f"Optimized Estimated Cost: {optimized_cost:.2f}")
        report_lines.append(f"Estimated Improvement: {improvement:.1f}%")
        report_lines.append("")

        # Recommendations
        recommendations = self.recommend_indexes(original, schema)
        if recommendations:
            report_lines.append("INDEX RECOMMENDATIONS:")
            report_lines.append("-" * 80)
            for idx, rec in enumerate(recommendations[:5], 1):
                report_lines.append(f"{idx}. {rec.create_statement}")
                report_lines.append(f"   Reason: {rec.reason}")
                report_lines.append(f"   Estimated Benefit: {rec.estimated_benefit:.2f}")
            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def validate(self) -> bool:
        """
        Validate the FSA configuration and state.

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(self.database_type, DatabaseType):
            return False
        if self.slow_query_threshold <= 0:
            return False
        if not isinstance(self.statistics, dict):
            return False
        return True

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle errors during query optimization.

        Args:
            exception (Exception): The exception that occurred

        Returns:
            Dict[str, Any]: Error information
        """
        error_info = {
            "success": False,
            "error": {
                "type": type(exception).__name__,
                "message": str(exception),
                "timestamp": datetime.now().isoformat()
            },
            "partial_results": {
                "queries_optimized": self.metadata.get("queries_optimized", 0),
                "cache_hits": self.metadata.get("cache_hits", 0)
            }
        }

        print(f"Query Optimizer FSA Error: {error_info}", file=sys.stderr)

        return error_info

    # Helper methods

    def _hash_query(self, query: str) -> str:
        """Generate hash for query caching."""
        return hashlib.md5(query.encode()).hexdigest()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent processing."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        return normalized

    def _replace_select_star(self, query: str, table: str) -> str:
        """Replace SELECT * with specific columns."""
        # This is a simplified version - in production, would need schema
        columns = "id, name, email, created_at"  # Example columns
        return re.sub(r"SELECT\s+\*", f"SELECT {columns}", query, flags=re.IGNORECASE)

    def _optimize_or_to_in(self, query: str) -> str:
        """Convert multiple OR conditions to IN clause."""
        # Pattern: column = value1 OR column = value2 OR ...
        pattern = r"(\w+)\s*=\s*'([^']+)'(?:\s+OR\s+\1\s*=\s*'([^']+)')+"

        def replacer(match):
            column = match.group(1)
            values = re.findall(r"'([^']+)'", match.group(0))
            return f"{column} IN ('" + "', '".join(values) + "')"

        return re.sub(pattern, replacer, query, flags=re.IGNORECASE)

    def _add_query_hints(self, query: str) -> str:
        """Add database hints if beneficial."""
        # Example: Add USE INDEX hint for MySQL
        if self.database_type == DatabaseType.MYSQL:
            # This is simplified - real implementation would analyze query
            pass
        return query

    def _calculate_improvement(self, original: str, optimized: str) -> float:
        """Calculate estimated improvement percentage."""
        # Simplified calculation based on query length and complexity
        orig_score = len(original) + original.upper().count("SELECT") * 10
        opt_score = len(optimized) + optimized.upper().count("SELECT") * 10

        if orig_score == 0:
            return 0.0

        improvement = ((orig_score - opt_score) / orig_score) * 100
        return max(0, min(100, improvement))

    def _contains_sequential_scan(self, plan: Dict[str, Any]) -> bool:
        """Check if execution plan contains sequential scan."""
        return plan.get("scan_type") == "sequential" or "Seq Scan" in str(plan)

    def _contains_nested_loop_join(self, plan: Dict[str, Any]) -> bool:
        """Check for nested loop joins."""
        return "Nested Loop" in str(plan) or plan.get("join_type") == "nested_loop"

    def _contains_filesort(self, plan: Dict[str, Any]) -> bool:
        """Check for filesort operation."""
        return "filesort" in str(plan).lower() or plan.get("extra", "").lower().count("filesort") > 0

    def _contains_temp_table(self, plan: Dict[str, Any]) -> bool:
        """Check for temporary table creation."""
        return "temporary" in str(plan).lower() or plan.get("extra", "").lower().count("temporary") > 0

    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract columns used in WHERE clause."""
        where_columns = defaultdict(list)

        # Simple pattern matching for WHERE clause
        where_match = re.search(r"WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|;|$)", query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)

            # Extract column references (simplified)
            column_pattern = r"(\w+)\.(\w+)|(\w+)\s*[=<>]"
            for match in re.finditer(column_pattern, where_clause):
                if match.group(1) and match.group(2):
                    where_columns[match.group(1)].append(match.group(2))
                elif match.group(3):
                    # No table prefix, assume first table
                    tables = self._extract_tables_from_query(query)
                    if tables:
                        where_columns[tables[0]].append(match.group(3))

        return dict(where_columns)

    def _extract_join_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract columns used in JOIN conditions."""
        join_columns = defaultdict(list)

        # Pattern for JOIN conditions
        join_pattern = r"JOIN\s+(\w+)(?:\s+AS\s+\w+)?\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)"
        for match in re.finditer(join_pattern, query, re.IGNORECASE):
            table = match.group(1)
            col = match.group(3)
            join_columns[table].append(col)

        return dict(join_columns)

    def _extract_order_by_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract columns used in ORDER BY clause."""
        order_columns = defaultdict(list)

        order_match = re.search(r"ORDER BY\s+(.+?)(?:LIMIT|;|$)", query, re.IGNORECASE)
        if order_match:
            order_clause = order_match.group(1)
            columns = [col.strip().split()[0] for col in order_clause.split(',')]

            tables = self._extract_tables_from_query(query)
            if tables:
                for col in columns:
                    if '.' in col:
                        table, column = col.split('.')
                        order_columns[table].append(column)
                    else:
                        order_columns[tables[0]].append(col)

        return dict(order_columns)

    def _estimate_index_benefit(self, table: str, columns: List[str]) -> float:
        """Estimate benefit of creating an index."""
        # Simplified estimation based on table size
        if table in self.statistics.get("tables", {}):
            row_count = self.statistics["tables"][table].get("row_count", 1000)
            # Benefit increases with table size
            return min(100, math.log10(row_count + 1) * 10)
        return 50.0  # Default benefit

    def _extract_join_tables(self, query: str) -> List[str]:
        """Extract tables involved in JOINs."""
        tables = []
        join_pattern = r"JOIN\s+(\w+)"
        for match in re.finditer(join_pattern, query, re.IGNORECASE):
            tables.append(match.group(1))
        return tables

    def _order_join_tables(self, tables: List[str]) -> List[str]:
        """Order tables for optimal join sequence."""
        # Order by table size (smallest first)
        table_sizes = {}
        for table in tables:
            if table in self.statistics.get("tables", {}):
                table_sizes[table] = self.statistics["tables"][table].get("row_count", 1000000)
            else:
                table_sizes[table] = 1000000

        return sorted(tables, key=lambda t: table_sizes.get(t, 1000000))

    def _is_correlated_subquery(self, query: str) -> bool:
        """Check if query contains correlated subquery."""
        # Simplified check - look for subquery with reference to outer query
        subquery_pattern = r"\(\s*SELECT.*WHERE.*=.*\)"
        return bool(re.search(subquery_pattern, query, re.IGNORECASE | re.DOTALL))

    def _convert_correlated_to_join(self, query: str) -> str:
        """Attempt to convert correlated subquery to JOIN."""
        # This is a complex transformation - simplified version
        return query  # Return original for now

    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from query."""
        tables = []

        # FROM clause
        from_pattern = r"FROM\s+(\w+)"
        tables.extend(re.findall(from_pattern, query, re.IGNORECASE))

        # JOIN clauses
        join_pattern = r"JOIN\s+(\w+)"
        tables.extend(re.findall(join_pattern, query, re.IGNORECASE))

        return list(set(tables))  # Remove duplicates

    def _extract_query_pattern(self, query: str) -> str:
        """Extract abstract pattern from query."""
        # Replace specific values with placeholders
        pattern = re.sub(r"'[^']*'", "?", query)
        pattern = re.sub(r"\b\d+\b", "?", pattern)
        return pattern

    def _is_cacheable(self, query: str) -> bool:
        """Determine if query result is cacheable."""
        # Queries with NOW(), RAND(), etc. are not cacheable
        non_cacheable_functions = ['NOW()', 'CURRENT_TIMESTAMP', 'RAND()', 'UUID()']
        return not any(func in query.upper() for func in non_cacheable_functions)

    def _calculate_cache_size(self, queries: List[str]) -> int:
        """Calculate recommended cache size in MB."""
        # Estimate based on number of unique queries
        unique_patterns = len(set(self._extract_query_pattern(q) for q in queries))
        # Assume average result size of 100KB
        return max(64, unique_patterns * 100 // 1024)

    def _calculate_cache_ttl(self, queries: List[str]) -> int:
        """Calculate recommended cache TTL in seconds."""
        # Default to 5 minutes, could be adjusted based on update frequency
        return 300

    def _find_common_tables(self, queries: List[str]) -> Set[str]:
        """Find tables common across queries."""
        table_sets = [set(self._extract_tables_from_query(q)) for q in queries]
        if not table_sets:
            return set()
        return set.intersection(*table_sets)

    def _can_combine_with_previous(self, query: str, previous_queries: List[Tuple[str, str]]) -> bool:
        """Check if query can be combined with previous ones."""
        # Simplified - check if accessing same tables
        if not previous_queries:
            return False

        current_tables = set(self._extract_tables_from_query(query))
        previous_tables = set(self._extract_tables_from_query(previous_queries[-1][1]))

        return current_tables == previous_tables

    def _combine_queries(self, query1: str, query2: str) -> str:
        """Combine two queries into one."""
        # Simplified combination using UNION
        return f"{query1} UNION ALL {query2}"

    def _extract_aggregation_pattern(self, query: str) -> str:
        """Extract aggregation pattern from query."""
        # Remove specific values, keep structure
        pattern = re.sub(r"'[^']*'", "'?'", query)
        pattern = re.sub(r"\b\d+\b", "?", pattern)
        return pattern

    def _assess_query_complexity(self, query: str) -> QueryComplexity:
        """Assess query complexity level."""
        score = 0

        # Count complexity indicators
        score += query.upper().count("JOIN") * 2
        score += query.upper().count("SELECT") - 1  # Subqueries
        score += 1 if "GROUP BY" in query.upper() else 0
        score += 1 if "ORDER BY" in query.upper() else 0
        score += 1 if "HAVING" in query.upper() else 0
        score += query.upper().count("UNION") * 2

        if score >= 10:
            return QueryComplexity.VERY_COMPLEX
        elif score >= 5:
            return QueryComplexity.COMPLEX
        elif score >= 2:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE

    def _extract_schema_from_query(self, query: str) -> Dict[str, Any]:
        """Extract schema information from query."""
        # Use existing statistics as schema
        tables = self._extract_tables_from_query(query)
        schema = {"tables": {}}

        for table in tables:
            if table in self.statistics.get("tables", {}):
                schema["tables"][table] = self.statistics["tables"][table]
            else:
                # Default schema for unknown tables
                schema["tables"][table] = {
                    "row_count": 10000,
                    "indexes": [],
                    "avg_row_size": 256
                }

        return schema

    def _generate_execution_plan(self, query: str) -> Dict[str, Any]:
        """Generate a simulated execution plan."""
        # In production, this would call EXPLAIN on the database
        plan = {
            "query": query,
            "scan_type": "index" if "WHERE" in query.upper() else "sequential",
            "rows_examined": 1000,
            "possible_indexes": ["idx_example"],
            "used_index": "idx_example" if "WHERE" in query.upper() else None,
            "join_type": "hash" if "JOIN" in query.upper() else None,
            "extra": ""
        }

        if "ORDER BY" in query.upper() and "LIMIT" not in query.upper():
            plan["extra"] += "Using filesort; "

        if len(self._extract_tables_from_query(query)) > 1:
            plan["extra"] += "Using temporary; "

        return plan

    def _index_to_dict(self, idx: IndexRecommendation) -> Dict[str, Any]:
        """Convert IndexRecommendation to dictionary."""
        return {
            "table": idx.table,
            "columns": idx.columns,
            "index_type": idx.index_type,
            "estimated_benefit": idx.estimated_benefit,
            "reason": idx.reason,
            "create_statement": idx.create_statement
        }

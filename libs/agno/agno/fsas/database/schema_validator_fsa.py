"""
Schema Validator FSA (Focused Specialized Agent)

This module provides comprehensive database schema validation, migration, and evolution
management capabilities for the MLA (Multi-Layer Agent) framework. It performs schema
validation, drift detection, migration planning, and cross-database schema translation.

Features:
- Database schema validation and verification
- Schema migration planning and execution
- Schema version control integration
- Schema drift detection
- Data type validation and optimization
- Constraint validation (foreign keys, check constraints, unique)
- Schema normalization analysis
- Denormalization recommendations
- Schema backward compatibility checking
- Cross-database schema translation
- Schema documentation generation
- Schema refactoring automation
- Schema performance impact analysis

Author: Agno Database Team
Version: 1.0.0
"""

import copy
import hashlib
import json
import re
from collections import defaultdict, deque
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
    DYNAMODB = "dynamodb"
    MSSQL = "mssql"
    ORACLE = "oracle"


class NormalizationLevel(Enum):
    """Database normalization levels."""
    FIRST_NF = "1NF"
    SECOND_NF = "2NF"
    THIRD_NF = "3NF"
    BCNF = "BCNF"
    FOURTH_NF = "4NF"
    FIFTH_NF = "5NF"


class MigrationSafety(Enum):
    """Migration safety levels."""
    SAFE = "safe"
    RISKY = "risky"
    DANGEROUS = "dangerous"
    DATA_LOSS = "data_loss"


@dataclass
class SchemaIssue:
    """Represents a schema validation issue."""
    severity: str
    category: str
    table: str
    column: Optional[str]
    description: str
    recommendation: str


@dataclass
class MigrationStep:
    """Represents a single migration step."""
    operation: str
    table: str
    details: Dict[str, Any]
    safety_level: MigrationSafety
    sql: str
    rollback_sql: str


@dataclass
class SchemaDrift:
    """Represents schema drift between versions."""
    added_tables: List[str]
    removed_tables: List[str]
    modified_tables: Dict[str, Dict[str, Any]]
    severity: str


class SchemaValidatorFSA:
    """
    Schema Validator FSA (Focused Specialized Agent)

    This agent performs comprehensive database schema validation, migration planning,
    and schema evolution management across multiple database platforms.

    Attributes:
        database_type (DatabaseType): Type of database being validated
        schema_cache (Dict): Cache of validated schemas
        migration_history (List): History of applied migrations
        current_version (str): Current schema version
    """

    def __init__(self, database_type: str = "postgresql"):
        """
        Initialize the Schema Validator FSA.

        Args:
            database_type (str): Type of database (postgresql, mysql, sqlite, mongodb, dynamodb)
        """
        self.database_type = DatabaseType(database_type.lower()) if isinstance(database_type, str) else database_type
        self.schema_cache: Dict[str, Any] = {}
        self.migration_history: List[Dict[str, Any]] = []
        self.current_version: str = "0.0.0"
        self.metadata: Dict[str, Any] = {
            "schemas_validated": 0,
            "migrations_planned": 0,
            "migrations_executed": 0,
            "drift_detections": 0,
        }
        self._initialize_type_mappings()
        self._initialize_validation_rules()

    def _initialize_type_mappings(self) -> None:
        """Initialize data type mappings between databases."""
        self.type_mappings = {
            DatabaseType.POSTGRESQL: {
                "string": "VARCHAR",
                "text": "TEXT",
                "integer": "INTEGER",
                "bigint": "BIGINT",
                "float": "REAL",
                "double": "DOUBLE PRECISION",
                "decimal": "DECIMAL",
                "boolean": "BOOLEAN",
                "date": "DATE",
                "datetime": "TIMESTAMP",
                "time": "TIME",
                "json": "JSONB",
                "blob": "BYTEA"
            },
            DatabaseType.MYSQL: {
                "string": "VARCHAR",
                "text": "TEXT",
                "integer": "INT",
                "bigint": "BIGINT",
                "float": "FLOAT",
                "double": "DOUBLE",
                "decimal": "DECIMAL",
                "boolean": "TINYINT(1)",
                "date": "DATE",
                "datetime": "DATETIME",
                "time": "TIME",
                "json": "JSON",
                "blob": "BLOB"
            },
            DatabaseType.SQLITE: {
                "string": "TEXT",
                "text": "TEXT",
                "integer": "INTEGER",
                "bigint": "INTEGER",
                "float": "REAL",
                "double": "REAL",
                "decimal": "REAL",
                "boolean": "INTEGER",
                "date": "TEXT",
                "datetime": "TEXT",
                "time": "TEXT",
                "json": "TEXT",
                "blob": "BLOB"
            },
            DatabaseType.MONGODB: {
                "string": "String",
                "text": "String",
                "integer": "Int32",
                "bigint": "Int64",
                "float": "Double",
                "double": "Double",
                "decimal": "Decimal128",
                "boolean": "Boolean",
                "date": "Date",
                "datetime": "Date",
                "time": "String",
                "json": "Object",
                "blob": "BinData"
            },
        }

    def _initialize_validation_rules(self) -> None:
        """Initialize schema validation rules."""
        self.validation_rules = [
            {
                "name": "table_name_convention",
                "severity": "medium",
                "check": lambda name: re.match(r'^[a-z][a-z0-9_]*$', name),
                "message": "Table names should be lowercase with underscores"
            },
            {
                "name": "column_name_convention",
                "severity": "low",
                "check": lambda name: re.match(r'^[a-z][a-z0-9_]*$', name),
                "message": "Column names should be lowercase with underscores"
            },
            {
                "name": "primary_key_required",
                "severity": "high",
                "check": lambda table: "primary_key" in table or any(c.get("primary_key") for c in table.get("columns", {}).values()),
                "message": "Every table should have a primary key"
            },
            {
                "name": "timestamp_columns",
                "severity": "low",
                "check": lambda table: any(c in table.get("columns", {}) for c in ["created_at", "updated_at"]),
                "message": "Consider adding created_at/updated_at columns"
            },
        ]

    def execute(self, schema: Dict[str, Any], operation: str = "validate") -> Dict[str, Any]:
        """
        Execute schema validation or migration operation.

        Args:
            schema (Dict[str, Any]): Schema definition to validate
            operation (str): Operation to perform (validate, migrate, analyze)

        Returns:
            Dict[str, Any]: Operation results
        """
        if not schema:
            raise ValueError("Schema cannot be empty")

        try:
            if operation == "validate":
                issues = self.validate_schema(schema)
                normalization = self.analyze_normalization(schema)
                constraints = self.validate_constraints(schema)

                result = {
                    "success": True,
                    "operation": operation,
                    "issues": [self._issue_to_dict(i) for i in issues],
                    "normalization_level": normalization.get("level"),
                    "normalization_recommendations": normalization.get("recommendations", []),
                    "constraint_issues": constraints,
                    "schema_hash": self._hash_schema(schema),
                    "metadata": self.metadata
                }

            elif operation == "analyze":
                issues = self.validate_schema(schema)
                normalization = self.analyze_normalization(schema)
                performance_impact = self.analyze_performance_impact(schema)
                circular_deps = self.detect_circular_dependencies(schema)

                result = {
                    "success": True,
                    "operation": operation,
                    "validation_issues": [self._issue_to_dict(i) for i in issues],
                    "normalization_analysis": normalization,
                    "performance_impact": performance_impact,
                    "circular_dependencies": circular_deps,
                    "foreign_key_issues": self.validate_foreign_keys(schema),
                    "metadata": self.metadata
                }

            elif operation == "document":
                documentation = self.generate_schema_documentation(schema)

                result = {
                    "success": True,
                    "operation": operation,
                    "documentation": documentation,
                    "metadata": self.metadata
                }

            else:
                raise ValueError(f"Unknown operation: {operation}")

            self.metadata["schemas_validated"] += 1
            return result

        except Exception as e:
            return self.error_handling(e)

    def validate_schema(self, schema_def: Dict[str, Any]) -> List[SchemaIssue]:
        """
        Validate database schema definition.

        Args:
            schema_def (Dict[str, Any]): Schema definition

        Returns:
            List[SchemaIssue]: List of validation issues
        """
        issues = []

        if "tables" not in schema_def:
            issues.append(SchemaIssue(
                severity="critical",
                category="structure",
                table="N/A",
                column=None,
                description="Schema definition missing 'tables' key",
                recommendation="Add 'tables' dictionary to schema definition"
            ))
            return issues

        tables = schema_def["tables"]

        # Validate each table
        for table_name, table_def in tables.items():
            # Check table name convention
            if not re.match(r'^[a-z][a-z0-9_]*$', table_name):
                issues.append(SchemaIssue(
                    severity="medium",
                    category="naming",
                    table=table_name,
                    column=None,
                    description="Table name doesn't follow naming convention",
                    recommendation="Use lowercase with underscores (snake_case)"
                ))

            # Check for columns
            if "columns" not in table_def or not table_def["columns"]:
                issues.append(SchemaIssue(
                    severity="critical",
                    category="structure",
                    table=table_name,
                    column=None,
                    description="Table has no columns defined",
                    recommendation="Add at least one column to the table"
                ))
                continue

            # Validate columns
            has_primary_key = False
            columns = table_def["columns"]

            for col_name, col_def in columns.items():
                # Check column name convention
                if not re.match(r'^[a-z][a-z0-9_]*$', col_name):
                    issues.append(SchemaIssue(
                        severity="low",
                        category="naming",
                        table=table_name,
                        column=col_name,
                        description="Column name doesn't follow naming convention",
                        recommendation="Use lowercase with underscores (snake_case)"
                    ))

                # Check for data type
                if "type" not in col_def:
                    issues.append(SchemaIssue(
                        severity="critical",
                        category="structure",
                        table=table_name,
                        column=col_name,
                        description="Column missing data type",
                        recommendation="Specify column data type"
                    ))

                # Check if primary key exists
                if col_def.get("primary_key"):
                    has_primary_key = True

                # Validate data type
                if "type" in col_def:
                    type_issues = self._validate_data_type(table_name, col_name, col_def["type"])
                    issues.extend(type_issues)

                # Check for nullable on foreign keys
                if col_def.get("foreign_key") and col_def.get("nullable", True):
                    issues.append(SchemaIssue(
                        severity="medium",
                        category="constraints",
                        table=table_name,
                        column=col_name,
                        description="Foreign key column is nullable",
                        recommendation="Consider making foreign key NOT NULL if relationship is mandatory"
                    ))

            # Check for primary key
            if not has_primary_key and "primary_key" not in table_def:
                issues.append(SchemaIssue(
                    severity="high",
                    category="constraints",
                    table=table_name,
                    column=None,
                    description="Table has no primary key",
                    recommendation="Add a primary key column (typically 'id')"
                ))

            # Check for timestamp columns
            has_created_at = "created_at" in columns
            has_updated_at = "updated_at" in columns

            if not has_created_at and not has_updated_at:
                issues.append(SchemaIssue(
                    severity="low",
                    category="best_practices",
                    table=table_name,
                    column=None,
                    description="Table missing timestamp columns",
                    recommendation="Consider adding created_at and updated_at columns"
                ))

        return issues

    def detect_schema_drift(self, current: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Detect drift between current and expected schema.

        Args:
            current (Dict[str, Any]): Current schema
            expected (Dict[str, Any]): Expected schema

        Returns:
            Dict[str, List[str]]: Categorized drift items
        """
        drift = {
            "added_tables": [],
            "removed_tables": [],
            "modified_tables": [],
            "added_columns": [],
            "removed_columns": [],
            "modified_columns": [],
            "added_indexes": [],
            "removed_indexes": [],
            "constraint_changes": []
        }

        current_tables = set(current.get("tables", {}).keys())
        expected_tables = set(expected.get("tables", {}).keys())

        # Detect added/removed tables
        drift["added_tables"] = list(current_tables - expected_tables)
        drift["removed_tables"] = list(expected_tables - current_tables)

        # Check modified tables
        common_tables = current_tables & expected_tables

        for table in common_tables:
            current_table = current["tables"][table]
            expected_table = expected["tables"][table]

            current_cols = set(current_table.get("columns", {}).keys())
            expected_cols = set(expected_table.get("columns", {}).keys())

            # Detect column changes
            added_cols = current_cols - expected_cols
            removed_cols = expected_cols - current_cols

            if added_cols:
                drift["added_columns"].extend([f"{table}.{col}" for col in added_cols])

            if removed_cols:
                drift["removed_columns"].extend([f"{table}.{col}" for col in removed_cols])

            # Check modified columns
            common_cols = current_cols & expected_cols
            for col in common_cols:
                current_col = current_table["columns"][col]
                expected_col = expected_table["columns"][col]

                if current_col.get("type") != expected_col.get("type"):
                    drift["modified_columns"].append(
                        f"{table}.{col}: {expected_col.get('type')} -> {current_col.get('type')}"
                    )

                if current_col.get("nullable") != expected_col.get("nullable"):
                    drift["constraint_changes"].append(
                        f"{table}.{col}: nullable changed"
                    )

            # Check index changes
            current_indexes = set(current_table.get("indexes", []))
            expected_indexes = set(expected_table.get("indexes", []))

            added_idx = current_indexes - expected_indexes
            removed_idx = expected_indexes - current_indexes

            if added_idx:
                drift["added_indexes"].extend([f"{table}.{idx}" for idx in added_idx])

            if removed_idx:
                drift["removed_indexes"].extend([f"{table}.{idx}" for idx in removed_idx])

        self.metadata["drift_detections"] += 1
        return drift

    def plan_migration(self, from_schema: Dict[str, Any], to_schema: Dict[str, Any]) -> List[MigrationStep]:
        """
        Plan migration steps from one schema to another.

        Args:
            from_schema (Dict[str, Any]): Source schema
            to_schema (Dict[str, Any]): Target schema

        Returns:
            List[MigrationStep]: Ordered migration steps
        """
        migration_steps = []

        from_tables = from_schema.get("tables", {})
        to_tables = to_schema.get("tables", {})

        from_table_names = set(from_tables.keys())
        to_table_names = set(to_tables.keys())

        # Step 1: Drop foreign key constraints (to avoid dependency issues)
        for table_name in from_table_names:
            table = from_tables[table_name]
            for col_name, col_def in table.get("columns", {}).items():
                if col_def.get("foreign_key"):
                    migration_steps.append(MigrationStep(
                        operation="drop_foreign_key",
                        table=table_name,
                        details={"column": col_name, "fk": col_def["foreign_key"]},
                        safety_level=MigrationSafety.SAFE,
                        sql=f"ALTER TABLE {table_name} DROP CONSTRAINT fk_{table_name}_{col_name};",
                        rollback_sql=f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{col_name} FOREIGN KEY ({col_name}) REFERENCES {col_def['foreign_key']};"
                    ))

        # Step 2: Drop removed tables
        removed_tables = from_table_names - to_table_names
        for table_name in removed_tables:
            migration_steps.append(MigrationStep(
                operation="drop_table",
                table=table_name,
                details={},
                safety_level=MigrationSafety.DATA_LOSS,
                sql=f"DROP TABLE {table_name};",
                rollback_sql=f"-- Cannot rollback DROP TABLE {table_name}"
            ))

        # Step 3: Create new tables
        added_tables = to_table_names - from_table_names
        for table_name in added_tables:
            table_def = to_tables[table_name]
            create_sql = self._generate_create_table_sql(table_name, table_def)
            migration_steps.append(MigrationStep(
                operation="create_table",
                table=table_name,
                details=table_def,
                safety_level=MigrationSafety.SAFE,
                sql=create_sql,
                rollback_sql=f"DROP TABLE {table_name};"
            ))

        # Step 4: Modify existing tables
        common_tables = from_table_names & to_table_names
        for table_name in common_tables:
            from_table = from_tables[table_name]
            to_table = to_tables[table_name]

            from_cols = from_table.get("columns", {})
            to_cols = to_table.get("columns", {})

            from_col_names = set(from_cols.keys())
            to_col_names = set(to_cols.keys())

            # Drop removed columns
            removed_cols = from_col_names - to_col_names
            for col_name in removed_cols:
                migration_steps.append(MigrationStep(
                    operation="drop_column",
                    table=table_name,
                    details={"column": col_name},
                    safety_level=MigrationSafety.DATA_LOSS,
                    sql=f"ALTER TABLE {table_name} DROP COLUMN {col_name};",
                    rollback_sql=f"-- Cannot rollback DROP COLUMN {table_name}.{col_name}"
                ))

            # Add new columns
            added_cols = to_col_names - from_col_names
            for col_name in added_cols:
                col_def = to_cols[col_name]
                col_sql = self._generate_column_definition(col_name, col_def)
                safety = MigrationSafety.SAFE if col_def.get("nullable", True) else MigrationSafety.RISKY

                migration_steps.append(MigrationStep(
                    operation="add_column",
                    table=table_name,
                    details={"column": col_name, "definition": col_def},
                    safety_level=safety,
                    sql=f"ALTER TABLE {table_name} ADD COLUMN {col_sql};",
                    rollback_sql=f"ALTER TABLE {table_name} DROP COLUMN {col_name};"
                ))

            # Modify existing columns
            common_cols = from_col_names & to_col_names
            for col_name in common_cols:
                from_col = from_cols[col_name]
                to_col = to_cols[col_name]

                # Check type change
                if from_col.get("type") != to_col.get("type"):
                    migration_steps.append(MigrationStep(
                        operation="modify_column_type",
                        table=table_name,
                        details={
                            "column": col_name,
                            "from_type": from_col.get("type"),
                            "to_type": to_col.get("type")
                        },
                        safety_level=MigrationSafety.DANGEROUS,
                        sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {to_col.get('type')};",
                        rollback_sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {from_col.get('type')};"
                    ))

                # Check nullable change
                if from_col.get("nullable", True) != to_col.get("nullable", True):
                    if to_col.get("nullable", True):
                        migration_steps.append(MigrationStep(
                            operation="set_nullable",
                            table=table_name,
                            details={"column": col_name},
                            safety_level=MigrationSafety.SAFE,
                            sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL;",
                            rollback_sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL;"
                        ))
                    else:
                        migration_steps.append(MigrationStep(
                            operation="set_not_nullable",
                            table=table_name,
                            details={"column": col_name},
                            safety_level=MigrationSafety.RISKY,
                            sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL;",
                            rollback_sql=f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL;"
                        ))

        # Step 5: Add new foreign keys
        for table_name in to_table_names:
            if table_name not in to_tables:
                continue

            table = to_tables[table_name]
            for col_name, col_def in table.get("columns", {}).items():
                if col_def.get("foreign_key"):
                    migration_steps.append(MigrationStep(
                        operation="add_foreign_key",
                        table=table_name,
                        details={"column": col_name, "references": col_def["foreign_key"]},
                        safety_level=MigrationSafety.RISKY,
                        sql=f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{col_name} FOREIGN KEY ({col_name}) REFERENCES {col_def['foreign_key']};",
                        rollback_sql=f"ALTER TABLE {table_name} DROP CONSTRAINT fk_{table_name}_{col_name};"
                    ))

        self.metadata["migrations_planned"] += 1
        return migration_steps

    def execute_migration(self, migration_plan: List[MigrationStep]) -> Dict[str, Any]:
        """
        Execute migration plan (simulation mode).

        Args:
            migration_plan (List[MigrationStep]): Migration steps to execute

        Returns:
            Dict[str, Any]: Execution results
        """
        results = {
            "success": True,
            "executed_steps": [],
            "failed_steps": [],
            "warnings": []
        }

        for step in migration_plan:
            # Safety check
            if step.safety_level == MigrationSafety.DATA_LOSS:
                results["warnings"].append(
                    f"WARNING: {step.operation} on {step.table} may cause data loss"
                )

            # Simulate execution
            try:
                # In production, this would execute actual SQL
                results["executed_steps"].append({
                    "operation": step.operation,
                    "table": step.table,
                    "sql": step.sql,
                    "safety": step.safety_level.value
                })
            except Exception as e:
                results["failed_steps"].append({
                    "operation": step.operation,
                    "table": step.table,
                    "error": str(e)
                })
                results["success"] = False

        self.metadata["migrations_executed"] += 1
        return results

    def validate_data_types(self, table: str, columns: Dict[str, str]) -> List[str]:
        """
        Validate data types for table columns.

        Args:
            table (str): Table name
            columns (Dict[str, str]): Column name to type mapping

        Returns:
            List[str]: List of validation issues
        """
        issues = []

        for col_name, col_type in columns.items():
            # Check if type is valid for current database
            valid_types = self.type_mappings.get(self.database_type, {}).values()

            if col_type.upper() not in [t.upper() for t in valid_types]:
                issues.append(
                    f"Column {table}.{col_name} has invalid type '{col_type}' for {self.database_type.value}"
                )

            # Check for deprecated types
            deprecated_types = {
                "TINYTEXT": "Use VARCHAR instead",
                "MEDIUMTEXT": "Use TEXT instead",
                "LONG": "Use BIGINT instead",
            }

            if col_type.upper() in deprecated_types:
                issues.append(
                    f"Column {table}.{col_name} uses deprecated type '{col_type}': {deprecated_types[col_type.upper()]}"
                )

        return issues

    def validate_constraints(self, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Validate schema constraints.

        Args:
            schema (Dict[str, Any]): Schema definition

        Returns:
            List[Dict[str, str]]: List of constraint issues
        """
        issues = []
        tables = schema.get("tables", {})

        for table_name, table_def in tables.items():
            columns = table_def.get("columns", {})

            # Check unique constraints
            unique_columns = [col for col, defn in columns.items() if defn.get("unique")]
            if len(unique_columns) > 5:
                issues.append({
                    "table": table_name,
                    "type": "unique_constraints",
                    "severity": "medium",
                    "message": f"Table has {len(unique_columns)} unique constraints, consider composite index"
                })

            # Check check constraints
            for col_name, col_def in columns.items():
                if "check" in col_def:
                    # Validate check constraint syntax
                    check = col_def["check"]
                    if not isinstance(check, str):
                        issues.append({
                            "table": table_name,
                            "column": col_name,
                            "type": "check_constraint",
                            "severity": "high",
                            "message": "Check constraint must be a string"
                        })

        return issues

    def analyze_normalization(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze schema normalization level.

        Args:
            schema (Dict[str, Any]): Schema definition

        Returns:
            Dict[str, Any]: Normalization analysis
        """
        analysis = {
            "level": NormalizationLevel.FIRST_NF.value,
            "violations": [],
            "recommendations": []
        }

        tables = schema.get("tables", {})

        # Check 1NF: Atomic values
        for table_name, table_def in tables.items():
            columns = table_def.get("columns", {})

            for col_name, col_def in columns.items():
                col_type = col_def.get("type", "").upper()

                # Check for array/list types (violates 1NF)
                if "ARRAY" in col_type or "JSON" in col_type:
                    analysis["violations"].append(
                        f"{table_name}.{col_name} contains non-atomic values ({col_type})"
                    )

        # Check 2NF: No partial dependencies
        for table_name, table_def in tables.items():
            # Check if table has composite primary key
            pk_columns = [col for col, defn in table_def.get("columns", {}).items()
                         if defn.get("primary_key")]

            if len(pk_columns) > 1:
                # Check for columns dependent on part of the key
                analysis["recommendations"].append(
                    f"Table {table_name} has composite primary key - verify no partial dependencies exist"
                )

        # Check 3NF: No transitive dependencies
        for table_name, table_def in tables.items():
            columns = table_def.get("columns", {})

            # Look for potential transitive dependencies
            # (simplified check - looks for non-key columns that could be in separate table)
            non_key_cols = [col for col, defn in columns.items()
                           if not defn.get("primary_key") and not defn.get("foreign_key")]

            if len(non_key_cols) > 10:
                analysis["recommendations"].append(
                    f"Table {table_name} has {len(non_key_cols)} non-key columns - consider normalization"
                )

        # Determine achieved normalization level
        if not analysis["violations"]:
            analysis["level"] = NormalizationLevel.THIRD_NF.value
            if not analysis["recommendations"]:
                analysis["level"] = NormalizationLevel.BCNF.value

        return analysis

    def recommend_denormalization(self, schema: Dict[str, Any], access_patterns: Dict[str, Any]) -> List[str]:
        """
        Recommend denormalization strategies based on access patterns.

        Args:
            schema (Dict[str, Any]): Current schema
            access_patterns (Dict[str, Any]): Query access patterns

        Returns:
            List[str]: Denormalization recommendations
        """
        recommendations = []

        # Analyze join frequency
        frequent_joins = access_patterns.get("frequent_joins", [])

        for join in frequent_joins:
            if join.get("frequency", 0) > 100:  # Joined frequently
                recommendations.append(
                    f"Consider denormalizing join between {join['table1']} and {join['table2']} "
                    f"(joined {join['frequency']} times) by adding {join['table2']} columns to {join['table1']}"
                )

        # Check for computed columns that are frequently queried
        aggregations = access_patterns.get("aggregations", [])

        for agg in aggregations:
            if agg.get("frequency", 0) > 50:
                recommendations.append(
                    f"Consider adding computed column for {agg['operation']} "
                    f"on {agg['table']}.{agg['column']} (computed {agg['frequency']} times)"
                )

        # Check for frequently accessed related data
        if not recommendations:
            recommendations.append("Schema appears well-normalized for current access patterns")

        return recommendations

    def check_backward_compatibility(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
        """
        Check backward compatibility between schema versions.

        Args:
            old (Dict[str, Any]): Old schema version
            new (Dict[str, Any]): New schema version

        Returns:
            List[str]: List of breaking changes
        """
        breaking_changes = []

        old_tables = old.get("tables", {})
        new_tables = new.get("tables", {})

        # Check for removed tables
        removed_tables = set(old_tables.keys()) - set(new_tables.keys())
        for table in removed_tables:
            breaking_changes.append(f"BREAKING: Table '{table}' was removed")

        # Check for removed columns
        common_tables = set(old_tables.keys()) & set(new_tables.keys())

        for table in common_tables:
            old_cols = set(old_tables[table].get("columns", {}).keys())
            new_cols = set(new_tables[table].get("columns", {}).keys())

            removed_cols = old_cols - new_cols
            for col in removed_cols:
                breaking_changes.append(f"BREAKING: Column '{table}.{col}' was removed")

            # Check for type changes
            common_cols = old_cols & new_cols
            for col in common_cols:
                old_type = old_tables[table]["columns"][col].get("type")
                new_type = new_tables[table]["columns"][col].get("type")

                if old_type != new_type:
                    breaking_changes.append(
                        f"BREAKING: Column '{table}.{col}' type changed from {old_type} to {new_type}"
                    )

                # Check for new NOT NULL constraints
                old_nullable = old_tables[table]["columns"][col].get("nullable", True)
                new_nullable = new_tables[table]["columns"][col].get("nullable", True)

                if old_nullable and not new_nullable:
                    breaking_changes.append(
                        f"BREAKING: Column '{table}.{col}' changed to NOT NULL"
                    )

        return breaking_changes

    def translate_schema(self, schema: Dict[str, Any], target_db: str) -> Dict[str, Any]:
        """
        Translate schema to target database format.

        Args:
            schema (Dict[str, Any]): Source schema
            target_db (str): Target database type

        Returns:
            Dict[str, Any]: Translated schema
        """
        target_type = DatabaseType(target_db.lower())
        translated = copy.deepcopy(schema)

        if target_type not in self.type_mappings:
            raise ValueError(f"Unsupported target database: {target_db}")

        target_types = self.type_mappings[target_type]
        source_types = self.type_mappings[self.database_type]

        # Create reverse mapping
        reverse_mapping = {v: k for k, v in source_types.items()}

        # Translate data types
        for table_name, table_def in translated.get("tables", {}).items():
            for col_name, col_def in table_def.get("columns", {}).items():
                current_type = col_def.get("type", "").upper()

                # Find generic type
                generic_type = None
                for gen, specific in source_types.items():
                    if specific.upper() == current_type:
                        generic_type = gen
                        break

                # Translate to target type
                if generic_type and generic_type in target_types:
                    col_def["type"] = target_types[generic_type]

        return translated

    def generate_schema_documentation(self, schema: Dict[str, Any]) -> str:
        """
        Generate comprehensive schema documentation.

        Args:
            schema (Dict[str, Any]): Schema definition

        Returns:
            str: Formatted documentation
        """
        doc_lines = []
        doc_lines.append("=" * 80)
        doc_lines.append("DATABASE SCHEMA DOCUMENTATION")
        doc_lines.append("=" * 80)
        doc_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc_lines.append(f"Database Type: {self.database_type.value}")
        doc_lines.append(f"Schema Version: {self.current_version}")
        doc_lines.append("")

        tables = schema.get("tables", {})

        # Overview
        doc_lines.append("SCHEMA OVERVIEW")
        doc_lines.append("-" * 80)
        doc_lines.append(f"Total Tables: {len(tables)}")

        total_columns = sum(len(t.get("columns", {})) for t in tables.values())
        doc_lines.append(f"Total Columns: {total_columns}")
        doc_lines.append("")

        # Table details
        doc_lines.append("TABLE DETAILS")
        doc_lines.append("-" * 80)

        for table_name in sorted(tables.keys()):
            table_def = tables[table_name]
            columns = table_def.get("columns", {})

            doc_lines.append(f"\nTable: {table_name}")
            doc_lines.append(f"Description: {table_def.get('description', 'N/A')}")
            doc_lines.append(f"Columns: {len(columns)}")
            doc_lines.append("")

            # Column details
            doc_lines.append("  Columns:")
            for col_name in sorted(columns.keys()):
                col_def = columns[col_name]
                col_type = col_def.get("type", "UNKNOWN")
                nullable = "NULL" if col_def.get("nullable", True) else "NOT NULL"
                pk = " [PK]" if col_def.get("primary_key") else ""
                fk = f" [FK -> {col_def['foreign_key']}]" if col_def.get("foreign_key") else ""
                unique = " [UNIQUE]" if col_def.get("unique") else ""

                doc_lines.append(
                    f"    - {col_name}: {col_type} {nullable}{pk}{fk}{unique}"
                )

            # Indexes
            if "indexes" in table_def and table_def["indexes"]:
                doc_lines.append("  Indexes:")
                for idx in table_def["indexes"]:
                    doc_lines.append(f"    - {idx}")

            doc_lines.append("")

        # Relationships
        doc_lines.append("RELATIONSHIPS")
        doc_lines.append("-" * 80)

        for table_name, table_def in tables.items():
            for col_name, col_def in table_def.get("columns", {}).items():
                if col_def.get("foreign_key"):
                    doc_lines.append(
                        f"{table_name}.{col_name} -> {col_def['foreign_key']}"
                    )

        doc_lines.append("")
        doc_lines.append("=" * 80)
        doc_lines.append("END OF DOCUMENTATION")
        doc_lines.append("=" * 80)

        return "\n".join(doc_lines)

    def refactor_schema(self, schema: Dict[str, Any], refactoring_type: str) -> Tuple[Dict[str, Any], List[str]]:
        """
        Refactor schema based on refactoring type.

        Args:
            schema (Dict[str, Any]): Current schema
            refactoring_type (str): Type of refactoring (normalize, denormalize, rename)

        Returns:
            Tuple[Dict[str, Any], List[str]]: Refactored schema and change log
        """
        refactored = copy.deepcopy(schema)
        changes = []

        if refactoring_type == "normalize":
            # Add timestamp columns to tables missing them
            for table_name, table_def in refactored.get("tables", {}).items():
                columns = table_def.get("columns", {})

                if "created_at" not in columns:
                    columns["created_at"] = {
                        "type": "TIMESTAMP",
                        "nullable": False,
                        "default": "CURRENT_TIMESTAMP"
                    }
                    changes.append(f"Added created_at to {table_name}")

                if "updated_at" not in columns:
                    columns["updated_at"] = {
                        "type": "TIMESTAMP",
                        "nullable": False,
                        "default": "CURRENT_TIMESTAMP"
                    }
                    changes.append(f"Added updated_at to {table_name}")

        elif refactoring_type == "add_indexes":
            # Add indexes to foreign key columns
            for table_name, table_def in refactored.get("tables", {}).items():
                if "indexes" not in table_def:
                    table_def["indexes"] = []

                for col_name, col_def in table_def.get("columns", {}).items():
                    if col_def.get("foreign_key"):
                        idx_name = f"idx_{table_name}_{col_name}"
                        if idx_name not in table_def["indexes"]:
                            table_def["indexes"].append(idx_name)
                            changes.append(f"Added index {idx_name}")

        return refactored, changes

    def analyze_performance_impact(self, schema_changes: Union[List[str], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze performance impact of schema changes.

        Args:
            schema_changes (Union[List[str], Dict[str, Any]]): Schema changes or schema definition

        Returns:
            Dict[str, Any]: Performance impact analysis
        """
        impact = {
            "read_performance": "neutral",
            "write_performance": "neutral",
            "storage_impact": "minimal",
            "index_impact": "none",
            "warnings": [],
            "recommendations": []
        }

        # Handle both schema dict and change list
        if isinstance(schema_changes, dict):
            # Analyze full schema
            tables = schema_changes.get("tables", {})

            total_indexes = sum(len(t.get("indexes", [])) for t in tables.values())
            total_columns = sum(len(t.get("columns", {})) for t in tables.values())

            if total_indexes > total_columns * 0.5:
                impact["warnings"].append("High index-to-column ratio may impact write performance")
                impact["write_performance"] = "slower"

            if total_indexes > total_columns * 0.3:
                impact["read_performance"] = "faster"

        return impact

    def validate_foreign_keys(self, schema: Dict[str, Any]) -> List[str]:
        """
        Validate foreign key constraints.

        Args:
            schema (Dict[str, Any]): Schema definition

        Returns:
            List[str]: List of foreign key issues
        """
        issues = []
        tables = schema.get("tables", {})

        for table_name, table_def in tables.items():
            for col_name, col_def in table_def.get("columns", {}).items():
                if col_def.get("foreign_key"):
                    fk = col_def["foreign_key"]

                    # Parse foreign key reference
                    if "." in fk:
                        ref_table, ref_col = fk.split(".", 1)
                    else:
                        ref_table = fk
                        ref_col = "id"

                    # Check if referenced table exists
                    if ref_table not in tables:
                        issues.append(
                            f"Foreign key {table_name}.{col_name} references non-existent table '{ref_table}'"
                        )
                        continue

                    # Check if referenced column exists
                    ref_columns = tables[ref_table].get("columns", {})
                    if ref_col not in ref_columns:
                        issues.append(
                            f"Foreign key {table_name}.{col_name} references non-existent column '{ref_table}.{ref_col}'"
                        )

        return issues

    def detect_circular_dependencies(self, schema: Dict[str, Any]) -> List[List[str]]:
        """
        Detect circular foreign key dependencies.

        Args:
            schema (Dict[str, Any]): Schema definition

        Returns:
            List[List[str]]: List of circular dependency chains
        """
        # Build dependency graph
        graph = defaultdict(list)
        tables = schema.get("tables", {})

        for table_name, table_def in tables.items():
            for col_name, col_def in table_def.get("columns", {}).items():
                if col_def.get("foreign_key"):
                    fk = col_def["foreign_key"]
                    ref_table = fk.split(".")[0] if "." in fk else fk

                    if ref_table in tables:
                        graph[table_name].append(ref_table)

        # Detect cycles using DFS
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path[:]):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            rec_stack.remove(node)
            return False

        for table in tables.keys():
            if table not in visited:
                dfs(table, [])

        return cycles

    def optimize_data_types(self, table: str) -> Dict[str, str]:
        """
        Recommend optimized data types for table columns.

        Args:
            table (str): Table name

        Returns:
            Dict[str, str]: Column to optimized type mapping
        """
        optimizations = {}

        # Common optimization patterns
        patterns = {
            "id": "BIGINT",  # Use BIGINT for IDs to avoid overflow
            "email": "VARCHAR(255)",
            "name": "VARCHAR(100)",
            "description": "TEXT",
            "price": "DECIMAL(10,2)",
            "quantity": "INTEGER",
            "is_active": "BOOLEAN",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        for col_name, optimized_type in patterns.items():
            optimizations[col_name] = optimized_type

        return optimizations

    def generate_migration_script(self, changes: List[Dict[str, Any]]) -> str:
        """
        Generate SQL migration script from changes.

        Args:
            changes (List[Dict[str, Any]]): List of schema changes

        Returns:
            str: SQL migration script
        """
        script_lines = []
        script_lines.append("-- Migration Script")
        script_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        script_lines.append(f"-- Database: {self.database_type.value}")
        script_lines.append("")

        for change in changes:
            operation = change.get("operation")

            if operation == "create_table":
                script_lines.append(f"-- Create table {change['table']}")
                script_lines.append(change.get("sql", ""))
                script_lines.append("")

            elif operation == "add_column":
                script_lines.append(f"-- Add column to {change['table']}")
                script_lines.append(change.get("sql", ""))
                script_lines.append("")

            elif operation == "drop_column":
                script_lines.append(f"-- Drop column from {change['table']}")
                script_lines.append(change.get("sql", ""))
                script_lines.append("")

        return "\n".join(script_lines)

    def rollback_migration(self, version: str) -> Dict[str, Any]:
        """
        Rollback migration to specific version.

        Args:
            version (str): Target version to rollback to

        Returns:
            Dict[str, Any]: Rollback results
        """
        result = {
            "success": True,
            "target_version": version,
            "current_version": self.current_version,
            "rollback_steps": [],
            "message": f"Rolled back to version {version}"
        }

        # In production, this would execute actual rollback
        # For now, simulate
        self.current_version = version

        return result

    def validate(self) -> bool:
        """
        Validate the FSA configuration and state.

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(self.database_type, DatabaseType):
            return False
        if not isinstance(self.type_mappings, dict):
            return False
        return True

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle errors during schema operations.

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
                "schemas_validated": self.metadata.get("schemas_validated", 0),
                "migrations_planned": self.metadata.get("migrations_planned", 0)
            }
        }

        print(f"Schema Validator FSA Error: {error_info}", file=sys.stderr)

        return error_info

    # Helper methods

    def _hash_schema(self, schema: Dict[str, Any]) -> str:
        """Generate hash for schema caching."""
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()

    def _issue_to_dict(self, issue: SchemaIssue) -> Dict[str, Any]:
        """Convert SchemaIssue to dictionary."""
        return {
            "severity": issue.severity,
            "category": issue.category,
            "table": issue.table,
            "column": issue.column,
            "description": issue.description,
            "recommendation": issue.recommendation
        }

    def _validate_data_type(self, table: str, column: str, data_type: str) -> List[SchemaIssue]:
        """Validate a single data type."""
        issues = []

        # Check for deprecated types
        deprecated = {
            "TINYTEXT": "VARCHAR(255)",
            "MEDIUMTEXT": "TEXT",
            "LONG": "BIGINT"
        }

        if data_type.upper() in deprecated:
            issues.append(SchemaIssue(
                severity="medium",
                category="data_types",
                table=table,
                column=column,
                description=f"Deprecated type '{data_type}' used",
                recommendation=f"Use '{deprecated[data_type.upper()]}' instead"
            ))

        return issues

    def _generate_create_table_sql(self, table_name: str, table_def: Dict[str, Any]) -> str:
        """Generate CREATE TABLE SQL statement."""
        lines = [f"CREATE TABLE {table_name} ("]

        columns = table_def.get("columns", {})
        column_defs = []

        for col_name, col_def in columns.items():
            col_sql = self._generate_column_definition(col_name, col_def)
            column_defs.append(f"  {col_sql}")

        # Add primary key
        pk_cols = [col for col, defn in columns.items() if defn.get("primary_key")]
        if pk_cols:
            column_defs.append(f"  PRIMARY KEY ({', '.join(pk_cols)})")

        lines.append(",\n".join(column_defs))
        lines.append(");")

        return "\n".join(lines)

    def _generate_column_definition(self, col_name: str, col_def: Dict[str, Any]) -> str:
        """Generate column definition SQL."""
        parts = [col_name, col_def.get("type", "TEXT")]

        if not col_def.get("nullable", True):
            parts.append("NOT NULL")

        if "default" in col_def:
            parts.append(f"DEFAULT {col_def['default']}")

        if col_def.get("unique"):
            parts.append("UNIQUE")

        return " ".join(parts)

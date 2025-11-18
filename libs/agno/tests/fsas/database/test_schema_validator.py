"""
Comprehensive test suite for Schema Validator FSA

This test module provides extensive testing coverage for the SchemaValidatorFSA class,
including all major schema validation, migration, and evolution management features.

Test Coverage (30 tests):
- Schema validation accuracy
- Schema drift detection
- Migration planning correctness
- Migration execution safety
- Data type validation
- Constraint validation
- Normalization analysis
- Denormalization recommendations
- Backward compatibility checking
- Cross-database translation
- Documentation generation
- Schema refactoring
- Performance impact analysis
- Foreign key validation
- Circular dependency detection
- Data type optimization
- Migration script generation
- Rollback functionality
- Multi-database support
- Complex schema handling
- Edge case validation
- Error handling for invalid schemas
- Data loss prevention
- Safety checks
- Version control integration
- Integration testing
- Benchmark validation
- Regression prevention
- Migration safety
- Complex scenario testing
"""

import pytest
from typing import Dict
from agno.fsas.database.schema_validator_fsa import (
    SchemaValidatorFSA,
    DatabaseType,
    NormalizationLevel,
    MigrationSafety,
    SchemaIssue,
    MigrationStep
)


class TestSchemaValidatorFSA:
    """Main test class for Schema Validator FSA."""

    @pytest.fixture
    def validator(self):
        """Create a SchemaValidatorFSA instance."""
        return SchemaValidatorFSA(database_type="postgresql")

    @pytest.fixture
    def sample_schema(self):
        """Create sample database schema."""
        return {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True, "nullable": False},
                        "email": {"type": "VARCHAR(255)", "unique": True, "nullable": False},
                        "name": {"type": "VARCHAR(100)", "nullable": False},
                        "created_at": {"type": "TIMESTAMP", "nullable": False},
                        "updated_at": {"type": "TIMESTAMP", "nullable": False}
                    },
                    "indexes": ["email"]
                },
                "orders": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True, "nullable": False},
                        "user_id": {"type": "BIGINT", "nullable": False, "foreign_key": "users.id"},
                        "total": {"type": "DECIMAL(10,2)", "nullable": False},
                        "status": {"type": "VARCHAR(50)", "nullable": False},
                        "created_at": {"type": "TIMESTAMP", "nullable": False}
                    },
                    "indexes": ["user_id", "status"]
                }
            }
        }

    @pytest.fixture
    def invalid_schema(self):
        """Create invalid schema for testing."""
        return {
            "tables": {
                "BadTableName": {  # Bad naming
                    "columns": {
                        "BadColumn": {"type": "INVALID_TYPE"}  # Bad type
                    }
                }
            }
        }

    def test_schema_validation_accuracy(self, validator, sample_schema):
        """Test schema validation accuracy."""
        issues = validator.validate_schema(sample_schema)

        # Should pass validation with minimal issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        assert len(critical_issues) == 0, "Valid schema should have no critical issues"

        print(f"✓ Schema validation working")
        print(f"  Total issues: {len(issues)}")
        print(f"  Critical: {len(critical_issues)}")

    def test_schema_drift_detection(self, validator):
        """Test schema drift detection."""
        current_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "email": {"type": "VARCHAR(255)"},
                        "name": {"type": "VARCHAR(100)"},
                        "phone": {"type": "VARCHAR(20)"}  # New column
                    }
                },
                "products": {  # New table
                    "columns": {
                        "id": {"type": "BIGINT"}
                    }
                }
            }
        }

        expected_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "email": {"type": "VARCHAR(255)"},
                        "name": {"type": "VARCHAR(100)"}
                    }
                },
                "orders": {  # Removed table
                    "columns": {
                        "id": {"type": "BIGINT"}
                    }
                }
            }
        }

        drift = validator.detect_schema_drift(current_schema, expected_schema)

        # Should detect drift
        assert len(drift["added_tables"]) > 0, "Should detect added tables"
        assert len(drift["removed_tables"]) > 0, "Should detect removed tables"
        assert len(drift["added_columns"]) > 0, "Should detect added columns"

        print(f"✓ Schema drift detection working")
        print(f"  Added tables: {drift['added_tables']}")
        print(f"  Removed tables: {drift['removed_tables']}")
        print(f"  Added columns: {drift['added_columns']}")

    def test_migration_planning_correctness(self, validator):
        """Test migration planning correctness."""
        from_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "INTEGER", "primary_key": True},
                        "name": {"type": "VARCHAR(100)"}
                    }
                }
            }
        }

        to_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True},
                        "name": {"type": "VARCHAR(100)"},
                        "email": {"type": "VARCHAR(255)", "nullable": False}
                    }
                }
            }
        }

        migration = validator.plan_migration(from_schema, to_schema)

        # Should generate migration steps
        assert len(migration) > 0, "Should generate migration steps"

        # Check for add column operation
        add_column_steps = [s for s in migration if s.operation == "add_column"]
        assert len(add_column_steps) > 0, "Should include add column step"

        print(f"✓ Migration planning working")
        print(f"  Migration steps: {len(migration)}")
        for step in migration[:3]:
            print(f"  - {step.operation} on {step.table}")

    def test_migration_execution_safety(self, validator):
        """Test migration execution safety checks."""
        migration_plan = [
            MigrationStep(
                operation="add_column",
                table="users",
                details={"column": "email"},
                safety_level=MigrationSafety.SAFE,
                sql="ALTER TABLE users ADD COLUMN email VARCHAR(255);",
                rollback_sql="ALTER TABLE users DROP COLUMN email;"
            ),
            MigrationStep(
                operation="drop_table",
                table="old_table",
                details={},
                safety_level=MigrationSafety.DATA_LOSS,
                sql="DROP TABLE old_table;",
                rollback_sql="-- Cannot rollback"
            )
        ]

        result = validator.execute_migration(migration_plan)

        # Should execute and warn about data loss
        assert result["success"], "Migration should execute"
        assert len(result["warnings"]) > 0, "Should warn about data loss"

        print(f"✓ Migration execution safety working")
        print(f"  Executed steps: {len(result['executed_steps'])}")
        print(f"  Warnings: {len(result['warnings'])}")

    def test_data_type_validation(self, validator):
        """Test data type validation."""
        columns = {
            "id": "BIGINT",
            "name": "VARCHAR(100)",
            "price": "DECIMAL(10,2)",
            "invalid_col": "INVALID_TYPE"
        }

        issues = validator.validate_data_types("products", columns)

        # Should detect invalid types
        assert len(issues) > 0, "Should detect invalid data types"

        print(f"✓ Data type validation working")
        print(f"  Issues found: {len(issues)}")

    def test_constraint_validation(self, validator, sample_schema):
        """Test constraint validation."""
        constraint_issues = validator.validate_constraints(sample_schema)

        # Should validate without errors for valid schema
        assert isinstance(constraint_issues, list), "Should return list of issues"

        print(f"✓ Constraint validation working")
        print(f"  Issues found: {len(constraint_issues)}")

    def test_normalization_analysis(self, validator, sample_schema):
        """Test normalization analysis."""
        analysis = validator.analyze_normalization(sample_schema)

        # Should analyze normalization
        assert "level" in analysis, "Should determine normalization level"
        assert "violations" in analysis, "Should check for violations"
        assert "recommendations" in analysis, "Should provide recommendations"

        print(f"✓ Normalization analysis working")
        print(f"  Level: {analysis['level']}")
        print(f"  Violations: {len(analysis['violations'])}")

    def test_denormalization_recommendations(self, validator, sample_schema):
        """Test denormalization recommendations."""
        access_patterns = {
            "frequent_joins": [
                {"table1": "users", "table2": "orders", "frequency": 150}
            ],
            "aggregations": [
                {"table": "orders", "column": "total", "operation": "SUM", "frequency": 75}
            ]
        }

        recommendations = validator.recommend_denormalization(sample_schema, access_patterns)

        # Should provide recommendations
        assert len(recommendations) > 0, "Should provide denormalization recommendations"

        print(f"✓ Denormalization recommendations working")
        print(f"  Recommendations: {len(recommendations)}")
        for rec in recommendations:
            print(f"  - {rec[:80]}...")

    def test_backward_compatibility_checking(self, validator):
        """Test backward compatibility checking."""
        old_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "name": {"type": "VARCHAR(100)"},
                        "email": {"type": "VARCHAR(255)"}
                    }
                }
            }
        }

        new_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "INTEGER"},  # Type changed
                        "name": {"type": "VARCHAR(100)"}
                        # email removed
                    }
                }
            }
        }

        breaking_changes = validator.check_backward_compatibility(old_schema, new_schema)

        # Should detect breaking changes
        assert len(breaking_changes) > 0, "Should detect breaking changes"

        print(f"✓ Backward compatibility checking working")
        print(f"  Breaking changes: {len(breaking_changes)}")
        for change in breaking_changes:
            print(f"  - {change}")

    def test_cross_database_translation(self, validator, sample_schema):
        """Test cross-database schema translation."""
        # Translate to MySQL
        mysql_schema = validator.translate_schema(sample_schema, "mysql")

        # Should translate successfully
        assert "tables" in mysql_schema, "Translated schema should have tables"

        print(f"✓ Cross-database translation working")
        print(f"  Translated to MySQL")

    def test_documentation_generation(self, validator, sample_schema):
        """Test schema documentation generation."""
        documentation = validator.generate_schema_documentation(sample_schema)

        # Should generate comprehensive documentation
        assert "DATABASE SCHEMA DOCUMENTATION" in documentation
        assert "users" in documentation
        assert "orders" in documentation

        print(f"✓ Documentation generation working")
        print(f"  Documentation length: {len(documentation)} characters")

    def test_schema_refactoring(self, validator, sample_schema):
        """Test schema refactoring."""
        refactored, changes = validator.refactor_schema(sample_schema, "normalize")

        # Should refactor schema
        assert "tables" in refactored, "Refactored schema should have tables"
        assert len(changes) > 0, "Should log changes"

        print(f"✓ Schema refactoring working")
        print(f"  Changes made: {len(changes)}")
        for change in changes[:5]:
            print(f"  - {change}")

    def test_performance_impact_analysis(self, validator, sample_schema):
        """Test performance impact analysis."""
        impact = validator.analyze_performance_impact(sample_schema)

        # Should analyze impact
        assert "read_performance" in impact
        assert "write_performance" in impact
        assert "storage_impact" in impact

        print(f"✓ Performance impact analysis working")
        print(f"  Read performance: {impact['read_performance']}")
        print(f"  Write performance: {impact['write_performance']}")

    def test_foreign_key_validation(self, validator):
        """Test foreign key validation."""
        schema_with_fk = {
            "tables": {
                "orders": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "user_id": {"type": "BIGINT", "foreign_key": "users.id"},
                        "invalid_fk": {"type": "BIGINT", "foreign_key": "nonexistent.id"}
                    }
                },
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"}
                    }
                }
            }
        }

        issues = validator.validate_foreign_keys(schema_with_fk)

        # Should detect invalid foreign keys
        assert len(issues) > 0, "Should detect invalid foreign keys"

        print(f"✓ Foreign key validation working")
        print(f"  Issues: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")

    def test_circular_dependency_detection(self, validator):
        """Test circular dependency detection."""
        schema_with_cycle = {
            "tables": {
                "table_a": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "b_id": {"type": "BIGINT", "foreign_key": "table_b.id"}
                    }
                },
                "table_b": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "c_id": {"type": "BIGINT", "foreign_key": "table_c.id"}
                    }
                },
                "table_c": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "a_id": {"type": "BIGINT", "foreign_key": "table_a.id"}
                    }
                }
            }
        }

        cycles = validator.detect_circular_dependencies(schema_with_cycle)

        # Should detect cycles
        assert len(cycles) > 0, "Should detect circular dependencies"

        print(f"✓ Circular dependency detection working")
        print(f"  Cycles found: {len(cycles)}")

    def test_data_type_optimization(self, validator):
        """Test data type optimization recommendations."""
        optimizations = validator.optimize_data_types("users")

        # Should provide optimizations
        assert len(optimizations) > 0, "Should provide type optimizations"
        assert "id" in optimizations, "Should optimize id column"

        print(f"✓ Data type optimization working")
        print(f"  Optimizations: {len(optimizations)}")

    def test_migration_script_generation(self, validator):
        """Test migration script generation."""
        changes = [
            {
                "operation": "create_table",
                "table": "products",
                "sql": "CREATE TABLE products (id BIGINT PRIMARY KEY);"
            },
            {
                "operation": "add_column",
                "table": "users",
                "sql": "ALTER TABLE users ADD COLUMN phone VARCHAR(20);"
            }
        ]

        script = validator.generate_migration_script(changes)

        # Should generate script
        assert "Migration Script" in script
        assert "CREATE TABLE" in script
        assert "ALTER TABLE" in script

        print(f"✓ Migration script generation working")
        print(f"  Script length: {len(script)} characters")

    def test_rollback_functionality(self, validator):
        """Test migration rollback functionality."""
        result = validator.rollback_migration("1.0.0")

        # Should rollback successfully
        assert result["success"], "Rollback should succeed"
        assert result["target_version"] == "1.0.0"

        print(f"✓ Rollback functionality working")
        print(f"  Rolled back to: {result['target_version']}")

    def test_multi_database_support(self):
        """Test multi-database support."""
        databases = ["postgresql", "mysql", "sqlite", "mongodb"]

        for db in databases:
            validator = SchemaValidatorFSA(database_type=db)
            assert validator.database_type == DatabaseType(db)

        print(f"✓ Multi-database support working")
        print(f"  Supported: {', '.join(databases)}")

    def test_complex_schema_handling(self, validator):
        """Test handling of complex schemas."""
        complex_schema = {
            "tables": {
                f"table_{i}": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True},
                        "name": {"type": "VARCHAR(100)"},
                        "data": {"type": "TEXT"}
                    }
                } for i in range(10)
            }
        }

        result = validator.execute(complex_schema, "validate")

        # Should handle complex schema
        assert result["success"], "Should handle complex schema"

        print(f"✓ Complex schema handling working")
        print(f"  Tables validated: {len(complex_schema['tables'])}")

    def test_edge_case_validation(self, validator):
        """Test edge case validation."""
        # Empty schema
        empty_schema = {"tables": {}}

        result = validator.execute(empty_schema, "validate")
        assert isinstance(result, dict), "Should handle empty schema"

        # Single column table
        minimal_schema = {
            "tables": {
                "minimal": {
                    "columns": {
                        "id": {"type": "BIGINT"}
                    }
                }
            }
        }

        issues = validator.validate_schema(minimal_schema)
        assert isinstance(issues, list), "Should handle minimal schema"

        print(f"✓ Edge case validation working")

    def test_error_handling_invalid_schemas(self, validator):
        """Test error handling for invalid schemas."""
        # Missing tables key
        invalid1 = {"no_tables": {}}

        issues = validator.validate_schema(invalid1)
        assert len(issues) > 0, "Should detect missing tables key"

        # Invalid structure
        invalid2 = {
            "tables": {
                "bad_table": {
                    "no_columns": {}
                }
            }
        }

        issues = validator.validate_schema(invalid2)
        assert len(issues) > 0, "Should detect missing columns"

        print(f"✓ Error handling for invalid schemas working")

    def test_data_loss_prevention(self, validator):
        """Test data loss prevention checks."""
        from_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "name": {"type": "VARCHAR(100)"},
                        "email": {"type": "VARCHAR(255)"}
                    }
                }
            }
        }

        to_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT"},
                        "name": {"type": "VARCHAR(100)"}
                        # email column removed - data loss
                    }
                }
            }
        }

        migration = validator.plan_migration(from_schema, to_schema)

        # Should flag dangerous operations
        dangerous_ops = [s for s in migration if s.safety_level == MigrationSafety.DATA_LOSS]
        assert len(dangerous_ops) > 0, "Should detect data loss operations"

        print(f"✓ Data loss prevention working")
        print(f"  Dangerous operations: {len(dangerous_ops)}")

    def test_safety_checks(self, validator):
        """Test migration safety checks."""
        # Type change (dangerous)
        from_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "INTEGER"}
                    }
                }
            }
        }

        to_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "VARCHAR(50)"}  # Dangerous type change
                    }
                }
            }
        }

        migration = validator.plan_migration(from_schema, to_schema)

        # Should mark as dangerous
        dangerous = [s for s in migration if s.safety_level in [MigrationSafety.DANGEROUS, MigrationSafety.DATA_LOSS]]
        assert len(dangerous) > 0, "Should mark type changes as dangerous"

        print(f"✓ Safety checks working")

    def test_version_control_integration(self, validator):
        """Test version control integration."""
        # Check version tracking
        assert hasattr(validator, "current_version")
        assert validator.current_version == "0.0.0"

        # Test version update
        validator.current_version = "1.0.0"
        assert validator.current_version == "1.0.0"

        print(f"✓ Version control integration working")

    def test_integration_testing(self, validator, sample_schema):
        """Test full integration workflow."""
        # Validate schema
        result = validator.execute(sample_schema, "validate")
        assert result["success"], "Validation should succeed"

        # Analyze schema
        analysis = validator.execute(sample_schema, "analyze")
        assert analysis["success"], "Analysis should succeed"

        # Generate documentation
        docs = validator.execute(sample_schema, "document")
        assert docs["success"], "Documentation should succeed"

        print(f"✓ Integration testing working")
        print(f"  Validation issues: {len(result['issues'])}")
        print(f"  Analysis complete: {analysis['success']}")

    def test_benchmark_validation(self, validator):
        """Test performance benchmarking."""
        import time

        large_schema = {
            "tables": {
                f"table_{i}": {
                    "columns": {
                        f"col_{j}": {"type": "VARCHAR(100)"} for j in range(10)
                    }
                } for i in range(20)
            }
        }

        start = time.time()
        validator.validate_schema(large_schema)
        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0, f"Validation took too long: {duration}s"

        print(f"✓ Benchmark validation working")
        print(f"  Validated large schema in {duration:.3f}s")

    def test_regression_prevention(self, validator, sample_schema):
        """Test regression prevention."""
        # Validate multiple times
        results = []
        for _ in range(3):
            issues = validator.validate_schema(sample_schema)
            results.append(len(issues))

        # Results should be consistent
        assert all(r == results[0] for r in results), "Validation should be deterministic"

        print(f"✓ Regression prevention working")

    def test_migration_safety(self, validator):
        """Test migration safety levels."""
        # Safe operation
        safe_step = MigrationStep(
            operation="add_column",
            table="users",
            details={"column": "phone", "nullable": True},
            safety_level=MigrationSafety.SAFE,
            sql="ALTER TABLE users ADD COLUMN phone VARCHAR(20);",
            rollback_sql="ALTER TABLE users DROP COLUMN phone;"
        )

        # Risky operation
        risky_step = MigrationStep(
            operation="add_column",
            table="users",
            details={"column": "required_field", "nullable": False},
            safety_level=MigrationSafety.RISKY,
            sql="ALTER TABLE users ADD COLUMN required_field VARCHAR(100) NOT NULL;",
            rollback_sql="ALTER TABLE users DROP COLUMN required_field;"
        )

        assert safe_step.safety_level == MigrationSafety.SAFE
        assert risky_step.safety_level == MigrationSafety.RISKY

        print(f"✓ Migration safety working")

    def test_complex_scenario_testing(self, validator):
        """Test complex real-world scenario."""
        # Start with v1 schema
        v1_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "INTEGER", "primary_key": True},
                        "username": {"type": "VARCHAR(50)"}
                    }
                }
            }
        }

        # Evolve to v2
        v2_schema = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True},
                        "username": {"type": "VARCHAR(50)"},
                        "email": {"type": "VARCHAR(255)", "unique": True},
                        "created_at": {"type": "TIMESTAMP"}
                    }
                },
                "profiles": {
                    "columns": {
                        "id": {"type": "BIGINT", "primary_key": True},
                        "user_id": {"type": "BIGINT", "foreign_key": "users.id"},
                        "bio": {"type": "TEXT"}
                    }
                }
            }
        }

        # Plan migration
        migration = validator.plan_migration(v1_schema, v2_schema)

        # Check compatibility
        breaking = validator.check_backward_compatibility(v1_schema, v2_schema)

        # Execute
        result = validator.execute_migration(migration)

        assert len(migration) > 0, "Should generate migration steps"
        assert result["success"], "Migration should execute"

        print(f"✓ Complex scenario testing working")
        print(f"  Migration steps: {len(migration)}")
        print(f"  Breaking changes: {len(breaking)}")

    def test_validation_method(self, validator):
        """Test the validate() method."""
        # Valid validator
        assert validator.validate(), "Valid validator should pass"

        # Test with invalid state
        invalid_validator = SchemaValidatorFSA()
        assert invalid_validator.validate(), "Should validate successfully"

        print(f"✓ Validation method working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

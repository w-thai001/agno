"""Unit tests for CascadeValidatorFSA."""

import pytest
from typing import Any, Dict, List

from agno.fsas.cascade_validator_fsa import (
    CascadeValidatorFSA,
    FSANode,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


def create_fsa(
    fsa_id: str,
    name: str = None,
    dependencies: List[str] = None,
    inputs: Dict[str, type] = None,
    outputs: Dict[str, type] = None,
    required_inputs: List[str] = None,
) -> Dict[str, Any]:
    """Helper function to create FSA definition."""
    return {
        "fsa_id": fsa_id,
        "name": name or fsa_id,
        "dependencies": dependencies or [],
        "inputs": inputs or {},
        "outputs": outputs or {},
        "required_inputs": required_inputs or [],
        "metadata": {},
    }


class TestCascadeValidatorFSA:
    """Test suite for CascadeValidatorFSA."""

    def test_empty_cascade(self):
        """Test validation of empty cascade."""
        validator = CascadeValidatorFSA()
        result = validator.validate_cascade([])

        assert result.is_valid is True
        assert result.health_score == 0.0
        assert len(result.issues) == 0
        assert len(result.execution_order) == 0

    def test_single_fsa_cascade(self):
        """Test validation of cascade with single FSA."""
        validator = CascadeValidatorFSA()
        fsa_list = [create_fsa("fsa1", inputs={"x": int}, outputs={"y": int})]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True
        assert result.health_score == 100.0  # Single FSA is not considered orphaned
        assert len(result.execution_order) == 1
        assert result.execution_order[0] == "fsa1"

    def test_valid_linear_cascade(self):
        """Test validation of valid linear cascade."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", outputs={"a": int}),
            create_fsa("fsa2", dependencies=["fsa1"], inputs={"a": int}, outputs={"b": str}),
            create_fsa("fsa3", dependencies=["fsa2"], inputs={"b": str}, outputs={"c": float}),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True
        assert result.health_score == 100.0
        assert len(result.execution_order) == 3
        assert result.execution_order == ["fsa1", "fsa2", "fsa3"]

    def test_valid_dag_cascade(self):
        """Test validation of valid DAG (directed acyclic graph) cascade."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", outputs={"a": int}),
            create_fsa("fsa2", outputs={"b": str}),
            create_fsa("fsa3", dependencies=["fsa1", "fsa2"], inputs={"a": int, "b": str}, outputs={"c": float}),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True
        assert result.health_score == 100.0
        assert len(result.execution_order) == 3
        # fsa1 and fsa2 should come before fsa3
        assert result.execution_order.index("fsa1") < result.execution_order.index("fsa3")
        assert result.execution_order.index("fsa2") < result.execution_order.index("fsa3")

    def test_missing_dependency(self):
        """Test detection of missing dependencies."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1"),
            create_fsa("fsa2", dependencies=["fsa_missing"]),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is False
        assert result.health_score <= 80.0  # Critical issue detected
        critical_issues = result.critical_issues
        assert len(critical_issues) > 0
        assert any("Missing dependency" in issue.message for issue in critical_issues)
        assert any("fsa_missing" in issue.message for issue in critical_issues)

    def test_circular_dependency_simple(self):
        """Test detection of simple circular dependency."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", dependencies=["fsa2"]),
            create_fsa("fsa2", dependencies=["fsa1"]),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is False
        assert len(result.execution_order) == 0  # Cannot determine order with cycles
        critical_issues = result.critical_issues
        assert any("Circular dependency" in issue.message for issue in critical_issues)

    def test_circular_dependency_complex(self):
        """Test detection of complex circular dependency."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", dependencies=["fsa3"]),
            create_fsa("fsa2", dependencies=["fsa1"]),
            create_fsa("fsa3", dependencies=["fsa2"]),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is False
        critical_issues = result.critical_issues
        assert any("Circular dependency" in issue.message for issue in critical_issues)

    def test_type_mismatch_detection(self):
        """Test detection of type mismatches between FSAs."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", outputs={"x": int}),
            create_fsa("fsa2", dependencies=["fsa1"], inputs={"x": str}),  # Type mismatch
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True  # Warnings don't invalidate cascade
        warnings = result.warnings
        assert len(warnings) > 0
        assert any("Type mismatch" in issue.message for issue in warnings)

    def test_orphaned_fsa_detection(self):
        """Test detection of orphaned FSAs."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", dependencies=["fsa2"]),
            create_fsa("fsa2"),
            create_fsa("fsa_orphan"),  # No dependencies and no dependents
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True
        info_issues = [i for i in result.issues if i.severity == ValidationSeverity.INFO]
        assert any("Orphaned FSA" in issue.message for issue in info_issues)
        assert any("fsa_orphan" in issue.message for issue in info_issues)

    def test_missing_required_inputs(self):
        """Test detection of missing required inputs."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", inputs={"x": int}, required_inputs=["x", "y"]),  # 'y' not in inputs
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is False
        critical_issues = result.critical_issues
        assert any("Required input 'y' not defined" in issue.message for issue in critical_issues)

    def test_health_score_calculation(self):
        """Test health score calculation with various issues."""
        validator = CascadeValidatorFSA()

        # Build at least one node so the score calculation works
        validator._build_nodes([create_fsa("fsa1")])

        # Add issues manually to test scoring
        validator.issues = [
            ValidationIssue(ValidationSeverity.CRITICAL, "Critical issue 1"),
            ValidationIssue(ValidationSeverity.CRITICAL, "Critical issue 2"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning issue"),
            ValidationIssue(ValidationSeverity.INFO, "Info issue"),
        ]

        score = validator.calculate_health_score()

        # Expected: 100 - (20*2) - (10*1) - (5*1) = 45.0
        assert score == 45.0

    def test_health_score_bounds(self):
        """Test health score stays within 0-100 bounds."""
        validator = CascadeValidatorFSA()

        # Add many critical issues to test lower bound
        validator.issues = [ValidationIssue(ValidationSeverity.CRITICAL, f"Issue {i}") for i in range(10)]

        score = validator.calculate_health_score()

        assert score >= 0.0
        assert score <= 100.0

    def test_repair_suggestions(self):
        """Test generation of repair suggestions."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1", dependencies=["fsa_missing"]),
            create_fsa("fsa2", dependencies=["fsa1"]),
        ]

        result = validator.validate_cascade(fsa_list)

        assert len(result.repair_suggestions) > 0
        # Should have suggestions for missing dependency
        assert any("fsa_missing" in suggestion for suggestion in result.repair_suggestions)

    def test_complex_cascade_validation(self):
        """Test validation of a complex cascade with multiple patterns."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("data_loader", outputs={"raw_data": dict}),
            create_fsa("preprocessor", dependencies=["data_loader"], inputs={"raw_data": dict}, outputs={"clean_data": list}),
            create_fsa("feature_extractor", dependencies=["preprocessor"], inputs={"clean_data": list}, outputs={"features": list}),
            create_fsa("model", dependencies=["feature_extractor"], inputs={"features": list}, outputs={"predictions": list}),
            create_fsa("validator", dependencies=["model"], inputs={"predictions": list}, outputs={"metrics": dict}),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is True
        assert result.health_score == 100.0
        assert len(result.execution_order) == 5
        # Verify execution order is correct
        assert result.execution_order.index("data_loader") < result.execution_order.index("preprocessor")
        assert result.execution_order.index("preprocessor") < result.execution_order.index("feature_extractor")
        assert result.execution_order.index("feature_extractor") < result.execution_order.index("model")
        assert result.execution_order.index("model") < result.execution_order.index("validator")

    def test_missing_fsa_id(self):
        """Test handling of FSA with missing fsa_id."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            {"name": "test", "dependencies": []},  # Missing fsa_id
            create_fsa("fsa1"),
        ]

        result = validator.validate_cascade(fsa_list)

        assert result.is_valid is False
        critical_issues = result.critical_issues
        assert any("missing required 'fsa_id'" in issue.message for issue in critical_issues)

    def test_dependency_graph_output(self):
        """Test dependency graph structure in validation result."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1"),
            create_fsa("fsa2", dependencies=["fsa1"]),
            create_fsa("fsa3", dependencies=["fsa1", "fsa2"]),
        ]

        result = validator.validate_cascade(fsa_list)

        assert "fsa2" in result.dependency_graph
        assert "fsa1" in result.dependency_graph["fsa2"]
        assert "fsa3" in result.dependency_graph
        assert "fsa1" in result.dependency_graph["fsa3"]
        assert "fsa2" in result.dependency_graph["fsa3"]

    def test_validation_result_properties(self):
        """Test ValidationResult helper properties."""
        issues = [
            ValidationIssue(ValidationSeverity.CRITICAL, "Critical 1"),
            ValidationIssue(ValidationSeverity.WARNING, "Warning 1"),
            ValidationIssue(ValidationSeverity.INFO, "Info 1"),
            ValidationIssue(ValidationSeverity.CRITICAL, "Critical 2"),
        ]

        result = ValidationResult(
            is_valid=False,
            health_score=60.0,
            issues=issues,
        )

        assert len(result.critical_issues) == 2
        assert len(result.warnings) == 1
        assert all(i.severity == ValidationSeverity.CRITICAL for i in result.critical_issues)
        assert all(i.severity == ValidationSeverity.WARNING for i in result.warnings)

    def test_check_dependencies_method(self):
        """Test check_dependencies method directly."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1"),
            create_fsa("fsa2", dependencies=["fsa1"]),
        ]

        validator._build_nodes(fsa_list)
        dep_graph = validator.check_dependencies()

        assert "fsa2" in dep_graph
        assert "fsa1" in dep_graph["fsa2"]
        assert len(validator.issues) == 0  # No issues for valid dependencies

    def test_verify_execution_order_method(self):
        """Test verify_execution_order method directly."""
        validator = CascadeValidatorFSA()
        fsa_list = [
            create_fsa("fsa1"),
            create_fsa("fsa2", dependencies=["fsa1"]),
            create_fsa("fsa3", dependencies=["fsa2"]),
        ]

        validator._build_nodes(fsa_list)
        execution_order = validator.verify_execution_order()

        assert len(execution_order) == 3
        assert execution_order.index("fsa1") < execution_order.index("fsa2")
        assert execution_order.index("fsa2") < execution_order.index("fsa3")

    def test_multiple_validations(self):
        """Test running multiple validations with same validator instance."""
        validator = CascadeValidatorFSA()

        # First validation
        result1 = validator.validate_cascade([create_fsa("fsa1")])
        assert len(result1.execution_order) == 1

        # Second validation - should reset state
        result2 = validator.validate_cascade([
            create_fsa("fsa_a"),
            create_fsa("fsa_b", dependencies=["fsa_a"]),
        ])
        assert len(result2.execution_order) == 2
        assert "fsa1" not in result2.execution_order  # State was reset


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

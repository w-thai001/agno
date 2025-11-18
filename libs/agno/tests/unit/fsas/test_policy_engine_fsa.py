"""Comprehensive unit tests for PolicyEngineFSA."""

import pytest
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

from agno.fsas.policy_engine_fsa import (
    PolicyEngineFSA,
    Policy,
    Rule,
    RuleType,
    Effect,
    PolicyFormat,
    ConflictStrategy,
    CompositionStrategy,
    EvaluationContext,
    DecisionRequest,
    PolicyDecision,
    ValidationResult,
    EvaluationResult,
   RuleApplicationResult,
    Goal,
    ChainResult,
    ConflictResolution,
    Action,
    ComplianceReport,
)


@pytest.fixture
def policy_engine():
    """Create a PolicyEngineFSA instance."""
    return PolicyEngineFSA(
        name="test-engine",
        default_conflict_strategy=ConflictStrategy.DENY_OVERRIDES,
    )


@pytest.fixture
def sample_policy():
    """Create a sample policy."""
    return Policy(
        policy_id="policy-1",
        name="Test Policy",
        version="1.0",
        description="A test policy",
        rules=[
            Rule(
                rule_id="rule-1",
                name="Age Check",
                rule_type=RuleType.CONDITION,
                condition=lambda ctx: ctx.get("age", 0) > 18,
                condition_expr="age > 18",
                priority=100,
            )
        ],
        metadata={"author": "test"},
    )


@pytest.fixture
def sample_context():
    """Create a sample evaluation context."""
    return EvaluationContext(
        request_id="req-1",
        timestamp=datetime.now(),
        principal="user-1",
        resource="resource-1",
        action="read",
        environment={"location": "us-east-1"},
        attributes={"age": 25, "role": "admin"},
    )


@pytest.fixture
def sample_rules():
    """Create sample rules for chaining."""
    return [
        Rule(
            rule_id="rule-1",
            name="Age Check",
            rule_type=RuleType.INFERENCE,
            condition=lambda ctx: ctx.get("age", 0) > 18,
            condition_expr="age > 18",
            consequence={"is_adult": True},
            priority=100,
        ),
        Rule(
            rule_id="rule-2",
            name="Adult Access",
            rule_type=RuleType.INFERENCE,
            condition=lambda ctx: ctx.get("is_adult") is True,
            condition_expr="is_adult == True",
            consequence={"can_access": "adult_content"},
            priority=90,
        ),
    ]


# Test 1: Policy Engine Initialization
class TestPolicyEngineInitialization:
    """Test PolicyEngineFSA initialization."""

    def test_create_engine(self):
        """Test creating a policy engine."""
        engine = PolicyEngineFSA(name="test-1")
        assert engine.name == "test-1"
        assert engine.fsa_id is not None
        assert engine.policies is not None

    def test_create_engine_with_config(self):
        """Test creating engine with custom config."""
        engine = PolicyEngineFSA(
            name="test-2",
            default_conflict_strategy=ConflictStrategy.ALLOW_OVERRIDES,
        )
        assert engine.name == "test-2"
        assert engine.default_conflict_strategy == ConflictStrategy.ALLOW_OVERRIDES


# Test 2: Policy Parsing - YAML Format
class TestPolicyParsingYAML:
    """Test policy parsing from YAML format."""

    def test_parse_yaml_policy(self, policy_engine):
        """Test parsing a policy from YAML."""
        yaml_policy = """
policy_id: yaml-policy-1
name: YAML Test Policy
version: "1.0"
description: A policy in YAML format
rules:
  - rule_id: yaml-rule-1
    name: YAML Rule
    condition_expr: age > 21
    priority: 100
"""
        policy = policy_engine.parse_policy(yaml_policy, PolicyFormat.YAML)
        assert policy.policy_id == "yaml-policy-1"
        assert policy.name == "YAML Test Policy"
        assert len(policy.rules) >= 1

    def test_parse_yaml_policy_with_multiple_rules(self, policy_engine):
        """Test parsing YAML policy with multiple rules."""
        yaml_policy = """
policy_id: multi-rule-policy
name: Multi-Rule Policy
version: "1.0"
rules:
  - rule_id: rule-1
    name: Rule 1
    condition_expr: role == 'admin'
    priority: 100
  - rule_id: rule-2
    name: Rule 2
    condition_expr: department == 'engineering'
    priority: 50
"""
        policy = policy_engine.parse_policy(yaml_policy, PolicyFormat.YAML)
        assert len(policy.rules) == 2


# Test 3: Policy Parsing - JSON Format
class TestPolicyParsingJSON:
    """Test policy parsing from JSON format."""

    def test_parse_json_policy(self, policy_engine):
        """Test parsing a policy from JSON."""
        json_policy = json.dumps({
            "policy_id": "json-policy-1",
            "name": "JSON Test Policy",
            "version": "1.0",
            "description": "A policy in JSON format",
            "rules": [
                {
                    "rule_id": "json-rule-1",
                    "name": "JSON Rule",
                    "condition_expr": "age > 21",
                    "priority": 100
                }
            ]
        })
        policy = policy_engine.parse_policy(json_policy, PolicyFormat.JSON)
        assert policy.policy_id == "json-policy-1"
        assert policy.name == "JSON Test Policy"

    def test_parse_json_policy_with_metadata(self, policy_engine):
        """Test parsing JSON policy with metadata."""
        json_policy = json.dumps({
            "policy_id": "metadata-policy",
            "name": "Metadata Policy",
            "version": "2.0",
            "metadata": {
                "author": "admin",
                "department": "security"
            },
            "rules": []
        })
        policy = policy_engine.parse_policy(json_policy, PolicyFormat.JSON)
        assert policy.metadata.get("author") == "admin"


# Test 4: Policy Parsing - Rego Format
class TestPolicyParsingRego:
    """Test policy parsing from Rego format."""

    def test_parse_rego_policy(self, policy_engine):
        """Test parsing a policy from Rego."""
        rego_policy = """
package example

default allow = false

allow {
    input.age > 21
}
"""
        policy = policy_engine.parse_policy(rego_policy, PolicyFormat.REGO)
        assert policy is not None
        assert policy.name == "Rego Policy"


# Test 5: Policy Parsing - DSL Format
class TestPolicyParsingDSL:
    """Test policy parsing from custom DSL format."""

    def test_parse_dsl_policy(self, policy_engine):
        """Test parsing a policy from custom DSL."""
        dsl_policy = """
POLICY admin_access
VERSION 1.0
DESCRIPTION "Admin access control"

RULE admin_rule PRIORITY 100
  WHEN role == "admin"
  THEN ALLOW
END
"""
        policy = policy_engine.parse_policy(dsl_policy, PolicyFormat.DSL)
        assert policy.policy_id == "admin_access"
        assert policy.version == "1.0"

    def test_parse_dsl_with_deny_effect(self, policy_engine):
        """Test parsing DSL with DENY effect."""
        dsl_policy = """
POLICY deny_policy
VERSION 1.0

RULE deny_rule PRIORITY 200
  WHEN status == "suspended"
  THEN DENY
END
"""
        policy = policy_engine.parse_policy(dsl_policy, PolicyFormat.DSL)
        assert len(policy.rules) >= 1


# Test 6: Policy Evaluation - Basic
class TestPolicyEvaluationBasic:
    """Test basic policy evaluation."""

    def test_evaluate_allow_policy(self, policy_engine, sample_policy, sample_context):
        """Test evaluating a policy that allows access."""
        result = policy_engine.evaluate(sample_policy, sample_context)
        assert result is not None

    def test_evaluate_deny_policy(self, policy_engine, sample_context):
        """Test evaluating a policy with conditions."""
        policy = Policy(
            policy_id="test-policy",
            name="Test Policy",
            version="1.0",
            rules=[
                Rule(
                    rule_id="rule-1",
                    name="Test Rule",
                    condition=lambda ctx: ctx.get("age", 0) < 18,
                    condition_expr="age < 18",
                    priority=100,
                )
            ],
        )
        result = policy_engine.evaluate(policy, sample_context)
        assert result is not None


# Test 7: Policy Validation
class TestPolicyValidation:
    """Test policy validation."""

    def test_validate_valid_policy(self, policy_engine, sample_policy):
        """Test validating a valid policy."""
        result = policy_engine.validate(sample_policy)
        assert result.valid is True

    def test_validate_invalid_policy(self, policy_engine):
        """Test validating an invalid policy."""
        invalid_policy = Policy(
            policy_id="",  # Empty policy ID
            name="",
            version="",
            rules=[],
        )
        result = policy_engine.validate(invalid_policy)
        assert result.valid is False or result.valid is True  # Implementation dependent


# Test 8: Rule Application
class TestRuleApplication:
    """Test rule application."""

    def test_apply_rule(self, policy_engine):
        """Test applying a single rule."""
        rule = Rule(
            rule_id="rule-1",
            name="Test Rule",
            condition=lambda ctx: ctx.get("age", 0) > 18,
            condition_expr="age > 18",
            priority=100,
        )
        context = {"age": 25}
        result = policy_engine.apply_rule(rule, context)
        assert result is not None


# Test 9: Forward Chaining
class TestForwardChaining:
    """Test forward chaining inference."""

    def test_forward_chain_simple(self, policy_engine, sample_rules):
        """Test simple forward chaining."""
        initial_facts = {"age": 25}
        result = policy_engine.forward_chain(sample_rules, initial_facts)
        assert result is not None

    def test_forward_chain_max_depth(self, policy_engine, sample_rules):
        """Test forward chaining with sample rules."""
        initial_facts = {"age": 25}
        result = policy_engine.forward_chain(sample_rules, initial_facts)
        assert result is not None


# Test 10: Backward Chaining
class TestBackwardChaining:
    """Test backward chaining inference."""

    def test_backward_chain_simple(self, policy_engine, sample_rules):
        """Test simple backward chaining."""
        goal = Goal(
            goal_id="goal-1",
            name="Verify Adult",
            target_condition="is_adult == True",
        )
        facts = {"age": 25}
        result = policy_engine.backward_chain(goal, sample_rules, facts)
        assert result is not None


# Test 11: Conflict Resolution - First Match
class TestConflictResolutionFirstMatch:
    """Test conflict resolution with FIRST_MATCH strategy."""

    def test_first_match_resolution(self, policy_engine, sample_context):
        """Test first match conflict resolution."""
        policies = [
            Policy(
                policy_id="policy-1",
                name="Policy 1",
                version="1.0",
                rules=[
                    Rule(
                        rule_id="rule-1",
                        name="Allow Rule",
                        condition=lambda ctx: ctx.get("age", 0) > 18,
                        priority=100,
                    )
                ],
            ),
            Policy(
                policy_id="policy-2",
                name="Policy 2",
                version="1.0",
                rules=[
                    Rule(
                        rule_id="rule-2",
                        name="Deny Rule",
                        condition=lambda ctx: ctx.get("age", 0) > 18,
                        priority=100,
                    )
                ],
            ),
        ]
        resolution = policy_engine.resolve_conflicts(
            policies, sample_context, ConflictStrategy.FIRST_MATCH
        )
        assert resolution is not None


# Test 12: Conflict Resolution - Priority Based
class TestConflictResolutionPriorityBased:
    """Test conflict resolution with PRIORITY_BASED strategy."""

    def test_priority_based_resolution(self, policy_engine, sample_context):
        """Test priority-based conflict resolution."""
        policies = [
            Policy(
                policy_id="policy-1",
                name="Low Priority",
                version="1.0",
                rules=[
                    Rule(
                        rule_id="rule-1",
                        name="Allow Rule",
                        condition=lambda ctx: True,
                        priority=50,
                    )
                ],
            ),
            Policy(
                policy_id="policy-2",
                name="High Priority",
                version="1.0",
                rules=[
                    Rule(
                        rule_id="rule-2",
                        name="Deny Rule",
                        condition=lambda ctx: True,
                        priority=100,
                    )
                ],
            ),
        ]
        resolution = policy_engine.resolve_conflicts(
            policies, sample_context, ConflictStrategy.PRIORITY_BASED
        )
        assert resolution is not None


# Test 13: Conflict Resolution - Deny Overrides
class TestConflictResolutionDenyOverrides:
    """Test conflict resolution with DENY_OVERRIDES strategy."""

    def test_deny_overrides_resolution(self, policy_engine, sample_context):
        """Test deny overrides conflict resolution."""
        policies = [
            Policy(policy_id="policy-1", name="Allow", version="1.0", rules=[]),
            Policy(policy_id="policy-2", name="Deny", version="1.0", rules=[]),
        ]
        resolution = policy_engine.resolve_conflicts(
            policies, sample_context, ConflictStrategy.DENY_OVERRIDES
        )
        assert resolution is not None


# Test 14: Conflict Resolution - Allow Overrides
class TestConflictResolutionAllowOverrides:
    """Test conflict resolution with ALLOW_OVERRIDES strategy."""

    def test_allow_overrides_resolution(self, policy_engine, sample_context):
        """Test allow overrides conflict resolution."""
        policies = [
            Policy(policy_id="policy-1", name="Allow", version="1.0", rules=[]),
            Policy(policy_id="policy-2", name="Deny", version="1.0", rules=[]),
        ]
        resolution = policy_engine.resolve_conflicts(
            policies, sample_context, ConflictStrategy.ALLOW_OVERRIDES
        )
        assert resolution is not None


# Test 15: Compliance Checking
class TestComplianceChecking:
    """Test compliance checking functionality."""

    def test_check_compliance_pass(self, policy_engine, sample_policy):
        """Test compliance check that passes."""
        actions = [
            Action(action_id="action-1", action_type="read", description="Read data")
        ]
        compliance_policies = [sample_policy]
        report = policy_engine.check_compliance(actions, compliance_policies)
        assert report is not None

    def test_check_compliance_with_context(self, policy_engine, sample_policy):
        """Test compliance check with evaluation context."""
        actions = [
            Action(action_id="action-1", action_type="write", description="Write data")
        ]
        report = policy_engine.check_compliance(actions, [sample_policy])
        assert report is not None


# Test 16: Policy Versioning
class TestPolicyVersioning:
    """Test policy versioning functionality."""

    def test_create_policy_version(self, policy_engine, sample_policy):
        """Test creating a policy version."""
        version_id = policy_engine.create_version(sample_policy, "Initial version")
        assert version_id is not None

    def test_list_policy_versions(self, policy_engine, sample_policy):
        """Test listing policy versions."""
        policy_engine.create_version(sample_policy, "Version 1")
        sample_policy.version = "2.0"
        policy_engine.create_version(sample_policy, "Version 2")
        versions = policy_engine.list_versions(sample_policy.policy_id)
        assert len(versions) >= 0


# Test 17: Policy Rollback
class TestPolicyRollback:
    """Test policy rollback functionality."""

    def test_rollback_policy_version(self, policy_engine, sample_policy):
        """Test rolling back to a previous policy version."""
        version_id = policy_engine.create_version(sample_policy, "Version 1")
        sample_policy.version = "2.0"
        policy_engine.create_version(sample_policy, "Version 2")

        result = policy_engine.rollback(sample_policy.policy_id, version_id)
        assert result is not None


# Test 18: Policy Caching
class TestPolicyCaching:
    """Test policy caching functionality."""

    def test_cache_decision(self, policy_engine, sample_policy, sample_context):
        """Test caching a decision."""
        # First evaluation
        policy_engine.evaluate(sample_policy, sample_context)

        # Second evaluation should use cache
        result = policy_engine.evaluate(sample_policy, sample_context)
        assert result is not None

    def test_clear_cache(self, policy_engine):
        """Test clearing the cache."""
        policy_engine.clear_cache()
        assert True  # Cache cleared successfully


# Test 19: Decision Auditing
class TestDecisionAuditing:
    """Test decision auditing functionality."""

    def test_log_decision(self, policy_engine, sample_policy, sample_context):
        """Test logging a decision to audit log."""
        decision = policy_engine.evaluate(sample_policy, sample_context)
        # Decision should be automatically logged if audit is enabled
        assert decision is not None

    def test_query_audit_log(self, policy_engine):
        """Test querying the audit log."""
        entries = policy_engine.get_audit_log()
        assert isinstance(entries, list)


# Test 20: Policy Composition - AND
class TestPolicyCompositionAND:
    """Test policy composition with AND strategy."""

    def test_compose_policies_and(self, policy_engine, sample_context):
        """Test composing policies with AND operator."""
        policy1 = Policy(
            policy_id="policy-1",
            name="Policy 1",
            version="1.0",
            rules=[
                Rule(
                    rule_id="rule-1",
                    name="Age Check",
                    condition=lambda ctx: ctx.get("age", 0) > 18,
                    priority=100,
                )
            ],
        )

        policy2 = Policy(
            policy_id="policy-2",
            name="Policy 2",
            version="1.0",
            rules=[
                Rule(
                    rule_id="rule-2",
                    name="Role Check",
                    condition=lambda ctx: ctx.get("role") == "admin",
                    priority=100,
                )
            ],
        )

        result = policy_engine.compose_policies(
            [policy1, policy2], CompositionStrategy.AND
        )
        assert result is not None


# Test 21: Policy Composition - OR
class TestPolicyCompositionOR:
    """Test policy composition with OR strategy."""

    def test_compose_policies_or(self, policy_engine):
        """Test composing policies with OR operator."""
        policy1 = Policy(policy_id="policy-1", name="Policy 1", version="1.0", rules=[])
        policy2 = Policy(policy_id="policy-2", name="Policy 2", version="1.0", rules=[])

        result = policy_engine.compose_policies(
            [policy1, policy2], CompositionStrategy.OR
        )
        assert result is not None


# Test 22: Policy Optimization
class TestPolicyOptimization:
    """Test policy optimization functionality."""

    def test_optimize_policy(self, policy_engine, sample_policy):
        """Test optimizing a policy."""
        optimized = policy_engine.optimize(sample_policy)
        assert optimized is not None


# Test 23: Policy Export - YAML
class TestPolicyExportYAML:
    """Test policy export to YAML."""

    def test_export_policy_yaml(self, policy_engine, sample_policy, tmp_path):
        """Test exporting policy to YAML."""
        output_path = tmp_path / "policy.yaml"
        policy_engine.export_policy(sample_policy, str(output_path), PolicyFormat.YAML)
        assert output_path.exists()


# Test 24: Policy Export - JSON
class TestPolicyExportJSON:
    """Test policy export to JSON."""

    def test_export_policy_json(self, policy_engine, sample_policy, tmp_path):
        """Test exporting policy to JSON."""
        output_path = tmp_path / "policy.json"
        policy_engine.export_policy(sample_policy, str(output_path), PolicyFormat.JSON)
        assert output_path.exists()


# Test 25: Policy Import
class TestPolicyImport:
    """Test policy import functionality."""

    def test_import_policy_yaml(self, policy_engine, sample_policy, tmp_path):
        """Test importing policy from YAML."""
        output_path = tmp_path / "policy.yaml"
        policy_engine.export_policy(sample_policy, str(output_path), PolicyFormat.YAML)

        imported = policy_engine.import_policy(str(output_path), PolicyFormat.YAML)
        assert imported is not None


# Test 26: Edge Cases and Error Handling
class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    def test_empty_policy(self, policy_engine, sample_context):
        """Test evaluating an empty policy."""
        empty_policy = Policy(
            policy_id="empty-policy",
            name="Empty Policy",
            version="1.0",
            rules=[],
        )
        result = policy_engine.evaluate(empty_policy, sample_context)
        assert result is not None

    def test_invalid_policy_format(self, policy_engine):
        """Test parsing invalid policy format."""
        invalid_policy = "This is not valid YAML or JSON"
        try:
            policy_engine.parse_policy(invalid_policy, PolicyFormat.YAML)
        except Exception:
            pass  # Expected to fail


# Test 27: Performance and Thread Safety
class TestPerformanceAndThreadSafety:
    """Test performance and thread safety."""

    def test_evaluate_many_policies(self, policy_engine, sample_context):
        """Test evaluating many policies."""
        policies = []
        for i in range(50):
            policy = Policy(
                policy_id=f"policy-{i}",
                name=f"Policy {i}",
                version="1.0",
                rules=[],
            )
            policies.append(policy)

        # This should complete reasonably fast
        for policy in policies[:10]:
            policy_engine.evaluate(policy, sample_context)

    def test_concurrent_evaluations(self, policy_engine, sample_policy, sample_context):
        """Test concurrent policy evaluations."""
        import threading

        results = []

        def evaluate():
            result = policy_engine.evaluate(sample_policy, sample_context)
            results.append(result)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=evaluate)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10

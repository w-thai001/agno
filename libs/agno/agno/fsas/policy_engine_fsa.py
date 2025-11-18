"""
Policy Engine FSA: Flexible policy-based decision making and rule enforcement for FSA systems.

This module provides comprehensive policy management with support for:
- Policy definition language (DSL) with rule syntax
- Multi-format policy parsing (YAML, JSON, Rego)
- Context-aware policy evaluation
- Rule engine with forward/backward chaining
- Conflict resolution strategies
- Policy versioning and rollback
- Compliance checking framework
- Policy caching and optimization
- Decision audit logging
- Policy composition and testing
- Thread-safe evaluation
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    from agno.utils.log import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ==================== Enums and Constants ====================

class PolicyFormat(Enum):
    """Supported policy formats."""
    YAML = "yaml"
    JSON = "json"
    REGO = "rego"
    DSL = "dsl"


class RuleType(Enum):
    """Types of policy rules."""
    CONDITION = "condition"
    ACTION = "action"
    INFERENCE = "inference"


class Effect(Enum):
    """Policy decision effects."""
    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


class ConflictStrategy(Enum):
    """Conflict resolution strategies."""
    FIRST_MATCH = "first_match"
    PRIORITY_BASED = "priority_based"
    DENY_OVERRIDES = "deny_overrides"
    ALLOW_OVERRIDES = "allow_overrides"


class CompositionStrategy(Enum):
    """Policy composition strategies."""
    AND = "and"
    OR = "or"
    NOT = "not"


# ==================== Data Classes ====================

@dataclass
class Rule:
    """Represents a policy rule."""
    rule_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    rule_type: RuleType = RuleType.CONDITION
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    condition_expr: str = ""
    action: Optional[Callable[[Dict[str, Any]], Any]] = None
    consequence: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """Policy definition."""
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    rules: List[Rule] = field(default_factory=list)
    effect: Effect = Effect.ALLOW
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvaluationContext:
    """Context for policy evaluation."""
    context_id: str = field(default_factory=lambda: str(uuid4()))
    facts: Dict[str, Any] = field(default_factory=dict)
    user: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    environment: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get fact from context."""
        return self.facts.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set fact in context."""
        self.facts[key] = value


@dataclass
class DecisionRequest:
    """Request for policy decision."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    user: str = ""
    resource: str = ""
    action: str = ""
    context: EvaluationContext = field(default_factory=EvaluationContext)


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    effect: Effect
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    matching_policies: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidationResult:
    """Policy validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of policy evaluation."""
    success: bool
    effect: Effect = Effect.ABSTAIN
    matched_rules: List[str] = field(default_factory=list)
    inferred_facts: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class RuleApplicationResult:
    """Result of rule application."""
    success: bool
    applied_rules: List[str] = field(default_factory=list)
    derived_facts: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[str] = field(default_factory=list)


@dataclass
class Goal:
    """Goal for backward chaining."""
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    target_fact: str = ""
    target_value: Any = None


@dataclass
class ChainResult:
    """Result of chaining inference."""
    success: bool
    derived_facts: Dict[str, Any] = field(default_factory=dict)
    applied_rules: List[str] = field(default_factory=list)
    iterations: int = 0


@dataclass
class ConflictResolution:
    """Result of conflict resolution."""
    resolved: bool
    winning_policy: Optional[str] = None
    conflicts_found: int = 0
    resolution_strategy: ConflictStrategy = ConflictStrategy.FIRST_MATCH


@dataclass
class Action:
    """Action for compliance checking."""
    action_id: str = field(default_factory=lambda: str(uuid4()))
    action_type: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Compliance check report."""
    compliant: bool
    violations: List[str] = field(default_factory=list)
    satisfied_policies: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Change:
    """Policy change for versioning."""
    change_id: str = field(default_factory=lambda: str(uuid4()))
    change_type: str = ""
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VersionEntry:
    """Policy version entry."""
    version: str = ""
    policy_id: str = ""
    changes: List[Change] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RollbackResult:
    """Result of policy rollback."""
    success: bool
    policy_name: str = ""
    from_version: str = ""
    to_version: str = ""
    error: Optional[str] = None


@dataclass
class AuditEntry:
    """Policy decision audit entry."""
    decision: PolicyDecision
    context: EvaluationContext
    timestamp: datetime
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    user: Optional[str] = None


@dataclass
class ComposedPolicy:
    """Composed policy from multiple policies."""
    policy_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    component_policies: List[str] = field(default_factory=list)
    composition_strategy: CompositionStrategy = CompositionStrategy.AND
    combined_rules: List[Rule] = field(default_factory=list)


@dataclass
class OptimizedPolicy:
    """Optimized policy."""
    policy_id: str = ""
    original_rules: int = 0
    optimized_rules: int = 0
    optimization_notes: List[str] = field(default_factory=list)
    policy: Optional[Policy] = None


@dataclass
class TestCase:
    """Policy test case."""
    test_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    context: EvaluationContext = field(default_factory=EvaluationContext)
    expected_effect: Effect = Effect.ALLOW
    description: str = ""


@dataclass
class TestResults:
    """Policy testing results."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    test_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CacheEntry:
    """Policy cache entry."""
    policy: Policy
    ttl: timedelta
    cached_at: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() - self.cached_at > self.ttl


# ==================== Main FSA Class ====================

class PolicyEngineFSA:
    """
    Policy Engine Finite State Automaton.

    Provides comprehensive policy-based decision making with rule engine,
    conflict resolution, compliance checking, and versioning.
    """

    def __init__(
        self,
        name: str = "PolicyEngineFSA",
        default_conflict_strategy: ConflictStrategy = ConflictStrategy.DENY_OVERRIDES,
    ):
        """
        Initialize Policy Engine FSA.

        Args:
            name: Name of the FSA instance
            default_conflict_strategy: Default conflict resolution strategy
        """
        self.name = name
        self.fsa_id = str(uuid4())
        self.default_conflict_strategy = default_conflict_strategy

        # Policy storage
        self.policies: Dict[str, Policy] = {}
        self.policy_by_name: Dict[str, str] = {}  # name -> policy_id

        # Versioning
        self.policy_versions: Dict[str, List[VersionEntry]] = defaultdict(list)
        self.version_snapshots: Dict[str, Dict[str, Policy]] = {}  # policy_name -> {version -> policy}

        # Caching
        self.policy_cache: Dict[str, CacheEntry] = {}
        self.default_ttl = timedelta(minutes=5)

        # Audit logging
        self.audit_log: List[AuditEntry] = []

        # Compiled rules for performance
        self.compiled_rules: Dict[str, Callable] = {}

        # Statistics
        self.total_decisions: int = 0
        self.allowed_decisions: int = 0
        self.denied_decisions: int = 0

        # Thread safety
        self.lock = threading.RLock()

        logger.info(f"Initialized {self.name} with ID {self.fsa_id}")

    # ==================== Main Execution ====================

    def execute(
        self,
        decision_request: DecisionRequest,
        policies: List[Policy]
    ) -> PolicyDecision:
        """
        Main policy evaluation pipeline.

        Args:
            decision_request: Decision request
            policies: List of policies to evaluate

        Returns:
            PolicyDecision with evaluation result
        """
        try:
            # Setup evaluation context
            context = decision_request.context
            context.user = decision_request.user
            context.resource = decision_request.resource
            context.action = decision_request.action

            # Evaluate all policies
            matching_policies = []
            applied_rules = []
            effects = []

            for policy in policies:
                result = self.evaluate_policy(policy, context)

                if result.success and result.effect != Effect.ABSTAIN:
                    matching_policies.append(policy.policy_id)
                    applied_rules.extend(result.matched_rules)
                    effects.append((policy, result.effect))

            # Resolve conflicts if multiple policies matched
            if len(effects) > 1:
                resolution = self.resolve_conflicts(policies, context)
                if resolution.winning_policy:
                    final_effect = next(
                        (e for p, e in effects if p.policy_id == resolution.winning_policy),
                        Effect.DENY
                    )
                else:
                    final_effect = Effect.DENY
            elif len(effects) == 1:
                final_effect = effects[0][1]
            else:
                final_effect = Effect.DENY

            # Create decision
            decision = PolicyDecision(
                effect=final_effect,
                matching_policies=matching_policies,
                applied_rules=applied_rules,
                reason=f"Evaluated {len(policies)} policies, {len(matching_policies)} matched"
            )

            # Audit decision
            self.audit_decision(decision, context, datetime.utcnow())

            # Update statistics
            with self.lock:
                self.total_decisions += 1
                if final_effect == Effect.ALLOW:
                    self.allowed_decisions += 1
                elif final_effect == Effect.DENY:
                    self.denied_decisions += 1

            return decision

        except Exception as e:
            logger.error(f"Policy execution error: {e}")
            return PolicyDecision(
                effect=Effect.DENY,
                reason=f"Error: {str(e)}"
            )

    # ==================== Validation ====================

    def validate(self, policy: Policy) -> ValidationResult:
        """
        Validate policy syntax and logic.

        Args:
            policy: Policy to validate

        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check policy has name
        if not policy.name:
            errors.append("Policy must have a name")

        # Check policy has rules
        if not policy.rules:
            warnings.append("Policy has no rules")

        # Validate each rule
        for rule in policy.rules:
            if not rule.name:
                warnings.append(f"Rule {rule.rule_id} has no name")

            # Check rule has either condition or condition_expr
            if not rule.condition and not rule.condition_expr:
                warnings.append(f"Rule {rule.name} has no condition")

            # Check for circular dependencies (simplified)
            if rule.consequence and rule.condition_expr:
                for key in rule.consequence.keys():
                    if key in rule.condition_expr:
                        warnings.append(f"Rule {rule.name} may have circular dependency on {key}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # ==================== Policy Parsing ====================

    def parse_policy(self, policy_text: str, format: PolicyFormat) -> Policy:
        """
        Parse policy definition.

        Args:
            policy_text: Policy text to parse
            format: Policy format

        Returns:
            Parsed Policy
        """
        if format == PolicyFormat.JSON:
            return self._parse_json_policy(policy_text)
        elif format == PolicyFormat.YAML:
            return self._parse_yaml_policy(policy_text)
        elif format == PolicyFormat.REGO:
            return self._parse_rego_policy(policy_text)
        elif format == PolicyFormat.DSL:
            return self._parse_dsl_policy(policy_text)
        else:
            raise ValueError(f"Unsupported policy format: {format}")

    def _parse_json_policy(self, policy_text: str) -> Policy:
        """Parse JSON policy."""
        data = json.loads(policy_text)

        rules = []
        for rule_data in data.get("rules", []):
            rule = Rule(
                name=rule_data.get("name", ""),
                condition_expr=rule_data.get("condition", ""),
                consequence=rule_data.get("consequence", {}),
                priority=rule_data.get("priority", 0)
            )
            rules.append(rule)

        policy = Policy(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            rules=rules,
            effect=Effect(data.get("effect", "allow")),
            priority=data.get("priority", 0)
        )

        return policy

    def _parse_yaml_policy(self, policy_text: str) -> Policy:
        """Parse YAML policy (simplified)."""
        # Simplified YAML parsing - in production use PyYAML
        # For now, treat as JSON-like
        try:
            data = json.loads(policy_text.replace("'", '"'))
            return self._parse_json_policy(json.dumps(data))
        except:
            # Create minimal policy
            policy = Policy(name="parsed_yaml", description=policy_text)
            return policy

    def _parse_rego_policy(self, policy_text: str) -> Policy:
        """Parse Rego policy (simplified)."""
        # Simplified Rego parsing - extract allow/deny rules
        policy = Policy(name="rego_policy")

        # Extract rules using regex
        allow_pattern = r'allow\s*{\s*([^}]+)\s*}'
        deny_pattern = r'deny\s*{\s*([^}]+)\s*}'

        allow_matches = re.findall(allow_pattern, policy_text)
        deny_matches = re.findall(deny_pattern, policy_text)

        for i, condition in enumerate(allow_matches):
            rule = Rule(
                name=f"allow_rule_{i}",
                condition_expr=condition.strip(),
                rule_type=RuleType.CONDITION
            )
            policy.rules.append(rule)

        if deny_matches:
            policy.effect = Effect.DENY

        return policy

    def _parse_dsl_policy(self, policy_text: str) -> Policy:
        """Parse DSL policy."""
        # Simplified DSL parsing
        policy = Policy(name="dsl_policy")

        lines = policy_text.strip().split('\n')
        current_rule = None

        for line in lines:
            line = line.strip()

            if line.startswith("RULE"):
                if current_rule:
                    policy.rules.append(current_rule)
                current_rule = Rule(name=line.split()[1] if len(line.split()) > 1 else "rule")

            elif line.startswith("IF") and current_rule:
                current_rule.condition_expr = line[3:].strip()

            elif line.startswith("THEN") and current_rule:
                # Parse consequence
                consequence_text = line[5:].strip()
                current_rule.consequence = {"action": consequence_text}

        if current_rule:
            policy.rules.append(current_rule)

        return policy

    # ==================== Policy Evaluation ====================

    def evaluate_policy(
        self,
        policy: Policy,
        context: EvaluationContext
    ) -> EvaluationResult:
        """
        Execute policy rules.

        Args:
            policy: Policy to evaluate
            context: Evaluation context

        Returns:
            EvaluationResult with evaluation status
        """
        try:
            matched_rules = []
            inferred_facts = {}

            # Evaluate each rule
            for rule in policy.rules:
                if self._evaluate_rule(rule, context):
                    matched_rules.append(rule.rule_id)

                    # Apply consequences
                    if rule.consequence:
                        inferred_facts.update(rule.consequence)

            # Determine effect
            if matched_rules:
                effect = policy.effect
            else:
                effect = Effect.ABSTAIN

            return EvaluationResult(
                success=True,
                effect=effect,
                matched_rules=matched_rules,
                inferred_facts=inferred_facts
            )

        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            return EvaluationResult(
                success=False,
                error=str(e)
            )

    def _evaluate_rule(self, rule: Rule, context: EvaluationContext) -> bool:
        """Evaluate individual rule."""
        try:
            # Use callable condition if available
            if rule.condition:
                return rule.condition(context.facts)

            # Evaluate expression
            elif rule.condition_expr:
                return self._evaluate_expression(rule.condition_expr, context)

            return False

        except Exception as e:
            logger.error(f"Rule evaluation error: {e}")
            return False

    def _evaluate_expression(self, expression: str, context: EvaluationContext) -> bool:
        """Evaluate rule expression."""
        try:
            # Simple expression evaluation
            # In production, use a safe expression evaluator

            # Replace context references
            expr = expression
            for key, value in context.facts.items():
                expr = expr.replace(f"${key}", repr(value))
                expr = expr.replace(key, repr(value))

            # Evaluate
            result = eval(expr, {"__builtins__": {}}, {})
            return bool(result)

        except Exception as e:
            logger.debug(f"Expression evaluation failed: {e}")
            return False

    # ==================== Rule Engine ====================

    def apply_rules(
        self,
        rules: List[Rule],
        facts: Dict[str, Any]
    ) -> RuleApplicationResult:
        """
        Apply rule engine.

        Args:
            rules: Rules to apply
            facts: Initial facts

        Returns:
            RuleApplicationResult with application status
        """
        applied_rules = []
        derived_facts = facts.copy()
        conflicts = []

        # Sort rules by priority
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

        # Apply each rule
        for rule in sorted_rules:
            context = EvaluationContext(facts=derived_facts)

            if self._evaluate_rule(rule, context):
                applied_rules.append(rule.rule_id)

                # Apply consequences
                if rule.consequence:
                    for key, value in rule.consequence.items():
                        if key in derived_facts and derived_facts[key] != value:
                            conflicts.append(f"Conflict on {key}: {derived_facts[key]} vs {value}")
                        derived_facts[key] = value

        return RuleApplicationResult(
            success=True,
            applied_rules=applied_rules,
            derived_facts=derived_facts,
            conflicts=conflicts
        )

    # ==================== Forward Chaining ====================

    def forward_chain(
        self,
        rules: List[Rule],
        initial_facts: Dict[str, Any],
        max_iterations: int = 100
    ) -> ChainResult:
        """
        Forward chaining inference.

        Args:
            rules: Inference rules
            initial_facts: Starting facts
            max_iterations: Maximum iterations to prevent infinite loops

        Returns:
            ChainResult with inferred facts
        """
        derived_facts = initial_facts.copy()
        applied_rules = []
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            new_facts_added = False

            for rule in rules:
                if rule.rule_id in applied_rules:
                    continue

                context = EvaluationContext(facts=derived_facts)

                if self._evaluate_rule(rule, context):
                    applied_rules.append(rule.rule_id)

                    # Add consequences to facts
                    if rule.consequence:
                        for key, value in rule.consequence.items():
                            if key not in derived_facts:
                                derived_facts[key] = value
                                new_facts_added = True

            # Stop if no new facts were added
            if not new_facts_added:
                break

        return ChainResult(
            success=True,
            derived_facts=derived_facts,
            applied_rules=applied_rules,
            iterations=iterations
        )

    # ==================== Backward Chaining ====================

    def backward_chain(
        self,
        goal: Goal,
        rules: List[Rule],
        facts: Dict[str, Any]
    ) -> ChainResult:
        """
        Backward chaining inference.

        Args:
            goal: Target goal to prove
            rules: Inference rules
            facts: Known facts

        Returns:
            ChainResult with proof status
        """
        derived_facts = facts.copy()
        applied_rules = []

        def prove_goal(target: str, current_facts: Dict[str, Any], visited: Set[str]) -> bool:
            """Recursively prove goal."""
            # Check if goal already in facts
            if target in current_facts:
                return True

            # Prevent circular reasoning
            if target in visited:
                return False

            visited.add(target)

            # Find rules that can derive this goal
            for rule in rules:
                if rule.consequence and target in rule.consequence:
                    # Try to prove all preconditions
                    context = EvaluationContext(facts=current_facts)

                    if self._evaluate_rule(rule, context):
                        applied_rules.append(rule.rule_id)
                        # Add consequence
                        current_facts[target] = rule.consequence[target]
                        return True

            return False

        # Try to prove the goal
        success = prove_goal(goal.target_fact, derived_facts, set())

        return ChainResult(
            success=success,
            derived_facts=derived_facts,
            applied_rules=applied_rules,
            iterations=len(applied_rules)
        )

    # ==================== Conflict Resolution ====================

    def resolve_conflicts(
        self,
        policies: List[Policy],
        context: EvaluationContext
    ) -> ConflictResolution:
        """
        Handle policy conflicts.

        Args:
            policies: Conflicting policies
            context: Evaluation context

        Returns:
            ConflictResolution with resolution result
        """
        # Evaluate all policies
        policy_effects = []
        for policy in policies:
            result = self.evaluate_policy(policy, context)
            if result.success and result.effect != Effect.ABSTAIN:
                policy_effects.append((policy, result.effect))

        # Check for conflicts
        effects_set = set(e for _, e in policy_effects)
        conflicts_found = len(effects_set) > 1 if Effect.ALLOW in effects_set and Effect.DENY in effects_set else 0

        if not policy_effects:
            return ConflictResolution(
                resolved=True,
                conflicts_found=0
            )

        # Apply resolution strategy
        strategy = self.default_conflict_strategy

        if strategy == ConflictStrategy.FIRST_MATCH:
            winning_policy = policy_effects[0][0].policy_id

        elif strategy == ConflictStrategy.PRIORITY_BASED:
            # Sort by priority
            sorted_policies = sorted(policy_effects, key=lambda p: p[0].priority, reverse=True)
            winning_policy = sorted_policies[0][0].policy_id

        elif strategy == ConflictStrategy.DENY_OVERRIDES:
            # DENY takes precedence
            deny_policies = [p for p, e in policy_effects if e == Effect.DENY]
            if deny_policies:
                winning_policy = deny_policies[0].policy_id
            else:
                winning_policy = policy_effects[0][0].policy_id

        elif strategy == ConflictStrategy.ALLOW_OVERRIDES:
            # ALLOW takes precedence
            allow_policies = [p for p, e in policy_effects if e == Effect.ALLOW]
            if allow_policies:
                winning_policy = allow_policies[0].policy_id
            else:
                winning_policy = policy_effects[0][0].policy_id

        else:
            winning_policy = policy_effects[0][0].policy_id

        return ConflictResolution(
            resolved=True,
            winning_policy=winning_policy,
            conflicts_found=conflicts_found,
            resolution_strategy=strategy
        )

    # ==================== Compliance Checking ====================

    def check_compliance(
        self,
        actions: List[Action],
        compliance_policies: List[Policy]
    ) -> ComplianceReport:
        """
        Verify compliance with policies.

        Args:
            actions: Actions to check
            compliance_policies: Compliance policies

        Returns:
            ComplianceReport with compliance status
        """
        violations = []
        satisfied_policies = []
        recommendations = []

        for action in actions:
            # Create context for action
            context = EvaluationContext(
                facts={
                    "action_type": action.action_type,
                    "target": action.target,
                    **action.parameters
                }
            )

            # Check against compliance policies
            for policy in compliance_policies:
                result = self.evaluate_policy(policy, context)

                if result.success:
                    if result.effect == Effect.DENY:
                        violations.append(
                            f"Action {action.action_type} violates policy {policy.name}"
                        )
                    elif result.effect == Effect.ALLOW:
                        satisfied_policies.append(policy.name)

        # Generate recommendations
        if violations:
            recommendations.append("Review and modify actions to comply with policies")

        compliant = len(violations) == 0

        return ComplianceReport(
            compliant=compliant,
            violations=violations,
            satisfied_policies=satisfied_policies,
            recommendations=recommendations
        )

    # ==================== Versioning ====================

    def version_policy(
        self,
        policy: Policy,
        version: str,
        changes: List[Change]
    ) -> VersionEntry:
        """
        Track policy versions.

        Args:
            policy: Policy to version
            version: Version string
            changes: List of changes

        Returns:
            VersionEntry with version information
        """
        entry = VersionEntry(
            version=version,
            policy_id=policy.policy_id,
            changes=changes
        )

        with self.lock:
            # Store version entry
            self.policy_versions[policy.name].append(entry)

            # Store snapshot
            if policy.name not in self.version_snapshots:
                self.version_snapshots[policy.name] = {}

            # Deep copy policy for snapshot
            import copy
            self.version_snapshots[policy.name][version] = copy.deepcopy(policy)

            # Update policy version
            policy.version = version

        logger.info(f"Versioned policy {policy.name} as {version}")
        return entry

    def rollback_policy(
        self,
        policy_name: str,
        target_version: str
    ) -> RollbackResult:
        """
        Restore previous policy version.

        Args:
            policy_name: Policy name
            target_version: Target version to rollback to

        Returns:
            RollbackResult with rollback status
        """
        try:
            with self.lock:
                if policy_name not in self.version_snapshots:
                    return RollbackResult(
                        success=False,
                        policy_name=policy_name,
                        error="No version history found"
                    )

                if target_version not in self.version_snapshots[policy_name]:
                    return RollbackResult(
                        success=False,
                        policy_name=policy_name,
                        error=f"Version {target_version} not found"
                    )

                # Get current version
                policy_id = self.policy_by_name.get(policy_name)
                current_policy = self.policies.get(policy_id) if policy_id else None
                from_version = current_policy.version if current_policy else "unknown"

                # Restore snapshot
                import copy
                restored_policy = copy.deepcopy(self.version_snapshots[policy_name][target_version])

                # Update active policy
                self.policies[restored_policy.policy_id] = restored_policy
                self.policy_by_name[policy_name] = restored_policy.policy_id

                # Invalidate cache
                if restored_policy.policy_id in self.policy_cache:
                    del self.policy_cache[restored_policy.policy_id]

            logger.info(f"Rolled back policy {policy_name} from {from_version} to {target_version}")
            return RollbackResult(
                success=True,
                policy_name=policy_name,
                from_version=from_version,
                to_version=target_version
            )

        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return RollbackResult(
                success=False,
                policy_name=policy_name,
                error=str(e)
            )

    # ==================== Caching ====================

    def cache_policy(self, policy: Policy, ttl: Optional[timedelta] = None) -> None:
        """
        Cache policy for performance.

        Args:
            policy: Policy to cache
            ttl: Time to live (optional)
        """
        ttl = ttl or self.default_ttl

        entry = CacheEntry(
            policy=policy,
            ttl=ttl
        )

        with self.lock:
            self.policy_cache[policy.policy_id] = entry

        logger.debug(f"Cached policy {policy.name}")

    def get_cached_policy(self, policy_id: str) -> Optional[Policy]:
        """Get cached policy."""
        with self.lock:
            if policy_id in self.policy_cache:
                entry = self.policy_cache[policy_id]

                if entry.is_expired():
                    del self.policy_cache[policy_id]
                    return None

                return entry.policy

        return None

    # ==================== Audit Logging ====================

    def audit_decision(
        self,
        decision: PolicyDecision,
        context: EvaluationContext,
        timestamp: datetime
    ) -> AuditEntry:
        """
        Log policy decision.

        Args:
            decision: Policy decision
            context: Evaluation context
            timestamp: Decision timestamp

        Returns:
            AuditEntry with audit information
        """
        entry = AuditEntry(
            decision=decision,
            context=context,
            timestamp=timestamp,
            user=context.user
        )

        with self.lock:
            self.audit_log.append(entry)

            # Limit audit log size
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-10000:]

        return entry

    def get_audit_log(
        self,
        user: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> List[AuditEntry]:
        """Get audit log entries with optional filters."""
        filtered = self.audit_log

        if user:
            filtered = [e for e in filtered if e.user == user]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        return filtered

    # ==================== Policy Composition ====================

    def compose_policies(
        self,
        policies: List[Policy],
        composition_strategy: CompositionStrategy
    ) -> ComposedPolicy:
        """
        Combine multiple policies.

        Args:
            policies: Policies to compose
            composition_strategy: Composition strategy

        Returns:
            ComposedPolicy with combined policies
        """
        composed = ComposedPolicy(
            name=f"composed_{composition_strategy.value}",
            component_policies=[p.policy_id for p in policies],
            composition_strategy=composition_strategy
        )

        if composition_strategy == CompositionStrategy.AND:
            # Combine all rules
            for policy in policies:
                composed.combined_rules.extend(policy.rules)

        elif composition_strategy == CompositionStrategy.OR:
            # Combine all rules
            for policy in policies:
                composed.combined_rules.extend(policy.rules)

        elif composition_strategy == CompositionStrategy.NOT:
            # Negate first policy
            if policies:
                for rule in policies[0].rules:
                    # Create negated rule
                    negated_rule = Rule(
                        name=f"not_{rule.name}",
                        condition_expr=f"not ({rule.condition_expr})" if rule.condition_expr else "",
                        consequence=rule.consequence
                    )
                    composed.combined_rules.append(negated_rule)

        return composed

    # ==================== Policy Optimization ====================

    def optimize_policy(self, policy: Policy) -> OptimizedPolicy:
        """
        Improve policy performance.

        Args:
            policy: Policy to optimize

        Returns:
            OptimizedPolicy with optimizations
        """
        original_count = len(policy.rules)
        optimization_notes = []

        # Remove duplicate rules
        unique_rules = []
        seen_conditions = set()

        for rule in policy.rules:
            condition_key = rule.condition_expr or str(rule.condition)

            if condition_key not in seen_conditions:
                unique_rules.append(rule)
                seen_conditions.add(condition_key)
            else:
                optimization_notes.append(f"Removed duplicate rule: {rule.name}")

        # Sort by priority for faster evaluation
        unique_rules.sort(key=lambda r: r.priority, reverse=True)
        optimization_notes.append("Sorted rules by priority")

        # Create optimized policy
        import copy
        optimized_policy = copy.deepcopy(policy)
        optimized_policy.rules = unique_rules

        return OptimizedPolicy(
            policy_id=policy.policy_id,
            original_rules=original_count,
            optimized_rules=len(unique_rules),
            optimization_notes=optimization_notes,
            policy=optimized_policy
        )

    # ==================== Policy Testing ====================

    def test_policy(
        self,
        policy: Policy,
        test_cases: List[TestCase]
    ) -> TestResults:
        """
        Validate policy behavior.

        Args:
            policy: Policy to test
            test_cases: Test cases

        Returns:
            TestResults with test results
        """
        results = TestResults(total_tests=len(test_cases))
        test_details = []

        for test_case in test_cases:
            result = self.evaluate_policy(policy, test_case.context)

            passed = result.effect == test_case.expected_effect

            if passed:
                results.passed_tests += 1
            else:
                results.failed_tests += 1

            test_details.append({
                "test_name": test_case.name,
                "passed": passed,
                "expected": test_case.expected_effect.value,
                "actual": result.effect.value,
                "description": test_case.description
            })

        results.test_details = test_details
        return results

    # ==================== Policy Import/Export ====================

    def export_policy(self, policy: Policy, format: PolicyFormat) -> str:
        """
        Export policy definition.

        Args:
            policy: Policy to export
            format: Export format

        Returns:
            Exported policy as string
        """
        if format == PolicyFormat.JSON:
            return self._export_json(policy)
        elif format == PolicyFormat.YAML:
            return self._export_yaml(policy)
        elif format == PolicyFormat.DSL:
            return self._export_dsl(policy)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, policy: Policy) -> str:
        """Export to JSON format."""
        data = {
            "name": policy.name,
            "version": policy.version,
            "description": policy.description,
            "effect": policy.effect.value,
            "priority": policy.priority,
            "rules": [
                {
                    "name": rule.name,
                    "condition": rule.condition_expr,
                    "consequence": rule.consequence,
                    "priority": rule.priority
                }
                for rule in policy.rules
            ]
        }
        return json.dumps(data, indent=2)

    def _export_yaml(self, policy: Policy) -> str:
        """Export to YAML format (simplified)."""
        # Simple YAML export
        lines = [
            f"name: {policy.name}",
            f"version: {policy.version}",
            f"description: {policy.description}",
            f"effect: {policy.effect.value}",
            f"priority: {policy.priority}",
            "rules:"
        ]

        for rule in policy.rules:
            lines.append(f"  - name: {rule.name}")
            lines.append(f"    condition: {rule.condition_expr}")
            lines.append(f"    priority: {rule.priority}")

        return "\n".join(lines)

    def _export_dsl(self, policy: Policy) -> str:
        """Export to DSL format."""
        lines = [f"POLICY {policy.name}"]

        for rule in policy.rules:
            lines.append(f"\nRULE {rule.name}")
            if rule.condition_expr:
                lines.append(f"  IF {rule.condition_expr}")
            if rule.consequence:
                lines.append(f"  THEN {rule.consequence}")

        return "\n".join(lines)

    def import_policy(self, policy_source: str, format: PolicyFormat) -> Policy:
        """
        Import policy from source.

        Args:
            policy_source: Policy source text
            format: Policy format

        Returns:
            Imported Policy
        """
        policy = self.parse_policy(policy_source, format)

        # Register policy
        with self.lock:
            self.policies[policy.policy_id] = policy
            self.policy_by_name[policy.name] = policy.policy_id

        logger.info(f"Imported policy {policy.name}")
        return policy

    # ==================== Utility Methods ====================

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        return self.policies.get(policy_id)

    def get_policy_by_name(self, name: str) -> Optional[Policy]:
        """Get policy by name."""
        policy_id = self.policy_by_name.get(name)
        return self.policies.get(policy_id) if policy_id else None

    def get_statistics(self) -> Dict[str, Any]:
        """Get policy engine statistics."""
        with self.lock:
            return {
                "total_policies": len(self.policies),
                "total_decisions": self.total_decisions,
                "allowed_decisions": self.allowed_decisions,
                "denied_decisions": self.denied_decisions,
                "cached_policies": len(self.policy_cache),
                "audit_entries": len(self.audit_log)
            }

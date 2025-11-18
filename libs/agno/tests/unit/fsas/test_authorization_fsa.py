"""
Comprehensive test suite for Authorization FSA.

This test suite provides complete coverage of the Authorization FSA including:
- RBAC (Role-Based Access Control)
- ABAC (Attribute-Based Access Control)
- Permission management
- Policy evaluation
- Caching mechanisms
- Audit logging
- Multi-tenancy
- Session and token management
"""

import time
from datetime import datetime, timedelta
from typing import List

import pytest

from agno.fsas.infrastructure.authorization_fsa import (
    AuditAction,
    AuditEntry,
    AuditLogger,
    AuthorizationCache,
    AuthorizationContext,
    AuthorizationDecision,
    AuthorizationError,
    AuthorizationFSA,
    AuthorizationState,
    ConditionEvaluator,
    InvalidPolicyError,
    InvalidRoleError,
    Permission,
    PermissionDeniedError,
    PermissionType,
    Policy,
    PolicyEffect,
    PolicyEngine,
    PolicyRule,
    Principal,
    Resource,
    ResourceNotFoundError,
    ResourceType,
    Role,
    RoleManager,
    RoleType,
    TenantIsolationError,
    create_default_authorization_fsa,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_principal() -> Principal:
    """Create a sample principal for testing."""
    return Principal(
        id="user-123",
        type="user",
        tenant_id="tenant-1",
        attributes={
            "department": "engineering",
            "level": "senior",
            "location": "us-west",
        },
        roles=["developer"],
    )


@pytest.fixture
def sample_resource() -> Resource:
    """Create a sample resource for testing."""
    return Resource(
        id="resource-456",
        type=ResourceType.API,
        tenant_id="tenant-1",
        owner_id="user-123",
        attributes={
            "environment": "production",
            "sensitivity": "high",
        },
        tags=["api", "critical"],
    )


@pytest.fixture
def sample_permission() -> Permission:
    """Create a sample permission for testing."""
    return Permission(
        name="api:read",
        resource_type=ResourceType.API,
        action=PermissionType.READ,
        resource_pattern="resource-*",
        tenant_id="tenant-1",
    )


@pytest.fixture
def sample_role() -> Role:
    """Create a sample role for testing."""
    return Role(
        name="developer",
        type=RoleType.CUSTOM,
        tenant_id="tenant-1",
        description="Developer role",
    )


@pytest.fixture
def auth_fsa() -> AuthorizationFSA:
    """Create an AuthorizationFSA instance for testing."""
    return AuthorizationFSA(
        cache_ttl=300.0,
        cache_enabled=True,
        audit_enabled=True,
    )


# ============================================================================
# Test Principal Model
# ============================================================================


class TestPrincipal:
    """Test cases for Principal model."""

    def test_principal_creation(self, sample_principal):
        """Test principal creation with all attributes."""
        assert sample_principal.id == "user-123"
        assert sample_principal.type == "user"
        assert sample_principal.tenant_id == "tenant-1"
        assert sample_principal.attributes["department"] == "engineering"
        assert "developer" in sample_principal.roles

    def test_principal_has_role(self, sample_principal):
        """Test checking if principal has a role."""
        assert sample_principal.has_role("developer")
        assert not sample_principal.has_role("admin")

    def test_principal_get_attribute(self, sample_principal):
        """Test getting principal attributes."""
        assert sample_principal.get_attribute("department") == "engineering"
        assert sample_principal.get_attribute("nonexistent", "default") == "default"

    def test_principal_without_tenant(self):
        """Test creating principal without tenant."""
        principal = Principal(id="global-user", type="service")
        assert principal.tenant_id is None
        assert principal.type == "service"


# ============================================================================
# Test Resource Model
# ============================================================================


class TestResource:
    """Test cases for Resource model."""

    def test_resource_creation(self, sample_resource):
        """Test resource creation with all attributes."""
        assert sample_resource.id == "resource-456"
        assert sample_resource.type == ResourceType.API
        assert sample_resource.tenant_id == "tenant-1"
        assert sample_resource.owner_id == "user-123"

    def test_resource_get_attribute(self, sample_resource):
        """Test getting resource attributes."""
        assert sample_resource.get_attribute("environment") == "production"
        assert sample_resource.get_attribute("missing") is None

    def test_resource_has_tag(self, sample_resource):
        """Test checking resource tags."""
        assert sample_resource.has_tag("api")
        assert sample_resource.has_tag("critical")
        assert not sample_resource.has_tag("deprecated")


# ============================================================================
# Test Permission Model
# ============================================================================


class TestPermission:
    """Test cases for Permission model."""

    def test_permission_creation(self, sample_permission):
        """Test permission creation."""
        assert sample_permission.name == "api:read"
        assert sample_permission.resource_type == ResourceType.API
        assert sample_permission.action == PermissionType.READ
        assert sample_permission.resource_pattern == "resource-*"

    def test_permission_matches_resource(self, sample_permission):
        """Test resource pattern matching."""
        assert sample_permission.matches_resource("resource-123")
        assert sample_permission.matches_resource("resource-abc")
        assert not sample_permission.matches_resource("other-123")

    def test_permission_wildcard_pattern(self):
        """Test wildcard permission pattern."""
        permission = Permission(
            name="all:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
        )
        assert permission.matches_resource("anything")
        assert permission.matches_resource("resource-123")

    def test_permission_expiration(self):
        """Test permission expiration."""
        # Non-expiring permission
        perm1 = Permission(
            name="test:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
        )
        assert not perm1.is_expired()

        # Expired permission
        perm2 = Permission(
            name="test:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert perm2.is_expired()

        # Future expiration
        perm3 = Permission(
            name="test:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert not perm3.is_expired()


# ============================================================================
# Test Role Model
# ============================================================================


class TestRole:
    """Test cases for Role model."""

    def test_role_creation(self, sample_role):
        """Test role creation."""
        assert sample_role.name == "developer"
        assert sample_role.type == RoleType.CUSTOM
        assert sample_role.tenant_id == "tenant-1"

    def test_role_name_validation(self):
        """Test role name validation."""
        # Valid names
        Role(name="valid-role_123", type=RoleType.CUSTOM)
        Role(name="system.admin", type=RoleType.SYSTEM)

        # Invalid names
        with pytest.raises(ValueError):
            Role(name="invalid role!", type=RoleType.CUSTOM)

        with pytest.raises(ValueError):
            Role(name="", type=RoleType.CUSTOM)

    def test_role_with_permissions(self):
        """Test role with permissions."""
        permission = Permission(
            name="test:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
        )
        role = Role(
            name="test-role",
            type=RoleType.CUSTOM,
            permissions=[permission],
        )
        assert len(role.permissions) == 1
        assert role.permissions[0].name == "test:read"

    def test_role_hierarchy(self):
        """Test role parent hierarchy."""
        role = Role(
            name="senior-dev",
            type=RoleType.CUSTOM,
            parent_roles=["developer", "code-reviewer"],
        )
        assert "developer" in role.parent_roles
        assert "code-reviewer" in role.parent_roles


# ============================================================================
# Test Policy Models
# ============================================================================


class TestPolicyRule:
    """Test cases for PolicyRule model."""

    def test_policy_rule_creation(self):
        """Test policy rule creation."""
        rule = PolicyRule(
            name="allow-read",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            principal_conditions={"department": "engineering"},
        )
        assert rule.name == "allow-read"
        assert rule.effect == PolicyEffect.ALLOW
        assert PermissionType.READ in rule.actions

    def test_policy_rule_priority(self):
        """Test policy rule priority."""
        rule1 = PolicyRule(
            name="high-priority",
            effect=PolicyEffect.DENY,
            priority=1,
            actions=[PermissionType.DELETE],
        )
        rule2 = PolicyRule(
            name="low-priority",
            effect=PolicyEffect.ALLOW,
            priority=100,
            actions=[PermissionType.READ],
        )
        assert rule1.priority < rule2.priority


class TestPolicy:
    """Test cases for Policy model."""

    def test_policy_creation(self):
        """Test policy creation."""
        policy = Policy(
            name="test-policy",
            version="1.0",
            tenant_id="tenant-1",
            default_effect=PolicyEffect.DENY,
        )
        assert policy.name == "test-policy"
        assert policy.version == "1.0"
        assert policy.default_effect == PolicyEffect.DENY

    def test_policy_get_applicable_rules(self):
        """Test getting applicable policy rules."""
        rule1 = PolicyRule(
            name="allow-read",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            enabled=True,
        )
        rule2 = PolicyRule(
            name="deny-delete",
            effect=PolicyEffect.DENY,
            actions=[PermissionType.DELETE],
            resource_types=[ResourceType.API],
            enabled=True,
        )
        rule3 = PolicyRule(
            name="disabled-rule",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            enabled=False,
        )

        policy = Policy(
            name="test-policy",
            rules=[rule1, rule2, rule3],
        )

        # Get rules for READ on API
        applicable = policy.get_applicable_rules(PermissionType.READ, ResourceType.API)
        assert len(applicable) == 1
        assert applicable[0].name == "allow-read"

        # Get rules for DELETE on API
        applicable = policy.get_applicable_rules(PermissionType.DELETE, ResourceType.API)
        assert len(applicable) == 1
        assert applicable[0].name == "deny-delete"


# ============================================================================
# Test Authorization Cache
# ============================================================================


class TestAuthorizationCache:
    """Test cases for AuthorizationCache."""

    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = AuthorizationCache(default_ttl=10.0)

        cache.set("value1", "key1", "key2")
        result = cache.get("key1", "key2")
        assert result == "value1"

    def test_cache_miss(self):
        """Test cache miss."""
        cache = AuthorizationCache()

        result = cache.get("nonexistent", "key")
        assert result is None

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = AuthorizationCache(default_ttl=0.1)  # 100ms TTL

        cache.set("value", "key")
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = AuthorizationCache()

        cache.set("value", "key1", "key2")
        assert cache.get("key1", "key2") == "value"

        cache.invalidate("key1", "key2")
        assert cache.get("key1", "key2") is None

    def test_cache_clear(self):
        """Test clearing entire cache."""
        cache = AuthorizationCache()

        cache.set("value1", "key1")
        cache.set("value2", "key2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = AuthorizationCache(max_size=100)

        cache.set("value1", "key1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_max_size(self):
        """Test cache size limit."""
        cache = AuthorizationCache(max_size=10)

        # Add more entries than max size
        for i in range(20):
            cache.set(f"value{i}", f"key{i}")

        stats = cache.get_stats()
        assert stats["size"] <= 10


# ============================================================================
# Test Condition Evaluator
# ============================================================================


class TestConditionEvaluator:
    """Test cases for ConditionEvaluator."""

    def test_evaluate_empty_conditions(self):
        """Test evaluating empty conditions."""
        result = ConditionEvaluator.evaluate({}, {"any": "context"})
        assert result is True

    def test_evaluate_equality(self):
        """Test equality condition."""
        conditions = {"department": "engineering"}
        context = {"department": "engineering"}
        assert ConditionEvaluator.evaluate(conditions, context)

        context = {"department": "sales"}
        assert not ConditionEvaluator.evaluate(conditions, context)

    def test_evaluate_operators(self):
        """Test various operators."""
        # eq operator
        assert ConditionEvaluator.evaluate(
            {"level": {"eq": 5}},
            {"level": 5},
        )

        # ne operator
        assert ConditionEvaluator.evaluate(
            {"level": {"ne": 3}},
            {"level": 5},
        )

        # in operator
        assert ConditionEvaluator.evaluate(
            {"role": {"in": ["admin", "developer"]}},
            {"role": "admin"},
        )

        # not_in operator
        assert ConditionEvaluator.evaluate(
            {"role": {"not_in": ["guest"]}},
            {"role": "admin"},
        )

        # gt operator
        assert ConditionEvaluator.evaluate(
            {"level": {"gt": 3}},
            {"level": 5},
        )

        # gte operator
        assert ConditionEvaluator.evaluate(
            {"level": {"gte": 5}},
            {"level": 5},
        )

        # lt operator
        assert ConditionEvaluator.evaluate(
            {"level": {"lt": 10}},
            {"level": 5},
        )

        # lte operator
        assert ConditionEvaluator.evaluate(
            {"level": {"lte": 5}},
            {"level": 5},
        )

    def test_evaluate_string_operators(self):
        """Test string-specific operators."""
        # contains operator
        assert ConditionEvaluator.evaluate(
            {"name": {"contains": "test"}},
            {"name": "test-resource"},
        )

        # matches operator (regex)
        assert ConditionEvaluator.evaluate(
            {"email": {"matches": r".*@example\.com$"}},
            {"email": "user@example.com"},
        )

    def test_evaluate_nested_keys(self):
        """Test nested key evaluation."""
        conditions = {"attributes.department": "engineering"}
        context = {
            "attributes": {
                "department": "engineering",
                "level": "senior",
            }
        }
        assert ConditionEvaluator.evaluate(conditions, context)

    def test_evaluate_exists_operator(self):
        """Test exists operator."""
        assert ConditionEvaluator.evaluate(
            {"email": {"exists": True}},
            {"email": "user@example.com"},
        )

        assert ConditionEvaluator.evaluate(
            {"email": {"exists": False}},
            {"name": "user"},
        )


# ============================================================================
# Test Role Manager
# ============================================================================


class TestRoleManager:
    """Test cases for RoleManager."""

    def test_initialization_with_system_roles(self):
        """Test that system roles are initialized."""
        manager = RoleManager()
        roles = manager.list_roles()

        role_names = [r.name for r in roles]
        assert "system:admin" in role_names
        assert "system:user" in role_names

    def test_add_role(self):
        """Test adding a role."""
        manager = RoleManager()
        role = Role(name="custom-role", type=RoleType.CUSTOM)

        manager.add_role(role)
        retrieved = manager.get_role("custom-role")
        assert retrieved is not None
        assert retrieved.name == "custom-role"

    def test_add_duplicate_role(self):
        """Test adding duplicate role raises error."""
        manager = RoleManager()
        role = Role(name="duplicate", type=RoleType.CUSTOM)

        manager.add_role(role)
        with pytest.raises(InvalidRoleError):
            manager.add_role(role)

    def test_remove_role(self):
        """Test removing a role."""
        manager = RoleManager()
        role = Role(name="temp-role", type=RoleType.CUSTOM)

        manager.add_role(role)
        manager.remove_role("temp-role")

        assert manager.get_role("temp-role") is None

    def test_remove_system_role_fails(self):
        """Test that system roles cannot be removed."""
        manager = RoleManager()

        with pytest.raises(InvalidRoleError):
            manager.remove_role("system:admin")

    def test_role_hierarchy(self):
        """Test role hierarchy inheritance."""
        manager = RoleManager()

        # Create role hierarchy
        base = Role(name="base-role", type=RoleType.CUSTOM)
        manager.add_role(base)

        mid = Role(
            name="mid-role",
            type=RoleType.CUSTOM,
            parent_roles=["base-role"],
        )
        manager.add_role(mid)

        top = Role(
            name="top-role",
            type=RoleType.CUSTOM,
            parent_roles=["mid-role"],
        )
        manager.add_role(top)

        # Get effective roles
        effective = manager.get_effective_roles(["top-role"])
        assert "top-role" in effective
        assert "mid-role" in effective
        assert "base-role" in effective

    def test_get_effective_permissions(self):
        """Test getting effective permissions from roles."""
        manager = RoleManager()

        perm1 = Permission(
            name="read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
        )
        perm2 = Permission(
            name="write",
            resource_type=ResourceType.API,
            action=PermissionType.UPDATE,
        )

        role1 = Role(
            name="reader",
            type=RoleType.CUSTOM,
            permissions=[perm1],
        )
        role2 = Role(
            name="writer",
            type=RoleType.CUSTOM,
            permissions=[perm2],
            parent_roles=["reader"],
        )

        manager.add_role(role1)
        manager.add_role(role2)

        # Get effective permissions for writer (should include reader's permissions)
        permissions = manager.get_effective_permissions(["writer"])
        perm_names = [p.name for p in permissions]

        assert "read" in perm_names
        assert "write" in perm_names

    def test_add_permission_to_role(self):
        """Test adding permission to role."""
        manager = RoleManager()
        role = Role(name="test-role", type=RoleType.CUSTOM)
        manager.add_role(role)

        permission = Permission(
            name="new-perm",
            resource_type=ResourceType.API,
            action=PermissionType.EXECUTE,
        )

        manager.add_permission_to_role("test-role", permission)

        role = manager.get_role("test-role")
        assert len(role.permissions) == 1
        assert role.permissions[0].name == "new-perm"

    def test_remove_permission_from_role(self):
        """Test removing permission from role."""
        manager = RoleManager()

        permission = Permission(
            name="temp-perm",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
        )
        role = Role(
            name="test-role",
            type=RoleType.CUSTOM,
            permissions=[permission],
        )
        manager.add_role(role)

        manager.remove_permission_from_role("test-role", permission.id)

        role = manager.get_role("test-role")
        assert len(role.permissions) == 0


# ============================================================================
# Test Policy Engine
# ============================================================================


class TestPolicyEngine:
    """Test cases for PolicyEngine."""

    def test_add_policy(self):
        """Test adding a policy."""
        engine = PolicyEngine()
        policy = Policy(name="test-policy")

        engine.add_policy(policy)
        retrieved = engine.get_policy(policy.id)

        assert retrieved is not None
        assert retrieved.name == "test-policy"

    def test_remove_policy(self):
        """Test removing a policy."""
        engine = PolicyEngine()
        policy = Policy(name="test-policy")

        engine.add_policy(policy)
        engine.remove_policy(policy.id)

        assert engine.get_policy(policy.id) is None

    def test_list_policies(self):
        """Test listing policies."""
        engine = PolicyEngine()

        policy1 = Policy(name="policy1", tenant_id="tenant-1")
        policy2 = Policy(name="policy2", tenant_id="tenant-2")

        engine.add_policy(policy1)
        engine.add_policy(policy2)

        # List all
        all_policies = engine.list_policies()
        assert len(all_policies) == 2

        # List by tenant
        tenant1_policies = engine.list_policies(tenant_id="tenant-1")
        assert len(tenant1_policies) == 1
        assert tenant1_policies[0].name == "policy1"

    def test_evaluate_allow_rule(self):
        """Test policy evaluation with allow rule."""
        engine = PolicyEngine()

        rule = PolicyRule(
            name="allow-eng-read",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            principal_conditions={"department": "engineering"},
        )

        policy = Policy(
            name="test-policy",
            rules=[rule],
            default_effect=PolicyEffect.DENY,
        )

        engine.add_policy(policy)

        # Create context
        principal = Principal(
            id="user-1",
            tenant_id="tenant-1",
            attributes={"department": "engineering"},
        )
        resource = Resource(
            id="api-1",
            type=ResourceType.API,
            tenant_id="tenant-1",
        )
        context = AuthorizationContext(
            principal=principal,
            resource=resource,
            action=PermissionType.READ,
        )

        # Evaluate
        allowed, matched_rules, reason = engine.evaluate(context)
        assert allowed is True
        assert len(matched_rules) > 0

    def test_evaluate_deny_rule(self):
        """Test policy evaluation with deny rule."""
        engine = PolicyEngine()

        rule = PolicyRule(
            name="deny-delete",
            effect=PolicyEffect.DENY,
            actions=[PermissionType.DELETE],
            resource_types=[ResourceType.API],
            priority=1,
        )

        policy = Policy(
            name="test-policy",
            rules=[rule],
        )

        engine.add_policy(policy)

        principal = Principal(id="user-1", tenant_id="tenant-1")
        resource = Resource(id="api-1", type=ResourceType.API, tenant_id="tenant-1")
        context = AuthorizationContext(
            principal=principal,
            resource=resource,
            action=PermissionType.DELETE,
        )

        allowed, matched_rules, reason = engine.evaluate(context)
        assert allowed is False
        assert "Denied by policy rule" in reason

    def test_evaluate_rule_priority(self):
        """Test that rules are evaluated by priority."""
        engine = PolicyEngine()

        # High priority deny rule
        deny_rule = PolicyRule(
            name="deny-high-priority",
            effect=PolicyEffect.DENY,
            actions=[PermissionType.READ],
            priority=1,
        )

        # Low priority allow rule
        allow_rule = PolicyRule(
            name="allow-low-priority",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            priority=100,
        )

        policy = Policy(
            name="test-policy",
            rules=[allow_rule, deny_rule],  # Order doesn't matter
        )

        engine.add_policy(policy)

        principal = Principal(id="user-1", tenant_id="tenant-1")
        resource = Resource(id="api-1", type=ResourceType.API, tenant_id="tenant-1")
        context = AuthorizationContext(
            principal=principal,
            resource=resource,
            action=PermissionType.READ,
        )

        # Deny should win due to higher priority (lower number)
        allowed, matched_rules, reason = engine.evaluate(context)
        assert allowed is False


# ============================================================================
# Test Audit Logger
# ============================================================================


class TestAuditLogger:
    """Test cases for AuditLogger."""

    def test_log_entry(self):
        """Test logging an audit entry."""
        logger = AuditLogger()

        logger.log(
            action=AuditAction.ACCESS_GRANTED,
            principal_id="user-1",
            resource_id="resource-1",
            decision=True,
            reason="Authorized",
        )

        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].action == AuditAction.ACCESS_GRANTED
        assert entries[0].principal_id == "user-1"

    def test_get_entries_with_filters(self):
        """Test getting entries with filters."""
        logger = AuditLogger()

        logger.log(
            action=AuditAction.ACCESS_GRANTED,
            principal_id="user-1",
            resource_id="resource-1",
        )
        logger.log(
            action=AuditAction.ACCESS_DENIED,
            principal_id="user-2",
            resource_id="resource-2",
        )

        # Filter by principal
        entries = logger.get_entries(principal_id="user-1")
        assert len(entries) == 1
        assert entries[0].principal_id == "user-1"

        # Filter by action
        entries = logger.get_entries(action=AuditAction.ACCESS_DENIED)
        assert len(entries) == 1
        assert entries[0].action == AuditAction.ACCESS_DENIED

    def test_max_entries_limit(self):
        """Test that audit logger respects max entries limit."""
        logger = AuditLogger(max_entries=10)

        # Log more than max
        for i in range(20):
            logger.log(
                action=AuditAction.AUTHORIZATION_CHECK,
                principal_id=f"user-{i}",
            )

        entries = logger.get_entries(limit=100)
        assert len(entries) <= 10

    def test_clear_entries(self):
        """Test clearing audit entries."""
        logger = AuditLogger()

        logger.log(action=AuditAction.ACCESS_GRANTED, principal_id="user-1")
        logger.log(action=AuditAction.ACCESS_DENIED, principal_id="user-2")

        logger.clear()
        entries = logger.get_entries()
        assert len(entries) == 0


# ============================================================================
# Test Authorization FSA - Core Functionality
# ============================================================================


class TestAuthorizationFSACore:
    """Test cases for core AuthorizationFSA functionality."""

    def test_initialization(self):
        """Test FSA initialization."""
        fsa = AuthorizationFSA()
        assert fsa.state == AuthorizationState.INITIAL
        assert fsa._role_manager is not None
        assert fsa._policy_engine is not None

    def test_state_transition(self):
        """Test FSA state transitions."""
        fsa = AuthorizationFSA()

        fsa.transition_to(AuthorizationState.AUTHENTICATING)
        assert fsa.state == AuthorizationState.AUTHENTICATING

        fsa.transition_to(AuthorizationState.AUTHORIZING)
        assert fsa.state == AuthorizationState.AUTHORIZING

    def test_create_default_fsa(self):
        """Test creating default FSA."""
        fsa = create_default_authorization_fsa()
        assert isinstance(fsa, AuthorizationFSA)
        assert fsa._cache is not None
        assert fsa._audit_logger is not None


# ============================================================================
# Test Authorization FSA - Session Management
# ============================================================================


class TestAuthorizationFSASession:
    """Test cases for session management."""

    def test_register_session(self, auth_fsa, sample_principal):
        """Test registering a session."""
        session_id = auth_fsa.register_session(sample_principal)
        assert session_id is not None
        assert sample_principal.session_id == session_id

        retrieved = auth_fsa.get_principal_from_session(session_id)
        assert retrieved is not None
        assert retrieved.id == sample_principal.id

    def test_revoke_session(self, auth_fsa, sample_principal):
        """Test revoking a session."""
        session_id = auth_fsa.register_session(sample_principal)
        auth_fsa.revoke_session(session_id)

        retrieved = auth_fsa.get_principal_from_session(session_id)
        assert retrieved is None

    def test_register_token(self, auth_fsa, sample_principal):
        """Test registering a token."""
        token_id = "token-123"
        auth_fsa.register_token(sample_principal, token_id)

        retrieved = auth_fsa.get_principal_from_token(token_id)
        assert retrieved is not None
        assert retrieved.id == sample_principal.id
        assert retrieved.token_id == token_id

    def test_revoke_token(self, auth_fsa, sample_principal):
        """Test revoking a token."""
        token_id = "token-123"
        auth_fsa.register_token(sample_principal, token_id)
        auth_fsa.revoke_token(token_id)

        retrieved = auth_fsa.get_principal_from_token(token_id)
        assert retrieved is None


# ============================================================================
# Test Authorization FSA - Role Management
# ============================================================================


class TestAuthorizationFSARole:
    """Test cases for role management in FSA."""

    def test_create_role(self, auth_fsa):
        """Test creating a role."""
        role = Role(name="test-role", type=RoleType.CUSTOM)
        auth_fsa.create_role(role)

        # Verify role was created
        roles = auth_fsa._role_manager.list_roles()
        role_names = [r.name for r in roles]
        assert "test-role" in role_names

    def test_assign_role(self, auth_fsa, sample_principal):
        """Test assigning a role to principal."""
        role = Role(name="test-role", type=RoleType.CUSTOM)
        auth_fsa.create_role(role)

        auth_fsa.assign_role(sample_principal.id, "test-role")

        roles = auth_fsa.get_principal_roles(sample_principal.id)
        assert "test-role" in roles

    def test_revoke_role(self, auth_fsa, sample_principal):
        """Test revoking a role from principal."""
        role = Role(name="test-role", type=RoleType.CUSTOM)
        auth_fsa.create_role(role)

        auth_fsa.assign_role(sample_principal.id, "test-role")
        auth_fsa.revoke_role(sample_principal.id, "test-role")

        roles = auth_fsa.get_principal_roles(sample_principal.id)
        assert "test-role" not in roles

    def test_delete_role(self, auth_fsa):
        """Test deleting a role."""
        role = Role(name="temp-role", type=RoleType.CUSTOM)
        auth_fsa.create_role(role)
        auth_fsa.delete_role("temp-role")

        role = auth_fsa._role_manager.get_role("temp-role")
        assert role is None


# ============================================================================
# Test Authorization FSA - Permission Management
# ============================================================================


class TestAuthorizationFSAPermission:
    """Test cases for permission management in FSA."""

    def test_grant_permission(self, auth_fsa, sample_principal, sample_permission):
        """Test granting a permission to principal."""
        auth_fsa.grant_permission(sample_principal.id, sample_permission)

        permissions = auth_fsa.get_effective_permissions(sample_principal)
        perm_names = [p.name for p in permissions]
        assert sample_permission.name in perm_names

    def test_revoke_permission(self, auth_fsa, sample_principal, sample_permission):
        """Test revoking a permission from principal."""
        auth_fsa.grant_permission(sample_principal.id, sample_permission)
        auth_fsa.revoke_permission(sample_principal.id, sample_permission.id)

        permissions = auth_fsa.get_effective_permissions(sample_principal)
        perm_ids = [p.id for p in permissions]
        assert sample_permission.id not in perm_ids

    def test_get_effective_permissions_with_roles(self, auth_fsa, sample_principal):
        """Test getting effective permissions from roles."""
        # Create role with permission
        permission = Permission(
            name="role-perm",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
        )
        role = Role(
            name="test-role",
            type=RoleType.CUSTOM,
            permissions=[permission],
        )
        auth_fsa.create_role(role)

        # Assign role to principal
        auth_fsa.assign_role(sample_principal.id, "test-role")

        # Get effective permissions
        permissions = auth_fsa.get_effective_permissions(sample_principal)
        perm_names = [p.name for p in permissions]
        assert "role-perm" in perm_names


# ============================================================================
# Test Authorization FSA - Authorization
# ============================================================================


class TestAuthorizationFSAAuthorize:
    """Test cases for authorization decisions."""

    def test_authorize_with_permission(self, auth_fsa, sample_principal, sample_resource):
        """Test authorization with valid permission."""
        # Grant permission
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        auth_fsa.grant_permission(sample_principal.id, permission)

        # Authorize
        decision = auth_fsa.authorize(
            principal=sample_principal,
            resource=sample_resource,
            action=PermissionType.READ,
        )

        assert decision.allowed is True
        assert "RBAC" in decision.reason

    def test_authorize_without_permission(self, auth_fsa, sample_principal, sample_resource):
        """Test authorization without permission."""
        decision = auth_fsa.authorize(
            principal=sample_principal,
            resource=sample_resource,
            action=PermissionType.DELETE,
        )

        assert decision.allowed is False

    def test_authorize_with_role(self, auth_fsa, sample_principal, sample_resource):
        """Test authorization through role."""
        # Create role with permission
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        role = Role(
            name="reader",
            type=RoleType.CUSTOM,
            permissions=[permission],
        )
        auth_fsa.create_role(role)
        auth_fsa.assign_role(sample_principal.id, "reader")

        # Authorize
        decision = auth_fsa.authorize(
            principal=sample_principal,
            resource=sample_resource,
            action=PermissionType.READ,
        )

        assert decision.allowed is True

    def test_authorize_with_policy(self, auth_fsa, sample_principal, sample_resource):
        """Test authorization with ABAC policy."""
        # Create policy
        rule = PolicyRule(
            name="allow-eng-read",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            principal_conditions={"department": "engineering"},
        )
        policy = Policy(
            name="test-policy",
            tenant_id="tenant-1",
            rules=[rule],
        )
        auth_fsa.add_policy(policy)

        # Authorize
        decision = auth_fsa.authorize(
            principal=sample_principal,
            resource=sample_resource,
            action=PermissionType.READ,
        )

        assert decision.allowed is True
        assert "ABAC" in decision.reason

    def test_tenant_isolation(self, auth_fsa):
        """Test tenant isolation enforcement."""
        principal = Principal(id="user-1", tenant_id="tenant-1")
        resource = Resource(
            id="resource-1",
            type=ResourceType.API,
            tenant_id="tenant-2",
        )

        decision = auth_fsa.authorize(
            principal=principal,
            resource=resource,
            action=PermissionType.READ,
        )

        assert decision.allowed is False
        assert "tenant isolation" in decision.reason.lower()

    def test_check_permission(self, auth_fsa, sample_principal, sample_resource):
        """Test check_permission method."""
        # Grant permission
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        auth_fsa.grant_permission(sample_principal.id, permission)

        # Check permission
        allowed = auth_fsa.check_permission(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )
        assert allowed is True

    def test_check_permission_with_raise(self, auth_fsa, sample_principal, sample_resource):
        """Test check_permission with raise_on_deny."""
        with pytest.raises(PermissionDeniedError):
            auth_fsa.check_permission(
                sample_principal,
                sample_resource,
                PermissionType.DELETE,
                raise_on_deny=True,
            )

    def test_require_permission_decorator(self, auth_fsa, sample_principal, sample_resource):
        """Test require_permission decorator."""
        # Grant permission
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        auth_fsa.grant_permission(sample_principal.id, permission)

        # Define decorated function
        @auth_fsa.require_permission(sample_resource, PermissionType.READ)
        def protected_function(principal: Principal):
            return "success"

        result = protected_function(sample_principal)
        assert result == "success"

    def test_require_permission_decorator_denied(
        self, auth_fsa, sample_principal, sample_resource
    ):
        """Test require_permission decorator with denied access."""

        @auth_fsa.require_permission(sample_resource, PermissionType.DELETE)
        def protected_function(principal: Principal):
            return "success"

        with pytest.raises(PermissionDeniedError):
            protected_function(sample_principal)


# ============================================================================
# Test Authorization FSA - Caching
# ============================================================================


class TestAuthorizationFSACache:
    """Test cases for caching functionality."""

    def test_cache_hit(self, auth_fsa, sample_principal, sample_resource):
        """Test cache hit on repeated authorization."""
        # Grant permission
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        auth_fsa.grant_permission(sample_principal.id, permission)

        # First call - cache miss
        decision1 = auth_fsa.authorize(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )

        # Second call - cache hit
        decision2 = auth_fsa.authorize(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )

        assert decision1.allowed == decision2.allowed

        # Check cache stats
        stats = auth_fsa.get_cache_stats()
        assert stats["hits"] >= 1

    def test_cache_invalidation_on_grant(self, auth_fsa, sample_principal, sample_resource):
        """Test cache invalidation when permission is granted."""
        # First authorization - denied
        decision1 = auth_fsa.authorize(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )
        assert decision1.allowed is False

        # Grant permission (should invalidate cache)
        permission = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        auth_fsa.grant_permission(sample_principal.id, permission)

        # Second authorization - allowed
        decision2 = auth_fsa.authorize(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )
        assert decision2.allowed is True

    def test_clear_cache(self, auth_fsa):
        """Test clearing cache."""
        auth_fsa.clear_cache()
        stats = auth_fsa.get_cache_stats()
        assert stats["size"] == 0


# ============================================================================
# Test Authorization FSA - Audit Logging
# ============================================================================


class TestAuthorizationFSAAudit:
    """Test cases for audit logging."""

    def test_audit_log_on_authorize(self, auth_fsa, sample_principal, sample_resource):
        """Test that authorization creates audit log."""
        auth_fsa.authorize(
            sample_principal,
            sample_resource,
            PermissionType.READ,
        )

        logs = auth_fsa.get_audit_logs(principal_id=sample_principal.id)
        assert len(logs) > 0

    def test_audit_log_filtering(self, auth_fsa, sample_principal, sample_resource):
        """Test filtering audit logs."""
        # Perform multiple authorizations
        auth_fsa.authorize(sample_principal, sample_resource, PermissionType.READ)
        auth_fsa.authorize(sample_principal, sample_resource, PermissionType.UPDATE)

        # Get logs for specific action
        logs = auth_fsa.get_audit_logs(
            principal_id=sample_principal.id,
            action=AuditAction.ACCESS_DENIED,
        )

        for log in logs:
            assert log.action == AuditAction.ACCESS_DENIED


# ============================================================================
# Test Authorization FSA - Statistics
# ============================================================================


class TestAuthorizationFSAStats:
    """Test cases for statistics."""

    def test_get_stats(self, auth_fsa, sample_principal):
        """Test getting FSA statistics."""
        # Register session
        auth_fsa.register_session(sample_principal)

        # Create role
        role = Role(name="test-role", type=RoleType.CUSTOM)
        auth_fsa.create_role(role)

        # Get stats
        stats = auth_fsa.get_stats()

        assert stats["state"] == auth_fsa.state.value
        assert stats["principals"]["sessions"] >= 1
        assert stats["roles"] >= 1
        assert "cache" in stats


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_multi_tenant_scenario(self):
        """Test multi-tenant authorization scenario."""
        fsa = AuthorizationFSA()

        # Create principals from different tenants
        user1 = Principal(id="user-1", tenant_id="tenant-1")
        user2 = Principal(id="user-2", tenant_id="tenant-2")

        # Create tenant-specific resources
        resource1 = Resource(
            id="resource-1",
            type=ResourceType.API,
            tenant_id="tenant-1",
        )
        resource2 = Resource(
            id="resource-2",
            type=ResourceType.API,
            tenant_id="tenant-2",
        )

        # Grant permissions
        perm1 = Permission(
            name="api:read",
            resource_type=ResourceType.API,
            action=PermissionType.READ,
            resource_pattern="*",
            tenant_id="tenant-1",
        )
        fsa.grant_permission(user1.id, perm1)

        # User1 can access resource1
        decision = fsa.authorize(user1, resource1, PermissionType.READ)
        assert decision.allowed is True

        # User1 cannot access resource2 (different tenant)
        decision = fsa.authorize(user1, resource2, PermissionType.READ)
        assert decision.allowed is False

    def test_hierarchical_roles_scenario(self):
        """Test hierarchical roles scenario."""
        fsa = AuthorizationFSA()

        # Create role hierarchy: admin -> manager -> developer
        dev_perm = Permission(
            name="code:read",
            resource_type=ResourceType.FILE,
            action=PermissionType.READ,
        )
        developer = Role(
            name="developer",
            type=RoleType.CUSTOM,
            permissions=[dev_perm],
        )

        mgr_perm = Permission(
            name="code:update",
            resource_type=ResourceType.FILE,
            action=PermissionType.UPDATE,
        )
        manager = Role(
            name="manager",
            type=RoleType.CUSTOM,
            parent_roles=["developer"],
            permissions=[mgr_perm],
        )

        admin_perm = Permission(
            name="code:delete",
            resource_type=ResourceType.FILE,
            action=PermissionType.DELETE,
        )
        admin = Role(
            name="admin",
            type=RoleType.CUSTOM,
            parent_roles=["manager"],
            permissions=[admin_perm],
        )

        fsa.create_role(developer)
        fsa.create_role(manager)
        fsa.create_role(admin)

        # Assign admin role to user
        principal = Principal(id="user-1", tenant_id="tenant-1")
        fsa.assign_role(principal.id, "admin")

        # Admin should have all permissions (read, update, delete)
        permissions = fsa.get_effective_permissions(principal)
        perm_names = [p.name for p in permissions]

        assert "code:read" in perm_names
        assert "code:update" in perm_names
        assert "code:delete" in perm_names

    def test_complex_policy_scenario(self):
        """Test complex ABAC policy scenario."""
        fsa = AuthorizationFSA()

        # Policy: Allow engineering to read production resources during business hours
        # Deny delete operations on production resources
        allow_rule = PolicyRule(
            name="allow-eng-read-prod",
            effect=PolicyEffect.ALLOW,
            actions=[PermissionType.READ],
            resource_types=[ResourceType.API],
            principal_conditions={"department": "engineering"},
            resource_conditions={"environment": "production"},
            priority=10,
        )

        deny_rule = PolicyRule(
            name="deny-delete-prod",
            effect=PolicyEffect.DENY,
            actions=[PermissionType.DELETE],
            resource_types=[ResourceType.API],
            resource_conditions={"environment": "production"},
            priority=1,  # Higher priority (lower number)
        )

        policy = Policy(
            name="production-policy",
            rules=[allow_rule, deny_rule],
            tenant_id="tenant-1",
        )

        fsa.add_policy(policy)

        # Test allow rule
        eng_user = Principal(
            id="eng-1",
            tenant_id="tenant-1",
            attributes={"department": "engineering"},
        )
        prod_resource = Resource(
            id="api-1",
            type=ResourceType.API,
            tenant_id="tenant-1",
            attributes={"environment": "production"},
        )

        # Read should be allowed
        decision = fsa.authorize(eng_user, prod_resource, PermissionType.READ)
        assert decision.allowed is True

        # Delete should be denied (higher priority deny rule)
        decision = fsa.authorize(eng_user, prod_resource, PermissionType.DELETE)
        assert decision.allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

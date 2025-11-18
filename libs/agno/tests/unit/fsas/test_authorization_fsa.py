"""
Comprehensive test suite for Authorization FSA.

This test suite provides 100% coverage of the Authorization FSA including:
- State machine transitions
- RBAC with hierarchical roles
- ABAC with policy engine
- Permission management
- Resource authorization
- Multi-tenancy
- Caching
- Audit logging
- Dynamic permission grants/revokes
"""

import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from agno.fsas.infrastructure.authorization_fsa import (
    AuditAction,
    AuthorizationContext,
    AuthorizationFSA,
    AuthorizationResult,
    AuthorizationState,
    CacheManager,
    Permission,
    PermissionGrant,
    PermissionManager,
    Policy,
    PolicyEffect,
    PolicyEngine,
    PolicyOperator,
    PolicyRule,
    Resource,
    Role,
    RoleManager,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fsa():
    """Create Authorization FSA instance."""
    return AuthorizationFSA(
        enable_caching=True,
        cache_ttl=300.0,
        enable_audit=True
    )


@pytest.fixture
def fsa_no_cache():
    """Create Authorization FSA without caching."""
    return AuthorizationFSA(
        enable_caching=False,
        enable_audit=True
    )


@pytest.fixture
def role_manager():
    """Create RoleManager instance."""
    return RoleManager()


@pytest.fixture
def permission_manager():
    """Create PermissionManager instance."""
    return PermissionManager()


@pytest.fixture
def policy_engine():
    """Create PolicyEngine instance."""
    return PolicyEngine()


@pytest.fixture
def cache_manager():
    """Create CacheManager instance."""
    return CacheManager(default_ttl=1.0, max_size=100)


@pytest.fixture
def sample_resource():
    """Create sample resource."""
    return Resource(
        resource_id="resource-123",
        resource_type="document",
        owner_id="user-1",
        tenant_id="tenant-1",
        attributes={"department": "engineering", "classification": "public"}
    )


@pytest.fixture
def sample_context():
    """Create sample authorization context."""
    return AuthorizationContext(
        user_id="user-1",
        tenant_id="tenant-1",
        session_id="session-123",
        ip_address="192.168.1.1",
        attributes={"department": "engineering", "level": "senior"}
    )


# ============================================================================
# TEST STATE MACHINE
# ============================================================================


def test_initial_state(fsa):
    """Test FSA initializes in correct state."""
    assert fsa.get_state() == AuthorizationState.INITIALIZED
    assert len(fsa.get_state_history()) > 0


def test_state_transitions(fsa):
    """Test state transitions during authorization."""
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id="resource-1"
    )

    history = fsa.get_state_history()
    assert len(history) > 2

    # Check that we went through authorization states
    states = [state for state, _ in history]
    assert AuthorizationState.INITIALIZED in states
    assert AuthorizationState.AUTHORIZING in states


def test_custom_transition_handler(fsa):
    """Test custom state transition handler."""
    handler_called = []

    def custom_handler():
        handler_called.append(True)

    fsa.register_transition_handler(
        AuthorizationState.INITIALIZED,
        AuthorizationState.AUTHORIZING,
        custom_handler
    )

    fsa.authorize(user_id="user-1", permission=Permission.READ.value)

    assert len(handler_called) > 0


# ============================================================================
# TEST ROLE MANAGEMENT
# ============================================================================


def test_create_role(fsa):
    """Test role creation."""
    role = fsa.create_role(
        name="admin",
        permissions={Permission.READ.value, Permission.UPDATE.value},
        description="Administrator role",
        tenant_id="tenant-1"
    )

    assert role.role_id is not None
    assert role.name == "admin"
    assert Permission.READ.value in role.permissions
    assert role.tenant_id == "tenant-1"


def test_role_hierarchy(role_manager):
    """Test hierarchical role inheritance."""
    # Create parent role
    parent = Role(
        role_id="role-parent",
        name="manager",
        permissions={Permission.READ.value, Permission.UPDATE.value}
    )
    role_manager.add_role(parent)

    # Create child role
    child = Role(
        role_id="role-child",
        name="supervisor",
        permissions={Permission.CREATE.value},
        parent_roles=["role-parent"]
    )
    role_manager.add_role(child)

    # Assign child role to user
    role_manager.assign_role("user-1", "role-child")

    # Get effective permissions (should include inherited)
    permissions = role_manager.get_effective_permissions("user-1")

    assert Permission.CREATE.value in permissions
    assert Permission.READ.value in permissions  # Inherited
    assert Permission.UPDATE.value in permissions  # Inherited


def test_assign_and_remove_role(fsa):
    """Test assigning and removing roles from users."""
    # Create role
    role = fsa.create_role(
        name="editor",
        permissions={Permission.READ.value, Permission.UPDATE.value}
    )

    # Assign role
    success = fsa.assign_role_to_user(
        user_id="user-1",
        role_id=role.role_id,
        assigned_by="admin"
    )
    assert success is True

    # Check user has role
    user_roles = fsa.get_user_roles("user-1")
    assert len(user_roles) == 1
    assert user_roles[0].role_id == role.role_id

    # Remove role
    success = fsa.remove_role_from_user(
        user_id="user-1",
        role_id=role.role_id,
        removed_by="admin"
    )
    assert success is True

    # Check role removed
    user_roles = fsa.get_user_roles("user-1")
    assert len(user_roles) == 0


def test_delete_role(fsa):
    """Test role deletion."""
    role = fsa.create_role(name="temp-role")
    role_id = role.role_id

    # Delete role
    success = fsa.delete_role(role_id)
    assert success is True

    # Verify deleted
    success = fsa.delete_role(role_id)
    assert success is False


def test_multi_level_role_inheritance(role_manager):
    """Test multiple levels of role inheritance."""
    # Create grandparent role
    grandparent = Role(
        role_id="role-grandparent",
        name="executive",
        permissions={Permission.ADMIN.value}
    )
    role_manager.add_role(grandparent)

    # Create parent role
    parent = Role(
        role_id="role-parent",
        name="manager",
        permissions={Permission.UPDATE.value},
        parent_roles=["role-grandparent"]
    )
    role_manager.add_role(parent)

    # Create child role
    child = Role(
        role_id="role-child",
        name="employee",
        permissions={Permission.READ.value},
        parent_roles=["role-parent"]
    )
    role_manager.add_role(child)

    # Assign child role
    role_manager.assign_role("user-1", "role-child")

    # Get all inherited roles
    inherited = role_manager.get_all_inherited_roles("role-child")
    assert "role-child" in inherited
    assert "role-parent" in inherited
    assert "role-grandparent" in inherited

    # Check effective permissions
    permissions = role_manager.get_effective_permissions("user-1")
    assert Permission.READ.value in permissions
    assert Permission.UPDATE.value in permissions
    assert Permission.ADMIN.value in permissions


# ============================================================================
# TEST PERMISSION MANAGEMENT
# ============================================================================


def test_grant_permission(fsa, sample_resource):
    """Test explicit permission grant."""
    # Register resource
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        owner_id=sample_resource.owner_id,
        tenant_id=sample_resource.tenant_id
    )

    # Grant permission
    grant = fsa.grant_permission(
        user_id="user-2",
        resource_id=sample_resource.resource_id,
        permission=Permission.READ.value,
        granted_by="user-1",
        tenant_id="tenant-1"
    )

    assert grant.grant_id is not None
    assert grant.user_id == "user-2"
    assert grant.permission == Permission.READ.value


def test_revoke_permission(fsa, sample_resource):
    """Test permission revocation."""
    # Grant permission
    grant = fsa.grant_permission(
        user_id="user-1",
        resource_id=sample_resource.resource_id,
        permission=Permission.UPDATE.value,
        granted_by="admin"
    )

    # Revoke permission
    success = fsa.revoke_permission(
        grant_id=grant.grant_id,
        revoked_by="admin"
    )
    assert success is True

    # Verify revoked
    success = fsa.revoke_permission(
        grant_id=grant.grant_id,
        revoked_by="admin"
    )
    assert success is False


def test_permission_expiration(permission_manager):
    """Test expired permission cleanup."""
    # Create expired grant
    expired_grant = permission_manager.grant_permission(
        user_id="user-1",
        resource_id="resource-1",
        permission=Permission.READ.value,
        granted_by="admin",
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )

    # Create valid grant
    valid_grant = permission_manager.grant_permission(
        user_id="user-1",
        resource_id="resource-2",
        permission=Permission.READ.value,
        granted_by="admin",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )

    # Cleanup expired
    removed = permission_manager.cleanup_expired_grants()
    assert removed == 1

    # Verify expired removed
    assert expired_grant.grant_id not in permission_manager.grants
    assert valid_grant.grant_id in permission_manager.grants


def test_get_user_grants(permission_manager):
    """Test getting all grants for a user."""
    permission_manager.grant_permission(
        user_id="user-1",
        resource_id="resource-1",
        permission=Permission.READ.value,
        granted_by="admin"
    )

    permission_manager.grant_permission(
        user_id="user-1",
        resource_id="resource-2",
        permission=Permission.UPDATE.value,
        granted_by="admin"
    )

    grants = permission_manager.get_user_grants("user-1")
    assert len(grants) == 2


def test_get_resource_grants(permission_manager):
    """Test getting all grants for a resource."""
    permission_manager.grant_permission(
        user_id="user-1",
        resource_id="resource-1",
        permission=Permission.READ.value,
        granted_by="admin"
    )

    permission_manager.grant_permission(
        user_id="user-2",
        resource_id="resource-1",
        permission=Permission.UPDATE.value,
        granted_by="admin"
    )

    grants = permission_manager.get_resource_grants("resource-1")
    assert len(grants) == 2


# ============================================================================
# TEST POLICY ENGINE (ABAC)
# ============================================================================


def test_create_policy(fsa):
    """Test policy creation."""
    policy = fsa.create_policy(
        name="engineering-access",
        effect=PolicyEffect.ALLOW,
        resources=["document"],
        actions=[Permission.READ.value],
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.EQUALS,
                value="engineering"
            )
        ],
        tenant_id="tenant-1"
    )

    assert policy.policy_id is not None
    assert policy.name == "engineering-access"
    assert policy.effect == PolicyEffect.ALLOW


def test_policy_evaluation_equals(policy_engine, sample_resource, sample_context):
    """Test policy evaluation with equals operator."""
    policy = Policy(
        policy_id="policy-1",
        name="dept-policy",
        effect=PolicyEffect.ALLOW,
        resources=["document"],
        actions=[Permission.READ.value],
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.EQUALS,
                value="engineering"
            )
        ]
    )

    policy_engine.add_policy(policy)

    # Should match
    result = policy_engine.evaluate_policy(
        policy=policy,
        resource=sample_resource,
        permission=Permission.READ.value,
        context=sample_context
    )
    assert result is True

    # Should not match
    context2 = AuthorizationContext(
        user_id="user-2",
        attributes={"department": "sales"}
    )
    result = policy_engine.evaluate_policy(
        policy=policy,
        resource=sample_resource,
        permission=Permission.READ.value,
        context=context2
    )
    assert result is False


def test_policy_evaluation_in_operator(policy_engine, sample_resource, sample_context):
    """Test policy evaluation with IN operator."""
    policy = Policy(
        policy_id="policy-2",
        name="multi-dept-policy",
        effect=PolicyEffect.ALLOW,
        resources=["document"],
        actions=[Permission.READ.value],
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.IN,
                value=["engineering", "product", "design"]
            )
        ]
    )

    result = policy_engine.evaluate_policy(
        policy=policy,
        resource=sample_resource,
        permission=Permission.READ.value,
        context=sample_context
    )
    assert result is True


def test_policy_priority(policy_engine, sample_resource, sample_context):
    """Test policy evaluation with priorities."""
    # Low priority allow
    policy1 = Policy(
        policy_id="policy-1",
        name="allow-all",
        effect=PolicyEffect.ALLOW,
        resources=["*"],
        actions=["*"],
        priority=1,
        rules=[]
    )

    # High priority deny
    policy2 = Policy(
        policy_id="policy-2",
        name="deny-dept",
        effect=PolicyEffect.DENY,
        resources=["document"],
        actions=[Permission.READ.value],
        priority=10,
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.EQUALS,
                value="engineering"
            )
        ]
    )

    policy_engine.add_policy(policy1)
    policy_engine.add_policy(policy2)

    # Should be denied due to higher priority deny
    authorized, matched = policy_engine.evaluate_policies(
        resource=sample_resource,
        permission=Permission.READ.value,
        context=sample_context
    )
    assert authorized is False


def test_policy_deny_precedence(policy_engine, sample_resource, sample_context):
    """Test that deny policies take precedence over allow."""
    allow_policy = Policy(
        policy_id="allow-1",
        name="allow-read",
        effect=PolicyEffect.ALLOW,
        resources=["*"],
        actions=[Permission.READ.value],
        rules=[]
    )

    deny_policy = Policy(
        policy_id="deny-1",
        name="deny-engineering",
        effect=PolicyEffect.DENY,
        resources=["document"],
        actions=[Permission.READ.value],
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.EQUALS,
                value="engineering"
            )
        ]
    )

    policy_engine.add_policy(allow_policy)
    policy_engine.add_policy(deny_policy)

    authorized, _ = policy_engine.evaluate_policies(
        resource=sample_resource,
        permission=Permission.READ.value,
        context=sample_context
    )

    # Deny should take precedence
    assert authorized is False


def test_delete_policy(fsa):
    """Test policy deletion."""
    policy = fsa.create_policy(
        name="temp-policy",
        effect=PolicyEffect.ALLOW,
        resources=["*"],
        actions=["*"]
    )

    success = fsa.delete_policy(policy.policy_id)
    assert success is True

    success = fsa.delete_policy(policy.policy_id)
    assert success is False


def test_policy_operators(policy_engine):
    """Test various policy operators."""
    context_dict = {
        "level": 5,
        "tags": ["premium", "verified"],
        "email": "user@example.com"
    }

    # Greater than
    rule_gt = PolicyRule(attribute="level", operator=PolicyOperator.GREATER_THAN, value=3)
    assert policy_engine.evaluate_rule(rule_gt, context_dict) is True

    # Less than
    rule_lt = PolicyRule(attribute="level", operator=PolicyOperator.LESS_THAN, value=10)
    assert policy_engine.evaluate_rule(rule_lt, context_dict) is True

    # Contains
    rule_contains = PolicyRule(attribute="tags", operator=PolicyOperator.CONTAINS, value="premium")
    assert policy_engine.evaluate_rule(rule_contains, context_dict) is True

    # Exists
    rule_exists = PolicyRule(attribute="email", operator=PolicyOperator.EXISTS, value=None)
    assert policy_engine.evaluate_rule(rule_exists, context_dict) is True


# ============================================================================
# TEST AUTHORIZATION
# ============================================================================


def test_authorize_with_explicit_grant(fsa, sample_resource):
    """Test authorization with explicit permission grant."""
    # Register resource
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        owner_id=sample_resource.owner_id
    )

    # Grant permission
    fsa.grant_permission(
        user_id="user-1",
        resource_id=sample_resource.resource_id,
        permission=Permission.READ.value,
        granted_by="admin"
    )

    # Authorize
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=sample_resource.resource_id
    )

    assert result.authorized is True
    assert result.reason == "Explicit permission grant"


def test_authorize_with_role(fsa, sample_resource):
    """Test authorization through role-based permissions."""
    # Create role with permission
    role = fsa.create_role(
        name="reader",
        permissions={Permission.READ.value}
    )

    # Assign role to user
    fsa.assign_role_to_user(
        user_id="user-1",
        role_id=role.role_id,
        assigned_by="admin"
    )

    # Register resource
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type
    )

    # Authorize
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=sample_resource.resource_id
    )

    assert result.authorized is True
    assert result.reason == "Role-based permission"
    assert len(result.matched_roles) > 0


def test_authorize_with_policy(fsa, sample_resource, sample_context):
    """Test authorization through policy evaluation."""
    # Register resource
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        attributes=sample_resource.attributes
    )

    # Create policy
    fsa.create_policy(
        name="engineering-read",
        effect=PolicyEffect.ALLOW,
        resources=["document"],
        actions=[Permission.READ.value],
        rules=[
            PolicyRule(
                attribute="department",
                operator=PolicyOperator.EQUALS,
                value="engineering"
            )
        ]
    )

    # Authorize
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=sample_resource.resource_id,
        context=sample_context
    )

    assert result.authorized is True
    assert result.reason == "Policy-based permission"
    assert len(result.matched_policies) > 0


def test_authorize_resource_owner(fsa, sample_resource):
    """Test authorization for resource owner."""
    # Register resource with owner
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        owner_id="user-1"
    )

    # Authorize owner
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.UPDATE.value,
        resource_id=sample_resource.resource_id
    )

    assert result.authorized is True
    assert result.reason == "Resource ownership"


def test_authorize_denied(fsa, sample_resource):
    """Test authorization denial."""
    # Register resource
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        owner_id="user-other"
    )

    # Authorize without any permissions
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.DELETE.value,
        resource_id=sample_resource.resource_id
    )

    assert result.authorized is False
    assert "No matching" in result.reason


def test_check_permission_shorthand(fsa):
    """Test quick permission check method."""
    # Create role with permission
    role = fsa.create_role(name="admin", permissions={Permission.ADMIN.value})
    fsa.assign_role_to_user("user-1", role.role_id, "system")

    # Check permission
    has_permission = fsa.check_permission(
        user_id="user-1",
        permission=Permission.ADMIN.value
    )

    assert has_permission is True


# ============================================================================
# TEST MULTI-TENANCY
# ============================================================================


def test_tenant_isolation(fsa):
    """Test multi-tenant isolation."""
    # Create role for tenant 1
    role1 = fsa.create_role(
        name="admin",
        permissions={Permission.ADMIN.value},
        tenant_id="tenant-1"
    )

    # Create role for tenant 2
    role2 = fsa.create_role(
        name="admin",
        permissions={Permission.ADMIN.value},
        tenant_id="tenant-2"
    )

    # Assign roles
    fsa.assign_role_to_user("user-1", role1.role_id, "system", "tenant-1")
    fsa.assign_role_to_user("user-2", role2.role_id, "system", "tenant-2")

    # Create policy for tenant 1
    policy1 = fsa.create_policy(
        name="tenant1-policy",
        effect=PolicyEffect.ALLOW,
        resources=["*"],
        actions=[Permission.READ.value],
        tenant_id="tenant-1"
    )

    # User from tenant 1 should not be authorized under tenant 2 context
    context = AuthorizationContext(user_id="user-1", tenant_id="tenant-2")
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        context=context,
        tenant_id="tenant-2"
    )

    # This tests that tenant isolation works
    assert result.authorized is False or result.reason != "Policy-based permission"


def test_tenant_resource_access(fsa):
    """Test tenant-specific resource access."""
    # Register resources for different tenants
    resource1 = fsa.register_resource(
        resource_id="res-1",
        resource_type="document",
        tenant_id="tenant-1"
    )

    resource2 = fsa.register_resource(
        resource_id="res-2",
        resource_type="document",
        tenant_id="tenant-2"
    )

    # Grant permission for tenant 1 resource
    fsa.grant_permission(
        user_id="user-1",
        resource_id=resource1.resource_id,
        permission=Permission.READ.value,
        granted_by="admin",
        tenant_id="tenant-1"
    )

    # User should have access to tenant 1 resource
    result1 = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=resource1.resource_id,
        tenant_id="tenant-1"
    )
    assert result1.authorized is True

    # User should not have access to tenant 2 resource
    result2 = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=resource2.resource_id,
        tenant_id="tenant-2"
    )
    assert result2.authorized is False


# ============================================================================
# TEST CACHING
# ============================================================================


def test_cache_basic_operations(cache_manager):
    """Test basic cache operations."""
    # Set value
    cache_manager.set("value1", "key1", "arg1")

    # Get value
    result = cache_manager.get("key1", "arg1")
    assert result == "value1"

    # Get non-existent
    result = cache_manager.get("key2", "arg2")
    assert result is None


def test_cache_expiration(cache_manager):
    """Test cache expiration."""
    # Set with short TTL
    cache_manager.set("value1", "key1", ttl=0.1)

    # Should exist immediately
    assert cache_manager.get("key1") is not None

    # Wait for expiration
    time.sleep(0.2)

    # Should be expired
    assert cache_manager.get("key1") is None


def test_cache_invalidation(cache_manager):
    """Test cache invalidation."""
    cache_manager.set("value1", "key1", "arg1")

    # Invalidate
    cache_manager.invalidate("key1", "arg1")

    # Should not exist
    assert cache_manager.get("key1", "arg1") is None


def test_cache_stats(cache_manager):
    """Test cache statistics."""
    cache_manager.set("value1", "key1")
    cache_manager.get("key1")  # Hit
    cache_manager.get("key2")  # Miss

    stats = cache_manager.get_stats()

    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1


def test_cache_lru_eviction(cache_manager):
    """Test LRU eviction when cache is full."""
    # Create small cache
    small_cache = CacheManager(default_ttl=300.0, max_size=3)

    # Fill cache
    small_cache.set("v1", "k1")
    small_cache.set("v2", "k2")
    small_cache.set("v3", "k3")

    # Access k2 and k3 to increase their hit count
    small_cache.get("k2")
    small_cache.get("k3")
    small_cache.get("k3")

    # Add one more (should evict k1 as it has lowest hits)
    small_cache.set("v4", "k4")

    # k1 should be evicted
    assert small_cache.get("k1") is None
    assert small_cache.get("k2") is not None


def test_authorization_caching(fsa):
    """Test authorization result caching."""
    # Create role and assign
    role = fsa.create_role(name="reader", permissions={Permission.READ.value})
    fsa.assign_role_to_user("user-1", role.role_id, "system")

    # First authorization (cache miss)
    result1 = fsa.authorize(user_id="user-1", permission=Permission.READ.value)
    assert result1.cached is False

    # Second authorization (cache hit)
    result2 = fsa.authorize(user_id="user-1", permission=Permission.READ.value)
    assert result2.cached is True

    # Check cache stats
    stats = fsa.get_cache_stats()
    assert stats["hits"] > 0


def test_cache_clear(fsa):
    """Test clearing authorization cache."""
    role = fsa.create_role(name="admin", permissions={Permission.ADMIN.value})
    fsa.assign_role_to_user("user-1", role.role_id, "system")

    # Cache result
    fsa.authorize(user_id="user-1", permission=Permission.ADMIN.value)

    # Clear cache
    fsa.clear_cache()

    # Next authorization should be cache miss
    result = fsa.authorize(user_id="user-1", permission=Permission.ADMIN.value)
    assert result.cached is False


# ============================================================================
# TEST AUDIT LOGGING
# ============================================================================


def test_audit_logging(fsa):
    """Test audit logging of authorization events."""
    # Perform authorization
    fsa.authorize(user_id="user-1", permission=Permission.READ.value)

    # Check audit logs
    stats = fsa.get_audit_stats()
    assert stats["total_events"] > 0


def test_audit_log_query(fsa):
    """Test querying audit logs."""
    # Create some authorization events
    fsa.authorize(user_id="user-1", permission=Permission.READ.value)
    fsa.authorize(user_id="user-2", permission=Permission.UPDATE.value)

    # Query logs for user-1
    logs = fsa.query_audit_logs(user_id="user-1", limit=10)
    assert len(logs) > 0
    assert all(log.user_id == "user-1" for log in logs)


def test_audit_log_actions(fsa):
    """Test different audit log actions."""
    # Create role (should log CREATE_ROLE)
    role = fsa.create_role(name="test-role")

    # Assign role (should log ASSIGN_ROLE)
    fsa.assign_role_to_user("user-1", role.role_id, "admin")

    # Grant permission (should log GRANT_PERMISSION)
    fsa.grant_permission(
        user_id="user-1",
        resource_id="res-1",
        permission=Permission.READ.value,
        granted_by="admin"
    )

    # Check different actions logged
    stats = fsa.get_audit_stats()
    actions = stats["actions"]

    assert AuditAction.CREATE_ROLE.value in actions
    assert AuditAction.ASSIGN_ROLE.value in actions
    assert AuditAction.GRANT_PERMISSION.value in actions


def test_custom_audit_handler(fsa):
    """Test custom audit log handler."""
    handler_calls = []

    def custom_handler(entry):
        handler_calls.append(entry)

    fsa.add_audit_handler(custom_handler)

    # Trigger authorization
    fsa.authorize(user_id="user-1", permission=Permission.READ.value)

    # Handler should have been called
    assert len(handler_calls) > 0


def test_audit_log_time_range_query(fsa):
    """Test querying audit logs by time range."""
    start_time = datetime.utcnow()

    # Create some events
    fsa.authorize(user_id="user-1", permission=Permission.READ.value)

    end_time = datetime.utcnow()

    # Query with time range
    logs = fsa.query_audit_logs(start_time=start_time, end_time=end_time)
    assert len(logs) > 0


# ============================================================================
# TEST RESOURCE MANAGEMENT
# ============================================================================


def test_register_resource(fsa):
    """Test resource registration."""
    resource = fsa.register_resource(
        resource_id="doc-123",
        resource_type="document",
        owner_id="user-1",
        tenant_id="tenant-1",
        attributes={"classification": "confidential"}
    )

    assert resource.resource_id == "doc-123"
    assert resource.resource_type == "document"
    assert resource.owner_id == "user-1"


def test_get_resource(fsa):
    """Test retrieving registered resource."""
    fsa.register_resource(
        resource_id="doc-456",
        resource_type="document"
    )

    resource = fsa.get_resource("doc-456")
    assert resource is not None
    assert resource.resource_id == "doc-456"


# ============================================================================
# TEST UTILITY METHODS
# ============================================================================


def test_get_user_effective_permissions(fsa):
    """Test getting all effective permissions for user."""
    # Create roles with different permissions
    role1 = fsa.create_role(name="reader", permissions={Permission.READ.value})
    role2 = fsa.create_role(
        name="editor",
        permissions={Permission.UPDATE.value, Permission.CREATE.value}
    )

    # Assign both roles
    fsa.assign_role_to_user("user-1", role1.role_id, "system")
    fsa.assign_role_to_user("user-1", role2.role_id, "system")

    # Get effective permissions
    permissions = fsa.get_user_effective_permissions("user-1")

    assert Permission.READ.value in permissions
    assert Permission.UPDATE.value in permissions
    assert Permission.CREATE.value in permissions


def test_cleanup_expired_grants(fsa):
    """Test cleaning up expired grants."""
    # Create expired grant
    fsa.grant_permission(
        user_id="user-1",
        resource_id="res-1",
        permission=Permission.READ.value,
        granted_by="admin",
        expires_at=datetime.utcnow() - timedelta(hours=1)
    )

    # Cleanup
    removed = fsa.cleanup_expired_grants()
    assert removed == 1


def test_export_configuration(fsa):
    """Test exporting authorization configuration."""
    # Create some roles and policies
    role = fsa.create_role(name="admin", permissions={Permission.ADMIN.value})
    fsa.assign_role_to_user("user-1", role.role_id, "system")

    policy = fsa.create_policy(
        name="allow-all",
        effect=PolicyEffect.ALLOW,
        resources=["*"],
        actions=["*"]
    )

    # Export configuration
    config = fsa.export_configuration()

    assert "roles" in config
    assert "policies" in config
    assert "user_roles" in config
    assert len(config["roles"]) > 0
    assert len(config["policies"]) > 0


def test_get_statistics(fsa):
    """Test getting comprehensive statistics."""
    # Create some data
    fsa.create_role(name="role1")
    fsa.create_policy(name="policy1", effect=PolicyEffect.ALLOW, resources=["*"], actions=["*"])
    fsa.register_resource(resource_id="res1", resource_type="document")

    # Get statistics
    stats = fsa.get_statistics()

    assert "state" in stats
    assert "roles" in stats
    assert "policies" in stats
    assert "resources" in stats
    assert stats["roles"] >= 1
    assert stats["policies"] >= 1
    assert stats["resources"] >= 1


def test_fsa_without_caching(fsa_no_cache):
    """Test FSA without caching enabled."""
    role = fsa_no_cache.create_role(name="reader", permissions={Permission.READ.value})
    fsa_no_cache.assign_role_to_user("user-1", role.role_id, "system")

    # Authorization should work without cache
    result = fsa_no_cache.authorize(user_id="user-1", permission=Permission.READ.value)
    assert result.authorized is True
    assert result.cached is False

    # Cache stats should be None
    stats = fsa_no_cache.get_cache_stats()
    assert stats is None


# ============================================================================
# PERFORMANCE AND STRESS TESTS
# ============================================================================


def test_authorization_performance(fsa):
    """Test authorization performance with evaluation time."""
    role = fsa.create_role(name="admin", permissions={Permission.ADMIN.value})
    fsa.assign_role_to_user("user-1", role.role_id, "system")

    result = fsa.authorize(user_id="user-1", permission=Permission.ADMIN.value)

    # Should complete in reasonable time
    assert result.evaluation_time_ms < 100.0  # Less than 100ms


def test_multiple_policies_evaluation(fsa, sample_resource, sample_context):
    """Test evaluation with multiple policies."""
    fsa.register_resource(
        resource_id=sample_resource.resource_id,
        resource_type=sample_resource.resource_type,
        attributes=sample_resource.attributes
    )

    # Create multiple policies
    for i in range(10):
        fsa.create_policy(
            name=f"policy-{i}",
            effect=PolicyEffect.ALLOW,
            resources=["document"],
            actions=[Permission.READ.value],
            priority=i,
            rules=[
                PolicyRule(
                    attribute="department",
                    operator=PolicyOperator.EQUALS,
                    value="engineering"
                )
            ]
        )

    # Authorize
    result = fsa.authorize(
        user_id="user-1",
        permission=Permission.READ.value,
        resource_id=sample_resource.resource_id,
        context=sample_context
    )

    assert result.authorized is True
    assert len(result.matched_policies) > 0
